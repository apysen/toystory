"""Draw the Umbrella Lancer's line art (Pillow): the detail atlas his model's texture
is built from.

python tools/draw_umbrella_details.py  ->  assets/models/umbrella/source/umbrella_details.png

Run it before tools/build_umbrella_lancer_3d.py, which lays these regions over the
cloth and plate (toy3d.Builder.map_detail) and fills the top-left corner with the
palette swatches. Drawn as smooth vector shapes at 4x and scaled down; colours are
the model's palette; no shading (folds are geometry, lit by the room). The
fleur-de-lis and outline helpers are the Teacup's (draw_teacup_details_v2).

Regions (px in the 1024 atlas, origin top-left; the build uses the same numbers):
  TABARD    his tabard's front, flat: u across it, v from its top at the collar to
            its pointed hem. A teal field in a fine gold border, the concept's cream
            lion rampant on the chest and a gold fleur-de-lis low down.
  CAPE      the cape's outside unrolled: u across from his right edge to his left,
            v from the shoulders to the hem. Teal, a gold band along the hem and up
            both edges, and gold fleurs-de-lis scattered over its lower half.
  PAULDRON  a gold fleur on plain teal: both pauldrons' faces.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True
_TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _TOOLS)
import draw_teacup_details_v2 as motifs  # noqa: E402  (fleur_shapes, path, mirror, draw_motif)

OUT = os.path.join(_TOOLS, "..", "assets", "models", "umbrella", "source", "umbrella_details.png")
SIZE, K = 1024, 4
TABARD = (256, 0, 448, 544)
CAPE = (448, 0, 1024, 512)
PAULDRON = (0, 256, 256, 512)

TEAL, TEAL_DARK = (36, 106, 114), (14, 62, 80)
CREAM = (250, 232, 192)
GOLD, GOLD_DARK = (250, 184, 60), (176, 112, 30)


def box(region):
    x0, y0, x1, y1 = region
    return x0 * K, y0 * K, x1 * K, y1 * K


def lion_shapes():
    """A heraldic lion rampant facing the viewer's left: rearing on one hind leg,
    forepaws raised, the other hind leg lifted, a curling tail up behind. Unit
    space, y down, about -1 (top) .. 1 (foot)."""
    P = motifs.path
    body = P((-0.18, -0.80),                                          # top of the head
             ((-0.05, -0.86), (0.10, -0.80), (0.12, -0.66)),          # the mane over the back of the head
             ((0.22, -0.60), (0.24, -0.46), (0.18, -0.36)),           # mane down the neck
             ((0.30, -0.20), (0.34, 0.02), (0.26, 0.20)),             # the back down to the haunch
             ((0.36, 0.30), (0.34, 0.48), (0.22, 0.60)),              # the haunch
             ((0.20, 0.74), (0.22, 0.86), (0.34, 0.92)),              # the standing hind leg
             ((0.30, 1.0), (0.06, 1.0), (0.04, 0.92)),                # its foot
             ((0.06, 0.78), (0.04, 0.66), (-0.02, 0.58)),             # up its front
             ((-0.14, 0.62), (-0.28, 0.56), (-0.36, 0.64)),           # under to the raised hind leg
             ((-0.48, 0.66), (-0.52, 0.54), (-0.44, 0.48)),           # its paw
             ((-0.30, 0.40), (-0.18, 0.34), (-0.12, 0.20)),           # back up its thigh
             ((-0.14, 0.04), (-0.16, -0.08), (-0.22, -0.16)),         # the belly up to the chest
             ((-0.40, -0.12), (-0.56, -0.06), (-0.64, -0.14)),        # the lower foreleg reaching out
             ((-0.70, -0.20), (-0.64, -0.30), (-0.56, -0.26)),        # its paw
             ((-0.44, -0.22), (-0.32, -0.30), (-0.30, -0.36)),        # back along it
             ((-0.44, -0.42), (-0.60, -0.50), (-0.66, -0.60)),        # the upper foreleg
             ((-0.72, -0.68), (-0.64, -0.76), (-0.56, -0.70)),        # its paw
             ((-0.44, -0.62), (-0.36, -0.56), (-0.32, -0.56)),        # back to the jaw
             ((-0.40, -0.62), (-0.38, -0.74), (-0.18, -0.80)))        # the face up to the head
    tail = P((0.26, 0.16),
             ((0.48, 0.10), (0.58, -0.10), (0.52, -0.32)),
             ((0.48, -0.48), (0.58, -0.60), (0.70, -0.58)),           # curling up behind
             ((0.62, -0.52), (0.58, -0.44), (0.62, -0.32)),
             ((0.68, -0.08), (0.56, 0.16), (0.30, 0.24)))
    return [body, tail]


def draw_tabard(d):
    x0, y0, x1, y1 = TABARD
    d.rectangle(box(TABARD), fill=GOLD)
    inset = 7
    d.rectangle([(x0 + inset) * K, (y0 + inset) * K, (x1 - inset) * K, (y1 - inset) * K], fill=TEAL)
    cx = (x0 + x1) / 2 * K
    w = (x1 - x0) * K
    motifs.draw_motif(d, lion_shapes(), [], cx, (y0 + 0.2 * (y1 - y0)) * K, w * 0.36, CREAM, TEAL_DARK, CREAM,
                      line_w=0.05)
    parts, hi = motifs.fleur_shapes()
    motifs.draw_motif(d, parts, hi, cx, (y0 + 0.66 * (y1 - y0)) * K, w * 0.22, GOLD, GOLD_DARK, GOLD,
                      line_w=0.06)


def draw_cape(d):
    """The cape's outside, laid out by its cloth grid: u across its columns from his
    right edge to his left, v down its rows from the shoulders to the hem. A gold band
    along the hem row and up both edge columns, gold fleurs over its lower half."""
    x0, y0, x1, y1 = CAPE
    d.rectangle(box(CAPE), fill=TEAL)
    hem = (y1 - y0) / 14 * 0.55                 # most of the last row of 14
    edge = (x1 - x0) / 26 * 0.45                # most of the edge column of 26
    d.rectangle([x0 * K, (y1 - hem) * K, x1 * K, y1 * K], fill=GOLD)
    d.rectangle([x0 * K, y0 * K, (x0 + edge) * K, y1 * K], fill=GOLD)
    d.rectangle([(x1 - edge) * K, y0 * K, x1 * K, y1 * K], fill=GOLD)
    parts, hi = motifs.fleur_shapes()
    for u, v, s in ((0.18, 0.55, 1.0), (0.50, 0.62, 1.1), (0.82, 0.55, 1.0), (0.34, 0.80, 0.85), (0.66, 0.82, 0.85)):
        motifs.draw_motif(d, parts, hi, (x0 + u * (x1 - x0)) * K, (y0 + v * (y1 - y0)) * K, 26 * s * K,
                          GOLD, GOLD_DARK, GOLD, line_w=0.06)


def draw_pauldron(d):
    """A gold fleur on plain teal (the pauldrons'; their
    gold rims are geometry, so the region carries no border to show at its edges)."""
    x0, y0, x1, y1 = PAULDRON
    d.rectangle(box(PAULDRON), fill=TEAL)
    parts, hi = motifs.fleur_shapes()
    motifs.draw_motif(d, parts, hi, (x0 + x1) / 2 * K, (y0 + y1) / 2 * K, 70 * K, GOLD, GOLD_DARK, GOLD,
                      line_w=0.06)


def main():
    img = Image.new("RGBA", (SIZE * K, SIZE * K), TEAL + (255,))
    for region, draw in ((TABARD, draw_tabard), (CAPE, draw_cape), (PAULDRON, draw_pauldron)):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw(ImageDraw.Draw(layer))
        b = box(region)
        img.paste(layer.crop(b), b[:2])
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
