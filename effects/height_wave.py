from ..dome import classify_segments, draw_dome_groups, DOME_TOP, DOME_BOTTOM

NAME = "Height Wave"
VALUE = "height_wave"

_BAND_Y = (DOME_TOP + DOME_BOTTOM) / 2  # a mid-height band for the preview
_HALF = 14  # half the band height, in screen units


def _color(x1, y1, x2, y2):
    # A bright horizontal band at one height; the wave sweeps it up/down live.
    my = (y1 + y2) / 2
    return (0.2, 1.0, 0.4) if abs(my - _BAND_Y) <= _HALF else (0.0, 0.1, 0.05)


_GROUPS = classify_segments(_color)


def draw(ctx):
    draw_dome_groups(ctx, _GROUPS)
