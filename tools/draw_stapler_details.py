"""Draw the Stapler Rogue's line art (Pillow): the detail atlas his model's texture
is built from.

python tools/draw_stapler_details.py  ->  assets/models/stapler/source/stapler_details.png

Run it before tools/build_stapler_rogue_3d.py, which lays these regions over the
cloth (toy3d.Builder.map_detail, toy3d.bandage) and fills the top-left corner with
the palette swatches. Drawn as smooth vector lines at 4x and scaled down; colours
are the model's palette; no shading (the folds are geometry, lit by the room).
The wraps of his scarf and bandages are told apart by seam lines where one turn of
cloth lies on the next (they used to be painted stripes).

Regions (px in the 1024 atlas, origin top-left; the build uses the same numbers):
  COLLAR     the scarf's thick wrap round his neck: u round the neck, v round the
             tube of cloth, both carried on to 1.25. Purple, with the seams of
             its turns running diagonally round it.
  BAND_FORE  a forearm's bandage (4 wraps): u round the arm (to 1.25), v from the
             elbow to the wrist. Cream, with slanting seams between the wraps.
  BAND_SHIN  a shin's bandage (5 wraps), the same, from the knee to the ankle.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "models", "stapler", "source",
                   "stapler_details.png")
SIZE, K = 1024, 4                      # atlas px, supersampling
COLLAR = (256, 0, 896, 256)
BAND_FORE = (0, 256, 320, 512)
BAND_SHIN = (320, 256, 640, 512)
WRAPS = {BAND_FORE: 4, BAND_SHIN: 5}   # as build_stapler_rogue_3d's bandage() calls
TILT = 0.35                            # toy3d.bandage's default slant

PURPLE, PURPLE_DARK = (130, 10, 194), (94, 6, 150)
CREAM, SEAM = (233, 223, 198), (160, 142, 112)


def draw_collar(d):
    """The turns of the wrap: seams along 3u + 4v = n (where the old painted bands
    ran: every sixth face of 18 round the neck, stepping two per ring of 12)."""
    x0, y0, x1, y1 = COLLAR
    d.rectangle([x0 * K, y0 * K, x1 * K, y1 * K], fill=PURPLE)
    su, sv = (x1 - x0) / 1.25, (y1 - y0) / 1.25
    for n in range(-1, 10):
        pts = []
        for i in range(61):
            u = 1.25 * i / 60
            v = (n - 3 * u) / 4
            pts.append(((x0 + su * u) * K, (y0 + sv * v) * K))
        d.line(pts, fill=PURPLE_DARK, width=int(6.0 * K), joint="curve")
    # (nothing outside the region: crop to it so seams don't spill over)


def draw_bandage(d, region):
    """Seams where each wrap's edge lies on the next, slanting round the limb as
    toy3d.bandage winds it: t = along + tilt / wraps * cos(angle) / 2."""
    x0, y0, x1, y1 = region
    wraps = WRAPS[region]
    d.rectangle([x0 * K, y0 * K, x1 * K, y1 * K], fill=CREAM)
    su = (x1 - x0) / 1.25
    for n in range(0, wraps + 1):
        pts = []
        for i in range(81):
            u = 1.25 * i / 80
            v = n / wraps - TILT / wraps * 0.5 * math.cos(2 * math.pi * u)
            pts.append(((x0 + su * u) * K, (y0 + (y1 - y0) * v) * K))
        d.line(pts, fill=SEAM, width=int(2.5 * K), joint="curve")


def main():
    img = Image.new("RGBA", (SIZE * K, SIZE * K), PURPLE + (255,))
    for region, draw in ((COLLAR, draw_collar), (BAND_FORE, draw_bandage), (BAND_SHIN, draw_bandage)):
        x0, y0, x1, y1 = region
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if draw is draw_collar:
            draw(d)
        else:
            draw(d, region)
        box = (x0 * K, y0 * K, x1 * K, y1 * K)
        img.paste(layer.crop(box), box[:2])
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
