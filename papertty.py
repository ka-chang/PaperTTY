
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Written by Greg Meyer (2019) based off code by Jouko Strömmer (2018)
# Copyright and related rights waived via CC0
# https://creativecommons.org/publicdomain/zero/1.0/legalcode

import cProfile, io, pstats

from time import sleep, perf_counter
from IT8951 import EPD, constants

from render import Terminal
from vcsa import auto_resize_tty, read_vcsa

TTYN = 1
INV_FRAME_RATE = 0.1

def main():
    epd = EPD(vcom=-2.06)

    print('Initializing...')
    epd.clear()

    term = Terminal((epd.width, epd.height), frame_buf=epd.frame_buf)

    auto_resize_tty(TTYN, term.char_dims, (epd.width, epd.height))

    print('Running...')

    def update_callback():
        '''
        This function gets called whenever a character gets updated
        by term, in order to get quick updates on the screen
        '''
        epd.write_partial(constants.DisplayModes.DU)

    pr = cProfile.Profile()

    need_GL_update = False
    need_GC_update = False

    try:
        while True:

            loop_start = perf_counter()

            pr.enable()
            cursor_pos, data = read_vcsa(TTYN)
            changed = term.update(cursor_pos, data, callback=update_callback)
            pr.disable()

            if changed:
                last_change = perf_counter()
                need_GL_update = True
                need_GC_update = True
            elif need_GL_update and perf_counter() - last_change > 0.5:
                # if it's been a moment since any changes, update with grayscale
                epd.write_partial(constants.DisplayModes.GL16)
                need_GL_update = False
            elif need_GC_update and perf_counter() - last_change > 10:
                # if it's been long time, clear out the ghosting
                # TODO: don't need to write data again for this call
                epd.write_full(constants.DisplayModes.GC16)
                need_GC_update = False

            # TODO: it would be cool to trigger events off of changes
            # rather than just polling this file all the time. not sure
            # if there's a good way to do that

            # sleep for less time if the update took a while
            sleep_time = INV_FRAME_RATE - (perf_counter() - loop_start)
            if sleep_time > 0:
                sleep(sleep_time)

    except KeyboardInterrupt:
        print('Exiting...')
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        print(s.getvalue())

if __name__ == '__main__':
    main()
