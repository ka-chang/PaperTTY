
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Written by Greg Meyer (2019) based off code by Jouko Strömmer (2018)
# Copyright and related rights waived via CC0
# https://creativecommons.org/publicdomain/zero/1.0/legalcode

import cProfile, io, pstats, signal

from time import sleep, perf_counter
from IT8951 import EPD, AutoEPDDisplay, constants

from render import Terminal
from vcsa import auto_resize_tty, read_vcsa
from pipe_driver import PipeDisplay

from PIL import Image

class Runner:

    def __init__(self, profile=False, ttyn=1, frame_rate=10):

        self.ttyn = ttyn
        self.inv_frame_rate = 1/frame_rate
        self.profile = profile
        if self.profile:
            self.pr = cProfile.Profile()

        epd = EPD(vcom=-2.06)
        self.term_display = AutoEPDDisplay(epd)
        self.remote_display = PipeDisplay(epd)

        print('Initializing...')
        self.term_display.clear()

        self.term = Terminal((self.term_display.width, self.term_display.height), frame_buf=self.term_display.frame_buf)

        auto_resize_tty(self.ttyn, self.term.char_dims, (self.term_display.width, self.term_display.height))

        # handle both of these the same way
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        signal.signal(signal.SIGINT, self.sigterm_handler)

    def on_exit(self):
        '''
        Some things to do when we exit cleanly. We don't want to do them when we are not exiting cleanly,
        so they don't go in __del__
        '''

        print('Exiting...')

        if self.profile:
            s = io.StringIO()
            ps = pstats.Stats(self.pr, stream=s).sort_stats('cumulative')
            ps.print_stats()
            print(s.getvalue())

        self.display_penguin()

    def update_callback(self, need_gray):
        '''
        This function gets called whenever a character gets updated
        by term, in order to get quick updates on the screen
        '''
        if need_gray:
            self.term_display.write_partial(constants.DisplayModes.GL16)
        else:
            self.term_display.write_partial(constants.DisplayModes.DU)

    def update(self):
        '''
        Update the contents of the display
        '''

        # if another process has decided to take the display, do that
        if self.remote_display.active:
            self.remote_display.run()
            self.term_display.write_full(constants.DisplayModes.GC16)  # get our terminal back

        # currently just want to profile the updates done here
        if self.profile:
            self.pr.enable()

        cursor_pos, data = read_vcsa(self.ttyn)
        changed = self.term.update(cursor_pos, data, callback=self.update_callback)

        if self.profile:
            self.pr.disable()

        if changed:
            self.last_change = perf_counter()
            self.need_update = True
        elif self.need_update and perf_counter() - self.last_change > 10:
            # if it's been long time, clear out the ghosting
            self.term_display.write_full(constants.DisplayModes.GC16)
            self.need_update = False

    def run(self):
        print('Running...')
        self.running = True
        self.need_update = False

        # TODO: it would be cool to trigger events off of changes
        # rather than just polling this file all the time. not sure
        # if there's a good way to do that

        while self.running:

            loop_start = perf_counter()

            self.update()

            # sleep for less time if the update took a while
            sleep_time = self.inv_frame_rate - (perf_counter() - loop_start)
            if sleep_time > 0:
                sleep(sleep_time)

        self.on_exit()

    def sigterm_handler(self, sig=None, frame=None):
        self.running = False

    def display_penguin(self):
        img_path = 'pics/sleeping_penguin.png'

        # clear image to white
        img_bounds = (0, 0, self.term_display.width, self.term_display.height)
        self.term_display.frame_buf.paste(0xFF, box=img_bounds)

        img = Image.open(img_path)

        dims = self.term_display.frame_buf.size

        # half of the display size
        img.thumbnail([x//2 for x in dims])

        paste_coords = (  # put it at the bottom of the display, centered
            (dims[0] - img.size[0])//2,
            dims[1] - img.size[1],
        )
        self.term_display.frame_buf.paste(img, paste_coords)

        self.term_display.write_full(constants.DisplayModes.GC16)

def main():
    r = Runner()
    r.run()

if __name__ == '__main__':
    main()
