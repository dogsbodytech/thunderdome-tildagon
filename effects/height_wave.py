from ..dome import draw_dome, DOME_TOP, DOME_BOTTOM

NAME = "Height Wave"
VALUE = "height_wave"

_BAND_Y = (DOME_TOP + DOME_BOTTOM) / 2  # a mid-height band for the preview
_HALF = 14  # half the band height, in screen units


def draw(ctx):
    # A bright horizontal band at one height; the wave sweeps it up/down live.
    def color(x1, y1, x2, y2):
        my = (y1 + y2) / 2
        return (0.2, 1.0, 0.4) if abs(my - _BAND_Y) <= _HALF else (0.0, 0.1, 0.05)

    draw_dome(ctx, color)
