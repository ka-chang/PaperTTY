#!/usr/bin/env papertty

import argparse

from sys import path
path += ['../papertty/']

from papertty import Runner

def parse_args():
    p = argparse.ArgumentParser(description='Run a PaperTTY terminal.')
    p.add_argument('--flip', action='store_true', help='Rotate the display by 180 degrees')
    return p.parse_args()

def main():
    args = parse_args()
    r = Runner(flip=args.flip)
    r.run()

if __name__ == '__main__':
    main()
