import cv2
import logging
import os
import argparse

def parse_args():
    """Parse input arguments."""
    parser = argparse.ArgumentParser(description='Extract frames from a video file.')
    parser.add_argument('--source_dir', dest='source_dir', help='directory containing video file',
                        default='', type=str)
    parser.add_argument('--def', dest='prototxt',
                        help='prototxt file defining the network',
                        default=None, type=str)

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    return args

class FileStreamer(object):
    """Creates an instance of a video stream with user-defined properties 
    in a thread."""
    def __init__(self,FILENAME,CAMERA_WIDTH=300,CAMERA_HEIGHT=300):
        """Initialise camera stream. The stream will wait until
        a camera is attached to the specified port CAMERA_NUM.
        """
        self._FILE_PATH = os.path.join(cfg.DATA_DIR,FILENAME)
        print(self._FILE_PATH)
        self._capture = cv2.VideoCapture(self._FILE_PATH)

        if not self._capture.isOpened():
            print("FEED: incorrect path specified, exiting.")
            return

        self.setup_stream(CAMERA_WIDTH,CAMERA_HEIGHT)
        self.current_frame = self._capture.read()[1]
    
    def setup_stream(self,CAMERA_WIDTH,CAMERA_HEIGHT):
        """Configure video stream properties: HxW"""
        self._CAMERA_WIDTH = CAMERA_WIDTH
        self._CAMERA_HEIGHT = CAMERA_HEIGHT
        self._capture.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,self._CAMERA_WIDTH)
        self._capture.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,self._CAMERA_HEIGHT)
 
    def _update_frame(self):
        """Captures frames from the video stream and resizes to user-defined HxW.
        TODO: Remove resize() call by fixing set() calls in __init__.
        """
        current_frame_temp = self._capture.read()[1]
        self.current_frame = cv2.resize(current_frame_temp,
                        (self._CAMERA_WIDTH,self._CAMERA_HEIGHT))

    def get_frame(self):
        """Return current frame from video stream."""
        self._update_frame()
        return self.current_frame

if __name__ == '__main__':
    args = parse_args()
    logging.info('Called with args: {}'.format(args))
    
    vid = FileStreamer()
    frame = vid.get_frame()
    frame


