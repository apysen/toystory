"""Draw Teacup Cleric's clean porcelain and cloth line art at 4x resolution.

The atlas contains flat decoration only.  Form, folds, shading, and specular
response come from the model and scene lighting, as required by AGENTS.md.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "assets", "models", "teacup", "source", "teacup_details.png")
SIZE, K = 1024, 4

CUP = (256, 0, 1024, 184)
SLEEVE = (256, 192, 1024, 352)
COLLAR = (0, 256, 256, 512)
MANTLE = (256, 368, 1024, 512)
ROBE = (256, 528, 1024, 720)
TABARD = (0, 544, 144, 1024)
BOOK = (160, 736, 320, 1024)
PAGE = (328, 824, 472, 1024)
COAT = (480, 736, 1024, 1024)
EMBLEM = (152, 544, 408, 800)

CREAM = (249, 229, 198)
IVORY = (255, 243, 213)
BLUE = (36, 89, 180)
BLUE_DARK = (23, 50, 111)
GOLD = (245, 184, 63)
GOLD_LIGHT = (255, 220, 139)


def poly(draw, pts, fill, outline=None, width=1):
    draw.polygon([(int(x), int(y)) for x, y in pts], fill=fill)
    if outline:
        draw.line([(int(x), int(y)) for x, y in pts + [pts[0]]], fill=outline, width=width, joint="curve")


def fleur(draw, cx, cy, s, fill=BLUE, outline=BLUE_DARK):
    """Smooth, legible fleur-de-lis sized for the 128 px battle render."""
    pts = [
        (cx, cy - 1.00*s), (cx + .16*s, cy - .49*s), (cx + .12*s, cy - .12*s),
        (cx + .30*s, cy - .31*s), (cx + .56*s, cy - .43*s), (cx + .76*s, cy - .27*s),
        (cx + .67*s, cy - .01*s), (cx + .49*s, cy + .13*s), (cx + .25*s, cy + .12*s),
        (cx + .17*s, cy + .05*s), (cx + .24*s, cy + .39*s), (cx + .48*s, cy + .39*s),
        (cx + .48*s, cy + .58*s), (cx + .17*s, cy + .58*s), (cx + .11*s, cy + .88*s),
        (cx - .11*s, cy + .88*s), (cx - .17*s, cy + .58*s), (cx - .48*s, cy + .58*s),
        (cx - .48*s, cy + .39*s), (cx - .24*s, cy + .39*s), (cx - .17*s, cy + .05*s),
        (cx - .25*s, cy + .12*s), (cx - .49*s, cy + .13*s), (cx - .67*s, cy - .01*s),
        (cx - .76*s, cy - .27*s), (cx - .56*s, cy - .43*s), (cx - .30*s, cy - .31*s),
        (cx - .12*s, cy - .12*s), (cx - .16*s, cy - .49*s),
    ]
    poly(draw, pts, fill, outline, max(3*K, int(.075*s)))


def cross(draw, cx, cy, s, fill=IVORY, outline=GOLD_LIGHT):
    pts = [
        (cx - .13*s, cy - s), (cx + .13*s, cy - s),
        (cx + .13*s, cy - .25*s), (cx + .64*s, cy - .25*s),
        (cx + .64*s, cy + .13*s), (cx + .13*s, cy + .13*s),
        (cx + .13*s, cy + s), (cx - .13*s, cy + s),
        (cx - .13*s, cy + .13*s), (cx - .64*s, cy + .13*s),
        (cx - .64*s, cy - .25*s), (cx - .13*s, cy - .25*s),
    ]
    poly(draw, pts, fill, outline, max(3*K, int(.08*s)))


def ornate_cross(draw, cx, cy, s):
    """A crisp blue porcelain cross with gold terminals and inset highlights."""
    blue_w = max(6*K, int(.16*s))
    gold_w = max(3*K, int(.065*s))
    draw.line((cx, cy - .72*s, cx, cy + .78*s), fill=BLUE_DARK,
              width=blue_w, joint="curve")
    draw.line((cx - .52*s, cy - .12*s, cx + .52*s, cy - .12*s),
              fill=BLUE_DARK, width=blue_w, joint="curve")
    draw.line((cx, cy - .68*s, cx, cy + .74*s), fill=GOLD,
              width=gold_w, joint="curve")
    draw.line((cx - .48*s, cy - .12*s, cx + .48*s, cy - .12*s),
              fill=GOLD, width=gold_w, joint="curve")
    r = .115*s
    for x, y in ((cx, cy-.78*s), (cx, cy+.84*s),
                 (cx-.59*s, cy-.12*s), (cx+.59*s, cy-.12*s)):
        draw.ellipse((x-r, y-r, x+r, y+r), fill=GOLD, outline=BLUE_DARK,
                     width=max(2*K, int(.035*s)))


def porcelain_sprig(draw, cx, cy, s, angle=0.0):
    """Small curved tea-set sprig, drawn large then antialiased with the atlas."""
    import math
    ca, sa = math.cos(angle), math.sin(angle)
    def at(x, y):
        return (cx + (x*ca-y*sa)*s, cy + (x*sa+y*ca)*s)
    stem = [at(-.62, .28), at(-.25, .04), at(.05, -.22), at(.58, -.36)]
    draw.line(stem, fill=BLUE, width=max(3*K, int(.075*s)), joint="curve")
    for x, y, flip in ((-.28, .02, 1), (.05, -.18, -1), (.31, -.30, 1)):
        p = at(x, y)
        q = at(x + .23, y + .20*flip)
        draw.line((p, q), fill=BLUE, width=max(3*K, int(.065*s)))
        rr = .12*s
        draw.ellipse((q[0]-rr, q[1]-rr*.62, q[0]+rr, q[1]+rr*.62), fill=BLUE)


def region(draw, box, fill):
    x0, y0, x1, y1 = (v*K for v in box)
    draw.rectangle((x0, y0, x1, y1), fill=fill)
    return x0, y0, x1, y1


def draw_cup(draw):
    x0, y0, x1, y1 = region(draw, CUP, IVORY)
    w, h = x1-x0, y1-y0
    draw.line((x0, y0 + .10*h, x1, y0 + .10*h), fill=BLUE, width=7*K)
    draw.line((x0, y0 + .16*h, x1, y0 + .16*h), fill=GOLD, width=4*K)
    # Leave the face quarter quiet; motifs repeat around the back and sides.
    # map_detail's wrapped region spans 1.25 turns; these positions place the
    # two largest motifs immediately outside the eyes on the visible front.
    for f in (.05, .25, .55, .75):
        fleur(draw, x0 + f*w, y0 + .55*h, 36*K)
    draw.line((x0, y1 - .10*h, x1, y1 - .10*h), fill=GOLD, width=4*K)


def draw_sleeve(draw):
    x0, y0, x1, y1 = region(draw, SLEEVE, IVORY)
    w, h = x1-x0, y1-y0
    # 1.25 turns of art because toy3d.map_detail(..., wrap=True) carries the seam.
    for i in range(6):
        fleur(draw, x0 + (i + .5)*w/6, y0 + .48*h, 18*K)
    draw.line((x0, y1 - .18*h, x1, y1 - .18*h), fill=BLUE, width=9*K)
    draw.line((x0, y1 - .11*h, x1, y1 - .11*h), fill=GOLD, width=4*K)


def draw_collar(draw):
    x0, y0, x1, y1 = region(draw, COLLAR, IVORY)
    w, h = x1-x0, y1-y0
    c = (x0 + .5*w, y0 + .5*h)
    draw.ellipse((x0 + .055*w, y0 + .055*h, x1 - .055*w, y1 - .055*h),
                 outline=GOLD, width=5*K)
    draw.ellipse((x0 + .34*w, y0 + .34*h, x1 - .34*w, y1 - .34*h),
                 outline=BLUE, width=4*K)
    import math
    for i in range(8):
        a = 2*math.pi*i/8
        porcelain_sprig(draw, c[0] + math.cos(a)*.31*w,
                        c[1] + math.sin(a)*.31*h, 12*K, a + math.pi/2)


def draw_mantle(draw):
    x0, y0, x1, y1 = region(draw, MANTLE, IVORY)
    w, h = x1-x0, y1-y0
    draw.line((x0, y1 - .12*h, x1, y1 - .12*h), fill=GOLD, width=5*K)
    for i in range(8):
        fleur(draw, x0 + (i + .5)*w/8, y0 + .50*h, 18*K)


def draw_robe(draw):
    x0, y0, x1, y1 = region(draw, ROBE, CREAM)
    w, h = x1-x0, y1-y0
    # The model unwrap begins at the front split, so motifs avoid both seam edges.
    draw.line((x0, y1 - .10*h, x1, y1 - .10*h), fill=GOLD, width=5*K)
    for f in (.08, .22, .38, .62, .78, .92):
        fleur(draw, x0 + f*w, y1 - .30*h, 25*K)


def draw_tabard(draw):
    x0, y0, x1, y1 = region(draw, TABARD, BLUE)
    w, h = x1-x0, y1-y0
    inset = .075*w
    draw.rectangle((x0 + inset, y0 + .025*h, x1 - inset, y1 - .025*h),
                   outline=GOLD, width=4*K)
    fleur(draw, x0 + .50*w, y0 + .70*h, min(.34*w, .11*h), IVORY, GOLD_LIGHT)


def draw_book(draw):
    x0, y0, x1, y1 = region(draw, BOOK, BLUE_DARK)
    w, h = x1-x0, y1-y0
    draw.rectangle((x0 + 9*K, y0 + 8*K, x1 - 9*K, y1 - 8*K), outline=GOLD, width=6*K)
    ornate_cross(draw, x0 + .50*w, y0 + .50*h, min(.28*w, .16*h))
    for x in (x0 + 16*K, x1 - 16*K):
        for y in (y0 + 15*K, y1 - 15*K):
            draw.ellipse((x-5*K, y-5*K, x+5*K, y+5*K), fill=GOLD)


def draw_coat(draw):
    x0, y0, x1, y1 = region(draw, COAT, IVORY)
    w, h = x1-x0, y1-y0
    draw.line((x0 + .05*w, y0, x0 + .05*w, y1), fill=GOLD, width=5*K)
    draw.line((x1 - .05*w, y0, x1 - .05*w, y1), fill=GOLD, width=5*K)
    draw.line((x0, y1 - .08*h, x1, y1 - .08*h), fill=GOLD, width=5*K)
    for f in (.18, .50, .82):
        fleur(draw, x0 + f*w, y0 + .55*h, min(.055*w, .16*h))


def draw_page(draw):
    x0, y0, x1, y1 = region(draw, PAGE, IVORY)
    w, h = x1-x0, y1-y0
    for f in (.22, .34, .46, .58, .70):
        draw.line((x0 + .16*w, y0 + f*h, x1 - .16*w, y0 + f*h), fill=(146, 101, 67), width=2*K)
    cross(draw, x0 + .50*w, y0 + .83*h, 10*K, BLUE, GOLD)


def draw_emblem(draw):
    x0, y0, x1, y1 = region(draw, EMBLEM, IVORY)
    w, h = x1-x0, y1-y0
    draw.ellipse((x0 + .055*w, y0 + .055*h, x1 - .055*w, y1 - .055*h),
                 outline=GOLD, width=7*K)
    draw.ellipse((x0 + .105*w, y0 + .105*h, x1 - .105*w, y1 - .105*h),
                 outline=BLUE, width=3*K)
    ornate_cross(draw, x0 + .5*w, y0 + .49*h, .29*min(w, h))


def main():
    img = Image.new("RGBA", (SIZE*K, SIZE*K), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for fn in (draw_cup, draw_sleeve, draw_collar, draw_mantle, draw_robe,
               draw_tabard, draw_book, draw_coat, draw_page, draw_emblem):
        fn(draw)
    img = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT)
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
