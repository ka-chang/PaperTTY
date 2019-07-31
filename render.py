
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from vcsa import TTY_DTYPE

# mapping 3-bit colors (from VGA mode text) to
# e-paper display colors
COLOR_MAP = [0xFF]  # we want black to map to real white
for x in range(1, 8):
    # invert colors (since we want black-on-white) and convert to grayscale
    COLOR_MAP.append((0x70^(x<<4),))

class Terminal:
    '''
    A class that renders an image of the given terminal data.
    '''

    def __init__(self, display_dims, font=None, bold_font=None, line_spacing=1):

        self.cursor_pos = None

        # TODO: maybe should handle non-truetype fonts here
        if font is None:
            font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 24)
        if bold_font is None:
            bold_font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", 24)

        self.font = font
        self.bold_font = bold_font
        self.line_spacing = line_spacing
        self.char_dims = self.get_char_dims(self.line_spacing)

        # use 8 bits per pixel for display that can handle grayscale
        # may want to change this later and use bitmap font
        # 0xFF = white
        self.display = Image.new('L', display_dims, 0xFF)

        self.data = None

    def update(self, cursor_pos, data):
        '''
        Update the image of our terminal.

        Parameters
        ----------

        cursor_pos : (int, int)
            The text coordinates of the cursor

        data : np.ndarray
            A numpy array as returned by vcsa.get_vcsa

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

        # remove old cursor
        if self.cursor_pos is not None:
            cursor_x = self.cursor_pos[0]*self.char_dims[0]
            cursor_y = (self.cursor_pos[1] + 1)*self.char_dims[1]  # the +1 is so the cursor is at the bottom of the line
            bg_color = COLOR_MAP[(data[self.cursor_pos[1], self.cursor_pos[0]]['attr'] & 0b01110000) >> 4]
            draw.line((cursor_x, cursor_y, cursor_x+self.char_dims[0], cursor_y), fill=bg_color)

        # iterate through the places where the data arrays differ, changing the character there
        # TODO: allow to call display update after each one, so we only change the spots on the
        # screen where characters have changed!
        diffs = np.nonzero(data != self.data)
        for y,x in zip(*diffs):
            pos = (x*self.char_dims[0], y*self.char_dims[1])

            # TODO: cache the rendered characters?

            old_attr = self.data[y,x]['attr']
            new_attr = data[y,x]['attr']

            # need to write background color box to remove any character that is already there
            # or if background color has changed
            if (old_attr ^ new_attr) & 0b01110000 or chr(self.data[y,x]['char']) != ' ':
                box = pos[0], pos[1], pos[0]+self.char_dims[0], pos[1]+self.char_dims[1]
                bg_color = COLOR_MAP[(new_attr&0b01110000) >> 4]
                draw.rectangle(box, fill=bg_color)

            # whether to use "high-intensity"
            font = self.bold_font if new_attr & 0x08 else self.font

            # foreground color
            color = COLOR_MAP[new_attr & 0x07]

            # we are basically ignoring the encoding, by hoping it's ASCII (calling chr())
            # we expect to usually be UTF-8, which is ASCII most of the time
            # I'm not sure how /dev/vcsa handles encoding anyway
            draw.text(pos, chr(data[y,x]['char']), font=font, fill=color)

        # place cursor
        cursor_x = cursor_pos[0]*self.char_dims[0]
        cursor_y = (cursor_pos[1] + 1)*self.char_dims[1]  # the +1 is so the cursor is at the bottom of the line
        bg_color = COLOR_MAP[(data[cursor_pos[1], cursor_pos[0]]['attr'] & 0b01110000) >> 4]
        cursor_color = 0x00 if bg_color == 0xFF else 0xFF # dark background should have a white cursor
        draw.line((cursor_x, cursor_y, cursor_x+self.char_dims[0], cursor_y), fill=cursor_color)

        self.cursor_pos = cursor_pos
        self.data = data

        return diffs[0].size

    def get_char_dims(self, line_spacing):
        '''
        Get the dimensions of a single character when rendered in our font.
        The vertical dimension is multiplied by line_spacing.
        '''
        # this is hacky, but unfortunately there doesn't seem to be a
        # better way to do this that works for all possible fonts
        width, height = self.font.getsize('g')
        return (width, int(height*line_spacing))
