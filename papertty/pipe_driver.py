
import array
import struct
from os import mkfifo, remove, getpid, kill, umask
from signal import signal, SIGUSR1
from IT8951.display import AutoDisplay
from IT8951 import EPD
from IT8951.constants import DisplayModes

class AutoPipeDisplay(AutoDisplay):

    def __init__(self):

        # get width and height
        try:
            with open(PipeDisplay.info_path) as f:
                info = f.read().strip()
                width, height, pid = [int(x) for x in info.split(',')]
        except FileNotFoundError:
            raise FileNotFoundError('Could not find display info. Is the daemon running?')

        AutoDisplay.__init__(self, width, height)

        self.display_pid = pid

        # tell managing process that we want to display stuff
        self._send_start_sig()

    def __del__(self):
        # tell managing process that we're done sending stuff
        done_attrs = struct.pack('hhhhh', -1, 0, 0, 0, 0)
        with open(PipeDisplay.data_path, 'wb') as pipe:
            pipe.write(done_attrs)

    def _send_start_sig(self):
        kill(self.display_pid, SIGUSR1)

    def update(self, data, xy, dims, mode):

        attrs = struct.pack('hhhhh', mode, xy[0], xy[1], dims[0], dims[1])

        with open(PipeDisplay.data_path, 'wb') as pipe:
            pipe.write(attrs)
            array.array('B', data).tofile(pipe)

        # wait for display to be ready
        with open(PipeDisplay.ready_path, 'rb') as f:
            f.read()

class PipeDisplay:

    data_path = '/tmp/epd_data'
    ready_path = '/tmp/epd_ready'
    info_path = '/tmp/epd_info'

    def __init__(self, epd=None, vcom=None):
        if epd is None:
            epd = EPD(vcom)

        self.epd = epd
        self.width = self.epd.width
        self.height = self.epd.height

        old_umask = umask(0)
        mkfifo(self.data_path)
        umask(old_umask)

        mkfifo(self.ready_path)
        with open(self.info_path, 'w') as f:
            f.write('{},{},{}\n'.format(self.width, self.height, getpid()))

        self.active = False

        # activate upon receiving SIGUSR1
        signal(SIGUSR1, self.activate)

    def __del__(self):
        remove(self.data_path)
        remove(self.ready_path)
        remove(self.info_path)

    def activate(self, signal, frame):
        self.active = True

    def run(self):
        while self.active:
            try:
                self.update_epd()
            except KeyboardInterrupt:
                break

    def update_epd(self):

        with open(self.data_path, 'rb') as f:

            # first ten bytes are info about update
            attrs = f.read(10)
            mode, x, y, w, h = struct.unpack('hhhhh', attrs)

            # if mode is -1, that means we're done sending data
            if mode == -1:
                self.active = False
                return

            # the rest is pixel data
            data = array.array('B')
            data.fromfile(f, w*h)

        xy = x,y
        dims = w,h

        # send image to controller
        self.epd.wait_display_ready()
        self.epd.load_img_area(
            data,
            xy=xy,
            dims=dims,
        )

        # display sent image
        self.epd.display_area(
            xy,
            dims,
            mode
        )

        # connect to pipe to tell that we are ready
        with open(self.ready_path, 'wb') as f:
            pass

def main():
    print('Initializing...')
    display = PipeDisplay(vcom=-2.06)
    print('Running...')
    display.run()

if __name__ == '__main__':
    main()
