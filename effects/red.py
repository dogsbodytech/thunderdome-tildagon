from ..dome import draw_dome

NAME = "Red"
VALUE = "red"


def draw(ctx):
    draw_dome(ctx, lambda x1, y1, x2, y2: (1.0, 0.15, 0.15))
