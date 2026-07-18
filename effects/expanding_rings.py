import math

from ..dome import draw_dome

NAME = "Expanding Rings"
VALUE = "expanding_rings"

_RING_MM = 18  # radial spacing between rings, in screen units


def draw(ctx):
    # Concentric shells: alternate bright/dim by distance from centre.
    def color(x1, y1, x2, y2):
        r = math.sqrt(((x1 + x2) / 2) ** 2 + ((y1 + y2) / 2) ** 2)
        return (0.1, 0.5, 1.0) if int(r / _RING_MM) % 2 == 0 else (0.0, 0.05, 0.15)

    draw_dome(ctx, color)
