
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Written by Greg Meyer (2019) based off code by Jouko Strömmer (2018)
# Copyright and related rights waived via CC0
# https://creativecommons.org/publicdomain/zero/1.0/legalcode

import cProfile, io, pstats

from time import sleep, perf_counter
from IT8951 import EPD, AutoEPDDisplay, constants

from render import Terminal
from vcsa import auto_resize_tty, read_vcsa
from pipe_driver import PipeDisplay

TTYN = 1
INV_FRAME_RATE = 0.1

def main(profile=False):

    epd = EPD(vcom=-2.06)
    term_display = AutoEPDDisplay(epd)
    remote_display = PipeDisplay(epd)

    print('Initializing...')
    term_display.clear()

    term = Terminal((term_display.width, term_display.height), frame_buf=term_display.frame_buf)

    auto_resize_tty(TTYN, term.char_dims, (term_display.width, term_display.height))

    print('Running...')

    def update_callback(need_gray):
        '''
        This function gets called whenever a character gets updated
        by term, in order to get quick updates on the screen
        '''
        if need_gray:
            term_display.write_partial(constants.DisplayModes.GL16)
        else:
            term_display.write_partial(constants.DisplayModes.DU)

    if profile:
        pr = cProfile.Profile()

    need_update = False

    try:
        while True:

            # if another process has decided to take the display, do that
            if remote_display.active:
                remote_display.run()
                term_display.write_full(constants.DisplayModes.GC16)  # get our terminal back

            loop_start = perf_counter()

            if profile:
                pr.enable()

            cursor_pos, data = read_vcsa(TTYN)
            changed = term.update(cursor_pos, data, callback=update_callback)

            if profile:
                pr.disable()

            if changed:
                last_change = perf_counter()
                need_update = True
            elif need_update and perf_counter() - last_change > 10:
                # if it's been long time, clear out the ghosting
                term_display.write_full(constants.DisplayModes.GC16)
                need_update = False

            # TODO: it would be cool to trigger events off of changes
            # rather than just polling this file all the time. not sure
            # if there's a good way to do that

            # sleep for less time if the update took a while
            sleep_time = INV_FRAME_RATE - (perf_counter() - loop_start)
            if sleep_time > 0:
                sleep(sleep_time)

    except KeyboardInterrupt:
        print('Exiting...')

        if profile:
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats()
            print(s.getvalue())

if __name__ == '__main__':
    main()
