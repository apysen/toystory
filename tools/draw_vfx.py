"""Draw the battle's effect sprites as smooth vector line art (Pillow).

python tools/draw_vfx.py [name ...]  ->  assets/sprites/vfx/<name>/<name>_sheet.{png,json}

Every effect is clean vector art with an ink outline and a soft glow, drawn at 4x
and scaled down, never pixel art (the owner's rule, 2026-10-11):

  hit_spark      a strike lands: a starburst flash, its rays flying apart
  crit_burst     a critical: a bigger burst with a red ring, shards and sparks
  heal_sparkle   a heal: four-point sparkles twinkle up past a ring round the feet
  gaze_poof      the Gaze turns a unit into its object (and back): a puff of cloud
  suction_swirl  Vacuum's Suction: arms of air spiralling in to its nozzle
  cutting_line   the Paper Cutter's slash, laid in pieces along its line
  tea_lash       Teacup's dart of tea (the sprite fallback; her model bends 3D tea)
  staple_shot    a flying staple (the fallback for Stapler's 3D staples)
  toast          a tumbling slice (the fallback for the Toaster's 3D toast)
  dust_puff      floor dust kicked up as Umbrella springs into his float, or lands
  rain_streak    one falling drop of Raincheck's rain (a particle's picture)
  rain_splash    a drop of that rain landing: a little crown splash and ring

Each keeps its pixel original's frames, size and timing (the game plays them the
same), in Aseprite "hash" JSON with a frame tag, but drawn at DENSITY times the
battle's 128 px per metre, which the JSON meta "scale" says: SpriteLib.load_vfx
shows such a sheet smoothly filtered at the right size. Coordinates below are in
game pixels of the original frame (128 or 64 square, y down).
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

VFX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sprites", "vfx")
DENSITY = 4                # sheet pixels per game pixel
SS = 4                     # drawn this much bigger again, then scaled down (smooth edges)


class Frame:
    """One frame being drawn: a glow layer (blurred) under the line art, both in game
    pixels of a `px`-square frame."""

    def __init__(self, px):
        self.px = px
        self.k = DENSITY * SS
        size = px * self.k
        self.glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        self.art = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        self.g = ImageDraw.Draw(self.glow)
        self.a = ImageDraw.Draw(self.art)

    def p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def shape(self, pts, fill, ink=None, ink_w=1.0, glow=None, glow_grow=1.6):
        """A filled outline (game-px points), inked, with a soft glow under it."""
        if glow:
            cx = sum(x for x, _ in pts) / len(pts)
            cy = sum(y for _, y in pts) / len(pts)
            self.g.polygon(self.p([(cx + (x - cx) * glow_grow, cy + (y - cy) * glow_grow) for x, y in pts]),
                           fill=glow)
        if ink:
            self.a.line(self.p(pts + pts[:1]), fill=ink, width=max(1, int(ink_w * 2 * self.k)), joint="curve")
        self.a.polygon(self.p(pts), fill=fill)

    def circle(self, c, r, fill=None, ink=None, ink_w=1.0, glow=None, glow_r=1.8):
        x, y = c
        if glow:
            self.g.ellipse(self.p([(x - r * glow_r, y - r * glow_r), (x + r * glow_r, y + r * glow_r)]), fill=glow)
        if ink:
            w = ink_w
            self.a.ellipse(self.p([(x - r - w, y - r - w), (x + r + w, y + r + w)]), fill=ink)
        if fill:
            self.a.ellipse(self.p([(x - r, y - r), (x + r, y + r)]), fill=fill)

    def ring(self, c, rx, ry, width, color, glow=None, start=0, end=360):
        x, y = c
        box = self.p([(x - rx, y - ry), (x + rx, y + ry)])
        if glow:
            self.g.arc(box, start, end, fill=glow, width=max(1, int(width * 3 * self.k)))
        self.a.arc(box, start, end, fill=color, width=max(1, int(width * self.k)))

    def stroke(self, pts, width, color, ink=None, ink_w=0.8, glow=None, taper=None):
        """A line through game-px points, `width` game px wide (tapered by `taper`, a
        width at each point, when given), inked and glowing."""
        if taper:
            left, right = [], []
            for i, (x, y) in enumerate(pts):
                a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
                dx, dy = b[0] - a[0], b[1] - a[1]
                n = math.hypot(dx, dy) or 1.0
                nx, ny = -dy / n, dx / n
                w = taper[i] / 2
                left.append((x + nx * w, y + ny * w))
                right.append((x - nx * w, y - ny * w))
            outline = left + right[::-1]
            if glow:
                self.g.line(self.p(pts), fill=glow, width=max(1, int(max(taper) * 3 * self.k)), joint="curve")
            if ink:
                self.a.line(self.p(outline + outline[:1]), fill=ink, width=max(1, int(ink_w * 2 * self.k)),
                            joint="curve")
            self.a.polygon(self.p(outline), fill=color)
            return
        if glow:
            self.g.line(self.p(pts), fill=glow, width=max(1, int(width * 3 * self.k)), joint="curve")
        if ink:
            self.a.line(self.p(pts), fill=ink, width=max(1, int((width + ink_w * 2) * self.k)), joint="curve")
            for x, y in (pts[0], pts[-1]):
                r = (width / 2 + ink_w)
                self.a.ellipse(self.p([(x - r, y - r), (x + r, y + r)]), fill=ink)
        self.a.line(self.p(pts), fill=color, width=max(1, int(width * self.k)), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = width / 2
            self.a.ellipse(self.p([(x - r, y - r), (x + r, y + r)]), fill=color)

    def done(self, blur=3.0):
        glow = self.glow.filter(ImageFilter.GaussianBlur(radius=blur * self.k))
        out = Image.alpha_composite(glow, self.art)
        return out.resize((self.px * DENSITY, self.px * DENSITY), Image.LANCZOS)


def rgba(c, a=1.0):
    return tuple(c[:3]) + (max(0, min(255, int(255 * a))),)


def star(cx, cy, r, turn=0.0, points=4, sharp=3.4, n=96):
    """A sparkle with concave curved sides between its points."""
    out = []
    t = math.radians(turn)
    for i in range(n):
        a = 2 * math.pi * i / n
        if points == 4:
            c, s = math.cos(a), math.sin(a)
            x = math.copysign(abs(c) ** sharp, c)
            y = math.copysign(abs(s) ** sharp, s)
        else:
            m = abs(math.cos(points * a / 2)) ** sharp
            rr = 0.25 + 0.75 * m
            x, y = math.cos(a) * rr, math.sin(a) * rr
        out.append((cx + (x * math.cos(t) - y * math.sin(t)) * r, cy + (x * math.sin(t) + y * math.cos(t)) * r))
    return out


def spike(cx, cy, angle, r0, r1, width):
    """A tapered ray from radius r0 out to a point at r1."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    return [(cx + ux * r0 + nx * width / 2, cy + uy * r0 + ny * width / 2),
            (cx + ux * r1, cy + uy * r1),
            (cx + ux * r0 - nx * width / 2, cy + uy * r0 - ny * width / 2)]


def eased(t):
    return 1 - (1 - t) ** 2


# -- the effects ------------------------------------------------------------------------------

def hit_spark(f, n):
    """A strike lands: a small flash, a starburst, its rays flying apart into sparks."""
    INK, CORE, RAY, GLOW = (92, 52, 22), (255, 252, 238), (255, 222, 150), (255, 196, 110)
    fr = Frame(128)
    c = (64, 64)
    if f == 0:
        fr.shape(star(*c, 8, 45), rgba(CORE), rgba(INK), 0.5, glow=rgba(GLOW, 0.8), glow_grow=2.4)
    elif f == 1:
        for i in range(8):
            fr.shape(spike(*c, i * 45 + 22.5, 3, 22 if i % 2 == 0 else 13, 4.5), rgba(RAY), rgba(INK), 0.5)
        fr.circle(c, 5, rgba(CORE), rgba(INK), 0.5, glow=rgba(GLOW, 0.9), glow_r=4.0)
    else:
        t = (f - 1) / (n - 2)
        for i in range(8):
            a = math.radians(i * 45 + 22.5)
            r0, r1 = 10 + 18 * t, 22 + 18 * t
            if f == n - 1:
                fr.circle((c[0] + math.cos(a) * r1, c[1] + math.sin(a) * r1), 1.3, rgba(RAY, 0.7), glow=rgba(GLOW, 0.4))
                continue
            pts = [(c[0] + math.cos(a) * r, c[1] + math.sin(a) * r) for r in (r0, r1)]
            fr.stroke(pts, 0, rgba(RAY), rgba(INK), 0.5, glow=rgba(GLOW, 0.5), taper=[0.6, 3.0])
        fr.circle(c, 1.6, rgba(CORE, 0.8))
    return fr.done()


def crit_burst(f, n):
    """A critical: a flash, a big starburst inside a red ring, shards flung out, the
    ring breaking into dashes, sparks fading."""
    INK, CORE, RAY, RED, GLOW = (90, 22, 22), (255, 252, 240), (255, 224, 170), (232, 72, 52), (255, 140, 90)
    fr = Frame(128)
    c = (64, 64)
    if f == 0:
        fr.shape(star(*c, 10, 0), rgba(CORE), rgba(INK), 0.5, glow=rgba(GLOW, 0.9), glow_grow=2.6)
    elif f in (1, 2):
        big = f == 2
        ring_r = 24 if big else 15
        fr.ring(c, ring_r, ring_r, 3.0 if big else 2.4, rgba(RED), glow=rgba(GLOW, 0.7))
        for i in range(12):
            long = i % 2 == 0
            r1 = (46 if long else 30) if big else (30 if long else 20)
            fr.shape(spike(*c, i * 30, 4, r1, 5.0 if long else 3.5), rgba(RAY), rgba(INK), 0.5)
        fr.circle(c, 7 if big else 6, rgba(CORE), rgba(INK), 0.5, glow=rgba(GLOW, 0.9), glow_r=3.5)
        fr.circle(c, 3, rgba((255, 255, 255)))
    elif f == 3:
        for i in range(8):
            a = i * 45 + 20
            r = 34
            x, y = c[0] + math.cos(math.radians(a)) * r, c[1] + math.sin(math.radians(a)) * r
            fr.shape(spike(x, y, a, -7, 8, 4.5), rgba(RED), rgba(INK), 0.5, glow=rgba(GLOW, 0.5))
            fr.shape(spike(x, y, a, -3, 5, 2.0), rgba(RAY))
    elif f == 4:
        for i in range(12):
            a = i * 30
            fr.ring(c, 46, 46, 2.2, rgba(RED, 0.9), glow=rgba(GLOW, 0.5), start=a, end=a + 14)
        for i in range(6):
            a = math.radians(i * 60 + 15)
            fr.circle((c[0] + math.cos(a) * 54, c[1] + math.sin(a) * 54), 1.6, rgba(RAY), glow=rgba(GLOW, 0.5))
    else:
        for i in range(7):
            a = math.radians(i * 51 + 8)
            fr.circle((c[0] + math.cos(a) * 60, c[1] + math.sin(a) * 60), 1.2, rgba(RAY, 0.6), glow=rgba(GLOW, 0.3))
    return fr.done()


def heal_sparkle(f, n):
    """A heal: a ring of light spreads round the feet and fades while four-point
    sparkles twinkle up past it."""
    INK, CORE, TINT, GLOW, RING = (22, 74, 72), (255, 255, 250), (196, 255, 214), (120, 255, 170), (90, 230, 170)
    # x, base y, rise over the burst, size, the frame it's brightest at, turn
    sparkles = [(40, 82, 34, 9.0, 1.2, 0), (88, 78, 30, 7.5, 2.0, 12), (64, 70, 40, 11.0, 2.6, -8),
                (52, 96, 26, 6.0, 3.2, 20), (78, 92, 28, 8.0, 3.8, -15), (30, 66, 22, 5.5, 4.2, 5),
                (96, 62, 24, 6.5, 4.6, -10)]
    fr = Frame(128)
    t = f / (n - 1)
    fade = max(0.0, 1.0 - t * 1.15)
    if fade > 0:
        rx = 16 + 26 * t
        fr.ring((64, 104), rx, rx * 0.38, 2.2 * (1 - 0.5 * t), rgba(RING, fade), glow=rgba(GLOW, 0.6 * fade))
    for x, y, rise, size, peak, turn in sparkles:
        life = 1.0 - abs(f - peak) / 2.2
        if life <= 0:
            continue
        r = size * (0.35 + 0.65 * math.sin(life * math.pi / 2))
        cy = y - rise * t
        spin = turn + 25 * t
        fr.circle((x, cy), r * 0.9, glow=rgba(GLOW, 0.67 * life), glow_r=1.0)
        fr.a.polygon(fr.p(star(x, cy, r * 1.14, spin, sharp=3.2)), fill=rgba(INK))
        fr.a.polygon(fr.p(star(x, cy, r, spin, sharp=3.6)), fill=rgba(TINT))
        fr.a.polygon(fr.p(star(x, cy, r * 0.62, spin, sharp=3.6)), fill=rgba(CORE))
    return fr.done(blur=3.5)


def gaze_poof(f, n):
    """The Gaze's transformation: a puff of cloud swells, then breaks apart and fades."""
    INK, FILL, LIGHT, SHADE = (58, 64, 82), (206, 212, 224), (250, 252, 255), (172, 180, 198)
    fr = Frame(128)
    c = (64, 64)
    # puff offsets (unit circle) and sizes
    puffs = [(0.0, 0.0, 1.0), (-0.75, 0.25, 0.8), (0.75, 0.2, 0.85), (-0.35, -0.6, 0.75), (0.45, -0.55, 0.7),
             (0.0, 0.7, 0.7)]
    spread, size, alpha = [(4, 6, 1.0), (14, 15, 1.0), (19, 20, 1.0), (32, 12, 0.95), (44, 6, 0.7)][f]
    for i, (dx, dy, s) in enumerate(puffs if f < 3 else puffs[1:]):
        r = size * s
        x, y = c[0] + dx * spread, c[1] + dy * spread
        fr.circle((x, y), r, rgba(FILL, alpha), rgba(INK, alpha), 0.9)
        fr.circle((x + r * 0.12, y + r * 0.15), r * 0.82, rgba(SHADE, alpha))
        fr.circle((x - r * 0.08, y - r * 0.1), r * 0.8, rgba(FILL, alpha))
        fr.circle((x - r * 0.35, y - r * 0.38), r * 0.28, rgba(LIGHT, alpha))
    return fr.done()


def suction_swirl(f, n):
    """Suction: three arms of air spiralling in to a point, turning as they go, with
    motes drawn along them."""
    INK, AIR, MOTE, GLOW, CORE = (24, 70, 84), (168, 232, 246), (236, 252, 255), (120, 210, 235), (44, 128, 142)
    fr = Frame(128)
    c = (64, 64)
    turn = -f * 22
    for arm in range(3):
        base = arm * 120 + turn
        pts, widths = [], []
        for i in range(40):
            u = i / 39
            r = 56 - 48 * u
            a = math.radians(base + 260 * u)
            pts.append((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r))
            widths.append(0.6 + 3.2 * math.sin(math.pi * min(1.0, u * 1.15)))
        fr.stroke(pts, 0, rgba(AIR, 0.95), rgba(INK, 0.9), 0.5, glow=rgba(GLOW, 0.35), taper=widths)
        for m in range(3):
            u = ((m / 3) + f / 6 * 0.5) % 1.0
            r = 56 - 48 * u
            a = math.radians(base + 260 * u + 14)
            fr.circle((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r), 1.4, rgba(MOTE), glow=rgba(GLOW, 0.4))
    fr.circle(c, 5, rgba(CORE), rgba(INK), 0.8, glow=rgba(GLOW, 0.6), glow_r=2.5)
    fr.circle((c[0] - 1.5, c[1] - 1.5), 1.6, rgba(MOTE))
    return fr.done()


def cutting_line(f, n):
    """A piece of the Paper Cutter's slash across the frame: a thin line, a bright
    cut, glinting, then fading to a dashed trace."""
    INK, CUT, EDGE, GLOW = (30, 56, 78), (250, 254, 255), (176, 236, 255), (120, 210, 255)
    fr = Frame(128)
    y = 64
    if f == 0:
        fr.stroke([(0, y), (128, y)], 1.2, rgba(EDGE, 0.75))
    elif f == 1:
        fr.stroke([(0, y), (128, y)], 4.0, rgba(EDGE), rgba(INK), 0.5, glow=rgba(GLOW, 0.8))
        fr.stroke([(0, y), (128, y)], 1.6, rgba(CUT))
    elif f == 2:
        fr.stroke([(0, y), (128, y)], 2.0, rgba(CUT), rgba(INK), 0.4, glow=rgba(GLOW, 0.5))
        for x, dy, s in ((24, -9, 3.0), (60, 8, 2.4), (92, -8, 3.2), (112, 9, 2.0)):
            fr.a.polygon(fr.p(star(x, y + dy, s, 0, sharp=3.2)), fill=rgba(CUT))
    else:
        for x0 in range(0, 128, 12):
            fr.stroke([(x0 + 1, y), (x0 + 7, y)], 1.2, rgba(EDGE, 0.55))
    return fr.done(blur=2.5)


def tea_lash(f, n):
    """Teacup's dart of tea (looping, flying): a curl of her tea snapping out, with
    drops, in her tea's own brown and its crest's tan."""
    INK, TEA, CREST, GLOW = (66, 32, 12), (165, 82, 37), (201, 137, 89), (200, 130, 80)
    fr = Frame(128)
    curls = [
        [(52, 92), (60, 86), (70, 90)],
        [(52, 104), (60, 92), (66, 80), (64, 68), (58, 60)],
        [(62, 108), (66, 94), (64, 80), (60, 66), (62, 56), (70, 54), (72, 62), (66, 64)],
        [(58, 96), (62, 84), (60, 72), (62, 62), (68, 58)],
        [(60, 82), (66, 76), (72, 74)],
    ]
    pts = curls[f]
    widths = [1.0 + 5.0 * math.sin(math.pi * (0.15 + 0.7 * i / max(1, len(pts) - 1))) for i in range(len(pts))]
    fr.stroke(pts, 0, rgba(TEA), rgba(INK), 0.7, glow=rgba(GLOW, 0.25), taper=widths)
    fr.stroke(pts[1:-1] if len(pts) > 3 else pts, 1.0, rgba(CREST))
    drops = {1: [(48, 84, 2.4), (74, 88, 2.0)], 2: [(48, 80, 2.6), (78, 86, 2.2), (54, 96, 1.6)],
             3: [(50, 70, 2.2), (72, 80, 2.4), (54, 104, 1.8)], 4: [(54, 92, 1.8), (76, 84, 1.6)]}
    for x, y, r in drops.get(f, []):
        fr.circle((x, y), r, rgba(TEA), rgba(INK), 0.6)
    return fr.done(blur=2.0)


def staple_shot(f, n):
    """A staple flying right with speed lines behind it; a glint on the middle frame."""
    INK, STEEL, LIGHT, LINES = (36, 42, 58), (176, 186, 204), (236, 242, 250), (236, 240, 248)
    fr = Frame(64)
    shift = (0, 3, 1)[f]
    for y, x0, x1 in ((27, 6, 31), (32, 2 + shift, 31), (37, 8 - shift, 31)):
        fr.stroke([(x0, y), (x1, y)], 1.2, rgba(LINES, 0.7))
    # the staple, flying legs first: its crown behind, its legs pointing ahead
    bracket = [(34, 24), (46, 24), (46, 27), (37, 27), (37, 37), (46, 37), (46, 40), (34, 40)]
    fr.shape(bracket, rgba(STEEL), rgba(INK), 0.7)
    fr.stroke([(35.5, 25.5), (45, 25.5)], 0.9, rgba(LIGHT))
    if f == 1:
        fr.a.polygon(fr.p(star(48, 22, 4.0, 0, sharp=3.4)), fill=rgba(LIGHT))
    return fr.done(blur=1.5)


def toast(f, n):
    """A tumbling slice of toast, a quarter turn a frame."""
    INK, CRUST, CRUMB, BROWN = (70, 38, 18), (164, 98, 52), (242, 222, 182), (210, 156, 96)
    fr = Frame(64)
    c = (32, 32)
    turn = math.radians(90 * f)
    # a slice: square-ish with a domed top
    outline = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        x, y = math.cos(a), math.sin(a)
        rx, ry = 12.0, 14.0
        sx = math.copysign(abs(x) ** 0.45, x) * rx
        sy = math.copysign(abs(y) ** 0.45, y) * ry
        if y < 0:
            sx *= 1.0 + 0.12 * abs(y)
        outline.append((sx, sy))

    def place(pts, k=1.0):
        return [(c[0] + (x * math.cos(turn) - y * math.sin(turn)) * k,
                 c[1] + (x * math.sin(turn) + y * math.cos(turn)) * k) for x, y in pts]

    fr.shape(place(outline), rgba(CRUST), rgba(INK), 0.7)
    fr.a.polygon(fr.p(place(outline, 0.78)), fill=rgba(CRUMB))
    fr.circle(c, 5.0, rgba(BROWN))
    return fr.done(blur=1.5)


def dust_puff(f, n):
    """Floor dust kicked out sideways from under a jump or a landing: low puffs
    rolling out both ways along the floor, thinning as they go."""
    INK, FILL, LIGHT = (96, 84, 70), (214, 202, 182), (240, 232, 216)
    fr = Frame(128)
    floor = 92
    spread, size, alpha = [(6, 7, 0.95), (16, 10, 0.95), (26, 11, 0.85), (36, 10, 0.6), (44, 8, 0.3)][f]
    for side in (-1, 1):
        for k, (d, s, up) in enumerate(((0.55, 0.8, 0.0), (1.0, 1.0, 0.2), (1.35, 0.7, 0.1))):
            r = size * s
            x, y = 64 + side * spread * d, floor - r * 0.7 - up * size
            fr.circle((x, y), r, rgba(FILL, alpha), rgba(INK, alpha * 0.8), 0.8)
            fr.circle((x - side * r * 0.25, y - r * 0.3), r * 0.4, rgba(LIGHT, alpha))
    return fr.done(blur=1.5)


def rain_streak(f, n):
    """One falling drop: a slim tapered streak of pale blue with a bright head."""
    INK, WATER, GLOW = (60, 98, 140), (170, 214, 250), (150, 200, 255)
    fr = Frame(32)
    fr.stroke([(16, 3), (16, 27)], 2.0, rgba(WATER, 0.9), ink=rgba(INK, 0.6), ink_w=0.4, glow=rgba(GLOW, 0.35),
              taper=[0.3, 2.4])
    fr.circle((16, 27), 1.3, rgba((235, 246, 255), 1.0))
    return fr.done(blur=1.0)


def rain_splash(f, n):
    """A drop landing: a crown of droplets thrown up and a ring spreading out."""
    INK, WATER, LIGHT = (60, 98, 140), (170, 214, 250), (235, 246, 255)
    fr = Frame(64)
    t = (f + 1) / n
    a = 1.0 - 0.75 * t
    fr.ring((32, 46), 6 + 16 * t, 2 + 4 * t, 1.6, rgba(WATER, a), glow=rgba(WATER, 0.25 * a))
    for k in range(5):
        ang = math.radians(-160 + 35 * k)
        h = 14 * math.sin(math.pi * min(1.0, t * 1.3))
        x = 32 + math.cos(ang) * (4 + 10 * t)
        y = 46 - h * (0.6 + 0.4 * abs(math.sin(ang)))
        fr.circle((x, y), 1.6 * (1 - 0.4 * t), rgba(LIGHT, a), rgba(INK, a * 0.6), 0.4)
    return fr.done(blur=1.0)


EFFECTS = {
    "hit_spark": (hit_spark, 4, 128, 80), "crit_burst": (crit_burst, 6, 128, 80),
    "heal_sparkle": (heal_sparkle, 6, 128, 100), "gaze_poof": (gaze_poof, 5, 128, 80),
    "suction_swirl": (suction_swirl, 6, 128, 80), "cutting_line": (cutting_line, 4, 128, 80),
    "tea_lash": (tea_lash, 5, 128, 100), "staple_shot": (staple_shot, 3, 64, 80), "toast": (toast, 4, 64, 80),
    "dust_puff": (dust_puff, 5, 128, 80), "rain_streak": (rain_streak, 1, 32, 100),
    "rain_splash": (rain_splash, 4, 64, 70),
}


def write(name):
    draw, count, px, ms = EFFECTS[name]
    size = px * DENSITY
    out = os.path.join(VFX, name)
    os.makedirs(out, exist_ok=True)
    sheet = Image.new("RGBA", (size * count, size), (0, 0, 0, 0))
    frames = {}
    for f in range(count):
        sheet.paste(draw(f, count), (f * size, 0))
        frames[f"{name} {f}"] = {
            "frame": {"x": f * size, "y": 0, "w": size, "h": size}, "rotated": False, "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": size, "h": size}, "sourceSize": {"w": size, "h": size},
            "duration": ms,
        }
    sheet.save(os.path.join(out, name + "_sheet.png"))
    meta = {"app": "tools/draw_vfx.py", "image": name + "_sheet.png", "format": "RGBA8888",
            "size": {"w": size * count, "h": size}, "scale": str(DENSITY),
            "frameTags": [{"name": name, "from": 0, "to": count - 1, "direction": "forward"}]}
    with open(os.path.join(out, name + "_sheet.json"), "w", encoding="utf-8") as fh:
        json.dump({"frames": frames, "meta": meta}, fh, indent=1)
    return os.path.join(out, name + "_sheet.png")


if __name__ == "__main__":
    for nm in sys.argv[1:] or list(EFFECTS):
        print("wrote", write(nm))
