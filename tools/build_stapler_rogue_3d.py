"""Build the 3D Stapler Rogue (Blender).

Live, through the Blender MCP:   exec(open("tools/build_stapler_rogue_3d.py").read())  then  build_stapler()
Headless:  D:/Blender/blender.exe --background --python tools/build_stapler_rogue_3d.py

Heights and stance come off the 128 px idle frame (player/stapler/stapler_sheet.png,
foot pivot 68,118); the look follows the concept sheet
(assets/concept/animations/stapler.png) as closely as the model allows, with
the shared machinery in tools/toy3d.py. Same rules as the Lamp Warden: one
mesh and one palette material, every part a closed solid on its own bone,
cloth with even rows, sway weights and bone chains, human hands with the right
chirality, nothing clipping.

The rogue, as agreed against the concept:
  - head: a stapler set back in the shadow of the hood, only its jaws poking
    out, a glowing yellow eye at each side of its mouth
  - hood: a heavy rogue's hood, low over the head in flat folds, a short peak
    flopping back, a deep dark opening with a pale folded rim (no emblem)
  - scarf: a thick wrap round the neck that the hood and cloak tuck into, one
    long tail hanging off the back with two holes and a forked, torn end
  - cloak: hangs from the shoulders behind the arms, open in front, torn into
    long points at the hem, with holes
  - cream: a torn cream shirt over a black body, cream sleeves, bandaged
    forearms and shins, a ragged cream skirt under the belt
  - gear: bandolier with gold rings, belt with a gold buckle and loops, a satchel
    hanging off the belt on straps, staple strips clipped to the belt
  - two stapler pistols with open jaws and gold rivets, black gloves, black
    trousers, grey knee pads with gold rivets, brown ankle straps with gold
    buckles, black boots with steel toes

Writes assets/models/stapler/stapler_rogue.glb; the .blend and previews go in
assets/models/stapler/source/ (Godot-ignored).
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

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
                   grid_normals, cloth, bandage, build_hand, grip_frame)

# name, hex, emissive
PALETTE = [
    ("outline", "050203", False), ("purple", "820ac2", False),
    ("purple_dark", "5e0696", False), ("purple_light", "a640e0", False),
    ("cream", "e9dfc6", False), ("cream_shade", "b9aa8c", False),
    ("brown", "924626", False), ("brown_dark", "66301a", False),
    ("grey", "b6aaa6", False), ("grey_dark", "857a76", False),
    ("white", "faf2ee", False), ("black", "171316", False),
    ("black_light", "2c2428", False), ("gold", "e2aa2c", False),
    ("gold_dark", "9a6a18", False), ("eye", "ffe14a", True),
]

CX = 64  # the body's centre line, px
# regions of the detail atlas (draw_stapler_details.COLLAR, BAND_FORE, BAND_SHIN)
DETAIL_COLLAR = (256, 0, 896, 256)
DETAIL_BAND_FORE = (0, 256, 320, 512)
DETAIL_BAND_SHIN = (320, 256, 640, 512)


def body_weights(z):
    """Torso and everything worn on it blend hips -> spine -> chest up the body."""
    py = 118 - z / S
    if py >= 66:
        return [("hips", 1.0)]
    if py >= 58:
        t = (66 - py) / 8
        return [("hips", 1 - t), ("spine", t)]
    if py >= 50:
        t = (58 - py) / 8
        return [("spine", 1 - t), ("chest", t)]
    return [("chest", 1.0)]


ARMS = ("upperarm_R", "upperarm_L", "forearm_R", "forearm_L", "hand_R", "hand_L", "gun_R", "gun_L")
LEGS = ("thigh_R", "thigh_L", "shin_R", "shin_L", "foot_R", "foot_L")
CLIP_CHECKS = (
    [("head", "hood"), ("head", "collar"), ("hood", "torso"), ("hood", "shirt"), ("hood", "cloak"),
     ("bandolier", "shirt"), ("skirt", "pouch"), ("skirt", "belt"), ("scarf", "cloak"), ("cloak", "skirt"),
     ("cloak", "pouch"), ("shirt", "belt")]
    + [(a, c) for a in ARMS for c in ("cloak", "scarf", "shirt", "belt", "pouch", "skirt", "bandolier")]
    + [(a, "torso") for a in ARMS[2:]]
    + [(a, c) for a in ARMS[:2] for c in ("collar", "hood")]
    + [(a, c) for a in ARMS[4:] for c in ("collar", "hood", "head")]
    + [(a, c) for a in LEGS for c in ("cloak", "skirt", "pouch", "belt")]
)

CHAR = toy3d.Character(
    name="stapler_rogue", folder="stapler", object_name="StaplerRogue", pivot=(68, 118),
    palette=PALETTE,
    part_bone={"torso": "body", "shirt": "body", "bandolier": "body", "belt": "body", "pouch": "body",
               "skirt": "body", "cloak": "body", "hood": "head", "collar": "chest", "scarf": "chest"},
    # line art (the seams of the scarf's wrap and of the bandages) drawn by
    # tools/draw_stapler_details.py (run it first) onto a detail atlas laid over the cloth
    detail=os.path.join(toy3d.ROOT, "assets", "models", "stapler", "source", "stapler_details.png"),
    body_weights=body_weights, clip_checks=CLIP_CHECKS)
toy3d.configure(CHAR)

# shoulder, elbow, grip, grip axis (up the handle), barrel direction for each arm:
# the staplers held low and forward, elbows behind the hands and out
ARM_R = (P(CX - 14, 51, 0.0), P(CX - 21, 61, 0.025), P(CX - 24, 65, -0.13), (0.0, 0.2, 1.0), (-0.3, -1.0, 0.0))
ARM_L = (P(CX + 14, 51, 0.0), P(CX + 21, 61, 0.025), P(CX + 24, 65, -0.13), (0.0, 0.2, 1.0), (0.3, -1.0, 0.0))
# hip, knee, ankle, toe direction
LEG_R = (P(CX - 6, 76), P(CX - 12, 89, -0.035), P(CX - 18, 108, -0.01), (-0.7, -0.7, 0))
LEG_L = (P(CX + 6, 76), P(CX + 13, 89, -0.035), P(CX + 20, 108, -0.01), (0.7, -0.7, 0))

NECK = P(CX + 0.5, 118, 0.008)   # the hood's and the scarf's shared axis
NECK_SY = 0.92


def ring_pt(c, r_px, a, sy, py):
    return Vector((c.x + r_px * S * math.cos(a), c.y + r_px * S * math.sin(a) * sy, H(py)))


def interp(prof, py):
    """Linear interpolation in a [(py, value)] table sorted by py."""
    if py <= prof[0][0]:
        return prof[0][1]
    for (y0, v0), (y1, v1) in zip(prof, prof[1:]):
        if py <= y1:
            return v0 + (v1 - v0) * (py - y0) / (y1 - y0)
    return prof[-1][1]


def ang_from_front(a):
    """Angle in degrees between direction a and straight ahead (-Y)."""
    return abs((math.degrees(a) + 90 + 180) % 360 - 180)


def outward_from(axis_x, axis_y):
    return lambda p: Vector((p.x - axis_x, p.y - axis_y, 0.0))


# -- head: the stapler and the hood ---------------------------------------------------

def build_head(b):
    """The stapler, pointing forward (-Y): a grey top arm over a darker base, a
    dark mouth between them with a glowing eye at each side, a hinge at the back."""
    x = P(CX + 1, 0).x
    back, front = 0.045, -0.165
    length = back - front
    mid = (back + front) / 2
    b.finish(b.box(Vector((x, mid, H(34))), (0.072, length, 0.026)), "grey_dark", "head", smooth=False)
    b.finish(b.box(Vector((x, front + 0.008, H(32.5))), (0.074, 0.016, 0.012)), "grey", "head", smooth=False)
    b.finish(b.box(Vector((x, mid + 0.012, H(29.5))), (0.056, length - 0.03, 0.03)), "outline", "head", smooth=False)
    tilt = math.radians(5)
    arm_dir = Vector((0, -math.cos(tilt), -math.sin(tilt)))
    arm_c = Vector((x, mid - 0.004, H(24.5)))
    b.finish(b.box(arm_c, (0.068, length + 0.004, 0.036), zdir=(0, -math.sin(tilt), math.cos(tilt))),
             "grey", "head", smooth=False)
    nose = arm_c + arm_dir * (length / 2)
    b.finish(b.tube([nose + Vector((-0.034, 0, 0)), nose + Vector((0.034, 0, 0))], 0.018, 8), "grey", "head")
    b.finish(b.box(arm_c + Vector((0, 0.0, 0.019)), (0.03, length - 0.03, 0.004)), "white", "head", smooth=False)
    hinge = Vector((x, back - 0.006, H(29)))
    b.finish(b.tube([hinge + Vector((-0.04, 0, 0)), hinge + Vector((0.04, 0, 0))], 0.012, 8), "black", "head")
    for s in (-1, 1):  # eyes glowing in the dark of the mouth, under the jaws' overhang
        b.finish(b.sphere(Vector((x + s * 0.03, -0.075, H(29.5))), 0.011, 8, 5, (0.45, 1, 1)), "eye", "head")


def build_hood(b):
    """A heavy rogue's hood: low over the head, folded flat, a short peak
    flopping back, a deep opening framing the stapler with a pale folded rim,
    the dark inside showing. Its hem tucks into the scarf."""
    rows, cols = 22, 28
    pys = [3 + (41 - 3) * j / (rows - 1) for j in range(rows)]
    prof = [(3, 0.5), (6, 3.8), (9.5, 8.2), (13, 12.8), (17, 16.4), (22, 18.4), (28, 19), (35, 18.8), (41, 16)]

    def opening(py):  # half-width of the face opening in degrees
        return 0.0 if py < 14.5 else 34.0 * min(1.0, math.sqrt((py - 14.5) / 6.0))

    # the six columns either side of straight ahead bend to follow the opening's
    # arch, so its edge is a smooth curve rather than steps
    edge, reach = 3, 7

    def angle(j, i):
        k = i if i <= cols // 2 else i - cols
        w = opening(pys[j])
        if w > 0 and abs(k) <= reach:
            if abs(k) <= edge:
                return math.radians(-90 + w * k / edge)
            base = 360 * reach / cols
            return math.radians(-90 + math.copysign(w + (base - w) * (abs(k) - edge) / (reach - edge), k))
        return math.radians(-90 + 360 * k / cols)

    mids = []
    for j, py in enumerate(pys):
        row = []
        for i in range(cols):
            a = angle(j, i)
            front = max(0.0, -math.sin(a)) ** 2
            r = interp(prof, py) * (1 + 0.035 * math.sin(5 * a + 0.6 * j))   # flat folds
            p = ring_pt(NECK, r, a, NECK_SY, py)
            p.y -= 3.2 * S * front * math.exp(-((py - 15.5) / 4.0) ** 2)     # the brow overhangs
            p.y -= 1.2 * S * front * smoothstep((py - 14) / 6)                # the sides come forward
            t = max(0.0, min(1.0, (16 - py) / 13))                            # the point leans forward
            p.y -= 0.075 * t * t
            p.x += 0.006 * t * t
            p.z -= 0.012 * t ** 3
            row.append(p)
        mids.append(row)
    norms = grid_normals(mids, wrap=True, outward=outward_from(NECK.x, NECK.y))

    def is_open(j, i):
        if j < 0 or j >= rows - 1:
            return False
        k = i % cols
        k = k if k <= cols // 2 else k - cols
        return -edge <= k < edge and opening(pys[j]) > 0 and opening(pys[j + 1]) > 0

    verts, fronts, backs = cloth(b, mids, norms, 1.4 * S, keep=lambda j, i: not is_open(j, i), wrap=True)
    b.finish(verts, "purple", "hood", smooth=False)
    b.paint(list(backs.values()), "outline")                      # the deep inside
    for (j, i), f in fronts.items():
        if any(is_open(jj, ii) for jj, ii in ((j, i - 1), (j, i + 1), (j + 1, i), (j - 1, i))):
            b.paint(f, "purple_light")                          # the folded rim (no painted creases)
    b.joints["head"] = (P(CX, 42, 0.0), P(CX, 20, 0.0), "chest")


# -- scarf ---------------------------------------------------------------------------

COLLAR_R, COLLAR_TUBE, COLLAR_PY, COLLAR_FLAT = 13.5, 5.5, 42.0, 0.82


def build_scarf(b):
    """A thick wrap round the neck, then one long tail off the back of his right
    shoulder that hangs and curls, two holes in it and a forked, torn end."""
    prof = [(COLLAR_R + COLLAR_TUBE * math.cos(t), COLLAR_PY - COLLAR_FLAT * COLLAR_TUBE * math.sin(t))
            for t in (2 * math.pi * k / 12 for k in range(12))]

    def wrap(p, a):
        k = 1 + 0.05 * math.sin(3 * a + 0.5)
        p.x *= k
        p.y *= k
        return p
    verts, bands, _ = b.lathe(vprof(prof), 18, Matrix.Translation(Vector((NECK.x, NECK.y, 0))), sy=NECK_SY,
                              loop=True, warp=wrap)
    faces = b.finish(verts, "purple", "collar", smooth=False)

    # the turns of the wrap are drawn seams (draw_stapler_details.COLLAR): u round
    # the neck, v round the tube of cloth
    def collar_uv(co):
        dx, dy = co.x - NECK.x, (co.y - NECK.y) / NECK_SY
        r = math.hypot(dx, dy) / S
        py = CHAR.ground - co.z / S
        u = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
        v = (math.atan2((COLLAR_PY - py) / COLLAR_FLAT, r - COLLAR_R) / (2 * math.pi)) % 1.0
        return u, v
    b.map_detail(faces, DETAIL_COLLAR, collar_uv, wrap=True, wrap_v=True)

    # the tail: a ribbon down a path, turning a little as it hangs
    path = [P(CX - x, py, y) for x, py, y in ((6, 39, 0.12), (11, 39.5, 0.21), (16, 41.5, 0.28), (21, 45, 0.33),
                                               (26, 49.5, 0.37), (30, 54.5, 0.39), (32, 59, 0.385), (31, 63, 0.36))]
    rows, cols = 15, 4
    lengths = [0.0]
    for p, q in zip(path, path[1:]):
        lengths.append(lengths[-1] + (q - p).length)
    total = lengths[-1]

    def along(s):
        for k in range(len(path) - 1):
            if s <= lengths[k + 1] or k == len(path) - 2:
                f = (s - lengths[k]) / (lengths[k + 1] - lengths[k])
                return path[k].lerp(path[k + 1], f), (path[k + 1] - path[k]).normalized()

    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        c, tan = along(total * t)
        up = Vector((0, 0, 1))
        across = (up - tan * tan.dot(up)).normalized()           # its width stands up, flag-like
        twist = 1.0 * t                                           # and turns as it streams back
        across = (across * math.cos(twist) + tan.cross(across) * math.sin(twist)).normalized()
        normal = tan.cross(across).normalized()
        width = (7.0 + 7.0 * smoothstep(t / 0.3) - 3.5 * t) * S   # gathered where it leaves the wrap
        c = c + normal * 1.2 * S * math.sin(t * 9.0)              # ripples down its length
        mids.append([c + across * width * (k / (cols - 1) - 0.5) for k in range(cols)])
    # forked end: the last rows split into two tails, each pinched to a point
    fork = rows - 4
    last = mids[-1]
    l_tip = (last[0] + last[1]) / 2 + (last[0] - last[-1]) * 0.15 + (mids[-1][0] - mids[-2][0]) * 1.2
    r_tip = (last[2] + last[3]) / 2 + (mids[-1][3] - mids[-2][3]) * 0.6
    last[0], last[1] = l_tip + (last[0] - l_tip) * 0.15, l_tip + (last[1] - l_tip) * 0.15
    last[2], last[3] = r_tip + (last[2] - r_tip) * 0.15, r_tip + (last[3] - r_tip) * 0.15
    holes = {(4, 1), (8, 1)}
    norms = grid_normals(mids)

    verts, fronts, backs = cloth(b, mids, norms, 1.0 * S,
                                 keep=lambda j, i: not (j >= fork and i == 1), holes=holes)
    faces = b.finish(verts, "purple", "scarf", smooth=False)
    b.paint(list(backs.values()), "purple_dark")
    b.joints["scarf_1"] = (path[0], path[3], "chest")
    b.joints["scarf_2"] = (path[3], path[-1], "scarf_1")
    ids = [(b.bone_index("chest"), -0.1), (b.bone_index("scarf_1"), 0.25), (b.bone_index("scarf_2"), 0.75)]
    for v in verts:
        t = min(range(rows), key=lambda j: min((v.co - m).length for m in mids[j])) / (rows - 1)
        ws = [(i, max(0.0, 1.0 - abs(t - c) / 0.4)) for i, c in ids]
        tot = sum(w for _, w in ws) or 1.0
        dv = v[b.deform]
        dv.clear()
        for i, w in ws:
            if w > 0:
                dv[i] = w / tot
    for f in faces:
        for loop in f.loops:
            t = min(range(rows), key=lambda j: min((loop.vert.co - m).length for m in mids[j])) / (rows - 1)
            loop[b.sway].uv = (t ** 1.5, 0.0)


# -- body ---------------------------------------------------------------------------

TORSO_SY = 0.72
TORSO_PROF = [(0, 76), (12.5, 76), (13, 72), (12, 66), (13, 58), (14.5, 50), (14.5, 45), (10, 41), (7, 39), (0, 38)]
SHIRT_OPEN = 32.0    # half-width in degrees of the shirt's open front
SHIRT_HEM = 69.5     # it tucks under the belt (67-72)
SHIRT_FOLLOW = (13.0, 5.0, 60.0)   # reach, fade (px from the upper arm's axis), lowest row (py) that follows
ARMHOLE = (2.4, 1.6)          # cut cells within, then fit the edge at, px off the sleeve
BELT_TOP, BELT_BOTTOM = 67.0, 72.0


def torso_r(py):
    pts = sorted(TORSO_PROF[1:-1], key=lambda q: q[1])
    for (r0, y0), (r1, y1) in zip(pts, pts[1:]):
        if y0 <= py <= y1:
            return r0 + (r1 - r0) * (py - y0) / (y1 - y0)
    return pts[0][0] if py < pts[0][1] else pts[-1][0]


def body_pt(px, py, r, sy=TORSO_SY):
    """Point on an ellipse (radius r px, depth scale sy) round the body at row
    py, in front, at sprite column px; also the outward normal there."""
    dx = max(-r * 0.97, min(r * 0.97, px - CX))
    y = -sy * math.sqrt(r * r - dx * dx)
    n = Vector((dx, y / (sy * sy), 0)).normalized()
    return P(px, py, y * S), n


def shirt_lift(px, py):
    """How far a strap lying on him sits off the black body: on the shirt, or
    on the body where the shirt is open."""
    r = torso_r(py)
    dx = max(-r * 0.97, min(r * 0.97, px - CX))
    d = ang_from_front(math.atan2(-math.sqrt(r * r - dx * dx), dx))   # the shirt's own angle round the body
    return 0.6 + (2.0 - 0.45 * smoothstep((py - 63.5) / 3.0)) * smoothstep((d - (SHIRT_OPEN - 12)) / 6.0)


def arm_gap(p, side):
    """(distance in px from upper arm side's surface, closest point on its axis)."""
    sh, el = (ARM_R if side == "R" else ARM_L)[:2]
    seg = el - sh
    t = max(0.0, min(1.0, (p - sh).dot(seg) / seg.length_squared))
    c = sh + seg * t
    return (p - c).length / S - (5.0 - 0.7 * t), c


def build_torso(b):
    """Black body under a cream shirt open down the front, its hem tucked
    under the belt and its armholes fitted round the sleeves."""
    verts, _, _ = b.lathe(vprof(TORSO_PROF), 14, Matrix.Translation(P(CX, 118)), sy=TORSO_SY)
    for f in b.finish(verts, "black", "torso"):
        if min(arm_gap(f.calc_center_median(), s)[0] for s in "RL") < 4.0:
            b.paint([f], "cream")                    # under the armholes the body shows cloth, not black
    b.joints["root"] = (Vector((0, 0, 0)), Vector((0, -0.12, 0)), None)
    b.joints["hips"] = (P(CX, 74), P(CX, 62), "root")
    b.joints["spine"] = (P(CX, 62), P(CX, 52), "hips")
    b.joints["chest"] = (P(CX, 52), P(CX, 42), "spine")

    rows, cols = 13, 30
    pys = [44 + (SHIRT_HEM - 44) * j / (rows - 1) for j in range(rows)]
    angles = [math.radians(-90 + SHIRT_OPEN + (360 - 2 * SHIRT_OPEN) * i / cols) for i in range(cols + 1)]
    mids = []
    for j, py in enumerate(pys):
        row = []
        for i, a in enumerate(angles):
            r = torso_r(py) + 0.9 - 0.45 * smoothstep((py - 63.5) / 3.0)   # snug where the belt holds it
            jag = 0.03 * math.sin(j * 2.1) if i in (0, cols) and py < 62 else 0.0  # ragged front edges
            row.append(ring_pt(P(CX, 118), r, a + jag, TORSO_SY, py))
        mids.append(row)

    def cut(j, i):  # armholes: cells the sleeves pass through
        corners = (mids[j][i], mids[j][i + 1], mids[j + 1][i], mids[j + 1][i + 1])
        return any(arm_gap(c, s)[0] < ARMHOLE[0] for c in corners for s in "RL")
    gone = {(j, i) for j in range(rows - 1) for i in range(cols) if cut(j, i)}
    # pull the armholes' edges onto a smooth line just clear of each sleeve
    for j in range(rows):
        for i in range(cols + 1):
            around = [(jj, ii) for jj in (j - 1, j) for ii in (i - 1, i) if 0 <= jj < rows - 1 and 0 <= ii < cols]
            if any(c in gone for c in around) and not all(c in gone for c in around):
                p = mids[j][i]
                side = min("RL", key=lambda s: arm_gap(p, s)[0])
                gap, c = arm_gap(p, side)
                mids[j][i] = c + (p - c).normalized() * ((p - c).length - (gap - ARMHOLE[1]) * S)
    norms = grid_normals(mids, outward=outward_from(P(CX, 0).x, 0.0))
    verts, fronts, backs = cloth(b, mids, norms, 0.5 * S, keep=lambda j, i: (j, i) not in gone)
    b.finish(verts, "cream", "shirt", smooth=False)
    # round the armholes the shirt moves with the sleeve, so a raised arm
    # stretches the cloth instead of cutting through it
    toy3d.follow_limbs(b, [v for v in verts if v.co.z > H(SHIRT_FOLLOW[2])], H(0),
                       {"upperarm_R": ARM_R[:2], "upperarm_L": ARM_L[:2]},
                       reach=SHIRT_FOLLOW[0], fade=SHIRT_FOLLOW[1], pin=0.1)
    b.paint(list(backs.values()), "cream_shade")   # its inside (the folds are geometry: no painted valleys)


def build_gear(b):
    """Bandolier, belt, satchel and staple strips: everything sits on what holds it up."""
    # bandolier from his left shoulder across to the right hip, gold rings on it
    pts = [(CX + 11 - 21 * t, 43 + 24 * t) for t in (k / 10 for k in range(11))]
    path, normals = [], []
    for px, py in pts:
        lift = shirt_lift(px, py) + 1.2 * max(0.0, (47 - py) / 4)  # over the shirt's slope up to the neck
        p, n = body_pt(px, py, torso_r(py) + lift)
        path.append(p)
        normals.append(n)
    b.finish(b.strap(path, P(CX, 0), 3.6 * S, 1.1 * S, normals), "brown", "bandolier", smooth=False)
    for t in (0.22, 0.45, 0.68):
        k = t * 10
        i = int(k)
        c = path[i].lerp(path[i + 1], k - i)
        _, n = body_pt(*pts[i], torso_r(pts[i][1]))
        b.finish(b.ring(c + n * 0.9 * S, n, 1.0 * S, 2.3 * S, 0.9 * S, 10), "gold", "bandolier", smooth=False)

    # belt, its loops and a gold buckle
    belt = [(torso_r(BELT_BOTTOM) + 2.4, BELT_BOTTOM), (torso_r(BELT_TOP) + 2.4, BELT_TOP),
            (torso_r(BELT_TOP) + 1.0, BELT_TOP), (torso_r(BELT_BOTTOM) + 1.0, BELT_BOTTOM)]
    b.finish(b.lathe(vprof(belt), 28, Matrix.Translation(P(CX, 118)), sy=TORSO_SY, loop=True)[0],
             "brown", "belt", smooth=False)
    mid_py = (BELT_TOP + BELT_BOTTOM) / 2
    for px in (CX - 11, CX + 9):
        p, n = body_pt(px, mid_py, torso_r(mid_py) + 2.75)
        b.finish(b.box(p, (1.6 * S, 0.7 * S, 6.4 * S), xdir=Vector((0, 0, 1)).cross(n)), "brown_dark", "belt",
                 smooth=False)
    p, n = body_pt(CX + 1, mid_py, torso_r(mid_py) + 2.8)
    side = Vector((0, 0, 1)).cross(n).normalized()
    for off, size in ((side * 2.4, (0.9, 0.8, 5.6)), (-side * 2.4, (0.9, 0.8, 5.6)),
                      (Vector((0, 0, 2.4)), (5.6, 0.8, 0.9)), (Vector((0, 0, -2.4)), (5.6, 0.8, 0.9))):
        b.finish(b.box(p + off * S, tuple(v * S for v in size), xdir=side), "gold", "belt", smooth=False)
    b.finish(b.box(p + n * 0.2 * S, (3.6 * S, 0.5 * S, 0.8 * S), xdir=side), "grey", "belt", smooth=False)

    # satchel on his right hip, hanging off the belt on two straps
    top_py, bottom_py = BELT_BOTTOM - 0.5, BELT_BOTTOM + 7.5
    hi, _ = body_pt(CX - POUCH_X, top_py, skirt_r(top_py) + 0.9, skirt_sy(top_py))
    lo, n0 = body_pt(CX - POUCH_X, bottom_py, skirt_r(bottom_py) + 0.9, skirt_sy(bottom_py))
    side = Vector((0, 0, 1)).cross(n0).normalized()
    up = (hi - lo).normalized()
    n = up.cross(side).normalized()
    if n.dot(n0) < 0:
        n = -n
    for e in (-1, 1):   # both ends of the back must clear the curve
        for q in (top_py, bottom_py):
            p, _ = body_pt(CX - POUCH_X + e * 5, q, skirt_r(q) + 0.9, skirt_sy(q))
            lo += n * max(0.0, (p - lo).dot(n))
            hi = lo + up * (hi - lo).length
    centre = (hi + lo) / 2 + n * 2.2 * S
    first = len(b.bm.verts)
    b.finish(b.box(centre, (10 * S, 4.4 * S, 8 * S), xdir=side, zdir=up), "brown", "pouch", smooth=False)
    flap = centre + n * 0.6 * S + up * 2.2 * S
    b.finish(b.box(flap, (10.6 * S, 3.8 * S, 4 * S), xdir=side, zdir=up), "brown_dark", "pouch", smooth=False)
    b.finish(b.box(flap + n * 2.1 * S - up * 1.6 * S, (1.8 * S, 0.6 * S, 2 * S), xdir=side, zdir=up), "gold",
             "pouch", smooth=False)
    b.bm.verts.ensure_lookup_table()
    satchel = [b.bm.verts[i] for i in range(first, len(b.bm.verts))]
    for o in (-3.2, 3.2):
        px = CX - POUCH_X + o
        a, na = body_pt(px, BELT_TOP + 0.3, torso_r(BELT_TOP) + 2.7)
        c, _ = body_pt(px, BELT_BOTTOM + 0.3, torso_r(BELT_BOTTOM) + 2.7)
        d = centre + up * 4.0 * S + n * 2.4 * S + side * o * S
        b.finish(b.strap([a, c, d], P(CX, 0), 2.0 * S, 0.6 * S), "brown_dark", "pouch", smooth=False)

    # staple strips clipped to the belt at his left side
    first = len(b.bm.verts)
    for k, px in enumerate((CX + 13, CX + 15, CX + 17)):
        clip, n = body_pt(px, BELT_TOP + 2, torso_r(BELT_TOP + 2) + 2.9)
        side = Vector((0, 0, 1)).cross(n).normalized()
        b.finish(b.box(clip, (2.6 * S, 0.8 * S, 4.6 * S), xdir=side), "grey_dark", "pouch", smooth=False)
        length = 6 + 2 * k
        rows = [BELT_BOTTOM - 0.5 + length * f / 4 for f in range(5)]
        for lift, w, h, colour in ((1.5, 2.2, 1.0, "grey"), (2.35, 1.4, 0.4, "white")):
            pts = [body_pt(px, q, skirt_r(q) + lift, skirt_sy(q)) for q in rows]
            b.finish(b.strap([p for p, _ in pts], P(CX, 0), w * S, h * S, [m for _, m in pts]), colour, "pouch",
                     smooth=False)
    b.bm.verts.ensure_lookup_table()
    strips = [b.bm.verts[i] for i in range(first, len(b.bm.verts))]
    return [satchel, strips]


SKIRT_TOP, SKIRT_HEM = 70.5, 83.0
POUCH_X = 15.0   # px right of centre (his right) where the satchel hangs, at his side
HELD = (5.0, 4.0)   # px round hung gear where the skirt is held still, and the fade beyond


SKIRT_SNUG = 0.6   # px below the belt the skirt stays snug before it flares


def skirt_r(py):
    snug = BELT_BOTTOM + SKIRT_SNUG
    if py <= snug:
        return torso_r(py) + 0.3
    return interp([(snug, torso_r(snug) + 0.3), (77, 16.0), (SKIRT_HEM, 19.0), (SKIRT_HEM + 6, 20.0)], py)


def skirt_sy(py):
    return TORSO_SY + 0.06 * smoothstep((py - 72) / 12)


def build_skirt(b):
    """Ragged cream cloth hanging from under the belt over the hips, open at the
    front; near the thighs it follows them, so a kick swings it."""
    rows, cols, half = 8, 30, 30.0
    pys = [SKIRT_TOP + (SKIRT_HEM - SKIRT_TOP) * j / (rows - 1) for j in range(rows)]
    angles = [math.radians(-90 + half + (360 - 2 * half) * i / cols) for i in range(cols + 1)]
    mids = []
    for j, py in enumerate(pys):
        row = []
        for i, a in enumerate(angles):
            q = py + ((1.5 + 3.0 * hash01(i + 40)) if (j == rows - 1 and i % 2 == 0) else 0.0)
            row.append(ring_pt(P(CX, 118), skirt_r(q), a, skirt_sy(q), q))
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(P(CX, 0).x, 0.0))
    tears = {(rows - 2, 7), (rows - 2, 22)}
    verts, fronts, backs = cloth(b, mids, norms, 0.5 * S, keep=lambda j, i: (j, i) not in tears)
    faces = b.finish(verts, "cream", "skirt", smooth=False)
    b.paint(list(backs.values()), "cream_shade")   # its inside (the folds are geometry: no painted valleys)
    b.set_sway(faces, H(BELT_BOTTOM), H(SKIRT_HEM))
    return verts


def build_cloak(b):
    """Long purple cloak from the shoulders (tucked under the scarf), hanging
    behind the arms and open in front; torn into long points at the hem, holes
    through it. Even rows, a sway weight and a three-bone chain."""
    rows, cols = 16, 26
    top_py, hem_py = 44.0, 106.0
    prof = [(44, 15.6), (50, 21), (62, 25), (78, 29.5), (92, 34), (106, 38)]

    def span(t):   # the arc it covers widens towards the hem
        return math.radians(16 - 14 * t), math.radians(164 + 14 * t)
    centre = P(CX, 118, 0.02)
    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        py = top_py + (hem_py - top_py) * t
        row = []
        a0, a1 = span(t)
        for i in range(cols + 1):
            a = a0 + (a1 - a0) * i / cols
            q = py
            if j == rows - 1:   # long torn points
                q += (5 + 9 * hash01(i)) if i % 2 == 0 else -2.0
            elif j == rows - 2 and i % 2 == 0:
                q += 2 * hash01(i)
            fold = 3.5 * t * math.sin(6 * a + 0.4)
            p = ring_pt(centre, interp(prof, q) + fold, a, 0.95, q)
            p.y += 0.05 * t * t * max(0.0, math.sin(a))      # billows out behind
            p.x += 0.02 * t * t
            row.append(p)
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre.x, centre.y))
    holes = {(rows - 5, 5): 2, (rows - 4, 14): 2, (rows - 7, 19): 2, (6, 10): 2, (rows - 6, 2): 1, (9, 16): 1}
    tears = {(rows - 2, 9), (rows - 3, 9), (rows - 2, 18)}
    verts, fronts, backs = cloth(b, mids, norms, 1.3 * S, keep=lambda j, i: (j, i) not in tears, holes=holes)
    faces = b.finish(verts, "purple", "cloak", smooth=False)
    b.paint(list(backs.values()), "purple_dark")   # its lining (the folds are geometry: no painted streaks)
    b.set_sway(faces, H(top_py), H(hem_py))

    c = cols // 2
    js = [mids[min(rows - 1, round((py - top_py) / (hem_py - top_py) * (rows - 1)))][c] for py in (46, 66, 86, 102)]
    for i in range(3):
        b.joints[f"cloak_{i + 1}"] = (js[i], js[i + 1], "chest" if i == 0 else f"cloak_{i}")
    chain_weights(b, verts, H(top_py), H(top_py) - H(hem_py),
                  (("chest", -0.08), ("cloak_1", 0.2), ("cloak_2", 0.55), ("cloak_3", 0.9)), 0.35)


# -- arms and the stapler pistols -----------------------------------------------------

def build_gun(b, grip, u, d, part):
    """A mini stapler held like a pistol: black grip, grey base, purple top arm
    hinged open at the front like jaws, gold rivets at the hinge."""
    up = Vector(u).normalized()
    d = (d - up * d.dot(up)).normalized()
    side = d.cross(up).normalized()
    b.finish(b.box(grip, (0.022, 0.03, 0.062), xdir=side, zdir=up), "black", part, smooth=False)
    b.finish(b.box(grip - up * 0.031, (0.026, 0.034, 0.006), xdir=side, zdir=up), "grey_dark", part, smooth=False)
    base_c = grip + up * 0.04 + d * 0.05
    b.finish(b.box(base_c, (0.034, 0.17, 0.018), xdir=side, zdir=up), "grey", part, smooth=False)
    b.finish(b.box(base_c + d * 0.078 + up * 0.012, (0.036, 0.016, 0.008), xdir=side, zdir=up), "grey_dark", part,
             smooth=False)                                           # the anvil
    hinge = base_c - d * 0.08 + up * 0.009            # back end of the base's top face
    open_ = math.radians(7)
    along = d * math.cos(open_) + up * math.sin(open_)
    lid_up = up * math.cos(open_) - d * math.sin(open_)
    top_c = hinge + along * 0.085 + lid_up * 0.014     # its back edge rests on the hinge
    b.finish(b.box(hinge + up * 0.004 + d * 0.004, (0.036, 0.016, 0.026), xdir=side, zdir=up), "grey_dark", part,
             smooth=False)                                           # the hinge block joining top and base
    b.finish(b.box(top_c, (0.038, 0.17, 0.028), xdir=side, zdir=lid_up), "purple", part, smooth=False)
    b.finish(b.box(top_c + lid_up * 0.0145, (0.016, 0.13, 0.003), xdir=side, zdir=lid_up), "purple_light", part,
             smooth=False)
    b.finish(b.box(top_c + along * 0.075 - lid_up * 0.016, (0.03, 0.014, 0.008), xdir=side, zdir=lid_up),
             "grey_dark", part, smooth=False)                        # the striker
    for s in (-1, 1):
        b.finish(b.sphere(hinge + up * 0.006 + side * s * 0.0185, 0.0062, 8, 4, (1, 1, 1)), "gold", part)


def build_arm(b, shoulder, elbow, grip, axis, barrel, side):
    """Cream sleeve, bandaged forearm, brown wrist band, black glove on a pistol grip."""
    u, f, w = grip_frame(elbow, grip, axis, side)
    R = 0.011 + 0.8 * S
    wrist = grip - f * (R + 4.0 * S) + w * (R + 1.3 * S) * 0.5
    upper, fore, hand, gun = f"upperarm_{side}", f"forearm_{side}", f"hand_{side}", f"gun_{side}"
    b.finish(b.sphere(shoulder, 5.0 * S, 10, 6, (1, 0.9, 0.85)), "cream", upper)
    sleeve = b.finish(b.tube([shoulder, shoulder.lerp(elbow, 0.55), elbow], 4.0 * S, 10,
                             rs=[4.3 * S, 4.4 * S, 3.7 * S]), "cream", upper)
    for fc in sleeve:
        if (fc.calc_center_median() - shoulder).length > 0.75 * (elbow - shoulder).length:
            b.paint([fc], "cream_shade")                             # the rolled cuff
    b.finish(b.sphere(elbow, 3.7 * S, 8, 5), "cream_shade", fore)
    bandage(b, [elbow, wrist], [3.6 * S, 3.0 * S], fore, 4, region=DETAIL_BAND_FORE)
    b.finish(b.ring(elbow.lerp(wrist, 0.86), wrist - elbow, 2.6 * S, 3.7 * S, 1.8 * S), "brown", fore, smooth=False)
    palm = build_hand(b, grip, u, f, w, R, hand, colour="black", knuckle="black_light")
    b.finish(b.tube([wrist, palm - f * 1.8 * S], 3.0 * S, 8, rs=[3.2 * S, 2.8 * S]), "black", hand)
    build_gun(b, grip, u, Vector(barrel).normalized(), gun)
    b.joints[upper] = (shoulder, elbow, "chest")
    b.joints[fore] = (elbow, wrist, upper)
    b.joints[hand] = (wrist, grip, fore)
    b.joints[gun] = (grip, grip + Vector(barrel).normalized() * 0.1, hand)


# -- legs -----------------------------------------------------------------------------

def build_leg(b, hip, knee, ankle, toe, s):
    """Black trousers, grey knee pad with gold rivets, bandaged shin, brown ankle
    strap with a gold buckle, black boot with a steel toe and sole."""
    toe = Vector(toe).normalized()
    out = Vector((-1 if s == "R" else 1, 0, 0))
    thigh, shin, foot = f"thigh_{s}", f"shin_{s}", f"foot_{s}"
    base = Vector((ankle.x, ankle.y, 0.0))
    b.joints[thigh] = (hip, knee, "hips")
    b.joints[shin] = (knee, ankle, thigh)
    b.joints[foot] = (ankle, base + toe * 0.07 + Vector((0, 0, 0.02)), shin)
    # the thigh starts just below the hip joint, so swinging it never lifts its top into the belt
    b.finish(b.tube([hip.lerp(knee, 0.18), hip.lerp(knee, 0.55), knee], 4.8 * S, 10, rs=[5.2 * S, 5.5 * S, 4.4 * S]),
             "black", thigh)
    pad = knee + Vector((0, -2.6 * S, 0))
    b.finish(b.sphere(pad, 4.6 * S, 10, 6, (1, 0.6, 1.05)), "grey", shin)
    b.finish(b.sphere(pad + Vector((0, -2.0 * S, 1.2 * S)), 1.3 * S, 6, 4, (1, 0.6, 1)), "white", shin)
    for sx in (-1, 1):
        b.finish(b.sphere(pad + Vector((sx * 3.3 * S, -1.9 * S, -0.6 * S)), 0.9 * S, 6, 4), "gold", shin)
    b.finish(b.ring(knee, Vector((0, 0, 1)) + out * 0.2, 4.0 * S, 4.7 * S, 1.6 * S, 10), "brown", shin, smooth=False)
    top = knee.lerp(ankle, 0.14)
    bandage(b, [top, top.lerp(ankle, 0.5), ankle], [4.1 * S, 3.8 * S, 3.2 * S], shin, 5, region=DETAIL_BAND_SHIN)
    strap = knee.lerp(ankle, 0.86)
    b.finish(b.ring(strap, ankle - knee, 3.0 * S, 4.0 * S, 2.0 * S, 10), "brown", shin, smooth=False)
    b.finish(b.sphere(strap + out * 4.0 * S, 1.7 * S, 8, 4, (0.45, 1, 1)), "gold", shin)   # round buckle
    build_boot(b, base, toe, ankle, foot)


BOOT_SOLE = 0.013     # sole thickness, m
BOOT_BACK, BOOT_TIP = -0.034, 0.062   # along the foot from under the ankle


def boot_size(u):
    """(width, height above the sole) of the boot's upper at u along the foot:
    high round the ankle, low over the toes, rounded off at heel and tip."""
    w = interp([(BOOT_BACK, 0.044), (0.0, 0.046), (0.03, 0.054), (0.05, 0.052), (BOOT_TIP, 0.05)], u)
    h = interp([(BOOT_BACK, 0.038), (-0.015, 0.048), (0.005, 0.044), (0.025, 0.031), (0.045, 0.025),
                (BOOT_TIP, 0.022)], u)
    k = 1.0
    if u > 0.044:
        k = math.sqrt(max(0.0, 1 - ((u - 0.044) / (BOOT_TIP - 0.044)) ** 2))
    elif u < -0.022:
        k = math.sqrt(max(0.0, 1 - ((u + 0.022) / (BOOT_BACK + 0.022)) ** 2))
    return w * max(k, 0.12), h * max(k, 0.25)


def build_boot(b, base, toe, ankle, part):
    """A low rounded boot like the concept's: a domed upper lofted along the
    foot on a thick sole, a cream band across the instep, the steel toe cap,
    and the shaft rising into the ankle."""
    up = Vector((0, 0, 1))
    side = up.cross(toe).normalized()     # towards the foot's left
    z0 = BOOT_SOLE
    n_sec, n_ring = 12, 14

    def ring_at(u, lift=0.0):
        w, h = boot_size(u)
        pts = []
        for k in range(n_ring):
            ph = 2 * math.pi * k / n_ring
            c, sn = math.cos(ph), math.sin(ph)
            x = (w / 2 + lift) * math.copysign(abs(c) ** 0.75, c)
            z = z0 + h / 2 + (h / 2 + lift) * math.copysign(abs(sn) ** 0.75, sn)
            pts.append(base + toe * u + side * x + up * z)
        return pts

    bm = b.bm
    us = [BOOT_BACK + (BOOT_TIP - BOOT_BACK) * k / (n_sec - 1) for k in range(n_sec)]
    rings = [[bm.verts.new(p) for p in ring_at(u)] for u in us]
    made = [v for r in rings for v in r]
    for A, B in zip(rings, rings[1:]):
        for k in range(n_ring):
            m = (k + 1) % n_ring
            bm.faces.new((A[k], A[m], B[m], B[k]))
    for r, u in ((rings[0], us[0]), (rings[-1], us[-1])):   # close the heel and the tip
        w, h = boot_size(u)
        c = bm.verts.new(base + toe * u + up * (z0 + h / 2))
        made.append(c)
        for k in range(n_ring):
            bm.faces.new((r[k], r[(k + 1) % n_ring], c))
    b.finish(made, "black_light", part)
    # thick sole, a little proud of the upper all round
    outline = []
    for k in range(10):
        u = BOOT_BACK - 0.004 + (BOOT_TIP + 0.02) * k / 9
        outline.append((u, boot_size(min(u, 0.044))[0] / 2 + 0.004))
    pts = [(u, -hw) for u, hw in outline] + [(u, hw) for u, hw in reversed(outline)]
    pts = [(u, y * (math.sqrt(max(0.0, 1 - ((u - 0.05) / 0.032) ** 2)) if u > 0.05 else 1.0)) for u, y in pts]
    pts = [(u, y if abs(y) > 0.004 or u < 0.07 else math.copysign(0.004, y)) for u, y in pts]
    b.finish(b.slab(pts, BOOT_SOLE, frame(base + up * (BOOT_SOLE / 2), up, toe)), "black", part, smooth=False)
    # cream band across the instep, lying on the upper
    u = 0.014
    w, h = boot_size(u)
    band, normals = [], []
    for k in range(-1, 10):
        ph = math.radians(-20 + 220 * k / 8)
        c, sn = math.cos(ph), math.sin(ph)
        x = (w / 2 + 0.0035) * math.copysign(abs(c) ** 0.75, c)
        z = z0 + h / 2 + (h / 2 + 0.0035) * math.copysign(abs(sn) ** 0.75, sn)
        band.append(base + toe * u + side * x + up * max(z, z0 + 0.004))
        normals.append(side * c + up * sn)
    b.finish(b.strap(band, base, 0.016, 0.0035, normals), "cream", part, smooth=False)
    # steel toe cap and the shaft up into the ankle
    b.finish(b.sphere(base + toe * 0.05 + up * 0.02, 0.022, 10, 6, (1.15, 1.32, 0.78)), "grey", part)
    b.finish(b.tube([base + up * 0.03 - toe * 0.008, ankle + up * 1.5 * S], 4.6 * S, 10, rs=[4.8 * S, 3.8 * S]),
             "black_light", part)


# -- assembly ---------------------------------------------------------------------------

def build_mesh():
    b = Builder()
    build_torso(b)
    build_head(b)
    build_hood(b)
    build_scarf(b)
    build_cloak(b)
    skirt = build_skirt(b)
    n = len(b.bm.verts)
    hung = build_gear(b)
    b.bm.verts.ensure_lookup_table()
    gear = [b.bm.verts[i] for i in range(n, len(b.bm.verts))]
    for leg, s in ((LEG_R, "R"), (LEG_L, "L")):
        build_leg(b, *leg, s)
    for side, (sh, el, grip, axis, barrel) in (("R", ARM_R), ("L", ARM_L)):
        build_arm(b, sh, el, grip, axis, barrel, side)
    # the skirt swings with the thigh under it; what hangs on the skirt moves
    # exactly as the cloth it lies on
    top = H(BELT_BOTTOM + SKIRT_FOLLOW[3])
    toy3d.follow_limbs(b, skirt, top, {"thigh_R": LEG_R[:2], "thigh_L": LEG_L[:2]}, body=("hips",),
                       reach=SKIRT_FOLLOW[0], fade=SKIRT_FOLLOW[1], pin=SKIRT_FOLLOW[2])
    from mathutils.bvhtree import BVHTree
    faces = list({f for v in skirt for f in v.link_faces})
    at = {v: k for k, v in enumerate(skirt)}
    tree = BVHTree.FromPolygons([v.co for v in skirt], [[at[v] for v in f.verts] for f in faces])
    toy3d.follow_limbs(b, [v for v in gear if v.co.z < H(BELT_TOP)], top,
                       {"thigh_R": LEG_R[:2], "thigh_L": LEG_L[:2]}, body=("hips",),
                       reach=SKIRT_FOLLOW[0], fade=SKIRT_FOLLOW[1], pin=SKIRT_FOLLOW[2],
                       probe=lambda co: tree.find_nearest(co)[0])
    # the satchel is stiff leather hanging on the belt at his side: it rides with
    # the hips as one piece, and the cloth just under it is held still by its weight
    # (the staple strips are flexible and swing with the cloth they lie on)
    hips = b.bone_index("hips")
    for item in hung[:1]:
        for v in item:
            dv = v[b.deform]
            dv.clear()
            dv[hips] = 1.0
        centre = sum((v.co for v in item), Vector()) / len(item)
        for v in skirt:
            k = smoothstep(((v.co - centre).length / S - HELD[0]) / HELD[1])
            dv = v[b.deform]
            for i in list(dv.keys()):
                dv[i] = dv[i] * k + ((1 - k) if i == hips else 0.0)
    return b


SKIRT_FOLLOW = (20.0, 3.0, 8.0, 1.5)   # reach, fade, pin (px), and how far below the belt the pin starts (px)


def build_stapler():
    toy3d.configure(CHAR)
    return toy3d.build(build_mesh)


if __name__ == "__main__" and bpy.app.background:
    o, t, c = build_stapler()
    print("tris", sum(t.values()), t)
    print("clipping at rest", {k: v for k, v in c.items() if v})
    print("glb", toy3d.export_glb(o))
