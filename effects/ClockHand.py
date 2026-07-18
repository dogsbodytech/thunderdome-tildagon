import math

from ..dome import classify_segments, draw_dome_groups

NAME = "Clock Hand"
VALUE = "ClockHand"

_ANGLE = math.radians(-60)  # a fixed hand angle for the preview (y grows down)
_HALF = math.radians(24)    # half-width of the highlighted wedge
_TAU = 2 * math.pi


def _color(x1, y1, x2, y2):
    # Struts within a wedge around the hand angle glow; the rest stay dim.
    a = math.atan2((y1 + y2) / 2, (x1 + x2) / 2)
    d = abs(((a - _ANGLE + math.pi) % _TAU) - math.pi)
    return (1.0, 1.0, 1.0) if d <= _HALF else (0.14, 0.14, 0.2)


_GROUPS = classify_segments(_color)


def draw(ctx):
    draw_dome_groups(ctx, _GROUPS)
