"""Build a low-poly 3D Lamp Warden from the pixel sprite (Blender, feasibility test).

Live, through the Blender MCP:   exec(open("tools/build_lamp_warden_3d.py").read())
Headless:  D:/Blender/blender.exe --background --python tools/build_lamp_warden_3d.py

The generic machinery (Builder, primitives, material, rig, checks, export,
previews) is shared with the other toys in tools/toy3d.py; this file holds
the Lamp Warden himself.

Every position is read off the 128 px idle frame (player/lamp/lamp_sheet.png):
128 px = 1 m (BattleSpace.PIXELS_PER_METRE) and the foot pivot (x 70) sits on the
origin, so the model stands at the same size as the sprite card. The character
faces -Y; screen-left of the sprite is -X.

Optimisation choices:
  - one mesh, one material: every face samples a swatch of a 16x16 palette
    texture built from the sprite's colours, plus a matching emission texture
    for the shade and lantern glow -> one draw call in Godot
  - each part is a closed solid skinned rigidly to one bone of a small
    armature (exported as the GLB's skeleton); only the mantle blends, so it
    lifts with the upper arms instead of letting them through
  - low segment counts sized to what reads at 128 px
  - the cape and tabard are cloth grids with even rows down their length and a
    sway weight in UV2.x (0 where they are pinned, 1 at the hem) for a wind
    shader or a bone chain
  - clip_report() checks part pairs that must never intersect, at rest and
    with the arms raised (pose_test)

Writes assets/models/lamp/lamp_warden.glb; the .blend and preview renders go in
assets/models/lamp/source/ (Godot-ignored).
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

try:
    _TOOLS = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _TOOLS = os.path.join(os.getcwd(), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
sys.dont_write_bytecode = True   # no __pycache__ in tools/ (check_structure)
import toy3d  # noqa: E402
importlib.reload(toy3d)
from toy3d import (S, P, Builder, frame, vprof, resample, smoothstep, chain_weights, build_hand,  # noqa: E402
                   clip_report, mute_ik, preview_camera, export_glb)

# name, hex, emissive. Sprite palette first; the steel/cream shades are derived.
PALETTE = [
    ("outline", "0a0a0c", False), ("steel", "76868e", False),
    ("steel_dark", "4c5a62", False), ("steel_light", "a8b6bc", False),
    ("cream", "faeed2", False), ("cream_shade", "c9c6b8", False),
    ("navy", "0e1e3a", False), ("navy_mid", "2a4666", False),
    ("brown", "825222", False), ("brown_dark", "5a3818", False),
    ("gold", "f6d66e", False), ("pale", "faeab2", False),
    ("glow", "faeab2", True), ("glow_hot", "fff8e6", True),
    ("unused0", "ff00ff", False), ("unused1", "ff00ff", False),
]
# parts skinned to another part's bone; every other part has a bone of its own
PART_BONE = {"torso": "body", "mantle": "body", "tabard": "body", "cape": "body", "belt": "body"}
BODY_BONES = ("hips", "spine", "chest")


def body_weights(z):
    """Robe, belt and mantle blend hips -> spine -> chest up the body."""
    py = 128 - z / S
    if py >= 64:          # skirt, belt and the tabard's top all move with the hips
        return [("hips", 1.0)]
    if py >= 56:
        t = (64 - py) / 8
        return [("hips", 1 - t), ("spine", t)]
    if py >= 48:
        t = (56 - py) / 8
        return [("spine", 1 - t), ("chest", t)]
    return [("chest", 1.0)]


# -- the warden ---------------------------------------------------------------

# the sprite's foot pivot is x 70 on the 128 px frame's bottom edge
CHAR = toy3d.configure(toy3d.Character(
    name="lamp_warden", folder="lamp", object_name="LampWarden", pivot=(70, 128), palette=PALETTE,
    part_bone=PART_BONE, body_weights=body_weights,
    detail=os.path.join(toy3d.ROOT, "assets", "models", "lamp", "source", "lamp_details.png")))
OUT_DIR, SRC_DIR = CHAR.out_dir, CHAR.src_dir

# regions of the detail atlas drawn by tools/draw_lamp_details.py (run it first)
DETAIL_TABARD = (256, 0, 448, 512)
DETAIL_SHIELD = (448, 0, 704, 256)
DETAIL_MANTLE = (0, 512, 1024, 640)
DETAIL_CAPE = (0, 640, 1024, 768)
DETAIL_ROBE = (0, 768, 1024, 896)


def build_shade(b):  # the head
    rim = P(53, 28, -0.1)
    apex = P(74, 4.5, 0.05)
    axis = (rim - apex).normalized()
    L = (rim - apex).length
    prof = [
        (0.0, -0.012), (0.04, -0.004), (0.062, 0.026), (0.076, 0.07), (0.09, 0.13),
        (0.108, 0.18), (0.122, L),                                   # outer: domed bell
        (0.114, L - 0.004),                                          # lip
        (0.1, L - 0.03), (0.08, 0.14), (0.063, 0.075), (0.046, 0.032), (0.0, 0.022),  # inner
    ]
    verts, bands, _ = b.lathe(prof, 14, frame(apex, axis, (0, 1, 0)))
    b.finish(verts, "steel", "head")
    b.paint(bands[5] + bands[6], "steel_dark")
    b.paint(bands[7], "brown")
    b.paint(bands[8] + bands[9], "glow")
    b.paint(bands[10] + bands[11], "glow_hot")
    b.finish(b.sphere(apex + axis * 0.14, 0.034, 8, 5), "glow_hot", "head")  # bulb
    # hub on the crown, where the lamp arm holds the shade (the arm's three brass
    # joints carry the gold; the crown has no knob of its own)
    b.finish(b.tube([apex - axis * 0.012, apex + axis * 0.03], 0.03, 8), "steel_dark", "head")
    b.joints["head"] = (apex, rim, "neck_upper")
    return apex


def build_lamp_arm(b, apex):
    """The desk-lamp arm is the warden's neck: a lower link rising from a
    swivel mount on the collar, the big brass elbow, and an upper link that
    holds the head (the shade). Each link has its own bone."""
    j0, j1, j2 = P(80, 9, 0.05), P(95, 22, 0.085), P(70, 38.5, 0.06)
    # lower link: swivel mount on top of the collar, twin rods up to the brass elbow
    b.finish(b.tube([P(70, 41.5, 0.058), P(70, 39, 0.06)], 4.2 * S, 8, rs=[4.6 * S, 3.8 * S]),
             "steel_dark", "neck_lower", smooth=False)
    b.finish(b.sphere(j2, 0.028, 8, 5), "gold", "neck_lower")
    # upper link: elbow joint, twin rods with the tension spring, up to the head
    b.finish(b.sphere(j1, 0.034, 10, 6), "gold", "neck_upper")
    for off in (-0.018, 0.018):
        o = Vector((0, off, 0))
        b.finish(b.tube([j1 + o, j2 + o], 0.009, 6), "steel", "neck_lower")
        b.finish(b.tube([j0 + o, j1 + o], 0.009, 6), "steel", "neck_upper")
    mid0, mid1 = j0.lerp(j1, 0.25), j0.lerp(j1, 0.75)
    b.finish(b.tube([mid0, mid1], 0.012, 6), "steel_dark", "neck_upper")
    b.finish(b.tube([apex, j0], 0.011, 6), "steel_dark", "neck_upper")
    b.finish(b.sphere(j0, 0.022, 8, 5), "gold", "neck_upper")
    b.joints["neck_lower"] = (j2, j1, "chest")
    b.joints["neck_upper"] = (j1, j0, "neck_lower")


ROBE_SY = 0.68
BELT_TOP = 128 - 66  # height of the belt's top edge, px above the ground
ROBE_PROF = [(0, 97), (23, 101), (22, 95), (20, 86), (16.5, 74), (14.9, 66), (14.5, 64), (12.5, 54), (9, 46), (0, 44)]


def robe_r(py):
    """Robe radius (px) at sprite height py, for laying straps on its surface."""
    pts = sorted(ROBE_PROF[1:-1], key=lambda q: q[1])
    for (r0, y0), (r1, y1) in zip(pts, pts[1:]):
        if y0 <= py <= y1:
            return r0 + (r1 - r0) * (py - y0) / (y1 - y0)
    return pts[0][0] if py < pts[0][1] else pts[-1][0]


def on_robe(px, py, lift=0.8):
    """Front surface of the robe under sprite pixel (px, py)."""
    r = robe_r(py) + lift
    dx = min(abs(px - 68), r * 0.95)
    return P(px, py, -ROBE_SY * math.sqrt(r * r - dx * dx) * S)


def build_torso(b):
    # navy robe and chest, slimmer than the first pass
    def robe_warp(p, a):
        if p.z < (128 - 96) * S:
            p.z += 0.01 * math.sin(5 * a)
        return p
    verts, bands, rings = b.lathe(vprof(ROBE_PROF), 12, Matrix.Translation(P(68, 128)), sy=ROBE_SY, warp=robe_warp)
    faces = b.finish(verts, "navy", "torso")
    # the hem flare (rings 1..3, rows 101 up to 86) carries the hem band's line art
    b.map_detail(bands[1] + bands[2], DETAIL_ROBE, b.grid_uv(rings, 1, 3, closed=True), wrap=True)
    b.paint([f for f in faces if f.calc_center_median().z > BELT_TOP * S], "cream")  # tunic above the belt
    b.joints["root"] = (Vector((0, 0, 0)), Vector((0, -0.12, 0)), None)
    b.joints["hips"] = (P(68, 92), P(68, 74), "root")
    b.joints["spine"] = (P(68, 74), P(68, 58), "hips")
    b.joints["chest"] = (P(68, 58), P(68, 44), "spine")
    b.paint(bands[0], "navy_mid")  # hem underside

    # cream mantle: a capelet open at the front so the navy chest shows,
    # scalloped along the hem
    def arm_angle(elbow):  # lathe angle of an arm as seen from the mantle's axis
        rel = elbow - P(69, 128)
        return math.atan2(rel.y / 0.74, rel.x)
    arm_angles = [(arm_angle(ARM_R[1]), MANTLE_ARCH[0]), (arm_angle(ARM_L[1]), MANTLE_ARCH[1])]

    def mantle_warp(p, a):
        t = max(0.0, ((128 - 50) * S - p.z) / (13 * S))
        k = 1 + 0.07 * t * math.sin(7 * a)
        for aa, lift in arm_angles:  # the hem arches up and out over each arm
            d = (a - aa + math.pi) % (2 * math.pi) - math.pi
            bump = math.exp(-(d / 0.45) ** 2)
            k += 0.08 * t * bump
            p.z += lift * S * t * t * bump
        p.x *= k
        p.y *= k
        p.z += 0.008 * t * math.cos(7 * a)
        return p
    rows, segs, a0, a1 = 8, 18, math.radians(-62), math.radians(242)
    outer = resample([(8, 41), (14.5, 43.5), (20, 48.5), (22.5, 55), (23.5, 63)], rows)
    inner = resample([(6.5, 42.5), (12.8, 45), (18.3, 49), (20.8, 55), (21.8, 63)], rows)
    verts, bands, rings = b.lathe(vprof(outer + inner[::-1]), segs, Matrix.Translation(P(69, 128)), sy=0.74,
                                  loop=True, arc=(a0, a1), warp=mantle_warp)
    b.finish(verts, "cream", "mantle")
    b.paint([f for band in bands[rows:2 * rows - 1] for f in band], "cream_shade")   # its lining
    # the outside carries the hem trim and stitches, collar (ring 0) to hem (ring rows - 1)
    b.map_detail([f for band in bands[:rows - 1] for f in band], DETAIL_MANTLE, b.grid_uv(rings, 0, rows - 1))
    # the mantle drapes over the arms: cloth close to an upper arm follows it,
    # so raising an arm lifts the cloth resting on it; the collar stays pinned
    top_z = (128 - 41) * S
    body = {b.bone_index(n) for n in BODY_BONES}
    arm_r, arm_l = b.bone_index("upperarm_R"), b.bone_index("upperarm_L")

    def near_arm(co, arm):
        shoulder, elbow = arm
        seg = elbow - shoulder
        t = max(0.0, min(1.0, (co - shoulder).dot(seg) / seg.length_squared))
        d = (co - (shoulder + seg * t)).length / S  # px from the arm's axis
        return smoothstep((16.0 - d) / 10.0)

    for v in verts:
        pinned = smoothstep((top_z - v.co.z) / (8 * S))
        kr = near_arm(v.co, ARM_R) * pinned
        kl = near_arm(v.co, ARM_L) * pinned
        if kr + kl > 1.0:
            kr, kl = kr / (kr + kl), kl / (kr + kl)
        dv = v[b.deform]
        for k in list(dv.keys()):
            if k in body:
                dv[k] *= 1.0 - kr - kl
        if kr > 0.001:
            dv[arm_r] = kr
        if kl > 0.001:
            dv[arm_l] = kl
    b.mantle_verts = verts  # the cape tucked under it copies these weights
    # brown collar band and the brass clasp holding the mantle shut at the throat
    b.finish(b.lathe(vprof([(10.5, 44), (10.5, 41), (7.5, 41), (7.5, 44)]), 12,
                     Matrix.Translation(P(68, 128)), sy=0.74, loop=True)[0], "brown", "torso")
    # on the front of the collar band (radius 10.5 px, rows 41-44), half sunk into it
    b.finish(b.sphere(P(68, 42.5, -10.5 * 0.74 * S - 0.004), 3.4 * S, 8, 5, (1, 0.55, 1)), "gold", "torso")

    # bandolier from the right shoulder across the chest to the left hip
    path = [on_robe(px, py, 0.6) for px, py in ((82, 47), (77, 53), (70, 59), (62, 64), (57.5, 67))]
    b.finish(b.strap(path, P(68, 0), 4 * S, 1.2 * S), "brown", "torso", smooth=False)
    b.finish(b.box(on_robe(70, 59, 1.6), (5 * S, 1.2 * S, 5 * S), xdir=(1, 0, -0.75)), "gold", "torso", smooth=False)

    # belt, buckle and pouch; the belt stands 1 px off the robe so the
    # tabard can tuck under it
    belt = [(robe_r(71) + 2.5, 71), (robe_r(66) + 2.5, 66), (robe_r(66) + 1.25, 66), (robe_r(71) + 1.25, 71)]
    b.finish(b.lathe(vprof(belt), 32, Matrix.Translation(P(68, 128)), sy=ROBE_SY, loop=True)[0],
             "brown", "belt", smooth=False)
    front = on_robe(66, 68.5, 2.9)
    b.finish(b.box(front, (0.034, 0.008, 0.03)), "gold", "belt", smooth=False)
    b.finish(b.box(front + Vector((0, -0.004, 0)), (0.016, 0.006, 0.014)), "brown_dark", "belt", smooth=False)
    pdir = Vector((1.0, 0.5, 0.0))
    pouch = on_robe(80, 74, 4.2)
    b.finish(b.box(pouch, (0.04, 0.026, 0.046), xdir=pdir), "brown", "belt", smooth=False)
    b.finish(b.box(pouch + Vector((0, -0.01, 0.014)), (0.042, 0.01, 0.022), xdir=pdir), "brown_dark", "belt", smooth=False)
    b.finish(b.sphere(pouch + Vector((0, -0.017, 0.006)), 0.006, 6, 4), "gold", "belt")


TABARD_X = [-7.5, -6.0, -3.5, -1.0, 1.0, 3.5, 6.0, 7.5]
TABARD_Y = [0, 1.5, 4, 7, 10, 12, 15, 17, 19, 21, 24, 27, 30, 33, 35.5, 37.5, 40]  # px below its top


def build_tabard(b):
    """Cloth panel tucked under the belt, lying on the robe and hanging free
    past its hem. A grid with rows down its length so it can sway; its front
    carries the banner's line art (a steel-blue border, a gold sun, gold
    diamonds), laid on the grid so it moves with the cloth."""
    cx, top = 66.5, 69.0          # top edge sits under the belt
    back_lift, front_lift = 0.5, 1.05

    def at(x, yy, lift):
        taper = max(0.04, min(1.0, (40.0 - yy) / 7.0))  # pointed bottom
        return on_robe(cx + x * taper, top + yy, lift)

    bm, xs, ys = b.bm, TABARD_X, TABARD_Y
    F = [[bm.verts.new(at(x, yy, front_lift)) for x in xs] for yy in ys]
    B = [[bm.verts.new(at(x, yy, back_lift)) for x in xs] for yy in ys]
    fronts, backs = [], []
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            fronts.append(bm.faces.new((F[j][i], F[j][i + 1], F[j + 1][i + 1], F[j + 1][i])))
            backs.append(bm.faces.new((B[j][i], B[j + 1][i], B[j + 1][i + 1], B[j][i + 1])))
    for j in range(len(ys) - 1):
        for i in (0, len(xs) - 1):
            bm.faces.new((F[j][i], F[j + 1][i], B[j + 1][i], B[j][i]))
    for i in range(len(xs) - 1):
        for j in (0, len(ys) - 1):
            bm.faces.new((F[j][i], B[j][i], B[j][i + 1], F[j][i + 1]))
    faces = b.finish([v for row in F + B for v in row], "navy", "tabard", smooth=False)
    b.map_detail(fronts, DETAIL_TABARD, {F[j][i]: ((x + 7.5) / 15.0, yy / 40.0)
                                         for j, yy in enumerate(ys) for i, x in enumerate(xs)})
    b.paint(backs, "navy_mid")
    b.set_sway(faces, (128 - 71) * S, (128 - top - ys[-1]) * S)
    # two-bone chain down the middle; weights blend from the hips down it
    # hinged just below the belt so the part tucked under it never moves
    b.joints["tabard_1"] = (at(0, 2.5, front_lift), at(0, 21, front_lift), "hips")
    b.joints["tabard_2"] = (at(0, 21, front_lift), at(0, 39, front_lift), "tabard_1")
    chain_weights(b, {v for f in faces for v in f.verts}, (128 - top) * S, 40 * S,
                  (("hips", 0.06), ("tabard_1", 0.38), ("tabard_2", 0.85)), 0.32)


def build_leg(b, hip, knee, ankle, toe, side, s):
    """Plate leg: cuisse, poleyn with a side wing, ridged greave, laminated sabaton.
    side is -1 for the leg on screen-left, +1 for screen-right."""
    toe = Vector(toe).normalized()
    out = Vector((side, 0, 0))
    thigh, shin, foot = f"thigh_{s}", f"shin_{s}", f"foot_{s}"
    base = Vector((ankle.x, ankle.y, 0.0))
    b.joints[thigh] = (hip, knee, "hips")
    b.joints[shin] = (knee, ankle, thigh)
    b.joints[foot] = (ankle, base + toe * 0.075 + Vector((0, 0, 0.02)), shin)
    b.finish(b.tube([hip, knee], 4.2 * S, 8, rs=[4.6 * S, 4.0 * S]), "steel_dark", thigh)  # cuisse

    # greave: a lathe up the shin with a keel down the front and rolled edges
    shin_dir = knee - ankle
    L = shin_dir.length
    M = frame(ankle, shin_dir, (0, -1, 0))  # local +X faces forward

    def keel(p, a, grow=0.0):
        k = 1 + 0.24 * max(0.0, math.cos(a)) ** 6 + grow
        p.x *= k
        p.y *= k
        return p
    prof = [(0, 0), (5.6 * S, 0), (5.2 * S, 0.06 * L), (4.5 * S, 0.16 * L), (4.9 * S, 0.42 * L),
            (5.3 * S, 0.7 * L), (5.9 * S, 0.9 * L), (6.4 * S, 0.97 * L), (5.6 * S, L), (0, L)]
    verts, bands, _ = b.lathe(prof, 10, M, sy=0.92, warp=keel)
    b.finish(verts, "steel", shin)
    b.paint(bands[1] + bands[6] + bands[7], "steel_light")  # rolled edges catch the light
    strap_prof = [(4.65 * S, 0.27 * L), (4.65 * S, 0.33 * L), (4.2 * S, 0.33 * L), (4.2 * S, 0.27 * L)]
    sv = b.lathe(strap_prof, 10, M, sy=0.92, loop=True, warp=lambda p, a: keel(p, a, 0.07))[0]
    b.finish(sv, "brown", shin, smooth=False)
    for a in (math.radians(65), math.radians(-65)):
        r = 6.1 * S
        b.finish(b.sphere(M @ Vector((r * math.cos(a), r * math.sin(a) * 0.92, 0.88 * L)), 1.1 * S, 6, 4), "gold", shin)

    # poleyn: knee cop with a fan-shaped wing on the outside
    b.finish(b.sphere(knee + Vector((0, -1.0 * S, 0)), 5.4 * S, 10, 6, (1, 0.85, 0.9)), "steel", shin)
    b.finish(b.sphere(knee + Vector((0, -5.6 * S, 0.4 * S)), 1.4 * S, 6, 4), "gold", shin)
    wing_c = knee + out * 4.6 * S + Vector((0, -0.6 * S, 0))
    fan = [(0, 0)] + [(4.8 * S * math.cos(t), 4.8 * S * math.sin(t))
                      for t in (math.radians(-80 + 20 * k) for k in range(9))]
    b.finish(b.slab(fan, 1.2 * S, frame(wing_c, out, (0, 1, 0))),
             "steel_light", shin, smooth=False)

    # sabaton: overlapping lames stepping down to a gold toe cap
    # ankle cuff: rises from inside the shoe and tucks up under the greave
    b.finish(b.tube([base + Vector((0, 0, 0.03)), ankle + Vector((0, 0, 1.5 * S))], 5.2 * S, 10,
                    rs=[5.4 * S, 4.6 * S]), "steel_dark", foot)
    b.finish(b.box(base - toe * 0.02 + Vector((0, 0, 0.03)), (0.04, 0.058, 0.05), xdir=toe), "steel", foot, smooth=False)
    for k in range(3):
        c = base + toe * (0.004 + 0.017 * k) + Vector((0, 0, 0.038 - 0.007 * k))
        zdir = Vector((0, 0, 1)) + toe * (0.35 + 0.15 * k)
        b.finish(b.box(c, (0.022, 0.06 - 0.003 * k, 0.03), xdir=toe, zdir=zdir),
                 "steel_light" if k == 1 else "steel", foot, smooth=False)
    b.finish(b.sphere(base + toe * 0.062 + Vector((0, 0, 0.016)), 0.022, 8, 5, (1.25, 1.25, 0.75)), "gold", foot)
    b.finish(b.box(base + toe * 0.018 + Vector((0, 0, 0.004)), (0.106, 0.064, 0.008), xdir=toe), "steel_dark", foot, smooth=False)
    side_dir = toe.cross(Vector((0, 0, 1)))
    if side_dir.dot(out) < 0:
        side_dir = -side_dir
    for k in range(3):
        c = base + toe * (0.004 + 0.017 * k) + Vector((0, 0, 0.034 - 0.007 * k))
        b.finish(b.sphere(c + side_dir * 0.031, 0.9 * S, 4, 3), "gold", foot)


def build_arm(b, shoulder, elbow, grip, axis, radius, side, upper_r=3.8 * S):
    """Upper arm, forearm and gauntlet gripping a bar (axis, radius) at grip.
    side "R" or "L" is the character's own right or left."""
    u = Vector(axis).normalized()
    if u.z < 0:
        u = -u
    f = grip - elbow
    f = (f - u * f.dot(u)).normalized()
    w = f.cross(u) if side == "R" else u.cross(f)  # palm side of the bar
    R = radius + 0.8 * S
    wrist = grip - f * (R + 4.0 * S) + w * (R + 1.3 * S) * 0.5
    upper, fore, hand = f"upperarm_{side}", f"forearm_{side}", f"hand_{side}"
    b.finish(b.sphere(shoulder, 5.5 * S, 8, 5, (1, 0.9, 0.8)), "steel", upper)
    b.finish(b.tube([shoulder, elbow], upper_r, 8), "steel_dark", upper)
    b.finish(b.sphere(elbow, 4.6 * S, 8, 5), "steel_light", fore)
    b.finish(b.tube([elbow, wrist], 4.4 * S, 8, rs=[4.4 * S, 3.8 * S]), "steel", fore)
    # brown band and flared cuff: kept apart and at different radii so the two
    # never share a surface (overlapping same-size rings flicker); a forearm too
    # short for both keeps just the cuff
    along = (wrist - elbow).length
    band = min(0.7 * along, along - 0.8 * S - 1.0 * S - 0.4 * S)
    if band > 2.5 * S:
        b.finish(b.ring(elbow + (wrist - elbow).normalized() * band, wrist - elbow, 3.6 * S, 4.5 * S, 2 * S),
                 "brown", fore, smooth=False)
    b.finish(b.ring(wrist, wrist - elbow, 3.2 * S, 4.8 * S, 1.6 * S), "steel_light", fore, smooth=False)  # cuff
    palm = build_hand(b, grip, u, f, w, R, hand)
    b.finish(b.tube([wrist, palm - f * 1.8 * S], 3.2 * S, 8, rs=[3.6 * S, 3.0 * S]), "steel_dark", hand)
    b.joints[upper] = (shoulder, elbow, "chest")
    b.joints[fore] = (elbow, wrist, upper)
    b.joints[hand] = (wrist, grip, fore)


def SP(px, py, d=0.0):
    """A point on the staff or its lantern: sprite space, moved by STAFF_SHIFT."""
    return P(px, py, d) + STAFF_SHIFT


def build_staff(b):
    d = -0.085
    pole = [SP(36.5, 125, d), STAFF_GRIP, SP(31, 24, d)]  # straight, so it slides through the hand

    def at(py):  # point on the pole at sprite height py
        for a, c in zip(pole, pole[1:]):
            z = (128 - py) * S
            if a.z <= z <= c.z:
                return a.lerp(c, (z - a.z) / (c.z - a.z))
        return pole[-1]

    b.finish(b.tube(pole, 2.2 * S, 6), "steel", "staff")
    for y0, y1, colour in ((40, 46, "brown"), (GRIP_ROW - 4, GRIP_ROW + 4, "brown"), (96, 102, "brown"),
                           (108, 111, "gold"), (120, 125, "gold")):
        b.finish(b.tube([at(y1), at(y0)], 3.0 * S, 6), colour, "staff", smooth=False)
    # crook: a little desk-lamp arm holding the lantern
    top, tip, brace = SP(29, 22, d), SP(11, 32, d), at(44)
    b.finish(b.sphere(top, 3.5 * S, 8, 5), "gold", "staff")
    b.finish(b.tube([top, tip], 1.9 * S, 6), "steel", "staff")
    b.finish(b.tube([brace, top.lerp(tip, 0.45)], 1.4 * S, 6), "steel_dark", "staff")
    b.finish(b.sphere(brace, 2.6 * S, 6, 4), "gold", "staff")
    b.finish(b.sphere(tip, 3.0 * S, 8, 5), "gold", "staff")
    # the lantern hangs from the knob on a short rod and swings on its own bone,
    # hinged at the knob's centre; the rod starts just outside the knob so it
    # never sinks into it however far the lantern swings
    b.finish(b.tube([tip + Vector((0, 0, -3.4 * S)), SP(11, 36.2, d)], 0.8 * S, 4), "steel_dark", "lantern")
    b.joints["lantern"] = (tip, SP(11, 66, d), "staff")

    prof = vprof([(0, 66), (1.5, 64), (3, 61), (4.5, 60), (7.5, 54), (8.3, 49), (7.5, 44),
                  (5, 40.5), (5.5, 40), (4.5, 37.5), (2, 36), (0, 35.5)])
    verts, bands, _ = b.lathe(prof, 8, Matrix.Translation(SP(11, 128, d)))
    b.finish(verts, "glow", "lantern", smooth=False)
    b.paint(bands[0] + bands[1] + bands[2], "gold")
    b.paint(bands[4] + bands[5], "glow_hot")
    b.paint(bands[7] + bands[8] + bands[9] + bands[10], "gold")
    # gold frame ribs over the glass
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        dirv = Vector((math.cos(a), math.sin(a), 0))
        rib = [SP(11, py, d) + dirv * (r + 0.6) * S for r, py in ((4.5, 60), (7.5, 54), (8.3, 49), (7.5, 44), (5, 40.5))]
        b.finish(b.tube(rib, 0.7 * S, 4), "gold", "lantern")


SHIELD_YAW = math.radians(25)
SHIELD_GRIP_AXIS = Vector((0.0, 0.0, 1.0))  # upright handle
SHIELD_NORMAL = Vector((math.sin(SHIELD_YAW), -math.cos(SHIELD_YAW), 0.0))
SHIELD_GRIP_DEPTH = 0.058  # strap sits this far behind the shield face, room for the fingers
SHIELD_GRIP = P(110, 84, -0.165) - SHIELD_NORMAL * SHIELD_GRIP_DEPTH + Vector((-0.02, 0.0, 0.03))


def ringed_slab(b, pts, th, M, zoff, warp, centre=(0.0, 0.0), rings=4):
    """Like Builder.slab, but the top and bottom are rings of quads closing on a
    centre point, so a warp that curves the outline curves the whole surface
    (a flat n-gon only bends at its rim, and whatever sits on it floats or sinks)."""
    bm = b.bm
    cx, cy = centre

    def layer(z):
        at = lambda x, y: M @ warp(Vector((x, y, z + zoff)))
        grid = [[bm.verts.new(at(cx + (x - cx) * k / rings, cy + (y - cy) * k / rings)) for x, y in pts]
                for k in range(1, rings + 1)]
        return bm.verts.new(at(cx, cy)), grid

    n = len(pts)
    verts = []
    for z, flip in ((th / 2, False), (-th / 2, True)):
        mid, grid = layer(z)
        verts += [mid] + [v for ring in grid for v in ring]
        for i in range(n):
            j = (i + 1) % n
            quads = [(mid, grid[0][i], grid[0][j])] + [(grid[k][i], grid[k + 1][i], grid[k + 1][j], grid[k][j])
                                                       for k in range(rings - 1)]
            for q in quads:
                bm.faces.new(tuple(reversed(q)) if flip else q)
        if not flip:
            top = grid[-1]
        else:
            bot = grid[-1]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    return verts


def build_shield(b):
    c = P(110, 84, -0.165)
    yaw = math.radians(25)
    normal = Vector((math.sin(yaw), -math.cos(yaw), 0))
    M = frame(c, normal, (math.cos(yaw), math.sin(yaw), 0))
    bend = lambda x: -2.0 * x * x  # edges curve back, face bulges out

    def warp(p):
        return Vector((p.x, p.y, p.z + bend(p.x)))

    shape = [(0, -32), (6, -25), (11, -16), (14, -6), (15.5, 5), (15, 18), (15, 27), (8, 28.5), (0, 29),
             (-8, 28.5), (-15, 27), (-15, 18), (-15.5, 5), (-14, -6), (-11, -16), (-6, -25)]
    px = lambda pts: [(x * S, y * S) for x, y in pts]
    # the plate, its face and the sun are ringed so they all follow the curve and
    # each layer lies flush on the one under it
    b.finish(ringed_slab(b, px(shape), 0.01, M, 0.0, warp), "steel_dark", "shield", smooth=False)
    face = [(x * (1 - 3 / 15.5), y * (1 - 3 / 31) - 0.3) for x, y in shape]
    plate = b.finish(ringed_slab(b, px(face), 0.004, M, 0.0065, warp), "steel", "shield", smooth=False)
    # its front carries a thin gold line just inside the edge, laid flat across the face
    Mi = M.inverted()

    def shield_uv(co):
        q = Mi @ co
        return (q.x / S + 15.5) / 31.0, (29.0 - q.y / S) / 61.0
    b.map_detail([f for f in plate if f.normal.dot(normal) > 0.5], DETAIL_SHIELD, shield_uv)
    # sun emblem, on the face's centre (its centroid)
    sx, sy = 0.0, 2.5 * S
    star = []
    for k in range(24):
        a = math.pi / 2 + k * math.pi / 12
        r = (10 if k % 2 == 0 else 5.5) * S
        star.append((sx + r * math.cos(a), sy + r * math.sin(a)))
    b.finish(ringed_slab(b, star, 0.003, M, 0.0098, warp, (sx, sy), 3), "pale", "shield", smooth=False)
    disc = [(sx + 3.6 * S * math.cos(a), sy + 3.6 * S * math.sin(a)) for a in (2 * math.pi * k / 10 for k in range(10))]
    b.finish(ringed_slab(b, disc, 0.003, M, 0.0125, warp, (sx, sy), 2), "cream", "shield", smooth=False)
    for x, y in ((-11, 22), (11, 22), (-12.5, -4), (12.5, -4), (0, -25)):
        lx, ly = x * S, y * S
        pos = M @ Vector((lx, ly, 0.009 + bend(lx)))
        b.finish(b.sphere(pos, 1.7 * S, 6, 4), "gold", "shield")
    # grip strap behind the shield, held by the left gauntlet
    b.finish(b.box(SHIELD_GRIP, (0.11, 0.012, 0.008), xdir=SHIELD_GRIP_AXIS, zdir=SHIELD_NORMAL),
             "brown", "shield", smooth=False)
    for end in (-1, 1):  # lugs riveting the handle to the back of the shield
        reach = SHIELD_GRIP_DEPTH - 0.006
        lug = SHIELD_GRIP + SHIELD_GRIP_AXIS * end * 0.051 + SHIELD_NORMAL * reach / 2
        b.finish(b.box(lug, (0.008, 0.012, reach), xdir=SHIELD_GRIP_AXIS, zdir=SHIELD_NORMAL),
                 "brown_dark", "shield", smooth=False)


# the cape's lathe profile (radius px, sprite row): a layer just under the mantle
# that comes out below its hem (row 63) as wide as the mantle and carries its
# line on down, so the two read as one cloak. Starting up at the neck at the
# mantle's own radius, the scalloped hem showed through it
CAPE_OUTER = [(17.5, 58), (18, 63.5), (21.5, 64.7), (24, 67), (27.5, 70), (30.5, 80), (34, 92), (37.5, 103), (40.5, 113)]
CAPE_CHAIN_ROWS = (72, 85, 99, 111)  # where the cape_1..3 chain runs down the back, below the pinned top
CAPE_PIN_ROWS = (69, 76)  # it moves with the mantle down to the first row, swings freely from the second


def build_cape(b):
    """A billowing cape: folds that deepen toward the hem, swept screen-left and
    lifted on that side, with a ragged uneven hem."""
    top_z, hem_z = (128 - CAPE_OUTER[0][1]) * S, (128 - 113) * S

    def warp(p, a):
        t = max(0.0, min(1.0, (top_z - p.z) / (top_z - hem_z)))
        fold = (7.0 * S) * t ** 1.1 * math.sin(7 * a + 0.6) + (2.0 * S) * t * math.sin(13 * a + 2.0)
        p.x += math.cos(a) * fold
        p.y += math.sin(a) * 0.7 * fold
        p.y += 0.035 * t * t * max(0.0, math.sin(a))      # billows out behind
        p.x -= 0.13 * t * t                               # swept screen-left
        lift = max(0.0, -math.cos(a))
        p.x -= 0.05 * t ** 2 * lift
        p.z += 0.05 * t ** 2.5 * lift                     # the trailing side lifts
        p.z += (0.018 * math.sin(3 * a + 1.0) + 0.008 * math.sin(11 * a)) * t ** 3
        return p

    rows = 13
    outer = resample(CAPE_OUTER, rows)
    inner = resample([(r - 1.5, py) for r, py in CAPE_OUTER], rows)
    inner[-1] = (inner[-1][0], 113.4)
    a0, a1, segs = math.radians(15), math.radians(168), 26
    verts, bands, rings = b.lathe(vprof(outer + inner[::-1]), segs, Matrix.Translation(P(68, 128, 0.012)), sy=0.7,
                                  loop=True, arc=(a0, a1), warp=warp)
    faces = b.finish(verts, "cream", "cape")
    b.paint([f for band in bands[rows:2 * rows - 1] for f in band], "cream_shade")   # its lining
    # the outside carries a thin line along the hem and up both edges
    b.map_detail([f for band in bands[:rows - 1] for f in band], DETAIL_CAPE, b.grid_uv(rings, 0, rows - 1))
    b.set_sway(faces, top_z, hem_z)  # pinned at the shoulders, free at the hem

    # three-bone chain down the middle of the back; weights blend down it
    def back_point(py):
        band = sorted((v.co for v in verts if abs((128 - v.co.z / S) - py) < 4), key=lambda c: -c.y)[:6]
        return sum(band, Vector()) / len(band)
    js = [back_point(py) for py in CAPE_CHAIN_ROWS]
    for i in range(3):
        b.joints[f"cape_{i + 1}"] = (js[i], js[i + 1], "chest" if i == 0 else f"cape_{i}")
    chain_weights(b, verts, top_z, top_z - hem_z,
                  (("chest", -0.08), ("cape_1", 0.2), ("cape_2", 0.55), ("cape_3", 0.9)), 0.35)
    # the cape under the mantle and its flare just below copy the weights of the
    # mantle beside them, so the two move as one when he leans, lifts an arm or
    # swings the cape; the swing starts below them
    mantle = KDTree(len(b.mantle_verts))
    for i, mv in enumerate(b.mantle_verts):
        mantle.insert(mv.co, i)
    mantle.balance()
    pin_z, free_z = ((128 - r) * S for r in CAPE_PIN_ROWS)
    for v in verts:
        k = smoothstep((v.co.z - free_z) / (pin_z - free_z))
        if k <= 0.0:
            continue
        dv = v[b.deform]
        for i in list(dv.keys()):
            dv[i] *= 1.0 - k
        near = b.mantle_verts[mantle.find(v.co)[1]][b.deform]
        for i, w in near.items():
            dv[i] = dv.get(i, 0.0) + k * w


def build_mesh():
    b = Builder()
    apex = build_shade(b)
    build_lamp_arm(b, apex)
    build_torso(b)
    build_tabard(b)
    build_cape(b)
    build_leg(b, P(61, 92), P(53, 101, -0.04), P(49, 115, -0.02), (-0.8, -0.6, 0), -1, "R")
    build_leg(b, P(76, 92), P(86, 101, -0.035), P(92, 115, -0.01), (0.85, -0.5, 0), 1, "L")
    staff_grip = STAFF_GRIP
    staff_axis = (P(31, 24) - P(36.5, 125)).normalized()
    # a slimmer upper arm passes between the mantle and the satchel; the gauntlet
    # sits a little wider than the leather wrap it closes on
    build_arm(b, ARM_R[0], ARM_R[1], staff_grip, staff_axis, 3.4 * S, "R", upper_r=3.3 * S)
    build_arm(b, ARM_L[0], ARM_L[1], SHIELD_GRIP, SHIELD_GRIP_AXIS, 0.006, "L")
    build_staff(b)
    build_shield(b)
    b.joints["staff"] = (staff_grip, SP(31, 24, -0.085), "hand_R")
    b.joints["shield"] = (SHIELD_GRIP, P(110, 84, -0.165), "hand_L")
    return b


# shoulder and elbow of each arm: the arms leave the mantle under its hem,
# elbows behind the hands and pointing out so each arm bends naturally. The
# staff arm holds the staff out in front of him: the upper arm drops down and
# halfway forward (clear of the belt's side), the forearm reaches straight ahead
GRIP_ROW = 69  # sprite row of the staff hand, under the leather wrap
# the staff stands out in front of his right side, moved in and forward from
# where the sprite draws it at his side, so the forearm reaches forward to it
STAFF_SHIFT = Vector((0.095, -0.20, 0.0))
STAFF_GRIP = SP(36.5 - 5.5 * (125 - GRIP_ROW) / 101, GRIP_ROW, -0.085)  # on the straight shaft SP(36.5, 125)-SP(31, 24)
ARM_R = (P(56, 58, -0.045), Vector((-0.172, -0.115, 0.435)))
ARM_L = (P(80, 58, -0.03), P(98, 69, -0.01))
MANTLE_ARCH = (5.5, 3.5)  # px the mantle's hem lifts over the right and left arm


# parts that must never pass through each other (others touch by design)
CLIP_CHECKS = [
    ("upperarm_R", "mantle"), ("upperarm_L", "mantle"), ("forearm_R", "mantle"), ("forearm_L", "mantle"),
    ("hand_R", "mantle"), ("hand_L", "mantle"),
    ("upperarm_R", "cape"), ("upperarm_L", "cape"), ("forearm_R", "cape"), ("forearm_L", "cape"),
    ("hand_R", "staff"), ("hand_L", "shield"), ("forearm_L", "shield"),
    ("lantern", "staff"), ("lantern", "hand_R"), ("lantern", "forearm_R"), ("lantern", "head"),
    ("lantern", "mantle"), ("lantern", "cape"), ("mantle", "cape"),
    ("neck_lower", "cape"), ("neck_upper", "upperarm_L"), ("neck_upper", "mantle"),
    ("head", "torso"), ("head", "mantle"), ("head", "cape"), ("head", "upperarm_R"), ("head", "upperarm_L"),
    ("cape", "shin_R"), ("cape", "shin_L"), ("cape", "foot_R"), ("cape", "foot_L"),
    ("tabard", "shin_R"), ("tabard", "shin_L"),
    ("tabard", "belt"), ("tabard", "torso"),
    ("belt", "upperarm_R"), ("belt", "forearm_R"), ("belt", "upperarm_L"), ("belt", "forearm_L"),
    ("shield", "torso"), ("shield", "mantle"), ("staff", "torso"), ("staff", "mantle"), ("staff", "cape"),
]


CHAR.clip_checks = CLIP_CHECKS


def build():
    """Build (or rebuild) the Lamp Warden: mesh, material and rig.
    Returns (obj, tris per part, rest clip report)."""
    toy3d.configure(CHAR)
    return toy3d.build(build_mesh)


def render_previews(obj):
    """Front, sprite-matched 128 px, 3/4 diorama and back renders into source/."""
    shoot = preview_camera(obj)
    shoot("preview_front.png", (-0.047, -5, 0.49), (-0.047, 0, 0.49), ortho=1.06)
    # same framing as the sprite card: 128 px over 1 m, foot pivot at x 70
    shoot("preview_128.png", (-0.047, -5, 0.5), (-0.047, 0, 0.5), ortho=1.0, res=128, width=0.009, aa=0.0)
    shoot("preview_3q.png", (-1.5, -2.4, 1.3), (0, 0, 0.45))
    shoot("preview_back.png", (1.2, 2.6, 1.0), (0, 0, 0.45))


def lantern_test(obj, deg=30):
    """Swing the lantern deg degrees each way about both horizontal axes and
    report clipping for each swing."""
    from mathutils import Quaternion
    mute_ik(obj.parent, True)
    pb = obj.parent.pose.bones["lantern"]
    pb.rotation_mode = "QUATERNION"
    rest = pb.bone.matrix_local.to_quaternion()
    out = {}
    for name, axis, sign in (("toward_pole", (0, 1, 0), 1), ("away", (0, 1, 0), -1),
                             ("forward", (1, 0, 0), -1), ("back", (1, 0, 0), 1)):
        pb.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(sign * deg)) @ rest
        bpy.context.view_layer.update()
        out[name] = {k: v for k, v in clip_report(obj, evaluated=True).items() if v}
    pb.rotation_quaternion = (1, 0, 0, 0)
    mute_ik(obj.parent, False)
    bpy.context.view_layer.update()
    return out


def pose_test(obj, raise_deg=55, render=True, swing="side"):
    """Move both upper arms (swing "side": raise sideways, "forward"/"back":
    swing about the shoulders), check clipping on the deformed mesh, render
    it, then put the rig back at rest."""
    from mathutils import Quaternion
    rig = obj.parent
    mute_ik(rig, True)

    def turn(bone, deg):
        pb = rig.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        rest = pb.bone.matrix_local.to_quaternion()
        pb.rotation_quaternion = rest.inverted() @ Quaternion((0, 1, 0), math.radians(deg)) @ rest

    if swing == "side":
        turn("upperarm_R", raise_deg)   # the character's right is screen-left (-X)
        turn("upperarm_L", -raise_deg)
    else:
        for bone in ("upperarm_R", "upperarm_L"):
            pb = rig.pose.bones[bone]
            pb.rotation_mode = "QUATERNION"
            rest = pb.bone.matrix_local.to_quaternion()
            sign = -1 if swing == "forward" else 1   # he faces -Y
            pb.rotation_quaternion = rest.inverted() @ Quaternion((1, 0, 0), math.radians(sign * raise_deg)) @ rest
    bpy.context.view_layer.update()
    clips = clip_report(obj, evaluated=True)
    if render:
        shoot = preview_camera(obj)
        shoot(f"pose_{swing}_front.png", (-0.047, -5, 0.55), (-0.047, 0, 0.55), ortho=1.3)
        shoot(f"pose_{swing}_3q.png", (-1.6, -2.4, 1.4), (0, 0, 0.5))
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
    mute_ik(rig, False)
    bpy.context.view_layer.update()
    return clips


if __name__ == "__main__" and bpy.app.background:
    o, t, c = build()
    print("tris", sum(t.values()), t)
    print("clipping at rest", {k: v for k, v in c.items() if v})
    print("clipping arms raised", {k: v for k, v in pose_test(o, render=False).items() if v})
    print("glb", export_glb(o))
