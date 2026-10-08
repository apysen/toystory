"""Bake conversation portraits for the enemies from their battle sprites (Pillow).

python tools/bake_portraits.py  ->  assets/portraits/<id>.png

Matches the hand-made portraits: a 64x64 close-up of the sprite at 2x
(128x128) on a muted backdrop with a lighter halo behind the head. Portraits
may be more detailed than battle sprites (vertical_slice_plan.md section 21);
these are stand-ins at the battle sprite's detail until drawn by hand.
"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(__file__), "..", "assets")
CROP = 64
SCALE = 2

# id -> (crop centre in sprite pixels, backdrop colour, halo colour)
PORTRAITS = {
    "pencil": ((64, 52), (94, 100, 84), (120, 126, 106)),
    "rubber": ((74, 56), (76, 98, 100), (100, 124, 124)),
    "bookend": ((64, 72), (88, 82, 104), (114, 108, 132)),
    "tape": ((58, 66), (82, 92, 112), (108, 118, 140)),
    "roomba": ((64, 72), (104, 96, 90), (132, 124, 116)),
}


def bake(pid, centre, backdrop, halo):
    sprite = Image.open(os.path.join(ROOT, "sprites", "enemies", pid, pid + ".png")).convert("RGBA")
    x0, y0 = centre[0] - CROP // 2, centre[1] - CROP // 2
    face = Image.new("RGBA", (CROP, CROP), (0, 0, 0, 0))
    face.alpha_composite(sprite.crop((max(x0, 0), max(y0, 0), x0 + CROP, y0 + CROP)), (max(-x0, 0), max(-y0, 0)))
    size = CROP * SCALE
    out = Image.new("RGBA", (size, size), backdrop + (255,))
    d = ImageDraw.Draw(out)
    r = size * 0.41
    cx, cy = size / 2, size * 0.45
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=halo + (255,))
    out.alpha_composite(face.resize((size, size), Image.NEAREST))
    path = os.path.join(ROOT, "portraits", pid + ".png")
    out.save(path)
    return out


def main():
    tiles = [bake(pid, *cfg) for pid, cfg in PORTRAITS.items()]
    gap = 8
    strip = Image.new("RGBA", (len(tiles) * (128 + gap) + gap, 128 + gap * 2), (40, 36, 44, 255))
    for i, t in enumerate(tiles):
        strip.alpha_composite(t, (gap + i * (128 + gap), gap))
    strip.save(os.path.join(ROOT, "portraits", "enemy_portraits_preview.png"))
    print("wrote", ", ".join(PORTRAITS))


if __name__ == "__main__":
    main()
