#!/usr/bin/env python3

from time import sleep
from papertty.controller import Controller

def main():
    print('Initializing...')
    display = Controller(vcom=-2.06)

    print('Running...')
    while True:  # events are handled by signal
        if display.check_active():
            display.run()
        sleep(0.5)

if __name__ == '__main__':
    main()
