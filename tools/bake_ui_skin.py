"""Bake the pixel-art UI skin: 9-slice panel and button states (Pillow).

python tools/bake_ui_skin.py  ->  assets/ui/skin/*.png

Drawn at 1 art pixel = 2 screen pixels so the frames match the battle
sprites' chunky pixel density. assets/ui/slice_theme.tres slices each image
with an 8px margin (4 art pixels).
"""
import os

from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "ui", "skin")
ART = 12  # art pixels per side; 4 border + 4 stretch + 4 border
SCALE = 2

INK = (20, 16, 24)
PANEL_FILL = (29, 26, 34)
PANEL_EDGE = (74, 66, 86)
PANEL_LIGHT = (112, 100, 128)
PANEL_SHADE = (44, 39, 52)

BUTTONS = {
    # state: (fill, top light, bottom shade)
    "button_normal": ((107, 85, 68), (150, 122, 96), (72, 56, 46)),
    "button_hover": ((132, 106, 82), (184, 152, 116), (88, 68, 54)),
    "button_pressed": ((80, 63, 51), (64, 50, 41), (107, 85, 68)),
    "button_disabled": ((70, 66, 74), (92, 88, 98), (52, 48, 56)),
}


def frame(fill, light, shade, notch=True):
    img = Image.new("RGBA", (ART, ART), (0, 0, 0, 0))
    px = img.load()
    for y in range(ART):
        for x in range(ART):
            edge = x in (0, ART - 1) or y in (0, ART - 1)
            corner = (x in (0, ART - 1)) and (y in (0, ART - 1))
            if corner and notch:
                continue
            if edge:
                px[x, y] = INK + (255,)
            elif y == 1 or x == 1:
                px[x, y] = light + (255,)
            elif y == ART - 2 or x == ART - 2:
                px[x, y] = shade + (255,)
            else:
                px[x, y] = fill + (255,)
    return img


def panel():
    img = frame(PANEL_FILL, PANEL_LIGHT, PANEL_SHADE)
    px = img.load()
    # A second, inset edge line gives the panel a bevelled rim.
    for i in range(2, ART - 2):
        for x, y in ((i, 2), (2, i), (i, ART - 3), (ART - 3, i)):
            px[x, y] = PANEL_EDGE + (255,)
    for x, y in ((2, 2), (ART - 3, 2), (2, ART - 3), (ART - 3, ART - 3)):
        px[x, y] = PANEL_LIGHT + (255,)
    return img


def save(name, img):
    img.resize((ART * SCALE, ART * SCALE), Image.NEAREST).save(os.path.join(OUT, name + ".png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    save("panel", panel())
    for name, colours in BUTTONS.items():
        save(name, frame(*colours))
    print("wrote panel,", ", ".join(BUTTONS))


if __name__ == "__main__":
    main()
