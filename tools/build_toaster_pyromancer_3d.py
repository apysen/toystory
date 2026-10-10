"""Build the 3D Toaster Pyromancer (Blender).

Live, through the Blender MCP:   exec(open("tools/build_toaster_pyromancer_3d.py").read())  then  build_toaster()
Headless:  D:/Blender/blender.exe --background --python tools/build_toaster_pyromancer_3d.py

Heights and stance come off the 128 px idle frame (player/toaster/toaster_sheet.png,
foot pivot 66,119); the look follows the concept sheet
(assets/concept/animations/toaster.png), with the shared machinery in
tools/toy3d.py. Same rules as the other toys: one mesh and one palette
material, every part a closed solid on its own bone, cloth with even rows, sway
weights and bone chains, human hands with the right chirality, nothing clipping.

The pyromancer, from the concept:
  - head: a steel toaster, its face the long side: two glowing vents for eyes
    (a bone up each, vent_R / vent_L, that the game hangs fire on, as if the
    toaster burned inside),
    gold rivets at the corners, a flat gold push-down lever sticking out level
    from a slot on his left side (on its own bone), and two slices
    of toast standing one behind the other in the slots on top (each on its own
    bone, so Toast Pop can launch them)
  - a thick red scarf wrapped round the neck, a gold sun brooch with a glowing
    gem at the throat
  - a cream robe: wide bell sleeves striped red at the cuff,
    a long skirt split at the front with red flames up from its hem (line art)
  - brown belt with a square gold buckle, a satchel hanging from it on his
    left hip
  - a red cape from the shoulders, dark red inside
  - black gloves held open, palm up, each with a bone over the palm that the
    game hangs its fire on (Godot draws the flames, so they move like fire;
    clips lift and flare them by moving the bones)
  - steel robot legs: round knee joints showing below the robe, gold ankle rings
    with bolts, steel boots
Built in a neutral pose: forearms forward, palms up at the waist. The concept's
raised hand belongs in the idle clip.

Writes assets/models/toaster/toaster_pyromancer.glb; the .blend and previews go
in assets/models/toaster/source/ (Godot-ignored).
"""
import importlib
import math
import os
import sys

import bmesh
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
                   grid_normals, cloth)

# name, hex, emissive: the sprite's eight colours, the shades between them, the
# toast, and the fire
PALETTE = [
    ("outline", "050303", False), ("red", "ba163e", False),
    ("red_dark", "720e32", False), ("red_light", "d8455c", False),
    ("cream", "f2dece", False), ("cream_shade", "c2bab2", False),
    ("steel_light", "d6d2cc", False), ("steel", "827e86", False),
    ("steel_dark", "3e323e", False), ("gold", "fab632", False),
    ("gold_dark", "b5761c", False), ("crust", "b8692a", False),
    ("toast", "f0c27c", False), ("black", "231a20", False),
    ("glow", "ff8a24", True), ("glow_hot", "fff0a8", True),
]

CX = 66  # the body's centre line, px (the sprite's foot pivot)


def body_weights(z):
    """Body, robe and everything worn on it blend hips -> spine -> chest up the body."""
    py = 119 - z / S
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
CLIP_CHECKS = (
    [("head", "scarf"), ("head", "torso"), ("head", "cape"), ("robe", "satchel"),
     ("robe", "belt"), ("cape", "robe"), ("cape", "satchel")]
    + [(a, c) for a in ARMS for c in ("cape", "scarf", "belt", "satchel", "robe")]
    + [(a, "torso") for a in ARMS[2:]]
    + [(a, c) for a in ARMS[4:] for c in ("head", "toast_front", "toast_back")]
    + [("toast_front", "toast_back")]
    + [(a, "lever") for a in ARMS[2:]]
    + [(a, c) for a in LEGS for c in ("cape", "robe", "satchel", "belt")]
)

CHAR = toy3d.Character(
    name="toaster_pyromancer", folder="toaster", object_name="ToasterPyromancer", pivot=(66, 119),
    palette=PALETTE,
    part_bone={"torso": "body", "belt": "body", "satchel": "body", "robe": "body",
               "cape": "body", "scarf": "chest", "neck": "head"},
    body_weights=body_weights, clip_checks=CLIP_CHECKS,
    detail=os.path.join(toy3d.ROOT, "assets", "models", "toaster", "source", "toaster_details.png"))
# the line art's regions in that atlas (px, origin top-left), as drawn by
# tools/draw_toaster_details.py (run it first)
DETAIL_ROBE = (0, 256, 1024, 640)
DETAIL_SLEEVE = (256, 0, 896, 256)
DETAIL_CHEST = (0, 640, 1024, 896)
toy3d.configure(CHAR)

# shoulder, elbow, wrist, palm direction (up), fingers' direction (forward)
ARM_R = (P(CX - 15.5, 57, 0.0), P(CX - 23, 65, 0.03), P(CX - 23.5, 70.5, -0.09))
ARM_L = (P(CX + 15.5, 57, 0.0), P(CX + 23, 65, 0.03), P(CX + 23.5, 70.5, -0.09))
# hip, knee, ankle, toe direction
LEG_R = (P(CX - 7, 84), P(CX - 9, 101, -0.02), P(CX - 11, 113, -0.005), (-0.35, -0.94, 0))
LEG_L = (P(CX + 7, 84), P(CX + 9, 101, -0.02), P(CX + 11, 113, -0.005), (0.35, -0.94, 0))

HEAD_C = P(CX, 32.0, 0.0)          # the toaster's middle: its base stands 2 px clear of the scarf, room to nod
VENT_HEIGHT = 0.076                 # the glowing slots in its face, where Godot burns fire
HEAD_SIZE = (36 * S, 0.19, 22 * S)  # width, depth, height
HEAD_ROUND = 0.022                  # radius of its rounded edges and corners
LEVER_REST = -0.002                 # the lever tab's height off the toaster's middle: halfway down its
                                    # slot, in reach of his hand above it, with room to press it down
NECK_PY = 46.0


def rounded_box(b, c, size, r, segments=3):
    """A box with its edges and corners rounded off to radius r (a bevel), as one
    closed solid; returns its verts."""
    verts = b.box(c, size)
    edges = list({e for v in verts for e in v.link_edges})
    res = bmesh.ops.bevel(b.bm, geom=verts + edges, offset=r, offset_type="OFFSET", segments=segments,
                          profile=0.5, affect="EDGES", clamp_overlap=True)
    seed = res["faces"][0].verts[0]
    seen, stack = {seed}, [seed]
    while stack:
        v = stack.pop()
        for e in v.link_edges:
            u = e.other_vert(v)
            if u not in seen:
                seen.add(u)
                stack.append(u)
    return list(seen)


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


def outward_from(axis_x, axis_y):
    return lambda p: Vector((p.x - axis_x, p.y - axis_y, 0.0))


# -- head: the toaster and its toast ------------------------------------------------

def build_head(b):
    """A steel toaster, its face the long side: a body with rounded edges and
    corners on a steel neck rising out of the scarf, a darker base band, two
    glowing vents for eyes framed in dark, gold rivets at the face's corners, a
    push-down lever on his left side, and two slots on top."""
    w, d, h = HEAD_SIZE
    c = HEAD_C
    b.finish(rounded_box(b, c, (w, d, h), HEAD_ROUND), "steel_light", "head")
    # the base band, a little proud all round and dropping 2 mm below the body's
    # bottom, so no two faces lie on each other (they would flicker)
    band = 0.016
    b.finish(rounded_box(b, c - Vector((0, 0, h / 2 - band / 2 + 0.002)), (w + 0.005, d + 0.005, band),
                         HEAD_ROUND + 0.0025), "steel", "head")
    # the neck: a steel post from inside the chest up into the toaster's base
    b.finish(b.tube([P(CX, NECK_PY + 6), P(CX, NECK_PY - 4.5)], 4.6 * S, 10), "steel_dark", "neck")
    front = c.y - d / 2
    for sx, name in ((-1, "vent_R"), (1, "vent_L")):   # the two vents: dark frame, glowing slot
        v = Vector((c.x + sx * 0.042, front, c.z + 0.004))
        b.finish(b.box(v - Vector((0, 0.0015, 0)), (0.028, 0.006, 0.09)), "outline", "head", smooth=False)
        b.finish(b.box(v - Vector((0, 0.003, 0)), (0.016, 0.006, 0.076)), "glow", "head", smooth=False)
        b.finish(b.box(v - Vector((0, 0.0055, 0.012)), (0.008, 0.004, 0.034)), "glow_hot", "head", smooth=False)
        # a bone up the slot, its head at the bottom, that the game hangs the fire
        # burning inside the toaster on (no mesh of its own)
        slot = v - Vector((0, 0.006, 0))
        b.joints[name] = (slot - Vector((0, 0, VENT_HEIGHT / 2)), slot + Vector((0, 0, VENT_HEIGHT / 2)), "head")
    for sx in (-1, 1):   # rivets at the face's corners
        for sz in (-1, 1):
            b.finish(b.sphere(Vector((c.x + sx * (w / 2 - 0.022), front - 0.001, c.z + sz * (h / 2 - 0.022))),
                              0.008, 8, 4, (1, 0.6, 1)), "gold", "head")
    # the push-down lever on his left side: a dark slot running down the side, and
    # (on its own bone, so it can be pressed and spring back) a flat gold tab
    # sticking out level from it, like a real toaster's
    side = c.x + w / 2
    b.finish(b.box(Vector((side + 0.001, c.y - 0.02, c.z + 0.005)), (0.006, 0.014, 0.1)), "outline", "head",
             smooth=False)
    stem = Vector((side, c.y - 0.02, c.z + LEVER_REST))
    b.finish(b.box(stem + Vector((0.008, 0, 0)), (0.02, 0.01, 0.008)), "gold_dark", "lever", smooth=False)
    b.finish(b.box(stem + Vector((0.03, 0, 0)), (0.03, 0.04, 0.011)), "gold", "lever", smooth=False)
    b.joints["lever"] = (stem, stem + Vector((0.045, 0, 0)), "head")
    # the two slots on top, one behind the other, dark, that the toast stands in
    top = c.z + h / 2
    for _, dy in TOAST_SLOTS:
        b.finish(b.box(Vector((c.x, c.y + dy, top + 0.001)), (0.17, 0.03, 0.004)), "outline", "head",
                 smooth=False)
    b.joints["head"] = (P(CX, NECK_PY, 0.0), P(CX, 24, 0.0), "chest")


def toast_outline(width, height):
    """A slice of bread seen face on: straight sides, a top that bulges into two
    shoulders, as (x, z) round its middle bottom."""
    pts = [(-width / 2, 0.0), (width / 2, 0.0)]
    for k in range(13):
        t = k / 12
        a = math.pi * t
        x = width / 2 * math.cos(a) * (1.0 + 0.08 * math.sin(a))
        z = height * 0.72 + height * 0.28 * math.sin(a) + height * 0.06 * math.sin(2 * a) ** 2
        pts.append((x * 1.06, z))
    return pts


TOAST_SLOTS = (("toast_front", -0.042), ("toast_back", 0.042))   # bone, depth off the toaster's middle
TOAST_SIZE = (0.15, 0.11, 0.018)     # width, height (short enough to sink right into the toaster), thickness


def build_toast(b):
    """Two slices standing in the slots one behind the other, faces to the front,
    golden crust round a lighter crumb; each on its own bone so it can pop."""
    w, d, h = HEAD_SIZE
    top = HEAD_C.z + h / 2
    width, height, th = TOAST_SIZE
    pts = toast_outline(width, height)
    inner = [(x * 0.84, 0.01 + z * 0.86) for x, z in pts]
    for k, (part, dy) in enumerate(TOAST_SLOTS):
        base = Vector((HEAD_C.x, HEAD_C.y + dy, top - 0.03 + 0.01 * k))   # centred in its slot
        # the slab's local X runs across, local Y up and local Z toward the front (-Y)
        M = Matrix.Translation(base) @ Matrix(((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, -1.0, 0.0),
                                               (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
        faces = b.finish(b.slab(pts, th, M), "crust", part, smooth=False)
        b.paint([f for f in faces if abs(f.normal.y) > 0.9], "toast")
        for zoff in (th / 2 + 0.0008, -th / 2 - 0.0008):   # the crumb, a crust rim round it
            faces += b.finish(b.slab(inner, 0.0016, M, zoff=zoff), "toast", part, smooth=False)
        for f in faces:   # UV2.y marks each slice (1 front, 2 back): the game hides a launched
            for loop in f.loops:   # slice until it reloads, and browns a slice that has toasted
                loop[b.sway].uv = (loop[b.sway].uv.x, k + 1.0)
        b.joints[part] = (base, base + Vector((0, 0, height)), "head")


# -- scarf and brooch ----------------------------------------------------------------

COLLAR = (P(CX, 119, 0.012), 0.86)   # the scarf's axis and its depth scale
COLLAR_R, COLLAR_TUBE, COLLAR_PY = 10.8, 4.1, 50.0


def scarf_front(dx_px=0.0, t=0.0):
    """A point on the scarf wrap's outer surface, dx_px across from the middle at
    the front, t round the wrap's tube from its outermost line (+ up), and the
    outward normal there."""
    centre, sy = COLLAR
    r = (COLLAR_R + COLLAR_TUBE * math.cos(t)) * S
    a = -math.pi / 2 + math.asin(max(-0.95, min(0.95, dx_px * S / r)))
    k = 1 + 0.05 * math.sin(3 * a + 0.5)
    p = Vector((centre.x + r * k * math.cos(a), centre.y + r * k * math.sin(a) * sy,
                H(COLLAR_PY - 0.85 * COLLAR_TUBE * math.sin(t)) + 0.006 * math.sin(2 * a + 1.0)))
    n = Vector((math.cos(a) * math.cos(t), math.sin(a) * math.cos(t) / sy, 0.85 * math.sin(t))).normalized()
    return p, n


def build_scarf(b):
    """A thick red wrap round the neck, and a fold of it coming out of the wrap
    at the front of his right shoulder."""
    centre, sy = COLLAR
    prof = [(COLLAR_R + COLLAR_TUBE * math.cos(t), COLLAR_PY - 0.85 * COLLAR_TUBE * math.sin(t))
            for t in (2 * math.pi * k / 12 for k in range(12))]

    def wrap(p, a):
        k = 1 + 0.05 * math.sin(3 * a + 0.5)
        p.x *= k
        p.y *= k
        p.z += 0.006 * math.sin(2 * a + 1.0)        # the wrap sits a little lower at the front
        return p
    verts, bands, _ = b.lathe(vprof(prof), 20, Matrix.Translation(Vector((centre.x, centre.y, 0))), sy=sy,
                              loop=True, warp=wrap)
    b.finish(verts, "red", "scarf", smooth=False)
    # a fold coming out of the wrap at the front of his right shoulder and lying
    # down his chest
    start, n0 = scarf_front(-8.0, -0.5)
    path, normals = [start - n0 * 1.5 * S], [n0]
    for px, py, lift in ((CX - 9, 56.5, 1.2), (CX - 10, 59.5, 1.1), (CX - 10.5, 62.5, 1.1)):
        q, m = body_pt(px, py, torso_r(py) + lift)
        path.append(q)
        normals.append(m)
    b.finish(b.strap(path, P(CX, 0, 0.012), 7 * S, 2.2 * S, normals), "red", "scarf", smooth=False)


def build_brooch(b):
    """A gold sun brooch pinning the scarf at the throat, a glowing gem in it."""
    c, n = scarf_front(1.0, -0.15)
    c = c + n * 0.3 * S                    # half sunk into the wrap
    b.finish(b.ring(c, n, 2.2 * S, 4.4 * S, 1.6 * S, 12), "gold", "scarf", smooth=False)
    for k in range(8):   # the sun's rays
        a = math.pi * k / 4
        ray = c + (Vector((math.cos(a), 0, math.sin(a))) * 5.0 * S) + n * 0.3 * S
        b.finish(b.sphere(ray, 1.0 * S, 6, 3, (1, 0.6, 1)), "gold_dark", "scarf")
    b.finish(b.sphere(c + n * 0.8 * S, 2.4 * S, 10, 5, (1, 0.7, 1)), "glow", "scarf")


# -- body and robe ---------------------------------------------------------------------

TORSO_SY = 0.72
TORSO_PROF = [(0, 84), (12, 84), (12.5, 78), (12, 72), (13.5, 64), (15, 58), (14.5, 54), (10, 50.5), (6, 49), (0, 48.5)]
BELT_TOP, BELT_BOTTOM = 64.0, 69.0


def torso_r(py):
    pts = sorted(TORSO_PROF[1:-1], key=lambda q: q[1])
    for (r0, y0), (r1, y1) in zip(pts, pts[1:]):
        if y0 <= py <= y1:
            return r0 + (r1 - r0) * (py - y0) / (y1 - y0)
    return pts[0][0] if py < pts[0][1] else pts[-1][0]


def body_pt(px, py, r, sy=TORSO_SY):
    """Point on an ellipse (radius r px, depth scale sy) round the body at row py,
    in front, at sprite column px; also the outward normal there."""
    dx = max(-r * 0.97, min(r * 0.97, px - CX))
    y = -sy * math.sqrt(r * r - dx * dx)
    n = Vector((dx, y / (sy * sy), 0)).normalized()
    return P(px, py, y * S), n


def build_torso(b):
    """The robe's body: cream over the hips into the skirt, and above the belt the
    line art's red band down the front, carrying on into the skirt's front bands."""
    verts, bands, _ = b.lathe(vprof(TORSO_PROF), 16, Matrix.Translation(P(CX, 119)), sy=TORSO_SY)
    faces = b.finish(verts, "cream", "torso")
    axis = P(CX, 119)
    top = TORSO_PROF[-2][1]

    def chest_uv(co):   # u round from straight behind (the front is 0.5), v from the neck to the belt
        a = math.degrees(math.atan2((co.y - axis.y) / TORSO_SY, co.x - axis.x))
        return ((a + 270) % 360) / 360, (H(top) - co.z) / (H(top) - H(BELT_BOTTOM))
    b.map_detail([f for f in faces if f.calc_center_median().z > H(BELT_BOTTOM) and abs(f.normal.z) < 0.95],
                 DETAIL_CHEST, chest_uv, wrap=True)
    b.joints["root"] = (Vector((0, 0, 0)), Vector((0, -0.12, 0)), None)
    b.joints["hips"] = (P(CX, 80), P(CX, 66), "root")
    b.joints["spine"] = (P(CX, 66), P(CX, 56), "hips")
    b.joints["chest"] = (P(CX, 56), P(CX, NECK_PY), "spine")


ROBE_TOP, ROBE_HEM = 66.5, 95.0
ROBE_OPEN = 24.0   # half-width in degrees of the split at the front, at the hem


def robe_r(py):
    return interp([(ROBE_TOP, torso_r(ROBE_TOP) + 0.1), (70, torso_r(70) + 0.1), (76, 15.0), (88, 18.0), (ROBE_HEM, 20.5),
                   (ROBE_HEM + 6, 21.5)], py)


def robe_sy(py):
    return TORSO_SY + 0.08 * smoothstep((py - 70) / 20)


def build_robe(b):
    """The robe's long skirt from under the belt nearly to the knees, split at the
    front, the concept's red flames licking up from the hem in line art; near the
    thighs it follows them, so a stride swings it."""
    rows, cols = 12, 34
    pys = [ROBE_TOP + (ROBE_HEM - ROBE_TOP) * j / (rows - 1) for j in range(rows)]
    mids = []
    for j, py in enumerate(pys):
        t = j / (rows - 1)
        half = ROBE_OPEN * smoothstep((t - 0.35) / 0.65)       # closed at the top, split lower down
        row = []
        for i in range(cols + 1):
            a = math.radians(-90 + half + (360 - 2 * half) * i / cols)
            q = py + (2.5 * hash01(i + 7) if j == rows - 1 else 0.0)
            fold = 0.6 * t * math.sin(5 * a)
            row.append(ring_pt(P(CX, 119), robe_r(q) + fold, a, robe_sy(q), q))
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(P(CX, 0).x, 0.0))
    verts, fronts, backs = cloth(b, mids, norms, 0.6 * S)
    faces = b.finish(verts, "cream", "robe", smooth=False)
    # the line art over its outside (inside, it is the same cream cloth): u round from straight ahead, v down to the hem
    axis = P(CX, 119)

    def robe_uv(co):
        py = 119 - co.z / S
        a = math.degrees(math.atan2((co.y - axis.y) / robe_sy(py), co.x - axis.x))
        return ((a + 90) % 360) / 360, (H(ROBE_TOP) - co.z) / (H(ROBE_TOP) - H(ROBE_HEM))
    b.map_detail([f for fs in fronts.values() for f in fs], DETAIL_ROBE, robe_uv)
    b.set_sway(faces, H(BELT_BOTTOM), H(ROBE_HEM))
    return verts


def build_cape(b):
    """A red cape from the shoulders, behind the arms, dark red inside, flaring
    toward the hem and longer on his left as in the sprite. Even rows, a sway
    weight and a three-bone chain."""
    rows, cols = 15, 26
    top_py, hem_py = 49.5, 108.0    # it starts tucked under the scarf wrap
    prof = [(49.5, 12.0), (53, 16.0), (58, 19.5), (70, 22.5), (85, 26.5), (98, 30.5), (108, 33)]

    def span(t):   # behind the arms at the top, wrapping further round toward the hem
        return math.radians(30 - 28 * t), math.radians(150 + 28 * t)
    centre = P(CX, 119, 0.03)
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
                q += 4.0 * (1 - i / cols) + (1.5 * hash01(i + 3) if i % 2 == 0 else 0.0)  # longer on his left
            fold = 3.0 * t * math.sin(6 * a + 0.4)
            p = ring_pt(centre, interp(prof, q) + fold, a, 0.92, q)
            p.y += 0.04 * t * t * max(0.0, math.sin(a))
            row.append(p)
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre.x, centre.y))
    verts, fronts, backs = cloth(b, mids, norms, 1.2 * S)
    faces = b.finish(verts, "red", "cape", smooth=False)
    b.paint(list(backs.values()), "red_dark")   # its folds are real, so the scene's light shades them
    b.set_sway(faces, H(top_py), H(hem_py))
    c = cols // 2
    js = [mids[min(rows - 1, round((py - top_py) / (hem_py - top_py) * (rows - 1)))][c] for py in (53, 72, 90, 106)]
    for i in range(3):
        b.joints[f"cape_{i + 1}"] = (js[i], js[i + 1], "chest" if i == 0 else f"cape_{i}")
    chain_weights(b, verts, H(top_py), H(top_py) - H(hem_py),
                  (("chest", -0.08), ("cape_1", 0.2), ("cape_2", 0.55), ("cape_3", 0.9)), 0.35)


SATCHEL = (11.0, (7.5, 4.4, 9.0))   # px right of centre (his left) on the belt; width, depth, height px


def build_gear(b):
    """Belt and buckle, and the satchel hanging from the belt on his left hip."""
    belt = [(torso_r(BELT_BOTTOM) + 2.2, BELT_BOTTOM), (torso_r(BELT_TOP) + 2.2, BELT_TOP),
            (torso_r(BELT_TOP) + 0.8, BELT_TOP), (torso_r(BELT_BOTTOM) + 0.8, BELT_BOTTOM)]
    b.finish(b.lathe(vprof(belt), 28, Matrix.Translation(P(CX, 119)), sy=TORSO_SY, loop=True)[0],
             "crust", "belt", smooth=False)
    mid_py = (BELT_TOP + BELT_BOTTOM) / 2
    p, n = body_pt(CX + 1, mid_py, torso_r(mid_py) + 2.6)
    side = Vector((0, 0, 1)).cross(n).normalized()
    for off, size in ((side * 2.6, (1.0, 0.8, 6.0)), (-side * 2.6, (1.0, 0.8, 6.0)),
                      (Vector((0, 0, 2.6)), (6.2, 0.8, 1.0)), (Vector((0, 0, -2.6)), (6.2, 0.8, 1.0))):
        b.finish(b.box(p + off * S, tuple(v * S for v in size), xdir=side), "gold", "belt", smooth=False)
    b.finish(b.box(p + n * 0.2 * S, (2.4 * S, 0.5 * S, 2.4 * S), xdir=side), "crust", "belt", smooth=False)

    # the satchel: a stiff leather box fixed to the belt on his left hip, its back
    # flat on the belt's outer face and its top tucked up behind the belt, a flap
    # and a gold clasp; nothing hangs
    px0, size = SATCHEL
    mid = (BELT_TOP + BELT_BOTTOM) / 2
    on_belt, n = body_pt(CX + px0, mid, torso_r(mid) + 2.2)
    side = Vector((0, 0, 1)).cross(n).normalized()
    w, d, h = (v * S for v in size)
    top = H(BELT_TOP + 1.0)                       # its top edge just under the belt's top
    centre = Vector((on_belt.x, on_belt.y, top - h / 2)) + n * (d / 2 - 0.2 * S)
    b.finish(b.box(centre, (w, d, h), xdir=side, zdir=(0, 0, 1)), "crust", "satchel", smooth=False)
    b.satchel_centre = centre
    flap = centre + n * 0.6 * S + Vector((0, 0, h / 2 - 2.0 * S))
    b.finish(b.box(flap, (w + 0.6 * S, d - 0.6 * S, 4.4 * S), xdir=side, zdir=(0, 0, 1)), "gold_dark", "satchel",
             smooth=False)
    b.finish(b.sphere(flap + n * (d / 2 - 0.1 * S) - Vector((0, 0, 1.6 * S)), 1.3 * S, 8, 4, (1, 0.6, 1)), "gold",
             "satchel")


# -- arms, hands and flames ---------------------------------------------------------------

def build_open_hand(b, wrist, f, up, side, part):
    """A black glove held open, palm up: a palm, four fingers a little curled up
    at the tips, the index finger beside the thumb. Turned palm up, a hand's
    thumb points outward, away from the body: a right hand's to his right, a
    left hand's to his left. f runs from the wrist to the fingertips."""
    f = f.normalized()
    up = (up - f * up.dot(f)).normalized()
    across = f.cross(up).normalized()             # toward his right
    thumb_side = across if side == "R" else -across
    palm = wrist + f * 3.2 * S
    b.finish(b.box(palm, (6.6 * S, 6.0 * S, 2.4 * S), xdir=across, zdir=up), "black", part, smooth=False)
    tip_base = palm + f * 3.0 * S
    for k, off in enumerate((2.5, 0.85, -0.85, -2.5)):
        o = thumb_side * off * S                  # index finger (off 2.5) nearest the thumb
        length = (4.6 if 0 < k < 3 else 4.0) * S
        pts = [tip_base + o, tip_base + o + f * length * 0.55 + up * 0.4 * S,
               tip_base + o + f * length + up * 1.6 * S]
        b.finish(b.tube(pts, 0.95 * S, 5, rs=[1.0 * S, 0.95 * S, 0.8 * S]), "black", part)
    t0 = palm + thumb_side * 3.0 * S - f * 0.8 * S
    b.finish(b.tube([t0, t0 + thumb_side * 2.2 * S + f * 1.4 * S + up * 0.8 * S,
                     t0 + thumb_side * 3.0 * S + f * 3.4 * S + up * 1.8 * S], 1.05 * S, 5,
                    rs=[1.15 * S, 1.0 * S, 0.85 * S]), "black", part)
    return palm


FLAME_HEIGHT = 0.11   # how tall the fire standing in each palm is; Godot draws it


def build_arm(b, shoulder, elbow, wrist, side):
    """Cream bell sleeve striped red at the cuff, a black glove
    open palm up, and over the palm the bone the game hangs its fire on (the
    flames are drawn in Godot, so they move like fire)."""
    upper, fore, hand, flame = f"upperarm_{side}", f"forearm_{side}", f"hand_{side}", f"flame_{side}"
    b.finish(b.sphere(shoulder, 5.2 * S, 10, 6, (1, 0.9, 0.85)), "cream", upper)
    b.finish(b.tube([shoulder, shoulder.lerp(elbow, 0.5), elbow], 4.2 * S, 10, rs=[4.4 * S, 4.4 * S, 4.0 * S]),
             "cream", upper)
    b.finish(b.sphere(elbow, 4.0 * S, 8, 5), "cream", fore)
    cuff = elbow.lerp(wrist, 0.86)
    sleeve = b.finish(b.tube([elbow, elbow.lerp(wrist, 0.5), cuff, cuff + (wrist - elbow) * 0.02],
                             4.0 * S, 12, rs=[4.0 * S, 4.6 * S, 6.0 * S, 6.0 * S]), "cream", fore)
    # the line art round the bell: a red stripe, a flaming red cuff
    axis = (wrist - elbow).normalized()
    length = (cuff - elbow).length + 0.02 * (wrist - elbow).length
    ref = (Vector((0, 0, 1)) - axis * axis.z).normalized()

    def sleeve_uv(co):
        r = co - elbow
        r -= axis * r.dot(axis)
        a = math.atan2(axis.cross(ref).dot(r), ref.dot(r))
        return (a / (2 * math.pi)) % 1.0, (co - elbow).dot(axis) / length
    b.map_detail([fc for fc in sleeve if abs(fc.normal.dot(axis)) < 0.9], DETAIL_SLEEVE, sleeve_uv, wrap=True)
    b.finish(b.tube([wrist - (wrist - elbow).normalized() * 3 * S, wrist + (wrist - elbow).normalized() * 1.6 * S],
                    2.5 * S, 8), "black", hand)
    f = Vector((wrist.x - elbow.x, wrist.y - elbow.y, 0)).normalized() * 0.92 + Vector((0, 0, 0.2))
    palm = build_open_hand(b, wrist, f, Vector((0, 0, 1)), side, hand)
    base = palm + Vector((0, 0, 1.4 * S))
    b.joints[upper] = (shoulder, elbow, "chest")
    b.joints[fore] = (elbow, wrist, upper)
    b.joints[hand] = (wrist, palm + f.normalized() * 3 * S, fore)
    b.joints[flame] = (base, base + Vector((0, 0, FLAME_HEIGHT)), hand)


# -- legs --------------------------------------------------------------------------------

BOOT_SOLE = 0.014
BOOT_BACK, BOOT_TIP = -0.036, 0.066


def boot_size(u):
    w = interp([(BOOT_BACK, 0.046), (0.0, 0.05), (0.03, 0.058), (0.05, 0.056), (BOOT_TIP, 0.052)], u)
    h = interp([(BOOT_BACK, 0.042), (-0.015, 0.052), (0.005, 0.046), (0.025, 0.033), (0.045, 0.027),
                (BOOT_TIP, 0.023)], u)
    k = 1.0
    if u > 0.046:
        k = math.sqrt(max(0.0, 1 - ((u - 0.046) / (BOOT_TIP - 0.046)) ** 2))
    elif u < -0.022:
        k = math.sqrt(max(0.0, 1 - ((u + 0.022) / (BOOT_BACK + 0.022)) ** 2))
    return w * max(k, 0.12), h * max(k, 0.25)


def build_boot(b, base, toe, ankle, part):
    """A steel boot: a domed upper on a dark sole, a darker steel cap over the
    toes and the shaft up into the ankle (the gold is the ankle ring above)."""
    up = Vector((0, 0, 1))
    side = up.cross(toe).normalized()
    z0 = BOOT_SOLE
    n_sec, n_ring = 12, 14
    bm = b.bm

    def ring_at(u):
        w, h = boot_size(u)
        out = []
        for k in range(n_ring):
            ph = 2 * math.pi * k / n_ring
            c, sn = math.cos(ph), math.sin(ph)
            x = (w / 2) * math.copysign(abs(c) ** 0.75, c)
            z = z0 + h / 2 + (h / 2) * math.copysign(abs(sn) ** 0.75, sn)
            out.append(base + toe * u + side * x + up * z)
        return out
    us = [BOOT_BACK + (BOOT_TIP - BOOT_BACK) * k / (n_sec - 1) for k in range(n_sec)]
    rings = [[bm.verts.new(p) for p in ring_at(u)] for u in us]
    made = [v for r in rings for v in r]
    for A, B in zip(rings, rings[1:]):
        for k in range(n_ring):
            m = (k + 1) % n_ring
            bm.faces.new((A[k], A[m], B[m], B[k]))
    for r, u in ((rings[0], us[0]), (rings[-1], us[-1])):
        w, h = boot_size(u)
        c = bm.verts.new(base + toe * u + up * (z0 + h / 2))
        made.append(c)
        for k in range(n_ring):
            bm.faces.new((r[k], r[(k + 1) % n_ring], c))
    b.finish(made, "steel_light", part)
    outline = []
    for k in range(10):
        u = BOOT_BACK - 0.004 + (BOOT_TIP + 0.02) * k / 9
        outline.append((u, boot_size(min(u, 0.046))[0] / 2 + 0.004))
    pts = [(u, -hw) for u, hw in outline] + [(u, hw) for u, hw in reversed(outline)]
    pts = [(u, y * (math.sqrt(max(0.0, 1 - ((u - 0.052) / 0.034) ** 2)) if u > 0.052 else 1.0)) for u, y in pts]
    pts = [(u, y if abs(y) > 0.004 or u < 0.072 else math.copysign(0.004, y)) for u, y in pts]
    b.finish(b.slab(pts, BOOT_SOLE, frame(base + up * (BOOT_SOLE / 2), up, toe)), "steel_dark", part, smooth=False)
    b.finish(b.sphere(base + toe * 0.052 + up * 0.021, 0.023, 10, 6, (1.15, 1.3, 0.8)), "steel", part)
    b.finish(b.tube([base + up * 0.03 - toe * 0.008, ankle + up * 1.5 * S], 4.6 * S, 10, rs=[4.9 * S, 3.9 * S]),
             "steel", part)


def build_leg(b, hip, knee, ankle, toe, s):
    """A steel robot leg: a thigh rod up into the robe, a round knee joint, a
    plated shin, a gold ankle ring with a bolt, and the boot."""
    toe = Vector(toe).normalized()
    out = Vector((-1 if s == "R" else 1, 0, 0))
    thigh, shin, foot = f"thigh_{s}", f"shin_{s}", f"foot_{s}"
    base = Vector((ankle.x, ankle.y, 0.0))
    b.joints[thigh] = (hip, knee, "hips")
    b.joints[shin] = (knee, ankle, thigh)
    b.joints[foot] = (ankle, base + toe * 0.07 + Vector((0, 0, 0.02)), shin)
    b.finish(b.tube([hip + Vector((0, 0, 2 * S)), knee], 3.6 * S, 10, rs=[4.2 * S, 3.6 * S]), "steel", thigh)
    b.finish(b.sphere(hip, 4.4 * S, 10, 6), "steel_dark", thigh)     # the hip joint, up inside the robe
    b.finish(b.sphere(knee, 4.6 * S, 12, 7), "steel_light", shin)
    b.finish(b.tube([knee, knee.lerp(ankle, 0.5), ankle], 3.4 * S, 10, rs=[3.8 * S, 4.0 * S, 3.2 * S]),
             "steel_light", shin)
    plate = knee.lerp(ankle, 0.42) + Vector((0, -3.4 * S, 0))
    b.finish(b.box(plate, (4.4 * S, 1.2 * S, 7.0 * S), zdir=(ankle - knee)), "steel", shin, smooth=False)
    b.finish(b.ring(ankle + Vector((0, 0, 0.6 * S)), Vector((0, 0, 1)), 3.6 * S, 5.0 * S, 2.6 * S, 12), "gold",
             shin, smooth=False)
    b.finish(b.sphere(ankle + out * 5.0 * S + Vector((0, 0, 0.6 * S)), 1.8 * S, 8, 4, (0.5, 1, 1)), "gold_dark",
             shin)
    build_boot(b, base, toe, ankle, foot)


# -- assembly ------------------------------------------------------------------------------

ROBE_FOLLOW = (18.0, 4.0, 6.0, 2.0)   # reach, fade, pin (px), and how far below the belt the pin starts (px)


def build_mesh():
    b = Builder()
    build_torso(b)
    build_head(b)
    build_toast(b)
    build_scarf(b)
    build_brooch(b)
    build_cape(b)
    robe = build_robe(b)
    build_gear(b)
    for leg, s in ((LEG_R, "R"), (LEG_L, "L")):
        build_leg(b, *leg, s)
    for side, (sh, el, wr) in (("R", ARM_R), ("L", ARM_L)):
        build_arm(b, sh, el, wr, side)
    # the robe swings with the thigh under it
    toy3d.follow_limbs(b, robe, H(BELT_BOTTOM + ROBE_FOLLOW[3]), {"thigh_R": LEG_R[:2], "thigh_L": LEG_L[:2]},
                       body=("hips",), reach=ROBE_FOLLOW[0], fade=ROBE_FOLLOW[1], pin=ROBE_FOLLOW[2])
    # the stiff satchel on the belt holds the robe just under it still, so a
    # stride swings the cloth around it rather than through it
    hips = b.bone_index("hips")
    for v in robe:
        k = smoothstep(((v.co - b.satchel_centre).length / S - SATCHEL_HELD[0]) / SATCHEL_HELD[1])
        dv = v[b.deform]
        for i in list(dv.keys()):
            dv[i] = dv[i] * k + ((1 - k) if i == hips else 0.0)
    return b


SATCHEL_HELD = (6.0, 5.0)   # px round the satchel where the robe is held still, and the fade beyond


def build_toaster():
    toy3d.configure(CHAR)
    return toy3d.build(build_mesh)


if __name__ == "__main__" and bpy.app.background:
    o, t, c = build_toaster()
    print("tris", sum(t.values()), t)
    print("clipping at rest", {k: v for k, v in c.items() if v})
    print("glb", toy3d.export_glb(o))
