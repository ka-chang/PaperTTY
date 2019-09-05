#!/usr/bin/env python3

from sys import path
path += ['../papertty/']

from papertty import Controller

def main():
    print('Initializing...')
    display = Controller(vcom=-2.06)
    print('Running...')
    display.run()

if __name__ == '__main__':
    main()
