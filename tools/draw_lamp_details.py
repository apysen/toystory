"""Draw the Lamp Warden's line art (Pillow): the detail atlas his model's texture is
built from.

python tools/draw_lamp_details.py  ->  assets/models/lamp/source/lamp_details.png

Run it before tools/build_lamp_warden_3d.py, which lays these regions over the
cloth (toy3d.Builder.map_detail) and fills the top-left corner with the palette
swatches. Drawn as smooth vector shapes at 4x and scaled down; colours are the
model's palette; no shading (the folds are geometry, lit by the room).

Regions (px in the 1024 atlas, origin top-left; the build uses the same numbers):
  TABARD  the tabard's front, flat, before its bottom tapers to a point: u across
          it (its 15 sprite px), v down it (its 40). A navy field, a fine cream
          border that follows the pointed hem, and the gold sun of the concept
          (the same sun as on his shield), the owner's pick 2026-10-11.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "models", "lamp", "source",
                   "lamp_details.png")
SIZE, K = 1024, 4                      # atlas px, supersampling
TABARD = (320, 0, 512, 512)            # 15 x 40 sprite px at 12.8 atlas px each
TABARD_W, TABARD_H = 15.0, 40.0        # sprite px, as build_lamp_warden_3d.TABARD_X / TABARD_Y

NAVY = (42, 70, 102)                   # palette navy_mid
CREAM = (250, 238, 210)
GOLD = (246, 214, 110)
GOLD_INK = (150, 104, 36)              # the sun's outline
PALE = (250, 234, 178)                 # its bright middle


def tabard_px(x, yy):
    """Atlas px (supersampled) of a point on the tabard: x across from its middle,
    yy down from its top, in sprite px."""
    x0, y0, x1, y1 = TABARD
    return ((x0 + (x + TABARD_W / 2) / TABARD_W * (x1 - x0)) * K, (y0 + yy / TABARD_H * (y1 - y0)) * K)


def draw_tabard(d):
    x0, y0, x1, y1 = TABARD
    d.rectangle([x0 * K, y0 * K, x1 * K, y1 * K], fill=CREAM)                 # the border
    d.rectangle([*tabard_px(-6.0, 1.5), *tabard_px(6.0, 37.5)], fill=NAVY)   # the field inside it
    # the sun: a ring of pointed rays round a disc, outlined in dark gold
    cx, cy = tabard_px(0.0, 18.0)
    unit = (x1 - x0) / TABARD_W * K                                           # one sprite px
    rays = 12
    outline = []
    for i in range(rays * 2):
        a = math.pi * i / rays - math.pi / 2
        r = (5.6 if i % 2 == 0 else 3.6) * unit
        outline.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.polygon(outline, fill=GOLD, outline=GOLD_INK, width=int(0.28 * unit))
    r = 2.9 * unit
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD, outline=GOLD_INK, width=int(0.28 * unit))
    r = 1.6 * unit
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=PALE)


def main():
    img = Image.new("RGBA", (SIZE * K, SIZE * K), NAVY + (255,))
    d = ImageDraw.Draw(img)
    draw_tabard(d)
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
