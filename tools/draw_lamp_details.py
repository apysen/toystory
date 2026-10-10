"""Draw the Lamp Warden's line art (Pillow): the detail atlas his model's
texture is built from.

python tools/draw_lamp_details.py  ->  assets/models/lamp/source/lamp_details.png

Run it before tools/build_lamp_warden_3d.py, which lays these regions over his
cloth and shield (toy3d.Builder.map_detail) and fills the top-left corner with the
palette swatches. Everything is drawn as smooth vector shapes at 4x and scaled
down, so the edges stay clean. Colours are the model's palette, and every line is
kept subtle (thin, close in colour): he reads by his shape. No shading is drawn:
the folds are real geometry and the scene's light shades them.

Regions (px in the 1024 atlas, origin top-left; the build uses the same numbers):
  TABARD  the banner's front, flat: u across it (x -7.5..7.5 sprite px), v down it
          (0..40 px below its top; its bottom tapers to a point, and the art
          tapers with it). Navy, a steel-blue border, a gold sun in the middle with
          long and short rays, a small gold diamond in each lower corner.
  MANTLE  the cream capelet's outside unrolled: u round it from one front edge to
          the other, v from the collar (0) to the scalloped hem (1). A thin brown
          line just above the hem (it follows the scallops) and a row of stitches.
  CAPE    the cream cape's outside: u round it, v from the top (0) to the hem (1).
          A thin brown line along the hem and up both edges.
  ROBE    the navy robe's hem flare, a full turn (819 px a turn, drawn on to
          u = 1.25 for faces across the seam): v from the hem (0) up (1). A
          navy-mid band at the hem under a thin steel-blue line.
  SHIELD  the steel face of the shield, flat: u across it (x -15.5..15.5 px), v
          down it (y 29 at the top .. -32 at the point). A thin gold line just
          inside its edge.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "models", "lamp", "source",
                   "lamp_details.png")
SIZE, K = 1024, 4                      # atlas px, supersampling
TABARD = (256, 0, 448, 512)
SHIELD = (448, 0, 704, 256)
MANTLE = (0, 512, 1024, 640)
CAPE = (0, 640, 1024, 768)
ROBE = (0, 768, 1024, 896)

NAVY, NAVY_MID = (14, 30, 58), (42, 70, 102)
STEEL, STEEL_LIGHT = (118, 134, 142), (168, 182, 188)
CREAM, BROWN = (250, 238, 210), (130, 82, 34)
GOLD = (246, 214, 110)

TABARD_X, TABARD_Y = (-7.5, 7.5), (0.0, 40.0)
SHIELD_FACE = [(0, -32), (6, -25), (11, -16), (14, -6), (15.5, 5), (15, 18), (15, 27), (8, 28.5), (0, 29),
               (-8, 28.5), (-15, 27), (-15, 18), (-15.5, 5), (-14, -6), (-11, -16), (-6, -25)]
SHIELD_X, SHIELD_Y = (-15.5, 15.5), (29.0, -32.0)


def box(region):
    return tuple(v * K for v in region)


def mapper(region, xs, ys):
    """Point in the region (supersampled px) of a point in the part's own
    coordinates, x running across xs and y down ys."""
    x0, y0, x1, y1 = box(region)

    def at(x, y):
        return (x0 + (x1 - x0) * (x - xs[0]) / (xs[1] - xs[0]), y0 + (y1 - y0) * (y - ys[0]) / (ys[1] - ys[0]))
    return at


def draw_tabard(d):
    at = mapper(TABARD, TABARD_X, TABARD_Y)
    x0, y0, x1, y1 = box(TABARD)
    d.rectangle([x0, y0, x1, y1], fill=NAVY_MID)
    # the steel-blue border, inset from the edge
    outer = [at(-6.6, 1.0), at(6.6, 1.0), at(6.6, 39.0), at(-6.6, 39.0)]
    inner = [at(-5.8, 1.8), at(5.8, 1.8), at(5.8, 38.2), at(-5.8, 38.2)]
    d.polygon(outer, fill=STEEL_LIGHT)
    d.polygon(inner, fill=NAVY_MID)
    # the gold sun: a disc with alternating long and short rays
    cx, cy = 0.0, 17.0
    for k in range(16):
        a = 2 * math.pi * k / 16
        r = 4.2 if k % 2 == 0 else 3.0
        w = 0.42 if k % 2 == 0 else 0.32
        tip = (cx + r * math.cos(a), cy + r * math.sin(a))
        left = (cx + 1.6 * math.cos(a + w), cy + 1.6 * math.sin(a + w))
        right = (cx + 1.6 * math.cos(a - w), cy + 1.6 * math.sin(a - w))
        d.polygon([at(*left), at(*tip), at(*right)], fill=GOLD)
    disc = [at(cx + 2.0 * math.cos(a), cy + 2.0 * math.sin(a)) for a in (2 * math.pi * k / 40 for k in range(40))]
    d.polygon(disc, fill=GOLD)
    ring = [at(cx + 1.35 * math.cos(a), cy + 1.35 * math.sin(a)) for a in (2 * math.pi * k / 40 for k in range(40))]
    d.line(ring + [ring[0]], fill=NAVY_MID, width=K)
    # a small gold diamond in each lower corner
    for sx in (-1, 1):
        x, y = sx * 3.9, 31.5
        d.polygon([at(x, y - 1.1), at(x + 0.8, y), at(x, y + 1.1), at(x - 0.8, y)], fill=GOLD)


def draw_shield(d):
    at = mapper(SHIELD, SHIELD_X, SHIELD_Y)
    x0, y0, x1, y1 = box(SHIELD)
    d.rectangle([x0, y0, x1, y1], fill=STEEL)
    # the face's own outline (as the build makes it), and a gold line just inside it
    face = [(x * (1 - 3 / 15.5), y * (1 - 3 / 31) - 0.3) for x, y in SHIELD_FACE]
    cx = sum(x for x, _ in face) / len(face)
    cy = sum(y for _, y in face) / len(face)
    line = [at(cx + (x - cx) * 0.9, cy + (y - cy) * 0.93) for x, y in face]
    d.line(line + [line[0]], fill=GOLD, width=3 * K, joint="curve")


def draw_mantle(d):
    x0, y0, x1, y1 = box(MANTLE)
    h = y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=CREAM)
    d.rectangle([x0, y0 + 0.9 * h, x1, y0 + 0.935 * h], fill=BROWN)        # the trim above the hem
    step = 22 * K
    x = x0 + step * 0.5
    while x < x1:                                                           # a row of stitches above it
        d.line([(x, y0 + 0.8 * h), (x + step * 0.45, y0 + 0.8 * h)], fill=BROWN, width=2 * K)
        x += step


def draw_cape(d):
    x0, y0, x1, y1 = box(CAPE)
    w, h = x1 - x0, y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=CREAM)
    d.rectangle([x0, y0 + 0.955 * h, x1, y0 + 0.975 * h], fill=BROWN)      # along the hem
    for x in (x0 + 0.008 * w, x1 - 0.016 * w):                             # and up both edges
        d.rectangle([x, y0 + 0.25 * h, x + 0.008 * w, y0 + 0.975 * h], fill=BROWN)


def draw_robe(d):
    x0, y0, x1, y1 = box(ROBE)
    h = y1 - y0
    d.rectangle([x0, y0, x1, y1], fill=NAVY)
    d.rectangle([x0, y0, x1, y0 + 0.2 * h], fill=NAVY_MID)                 # v = 0 is the hem
    d.rectangle([x0, y0 + 0.22 * h, x1, y0 + 0.25 * h], fill=STEEL_LIGHT)


def main():
    img = Image.new("RGBA", (SIZE * K, SIZE * K), (0, 0, 0, 0))
    for draw, region in ((draw_tabard, TABARD), (draw_shield, SHIELD), (draw_mantle, MANTLE), (draw_cape, CAPE),
                         (draw_robe, ROBE)):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))   # each region drawn alone, clipped to its box
        draw(ImageDraw.Draw(layer))
        b = box(region)
        img.paste(layer.crop(b), b[:2])
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
