
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from .vcsa import TTY_DTYPE

# mapping 3-bit colors (from VGA mode text) to
# e-paper display colors
FG_COLOR_MAP = [0xFF]  # we want black to map to real white
for x in range(1, 8):
    # invert colors (since we want black-on-white) and convert to grayscale
    FG_COLOR_MAP.append(0x70^(x<<4))

# make all the background shades lighter, for contrast
BG_COLOR_MAP = [0xFF]
for x in range(1, 7):
    BG_COLOR_MAP.append(0xB0^(x<<3)&0xF0)
BG_COLOR_MAP.append(0x00)  # white should map to real black

class Terminal:
    '''
    A class that renders an image of the given terminal data.
    '''

    def __init__(self, display_dims, frame_buf=None, font=None, bold_font=None, line_spacing=1):

        self.cursor_pos = None

        # TODO: maybe should handle non-truetype fonts here
        if font is None:
            font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 20)
        if bold_font is None:
            bold_font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", 20)

        self.font = font
        self.bold_font = bold_font
        self.line_spacing = line_spacing
        self.char_dims = self.get_char_dims(self.line_spacing)

        # use 8 bits per pixel for display that can handle grayscale
        # may want to change this later and use bitmap font
        # 0xFF = white
        if frame_buf is None:
            self.display = Image.new('L', display_dims, 0xFF)
        else:
            self.display = frame_buf

        self.data = None

    def _draw_cursor(self, position, tty_data, draw, remove=False):
        cursor_x = position[0]*self.char_dims[0]
        cursor_y = (position[1]+1)*self.char_dims[1]  # the +1 is so the cursor is at the bottom of the line

        attr = tty_data[position[1], position[0]]['attr']  # the text attributes at this position
        bg_color = BG_COLOR_MAP[(attr & 0b01110000) >> 4]

        if remove:
            cursor_color = bg_color   # draw over it in the same color as the background
        else:
            cursor_color = 0xFF if bg_color == 0x00 else 0x00

        draw.line((cursor_x, cursor_y, cursor_x+self.char_dims[0], cursor_y), fill=cursor_color)

        # whether we drew any gray
        return bg_color not in (0x00, 0xFF)

    def update(self, cursor_pos, data, callback=lambda *args, **kwargs: None):
        '''
        Update the image of our terminal.

        Parameters
        ----------

        cursor_pos : (int, int)
            The text coordinates of the cursor

        data : np.ndarray
            A numpy array as returned by vcsa.get_vcsa

        callback : function
            A function that will be called for intermediate updates

        Returns
        -------

        int
            The number of characters changed
'''

        if self.data is None:
            # this is the data that would yield an all-white screen, so since
            # we've set our display to all white we'll use that as the starting point
            self.data = np.full(data.shape, np.array((0x20, 0x07), dtype=data.dtype), dtype=TTY_DTYPE)

        # if nothing has changed, we don't need to do anything
        if cursor_pos == self.cursor_pos and np.array_equal(self.data, data):
            return 0

        draw = ImageDraw.Draw(self.display)

        # all of the places where the character or attribute has changed
        diffs = np.nonzero(data != self.data)

        # set to true when we make a change that requires a grayscale update (not b&w)
        gray_changes = False

        # remove old cursor
        if self.cursor_pos is not None:
            gray_changes = self._draw_cursor(self.cursor_pos, data, draw, remove=True) or gray_changes
            # only call callback if we won't already be updating this spot below
            # (e.g. old cursor was on a different line than all text changes)
            if diffs[0].size and self.cursor_pos[1] != diffs[0][0]:
                callback(gray_changes)
                gray_changes = False

        # iterate through the places where the data arrays differ, changing the character there
        prev_y = diffs[0][0] if diffs[0].size else None
        for y,x in zip(*diffs):

            # call callback if there was a gap between the rows
            # main idea is to avoid updating half the screen because the text in two distant
            # areas changed.
            if y > prev_y + 5:
                callback(gray_changes)
                gray_changes = False

            prev_y = y

            pos = (x*self.char_dims[0], y*self.char_dims[1])
            old_attr = self.data[y,x]['attr']
            new_attr = data[y,x]['attr']

            # need to write background color box to remove any character that is already there
            # or if background color has changed
            bg_color = BG_COLOR_MAP[(new_attr&0b01110000) >> 4]
            if (old_attr ^ new_attr) & 0b01110000 or chr(self.data[y,x]['char']) != ' ':
                box = pos[0], pos[1], pos[0]+self.char_dims[0], pos[1]+self.char_dims[1]
                draw.rectangle(box, fill=bg_color)

            # whether to use "high-intensity" (bold)
            font = self.bold_font if new_attr & 0x08 else self.font

            # foreground color
            fg_color = FG_COLOR_MAP[new_attr & 0x07]

            # we are basically ignoring the encoding, by hoping it's ASCII (calling chr())
            # we expect to usually be UTF-8, which is ASCII most of the time
            # I'm not sure how /dev/vcsa handles encoding+attributes anyway
            draw.text(pos, chr(data[y,x]['char']), font=font, fill=fg_color)

            # whether we have drawn any gray
            gray_changes = gray_changes or bg_color not in (0x00, 0xFF)
            gray_changes = gray_changes or fg_color not in (0x00, 0xFF)

        # if the last text that happened was not on the same row as the cursor we're about to update, then
        # run the callback
        if prev_y != cursor_pos[1]:
            callback(gray_changes)
            gray_changes = False

        # place cursor
        gray_changes = self._draw_cursor(cursor_pos, data, draw) or gray_changes

        callback(gray_changes)

        self.cursor_pos = cursor_pos
        self.data = data

        return diffs[0].size + 1 # +1 for cursor movement

    def get_char_dims(self, line_spacing):
        '''
        Get the dimensions of a single character when rendered in our font.
        The vertical dimension is multiplied by line_spacing.
        '''
        # this is hacky, but unfortunately there doesn't seem to be a
        # better way to do this that works for all possible fonts
        width, height = self.font.getsize('g')
        return (width, int(height*line_spacing))
