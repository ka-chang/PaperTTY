'''
This file defines two classes for controlling the e-paper display.

The Controller class waits for input on some pipes (currently opened in tmp).
When it gets input there, it puts the data it receives onto the display.

The AutoWorkerDisplay class is a derived class from AutoDisplay. Instead of
directly updating the display like AutoEPDDisplay (from the IT8951 module) does,
it sends data to an instance of the Controller class, which should be running
in another process. This is nice because the Controller can run with root privileges
but any process with an AutoWorkerDisplay instance doesn't need root.
'''

import array
import struct
from os import mkfifo, remove, getpid, kill, umask
from os.path import isfile, exists
from IT8951.display import AutoDisplay
from IT8951.interface import EPD

class AutoWorkerDisplay(AutoDisplay):
    '''
    This class is a subclass of AutoDisplay, so it automatically
    tracks changes to its frame_buf attribute and sends display updates
    accordingly. However, this class doesn't update the display directly
    but instead sends data to a running instance of the Controller class
    through its named pipes.
    '''

    def __init__(self, **kwargs):

        # attempt to get lock on display. our lock is just creating a file
        try:
            open(Controller.lock_path, 'x').close()
            self.have_lock = True
        except FileExistsError:
            self.have_lock = False
            raise RuntimeError('Could not get a lock on display controller. '
                               'Is another process using it? If not, delete '
                               '{}'.format(Controller.lock_path))

        # get width and height
        try:
            with open(Controller.info_path) as f:
                info = f.read().strip()
                width, height, pid = [int(x) for x in info.split(',')]
        except FileNotFoundError:
            raise FileNotFoundError('Could not find display info. Is the daemon running?')

        AutoDisplay.__init__(self, width, height, **kwargs)

        self.display_pid = pid

    def __del__(self):
        if self.have_lock:
            # tell managing process that we're done sending stuff
            done_attrs = struct.pack('hhhhh', -1, 0, 0, 0, 0)
            with open(Controller.data_path, 'wb') as pipe:
                pipe.write(done_attrs)

            # remove lock
            remove(Controller.lock_path)

    def update(self, data, xy, dims, mode):
        '''
        This function is called by the functions defined in AutoDisplay
        when it needs to update the display.
        '''

        attrs = struct.pack('hhhhh', mode, xy[0], xy[1], dims[0], dims[1])

        with open(Controller.data_path, 'wb') as pipe:
            pipe.write(attrs)
            array.array('B', data).tofile(pipe)

        # wait for display to be ready
        with open(Controller.ready_path, 'rb') as f:
            f.read()

class Controller:
    '''
    This class receives data from other processes and displays it on the
    e-paper display. When activated (by a process creating the lock file,
    and then check_active() and run() being called in that order)
    it waits for data in its named pipes until it receives
    a special set of data that tell it to deactivate.
    '''

    data_path = '/tmp/epd_data'
    ready_path = '/tmp/epd_ready'
    info_path = '/tmp/epd_info'
    lock_path = '/tmp/epd_lock'

    def __init__(self, epd=None, vcom=None, flip=False):

        # track what files we have made so we can clean up at the end
        # we can't be sure we've made everything if e.g. there is an
        # exception raised while this is happening
        self.files_created = []

        if exists(self.info_path):
            raise RuntimeError('Display files already exist. Is there another '
                               'instance running?')

        if epd is None:
            epd = EPD(vcom)

        self.epd = epd
        self.width = self.epd.width
        self.height = self.epd.height
        self.flip = flip

        # we need to set the permissions of the named pipes correctly so
        # that this class can be run as root, but the communicating processes
        # don't need root
        old_umask = umask(0)
        mkfifo(self.data_path)
        self.files_created.append(self.data_path)
        umask(old_umask)

        mkfifo(self.ready_path)
        self.files_created.append(self.ready_path)

        with open(self.info_path, 'w') as f:
            f.write('{},{},{}\n'.format(self.width, self.height, getpid()))
        self.files_created.append(self.info_path)

        self.active = False

    def __del__(self):
        for f in self.files_created:
            remove(f)

    def check_active(self):
        # we are active if the lock file exists (i.e. someone is trying to
        # get a lock on the display)
        if isfile(self.lock_path):
            self.active = True
            return True
        else:
            return False

    def run(self):
        '''
        Run the display update loop. Stop either if we have deactivated,
        or if we receive SIGINT
        '''
        while self.active:
            self.update_epd()

    def update_epd(self):
        '''
        Receive data from the named pipe, process it, and display it
        on the EPD.
        '''

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

        if self.flip:
            xy = (self.width - x - w, self.height - y - h)
            data = data[::-1]
        else:
            xy = x, y
        dims = w, h

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
