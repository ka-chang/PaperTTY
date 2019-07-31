
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Written by Greg Meyer (2019) based off code by Jouko Strömmer (2018)
# Copyright and related rights waived via CC0
# https://creativecommons.org/publicdomain/zero/1.0/legalcode

import cProfile, io, pstats

from time import sleep
from IT8951 import EPD, constants

from render import Terminal
from vcsa import auto_resize_tty, read_vcsa

TTYN = 1

def main():
    epd = EPD(vcom=-2.06)

    print('Initializing...')
    epd.clear()

    term = Terminal((epd.width, epd.height))

    auto_resize_tty(TTYN, term.char_dims, (epd.width, epd.height))

    print('Running...')

    pr = cProfile.Profile()

    try:
        while True:

            pr.enable()
            cursor_pos, data = read_vcsa(TTYN)
            changed = term.update(cursor_pos, data)
            if changed:
                epd.frame_buf = term.display

                # TODO: need more black pixels for DU
                if changed < 5:
                    epd.write_partial(constants.DisplayModes.DU)
                else:
                    epd.write_partial(constants.DisplayModes.GL16)

            pr.disable()

            # TODO: it would be cool to trigger events off of changes
            # rather than just polling this file all the time. not sure
            # if there's a good way to do that
            sleep(0.1)

    except KeyboardInterrupt:
        print('Exiting...')
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        print(s.getvalue())


if __name__ == '__main__':
    main()
