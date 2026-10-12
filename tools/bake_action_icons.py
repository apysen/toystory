"""Bake the action ring icons (Pillow).

python tools/bake_action_icons.py  ->  assets/sprites/ui/actions/<id>.png

32x32 pixel-art medallions shown at 2x on the Paper Mario style ring. The rim
colour says what kind of action it is: red Attack, orange Arts that make
Noise, teal quiet (0-Noise) Arts, blue items, green Talk, grey Wait.
"""
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites", "ui", "actions")
S = 32
INK = (24, 18, 28, 255)
WHITE = (250, 246, 236, 255)

KIND = {
    "attack": (217, 72, 59), "noisy": (232, 145, 58), "quiet": (63, 174, 138),
    "item": (63, 127, 208), "talk": (92, 186, 92), "wait": (138, 138, 150),
}


def medallion(kind):
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = KIND[kind]
    d.ellipse([1, 1, 30, 30], fill=INK)
    d.ellipse([2, 2, 29, 29], fill=c + (255,))
    d.ellipse([4, 4, 27, 27], fill=tuple(int(v * 0.72) for v in c) + (255,))
    d.arc([4, 4, 27, 27], 200, 320, fill=tuple(min(255, int(v * 1.25)) for v in c) + (255,), width=1)
    return img, d


def star(d, cx, cy, r1, r2, n=8):
    import math
    pts = []
    for k in range(n * 2):
        r = r1 if k % 2 == 0 else r2
        a = math.pi * k / n - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=WHITE, outline=INK)


def glyph(name, d):
    if name == "attack":
        star(d, 16, 16, 10, 4.5)
    elif name == "guard_beam":
        d.polygon([(9, 9), (23, 9), (23, 17), (16, 24), (9, 17)], fill=WHITE, outline=INK)
        d.line([(16, 11), (16, 21)], fill=INK)
    elif name == "flashbulb":
        d.ellipse([11, 8, 21, 18], fill=WHITE, outline=INK)
        d.rectangle([13, 18, 19, 22], fill=(200, 200, 205, 255), outline=INK)
        for x0, y0, x1, y1 in [(7, 12, 9, 12), (23, 12, 25, 12), (16, 4, 16, 6), (9, 6, 10, 7), (22, 7, 23, 6)]:
            d.line([(x0, y0), (x1, y1)], fill=WHITE, width=1)
    elif name == "pin":
        d.ellipse([12, 7, 20, 15], fill=WHITE, outline=INK)
        d.line([(16, 15), (16, 25)], fill=INK, width=3)
        d.line([(16, 15), (16, 24)], fill=WHITE, width=1)
    elif name == "staple_burst":
        for ox in (-4, 4):
            d.line([(12 + ox, 10), (12 + ox, 22)], fill=WHITE, width=2)
            d.line([(12 + ox, 10), (20 + ox, 10)], fill=WHITE, width=2)
            d.line([(20 + ox, 10), (20 + ox, 22)], fill=WHITE, width=2)
    elif name == "spotlight":
        light = (255, 228, 140, 255)
        d.polygon([(13, 11), (19, 11), (25, 24), (7, 24)], fill=light)          # the beam
        d.ellipse([6, 21, 26, 27], fill=WHITE, outline=INK)                      # the pool on the floor
        d.polygon([(11, 5), (21, 5), (20, 11), (12, 11)], fill=(200, 200, 205, 255), outline=INK)  # the shade
        d.line([(12, 11), (20, 11)], fill=WHITE)
    elif name == "staple_storm":
        import math
        d.ellipse([13, 13, 19, 19], fill=WHITE, outline=INK)
        for k in range(8):
            a = math.pi * k / 4
            ux, uy = math.cos(a), math.sin(a)
            px, py = -uy, ux                                                     # across the flight
            x0, y0 = 16 + ux * 7, 16 + uy * 7
            x1, y1 = 16 + ux * 12, 16 + uy * 12
            d.line([(x0 + px * 2, y0 + py * 2), (x1 + px * 2, y1 + py * 2)], fill=WHITE)  # the legs
            d.line([(x0 - px * 2, y0 - py * 2), (x1 - px * 2, y1 - py * 2)], fill=WHITE)
            d.line([(x0 + px * 2, y0 + py * 2), (x0 - px * 2, y0 - py * 2)], fill=WHITE)  # the crown
    elif name == "eject":
        d.rounded_rectangle([10, 13, 22, 24], 3, fill=(236, 196, 128, 255), outline=INK)
        d.polygon([(16, 5), (21, 11), (11, 11)], fill=WHITE, outline=INK)
    elif name == "flash_bake":
        d.polygon([(16, 5), (22, 15), (20, 23), (12, 23), (10, 15), (14, 12)], fill=(255, 214, 102, 255), outline=INK)
        d.polygon([(16, 13), (19, 18), (17, 22), (14, 22), (13, 18)], fill=WHITE)
    elif name == "overheat":
        fire, hot = (214, 48, 38, 255), (255, 214, 102, 255)
        d.polygon([(6, 25), (7, 15), (10, 19), (11, 11), (14, 17), (16, 13), (18, 17), (21, 11), (22, 19),
                   (25, 15), (26, 25)], fill=fire, outline=INK)                  # fire bursting out round it
        d.rounded_rectangle([9, 16, 23, 26], 3, fill=(200, 200, 205, 255), outline=INK)  # the toaster
        d.line([(12, 20), (12, 23)], fill=hot, width=2)                         # its white-hot vents
        d.line([(20, 20), (20, 23)], fill=hot, width=2)
        d.rounded_rectangle([13, 3, 19, 10], 2, fill=(236, 196, 128, 255), outline=INK)  # a slice blasting out
        d.line([(16, 11), (16, 15)], fill=WHITE)
    elif name == "warm_pour":
        d.polygon([(16, 6), (21, 15), (21, 18), (16, 23), (11, 18), (11, 15)], fill=WHITE, outline=INK)
        d.line([(16, 12), (16, 19)], fill=(92, 186, 92, 255), width=2)
        d.line([(13, 16), (19, 16)], fill=(92, 186, 92, 255), width=2)
    elif name == "steady_sip":
        d.rounded_rectangle([9, 14, 21, 23], 3, fill=WHITE, outline=INK)
        d.arc([19, 15, 25, 21], 270, 90, fill=WHITE, width=2)
        for x in (12, 16):
            d.arc([x - 2, 6, x + 2, 12], 90, 270, fill=WHITE, width=1)
    elif name == "tea_break":
        tea, crest = (255, 206, 120, 255), (120, 66, 28, 255)
        d.arc([4, 16, 28, 28], 0, 360, fill=tea, width=2)                        # the ring of tea round her
        d.polygon([(14, 18), (14, 11), (9, 5), (13, 7), (16, 3), (19, 7), (23, 5), (18, 11), (18, 18)],
                  fill=tea, outline=INK)                                         # the column bursting out of the cup
        d.line([(16, 7), (16, 15)], fill=WHITE)
        for x, y in ((6, 9), (26, 9), (5, 14), (27, 14)):                        # spray over the area
            d.rectangle([x - 1, y - 1, x, y], fill=tea)
        d.polygon([(9, 17), (23, 17), (21, 24), (11, 24)], fill=WHITE, outline=INK)  # the cup
        d.line([(10, 18), (22, 18)], fill=crest)                                 # the tea in it
        d.arc([20, 18, 26, 23], 270, 90, fill=WHITE, width=2)                    # its handle
        d.line([(12, 25), (20, 25)], fill=INK)                                   # its foot
    elif name == "suction":
        for r in (10, 6, 2):
            d.arc([16 - r, 16 - r, 16 + r, 16 + r], 30, 300, fill=WHITE, width=2)
    elif name == "blowback":
        for y, l in ((11, 12), (16, 15), (21, 10)):
            d.line([(8, y), (8 + l, y)], fill=WHITE, width=2)
        d.polygon([(22, 12), (26, 16), (22, 20)], fill=WHITE, outline=INK)
    elif name == "lunge":
        d.polygon([(8, 14), (19, 14), (19, 10), (26, 16), (19, 22), (19, 18), (8, 18)], fill=WHITE, outline=INK)
        d.line([(5, 11), (9, 11)], fill=WHITE)
        d.line([(4, 21), (8, 21)], fill=WHITE)
    elif name == "canopy":
        d.pieslice([6, 7, 26, 27], 180, 360, fill=WHITE, outline=INK)
        d.line([(16, 17), (16, 25)], fill=INK, width=2)
        d.arc([13, 22, 17, 27], 0, 180, fill=INK, width=2)
    elif name == "item":
        d.ellipse([8, 8, 24, 24], fill=(214, 206, 176, 255), outline=INK)
        d.ellipse([12, 12, 20, 20], fill=(70, 100, 160, 255), outline=INK)
        d.rectangle([21, 17, 26, 21], fill=(214, 206, 176, 255), outline=INK)
    elif name == "talk":
        d.rounded_rectangle([7, 8, 25, 21], 4, fill=WHITE, outline=INK)
        d.polygon([(11, 20), (11, 26), (16, 20)], fill=WHITE, outline=INK)
        for x in (12, 16, 20):
            d.point((x, 14), fill=INK)
            d.point((x + 1, 14), fill=INK)
    elif name == "wait":
        d.polygon([(10, 7), (22, 7), (16, 16)], fill=WHITE, outline=INK)
        d.polygon([(10, 25), (22, 25), (16, 16)], fill=WHITE, outline=INK)
        d.polygon([(13, 22), (19, 22), (16, 18)], fill=(214, 180, 110, 255))


ICONS = {
    "attack": "attack", "guard_beam": "noisy", "flashbulb": "noisy", "spotlight": "noisy", "pin": "noisy",
    "staple_burst": "noisy", "staple_storm": "noisy",
    "eject": "noisy", "flash_bake": "noisy", "overheat": "noisy", "warm_pour": "noisy", "steady_sip": "quiet",
    "tea_break": "noisy", "suction": "noisy",
    "blowback": "noisy", "lunge": "noisy", "canopy": "quiet", "item": "item", "talk": "talk", "wait": "wait",
}


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = (len(ICONS) + 7) // 8
    sheet = Image.new("RGBA", (S * 8, S * rows), (40, 36, 44, 255))
    for i, (name, kind) in enumerate(ICONS.items()):
        img, d = medallion(kind)
        glyph(name, d)
        img.save(os.path.join(OUT, name + ".png"))
        sheet.alpha_composite(img, ((i % 8) * S, (i // 8) * S))
    sheet.resize((S * 8 * 3, S * rows * 3), Image.NEAREST).save(os.path.join(OUT, "actions_preview.png"))
    print("wrote", len(ICONS), "icons")


if __name__ == "__main__":
    main()
