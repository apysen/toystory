"""Build the Teacup Cleric approval model.

The 128 px player concept fixes scale and silhouette.  This procedural source
deliberately stops before rigging, animation, GLB export, and Godot integration;
it nevertheless authors joints and deformation weights with the mesh so the
approved model is ready to rig.  Steam and blessing sparkles are Godot VFX.
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
sys.dont_write_bytecode = True
import toy3d  # noqa: E402
importlib.reload(toy3d)
from toy3d import (Builder, H, P, S, build_hand, chain_weights, cloth, frame,  # noqa: E402
                   detail_uv, grid_normals, grip_frame, smoothstep)


PALETTE = [
    ("outline", "050402", False), ("blue_dark", "17326f", False),
    ("blue_mid", "1d4798", False), ("blue", "2459b4", False),
    ("blue_light", "3970cb", False), ("mauve", "4b3b43", False),
    ("brown_dark", "713616", False), ("brown", "a55225", False),
    ("tan", "c98959", False), ("skin", "deb292", False),
    ("cream_shade", "e8c39f", False), ("amber", "f29a2e", False),
    ("gold", "f5b83f", False), ("cream_warm", "f8d9a8", False),
    ("cream", "f9e5c6", False), ("ivory", "fff3d5", False),
]

CX, GROUND = 61, 123
DETAIL = os.path.join(toy3d.ROOT, "assets", "models", "teacup", "source", "teacup_details.png")


def body_weights(z):
    """Smooth body weights, expressed in the same vertical zones as the approved toys."""
    if z < H(84):
        return [("hips", 1.0)]
    if z < H(64):
        t = smoothstep((z - H(84)) / (H(64) - H(84)))
        return [("hips", 1 - t), ("spine", t)]
    t = smoothstep((z - H(64)) / (H(47) - H(64)))
    return [("spine", 1 - t), ("chest", t)]


PART_BONE = {
    "torso": "body", "robe": "body", "outer_robe": "body", "mid_robe": "body",
    "belt": "hips", "tabard": "body", "collar": "chest",
    "mantle": "chest", "head": "head", "neck": "chest", "medallion": "chest",
    "cape": "chest", "book": "hand_R", "upperarm_R": "upperarm_R",
    "forearm_R": "forearm_R", "hand_R": "hand_R", "upperarm_L": "upperarm_L",
    "forearm_L": "forearm_L", "hand_L": "hand_L", "thigh_R": "thigh_R",
    "shin_R": "shin_R", "foot_R": "foot_R", "thigh_L": "thigh_L",
    "shin_L": "shin_L", "foot_L": "foot_L",
}

CLIP_CHECKS = (
    ("head", "collar"), ("head", "mantle"), ("book", "head"), ("book", "torso"),
    ("forearm_R", "torso"), ("forearm_L", "torso"),
    ("forearm_R", "book"),
    ("robe", "foot_R"), ("robe", "foot_L"),
    ("mid_robe", "robe"), ("outer_robe", "robe"),
    ("outer_robe", "mid_robe"), ("cape", "outer_robe"),
    # Cape/mantle is deliberately omitted: the cape's sewn yoke is tucked
    # beneath the mantle, while their visible surfaces remain ordered.
    ("tabard", "belt"), ("medallion", "tabard"),
)

CHAR = toy3d.Character(
    name="teacup_cleric", folder="teacup", object_name="TeacupCleric",
    pivot=(CX, GROUND), palette=PALETTE, part_bone=PART_BONE,
    body_weights=body_weights, clip_checks=CLIP_CHECKS, detail=DETAIL,
)
toy3d.configure(CHAR)

DETAIL_CUP = (256, 0, 1024, 184)
DETAIL_SLEEVE = (256, 192, 1024, 352)
DETAIL_COLLAR = (0, 256, 256, 512)
DETAIL_MANTLE = (256, 368, 1024, 512)
DETAIL_ROBE = (256, 528, 1024, 720)
DETAIL_TABARD = (0, 544, 144, 1024)
DETAIL_BOOK = (160, 736, 320, 1024)
DETAIL_PAGE = (328, 824, 472, 1024)
DETAIL_COAT = (480, 736, 1024, 1024)
DETAIL_EMBLEM = (152, 544, 408, 800)


def interp(points, x):
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def ring_pt(centre, radius, angle, sy, py):
    return Vector((centre.x + radius * S * math.cos(angle),
                   centre.y + radius * S * sy * math.sin(angle), H(py)))


def outward_from(centre, sy=1.0):
    return lambda p: Vector((p.x - centre.x, (p.y - centre.y) / (sy * sy), 0.0))


def add_joints(b):
    b.joints["root"] = (Vector((0, 0, 0)), Vector((0, -0.10, 0)), None)
    b.joints["hips"] = (P(CX, 91), P(CX, 72), "root")
    b.joints["spine"] = (P(CX, 72), P(CX, 58), "hips")
    b.joints["chest"] = (P(CX, 58), P(CX, 45), "spine")
    b.joints["neck"] = (P(CX, 45), P(CX, 39), "chest")
    b.joints["head"] = (P(CX, 39), P(CX, 22), "neck")


# -- porcelain head ---------------------------------------------------------

HEAD_C = P(CX, 27)
HEAD_H = 20.5 * S
CUP_SY = 1.0


def capsule_outline(rx, rz, n=16):
    """A flat rounded eye/card outline in local X/Z coordinates."""
    return [(rx * math.copysign(abs(math.cos(a)) ** .72, math.cos(a)),
             rz * math.copysign(abs(math.sin(a)) ** .72, math.sin(a)))
            for a in (2 * math.pi * k / n for k in range(n))]


def build_head(b):
    """A broad, shallow teacup—not a mug—with a real inner bowl and mounted handle."""
    c, h = HEAD_C, HEAD_H
    # Outer wall rises from a small foot into the broad bowl; the inner wall
    # returns beneath the rim so the porcelain remains one closed shell.
    prof = [
        (0.0, -h * .50), (.060, -h * .50), (.078, -h * .43),
        (.108, -h * .20), (.138, h * .29), (.153, h * .46),
        (.157, h * .50), (.135, h * .50), (.132, h * .42),
        (.119, h * .25), (.096, -h * .20), (.067, -h * .36), (0.0, -h * .36),
    ]
    verts, bands, _ = b.lathe(prof, 32, Matrix.Translation(c), sy=CUP_SY)
    faces = b.finish(verts, "ivory", "head")
    b.paint(bands[0] + bands[1], "gold")
    b.paint(bands[8] + bands[9] + bands[10], "cream_shade")

    def cup_uv(co):
        a = math.atan2((co.y - c.y) / CUP_SY, co.x - c.x)
        return ((a + math.pi * 1.5) % (2 * math.pi)) / (2 * math.pi), \
            (c.z + h * .46 - co.z) / (h * .94)
    b.map_detail([f for f in bands[3] + bands[4] if abs(f.normal.z) < .92],
                 DETAIL_CUP, cup_uv, wrap=True)

    # The lip is structural and restrained; its blue/gold decoration is atlas art.
    for z, rin, rout, th, colour in ((h * .48, .132, .160, .010, "ivory"),
                                      (h * .52, .145, .159, .006, "gold")):
        lip, _, _ = b.lathe([(rout, -th/2), (rout, th/2),
                             (rin, th/2), (rin, -th/2)], 32,
                            Matrix.Translation(c + Vector((0, 0, z))),
                            sy=CUP_SY, loop=True)
        b.finish(lip, colour, "head", smooth=False)

    tea_z = c.z + h * .475
    tea, _, _ = b.lathe([(0, -.002), (.140, -.002), (.140, .003), (0, .003)], 32,
                        Matrix.Translation(Vector((c.x, c.y, tea_z))), sy=CUP_SY)
    b.finish(tea, "brown_dark", "head")
    # A hidden liquid plug reaches the inner bowl floor, keeping the tea attached
    # without changing the visible surface.
    b.finish(b.tube([Vector((c.x, c.y, tea_z)),
                     Vector((c.x, c.y, c.z - h * .39))], .012, 8),
             "brown_dark", "head")
    tea_ring, _, _ = b.lathe([(.140, -.002), (.140, .002), (.122, .002), (.122, -.002)],
                             32, Matrix.Translation(Vector((c.x, c.y, tea_z + .002))),
                             sy=CUP_SY, loop=True)
    b.finish(tea_ring, "tan", "head", smooth=False)

    # Exterior cubic handle.  The endpoints follow the changing cup radius;
    # their short mounts enter only the porcelain wall, never the inner bowl.
    p0 = c + Vector((.142, .002, .055))
    p1 = c + Vector((.238, .002, .058))
    p2 = c + Vector((.235, .002, -.055))
    p3 = c + Vector((.104, .002, -.055))
    pts = []
    for k in range(21):
        t = k / 20
        u = 1.0 - t
        pts.append(p0 * (u ** 3) + p1 * (3 * u * u * t)
                   + p2 * (3 * u * t * t) + p3 * (t ** 3))
    b.finish(b.tube(pts, .015, 10, rs=[.014, .015] + [.016] * 17 + [.015, .014]),
             "ivory", "head")
    for p, depth in ((p0, .006), (p3, .005)):
        b.finish(b.tube([p - Vector((depth, 0, 0)), p + Vector((.008, 0, 0))],
                        .0135, 10), "ivory", "head")

    # Layered porcelain inlays, warped vertex-by-vertex onto the cup wall.  The
    # local frame follows the conical slope and every outline point is projected
    # back to the ellipse, so the eyes are neither vertical cards nor decals.
    eye_z = c.z - .010
    wall_r0, wall_dr, wall_sy = .119, .383, CUP_SY
    for sx in (-1, 1):
        ex = sx * .048
        a0 = -math.acos(ex / wall_r0)
        surf = Vector((c.x + ex, c.y + wall_sy * wall_r0 * math.sin(a0), eye_z))
        tangent = Vector((-wall_r0 * math.sin(a0), wall_sy * wall_r0 * math.cos(a0), 0)).normalized()
        rise = Vector((wall_dr * math.cos(a0), wall_sy * wall_dr * math.sin(a0), 1))
        normal = tangent.cross(rise).normalized()
        if normal.y > 0:
            normal = -normal
        base = frame(surf, normal, tangent)

        def eye_layer(outline, thickness, lift, shift, colour):
            def conform(p):
                q = Vector((p.x + shift[0], p.y + shift[1], 0))
                approx = base @ q
                radius = wall_r0 + wall_dr * (approx.z - eye_z)
                xrel = approx.x - c.x
                y = c.y - wall_sy * math.sqrt(max(.0001, radius * radius - xrel * xrel))
                aa = math.atan2((y - c.y) / wall_sy, xrel)
                ta = Vector((-radius * math.sin(aa), wall_sy * radius * math.cos(aa), 0)).normalized()
                rz = Vector((wall_dr * math.cos(aa), wall_sy * wall_dr * math.sin(aa), 1))
                n = ta.cross(rz).normalized()
                if n.y > 0:
                    n = -n
                return Vector((approx.x, y, approx.z)) + n * (lift + p.z)
            b.finish(b.slab(outline, thickness, Matrix.Identity(4), warp=conform),
                     colour, "head", smooth=False)

        eye_layer(capsule_outline(.018, .040), .0012, .0006, (0, 0), "outline")
        eye_layer(capsule_outline(.010, .029), .0010, .0017, (0, -.001), "amber")
        eye_layer(capsule_outline(.0032, .0060, 10), .0008, .0026,
                  (-sx * .0025, .009), "ivory")

    # Neck parts overlap both the torso and the cup foot, so the head cannot float.
    b.finish(b.tube([P(CX, 46), P(CX, 37)], .041, 12, rs=[.049, .039]),
             "blue_dark", "neck")
    b.finish(b.ring(P(CX, 43), (0, 0, 1), .039, .057, .018, 16),
             "gold", "neck", smooth=False)


# -- body and cloth ---------------------------------------------------------

TORSO_PROF = [(0, 91), (13, 91), (14.5, 80), (15.5, 68), (16, 57),
              (17.5, 51), (13, 46), (7, 44), (0, 44)]
TORSO_SY = .70
BELT_TOP, BELT_BOTTOM = 66.0, 72.0


def torso_r(py):
    pts = sorted(TORSO_PROF[1:-1], key=lambda q: q[1])
    return interp([(y, r) for r, y in pts], py)


def body_pt(px, py, r, sy=TORSO_SY):
    dx = max(-r * .97, min(r * .97, px - CX))
    y = -sy * math.sqrt(max(0.0, r * r - dx * dx))
    n = Vector((dx, y / (sy * sy), 0)).normalized()
    return P(px, py, y * S), n


def build_torso(b):
    verts, _, _ = b.lathe([(r * S, H(py)) for r, py in TORSO_PROF], 20,
                          Matrix.Translation(P(CX, GROUND)), sy=TORSO_SY)
    b.finish(verts, "blue_dark", "torso")
    add_joints(b)


ROBE_TOP, ROBE_HEM = 63.0, 108.0


def robe_r(py):
    return interp([(ROBE_TOP, 15.8), (70, 16.4), (82, 20.5), (96, 26.0), (ROBE_HEM, 29.0)], py)


def robe_sy(py):
    return .70 + .08 * smoothstep((py - 70) / 30)


def build_robe(b):
    """One open-front robe surface, with folds in its geometry and a split at the hem."""
    rows, cols = 15, 36
    centre = P(CX, GROUND)
    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        py = ROBE_TOP + (ROBE_HEM - ROBE_TOP) * t
        half = math.radians(10 + 20 * smoothstep((t - .20) / .80))
        row = []
        for i in range(cols + 1):
            a = -math.pi / 2 + half + (2 * math.pi - 2 * half) * i / cols
            fold = (1.25 * t + .25 * t * t) * math.sin(7 * a + .25)
            hem = 1.6 * (math.sin(i * 1.7) ** 2) if j == rows - 1 else 0.0
            row.append(ring_pt(centre, robe_r(py + hem) + fold, a, robe_sy(py), py + hem))
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre, .75))
    verts, fronts, backs = cloth(b, mids, norms, .70 * S)
    faces = b.finish(verts, "cream", "robe", smooth=False)
    b.paint(list(backs.values()), "cream_shade")

    def robe_uv(co):
        py = GROUND - co.z / S
        a = math.atan2((co.y - centre.y) / robe_sy(py), co.x - centre.x)
        return ((a + math.pi * 1.5) % (2 * math.pi)) / (2 * math.pi), \
            (H(ROBE_TOP) - co.z) / (H(ROBE_TOP) - H(ROBE_HEM))
    b.map_detail([f for fs in fronts.values() for f in fs], DETAIL_ROBE, robe_uv, wrap=True)
    b.set_sway(faces, H(BELT_BOTTOM), H(ROBE_HEM))
    chain_weights(b, verts, H(ROBE_TOP), H(ROBE_TOP) - H(ROBE_HEM),
                  (("hips", .0), ("robe_1", .38), ("robe_2", .78)), .46)
    c = cols // 2
    b.joints["robe_1"] = (mids[2][c], mids[8][c], "hips")
    b.joints["robe_2"] = (mids[8][c], mids[-1][c], "robe_1")
    return verts


def map_grid_detail(b, fronts, mids, region, pad=6):
    """Map a cloth grid without angle reconstruction or atlas-edge bleeding."""
    rows, cols = len(mids), len(mids[0]) - 1
    x0, y0, x1, y1 = region
    for (j, i), fs in fronts.items():
        corners = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
        targets = (mids[j][i], mids[j][i + 1], mids[j + 1][i + 1], mids[j + 1][i])
        for face in fs:
            unused = set(range(4))
            for loop in face.loops:
                k = min(unused, key=lambda n: (loop.vert.co - targets[n]).length_squared)
                unused.remove(k)
                ci, cj = corners[k]
                u, v = ci / cols, cj / (rows - 1)
                loop[b.uv].uv = detail_uv(x0 + pad + (x1 - x0 - 2 * pad) * u,
                                           y0 + pad + (y1 - y0 - 2 * pad) * v)


def build_wrap_layer(b, part, colour, lining, top_py, hem_py, radial_px,
                     opening_top, opening_hem, detail=None, rows=14, cols=34):
    """Build one closed, open-front garment that remains continuous round the back."""
    centre = P(CX, GROUND)
    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        py = top_py + (hem_py - top_py) * t
        radial = (radial_px[0] + (radial_px[1] - radial_px[0]) * smoothstep(t / .40)
                  if isinstance(radial_px, tuple) else radial_px)
        half = math.radians(opening_top + (opening_hem - opening_top) * smoothstep(t))
        row = []
        for i in range(cols + 1):
            a = -math.pi / 2 + half + (2 * math.pi - 2 * half) * i / cols
            hem = 2.6 * (math.sin(i * 1.37) ** 2) * smoothstep((t - .84) / .16)
            fold = (1.0 + .8 * t) * math.sin(6 * a + .4) * t
            q = py + hem
            row.append(ring_pt(centre, robe_r(q) + radial + fold, a, robe_sy(q), q))
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre, .76))
    verts, fronts, backs = cloth(b, mids, norms, .72 * S)
    faces = b.finish(verts, colour, part, smooth=False)
    b.paint(list(backs.values()), lining)
    if detail:
        map_grid_detail(b, fronts, mids, detail)
    b.set_sway(faces, H(BELT_BOTTOM), H(hem_py))
    chain_weights(b, verts, H(top_py), H(top_py) - H(hem_py),
                  (("hips", -.05), ("robe_1", .40), ("robe_2", .82)), .48)
    return verts


def build_coat_layers(b):
    """Two genuine robe shells: blue mid-layer and porcelain outer coat."""
    mid = build_wrap_layer(b, "mid_robe", "blue", "blue_dark",
                           42.0, 110.0, (-1.2, 4.8), 12.0, 38.0, None, rows=16, cols=28)
    outer = build_wrap_layer(b, "outer_robe", "ivory", "cream_shade",
                             42.0, 104.5, (1.8, 8.0), 17.0, 47.0,
                             DETAIL_COAT, rows=16, cols=30)
    return mid, outer


def tabard_radial(py):
    """Place the tabard midway between the blue and porcelain robe shells."""
    mid_t = (py - 42.0) / (110.0 - 42.0)
    outer_t = (py - 42.0) / (104.5 - 42.0)
    mid = -1.2 + (4.8 - -1.2) * smoothstep(mid_t / .40)
    outer = 1.8 + (8.0 - 1.8) * smoothstep(outer_t / .40)
    return (mid + outer) * .5


def tabard_centre(py):
    p, _ = body_pt(CX, py, robe_r(py) + tabard_radial(py), robe_sy(py))
    p.y -= .004
    return p


def build_cape(b):
    """Lamp-style cape: tucked under the mantle, pinned with it, then free."""
    top_py, hem_py = 55.5, 111.0
    # As on Lamp Warden, the first rows sit just under the mantle and a dense
    # pair of rows carries its silhouette out below the lowest scallop.
    pys = [55.5, 58.5, 60.8, 61.3, 64.0, 68.0, 73.0, 79.0,
           85.0, 91.0, 97.0, 103.0, 108.0, 111.0]
    rows, cols = len(pys), 28
    centre = P(CX, GROUND)
    mids = []
    for j, py in enumerate(pys):
        t = (py - top_py) / (hem_py - top_py)
        a0, a1 = math.radians(22 - 16 * t), math.radians(158 + 16 * t)
        row = []
        for i in range(cols + 1):
            a = a0 + (a1 - a0) * i / cols
            q = py + (2.4 * (math.sin(i * 1.55) ** 2) if j == rows - 1 else 0.0)
            if q <= 58.5:
                mt = max(0.0, min(1.0, (q - 44.5) / (59.0 - 44.5)))
                radius = 17.0 + 12.0 * mt - 2.6
            elif q <= 60.8:
                radius = 26.0 + 1.6 * smoothstep((q - 58.5) / 2.3)
            else:
                radius = robe_r(q) + 11.2 + 2.0 * t
            radius += 1.8 * t * math.sin(6 * a + .35)
            sy = .74 + .18 * smoothstep((q - 60.8) / 16.0)
            p = ring_pt(centre, radius, a, sy, q)
            p.y += .010 * t * t * max(0, math.sin(a))
            row.append(p)
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre, .92))
    verts, fronts, backs = cloth(b, mids, norms, 1.0 * S)
    faces = b.finish(verts, "blue_dark", "cape", smooth=False)
    b.paint(list(backs.values()), "cream_shade")
    b.set_sway(faces, H(top_py), H(hem_py))
    c = cols // 2
    js = [mids[round(k * (rows - 1) / 3)][c] for k in range(4)]
    for i in range(3):
        b.joints[f"cape_{i + 1}"] = (js[i], js[i + 1], "chest" if i == 0 else f"cape_{i}")
    chain_weights(b, verts, H(top_py), H(top_py) - H(hem_py),
                  (("chest", -.08), ("cape_1", .18), ("cape_2", .54), ("cape_3", .90)), .36)
    return verts


def build_mantle(b):
    """A thick shoulder capelet with fitted arm gaps and a scalloped lower edge."""
    rows, cols = 7, 34
    top_py, hem_py = 42.0, 59.0
    centre = P(CX, GROUND)
    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        py = top_py + (hem_py - top_py) * t
        half = math.radians(20 + 8 * t)
        row = []
        for i in range(cols + 1):
            a = -math.pi / 2 + half + (2 * math.pi - 2 * half) * i / cols
            scallop = 1.7 * (math.sin(5 * a) ** 2) * smoothstep((t - .65) / .35)
            row.append(ring_pt(centre, 17.0 + 12.0 * t, a, .74, py + scallop))
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre, .74))
    verts, fronts, backs = cloth(b, mids, norms, .95 * S)
    faces = b.finish(verts, "ivory", "mantle", smooth=False)
    b.paint(list(backs.values()), "blue_dark")

    def mantle_uv(co):
        a = math.atan2((co.y - centre.y) / .74, co.x - centre.x)
        return ((a + math.pi * 1.5) % (2 * math.pi)) / (2 * math.pi), \
            (H(top_py) - co.z) / (H(top_py) - H(hem_py))
    b.map_detail([f for fs in fronts.values() for f in fs], DETAIL_MANTLE, mantle_uv, wrap=True)
    b.mantle_verts = verts

    return verts


def pin_cape_to_mantle(b, cape):
    """Copy Lamp Warden's pinned-row behavior onto the cape attachment."""
    mantle = KDTree(len(b.mantle_verts))
    for i, mv in enumerate(b.mantle_verts):
        mantle.insert(mv.co, i)
    mantle.balance()
    pin_z, free_z = H(58.5), H(68.0)
    for v in cape:
        k = smoothstep((v.co.z - free_z) / (pin_z - free_z))
        if k <= 0.0:
            continue
        dv = v[b.deform]
        for i in list(dv.keys()):
            dv[i] *= 1.0 - k
        near = b.mantle_verts[mantle.find(v.co)[1]][b.deform]
        for i, w in near.items():
            dv[i] = dv.get(i, 0.0) + k * w


def build_saucer_collar(b):
    """A shallow porcelain saucer collar, with a line-art pendant beneath it."""
    # Sit directly beneath the cup foot, leaving only a short blue neck reveal.
    c = P(CX, 40.5)
    prof = [(.052, -.005), (.055, .006), (.132, .010), (.151, .003),
            (.151, -.004), (.132, -.010), (.055, -.011)]
    verts, _, _ = b.lathe(prof, 32, Matrix.Translation(c), sy=1.0, loop=True)
    faces = b.finish(verts, "ivory", "collar", smooth=False)
    b.map_detail([f for f in faces if f.normal.z > .35], DETAIL_COLLAR,
                 lambda co: (.5 + (co.x - c.x) / .31,
                             .5 + (co.y - c.y) / .31))
    b.finish(b.ring(c + Vector((0, 0, .007)), (0, 0, 1), .143, .153, .006, 32),
             "gold", "collar", smooth=False)

    # Seat the medallion on the tabard's actual vertical tangent.  Its back
    # face clears the curved cloth by 4 mm, enough to clear its local bulge
    # while remaining visually seated beneath the collar.
    med_py = 47.2
    up = (tabard_centre(med_py - 1.0) - tabard_centre(med_py + 1.0)).normalized()
    normal = Vector((0.0, -up.z, up.y)).normalized()
    med = tabard_centre(med_py) + normal * (.65 * S / 2 + .006 / 2 + .004)
    outline = [(math.cos(2 * math.pi * k / 20) * .034,
                math.sin(2 * math.pi * k / 20) * .038) for k in range(20)]
    med_faces = b.finish(b.slab(outline, .006, frame(med, normal, (1, 0, 0))),
                         "ivory", "medallion", smooth=False)
    b.map_detail([f for f in med_faces if f.normal.y < -.7], DETAIL_EMBLEM,
                 lambda co: (.5 + (co.x - med.x) / .068,
                             .5 - (co.z - med.z) / .076))


def build_belt_and_tabard(b):
    belt, _, _ = b.lathe([(17.0 * S, H(BELT_BOTTOM)), (17.3 * S, H(BELT_BOTTOM)),
                          (17.3 * S, H(BELT_TOP)), (17.0 * S, H(BELT_TOP))],
                         28, Matrix.Identity(4), sy=.72, loop=True)
    b.finish(belt, "brown_dark", "belt", smooth=False)
    buckle = P(CX, 69, -12.7 * S)
    b.finish(b.box(buckle, (.056, .018, .046)), "gold", "belt", smooth=False)
    b.finish(b.box(buckle - Vector((0, .011, 0)), (.032, .006, .023)), "brown_dark", "belt", smooth=False)

    rows, cols = 16, 6
    top_py, hem_py = 41.5, 103.0
    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        py = top_py + (hem_py - top_py) * t
        half = 6.8 - .8 * t
        row = []
        for i in range(cols + 1):
            u = i / cols
            q = py - (5.0 * abs(2 * u - 1) * smoothstep((t - .78) / .22))
            # Keep the entire tabard between the blue mid-robe and porcelain
            # outer robe.  This is a real depth ordering, not a front overlay.
            radial = tabard_radial(py)
            p, _ = body_pt(CX + (2 * u - 1) * half, q, robe_r(q) + radial, robe_sy(q))
            p.y -= .004
            row.append(p)
        mids.append(row)
    norms = grid_normals(mids, outward=lambda p: Vector((0, -1, 0)))
    verts, fronts, backs = cloth(b, mids, norms, .65 * S)
    faces = b.finish(verts, "blue", "tabard", smooth=False)
    b.paint(list(backs.values()), "blue_dark")
    b.map_detail([f for fs in fronts.values() for f in fs], DETAIL_TABARD,
                 lambda co: (.5 + co.x / (13.6 * S),
                             (H(top_py) - co.z) / (H(top_py) - H(hem_py))))
    b.set_sway(faces, H(BELT_BOTTOM), H(hem_py))


# -- limbs, sleeves, book, and hands ---------------------------------------

ARM_R = (P(CX - 17, 50), P(CX - 27, 65, -.005), P(CX - 31, 57, -.100))
ARM_L = (P(CX + 17, 50), P(CX + 27, 65, -.005), P(CX + 35, 58, -.085))


def build_arm(b, side, joints):
    shoulder, elbow, wrist = joints
    upper, fore = "upperarm_" + side, "forearm_" + side
    b.joints[upper] = (shoulder, elbow, "chest")
    b.joints[fore] = (elbow, wrist, upper)
    hand_end = wrist + (wrist - elbow).normalized() * .065
    b.joints["hand_" + side] = (wrist, hand_end, fore)

    b.finish(b.sphere(shoulder, .053, 12, 7, (1.0, .88, 1.0)), "ivory", upper)
    b.finish(b.tube([shoulder, shoulder.lerp(elbow, .48), elbow], .040, 12,
                    rs=[.047, .043, .036]), "cream", upper)
    axis = (wrist - elbow).normalized()
    end = wrist - axis * .014
    cuff = end - axis * (.025 if side == "R" else 0.0)
    sleeve_end = cuff - axis * .011
    cuff_scale = .84 if side == "R" else 1.0
    verts = b.tube([elbow, elbow.lerp(sleeve_end, .32), elbow.lerp(sleeve_end, .66), sleeve_end], .040, 16,
                   rs=[.036, .047, .063 * cuff_scale, .074 * cuff_scale])
    faces = b.finish(verts, "ivory", fore)
    ref = Vector((0, 0, 1)) - axis * axis.z
    if ref.length < .001:
        ref = axis.orthogonal()
    ref.normalize()
    length = (cuff - elbow).length

    def sleeve_uv(co):
        r = co - elbow
        along = r.dot(axis)
        radial = r - axis * along
        a = math.atan2(axis.cross(ref).dot(radial), ref.dot(radial))
        return (a / (2 * math.pi)) % 1.0, along / length
    b.map_detail([f for f in faces if abs(f.normal.dot(axis)) < .90], DETAIL_SLEEVE, sleeve_uv, wrap=True)
    # A recessed dark opening and raised porcelain cuff give the sleeve real depth.
    b.finish(b.ring(cuff - axis * .008, axis, 0, .065 * cuff_scale, .004, 16),
             "blue_dark", fore, smooth=False)
    b.finish(b.ring(cuff - axis * .002, axis, .031 * cuff_scale, .078 * cuff_scale, .012, 16),
             "ivory", fore, smooth=False)
    b.finish(b.ring(cuff + axis * .005, axis, .066 * cuff_scale, .079 * cuff_scale, .006, 16),
             "gold", fore, smooth=False)
    build_sleeve_drape(b, side, elbow, cuff, fore)


def build_sleeve_drape(b, side, elbow, cuff, part):
    """Large heraldic sleeve panel hanging from the forearm as in the concept."""
    sx = -1 if side == "R" else 1
    out = Vector((sx, 0, 0))
    rows, cols = 9, 5
    top_inner = elbow + out * .010 - Vector((0, .025, 0))
    top_outer = elbow + out * .075 - Vector((0, .020, .010))
    bot_inner = cuff + out * .025 + Vector((0, .010, -.145))
    bot_outer = cuff + out * .125 + Vector((0, .020, -.185))
    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        a = top_inner.lerp(bot_inner, t)
        c = top_outer.lerp(bot_outer, t)
        row = []
        for i in range(cols):
            u = i / (cols - 1)
            p = a.lerp(c, u)
            p.y -= .010 * math.sin(math.pi * u) * math.sin(math.pi * t)
            if j == rows - 1:
                p.z += .018 * abs(2 * u - 1)
            row.append(p)
        mids.append(row)
    norms = grid_normals(mids, outward=lambda p: Vector((0, -1, 0)))
    verts, fronts, backs = cloth(b, mids, norms, .65 * S)
    faces = b.finish(verts, "ivory", part, smooth=False)
    b.paint(list(backs.values()), "blue")
    b.map_detail([f for fs in fronts.values() for f in fs], DETAIL_COAT,
                 lambda co: ((co.x - min(top_inner.x, bot_inner.x, top_outer.x, bot_outer.x)) /
                             (max(top_inner.x, bot_inner.x, top_outer.x, bot_outer.x) -
                              min(top_inner.x, bot_inner.x, top_outer.x, bot_outer.x)),
                             (max(top_inner.z, top_outer.z) - co.z) /
                             (max(top_inner.z, top_outer.z) - min(bot_inner.z, bot_outer.z))))
    b.set_sway(faces, elbow.z, min(bot_inner.z, bot_outer.z))


def open_hand(b, wrist, forward, palm_up, side, palm_at=None):
    """Approved-character open glove construction, with correct thumb chirality."""
    part = "hand_" + side
    f = Vector(forward).normalized()
    up = Vector(palm_up) - f * Vector(palm_up).dot(f)
    up.normalize()
    across = f.cross(up).normalized()
    thumb_side = across if side == "R" else -across
    palm = Vector(palm_at) if palm_at is not None else wrist + f * 3.2 * S
    b.finish(b.box(palm, (6.6 * S, 6.0 * S, 2.4 * S), xdir=across, zdir=up),
             "mauve", part, smooth=False)
    tip_base = palm + f * 3.0 * S
    for k, off in enumerate((2.5, .85, -.85, -2.5)):
        o = thumb_side * off * S
        length = (4.6 if 0 < k < 3 else 4.0) * S
        pts = [tip_base + o, tip_base + o + f * length * .55 + up * .4 * S,
               tip_base + o + f * length + up * 1.6 * S]
        b.finish(b.tube(pts, .95 * S, 5, rs=[1.0 * S, .95 * S, .8 * S]), "mauve", part)
    t0 = palm + thumb_side * 3.0 * S - f * .8 * S
    b.finish(b.tube([t0, t0 + thumb_side * 2.2 * S + f * 1.4 * S + up * .8 * S,
                     t0 + thumb_side * 3.0 * S + f * 3.4 * S + up * 1.8 * S],
                    1.05 * S, 5, rs=[1.15 * S, 1.0 * S, .85 * S]), "mauve", part)
    return palm


def book_wing(b, spine, sign, axis, across, facing):
    """One cover/page wing; its inner pages face the cleric's head."""
    w, h = .087, .154
    xdir = (across * sign + facing * .24).normalized()
    xdir = (xdir - axis * xdir.dot(axis)).normalized()
    normal = axis.cross(xdir).normalized()
    if normal.dot(facing) < 0:
        normal = -normal
    centre = spine + xdir * w * .52
    cover = b.finish(b.box(centre, (w, .012, h), xdir=xdir, zdir=axis),
                     "blue_dark", "book", smooth=False)
    # Map each cover independently so the cross remains centred and undistorted.
    b.map_detail([f for f in cover if f.normal.dot(normal) > .7], DETAIL_BOOK,
                 lambda co: ((co - spine).dot(xdir) / w,
                             .5 - (co - spine).dot(axis) / h))
    page_c = centre + normal * .011
    for k in range(4):
        q = page_c + normal * (.003 * k) + xdir * (.0015 * k)
        page_faces = b.finish(b.box(q, (w - .021 - .003 * k, .006, h - .023 - .004 * k),
                                    xdir=xdir, zdir=axis),
                              "ivory" if k < 3 else "cream_warm", "book", smooth=False)
        if k == 3:
            b.map_detail([f for f in page_faces if f.normal.dot(normal) > .7], DETAIL_PAGE,
                         lambda co: ((co - (q - xdir * (w - .030) / 2)).dot(xdir) / (w - .030),
                                     .5 - (co - q).dot(axis) / (h - .035)))
    # A narrow concealed binding joins the cover and every raised page layer
    # to the gold spine, keeping the open book a single physical assembly.
    binding = spine + xdir * .010 + normal * .010
    b.finish(b.box(binding, (.022, .036, h - .030), xdir=xdir, zdir=axis),
             "blue_dark", "book", smooth=False)
    return centre, xdir, normal


def build_book_and_grip(b):
    wrist = ARM_R[2]
    fore_axis = (wrist - ARM_R[1]).normalized()
    # Carry the book beyond the flared cuff as one book/hand assembly.  Moving
    # along the forearm preserves the approved grip and page-facing direction.
    spine = P(CX - 27, 52, -.120) + fore_axis * .020 + Vector((0, -.040, 0))
    facing = (P(CX, 27, -.015) - spine).normalized()
    up = Vector((0, 0, 1))
    axis = (up - facing * up.dot(facing)).normalized()
    across = facing.cross(axis).normalized()
    book_wing(b, spine, -1, axis, across, facing)
    book_wing(b, spine, 1, axis, across, facing)
    b.finish(b.tube([spine - axis * .082, spine + axis * .082],
                    .013, 10), "gold", "book")
    # The palm lies flat against the exterior of the spine.  Fingers run at a
    # right angle to the spine, outside the book, rather than supporting pages
    # from underneath or pointing toward the camera.
    finger_dir = across if across.x > 0 else -across
    outside = -facing
    contact = spine - axis * .025 + outside * .018
    palm_at = contact - finger_dir * .020
    palm = open_hand(b, wrist, finger_dir, facing, "R", palm_at=palm_at)
    b.finish(b.sphere(wrist - fore_axis * .010, .022, 10, 6, (1.0, .78, .86)),
             "mauve", "hand_R")
    cuff_anchor = wrist - fore_axis * .036
    b.finish(b.sphere(cuff_anchor, .029, 10, 6, (1.0, .78, .86)),
             "mauve", "hand_R")
    b.finish(b.tube([cuff_anchor, wrist, palm], .018, 8,
                    rs=[.020, .021, .019]), "mauve", "hand_R")


def build_arms(b):
    build_arm(b, "R", ARM_R)
    build_arm(b, "L", ARM_L)
    build_book_and_grip(b)
    # Character-left hand is the blessing gesture; steam/sparkles remain in Godot.
    palm = open_hand(b, ARM_L[2], (.28, -.86, .42), (0, 0, 1), "L")
    b.finish(b.sphere(ARM_L[2], .024, 10, 6, (1.0, .78, .82)), "mauve", "hand_L")
    b.finish(b.tube([ARM_L[2], palm], .017, 8, rs=[.020, .018]), "mauve", "hand_L")


# -- legs ------------------------------------------------------------------

SHOE_BACK, SHOE_TIP, SHOE_SOLE = -.034, .064, 0.0


def shoe_size(u):
    w = interp([(SHOE_BACK, .050), (-.005, .060), (.030, .067), (SHOE_TIP, .053)], u)
    h = interp([(SHOE_BACK, .040), (-.008, .052), (.018, .040), (.045, .027), (SHOE_TIP, .020)], u)
    if u > .046:
        k = math.sqrt(max(0.0, 1 - ((u - .046) / (SHOE_TIP - .046)) ** 2))
    elif u < -.022:
        k = math.sqrt(max(0.0, 1 - ((u + .022) / (SHOE_BACK + .022)) ** 2))
    else:
        k = 1.0
    return w * max(k, .14), h * max(k, .28)


def build_shoe(b, base, ankle, part):
    """Approved-character multi-section boot loft, styled as the concept's strapped shoe."""
    toe = Vector((0, -1, 0))
    up = Vector((0, 0, 1))
    side = up.cross(toe).normalized()
    bm = b.bm
    us = [SHOE_BACK + (SHOE_TIP - SHOE_BACK) * k / 10 for k in range(11)]
    rings = []
    for u in us:
        w, h = shoe_size(u)
        ring = []
        for k in range(12):
            a = 2 * math.pi * k / 12
            x = w / 2 * math.copysign(abs(math.cos(a)) ** .76, math.cos(a))
            z = SHOE_SOLE + h / 2 + h / 2 * math.copysign(abs(math.sin(a)) ** .76, math.sin(a))
            ring.append(bm.verts.new(base + toe * u + side * x + up * z))
        rings.append(ring)
    made = [v for ring in rings for v in ring]
    for A, B in zip(rings, rings[1:]):
        for k in range(12):
            n = (k + 1) % 12
            bm.faces.new((A[k], A[n], B[n], B[k]))
    for ring, u in ((rings[0], us[0]), (rings[-1], us[-1])):
        _, h = shoe_size(u)
        c = bm.verts.new(base + toe * u + up * (SHOE_SOLE + h / 2))
        made.append(c)
        for k in range(12):
            bm.faces.new((ring[k], ring[(k + 1) % 12], c))
    b.finish(made, "ivory", part)

    b.finish(b.tube([base + up * .030 - toe * .008, ankle + up * 1.2 * S],
                    4.0 * S, 10, rs=[4.4 * S, 3.4 * S]), "cream", part)
    strap = base + toe * .003 + up * .050
    b.finish(b.box(strap, (.064, .022, .012), xdir=side, zdir=up),
             "brown", part, smooth=False)
    buckle = strap + Vector((0, -.013, .004))
    b.finish(b.box(buckle, (.024, .006, .020), xdir=side, zdir=up),
             "gold", part, smooth=False)
    b.finish(b.box(buckle - Vector((0, .004, 0)), (.012, .004, .009), xdir=side, zdir=up),
             "brown_dark", part, smooth=False)


def build_leg(b, side, sx):
    hip, knee, ankle = P(CX + sx * 8, 90), P(CX + sx * 9, 107, -.002), P(CX + sx * 11, 118)
    thigh, shin, foot = "thigh_" + side, "shin_" + side, "foot_" + side
    b.joints[thigh] = (hip, knee, "hips")
    b.joints[shin] = (knee, ankle, thigh)
    toe = ankle + Vector((0, -.070, -.004))
    b.joints[foot] = (ankle, toe, shin)
    b.finish(b.tube([hip, hip.lerp(knee, .48), knee], .029, 10,
                    rs=[.033, .030, .027]), "mauve", thigh)
    b.finish(b.sphere(knee, .036, 12, 7), "gold", shin)
    b.finish(b.sphere(knee - Vector((0, .024, 0)), .021, 10, 6, (1, .45, 1)), "amber", shin)
    b.finish(b.tube([knee, knee.lerp(ankle, .5), ankle], .024, 10,
                    rs=[.027, .024, .021]), "cream", shin)
    b.finish(b.ring(ankle + Vector((0, 0, .010)), (0, 0, 1), .022, .038, .018, 12),
             "gold", foot, smooth=False)
    build_shoe(b, Vector((ankle.x, ankle.y, 0)), ankle, foot)


def build_mesh():
    b = Builder()
    build_torso(b)
    robe = build_robe(b)
    build_coat_layers(b)
    mantle = build_mantle(b)
    build_saucer_collar(b)
    cape = build_cape(b)
    build_belt_and_tabard(b)
    build_head(b)
    build_arms(b)
    build_leg(b, "R", -1)
    build_leg(b, "L", 1)
    toy3d.follow_limbs(b, robe, H(BELT_BOTTOM),
                       {"thigh_R": (P(CX - 8, 90), P(CX - 9, 107)),
                        "thigh_L": (P(CX + 8, 90), P(CX + 9, 107))},
                       body=("hips",), reach=13, fade=7, pin=7)
    toy3d.follow_limbs(b, mantle, H(42.0),
                       {"upperarm_R": ARM_R[:2], "upperarm_L": ARM_L[:2]},
                       body=("chest",), reach=14, fade=7, pin=6)
    pin_cape_to_mantle(b, cape)
    return b


def build_preview():
    """Build one unrigged mesh/material for owner approval."""
    toy3d.configure(CHAR)
    os.makedirs(CHAR.src_dir, exist_ok=True)
    open(os.path.join(CHAR.src_dir, ".gdignore"), "a").close()
    for name in ("Cube", "Camera", "Light", CHAR.object_name, CHAR.object_name + "Rig"):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    col = bpy.data.collections.get(CHAR.object_name)
    if col is None:
        col = bpy.data.collections.new(CHAR.object_name)
        bpy.context.scene.collection.children.link(col)
    b = build_mesh()
    mesh, tris = toy3d.finish_mesh(b)
    mesh.materials.append(toy3d.make_material())
    obj = bpy.data.objects.new(CHAR.object_name, mesh)
    col.objects.link(obj)
    obj["toy"] = CHAR.object_name
    obj["parts"] = b.parts
    toy3d.show_colours()
    return obj, tris


def validate_mesh(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    nonmanifold = sum(1 for e in bm.edges if not e.is_manifold)
    loose = sum(1 for v in bm.verts if not v.link_faces)
    bm.free()
    ngons = sum(1 for p in obj.data.polygons if len(p.vertices) > 4)
    return {"verts": len(obj.data.vertices), "tris": len(obj.data.polygons),
            "ngons": ngons, "nonmanifold_edges": nonmanifold, "loose_verts": loose,
            "rest_clips": toy3d.clip_report(obj),
            "island_gaps": [(g, tuple(round(x, 4) for x in c), round(d, 4))
                            for g, c, d in toy3d.island_gaps(obj)]}


def render_previews(obj):
    shoot = toy3d.preview_camera(obj)
    col = obj.users_collection[0]
    fill_data = bpy.data.lights.new(CHAR.object_name + "PreviewFill", "SUN")
    fill_data.energy = .55
    fill = bpy.data.objects.new(CHAR.object_name + "PreviewFill", fill_data)
    col.objects.link(fill)
    fill.rotation_euler = (math.radians(-35), math.radians(15), math.radians(145))
    cx = (64 - CHAR.px) * S
    cz = (CHAR.ground - 64) * S
    shoot("preview_front.png", (cx, -5, cz), (cx, 0, cz), ortho=1.06)
    shoot("preview_128.png", (cx, -5, cz), (cx, 0, cz), ortho=1.0, res=128, width=.009, aa=0)
    shoot("preview_3q.png", (-1.4, -2.2, 1.15), (0, 0, .43), ortho=1.05)
    shoot("preview_side.png", (5, 0, cz), (0, 0, cz), ortho=1.06)
    shoot("preview_back.png", (1.2, 2.6, 1.05), (0, 0, .43), ortho=1.05)
    shoot("preview_handle_close.png", (1.25, -1.8, 1.55), (0, 0, .94), ortho=.46)
    shoot("preview_book_close.png", (-1.35, -1.8, 1.02), (-.20, -.10, .58), ortho=.52)


if __name__ == "__main__" and bpy.app.background:
    obj, tris = build_preview()
    print("tris", sum(tris.values()), tris)
    print("validation", validate_mesh(obj))
    render_previews(obj)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(CHAR.src_dir, "teacup_cleric_preview.blend"))
    print("preview only: no rig, animations, GLB, steam, or sparkles")
