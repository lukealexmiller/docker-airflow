import subprocess as sp

import numpy as np


FFMPEG_BIN = "ffmpeg"

command = [ FFMPEG_BIN,
            '-i', 'myHolidays.mp4',
            '-f', 'image2pipe',
            '-pix_fmt', 'rgb24',
            '-vcodec', 'rawvideo', '-']

# Note: set bufsize > individual frame size
pipe = sp.Popen(command, stdout = sp.PIPE, bufsize=10**8)

# read 420*360*3 bytes (= 1 frame)
raw_image = pipe.stdout.read(1920*1080*3)
# transform the byte read into a numpy array
image =  np.fromstring(raw_image, dtype='uint8')
#image = image.reshape((360,420,3))

# throw away the data in the pipe's buffer.
pipe.stdout.flush()

#ffmpeg -i ~/DirectoryName/video_name.mp4 -s hd720 -r 30 -f image2  image%05d.jpg