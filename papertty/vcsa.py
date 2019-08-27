
import struct
import fcntl
import termios
import numpy as np

TTY_DTYPE = np.dtype([('char', np.ubyte), ('attr', np.ubyte)])

def auto_resize_tty(ttyn, font_dims, display_dims):
    '''
    Find the number of rows and columns of font_dims that can fit in display_dims,
    and then set ttyn's size to that.
    '''
    rows = display_dims[1]//font_dims[1]
    cols = display_dims[0]//font_dims[0]

    print('setting TTY size to {} rows, {} cols'.format(rows, cols))

    tty_path = '/dev/tty{}'.format(ttyn)
    with open(tty_path, 'w') as tty:
        size = struct.pack("HHHH", int(rows), int(cols), 0, 0)
        try:
            fcntl.ioctl(tty.fileno(), termios.TIOCSWINSZ, size)
        except OSError:
            print("Could not set TTY size (rows={}, cols={}); continuing.".format(rows, cols))

def read_vcsa(ttyn):
    '''
    Read the vcsa for tty number ttyn into numpy array
    '''

    if not isinstance(ttyn, str):
        vcsa = '/dev/vcsa{}'.format(ttyn)
    else:
        vcsa = ttyn  # mostly for debugging, allow reading arbitrary files

    with open(vcsa, 'rb') as f:
        # read the first 4 bytes to get the console attributes
        attributes = f.read(4)
        raw_data = f.read()

    rows, cols, cursor_x, cursor_y = list(map(ord, struct.unpack('cccc', attributes)))

    # read the remaining char-attribute pairs into a numpy array
    data = np.frombuffer(raw_data, dtype=TTY_DTYPE).reshape(rows, cols)

    # terminal size is returned implicitly as the dimensions of the data array
    return (cursor_x, cursor_y), data

# TODO
def valid_vcsa(vcsa):
    """Check that the vcsa device and associated terminal seem sane"""
    vcsa_kernel_major = 7
    tty_kernel_major = 4
    vcsa_range = range(128, 191)
    tty_range = range(1, 63)

    tty = PaperTTY.ttydev(vcsa)
    vs = os.stat(vcsa)
    ts = os.stat(tty)

    vcsa_major, vcsa_minor = os.major(vs.st_rdev), os.minor(vs.st_rdev)
    tty_major, tty_minor = os.major(ts.st_rdev), os.minor(ts.st_rdev)
    if not (vcsa_major == vcsa_kernel_major and vcsa_minor in vcsa_range):
        print("Not a valid vcsa device node: {} ({}/{})".format(vcsa, vcsa_major, vcsa_minor))
        return False
    read_vcsa = os.access(vcsa, os.R_OK)
    write_tty = os.access(tty, os.W_OK)
    if not read_vcsa:
        print("No read access to {} - maybe run with sudo?".format(vcsa))
        return False
    if not (tty_major == tty_kernel_major and tty_minor in tty_range):
        print("Not a valid TTY device node: {}".format(vcsa))
    if not write_tty:
        print("No write access to {} so cannot set terminal size, maybe run with sudo?".format(tty))
    return True
