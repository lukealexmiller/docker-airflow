import pprint
import numpy as np
import pdb
import sys
import os.path
import time
import tensorflow as tf

this_dir = os.chdir("/root/faster_rcnn")

from lib.fast_rcnn.test import test_net
from lib.fast_rcnn.config import cfg, cfg_from_file
from lib.datasets.factory import get_imdb
from lib.networks.factory import get_network

cfg_file = "experiments/cfgs/faster_rcnn_end2end_wider.yml"
gpu_id = 0
network_name = "VGGnet_test"
iters = 110000
checkpoint_model = ("output/faster_rcnn_voc_vgg/voc_2007_trainval/VGGnet_fast_rcnn_iter_%d.ckpt")%iters
imdb_name = "voc_2007_trainval"
comp_mode = False

cfg_from_file(cfg_file)

print('Using config:')
pprint.pprint(cfg)
   
weights_filename = os.path.splitext(os.path.basename(checkpoint_model))[0]

imdb = get_imdb(imdb_name)
imdb.competition_mode(comp_mode)

device_name = '/gpu:{:d}'.format(gpu_id)
print device_name

network = get_network(network_name)
print 'Use network `{:s}` in training'.format(network_name)

# start a session
saver = tf.train.Saver()
sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))
saver.restore(sess, checkpoint_model)
print ('Loading model weights from {:s}').format(checkpoint_model)

test_net(sess, network, imdb, weights_filename)

sess.close()