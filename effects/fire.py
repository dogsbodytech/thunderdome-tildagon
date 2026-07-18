from ..dome import draw_dome, DOME_TOP, DOME_BOTTOM

NAME = "Fire"
VALUE = "fire"

_SPAN = DOME_BOTTOM - DOME_TOP


def draw(ctx):
    # Yellow at the top, red at the bottom, blended by segment height.
    def color(x1, y1, x2, y2):
        t = ((y1 + y2) / 2 - DOME_TOP) / _SPAN  # 0.0 top .. 1.0 bottom
        t = 0.0 if t < 0 else 1.0 if t > 1 else t
        return (1.0, 1.0 - t, 0.0)

    draw_dome(ctx, color)
