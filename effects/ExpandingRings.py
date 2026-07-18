import math

from ..dome import classify_segments, draw_dome_groups

NAME = "Expanding Rings"
VALUE = "ExpandingRings"

_RING_MM = 18  # radial spacing between rings, in screen units


def _color(x1, y1, x2, y2):
    # Concentric shells: alternate bright/dim by distance from centre.
    r = math.sqrt(((x1 + x2) / 2) ** 2 + ((y1 + y2) / 2) ** 2)
    return (0.1, 0.5, 1.0) if int(r / _RING_MM) % 2 == 0 else (0.0, 0.05, 0.15)


_GROUPS = classify_segments(_color)


def draw(ctx):
    draw_dome_groups(ctx, _GROUPS)
