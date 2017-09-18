import argparse
import os
import cv2
import cPickle
import numpy as np
import pprint
import time
import sys

"""Read pickled detection file, extract detections corresponding to
   correct class and and above a set threshold probability, and apply a 
   Gaussian smoothing kernel to the regions within the bounding boxes.
"""

def parse_args():
    """Parse input arguments
    """
    parser = argparse.ArgumentParser(
                        description='Blur faces using pickled detection file.')
    parser.add_argument('--image_dir', dest='image_dir',
                        help=('absolute path to directory containing images '
                              'and detection file'),
                        default=None, type=str)
    parser.add_argument('--threshold', dest='threshold',
                        help='probability threshold for positive detection',
                        default=0.8, type=float)
    parser.add_argument('--class_id', dest='cls_idx',
                        help='index of class to be blurred',
                        default=1, type=int)
    parser.add_argument('--kernel', dest='kxy',
                        help='size of Gaussian blurring  (odd)',
                        default=9, type=int)
    parser.add_argument('--sigma', dest='sxy',
                        help='sigma of Gaussian blurring kernel',
                        default=8, type=int)
    parser.add_argument('--compression', dest='compress',
                        help='png compression level',
                        default=0, type=int) 


    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    return args

def read_from_pickle(file_path):
    with open(file_path, 'rb') as f:
        data = cPickle.load(f)
    return data

def blur_face(frame,min_coord,max_coord,kxy,sxy):
    x1,y1 = min_coord
    x2,y2 = max_coord

    # Extract face region from frame
    face = frame[y1:y2,x1:x2]

    if kxy%2 != 1:
        kxy += 1
        print(('Warning: supplied kernel size was even. '
              'Increased by one to {:s}').format(kxy))
    # Blur region with using Gaussian smoothing kernel
    face_blur = cv2.GaussianBlur(face,(kxy,kxy),sxy)
    # DEBUG
    face_blur = np.zeros(face_blur.shape, np.uint8)

    # Replace face region with blurred version
    frame[y1:y2,x1:x2] = face_blur
    return frame

def read_annotation_write_to_frame(image_dir,cls_idx,threshold,compress,kxy,sxy):
    results_file_path = os.path.join(image_dir,'detections.pkl')
    bboxes_full = read_from_pickle(results_file_path)
    print(('Reading pickled detections from file: '
           '{:s}').format(results_file_path))
    bboxes_full = bboxes_full[cls_idx]

    # Get list of images in image_dir and sort according to numeric label
    images = [os.path.join(image_dir,name) for name in os.listdir(image_dir)
            if os.path.splitext(name)[1] == '.png']
    images.sort(key = lambda x: int(os.path.splitext(os.path.basename(x))[0]))
    num_images = len(images)

    print(('Running face blurring on {:d} frame(s) in: {:s}')
        .format(num_images,image_dir))
    
    # Set png compression level
    compression = [cv2.cv.CV_IMWRITE_PNG_COMPRESSION, compress]

    for i, bboxes in enumerate(bboxes_full):
        print('Processing frame: {:d}'.format(i))
        image_path = os.path.join(image_dir,images[i])
        im = cv2.imread(image_path)

        count = 0
        start_time = time.time()
        for bbox in bboxes:
            if bbox[4] >= threshold:
                count += 1
                min_coord, max_coord = (int(bbox[0]),int(bbox[1])), \
                                       (int(bbox[2]),int(bbox[3]))
                # Blur detected face region
                im = blur_face(im,min_coord,max_coord,kxy,sxy)

        # Write frame with blurred detections back to file.
        cv2.imwrite(image_path, im, compression)
        print(('Number of bounding boxes passing detection '
               'threshold: {:d}/{:d}').format(count,len(bboxes)))
        blur_time = time.time() - start_time
        print(('blur_face: {:d}/{:d} {:.3f}s')
              .format(i + 1, num_images, blur_time))

 
if __name__ == '__main__':
    args = parse_args()

    print('Face blurring function called with arguments:')
    pprint.pprint(args)

    read_annotation_write_to_frame(args.image_dir,args.cls_idx,
                               args.threshold,args.compress,args.kxy,args.sxy)
