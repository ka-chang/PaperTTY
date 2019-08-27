
from sys import path
path += ['../papertty/']

from papertty import Runner

def main():
    r = Runner()
    r.run()

if __name__ == '__main__':
    main()
