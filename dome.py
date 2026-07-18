# Shared dome wireframe geometry + drawing, used by the effect previews.

# Vertical extent of the wireframe (min/max y across DOME_SEGMENTS), for
# effects that colour by height (e.g. a bottom-to-top gradient).
DOME_TOP = -67
DOME_BOTTOM = 54

# 2V geodesic hemisphere wireframe, precomputed from dome/Assembly.drawio.svg
# geometry (2V = 2 strut classes; source 3V had a third). Screen-space coords
# centred on (0, 0), 240x240.
DOME_SEGMENTS = (
    (
        (-25, -46, 26, -40), (-69, -31, -40, -61), (15, -37, 26, 10),
        (26, -40, 65, -37), (26, -40, 56, 1), (-40, -43, 0, -65),
        (-69, 0, -40, -43), (-81, -23, -69, -31), (0, -4, 26, -40),
        (-69, -31, -25, -46), (26, 10, 56, 49), (50, -52, 85, -15),
        (0, -65, 15, -37), (-90, 16, -69, -31), (-90, 34, -69, 0),
        (-81, -23, -69, 0), (-25, 1, 26, 10), (65, -8, 85, -15),
        (0, -65, 15, -67), (26, 10, 65, -8), (65, -37, 85, -15),
        (85, -15, 90, 16), (15, -67, 26, -40), (0, 54, 26, 10),
        (0, -65, 50, -52), (-69, -31, -56, 1), (-69, 0, -25, 1),
        (85, -15, 90, 34), (-69, 0, -56, 49), (-40, -61, 0, -65),
    ),
    (
        (-25, -46, 0, -4), (50, -52, 65, -8), (-90, 34, -56, 49),
        (-25, 1, 0, 54), (-56, 1, 0, -4), (-90, 34, -81, -23),
        (-40, -43, -25, 1), (-25, 1, 15, -37), (-56, 1, -25, -46),
        (15, -37, 50, -52), (15, -37, 65, -8), (56, 49, 65, -8),
        (15, -67, 50, -52), (-40, -43, 15, -37), (0, -4, 56, 1),
        (-90, 16, -81, -23), (50, -52, 65, -37), (-40, -61, 15, -67),
        (0, 54, 56, 49), (-81, -23, -40, -43), (-25, -46, 15, -67),
        (90, 34, 90, 16), (-90, 16, -56, 1), (56, 1, 90, 16),
        (-90, 34, -90, 16), (65, -37, 90, 16), (56, 1, 65, -37),
        (15, -67, 65, -37), (-40, -61, -25, -46), (56, 49, 90, 34),
        (-56, 49, -25, 1), (-56, 49, 0, 54), (65, -8, 90, 34),
        (-40, -43, -40, -61), (-81, -23, -40, -61),
    ),
)


def classify_segments(color_fn):
    """Bucket the wireframe segments by colour, calling
    color_fn(x1, y1, x2, y2) -> (r, g, b) once per segment. Returns a list of
    (color, segments) groups, dimmest first so bright struts stroke on top.
    Static previews should call this once at import and hand the result to
    draw_dome_groups(); only recompute when the colours actually change."""
    groups = {}
    for segs in DOME_SEGMENTS:
        for seg in segs:
            groups.setdefault(color_fn(*seg), []).append(seg)
    return sorted(groups.items(), key=lambda g: sum(g[0]))


def draw_dome_groups(ctx, groups):
    """Stroke pre-classified segment groups, one batched path per colour."""
    ctx.line_width = 2
    for color, segs in groups:
        ctx.rgb(*color).begin_path()
        for x1, y1, x2, y2 in segs:
            ctx.move_to(x1, y1).line_to(x2, y2)
        ctx.stroke()


def draw_dome(ctx, color_fn):
    """Stroke the dome wireframe, colouring each segment via
    color_fn(x1, y1, x2, y2) -> (r, g, b) with floats 0.0-1.0. Classifies
    every frame — fine for animated colours; static previews should
    precompute with classify_segments() instead."""
    draw_dome_groups(ctx, classify_segments(color_fn))
