"""Draw the Toaster Pyromancer's line art (Pillow): the detail atlas his model's
texture is built from.

python tools/draw_toaster_details.py  ->  assets/models/toaster/source/toaster_details.png

Run it before tools/build_toaster_pyromancer_3d.py, which lays these regions over
the cloth (toy3d.Builder.map_detail) and fills the top-left corner with the palette
swatches. Everything is drawn as smooth vector shapes at 4x and scaled down, so the
edges stay clean. Colours are the model's palette. No shading is drawn: the
cloth's folds are real geometry and the scene's light shades them.

Regions (px in the 1024 atlas, origin top-left; the build uses the same numbers):
  ROBE    the robe's skirt unrolled: u runs round it from one front edge to the
          other (u = 0..1 is a full turn from straight ahead), v down from under
          the belt to the hem. Cream, a red band down each front
          edge, and a border of red flames licking up from the hem.
  SLEEVE  a bell sleeve unrolled: u round the sleeve (512 px a turn, drawn on to
          u = 1.25 for faces across the seam), v from the elbow to the cuff. Cream,
          a thin red stripe, and a red cuff with flames rising from it.
  CHEST   his body above the belt unrolled: u round from straight behind (so the
          front is u = 0.5; 819 px a turn, drawn on to u = 1.25), v from the neck
          down to the belt. Cream, and the red band down the front that carries on
          into the robe's front bands.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "models", "toaster", "source",
                   "toaster_details.png")
SIZE, K = 1024, 4                      # atlas px, supersampling
ROBE = (0, 256, 1024, 640)
SLEEVE = (256, 0, 896, 256)
CHEST = (0, 640, 1024, 896)
ROBE_OPEN = 24.0                       # degrees, as build_toaster_pyromancer_3d.ROBE_OPEN

CREAM = (242, 222, 206)
RED, RED_DARK, RED_LIGHT = (186, 22, 62), (114, 14, 50), (216, 69, 92)
GOLD = (250, 182, 50)


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def flame(cx, base, w, h, lean, curl):
    """Outline of one tongue of flame standing on a line at y = base: a wide
    root narrowing up an S-curve to a tip that flicks to one side."""
    left, right = [], []
    n = 24
    for k in range(n + 1):
        t = k / n
        half = w / 2 * (1 - t) ** 0.85 * (1 + 0.25 * math.sin(math.pi * t))
        x = cx + lean * h * t * t + curl * w * 0.35 * math.sin(math.pi * t * 1.4)
        y = base - h * t
        left.append((x - half, y))
        right.append((x + half, y))
    tip = (cx + lean * h + curl * w * 0.45, base - h * 1.04)
    return left + [tip] + right[::-1]


def flame_row(d, x0, x1, base, hmin, hmax, wmin, wmax, seed, period=None):
    """A row of flames between x0 and x1 standing on y = base, each drawn as a
    dark outline, red body and a light inner tongue. With period, the row repeats
    every period px (for art round a tube)."""
    rnd = random.Random(seed)
    tongues = []
    x = x0
    while x < (x0 + period if period else x1):
        w = rnd.uniform(wmin, wmax)
        tongues.append((x + w / 2, w, rnd.uniform(hmin, hmax), rnd.uniform(-0.15, 0.15), rnd.choice((-1, 1))))
        x += w * rnd.uniform(0.62, 0.8)
    reps = range(int(math.ceil((x1 - x0) / period)) + 1) if period else (0,)
    for r in reps:
        for cx, w, h, lean, curl in tongues:
            cx += (period or 0) * r
            if cx - w > x1:
                continue
            outline = flame(cx, base + 6 * K, w + 7 * K, h + 7 * K, lean, curl)
            d.polygon(outline, fill=RED_DARK)
            d.polygon(flame(cx, base + 6 * K, w, h, lean, curl), fill=RED)
            d.polygon(flame(cx + w * 0.06 * curl, base + 2 * K, w * 0.42, h * 0.55, lean * 0.6, -curl), fill=RED_LIGHT)


def draw_robe(img):
    x0, y0, x1, y1 = (v * K for v in ROBE)
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1, y1], fill=CREAM)
    w, h = x1 - x0, y1 - y0
    # the red band down each front edge, following the split as it opens toward the hem
    for side in (0, 1):
        pts_out, pts_in = [], []
        for j in range(41):
            v = j / 40
            half = ROBE_OPEN * smoothstep((v - 0.35) / 0.65) / 360.0
            u = half if side == 0 else 1 - half
            inward = 0.022 if side == 0 else -0.022
            pts_out.append((x0 + w * u, y0 + h * v))
            pts_in.append((x0 + w * (u + inward), y0 + h * v))
        d.polygon(pts_out + pts_in[::-1], fill=RED)
        d.line(pts_in, fill=RED_DARK, width=2 * K)
    # flames licking up from the hem, over a solid red border along the bottom
    band = y1 - 0.12 * h
    d.rectangle([x0, band, x1, y1], fill=RED)
    flame_row(d, x0 - 30 * K, x1 + 30 * K, band, 0.22 * h, 0.42 * h, 26 * K, 46 * K, seed=11)
    d.line([(x0, band + 0.05 * h), (x1, band + 0.05 * h)], fill=RED_DARK, width=2 * K)


def draw_sleeve(img):
    x0, y0, x1, y1 = (v * K for v in SLEEVE)
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1, y1], fill=CREAM)
    period = (x1 - x0) / 1.25
    h = y1 - y0
    d.rectangle([x0, y0 + 0.56 * h, x1, y0 + 0.6 * h], fill=RED)       # a thin red stripe
    band = y0 + 0.82 * h                                                # the red cuff
    d.rectangle([x0, band, x1, y1], fill=RED)
    flame_row(d, x0, x1, band, 0.12 * h, 0.2 * h, 30 * K, 44 * K, seed=7, period=period)
    d.line([(x0, y1 - 0.05 * h), (x1, y1 - 0.05 * h)], fill=GOLD, width=3 * K)


def draw_chest(img):
    x0, y0, x1, y1 = (v * K for v in CHEST)
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1, y1], fill=CREAM)
    turn = (x1 - x0) / 1.25
    # the same band as the top of the robe's front edges: 0.022 of a turn either
    # side of straight ahead, dark red lines along its edges
    left, right = x0 + turn * (0.5 - 0.022), x0 + turn * (0.5 + 0.022)
    d.rectangle([left, y0, right, y1], fill=RED)
    for x in (left, right):
        d.line([(x, y0), (x, y1)], fill=RED_DARK, width=2 * K)


def main():
    img = Image.new("RGBA", (SIZE * K, SIZE * K), (0, 0, 0, 0))
    for draw, box in ((draw_robe, ROBE), (draw_sleeve, SLEEVE), (draw_chest, CHEST)):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))   # each region drawn alone, clipped to its box
        draw(layer)
        box = tuple(v * K for v in box)
        img.paste(layer.crop(box), box[:2])
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
