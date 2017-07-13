import argparse
import os
import cv2 #TODO: Repalce OpenCV
import cPickle
import logging
import numpy as np
import tensorflow as tf

# Add Faster R-CNN path to allow for importing
sys.path.append('/usr/local/airflow/faster_rcnn')

from lib.fast_rcnn.test import im_detect
from lib.fast_rcnn.config import cfg, cfg_from_file
from lib.networks.factory import get_network
from lib.utils.timer import Timer
from lib.utils.cython_nms import nms, nms_new #TODO: Require both of there?

def parse_args():
    """Parse input arguments
    """
    parser = argparse.ArgumentParser(description='Run inference on Fast R-CNN network.')
    parser.add_argument('--gpu', dest='gpu_id', help='GPU id to use',
                        default=0, type=int)
    parser.add_argument('--weights', dest='weights',
                        help='path to weights file to restore model',
                        default=None, type=str)
    parser.add_argument('--cfg', dest='cfg_file',
                        help='path to configuration file', default=None, type=str)
    parser.add_argument('--network', dest='network_name',
                        help='name of the network',
                        default=None, type=str)
    parser.add_argument('--image_dir', dest='image_dir',
                        help='absolute path to directory containing images',
                        default=None, type=str)
    parser.add_argument('--num_classes', dest='num_classes',
                        help='number of object classes to detect',
                        default=None, type=int)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    return args

def test_net(sess, net, image_dir, num_classes=2, max_per_image=300, thresh=0.05):
    """Perform inference using a Fast R-CNN network on a folder of images.
    """
    images = [name for name in os.listdir(image_dir) if os.path.isfile(os.path.join(image_dir, name))]
    num_images = len(images)
    logging.info('Running inference on {:s} frame(s) in: {:s}'.format(num_images,image_dir))
    
    # All detections are collected into:
    #    all_boxes[cls][image] = N x 5 array of detections in
    #    (x1, y1, x2, y2, score)
    all_boxes = [[[] for _ in xrange(num_images)]
                 for _ in xrange(num_classes)]

    # Start timers to keep track of inference progress
    _t = {'im_detect' : Timer(), 'misc' : Timer()}

    det_file = os.path.join(image_dir, 'detections.pkl') #TODO: Change path?
    # if os.path.exists(det_file):
    #     with open(det_file, 'rb') as f:
    #         all_boxes = cPickle.load(f)

    for i in xrange(num_images): #TODO: Use tf.Record()
        # Filter out any ground truth boxes
        box_proposals = None

        im = cv2.imread(images(i))

        _t['im_detect'].tic()
        scores, boxes = im_detect(sess, net, im, box_proposals)
        detect_time = _t['im_detect'].toc(average=False)

        _t['misc'].tic()
        # Skip j = 0, because it's the background class
        for j in xrange(1, num_classes):
            inds = np.where(scores[:, j] > thresh)[0]
            cls_scores = scores[inds, j]
            cls_boxes = boxes[inds, j*4:(j+1)*4]
            cls_dets = np.hstack((cls_boxes, cls_scores[:, np.newaxis])) \
                .astype(np.float32, copy=False)
            keep = nms(cls_dets, cfg.TEST.NMS)
            cls_dets = cls_dets[keep, :]
            all_boxes[j][i] = cls_dets

        # Limit to max_per_image detections *over all classes*
        if max_per_image > 0:
            image_scores = np.hstack([all_boxes[j][i][:, -1]
                                      for j in xrange(1, num_classes)])
            if len(image_scores) > max_per_image:
                image_thresh = np.sort(image_scores)[-max_per_image]
                for j in xrange(1, num_classes):
                    keep = np.where(all_boxes[j][i][:, -1] >= image_thresh)[0]
                    all_boxes[j][i] = all_boxes[j][i][keep, :]
        nms_time = _t['misc'].toc(average=False)

        logging.info('im_detect: {:d}/{:d} {:.3f}s {:.3f}s' \
              .format(i + 1, num_images, detect_time, nms_time))

    # Store detections as pickle file.
    with open(det_file, 'wb') as f:
        cPickle.dump(all_boxes, f, cPickle.HIGHEST_PROTOCOL) #TODO: Is this the best format?

if __name__ == '__main__':
    args = parse_args()
    cfg_from_file(args.cfg_file)

    # Restrict access to user-defined GPU
    cfg.gpu_id = args.gpu_id
    logging.info('Restricting access to: /gpu:{:d}'.format(cfg.gpu_id))
    os.environ["CUDA_VISIBLE_DEVICES"] = "{:d}".format(cfg.gpu_id)

    # Use 4 anchor scales
    cfg.ANCHOR_SCALES = [4,8,16,32]

    logging.info('Using config:') #TODO: Is this really needed?
    for line in pprint.pformat(cfg).split('\n'):
        logging.debug(line)

    # Define graph
    network = get_network(args.network_name)
    logging.info('Loaded network: `{:s}`'.format(args.network_name))

    # Extract filename of weights to pass to test_net()
    weights_filename = os.path.splitext(os.path.basename(args.weights))[0]

    # Start TF session
    saver = tf.train.Saver()
    with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as sess:

        saver.restore(sess, args.weights)
        logging.info(('Loaded model weights from {:s}').format(args.weights))

        test_net(sess, network, args.image_dir, args.num_classes)
