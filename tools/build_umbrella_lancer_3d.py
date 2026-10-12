"""Build the 3D Umbrella Lancer (Blender).

Live, through the Blender MCP:   exec(open("tools/build_umbrella_lancer_3d.py").read())  then  build_umbrella()
Headless:  D:/Blender/blender.exe --background --python tools/build_umbrella_lancer_3d.py

Heights and stance come off the 128 px idle frame (player/umbrella/umbrella_sheet.png,
foot pivot 58,114); the look follows the concept (assets/concept/player/umbrella.png),
with the shared machinery in tools/toy3d.py. Same rules as the other toys: one mesh
and one palette material, every part a closed solid on its own bone, cloth with even
rows, sway weights and bone chains, line art on a detail atlas
(tools/draw_umbrella_details.py, run it first), nothing floating or clipping.

The lancer, from the concept (he faces screen-right there, so his right side is
toward the viewer: the fist is his right, the lance his left):
  - hat: an open umbrella worn as a wide conical hat, teal and cream panels, gold
    ribs with a gold drop at each rib's end (each on its own bone, hat_tip_0..7,
    for the game's spring bones), a gold cross finial on top, its shaft standing
    on his head
  - a blank cream face with two dark eye slits, a teal scarf wrapped round the neck
  - silver plate with gold trim; a teal tabard with a cream lion rampant and a gold
    fleur-de-lis (line art), a brown belt with a round gold buckle
  - teal pauldrons with a gold fleur on both shoulders (the owner's note)
  - a teal skirt under the tabard, a teal cape, the same inside and out, a gold hem
    and fleurs
  - plate legs with gold knee cops and gold-trimmed sabatons
  - the lance: a furled umbrella held in his left hand, teal and cream panels
    gathered round its shaft, a gold guard at the grip, a gold ferrule and spike.
    Its ribs are bones (rib_0..7, hinged at the ferrule, children of the lance
    bone), so clips can spring it open into a canopy (travel, Canopy, Raincheck).
    The lance bone hangs off the root; the clips hold it in his left fist.
Built with both arms hanging alike at his sides, fists closed (the left mirrors the
right exactly, the owner's pick), the lance slotted into the left fist along its grip.

Writes assets/models/umbrella/umbrella_lancer.glb; the .blend and previews go in
assets/models/umbrella/source/ (Godot-ignored).
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

try:
    _TOOLS = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _TOOLS = os.path.join(os.getcwd(), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
sys.dont_write_bytecode = True   # no __pycache__ in tools/ (check_structure)
import toy3d  # noqa: E402
importlib.reload(toy3d)
from toy3d import (S, P, H, Builder, frame, vprof, smoothstep, chain_weights, hash01,  # noqa: E402
                   grid_normals, cloth, build_hand, grip_frame)

# name, hex, emissive: the sprite's eight colours and the shades between them
PALETTE = [
    ("outline", "08080a", False), ("teal", "246a72", False),
    ("teal_dark", "0e3e50", False), ("teal_light", "3a8a90", False),
    ("cream", "fae8c0", False), ("cream_shade", "d8c8a0", False),
    ("steel_light", "d6cec0", False), ("steel", "92867c", False),
    ("steel_dark", "5e564e", False), ("gold", "fab83c", False),
    ("gold_dark", "b0701e", False), ("brown", "704026", False),
    ("brown_dark", "4a2a1a", False), ("black", "1c1a1e", False),
    ("unused0", "ff00ff", False), ("unused1", "ff00ff", False),
]

CX = 58          # the body's centre line, px (the sprite's foot pivot)
GROUND = 114


def body_weights(z):
    """Body and everything worn on it blend hips -> spine -> chest up the body."""
    py = GROUND - z / S
    if py >= 72:
        return [("hips", 1.0)]
    if py >= 64:
        t = (72 - py) / 8
        return [("hips", 1 - t), ("spine", t)]
    if py >= 56:
        t = (64 - py) / 8
        return [("spine", 1 - t), ("chest", t)]
    return [("chest", 1.0)]


ARMS = ("upperarm_R", "upperarm_L", "forearm_R", "forearm_L", "hand_R", "hand_L")
LEGS = ("thigh_R", "thigh_L", "shin_R", "shin_L", "foot_R", "foot_L")
LANCE = ("lance", "canopy")
CLIP_CHECKS = (
    [("head", "scarf"), ("hat", "cape"), ("hat", "scarf"), ("cape", "skirt"), ("tabard", "skirt"),
     ("tabard", "torso"), ("cape", "torso"), ("cape", "belt")]
    + [(a, c) for a in ARMS[2:] for c in ("cape", "skirt", "tabard", "belt", "torso")]
    + [(a, c) for a in ("upperarm_R", "upperarm_L") for c in ("cape", "belt", "tabard")]
    + [(a, c) for a in LEGS[2:] for c in ("cape", "skirt", "tabard")]
    + [(a, c) for a in LANCE for c in LEGS + ("skirt", "tabard", "cape", "belt", "torso", "forearm_R", "hand_R")]
    + [("canopy", "hand_L"), ("canopy", "forearm_L")]
    # the umbrella clear of his hat (only an attack or Art swinging it to the front may
    # pass through, the owner's allowance)
    + [("lance", "hat"), ("canopy", "hat")]
    # (The cape's top tucks into the scarf wrap at the neck and under both pauldrons;
    # the left hand closes on the lance's shaft by design; the thighs and hip
    # joints sit up inside the skirt; the skirt's and tabard's tops tuck under the
    # belt, which sits snug on them; each shoulder
    # ball sits in its pauldron.)
)

CHAR = toy3d.Character(
    name="umbrella_lancer", folder="umbrella", object_name="UmbrellaLancer", pivot=(CX, GROUND),
    palette=PALETTE,
    part_bone={"torso": "body", "belt": "body", "tabard": "body", "skirt": "body", "cape": "body",
               "scarf": "chest", "neck": "chest", "hat": "head", "pauldron_R": "upperarm_R",
               "pauldron_L": "upperarm_L", "canopy": "lance"},
    body_weights=body_weights, clip_checks=CLIP_CHECKS,
    detail=os.path.join(toy3d.ROOT, "assets", "models", "umbrella", "source", "umbrella_details.png"))
# the line art's regions in that atlas (draw_umbrella_details.TABARD, CAPE, PAULDRON)
DETAIL_TABARD = (256, 0, 448, 544)
DETAIL_CAPE = (448, 0, 1024, 512)
DETAIL_PAULDRON = (0, 256, 256, 512)
toy3d.configure(CHAR)

# shoulder, elbow and grip of each arm: the right fist hangs at his side, closed on a
# 0.5 px bar running forward and a little up; the left arm is the right mirrored
# exactly (the owner's pick), and the lance is slotted into its fist along that bar
ARM_R = (P(CX - 13, 51, 0.0), P(CX - 18.5, 61.5, 0.012), P(CX - 21, 72, -0.004))
ARM_L = tuple(Vector((-p.x + 2 * P(CX, 0).x, p.y, p.z)) for p in ARM_R)
FIST_AXIS = Vector((0.0, -1.0, 0.15)).normalized()
FIST_BAR = 0.5                                           # px: the bar the fists close on
LANCE_DIR = FIST_AXIS                                    # through the left fist
# hip, knee, ankle, toe direction
LEG_R = (P(CX - 5.5, 80), P(CX - 7.5, 93, -0.016), P(CX - 9, 107, -0.004), (-0.3, -0.95, 0))
LEG_L = (P(CX + 5.5, 80), P(CX + 7.5, 93, -0.016), P(CX + 9, 107, -0.004), (0.3, -0.95, 0))

TORSO_SY = 0.72
TORSO_PROF = [(0, 84), (9.5, 84), (10, 76), (9.6, 66), (11.2, 58), (12, 54), (10.5, 50.5), (6, 48.5), (0, 48)]
BELT_TOP, BELT_BOTTOM = 61.5, 65.5
NECK_PY = 48.0
HEAD_C = P(CX, 40.5, 0.0)
HEAD_R = (6.4, 6.0, 7.0)          # px: across, front to back, up
# the eye slits: px either side of the face's middle and above the head's centre;
# width and height (px), thickness, and how far the front stands off the face (px)
EYE_APART, EYE_HEIGHT = 2.1, -1.2      # (low enough to show under the brim)
EYE_SIZE = (0.9, 3.0)
EYE_TH, EYE_PROUD = 0.5, 0.15


def interp(prof, py):
    """Linear interpolation in a [(py, value)] table sorted by py."""
    if py <= prof[0][0]:
        return prof[0][1]
    for (y0, v0), (y1, v1) in zip(prof, prof[1:]):
        if py <= y1:
            return v0 + (v1 - v0) * (py - y0) / (y1 - y0)
    return prof[-1][1]


def clamp01(x):
    """Keep an atlas lookup inside its region (just inside its edge)."""
    return max(0.01, min(0.99, x))


def ring_pt(c, r_px, a, sy, py):
    return Vector((c.x + r_px * S * math.cos(a), c.y + r_px * S * math.sin(a) * sy, H(py)))


def outward_from(axis_x, axis_y):
    return lambda p: Vector((p.x - axis_x, p.y - axis_y, 0.0))


def torso_r(py):
    pts = sorted(TORSO_PROF[1:-1], key=lambda q: q[1])
    for (r0, y0), (r1, y1) in zip(pts, pts[1:]):
        if y0 <= py <= y1:
            return r0 + (r1 - r0) * (py - y0) / (y1 - y0)
    return pts[0][0] if py < pts[0][1] else pts[-1][0]


# -- body --------------------------------------------------------------------------------

def build_torso(b):
    """The breastplate above the belt, the padded black gambeson below it (under the
    skirt), the belt and its round gold buckle (no hanging strap, the owner's pick)."""
    verts, bands, _ = b.lathe(vprof(TORSO_PROF), 16, Matrix.Translation(P(CX, GROUND)), sy=TORSO_SY)
    faces = b.finish(verts, "steel_light", "torso")
    b.paint([f for f in faces if f.calc_center_median().z < H(BELT_BOTTOM)], "black")
    b.joints["root"] = (Vector((0, 0, 0)), Vector((0, -0.12, 0)), None)
    b.joints["hips"] = (P(CX, 80), P(CX, 66), "root")
    b.joints["spine"] = (P(CX, 66), P(CX, 57), "hips")
    b.joints["chest"] = (P(CX, 57), P(CX, NECK_PY), "spine")
    # (over the tabard and the skirt's top, which tuck under it)
    belt = [(torso_r(BELT_BOTTOM) + 3.0, BELT_BOTTOM), (torso_r(BELT_TOP) + 3.0, BELT_TOP),
            (torso_r(BELT_TOP) + 0.9, BELT_TOP), (torso_r(BELT_BOTTOM) + 0.9, BELT_BOTTOM)]
    b.finish(b.lathe(vprof(belt), 28, Matrix.Translation(P(CX, GROUND)), sy=TORSO_SY, loop=True)[0],
             "brown", "belt", smooth=False)
    mid = (BELT_TOP + BELT_BOTTOM) / 2
    r = torso_r(mid) + 3.0
    front = P(CX, mid, -TORSO_SY * r * S)
    b.finish(b.ring(front, Vector((0, -1, 0)), 1.0 * S, 2.6 * S, 1.2 * S, 12), "gold", "belt", smooth=False)
    b.finish(b.sphere(front, 1.1 * S, 8, 4), "gold_dark", "belt")


SKIRT_TOP, SKIRT_HEM = BELT_BOTTOM - 1.0, 88.0


def skirt_r(py):
    return interp([(SKIRT_TOP, torso_r(SKIRT_TOP) + 0.3), (70, 11.6), (80, 13.6), (SKIRT_HEM, 15.2),
                   (SKIRT_HEM + 6, 16.0)], py)


def build_skirt(b):
    """A teal skirt (the gambeson's tails) from under the belt to just above the knees,
    a cream lining; near the thighs it follows them, so a stride swings it."""
    rows, cols = 9, 32
    pys = [SKIRT_TOP + (SKIRT_HEM - SKIRT_TOP) * j / (rows - 1) for j in range(rows)]
    mids = []
    for j, py in enumerate(pys):
        t = j / (rows - 1)
        row = []
        for i in range(cols + 1):
            a = math.radians(-90 + 360 * i / cols)
            fold = 0.5 * t * math.sin(6 * a)
            row.append(ring_pt(P(CX, GROUND), skirt_r(py) + fold, a, TORSO_SY + 0.06 * t, py))
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(P(CX, 0).x, 0.0))
    verts, fronts, backs = cloth(b, mids, norms, 0.6 * S)
    faces = b.finish(verts, "teal", "skirt", smooth=False)
    b.paint(list(backs.values()), "cream")
    b.set_sway(faces, H(BELT_BOTTOM), H(SKIRT_HEM))
    return verts


TABARD_X = [-7.5, -5.5, -3.0, -1.0, 1.0, 3.0, 5.5, 7.5]
TABARD_TOP, TABARD_HEM = 49.5, 96.0


def tabard_depth(x, py, lift):
    """Front surface (y, m) under the tabard at column x px off centre, row py: the
    torso above the belt; below it the skirt's real front, with its flare toward the
    hem and the crest of its folds (0.5 px) and half its thickness, so the tabard lies
    on it rather than in it."""
    if py < SKIRT_TOP:
        r, sy = torso_r(py) + lift, TORSO_SY
    else:
        t = max(0.0, min(1.0, (py - SKIRT_TOP) / (SKIRT_HEM - SKIRT_TOP)))
        r = max(torso_r(py), skirt_r(min(py, SKIRT_HEM)) + 0.5 * t + 0.3) + lift
        sy = TORSO_SY + 0.06 * t
    dx = min(abs(x), r * 0.95)
    return -sy * math.sqrt(r * r - dx * dx) * S


def build_tabard(b):
    """The teal tabard down his front from the collar, under the belt, hanging free
    past the skirt to a point; the lion, fleur and gold border are line art. Above
    the belt it rides the chest; below, a two-bone chain."""
    # rows close together over the rounded top of his chest (wider apart, the flat strips
    # between them cut into it), one on its fullest row (54), then evenly down to the hem
    ys = [TABARD_TOP + 0.5 * k for k in range(7)] + [53.25, 54.0] + [54.0 + (TABARD_HEM - 54.0) * k / 16 for k in range(1, 17)]
    bm = b.bm

    def at(x, py, lift):
        taper = max(0.05, min(1.0, (TABARD_HEM - py) / 6.0))        # pointed bottom
        w = 1.0 + 0.12 * smoothstep((py - BELT_BOTTOM) / 20)          # a little wider below the belt
        xx = x * taper * w
        return P(CX + xx, py, tabard_depth(xx, py, lift))
    F = [[bm.verts.new(at(x, py, 1.0)) for x in TABARD_X] for py in ys]
    B = [[bm.verts.new(at(x, py, 0.55)) for x in TABARD_X] for py in ys]
    fronts, backs = [], []
    for j in range(len(ys) - 1):
        for i in range(len(TABARD_X) - 1):
            fronts.append(bm.faces.new((F[j][i], F[j][i + 1], F[j + 1][i + 1], F[j + 1][i])))
            backs.append(bm.faces.new((B[j][i], B[j + 1][i], B[j + 1][i + 1], B[j][i + 1])))
    for j in range(len(ys) - 1):
        for i in (0, len(TABARD_X) - 1):
            bm.faces.new((F[j][i], F[j + 1][i], B[j + 1][i], B[j][i]))
    for i in range(len(TABARD_X) - 1):
        for j in (0, len(ys) - 1):
            bm.faces.new((F[j][i], B[j][i], B[j][i + 1], F[j][i + 1]))
    flat = {F[j][i]: ((x + 7.5) / 15.0, (py - TABARD_TOP) / (TABARD_HEM - TABARD_TOP))
            for j, py in enumerate(ys) for i, x in enumerate(TABARD_X)}
    faces = b.finish([v for row in F + B for v in row], "teal", "tabard", smooth=False)
    b.paint(backs, "teal_dark")
    at_corner = {tuple(round(c, 6) for c in v.co): uv for v, uv in flat.items()}
    b.map_detail(fronts, DETAIL_TABARD, lambda co: at_corner[tuple(round(c, 6) for c in co)])
    b.set_sway(faces, H(BELT_BOTTOM + 1), H(TABARD_HEM))
    b.joints["tabard_1"] = (at(0, BELT_BOTTOM + 1.5, 1.0), at(0, 81, 1.0), "hips")
    b.joints["tabard_2"] = (at(0, 81, 1.0), at(0, TABARD_HEM, 1.0), "tabard_1")
    below = [v for row in F + B for v in row if v.co.z < H(BELT_BOTTOM + 1)]
    chain_weights(b, below, H(BELT_BOTTOM + 1), H(BELT_BOTTOM + 1) - H(TABARD_HEM),
                  (("hips", 0.0), ("tabard_1", 0.38), ("tabard_2", 0.85)), 0.36)


CAPE_HUG = (66.0, 2.0, 0.06)    # row (px) it starts to flare from, px its middle stands off the body
                                 # (half its thickness and a gap), px it flares out per row below that


def cape_body_depth(py):
    """How far (px) behind his centre line the body is at row py: the back, the belt
    round it and the skirt below it."""
    d = TORSO_SY * torso_r(py)
    if BELT_TOP - 0.5 <= py <= BELT_BOTTOM + 0.5:
        d = max(d, TORSO_SY * (torso_r(py) + 3.0))
    if py >= SKIRT_TOP:
        t = max(0.0, min(1.0, (py - SKIRT_TOP) / (SKIRT_HEM - SKIRT_TOP)))
        d = max(d, (TORSO_SY + 0.06 * t) * (skirt_r(min(py, SKIRT_HEM)) + 0.5 * t) + 0.3)
    return d


def build_cape(b):
    """A teal cape from the shoulders behind the arms, teal inside too, flaring to a torn
    hem with long points; the gold hem band and fleurs are line art. Even rows, a
    sway weight and a three-bone chain."""
    rows, cols = 15, 26
    top_py, hem_py = 48.0, 97.0
    prof = [(48.0, 6.6), (52, 12.4), (57, 16.0), (68, 18.0), (82, 21.5), (97, 25.0), (104, 26.0)]   # its top in the scarf wrap's ring

    def span(t):
        return math.radians(28 - 30 * t), math.radians(152 + 30 * t)
    centre = P(CX, GROUND, 0.02)
    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        py = top_py + (hem_py - top_py) * t
        a0, a1 = span(t)
        row = []
        for i in range(cols + 1):
            a = a0 + (a1 - a0) * i / cols
            q = py
            if j == rows - 1:
                q += (5.0 * hash01(i + 11) if i % 2 == 0 else 0.5) + 2.0 * (i / cols)   # torn points, longer on his left
            fold = 2.6 * t * math.sin(6 * a + 0.5)
            # its top edge runs round the scarf wrap's own ring (the wrap's axis and
            # depth scale), tucked inside the wrap; lower down it hangs from the
            # shoulders round its own axis, a little behind
            k_top = smoothstep(1 - t / 0.25)
            c = Vector((centre.x, centre.y * (1 - k_top) + 0.004 * k_top, centre.z))
            p = ring_pt(c, interp(prof, q) + fold, a, 0.9 * (1 - k_top) + 0.86 * k_top, q)
            p.y += 0.035 * t * t * max(0.0, math.sin(a))
            # across his back it lies on him (the shoulder blades, the back, the belt,
            # the skirt) rather than standing off in a shell, then hangs almost straight
            # down past the skirt's hem, flaring only a little toward its own; the
            # sides over the pauldrons keep their sweep (from the shoulders' slope
            # down: above it the top tucks into the scarf wrap)
            hug = math.sin(a) ** 2 * smoothstep((q - 51.0) / 4.0)
            depth = cape_body_depth(min(q, SKIRT_HEM)) + CAPE_HUG[1] + CAPE_HUG[2] * max(0.0, q - CAPE_HUG[0])
            on_back = depth * S * max(0.0, math.sin(a))
            p.y -= hug * max(0.0, p.y - on_back)
            row.append(p)
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre.x, centre.y))
    verts, fronts, backs = cloth(b, mids, norms, 1.1 * S)
    faces = b.finish(verts, "teal", "cape", smooth=False)

    # its art by the cloth's own grid: each corner's column and row, on the outside and
    # on the inside alike (the owner's pick: the same teal, gold hem and fleurs both sides)
    grid = {}
    for j in range(rows):
        for i in range(cols + 1):
            for side in (1, -1):
                p = mids[j][i] + side * norms[j][i] * 1.1 * S / 2
                grid[tuple(round(c, 5) for c in p)] = (i / cols, j / (rows - 1))
    b.map_detail([f for fs in fronts.values() for f in fs] + list(backs.values()), DETAIL_CAPE,
                 lambda co: grid[tuple(round(c, 5) for c in co)])
    b.set_sway(faces, H(top_py), H(hem_py))
    c = cols // 2
    # (the first link pivots at its top edge, so swinging back lifts all of it off his back)
    js = [mids[min(rows - 1, round((py - top_py) / (hem_py - top_py) * (rows - 1)))][c] for py in (48, 68, 84, 97)]
    for i in range(3):
        b.joints[f"cape_{i + 1}"] = (js[i], js[i + 1], "chest" if i == 0 else f"cape_{i}")
    chain_weights(b, verts, H(top_py), H(top_py) - H(hem_py),
                  (("chest", -0.08), ("cape_1", 0.2), ("cape_2", 0.55), ("cape_3", 0.9)), 0.35)


# -- head, scarf and hat ---------------------------------------------------------------------

def build_head(b):
    """A blank cream face with two dark eye slits, on a short steel neck. Each slit is
    a thin plate set on the face's curve, standing just clear of it (no coplanar
    faces), not a block poking out."""
    rx, ry, rz = HEAD_R
    b.finish(b.sphere(HEAD_C, 1.0, 16, 10, (rx * S, ry * S, rz * S)), "cream", "head")
    for side in (-1, 1):
        x, z = side * EYE_APART * S, EYE_HEIGHT * S
        # the face's surface under the eye, and its normal there
        k = 1 - (x / (rx * S)) ** 2 - (z / (rz * S)) ** 2
        y = -ry * S * math.sqrt(max(k, 0.0))
        n = Vector((x / (rx * S) ** 2, y / (ry * S) ** 2, z / (rz * S) ** 2)).normalized()
        c = HEAD_C + Vector((x, y, z)) + n * (EYE_PROUD * S - EYE_TH * S / 2)
        b.finish(b.box(c, (EYE_SIZE[0] * S, EYE_SIZE[1] * S, EYE_TH * S), xdir=Vector((1, 0, 0)), zdir=n),
                 "outline", "head", smooth=False)
    b.finish(b.tube([HEAD_C - Vector((0, 0, rz * S * 0.6)), P(CX, NECK_PY + 3.5)], 2.6 * S, 8), "steel_dark",
             "neck")
    b.joints["head"] = (P(CX, NECK_PY), P(CX, 26), "chest")


def build_scarf(b):
    """A teal scarf wrapped round the neck, the green of the rest of his livery (the
    owner's pick; its hanging end taken off)."""
    c = P(CX, NECK_PY, 0.004)
    prof = [(7.0 + 2.1 * math.cos(t), NECK_PY - 0.85 * 2.1 * math.sin(t)) for t in (2 * math.pi * k / 10 for k in range(10))]
    verts = b.lathe(vprof(prof), 18, Matrix.Translation(Vector((c.x, c.y, 0))), sy=0.86, loop=True,
                    warp=lambda p, a: Vector((p.x * (1 + 0.04 * math.sin(3 * a)), p.y * (1 + 0.04 * math.sin(3 * a)), p.z)))[0]
    b.finish(verts, "teal", "scarf", smooth=False)


HAT_PROF = [(0.0, 24.0), (7.0, 27.4), (15.0, 31.0), (23.0, 34.3), (31.0, 37.4)]   # (r px, row): apex to brim
HAT_RIBS = 8


def hat_rim(a):
    """Row of the hat's rim at angle a: it arcs up between the rib tips."""
    k = abs(math.cos(HAT_RIBS * a / 2))
    return HAT_PROF[-1][1] - 1.6 * (1 - k)


def build_hat(b):
    """An open umbrella worn as a hat: teal and cream panels, gold ribs, a gold drop
    on its own bone at each rib's end, a gold cross finial, and the umbrella's shaft
    standing on his head."""
    c = P(CX, GROUND, 0.0)
    segs = HAT_RIBS * 4
    outer = [(r, row) for r, row in HAT_PROF]
    inner = [(r, row + 1.0) for r, row in reversed(HAT_PROF)]

    def scallop(p, a):
        r = math.hypot(p.x, p.y / 1.0) / S
        if r > 2.0:
            t = r / HAT_PROF[-1][0]
            p.z += (HAT_PROF[-1][1] - hat_rim(a)) * S * t ** 3
        return p
    verts, bands, _ = b.lathe(vprof(outer + inner), segs, Matrix.Translation(Vector((c.x, c.y, 0))), loop=True,
                              warp=scallop)
    faces = b.finish(verts, "teal", "hat", smooth=False)
    n_out = len(outer) - 1
    for k, band in enumerate(bands):
        for i, f in enumerate(band):
            if k < n_out:
                if (i // 4) % 2:
                    b.paint([f], "cream")
            else:
                b.paint([f], "teal_dark")                    # its underside
    apex = P(CX, HAT_PROF[0][1])
    # the shaft from his crown up to the apex, inside the hat
    b.finish(b.tube([HEAD_C + Vector((0, 0, (HEAD_R[2] - 1.0) * S)), apex - Vector((0, 0, 0.5 * S))], 1.3 * S, 8),
             "steel_dark", "hat")
    for i in range(HAT_RIBS):
        a = 2 * math.pi * i / HAT_RIBS
        pts = []
        for r, row in HAT_PROF[1:]:
            q = row - 0.35 - (HAT_PROF[-1][1] - hat_rim(a)) * (r / HAT_PROF[-1][0]) ** 3 * 0.0
            pts.append(ring_pt(c, r, a, 1.0, q))
        b.finish(b.tube(pts, 0.55 * S, 5), "gold", "hat")
        end = ring_pt(c, HAT_PROF[-1][0] - 0.2, a, 1.0, HAT_PROF[-1][1] + 0.2)   # seated in the rim at the rib's end
        bone = f"hat_tip_{i}"
        drop = end + Vector((0, 0, -2.6 * S))
        b.finish(b.tube([end + Vector((0, 0, 1.3 * S)), drop], 0.45 * S, 5), "gold", bone)
        b.finish(b.sphere(drop, 1.25 * S, 8, 5, (1, 1, 1.2)), "gold", bone)
        b.joints[bone] = (end, drop + Vector((0, 0, -1.2 * S)), "head")
    # the finial: a gold ball on the apex, a stem and a cross with ball ends
    b.finish(b.sphere(apex, 1.6 * S, 8, 5), "gold", "hat")
    top = P(CX, 16.5)
    b.finish(b.tube([apex, top], 0.7 * S, 6), "gold", "hat")
    bar = P(CX, 19.5)
    b.finish(b.tube([bar - Vector((2.6 * S, 0, 0)), bar + Vector((2.6 * S, 0, 0))], 0.7 * S, 6), "gold", "hat")
    for p in (top, bar - Vector((2.6 * S, 0, 0)), bar + Vector((2.6 * S, 0, 0))):
        b.finish(b.sphere(p, 1.0 * S, 6, 4), "gold", "hat")


# -- arms ------------------------------------------------------------------------------------

def build_pauldron(b, shoulder, side):
    """A shoulder plate: a teal dome over the shoulder ball with a gold rim and the
    concept's gold fleur on its outside (line art); both shoulders alike."""
    out = Vector((-1 if side == "R" else 1, 0, 0))
    c = shoulder + out * 1.0 * S + Vector((0, 0, 1.4 * S))
    part = f"pauldron_{side}"
    prof = [(0.0, 5.4 * S), (3.2 * S, 4.6 * S), (5.6 * S, 2.4 * S), (6.6 * S, -0.6 * S), (6.9 * S, -2.6 * S),
            (6.2 * S, -2.8 * S), (5.8 * S, -0.8 * S), (4.8 * S, 1.8 * S), (2.6 * S, 3.8 * S), (0.0, 4.4 * S)]
    M = frame(c, out * 0.55 + Vector((0, 0, 1)), (0, 1, 0))
    verts = b.lathe(prof, 16, M, sy=0.95)[0]
    faces = b.finish(verts, "teal", part)
    rim = b.ring(M @ Vector((0, 0, -2.4 * S)), (M.to_3x3() @ Vector((0, 0, 1))), 6.3 * S, 7.4 * S, 1.3 * S, 16)
    b.finish(rim, "gold", part, smooth=False)
    fwd, up = Vector((0, -1, 0)), Vector((0, 0, 1))

    def uv(co):
        d = co - c
        return clamp01(0.5 + d.dot(fwd) / (13 * S)), clamp01(0.5 - d.dot(up) / (11 * S))
    b.map_detail([f for f in faces if f.normal.dot(out) > 0.2], DETAIL_PAULDRON, uv)


def build_arm(b, shoulder, elbow, grip, axis, radius, side):
    """Plate arm: shoulder ball, rerebrace, a gold-ringed couter at the elbow, the
    vambrace with a gold cuff, and a steel gauntlet closed round a bar (axis,
    radius) at grip: the lance's shaft for the left, nothing for the right fist."""
    u = Vector(axis).normalized()
    if u.z < 0:
        u = -u
    f = grip - elbow
    f = (f - u * f.dot(u)).normalized()
    w = f.cross(u) if side == "R" else u.cross(f)
    R = radius + 0.8 * S
    wrist = grip - f * (R + 4.0 * S) + w * (R + 1.3 * S) * 0.5
    upper, fore, hand = f"upperarm_{side}", f"forearm_{side}", f"hand_{side}"
    b.finish(b.sphere(shoulder, 4.6 * S, 10, 6), "steel_dark", upper)
    b.finish(b.tube([shoulder, elbow], 3.4 * S, 10, rs=[3.6 * S, 3.2 * S]), "steel_light", upper)
    b.finish(b.sphere(elbow, 3.9 * S, 10, 6), "steel", fore)
    b.finish(b.ring(elbow, wrist - shoulder, 3.6 * S, 4.3 * S, 1.0 * S, 12), "gold", fore, smooth=False)
    b.finish(b.tube([elbow, wrist], 3.5 * S, 10, rs=[3.5 * S, 3.0 * S]), "steel_light", fore)
    b.finish(b.ring(wrist, wrist - elbow, 2.9 * S, 4.2 * S, 1.6 * S, 12), "gold", fore, smooth=False)
    palm = build_hand(b, grip, u, f, w, R, hand, colour="steel_light", knuckle="steel")
    b.finish(b.tube([wrist, palm - f * 1.8 * S], 3.0 * S, 8, rs=[3.4 * S, 2.8 * S]), "steel_dark", hand)
    b.joints[upper] = (shoulder, elbow, "chest")
    b.joints[fore] = (elbow, wrist, upper)
    b.joints[hand] = (wrist, grip, fore)
    build_pauldron(b, shoulder, side)


# -- the lance -------------------------------------------------------------------------------

LANCE_GRIP_U = 0.0
# A stick umbrella's layout, at about 1 m long (comically large for him, but laid out
# like a real one, so it opens and closes believably): metres along the lance from
# the fist's grip toward the spike.
CAP_U = -0.022                 # the handle's gold cap, just behind the fist (further, it reaches the cape)
HANDLE_U = 0.045               # the handle (in the fist) ends at a gold collar
RUNNER_U = 0.285               # the runner (sliding collar) when furled, just below the canopy
RIB_END_U = 0.30               # the furled canopy's bottom: the ribs' ends
NOTCH_U = 0.92                 # the top notch the ribs are hinged at
FERRULE_U, TIP_U = 0.94, 1.0   # the gold ferrule and its spike above the notch
CANOPY_RIBS = 8
SHAFT_R, HANDLE_R = 1.0, 1.2   # px
CANOPY_TH = 0.35               # px: the canopy cloth's thickness (its lining clear of the ribs)


def canopy_r(u):
    """Radius (px) of the furled canopy at u along the lance, before its pleats: the
    cloth gathered fullest a little above the rib ends, tapering to the notch."""
    t = (u - RIB_END_U) / (NOTCH_U - RIB_END_U)
    return interp([(0.0, 3.6), (0.12, 4.6), (0.4, 4.2), (0.75, 2.6), (1.0, 1.3)], t)


def build_lance(b):
    """The stick umbrella he fights with: a brown handle in his fist with a gold cap,
    a bare steel shaft, the canopy furled slim round it in eight teal and cream panels
    over eight ribs hinged at the top notch, a runner below the canopy with eight
    stretchers up to the middle of each rib, and a gold ferrule and spike. Ribs,
    runner and stretchers are bones: turning the ribs out and sliding the runner up
    (open_canopy) opens it as a real umbrella opens."""
    grip = ARM_L[2]
    a = LANCE_DIR
    M = frame(grip, a, (0, 0, 1))                 # local Z along the lance, X roughly up
    at = lambda u, r=0.0, th=0.0: M @ Vector((r * math.cos(th), r * math.sin(th), u))
    b.finish(b.tube([at(CAP_U), at(HANDLE_U)], HANDLE_R * S, 8), "brown", "lance")
    b.finish(b.sphere(at(CAP_U), 1.6 * S, 8, 5), "gold", "lance")
    b.finish(b.ring(at(HANDLE_U), a, 0.9 * S, 1.8 * S, 1.2 * S, 10), "gold", "lance", smooth=False)
    b.finish(b.tube([at(HANDLE_U - 0.004), at(FERRULE_U + 0.004)], SHAFT_R * S, 8), "steel_dark", "lance")
    b.finish(b.tube([at(NOTCH_U - 0.008), at(FERRULE_U)], 1.5 * S, 10, rs=[1.5 * S, 1.8 * S]), "gold", "lance")
    b.finish(b.tube([at(FERRULE_U), at(TIP_U - 0.004), at(TIP_U)], 1.9 * S, 10,
                    rs=[1.9 * S, 0.45 * S, 0.1 * S]), "gold", "lance")
    # on the root, not the hand: clips carry it in his left fist frame by frame (from the
    # fist's IK pose), so in broken it can leave his hand and fall over him
    b.joints["lance"] = (at(0.0), at(TIP_U), "root")

    # the canopy: a pleated cloth shell round the shaft, its outside and its lining a
    # little inside it, closed at the hem and the notch, so opened it shows the same
    # panels inside as out (and the ribs under the lining); panels alternating
    segs = CANOPY_RIBS * 4
    us = [RIB_END_U + (NOTCH_U - RIB_END_U) * k / 16 for k in range(17)]
    prof = [(canopy_r(u) * S, u) for u in us] + [((canopy_r(u) - CANOPY_TH) * S, u) for u in reversed(us)]

    def pleat(p, th):
        k = 1.0 + 0.17 * math.cos(CANOPY_RIBS * th)
        return Vector((p.x * k, p.y * k, p.z))
    verts, bands, _ = b.lathe(prof, segs, M, loop=True, warp=pleat)
    b.finish(verts, "teal", "canopy", smooth=False)
    for band in bands:                 # each face by its place round the shaft, inside and out
        for i, f in enumerate(band):
            if ((i + 2) // 4) % 2:
                b.paint([f], "cream")

    # ribs: hinged at the notch, running down a pleat ridge just inside the cloth to a
    # gold tip at its bottom edge
    ribs = []
    for i in range(CANOPY_RIBS):
        th = 2 * math.pi * i / CANOPY_RIBS
        hinge = at(NOTCH_U - 0.006, 1.2 * S, th)
        end = at(RIB_END_U + 0.004, canopy_r(RIB_END_U) * 1.17 * S, th)
        bone = f"rib_{i}"
        b.joints[bone] = (hinge, end, "lance")
        rod = [at(u, canopy_r(u) * 1.17 * 0.82 * S, th) for u in (NOTCH_U - 0.012, (NOTCH_U + RIB_END_U) / 2, RIB_END_U + 0.006)]
        b.finish(b.tube(rod, 0.4 * S, 5), "steel_dark", bone)
        b.finish(b.sphere(end, 1.1 * S, 6, 4), "gold", bone)
        ribs.append((bone, th, rod[1]))

    # the runner: a gold collar sliding on the shaft (its own bone), and a stretcher
    # from it to the middle of each rib (each on its own bone, turned to its rib)
    b.finish(b.tube([at(RUNNER_U - 0.014), at(RUNNER_U + 0.014)], 1.8 * S, 10), "gold", "runner")
    b.joints["runner"] = (at(RUNNER_U), at(RUNNER_U + 0.04), "lance")
    for bone, th, mid in ribs:
        foot = at(RUNNER_U + 0.01, 1.5 * S, th)
        name = "stretcher" + bone[3:]
        b.finish(b.tube([foot, mid], 0.35 * S, 5), "steel_dark", name)
        b.joints[name] = (foot, mid, "runner")

    # each point of the canopy follows the two ribs either side of it (by its angle
    # round the shaft); near the notch it stays on the lance
    lance_i = b.bone_index("lance")
    Minv = M.inverted()
    for v in verts:
        lp = Minv @ v.co
        th = math.atan2(lp.y, lp.x) % (2 * math.pi)
        x = th / (2 * math.pi / CANOPY_RIBS)
        i0 = int(math.floor(x)) % CANOPY_RIBS
        i1 = (i0 + 1) % CANOPY_RIBS
        t = x - math.floor(x)
        hold = smoothstep((lp.z - (NOTCH_U - 0.08)) / 0.08)          # 1 at the notch
        dv = v[b.deform]
        dv.clear()
        if hold > 0:
            dv[lance_i] = hold
        for bone, k in ((ribs[i0][0], 1 - t), (ribs[i1][0], t)):
            if k * (1 - hold) > 1e-4:
                dv[b.bone_index(bone)] = k * (1 - hold)


# -- legs ------------------------------------------------------------------------------------

def build_leg(b, hip, knee, ankle, toe, s):
    """Plate leg: a cuisse up inside the skirt, a gold-ringed knee cop, a greave, a
    gold ankle ring and a sabaton with a gold-trimmed toe."""
    toe = Vector(toe).normalized()
    out = Vector((-1 if s == "R" else 1, 0, 0))
    thigh, shin, foot = f"thigh_{s}", f"shin_{s}", f"foot_{s}"
    base = Vector((ankle.x, ankle.y, 0.0))
    b.joints[thigh] = (hip, knee, "hips")
    b.joints[shin] = (knee, ankle, thigh)
    b.joints[foot] = (ankle, base + toe * 0.07 + Vector((0, 0, 0.02)), shin)
    b.finish(b.sphere(hip, 4.2 * S, 10, 6), "steel_dark", thigh)
    b.finish(b.tube([hip, knee], 4.0 * S, 10, rs=[4.4 * S, 3.6 * S]), "steel_light", thigh)
    b.finish(b.sphere(knee + Vector((0, -0.8 * S, 0)), 4.2 * S, 12, 7, (1, 0.9, 1)), "steel", shin)
    b.finish(b.ring(knee + Vector((0, -0.8 * S, 0)), Vector((0, -1, 0.25)), 2.4 * S, 3.6 * S, 1.6 * S, 12),
             "gold", shin, smooth=False)
    b.finish(b.tube([knee, knee.lerp(ankle, 0.5), ankle], 3.6 * S, 10, rs=[3.8 * S, 4.0 * S, 3.2 * S]), "steel_light", shin)
    b.finish(b.ring(ankle + Vector((0, 0, 0.8 * S)), Vector((0, 0, 1)), 3.0 * S, 4.4 * S, 1.6 * S, 12), "gold",
             shin, smooth=False)
    # sabaton: a steel shoe, its toe plates stepping down, a gold toe cap
    b.finish(b.tube([base + Vector((0, 0, 0.026)), ankle + Vector((0, 0, 1.0 * S))], 4.0 * S, 10,
                    rs=[4.4 * S, 3.4 * S]), "steel_dark", foot)
    b.finish(b.box(base - toe * 0.012 + Vector((0, 0, 0.022)), (0.045, 0.06, 0.042), xdir=toe), "steel_light", foot,
             smooth=False)
    for k in range(2):
        c = base + toe * (0.022 + 0.017 * k) + Vector((0, 0, 0.026 - 0.006 * k))
        b.finish(b.box(c, (0.024, 0.052 - 0.004 * k, 0.026), xdir=toe, zdir=Vector((0, 0, 1)) + toe * 0.4),
                 "steel" if k == 0 else "steel_light", foot, smooth=False)
    b.finish(b.sphere(base + toe * 0.056 + Vector((0, 0, 0.012)), 0.018, 8, 5, (1.2, 1.2, 0.7)), "gold", foot)
    b.finish(b.box(base + toe * 0.012 + Vector((0, 0, 0.004)), (0.09, 0.058, 0.008), xdir=toe), "steel_dark", foot,
             smooth=False)


# -- assembly --------------------------------------------------------------------------------

SKIRT_FOLLOW = (16.0, 4.0, 5.0)   # reach, fade, pin (px)
TABARD_HOLD = (8.5, 3.0)          # px either side of the middle the skirt under the tabard is held, and the fade


def build_mesh():
    b = Builder()
    build_torso(b)
    build_head(b)
    build_hat(b)
    build_scarf(b)
    skirt = build_skirt(b)
    build_tabard(b)
    build_cape(b)
    for leg, s in ((LEG_R, "R"), (LEG_L, "L")):
        build_leg(b, *leg, s)
    # both fists alike: the right closed on nothing, the left on the lance's handle
    for side, (sh, el, gr) in (("R", ARM_R), ("L", ARM_L)):
        build_arm(b, sh, el, gr, FIST_AXIS, FIST_BAR * S, side)
    build_lance(b)
    toy3d.follow_limbs(b, skirt, H(BELT_BOTTOM + 1), {"thigh_R": LEG_R[:2], "thigh_L": LEG_L[:2]},
                       body=("hips",), reach=SKIRT_FOLLOW[0], fade=SKIRT_FOLLOW[1], pin=SKIRT_FOLLOW[2])
    # the strip of skirt behind the tabard stays with the hips (as a satchel holds the
    # cloth under it still): the tabard hangs over it on its own chain, which the clips
    # swing forward with the leading thigh (settle()), and a skirt bulging forward with
    # the thigh there would push through it; the skirt round the sides still follows
    hips = b.bone_index("hips")
    centre = P(CX, 0)
    for v in skirt:
        dx = abs(v.co.x - centre.x) / S
        front = v.co.y < centre.y
        k = smoothstep((dx - TABARD_HOLD[0]) / TABARD_HOLD[1]) if front else 1.0
        dv = v[b.deform]
        for i2 in list(dv.keys()):
            dv[i2] = dv[i2] * k + ((1 - k) if i2 == hips else 0.0)
    return b


def build_umbrella():
    toy3d.configure(CHAR)
    obj, tris, rest = toy3d.build(build_mesh)
    # each stretcher stays aimed at the middle of its rib as the ribs turn and the
    # runner slides (the export bakes it)
    rig = obj.parent
    for i in range(CANOPY_RIBS):
        c = rig.pose.bones[f"stretcher_{i}"].constraints.new("DAMPED_TRACK")
        c.target, c.subtarget, c.head_tail = rig, f"rib_{i}", 0.5
    return obj, tris, rest


def open_canopy(obj, degrees=68.0):
    """Open the lance's umbrella by `degrees` (0 furled): each rib swings out from the
    shaft about the line across it through its hinge, and the runner slides up the
    shaft to where its stretchers (their true length) reach the ribs. Clips key the
    same pose."""
    rig = obj.parent
    lance = rig.data.bones["lance"]
    axis = (lance.tail_local - lance.head_local).normalized()
    for i in range(CANOPY_RIBS):
        pb = rig.pose.bones[f"rib_{i}"]
        rest = pb.bone.matrix_local.to_3x3()
        d = (pb.bone.tail_local - pb.bone.head_local).normalized()
        out = (d - axis * d.dot(axis)).normalized()              # straight out from the shaft
        turn = axis.cross(out).normalized()                       # across it, through the hinge
        local = rest.inverted() @ turn
        q = Quaternion(local, math.radians(degrees))
        if (rest @ (q @ Vector((0, 1, 0)))).dot(out) < d.dot(out):   # out, not into the shaft
            q = Quaternion(local, -math.radians(degrees))
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = q
    # the runner: rib 0's middle (where its stretcher meets it) in the lance's rest
    # frame, then the runner's place on the shaft that keeps the stretcher its length
    rb = rig.data.bones["rib_0"]
    q = rig.pose.bones["rib_0"].rotation_quaternion
    rest = rb.matrix_local.to_3x3()
    mid = rb.head_local + rest @ (q @ Vector((0, rb.length * 0.5, 0)))
    st = rig.data.bones["stretcher_0"]
    length = st.length
    rel = mid - lance.head_local
    along, radial = rel.dot(axis), (rel - axis * rel.dot(axis)).length
    foot_r = ((st.head_local - lance.head_local) - axis * (st.head_local - lance.head_local).dot(axis)).length
    foot_along = along - math.sqrt(max(length ** 2 - (radial - foot_r) ** 2, 0.0))
    slide = foot_along - (st.head_local - lance.head_local).dot(axis)
    pr = rig.pose.bones["runner"]
    pr.location = (0.0, slide, 0.0)                               # along its own Y, the shaft
    bpy.context.view_layer.update()
    return slide

if __name__ == "__main__" and bpy.app.background:
    o, t, c = build_umbrella()
    print("tris", sum(t.values()), t)
    print("clipping at rest", {k: v for k, v in c.items() if v})
    print("islands", toy3d.island_gaps(o))
