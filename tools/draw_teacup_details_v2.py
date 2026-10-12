"""Draw the Teacup Cleric v2's line art (Pillow): the detail atlas her model's
texture is built from.

python tools/draw_teacup_details_v2.py <layout.json>
    -> assets/models/teacup/source/v2/teacup_details_v2.png
python tools/draw_teacup_details_v2.py --motifs <out.png>
    -> a sheet of the motifs alone, large and at battle scale, for review

The build (tools/build_teacup_cleric_v2_3d.py) runs this itself: it unrolls every
decorated surface flat (each cloth grid relaxed to keep its true lengths, the
cup's wall unrolled like a cone, flat parts projected), packs those regions into
the 2048 px atlas at one density (atlas px per metre, the same across and down,
so nothing is stretched), and writes the layout JSON this script reads:

  {"size": 2048, "palette_px": 512, "density": px per metre,
   "regions": {name: {"box": [x0, y0, x1, y1], "density": px/m,
                      "grid": rows of columns of [x, y] px (cloth and the cup),
                      "outline": [[x, y], ...] px (flat parts), ...}}}

A grid's rows run across the surface and its columns down it (down the cloth
toward the hem, up the cup's wall from its rim), so the art finds its hems, front
edges and seams from the grid's first and last rows and columns, and lays motifs
upright along the columns. The palette swatches fill the top-left corner
(toy3d.atlas_size) and are added by the build, not here.

Everything is drawn as smooth vector shapes (cubic Bezier outlines) at 4x and
scaled down, so the edges stay clean; colours are the model's palette. No shading
is drawn: folds are real geometry and the scene's light shades them. Each motif is
a dark outline, a mid fill and one small flat highlight shape, sized in metres so
it reads at the 128 px battle scale (1 sprite px = 7.8 mm).
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "models", "teacup", "source", "v2",
                   "teacup_details_v2.png")
K = 4                                    # supersampling

OUTLINE = (5, 4, 2)
BLUE_DARK, BLUE_MID, BLUE, BLUE_LIGHT = (23, 50, 111), (29, 71, 152), (36, 89, 180), (57, 112, 203)
BROWN_DARK, BROWN, TAN = (113, 54, 22), (165, 82, 37), (201, 137, 89)
AMBER, GOLD = (242, 154, 46), (225, 169, 58)
CREAM_SHADE, CREAM_WARM, CREAM, IVORY = (232, 195, 159), (228, 200, 155), (229, 211, 182), (235, 224, 196)
# (gold and the three lightest creams 8% under the sprite's, as in the build's PALETTE)

# motif sizes, metres tall (a sprite px is 7.8 mm, so 5 cm is about 6 px at battle scale)
FLEUR_CUP = 0.056
FLEUR_ROBE = 0.070
FLEUR_COAT = 0.064
FLEUR_MANTLE = 0.040
FLEUR_SLEEVE = 0.050
FLEUR_DRAPE = 0.085
FLEUR_TABARD = 0.075
FLEUR_BOOK = 0.070
CROSS_TABARD = 0.050
TRIM = 0.012                             # gold hem and edge bands, metres wide


# -- curves ---------------------------------------------------------------------------

def bezier(p0, p1, p2, p3, n=16):
    """Points along a cubic Bezier from p0 to p3 (p0 left out, so segments chain)."""
    out = []
    for k in range(1, n + 1):
        t = k / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def path(start, *segments, n=16):
    """A closed outline from a start point and cubic segments (c1, c2, end)."""
    pts, p = [start], start
    for c1, c2, end in segments:
        pts += bezier(p, c1, c2, end, n)
        p = end
    return pts


def mirror(half):
    """A symmetric outline from its right half (x >= 0), drawn top to bottom."""
    return half + [(-x, y) for x, y in reversed(half)]


def offset(pts, d):
    """Grow (d > 0) or shrink a closed outline by d along its vertex normals."""
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    sgn = 1 if area > 0 else -1
    out = []
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[(i + 1) % n]
        tx, ty = cx - ax, cy - ay
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = ty / ln * sgn, -tx / ln * sgn       # outward
        out.append((bx + nx * d, by + ny * d))
    return out


# -- motifs, in unit space: y down, about -1 (top) .. 1 (foot) ----------------------------

def fleur_shapes():
    """The concept's fleur-de-lis: a tall pointed centre petal, side petals that rise
    and curl over outward and down to a hooked tip, a band across, and a short
    flared foot below it. Returns (silhouette parts, highlight shapes), each a list
    of closed outlines, normalised to fit -1..1 tall, centred."""
    centre = mirror(path((0.0, -1.0),
                         ((0.09, -0.86), (0.24, -0.64), (0.23, -0.42)),
                         ((0.22, -0.28), (0.14, -0.18), (0.11, -0.08))))
    side = path((0.12, -0.08),
                ((0.12, -0.42), (0.28, -0.70), (0.52, -0.72)),       # inner edge, up and over
                ((0.74, -0.74), (0.88, -0.58), (0.84, -0.40)),       # over the top and down
                ((0.81, -0.26), (0.70, -0.20), (0.62, -0.25)),       # curling in underneath
                ((0.56, -0.29), (0.57, -0.37), (0.63, -0.38)),       # the hooked tip
                ((0.68, -0.39), (0.66, -0.52), (0.54, -0.52)),       # back up inside the curl
                ((0.40, -0.52), (0.33, -0.36), (0.36, -0.08)))       # down to the band
    band = path((-0.42, -0.14),
                ((-0.14, -0.17), (0.14, -0.17), (0.42, -0.14)),
                ((0.50, -0.12), (0.50, 0.0), (0.42, 0.02)),
                ((0.14, -0.01), (-0.14, -0.01), (-0.42, 0.02)),
                ((-0.50, 0.0), (-0.50, -0.12), (-0.42, -0.14)))
    foot = mirror(path((0.0, -0.02),
                       ((0.06, -0.02), (0.10, -0.01), (0.12, 0.0)),
                       ((0.18, 0.12), (0.30, 0.20), (0.40, 0.22)),        # flaring out
                       ((0.46, 0.24), (0.46, 0.32), (0.40, 0.33)),        # its rounded end
                       ((0.28, 0.34), (0.16, 0.28), (0.09, 0.24)),
                       ((0.07, 0.32), (0.04, 0.40), (0.0, 0.46))))        # down to the point
    side_l = [(-x, y) for x, y in reversed(side)]
    hi_centre = mirror(path((0.0, -0.82), ((0.04, -0.70), (0.08, -0.56), (0.07, -0.44)),
                            ((0.06, -0.38), (0.03, -0.36), (0.0, -0.36))))
    hi_side = path((0.40, -0.56), ((0.50, -0.61), (0.68, -0.60), (0.75, -0.48)),
                   ((0.68, -0.53), (0.54, -0.56), (0.40, -0.56)))
    hi_side_l = [(-x, y) for x, y in reversed(hi_side)]
    parts, hi = [centre, side, side_l, band, foot], [hi_centre, hi_side, hi_side_l]
    ys = [y for p in parts for _, y in p]
    mid, half = (min(ys) + max(ys)) / 2, (max(ys) - min(ys)) / 2
    sx = 0.88 / half                                   # a touch narrower than tall
    norm = [[(x * sx, (y - mid) / half) for x, y in p] for p in parts]
    return norm, [[(x * sx, (y - mid) / half) for x, y in p] for p in hi]


def cross_shapes():
    """A cross with flared, rounded arm ends (the tabard's and the pages')."""
    def arm(rot):
        half = path((0.0, -1.0),
                    ((0.12, -1.0), (0.24, -0.98), (0.24, -0.90)),
                    ((0.20, -0.64), (0.12, -0.36), (0.12, -0.12)))
        pts = mirror(half)
        c, s = math.cos(rot), math.sin(rot)
        return [(x * c - y * s, x * s + y * c) for x, y in pts]
    hub = [(math.cos(a) * 0.17, math.sin(a) * 0.17) for a in (2 * math.pi * k / 16 for k in range(16))]
    arms = [arm(r) for r in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    # the long lower arm: stretch the bottom one
    arms[2] = [(x, y * 1.35) for x, y in arms[2]]
    hi = [[(x * 0.35, y * 0.55 - 0.05) for x, y in mirror(path((0.0, -0.95), ((0.06, -0.9), (0.08, -0.7),
                                                                              (0.06, -0.3)),
                                                                ((0.05, -0.2), (0.02, -0.2), (0.0, -0.2))))]]
    return arms + [hub], hi


def quatrefoil_shapes():
    """The brooch's quatrefoil: four round lobes round a square, a cross in it."""
    lobes = []
    for k in range(4):
        a = math.pi / 2 * k
        cx, cy = math.cos(a) * 0.48, math.sin(a) * 0.48
        lobes.append([(cx + math.cos(t) * 0.52, cy + math.sin(t) * 0.52)
                      for t in (2 * math.pi * i / 28 for i in range(28))])
    return lobes


def sprig_shapes():
    """A small porcelain sprig: a curved stem, three teardrop leaves and a berry."""
    stem = path((-0.92, 0.30), ((-0.40, 0.18), (0.10, -0.10), (0.78, -0.40)),
                ((0.80, -0.33), (0.79, -0.31), (0.77, -0.30)),
                ((0.10, -0.02), (-0.40, 0.26), (-0.90, 0.38)))
    leaves = []
    for x, y, ang in ((-0.46, 0.22, -2.3), (-0.05, 0.03, 0.9), (0.36, -0.20, -2.1)):
        leaf = path((0.0, 0.0), ((0.26, -0.14), (0.30, -0.50), (0.0, -0.72)),
                    ((-0.30, -0.50), (-0.26, -0.14), (0.0, 0.0)))
        c, s_ = math.cos(ang), math.sin(ang)
        leaves.append([(x + px * c - py * s_, y + px * s_ + py * c) for px, py in leaf])
    berry = [(0.86 + math.cos(t) * 0.13, -0.40 + math.sin(t) * 0.13) for t in (2 * math.pi * i / 16 for i in range(16))]
    return [stem] + leaves + [berry]


def place(shape, cx, cy, size, ux=(1.0, 0.0), uy=(0.0, 1.0)):
    """Unit-space outline -> image px: centred on (cx, cy), size px per unit, its
    x and y axes along ux and uy (unit vectors; uy points down the motif)."""
    return [(cx + (x * ux[0] + y * uy[0]) * size, cy + (x * ux[1] + y * uy[1]) * size) for x, y in shape]


def draw_motif(d, parts, highlights, cx, cy, size, fill, line, light, ux=(1.0, 0.0), uy=(0.0, 1.0),
               line_w=0.075):
    """Dark outline (every part grown by line_w units, drawn first), then the fills."""
    w = max(1, int(round(2 * line_w * size)))
    for p in parts:
        pts = place(p, cx, cy, size, ux, uy)
        d.polygon(pts, fill=line)
        d.line(pts + pts[:2], fill=line, width=w, joint="curve")
        for x, y in pts[::4]:                       # round the stroke's sharp corners
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=line)
    for p in parts:
        d.polygon(place(p, cx, cy, size, ux, uy), fill=fill)
    # (no highlights: painted-on light is left out, the room's light shades the model)


def fleur(d, cx, cy, height, fill=BLUE, line=BLUE_DARK, light=BLUE_LIGHT, ux=(1.0, 0.0), uy=(0.0, 1.0)):
    """A fleur-de-lis height px tall, centred on (cx, cy), upright along -uy."""
    parts, hi = fleur_shapes()
    draw_motif(d, parts, hi, cx, cy, height / 2.0 / 1.1, fill, line, light, ux, uy)


def cross(d, cx, cy, height, fill=IVORY, line=BLUE_DARK, light=CREAM, ux=(1.0, 0.0), uy=(0.0, 1.0)):
    """A cross height px tall centred on (cx, cy), upright along -uy. Its long lower
    arm is balanced by a nudge up the motif's own axis (not the image's y, which
    runs across the cloth in a region packed a quarter turn)."""
    parts, hi = cross_shapes()
    nudge = height * 0.08
    draw_motif(d, parts, hi, cx - uy[0] * nudge, cy - uy[1] * nudge, height / 2.35, fill, line, light, ux, uy,
               line_w=0.09)


def sprig(d, cx, cy, size, angle=0.0, fill=BLUE, line=BLUE_DARK):
    c, s = math.cos(angle), math.sin(angle)
    draw_motif(d, sprig_shapes(), [], cx, cy, size / 2, fill, line, fill, (c, s), (-s, c), line_w=0.05)


# -- grids --------------------------------------------------------------------------------

class Grid:
    """A region's unrolled grid (rows of columns of px points, at K x)."""

    def __init__(self, rows, up=None, stretch=None):
        self.p = [[(x * K, y * K) for x, y in row] for row in rows]
        self.up = up                       # world up at each point, as a unit 2D direction
        self.stretch = stretch             # per cell, how far its unwrap departs from true lengths
        self.rows, self.cols = len(self.p), len(self.p[0])

    def stretch_near(self, u, v, reach=1):
        """The worst stretch of the cells within reach cells of (u, v)."""
        if not self.stretch:
            return 0.0
        i, j = min(int(u * (self.cols - 1)), self.cols - 2), min(int(v * (self.rows - 1)), self.rows - 2)
        return max(self.stretch[jj][ii] for jj in range(max(0, j - reach), min(self.rows - 1, j + reach + 1))
                   for ii in range(max(0, i - reach), min(self.cols - 1, i + reach + 1)))

    def upright(self, u, v):
        """(ux, uy) for a motif standing upright in the world at (u, v): uy runs down
        the motif (against world up), ux across it."""
        x, y = u * (self.cols - 1), v * (self.rows - 1)
        i, j = min(int(x), self.cols - 2), min(int(y), self.rows - 2)
        fx, fy = x - i, y - j
        a, b, c, e = self.up[j][i], self.up[j][i + 1], self.up[j + 1][i + 1], self.up[j + 1][i]
        dx = (1 - fx) * (1 - fy) * a[0] + fx * (1 - fy) * b[0] + fx * fy * c[0] + (1 - fx) * fy * e[0]
        dy = (1 - fx) * (1 - fy) * a[1] + fx * (1 - fy) * b[1] + fx * fy * c[1] + (1 - fx) * fy * e[1]
        ln = math.hypot(dx, dy) or 1.0
        uy = (-dx / ln, -dy / ln)
        return (-uy[1], uy[0]), uy

    def at(self, u, v):
        """Point at fractional (u across 0..1, v down 0..1), bilinear in the grid."""
        x, y = u * (self.cols - 1), v * (self.rows - 1)
        i, j = min(int(x), self.cols - 2), min(int(y), self.rows - 2)
        fx, fy = x - i, y - j
        a, b, c, e = self.p[j][i], self.p[j][i + 1], self.p[j + 1][i + 1], self.p[j + 1][i]
        return ((1 - fx) * (1 - fy) * a[0] + fx * (1 - fy) * b[0] + fx * fy * c[0] + (1 - fx) * fy * e[0],
                (1 - fx) * (1 - fy) * a[1] + fx * (1 - fy) * b[1] + fx * fy * c[1] + (1 - fx) * fy * e[1])

    def axes(self, u, v, h=0.01):
        """Unit vectors across (ux) and down (uy) the grid at (u, v)."""
        a, b = self.at(max(0, u - h), v), self.at(min(1, u + h), v)
        c, e = self.at(u, max(0, v - h)), self.at(u, min(1, v + h))
        ux = (b[0] - a[0], b[1] - a[1])
        uy = (e[0] - c[0], e[1] - c[1])
        lx, ly = math.hypot(*ux) or 1, math.hypot(*uy) or 1
        return (ux[0] / lx, ux[1] / lx), (uy[0] / ly, uy[1] / ly)

    def outline(self):
        top = self.p[0]
        right = [r[-1] for r in self.p]
        bottom = self.p[-1][::-1]
        left = [r[0] for r in self.p][::-1]
        return top + right + bottom + left

    def edge_band(self, which, width):
        """A band width px wide inside one edge of the grid: 'bottom', 'top', 'left', 'right'."""
        if which in ("bottom", "top"):
            line = self.p[-1] if which == "bottom" else self.p[0]
            inner = self.p[-2] if which == "bottom" else self.p[1]
        else:
            line = [r[-1] for r in self.p] if which == "right" else [r[0] for r in self.p]
            inner = [r[-2] for r in self.p] if which == "right" else [r[1] for r in self.p]
        band = []
        for (x, y), (ix, iy) in zip(line, inner):
            dx, dy = ix - x, iy - y
            ln = math.hypot(dx, dy) or 1
            band.append((x + dx / ln * width, y + dy / ln * width))
        # carry the outer line a little past the grid so the band's edge never shows a gap
        out = []
        for (x, y), (ix, iy) in zip(line, inner):
            dx, dy = ix - x, iy - y
            ln = math.hypot(dx, dy) or 1
            out.append((x - dx / ln * 3 * K, y - dy / ln * 3 * K))
        return out + band[::-1]


def fill_box(d, box, colour):
    x0, y0, x1, y1 = box
    if os.environ.get("TEACUP_DEBUG_PANELS") and colour == IVORY and FILL_KIND[0] in PANEL_TINT:
        colour = PANEL_TINT[FILL_KIND[0]]
    d.rectangle([x0 * K, y0 * K, x1 * K - 1, y1 * K - 1], fill=colour)


# -- regions ------------------------------------------------------------------------------

def draw_cup(d, r, m):
    """The cup's wall unrolled (rows from the rim down to the foot, the front in the
    middle column): a gold band under the rim with a fine blue line, a gold line
    above the foot, blue fleurs round it with sprigs between, the face kept clear."""
    g = Grid(r["grid"])
    fill_box(d, r["box"], IVORY)
    # (the rim's top centimetre is under the lip ring's overhang)
    for v, w, col in ((0.20, 0.0032, BLUE), (0.255, 0.0022, GOLD), (0.95, 0.0035, GOLD)):
        pts = [g.at(u / 60, v) for u in range(61)]
        d.line(pts, fill=col, width=int(m(w)), joint="curve")
    # u = 0.5 is straight ahead; the eyes take about +-0.07 of a turn
    for u in (0.5 - 0.155, 0.5 + 0.155, 0.5 - 0.33, 0.5 + 0.33, 0.0, 1.0):
        x, y = g.at(u, 0.62)
        ux, uy = g.axes(u, 0.62)
        fleur(d, x, y, m(FLEUR_CUP), ux=ux, uy=uy)
    for u in (0.5 - 0.245, 0.5 + 0.245, 0.5 - 0.415, 0.5 + 0.415):
        x, y = g.at(u, 0.64)
        ux, uy = g.axes(u, 0.64)
        sprig(d, x, y, m(0.026), math.atan2(ux[1], ux[0]) - 0.5)


def scatter(d, g, m, size, rows, colours=(BLUE, BLUE_DARK, BLUE_LIGHT), margin=0.06, step=None, stagger=True):
    """Fleurs in rows across a cloth grid: rows is a list of v (0..1 down the grid);
    they're spaced step metres apart (about two fleurs' width) along each row."""
    step = step or size * 1.9
    for k, v in enumerate(rows):
        # the row's length in px, to space the fleurs evenly in metres
        pts = [g.at(u / 80, v) for u in range(81)]
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        n = max(1, int(length / m(step)))
        for i in range(n):
            f = (i + (0.5 if not stagger or k % 2 == 0 else 1.0)) / n
            if f > 1 - margin or f < margin:
                continue
            x, y = g.at(f, v)
            ux, uy = g.axes(f, v)
            fleur(d, x, y, m(size), *colours, ux=ux, uy=uy)


def draw_robe(d, r, m):
    """The underskirt (cream): a gold hem and a row of blue fleurs above it."""
    g = Grid(r["grid"])
    fill_box(d, r["box"], CREAM)
    d.polygon(g.edge_band("bottom", m(TRIM)), fill=GOLD)
    scatter(d, g, m, FLEUR_ROBE, [0.74], step=FLEUR_ROBE * 2.0)


def draw_coat(d, r, m):
    """The porcelain outer coat (ivory): gold trim down both front edges and along
    the hem, blue fleurs in staggered rows."""
    g = Grid(r["grid"])
    fill_box(d, r["box"], IVORY)
    for e in ("left", "right", "bottom"):
        d.polygon(g.edge_band(e, m(TRIM)), fill=GOLD)
    scatter(d, g, m, FLEUR_COAT, [0.38, 0.72], step=FLEUR_COAT * 2.3)


def draw_mid(d, r, m):
    """The blue mid robe: a gold line along its hem and front edges."""
    g = Grid(r["grid"])
    fill_box(d, r["box"], BLUE)
    for e in ("left", "right", "bottom"):
        d.polygon(g.edge_band(e, m(TRIM * 0.7)), fill=GOLD)


def draw_mantle(d, r, m):
    """The shoulder mantle (ivory): a gold band along its scalloped hem and small
    fleurs in a row round it."""
    g = Grid(r["grid"])
    fill_box(d, r["box"], IVORY)
    d.polygon(g.edge_band("bottom", m(TRIM)), fill=GOLD)
    for e in ("left", "right"):
        d.polygon(g.edge_band(e, m(TRIM * 0.8)), fill=GOLD)
    scatter(d, g, m, FLEUR_MANTLE, [0.52], step=FLEUR_MANTLE * 2.4, stagger=False)


def draw_cape(d, r, m):
    """The royal blue cape: a gold hem."""
    g = Grid(r["grid"])
    fill_box(d, r["box"], BLUE)
    d.polygon(g.edge_band("bottom", m(TRIM * 1.2)), fill=GOLD)


def draw_tabard(d, r, m):
    """The blue tabard: a gold border inside its outline, a white cross under the brooch
    and an ivory fleur near the pointed hem."""
    g = Grid(r["grid"])
    fill_box(d, r["box"], BLUE)
    for e in ("left", "right", "bottom", "top"):
        d.polygon(g.edge_band(e, m(0.006)), fill=GOLD)
    x, y = g.at(0.5, 0.15)                  # just below the brooch
    ux, uy = g.axes(0.5, 0.15)
    cross(d, x, y, m(CROSS_TABARD), IVORY, BLUE_DARK, CREAM, ux=ux, uy=uy)
    x, y = g.at(0.5, 0.80)
    ux, uy = g.axes(0.5, 0.80)
    fleur(d, x, y, m(FLEUR_TABARD), CREAM, BLUE_DARK, IVORY, ux=ux, uy=uy)


MAX_STRETCH = 0.10                       # no motif where the cloth's unwrap stretches more than this


def fits(g, u, v, half_px, bottom_px=0.0):
    """Whether a motif half_px in radius at (u, v) lies wholly inside the grid, with
    bottom_px kept clear along its last row (the lining band): measured along the
    grid's own rows and columns, so a motif is never cut by a panel's seam."""
    for du, dv in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        uu, vv, step = u, v, 0.002
        pos, gone = g.at(u, v), 0.0
        while gone < half_px + (bottom_px if dv == 1 else 0.0):
            nu, nv = uu + du * step, vv + dv * step
            if not (0.0 <= nu <= 1.0 and 0.0 <= nv <= 1.0):
                return False
            q = g.at(nu, nv)
            gone += math.dist(pos, q)
            pos, uu, vv = q, nu, nv
    return True


def upright_motifs(d, g, m, spots, band=0.0):
    """Fleurs at (u, v, size) standing upright in the world, skipping any spot whose
    cloth stretches more than MAX_STRETCH in the unwrap or where the fleur would not
    fit whole inside the panel (clear of a band metres wide along its last row)."""
    for u, v, size in spots:
        if g.stretch_near(u, v) > MAX_STRETCH:
            continue
        if not fits(g, u, v, m(size) * 0.5, m(band)):
            continue
        x, y = g.at(u, v)
        ux, uy = g.upright(u, v)
        fleur(d, x, y, m(size), ux=ux, uy=uy)


def draw_sleeve_upper(d, r, m):
    """A sleeve's upper tube (rows from the shoulder to the elbow, its seam under the
    arm at both side edges, the top of the arm in the middle): ivory, small fleurs
    down its outside."""
    g = Grid(r["grid"], r.get("up"), r.get("stretch"))
    fill_box(d, r["box"], IVORY)
    upright_motifs(d, g, m, ((0.27, 0.62, FLEUR_SLEEVE * 0.8), (0.73, 0.62, FLEUR_SLEEVE * 0.8)))


LINING_BAND = 0.024                      # m of blue lining turned out along a sleeve's opening
EDGE_TRIM = 0.0045                       # m of gold at its very edge


LAYOUT = {}                              # the whole layout, while drawing (for a panel's neighbours)
# a sleeve's panels round its opening, each one's first column the previous one's last
SLEEVE_RING = ("bell", "drape_a", "drape_b")


def fit_similarity(src, dst):
    """The similarity transform (complex a, b: z -> a z + b) best taking the points
    src onto dst (least squares)."""
    zs = [complex(*p) for p in src]
    zd = [complex(*p) for p in dst]
    ms, md = sum(zs) / len(zs), sum(zd) / len(zd)
    num = sum((d - md) * (s - ms).conjugate() for s, d in zip(zs, zd))
    den = sum(abs(s - ms) ** 2 for s in zs) or 1.0
    a = num / den
    return a, md - a * ms


def neighbour_edges(name, g):
    """The opening edges of the panels either side of this sleeve panel, carried
    into this panel's unwrap by matching the column they share: (before, after),
    each a list of px points running away from this panel (or None)."""
    side, part = name.rsplit("_", 1) if not name.endswith(("_a", "_b")) else (name[:-8], name[-7:])
    if part not in SLEEVE_RING:
        return None, None
    k = SLEEVE_RING.index(part)
    out = []
    for nk, mine, theirs in (((k - 1) % 3, 0, -1), ((k + 1) % 3, -1, 0)):
        other = LAYOUT.get(f"{side}_{SLEEVE_RING[nk]}")
        if not other:
            out.append(None)
            continue
        og = [[(x * K, y * K) for x, y in row] for row in other["grid"]]
        shared_me = [row[mine] for row in g.p]
        shared_them = [row[theirs] for row in og]
        a, b = fit_similarity(shared_them, shared_me)
        edge = og[-1] if theirs == -1 else og[-1][:]
        pts = [a * complex(*p) + b for p in edge]
        pts = [(z.real, z.imag) for z in pts]
        out.append(pts[::-1][1:] if theirs == -1 else pts[1:])
    return out[0], out[1]


def opening_band(d, g, m, name=""):
    """The sleeve's lining turned back along the opening (its last row): a wide blue
    band with a thin gold edge, each everything within its width of the opening's
    edge (a round-ended stroke along it). The edge is carried on past the panel's
    ends along its end directions, as the opening goes on into the next panel, so
    the bands of panels unrolled apart meet at their seams; outside the panel the
    paint falls where no face samples it."""
    edge = list(g.p[-1])
    before, after = neighbour_edges(name, g)
    reach = m(0.05)

    def carry(a, b):                     # from b on, away from a, reach px
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy) or 1.0
        return (b[0] + dx / ln * reach, b[1] + dy / ln * reach)
    # on into the next panels along their own opening edges where they are known
    head = before[::-1] if before else [carry(edge[1], edge[0])]
    tail = after if after else [carry(edge[-2], edge[-1])]
    edge = head + edge + tail
    for width, colour in ((LINING_BAND, BLUE), (EDGE_TRIM, GOLD)):
        w = m(width)
        d.line(edge, fill=colour, width=int(2 * w), joint="curve")
        for x, y in (edge[0], edge[-1]):
            d.ellipse([x - w, y - w, x + w, y + w], fill=colour)


DEBUG_PANELS = os.environ.get("TEACUP_DEBUG_PANELS")   # tint each sleeve panel (debugging the unwrap)
PANEL_TINT = {"sleeve_upper": (240, 120, 120), "sleeve_bell": (120, 220, 120), "sleeve_drape": (230, 220, 90),
              "sleeve_drape_b": (220, 120, 230)}
FILL_KIND = [""]


def draw_sleeve_bell(d, r, m):
    """The bell over the forearm (rows from the elbow to the wrist opening, the top
    of the forearm in the middle): ivory, the lining band along the opening, fleurs."""
    g = Grid(r["grid"], r.get("up"), r.get("stretch"))
    fill_box(d, r["box"], IVORY)
    opening_band(d, g, m, r["name"])
    upright_motifs(d, g, m, ((0.24, 0.55, FLEUR_SLEEVE), (0.76, 0.55, FLEUR_SLEEVE)), LINING_BAND + 0.004)


def draw_sleeve_drape(d, r, m):
    """One layer of the drape (rows from the elbow to the opening; the opening's
    edge, which runs down to the drape's point, is its last row; its bottom crease
    is one side edge): ivory, the lining band along the opening and a big fleur
    standing upright as it hangs, wholly inside the panel."""
    g = Grid(r["grid"], r.get("up"), r.get("stretch"))
    fill_box(d, r["box"], IVORY)
    opening_band(d, g, m, r["name"])
    upright_motifs(d, g, m, ((0.5, 0.48, FLEUR_DRAPE),), LINING_BAND + 0.004)


def draw_flat(d, r, m, bg):
    x0, y0, x1, y1 = (v * K for v in r["box"])
    fill_box(d, r["box"], bg)
    return x0, y0, x1, y1


def draw_book_cover(d, r, m):
    """The book's outside, both covers and the spine laid out flat: dark blue, a
    gold border round each cover and an ivory fleur in each."""
    fill_box(d, r["box"], BLUE_DARK)
    for c in r["covers"]:                      # [x0, y0, x1, y1] px of each cover
        x0, y0, x1, y1 = (v * K for v in c)
        inset = m(0.008)
        d.rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset], outline=GOLD, width=int(m(0.0035)))
        fleur(d, (x0 + x1) / 2, (y0 + y1) / 2, min((x1 - x0) * 0.62, m(FLEUR_BOOK)), IVORY, GOLD, CREAM)


# The open book's two pages: her Arts (docs/character_abilities_stats.md), each
# Art's name as a header and its description under it: Warm Pour and Steady Sip on
# her left page, her signature Tea Break on the right (the owner's layout).
BOOK_PAGES = (
    (("Warm Pour", "Restores 30% of the target's maximum HP, rounded up.", "Range 3  ·  Noise +1"),
     ("Steady Sip", "Removes one negative status and grants +2 Defense until the next Player Phase.",
      "Noise 0")),
    (("Tea Break", "Heals all allies in the area for 20% of maximum HP, rounded up, and removes one "
      "negative status from each affected ally.", "Signature Art  ·  Noise +2"),),
)
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts", "ebgaramond")


def font(name, px):
    """EB Garamond (assets/fonts/ebgaramond) at px."""
    from PIL import ImageFont
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(px))


def tea_art(d, cx, cy, size):
    """A little teacup on its saucer with three curls of steam, in the book's ink:
    size px wide, centred on (cx, cy)."""
    s = size / 2
    ink, lw = BROWN_DARK, max(1, int(size * 0.025))
    # saucer: a shallow dish seen from a little above, its rim flaring up from a
    # small foot: the underside curves down from the rim's ends to the foot, the rim
    # is an ellipse over it, and the well the cup stands in sits inside the rim
    ry = cy + 0.26 * s                         # the rim's middle
    under = path((cx - s, ry),
                 ((cx - 0.86 * s, ry + 0.12 * s), (cx - 0.62 * s, ry + 0.16 * s), (cx - 0.40 * s, ry + 0.17 * s)),
                 ((cx - 0.10 * s, ry + 0.19 * s), (cx + 0.10 * s, ry + 0.19 * s), (cx + 0.40 * s, ry + 0.17 * s)),
                 ((cx + 0.62 * s, ry + 0.16 * s), (cx + 0.86 * s, ry + 0.12 * s), (cx + s, ry)))
    d.polygon(under, fill=IVORY)
    d.line(under, fill=ink, width=lw, joint="curve")
    d.line([(cx - 0.32 * s, ry + 0.175 * s), (cx + 0.32 * s, ry + 0.175 * s)], fill=ink, width=max(1, lw // 2))  # the foot ring
    d.ellipse([cx - s, ry - 0.13 * s, cx + s, ry + 0.13 * s], fill=IVORY, outline=ink, width=lw)
    d.ellipse([cx - 0.84 * s, ry - 0.09 * s, cx + 0.84 * s, ry + 0.09 * s], outline=BLUE, width=max(1, lw // 2))
    d.ellipse([cx - 0.46 * s, ry - 0.05 * s, cx + 0.46 * s, ry + 0.07 * s], outline=TAN, width=max(1, lw // 2))
    # handle: a ring on the cup's right
    d.ellipse([cx + 0.42 * s, cy - 0.22 * s, cx + 0.86 * s, cy + 0.18 * s], outline=ink, width=int(lw * 1.6))
    # the bowl: a wide, rounded cup from its rim down to a small foot
    bowl = path((cx - 0.66 * s, cy - 0.30 * s),
                ((cx - 0.64 * s, cy + 0.10 * s), (cx - 0.36 * s, cy + 0.36 * s), (cx, cy + 0.36 * s)),
                ((cx + 0.36 * s, cy + 0.36 * s), (cx + 0.64 * s, cy + 0.10 * s), (cx + 0.66 * s, cy - 0.30 * s)))
    d.polygon(bowl, fill=IVORY, outline=ink)
    d.line(bowl + [bowl[0]], fill=ink, width=lw, joint="curve")
    # a blue band round the bowl, and the tea inside its rim
    d.line([(cx - 0.62 * s, cy - 0.06 * s), (cx + 0.62 * s, cy - 0.06 * s)], fill=BLUE, width=int(lw * 1.4))
    d.ellipse([cx - 0.66 * s, cy - 0.40 * s, cx + 0.66 * s, cy - 0.20 * s], fill=IVORY, outline=ink, width=lw)
    d.ellipse([cx - 0.56 * s, cy - 0.37 * s, cx + 0.56 * s, cy - 0.23 * s], fill=BROWN)
    # steam: three soft S-curls rising from the tea
    for k, dx in enumerate((-0.30, 0.0, 0.30)):
        x0, y0 = cx + dx * s, cy - 0.46 * s
        h = (0.55 if k == 1 else 0.42) * s
        curl = bezier((x0, y0), (x0 - 0.16 * s, y0 - h * 0.35), (x0 + 0.16 * s, y0 - h * 0.65),
                                   (x0, y0 - h), 20)
        d.line([(x0, y0)] + curl, fill=TAN, width=lw, joint="curve")


def wrap(d, text, f, width):
    """Lines of text that each fit width px in font f."""
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=f) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def draw_page(d, r, m):
    """The open pages: on each, its Arts one under another (the name as a header, a
    small rule, the description and a footer line), and a small blue cross at the foot. The
    pages' atlas is laid out as the book is seen from outside (the cover's side),
    so the art is drawn on its own layer and mirrored left to right: the text reads
    the right way round from her side, BOOK_PAGES[0] on her left page."""
    from PIL import Image, ImageDraw
    fill_box(d, r["box"], IVORY)
    bx0, by0, bx1, by1 = (int(v * K) for v in r["box"])
    layer = Image.new("RGBA", (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    # each page's rectangle on the mirrored layer, left to right as she reads them
    rects = sorted((bx1 - c[2] * K, c[1] * K - by0, bx1 - c[0] * K, c[3] * K - by0) for c in r["pages"])
    for (x0, y0, x1, y1), entries in zip(rects, BOOK_PAGES):
        w, h = x1 - x0, y1 - y0
        cx = (x0 + x1) / 2
        y = y0 + 0.04 * h
        for title, body, foot in entries:
            head = font("EBGaramond-Bold.ttf", m(0.0075))
            for line in wrap(dl, title, head, w * 0.92):
                dl.text((cx, y), line, font=head, fill=BROWN_DARK, anchor="ma")
                y += m(0.0085)
            y += m(0.002)
            dl.line([(cx - 0.32 * w, y), (cx + 0.32 * w, y)], fill=TAN, width=int(m(0.0007)))
            y += m(0.004)
            text = font("EBGaramond-Regular.ttf", m(0.0052))
            for line in wrap(dl, body, text, w * 0.90):
                dl.text((cx, y), line, font=text, fill=BROWN, anchor="ma")
                y += m(0.0064)
            y += m(0.0025)
            small = font("EBGaramond-Italic.ttf", m(0.0046))
            dl.text((cx, y), foot, font=small, fill=BROWN, anchor="ma")
            y += m(0.012)                   # space before the next Art
        cross_y = y0 + 0.88 * h
        if len(entries) == 1:               # a page with one Art: a little teacup in the space under it
            size = min(w * 0.55, (cross_y - y) * 0.95)
            tea_art(dl, cx, (y + cross_y) / 2 - m(0.004), size)
        cross(dl, cx, cross_y, m(0.018), BLUE, BLUE_DARK, BLUE_LIGHT)
    layer = layer.transpose(Image.FLIP_LEFT_RIGHT)
    d._image.paste(layer, (bx0, by0), layer)


def draw_collar(d, r, m):
    """The saucer collar seen from above: a gold rim line, a blue ring, sprigs."""
    x0, y0, x1, y1 = draw_flat(d, r, m, IVORY)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rad = r["radius"] * K                      # px of the saucer's outer edge
    for rr, col, w in ((rad - m(0.010), GOLD, m(0.006)), (rad * 0.52, BLUE, m(0.003))):
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=col, width=int(w))
    for i in range(10):
        a = 2 * math.pi * (i + 0.5) / 10
        sprig(d, cx + math.cos(a) * rad * 0.76, cy + math.sin(a) * rad * 0.76, m(0.024), a + math.pi / 2)


def draw_brooch(d, r, m):
    """The gold quatrefoil brooch's face: amber outline, gold lobes and an amber
    cross (no painted highlight: the room's light shades it)."""
    x0, y0, x1, y1 = draw_flat(d, r, m, GOLD)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = r["radius"] * K / 1.0
    lobes = quatrefoil_shapes()
    for p in lobes:
        d.polygon(place(p, cx, cy, s), fill=BROWN)
    for p in lobes:
        d.polygon(place(offset(p, -0.07), cx, cy, s), fill=GOLD)
    parts, _ = cross_shapes()
    for p in parts:
        d.polygon(place(offset(p, 0.08), cx, cy, s * 0.42), fill=BROWN)
    for p in parts:
        d.polygon(place(p, cx, cy, s * 0.42), fill=AMBER)


DRAW = {"cup": draw_cup, "robe": draw_robe, "coat": draw_coat, "mid": draw_mid, "mantle": draw_mantle,
        "cape": draw_cape, "tabard": draw_tabard, "sleeve_upper": draw_sleeve_upper,
        "sleeve_bell": draw_sleeve_bell, "sleeve_drape": draw_sleeve_drape,
        "book_cover": draw_book_cover, "page": draw_page, "collar": draw_collar, "brooch": draw_brooch}


def main(layout_path, out=OUT):
    from PIL import Image, ImageDraw
    with open(layout_path, encoding="utf-8") as f:
        layout = json.load(f)
    size = layout["size"]
    img = Image.new("RGBA", (size * K, size * K), (0, 0, 0, 0))
    LAYOUT.clear()
    LAYOUT.update(layout["regions"])
    for name, r in layout["regions"].items():
        r["name"] = name
        kind = r.get("kind", name)
        FILL_KIND[0] = kind if not name.endswith("drape_b") else "sleeve_drape_b"
        dens = r["density"]
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))   # each region drawn alone, clipped to its box
        d = ImageDraw.Draw(layer)
        DRAW[kind](d, r, lambda metres, k=dens: metres * k * K)
        box = tuple(int(v * K) for v in r["box"])
        img.paste(layer.crop(box), box[:2])
    img = img.resize((size, size), Image.LANCZOS)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print("wrote", os.path.normpath(out))


def motif_sheet(out):
    """The motifs at review size and at battle scale (1 px = 7.8 mm)."""
    from PIL import Image, ImageDraw
    W, H = 1400, 520
    img = Image.new("RGB", (W * K, H * K), IVORY)
    d = ImageDraw.Draw(img)
    fleur(d, 190 * K, 230 * K, 330 * K)
    fleur(d, 480 * K, 230 * K, 330 * K, CREAM, BLUE_DARK, IVORY)
    d.rectangle([640 * K, 30 * K, 900 * K, 430 * K], fill=BLUE)
    cross(d, 770 * K, 230 * K, 300 * K)
    sprig(d, 1040 * K, 150 * K, 220 * K)
    lobes = quatrefoil_shapes()
    for p in lobes:
        d.polygon(place(p, 1040 * K, 360 * K, 80 * K), fill=BROWN)
    for p in lobes:
        d.polygon(place(offset(p, -0.07), 1040 * K, 360 * K, 80 * K), fill=GOLD)
    parts, _ = cross_shapes()
    for p in parts:
        d.polygon(place(offset(p, 0.08), 1040 * K, 360 * K, 34 * K), fill=BROWN)
        d.polygon(place(p, 1040 * K, 360 * K, 34 * K), fill=AMBER)
    # battle scale: each motif at its real size, 128 px per metre, then blown up 4x nearest
    small = Image.new("RGB", (64 * K, 16 * K), IVORY)
    sd = ImageDraw.Draw(small)
    for k, hgt in enumerate((FLEUR_CUP, FLEUR_ROBE, FLEUR_MANTLE, FLEUR_DRAPE)):
        fleur(sd, (8 + 14 * k) * K, 8 * K, hgt * 128 * K)
    small = small.resize((64, 16), Image.LANCZOS).resize((64 * 8, 16 * 8), Image.NEAREST)
    img = img.resize((W, H), Image.LANCZOS)
    img.paste(small, (1180 - 300, 440))
    img.save(out)
    print("wrote", out)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--motifs":
        motif_sheet(sys.argv[2])
    else:
        main(sys.argv[1], *(sys.argv[2:3]))
