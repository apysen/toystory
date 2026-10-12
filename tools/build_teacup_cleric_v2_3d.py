"""Build the Teacup Cleric v2 (Blender), a separate model to compare with v1.

Headless:  D:/Blender/blender.exe --background --python tools/build_teacup_cleric_v2_3d.py
    builds and rigs v2, prints its checks (rest clips, floating pieces, vertex
    groups, atlas density), builds v1 beside it from its own unchanged script and
    renders both side by side into assets/models/teacup/source/v2/compare_*.png
Live, through the Blender MCP:  exec(open("tools/build_teacup_cleric_v2_3d.py").read())
    then  obj, tris, rest = build_teacup_v2()

v2 is object TeacupClericV2 / character teacup_cleric_v2, so it sits beside v1
(TeacupCleric) in one scene; everything it writes stays in source/v2 (no GLB, no
Godot integration yet). The 128 px player concept fixes scale and silhouette, the
concept sheet the look. Steam and blessing sparkles are Godot VFX.

Line art: a 2048 px atlas (toy3d.Character(detail_size=2048)) drawn by
tools/draw_teacup_details_v2.py, which this build runs itself once it has
unrolled every decorated surface and packed the regions (see Atlas below).
"""
import importlib
import json
import math
import os
import subprocess
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
    ("gold", "e1a93a", False), ("cream_warm", "e4c89b", False),
    ("cream", "e5d3b6", False), ("ivory", "ebe0c4", False),
]
# (ivory, cream, cream_warm and gold sit 8% under the sprite's: at full brightness the
# battle room's bloom haloed her porcelain gold; the owner's pick, 2026-10-11)

CX, GROUND = 61, 123


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
    "mantle": "chest", "head": "head", "neck": "chest", "brooch": "chest", "brooch_ring": "chest",
    "cape": "chest", "book": "book", "upperarm_R": "upperarm_R",
    "forearm_R": "forearm_R", "hand_R": "hand_R", "upperarm_L": "upperarm_L",
    "forearm_L": "forearm_L", "hand_L": "hand_L", "thigh_R": "thigh_R",
    "shin_R": "shin_R", "foot_R": "foot_R", "thigh_L": "thigh_L",
    "shin_L": "shin_L", "foot_L": "foot_L",
    "sleeve_R": "forearm_R", "sleeve_L": "forearm_L",     # reweighted in build_sleeve
    "cord": "chest", "tassel": "chest", "tabard_tassel": "hips",   # reweighted to their chains in build_gear
}

CLIP_CHECKS = (
    ("head", "collar"), ("head", "mantle"), ("book", "head"), ("book", "torso"),
    ("forearm_R", "torso"), ("forearm_L", "torso"), ("forearm_R", "outer_robe"), ("forearm_L", "outer_robe"),
    ("forearm_R", "book"),
    ("robe", "foot_R"), ("robe", "foot_L"),
    ("mid_robe", "robe"), ("outer_robe", "robe"),
    ("outer_robe", "mid_robe"), ("cape", "outer_robe"),
    # Cape/mantle is deliberately omitted: the cape's sewn yoke is tucked
    # beneath the mantle, while their visible surfaces remain ordered.
    ("tabard", "belt"), ("brooch", "tabard"), ("brooch", "collar"), ("brooch", "head"),
    ("sleeve_R", "book"), ("sleeve_L", "book"), ("sleeve_R", "hand_R"), ("sleeve_L", "hand_L"), ("hand_R", "book"),
    ("sleeve_R", "torso"), ("sleeve_L", "torso"), ("sleeve_R", "outer_robe"), ("sleeve_L", "outer_robe"),
    ("sleeve_R", "mid_robe"), ("sleeve_L", "mid_robe"), ("sleeve_R", "robe"), ("sleeve_L", "robe"),
    ("sleeve_R", "thigh_R"), ("sleeve_L", "thigh_L"), ("sleeve_R", "cape"), ("sleeve_L", "cape"),
    ("sleeve_R", "tabard"), ("sleeve_L", "tabard"), ("sleeve_R", "belt"), ("sleeve_L", "belt"),
    ("sleeve_R", "mantle"), ("sleeve_L", "mantle"),
    ("sleeve_R", "forearm_R"), ("sleeve_L", "forearm_L"),     # the bell over the cream under-sleeve
    # (the sleeve against the slim upper arm hidden inside it is left out: it rests
    # on it by design and none of it shows)
    ("cord", "tabard"), ("cord", "outer_robe"), ("cord", "mid_robe"), ("cord", "robe"), ("cord", "mantle"),
    ("cord", "brooch_ring"), ("cord", "sleeve_R"), ("cord", "sleeve_L"),
    ("tassel", "tabard"), ("tassel", "robe"), ("tassel", "outer_robe"), ("tassel", "mid_robe"),
    ("tassel", "sleeve_R"), ("tassel", "sleeve_L"), ("tassel", "thigh_R"), ("tassel", "thigh_L"),
    ("tabard_tassel", "robe"), ("tabard_tassel", "outer_robe"), ("tabard_tassel", "mid_robe"),
    ("tabard_tassel", "thigh_R"), ("tabard_tassel", "thigh_L"), ("tabard_tassel", "shin_R"),
    ("tabard_tassel", "shin_L"),
    # The cords start in the brooch's lobes and the tabard's tassels are knotted
    # into its edge, by design.
    # Each elbow ball sits in the upper arm's end by design (as on the Toaster).
    # The brooch's link rings pass through the tabard's top edge by design, and
    # its pin is sunk in the torso.
)

V2_DIR = os.path.join(toy3d.ROOT, "assets", "models", "teacup", "source", "v2")
DETAIL = os.path.join(V2_DIR, "teacup_details_v2.png")
LAYOUT = os.path.join(V2_DIR, "teacup_details_v2_layout.json")
COLLIDERS = os.path.join(V2_DIR, "teacup_cleric_v2_colliders.json")
DRAW_SCRIPT = os.path.join(_TOOLS, "draw_teacup_details_v2.py")
ATLAS_SIZE = 2048
ATLAS_PYTHON = os.environ.get("TOY_PYTHON", "python")   # plain Python with Pillow, for the art

CHAR = toy3d.Character(
    name="teacup_cleric_v2", folder="teacup", object_name="TeacupClericV2",
    pivot=(CX, GROUND), palette=PALETTE, part_bone=PART_BONE,
    body_weights=body_weights, clip_checks=CLIP_CHECKS, detail=DETAIL, detail_size=ATLAS_SIZE,
)
# a comparison build, not a game model yet: everything it writes stays in source/v2
CHAR.out_dir = CHAR.src_dir = V2_DIR
toy3d.configure(CHAR)


# -- the line-art atlas ---------------------------------------------------------
#
# Every decorated surface is unrolled flat in metres: a cloth grid is relaxed until
# its rows, columns and diagonals keep their true lengths (so a flaring mantle
# unrolls to the curved band it really is), the cup's wall likewise (a cone
# unrolls to an arc), and flat parts are projected. The regions are then packed
# into the 2048 px atlas at one density, the same across and down, so no motif
# is stretched; the layout goes to tools/draw_teacup_details_v2.py as JSON and
# the art is drawn to fit it.

ATLAS_GUTTER = 6               # px of background round each region (linear filtering stays clean)
ATLAS_MIN_DENSITY = 1000.0     # px per metre every visible surface gets at least
# regions that are seen close up (the face, the book, the brooch) get more
ATLAS_PRIORITY = {"sleeve_upper": 1.0, "sleeve_bell": 1.0, "sleeve_drape": 1.0, "cup": 1.2, "book_cover": 1.4, "page": 3.0, "brooch": 2.0, "collar": 1.05, "tabard": 1.1}


def outer_grid(mids, norms, th):
    """The cloth's outer surface (its front faces, where the art lies) as a grid:
    unrolled in place of the middle surface, so the art's size matches the faces
    it is drawn on even where the cloth curves tightly (a 43 mm sleeve's outside is
    5 % longer round than its middle)."""
    return [[p + n * th / 2 for p, n in zip(row, nrow)] for row, nrow in zip(mids, norms)]


def world_up(mids, flat):
    """At each grid point, the way world up (+Z) runs in the unrolled grid (a unit
    2D direction), so art on hanging cloth stands upright however it is unrolled."""
    rows, cols = len(mids), len(mids[0])
    out = []
    for j in range(rows):
        row = []
        for i in range(cols):
            ja, jb, ia, ib = max(j - 1, 0), min(j + 1, rows - 1), max(i - 1, 0), min(i + 1, cols - 1)
            du3, dv3 = mids[j][ib] - mids[j][ia], mids[jb][i] - mids[ja][i]
            du2 = Vector(flat[j][ib]) - Vector(flat[j][ia])
            dv2 = Vector(flat[jb][i]) - Vector(flat[ja][i])
            z = Vector((0, 0, 1))
            g11, g12, g22 = du3.dot(du3), du3.dot(dv3), dv3.dot(dv3)
            det = g11 * g22 - g12 * g12
            if det < 1e-14:
                row.append((0.0, -1.0))
                continue
            r1, r2 = z.dot(du3), z.dot(dv3)
            a, c = (r1 * g22 - r2 * g12) / det, (r2 * g11 - r1 * g12) / det
            up = du2 * a + dv2 * c
            row.append(tuple(up.normalized()) if up.length > 1e-9 else (0.0, -1.0))
        out.append(row)
    return out


def cell_stretch(mids, flat):
    """Per cell, the worst departure of its unrolled edges and diagonals from their
    true lengths (0.1 = 10 %), so the art keeps its motifs off stretched cloth."""
    out = []
    for j in range(len(mids) - 1):
        row = []
        for i in range(len(mids[0]) - 1):
            worst = 0.0
            for (a, b_), (c, d) in ((((j, i), (j, i + 1)), ((j + 1, i), (j + 1, i + 1))),
                                    (((j, i), (j + 1, i)), ((j, i + 1), (j + 1, i + 1))),
                                    (((j, i), (j + 1, i + 1)), ((j, i + 1), (j + 1, i)))):
                for (p, q) in ((a, b_), (c, d)):
                    true = (mids[p[0]][p[1]] - mids[q[0]][q[1]]).length
                    if true > 1e-5:
                        worst = max(worst, abs(math.dist(flat[p[0]][p[1]], flat[q[0]][q[1]]) / true - 1))
            row.append(round(worst, 3))
        out.append(row)
    return out


def flatten_grid(mids, iterations=500, no_fold=False):
    """Unroll a grid of 3D points (rows of columns) flat: start from arc lengths
    along the middle column and along each row, then relax every row, column and
    diagonal edge toward its true 3D length. Returns rows of (u, v) metres,
    turned so the middle column runs straight down (+v)."""
    rows, cols = len(mids), len(mids[0])
    c = cols // 2
    vs = [0.0]
    for j in range(1, rows):
        vs.append(vs[-1] + (mids[j][c] - mids[j - 1][c]).length)
    pos = []
    for j in range(rows):
        us = [0.0] * cols
        for i in range(c + 1, cols):
            us[i] = us[i - 1] + (mids[j][i] - mids[j][i - 1]).length
        for i in range(c - 1, -1, -1):
            us[i] = us[i + 1] - (mids[j][i + 1] - mids[j][i]).length
        pos.append([[us[i], vs[j]] for i in range(cols)])
    links = []
    for j in range(rows):
        for i in range(cols):
            for dj, di in ((0, 1), (1, 0), (1, 1), (1, -1)):
                jj, ii = j + dj, i + di
                if jj < rows and 0 <= ii < cols:
                    links.append((pos[j][i], pos[jj][ii], (mids[j][i] - mids[jj][ii]).length))
    # rows that lie almost on each other in 3D (a bell's squeezed rows, 1 mm apart)
    # fold over in the relaxation, mirroring the art across them: with no_fold,
    # after each pass every column link is kept running down the grid (across its
    # row) by at least half its true length, so no cell turns over
    col_links = [] if not no_fold else [(pos[j][i], pos[j + 1][i], pos[j][max(i - 1, 0)], pos[j][min(i + 1, cols - 1)],
                  .5 * (mids[j + 1][i] - mids[j][i]).length) for j in range(rows - 1) for i in range(cols)]
    for _ in range(iterations):
        for a, b, rest in links:
            dx, dy = b[0] - a[0], b[1] - a[1]
            d = math.hypot(dx, dy)
            if d < 1e-9:
                continue
            k = (d - rest) / d * 0.5
            a[0] += dx * k
            a[1] += dy * k
            b[0] -= dx * k
            b[1] -= dy * k
        for a, b, left, right, least in col_links:
            rx, ry = right[0] - left[0], right[1] - left[1]
            ln = math.hypot(rx, ry)
            if ln < 1e-9:
                continue
            nx, ny = -ry / ln, rx / ln               # down the grid (the start layout's +v side)
            down = (b[0] - a[0]) * nx + (b[1] - a[1]) * ny
            if down < least:
                k = (least - down) * .5
                a[0] -= nx * k
                a[1] -= ny * k
                b[0] += nx * k
                b[1] += ny * k
    (x0, y0), (x1, y1) = pos[0][c], pos[-1][c]
    ang = math.atan2(x1 - x0, y1 - y0)
    ca, sa = math.cos(ang), math.sin(ang)
    return [[(x * ca - y * sa, x * sa + y * ca) for x, y in row] for row in pos]


class Atlas:
    """Collects each region's corner UVs (in metres, unrolled) while the parts are
    built; finish() packs the regions, sets the UVs, writes the layout and has the
    art drawn for it."""

    def __init__(self):
        self.regions = {}     # name -> {"kind", "loops": [(loop, (u, v))], "guides": {}}

    def add(self, name, kind, loops, guides=None):
        r = self.regions.setdefault(name, {"kind": kind, "loops": [], "guides": {}})
        r["loops"] += loops
        r["guides"].update(guides or {})

    def grid(self, name, kind, mids, fronts, no_fold=False):
        """A cloth panel: its unrolled grid, each front face's corners matched to the
        nearest grid point of its cell."""
        flat = flatten_grid(mids, no_fold=no_fold)
        loops = []
        for (j, i), fs in fronts.items():
            corners = ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))
            for face in fs:
                free = list(corners)
                for loop in face.loops:
                    k = min(free, key=lambda q: (loop.vert.co - mids[q[0]][q[1]]).length_squared)
                    free.remove(k)
                    loops.append((loop, flat[k[0]][k[1]]))
        self.add(name, kind, loops, {"grid": flat, "up": world_up(mids, flat), "stretch": cell_stretch(mids, flat)})

    def grid_indexed(self, name, kind, mids, faces, index, wrap_cols=None):
        """Faces whose verts sit exactly on grid points, index: vert -> (j, i). With
        wrap_cols, the grid's last column repeats its first (a seam round a tube):
        a face across the seam takes the repeated column."""
        flat = flatten_grid(mids)
        loops = []
        for face in faces:
            ids = [index[loop.vert] for loop in face.loops]
            if wrap_cols and max(i for _, i in ids) - min(i for _, i in ids) > wrap_cols // 2:
                ids = [(j, i + wrap_cols if i < wrap_cols // 2 else i) for j, i in ids]
            loops += [(loop, flat[j][i]) for loop, (j, i) in zip(face.loops, ids)]
        self.add(name, kind, loops, {"grid": flat})

    def flat(self, name, kind, faces, uv_at, guides=None):
        """Flat faces projected: uv_at(co) gives (u, v) metres."""
        self.add(name, kind, [(loop, uv_at(loop.vert.co)) for f in faces for loop in f.loops], guides)

    # -- packing ----------------------------------------------------------------

    @staticmethod
    def _extent(r):
        pts = [uv for _, uv in r["loops"]] + [p for row in r["guides"].get("grid", ()) for p in row]
        us, vs = [p[0] for p in pts], [p[1] for p in pts]
        return min(us), min(vs), max(us), max(vs)

    def _pack(self, density):
        """MaxRects-pack every region at density (times its priority) into the
        atlas round the palette corner, best short side fit, turned a quarter
        when that fits better (the art follows each region's own grid, so it
        turns with it). Returns {name: (x, y, w, h, px per metre, turned)}, or
        None if they don't fit."""
        pal = toy3d.atlas_size(CHAR)[1]
        items = []
        for name, r in self.regions.items():
            u0, v0, u1, v1 = r["extent"]
            k = density * ATLAS_PRIORITY.get(name, ATLAS_PRIORITY.get(r["kind"], 1.0))
            items.append((name, math.ceil((u1 - u0) * k) + 2 * ATLAS_GUTTER,
                          math.ceil((v1 - v0) * k) + 2 * ATLAS_GUTTER, k, "grid" in r["guides"]))
        items.sort(key=lambda it: -it[1] * it[2])
        free = [(pal, 0, ATLAS_SIZE - pal, pal), (0, pal, ATLAS_SIZE, ATLAS_SIZE - pal)]
        placed = {}
        for name, w, h, k, can_turn in items:      # flat parts' art is drawn upright: they never turn
            best = None
            for fx, fy, fw, fh in free:
                for ww, hh, turned in ((w, h, False), (h, w, True))[:2 if can_turn else 1]:
                    if ww <= fw and hh <= fh:
                        score = (min(fw - ww, fh - hh), max(fw - ww, fh - hh))
                        if best is None or score < best[0]:
                            best = (score, fx, fy, ww, hh, turned)
            if best is None:
                return None
            _, x, y, ww, hh, turned = best
            placed[name] = (x, y, ww, hh, k, turned)
            nxt = []
            for fx, fy, fw, fh in free:     # split every free rect the new one overlaps
                if x >= fx + fw or x + ww <= fx or y >= fy + fh or y + hh <= fy:
                    nxt.append((fx, fy, fw, fh))
                    continue
                if x > fx:
                    nxt.append((fx, fy, x - fx, fh))
                if x + ww < fx + fw:
                    nxt.append((x + ww, fy, fx + fw - x - ww, fh))
                if y > fy:
                    nxt.append((fx, fy, fw, y - fy))
                if y + hh < fy + fh:
                    nxt.append((fx, y + hh, fw, fy + fh - y - hh))
            free = [a for a in nxt if not any(a != c and c[0] <= a[0] and c[1] <= a[1] and
                                              a[0] + a[2] <= c[0] + c[2] and a[1] + a[3] <= c[1] + c[3]
                                              for c in nxt)]
        return placed

    def finish(self, b):
        for name, r in self.regions.items():
            r["extent"] = u0, v0, u1, v1 = self._extent(r)
            print(f"atlas region {name}: {u1 - u0:.3f} x {v1 - v0:.3f} m")
        density, placed = 2000.0, None
        while placed is None:
            density -= 10.0
            placed = self._pack(density)
        assert density >= ATLAS_MIN_DENSITY, f"the atlas only fits at {density} px/m"
        layout = {"size": ATLAS_SIZE, "palette_px": toy3d.atlas_size(CHAR)[1], "density": density,
                  "regions": {}}
        for name, r in self.regions.items():
            x, y, w, h, k, turned = placed[name]
            u0, v0, u1, _ = r["extent"]

            def px(p, x=x, y=y, k=k, turned=turned, u0=u0, v0=v0, u1=u1):
                if turned:                 # a quarter turn: u runs down the box, v across it (mirrored back)
                    return [round(x + ATLAS_GUTTER + (p[1] - v0) * k, 2),
                            round(y + ATLAS_GUTTER + (u1 - p[0]) * k, 2)]
                return [round(x + ATLAS_GUTTER + (p[0] - u0) * k, 2), round(y + ATLAS_GUTTER + (p[1] - v0) * k, 2)]
            for loop, uv in r["loops"]:
                loop[b.uv].uv = detail_uv(*px(uv))
            out = {"kind": r["kind"], "box": [x, y, x + w, y + h], "density": k}
            for key, g in r["guides"].items():
                if key == "grid":
                    out[key] = [[px(p) for p in row] for row in g]
                elif key == "up":          # directions: turned with the region, not moved
                    out[key] = [[[round(d[1], 4), round(-d[0], 4)] if turned else [round(d[0], 4), round(d[1], 4)]
                                 for d in row] for row in g]
                elif key == "radius":
                    out[key] = g * k
                elif key == "stretch":     # per cell, unitless
                    out[key] = g
                else:                      # rectangles [u0, v0, u1, v1] in metres
                    out[key] = []
                    for q in g:
                        (ax, ay), (bx, by) = px(q[:2]), px(q[2:])
                        out[key].append([min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)])
            out["turned"] = turned
            layout["regions"][name] = out
        os.makedirs(V2_DIR, exist_ok=True)
        with open(LAYOUT, "w", encoding="utf-8") as f:
            json.dump(layout, f, indent=1)
        subprocess.run([ATLAS_PYTHON, DRAW_SCRIPT, LAYOUT, DETAIL], check=True)
        b.atlas_layout = layout
        return layout


def atlas_density(obj):
    """Measured atlas px per metre of each region, across (u) and down (v): the
    median over its faces' edges of UV length / true length, split by which way
    each edge runs in the atlas."""
    import statistics
    with open(LAYOUT, encoding="utf-8") as f:
        boxes = {n: r["box"] for n, r in json.load(f)["regions"].items()}
    me = obj.data
    uv = me.uv_layers["UVMap"].data
    out = {}
    for poly in me.polygons:
        idx = list(poly.loop_indices)
        cx = sum(uv[i].uv.x for i in idx) / len(idx) * ATLAS_SIZE
        cy = (1 - sum(uv[i].uv.y for i in idx) / len(idx)) * ATLAS_SIZE
        name = next((n for n, (x0, y0, x1, y1) in boxes.items() if x0 <= cx < x1 and y0 <= cy < y1), None)
        if name is None:
            continue
        for a, c in zip(idx, idx[1:] + idx[:1]):
            d3 = (me.vertices[me.loops[a].vertex_index].co - me.vertices[me.loops[c].vertex_index].co).length
            du, dv = (uv[c].uv.x - uv[a].uv.x) * ATLAS_SIZE, (uv[c].uv.y - uv[a].uv.y) * ATLAS_SIZE
            if d3 < 1e-4 or math.hypot(du, dv) < 1e-3:
                continue
            out.setdefault(name, ([], []))[0 if abs(du) > abs(dv) else 1].append(math.hypot(du, dv) / d3)
    return {n: (round(statistics.median(a)) if a else None, round(statistics.median(c)) if c else None)
            for n, (a, c) in sorted(out.items())}


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

HEAD_H = 20.5 * S
# the saucer collar, and the shallow well in its middle the cup's foot stands in:
# the well floor is SAUCER_WELL above the saucer's middle, WELL_DEPTH below the
# plate round it, and the foot rests on it (0.3 mm clear, so it touches without
# the two surfaces lying on each other)
SAUCER_C = P(CX, 40.5)
SAUCER_WELL, WELL_DEPTH, WELL_R = .0075, .0018, .066
HEAD_C = Vector((P(CX, 27).x, P(CX, 27).y, SAUCER_C.z + SAUCER_WELL + .0003 + HEAD_H * .5))
CUP_SY = 1.0
# The tea: a disc of concentric rings on its own bone ("tea", a child of the head)
# TEA_DROP below the porcelain rim, tagged UV2.y = 3 (UV2.x its radius) for the
# game's unit shader, which heaves it in waves as it sloshes (the game also tips it
# about in the cup, UnitTea and TeaLevel).
# settle() keeps it level with the world, but never further off the cup's own
# tilt than TEA_MAX_TILT, where its high edge would reach TEA_FREEBOARD under the rim.
TEA_DROP = .012
TEA_Z = HEAD_C.z + HEAD_H * .5 - TEA_DROP
TEA_R = .126               # the bowl is 13.2 cm wide there: room to tilt without touching it
TEA_FREEBOARD = .003
TEA_MAX_TILT = math.degrees(math.asin((TEA_DROP - TEA_FREEBOARD) / TEA_R))
TEA_LOWEST = -.016         # m the tea may be lowered: its plug then just stays inside the cup's bottom
# the surface (radius, height off the tea level): flat, with a little meniscus at the
# edge, in rings close enough for the game's waves to bend it (the owner had the
# old stylised crest ring taken out, 2026-10-11)
TEA_WAVE = ((0.0, .0003), (.024, .0003), (.046, .0003), (.067, .0003), (.081, .0003),
            (.100, .0003), (.114, .0004), (TEA_R, .0010))


def capsule_outline(rx, rz, n=16):
    """A flat rounded eye/card outline in local X/Z coordinates."""
    return [(rx * math.copysign(abs(math.cos(a)) ** .72, math.cos(a)),
             rz * math.copysign(abs(math.sin(a)) ** .72, math.sin(a)))
            for a in (2 * math.pi * k / n for k in range(n))]


def build_tea(b, c, h):
    """The tea's surface: a closed, flat disc of concentric rings on the tea bone
    (UV2.y = 3), held up by a hidden plug from the bowl's floor on the head."""
    top = [(r, z) for r, z in TEA_WAVE]
    # (thick enough underneath, bevelled in, that the plug's outline stays inside it)
    prof = [(0.0, -.009), (TEA_R - .010, -.009)] + [(TEA_R, -.002)] + top[::-1]
    verts, _, _ = b.lathe(prof, 32, Matrix.Translation(Vector((c.x, c.y, TEA_Z))), sy=CUP_SY)
    faces = b.finish(verts, "brown_dark", "tea", smooth=False)
    # UV2.y = 3 marks the tea for the game's shader; UV2.x is how far out from the
    # middle each point is (0 middle, 1 edge), so its waves can run outward over it
    for f in faces:
        for loop in f.loops:
            co = loop.vert.co
            loop[b.sway].uv = (min(1.0, math.hypot(co.x - c.x, co.y - c.y) / TEA_R), 3.0)
    b.joints["tea"] = (Vector((c.x, c.y, TEA_Z)), Vector((c.x, c.y, TEA_Z + .04)), "head")
    # the hidden plug reaches the inner bowl's floor, keeping the tea attached; it is
    # on the tea's bone, so it drains away with it, and sinks into the cup's 18 mm
    # thick bottom when the tea is lowered (TEA_LOWEST)
    b.finish(b.tube([Vector((c.x, c.y, TEA_Z - .007)), Vector((c.x, c.y, c.z - h * .39))], .012, 8),
             "brown_dark", "tea")


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
    verts, bands, rings = b.lathe(prof, 32, Matrix.Translation(c), sy=CUP_SY)
    faces = b.finish(verts, "ivory", "head")
    b.paint(bands[0] + bands[1], "gold")
    # (the inner wall stays porcelain all the way down: the tea is lowered, and in
    # broken poured out, so the bowl shows; the gap round the disc reads as a rim)
    # the decorated wall (profile points 3..5) unrolled: rows from the rim down,
    # columns round from straight behind (ring index 8, +Y), so the front is the
    # middle column and the seam is at the back
    wall = [rings[5], rings[4], rings[3]]
    index = {v: (j, (i - 8) % 32) for j, ring in enumerate(wall) for i, v in enumerate(ring)}
    mids = [[ring[(i + 8) % 32].co.copy() for i in range(33)] for ring in wall]
    b.atlas.grid_indexed("cup", "cup", mids, bands[3] + bands[4], index, wrap_cols=32)

    # The lip is structural and restrained; its blue/gold decoration is atlas art.
    for z, rin, rout, th, colour in ((h * .48, .132, .160, .010, "ivory"),
                                      (h * .52, .145, .159, .006, "gold")):
        lip, _, _ = b.lathe([(rout, -th/2), (rout, th/2),
                             (rin, th/2), (rin, -th/2)], 32,
                            Matrix.Translation(c + Vector((0, 0, z))),
                            sy=CUP_SY, loop=True)
        b.finish(lip, colour, "head", smooth=False)

    build_tea(b, c, h)

    # Exterior cubic handle.  The endpoints follow the changing cup radius;
    # their short mounts enter only the porcelain wall, never the inner bowl.
    def wall(z, side):
        """The cup's outer (side 0) or inner (side 1) wall radius at height z off its middle."""
        pts = sorted((pz, r) for r, pz in (prof[2:7] if side == 0 else prof[7:12]))
        return interp(pts, z)
    top_z, bot_z = .055, -.055
    p0 = c + Vector((wall(top_z, 0) - .0015, .002, top_z))
    p1 = c + Vector((.238, .002, .058))
    p2 = c + Vector((.235, .002, -.055))
    p3 = c + Vector((wall(bot_z, 0) - .0015, .002, bot_z))
    pts = []
    for k in range(21):
        t = k / 20
        u = 1.0 - t
        pts.append(p0 * (u ** 3) + p1 * (3 * u * u * t)
                   + p2 * (3 * u * t * t) + p3 * (t ** 3))
    b.finish(b.tube(pts, .015, 10, rs=[.014, .015] + [.016] * 17 + [.015, .014]),
             "ivory", "head")
    # each mount: a short collar from 1.5 mm inside the wall (never reaching the
    # inner bowl) out along the handle
    for p, z in ((p0, top_z), (p3, bot_z)):
        assert c.x + wall(z, 1) < p.x - .002, "a handle mount reaches the inner bowl"
        b.finish(b.tube([p, p + Vector((.012, 0, 0))], .0135, 10), "ivory", "head")

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

TORSO_PROF = [(0, 91), (13, 91), (14.5, 80), (15.5, 68), (15, 57),
              (14, 51), (12, 46), (7, 44), (0, 44)]   # narrow shoulders: the sleeves start just outside them
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

    b.atlas.grid("robe", "robe", outer_grid(mids, norms, .70 * S), fronts)
    b.set_sway(faces, H(BELT_BOTTOM), H(ROBE_HEM))
    body_and_skirt(b, verts, ROBE_HEM, (.0, .38, .78), .46)
    return verts


BELT_BLEND = 4.0           # px above and below the belt the body's weights blend into the skirt's
# The skirts hang on a ring of short chains from the belt (skirt_<side>_1, _2; the
# side by its angle round her, 0 = her left, -90 = the front opening), so each part
# of the hem can swing on its own under Godot's spring bones; in the clips they stay
# at rest on the hips. The three robe layers below the belt share them.
SKIRT_CHAINS = {"FL": -60.0, "L": 0.0, "BL": 60.0, "BR": 120.0, "R": 180.0, "FR": -120.0}
SKIRT_SPACING = 60.0       # degrees between neighbouring chains: a point blends between the two either side
SKIRT_HEM = 108.0          # py the chains reach down to (the longest layer's hem)


def skirt_joints(b):
    """The skirt chains' bones, from the belt down the outer coat to the hem."""
    centre = P(CX, GROUND)
    top, hem, flare, narrow = OUTER_COAT
    for side, deg in SKIRT_CHAINS.items():
        a = math.radians(deg)
        pts = [ring_pt(centre, layer_radius(py, a, top, hem, flare, narrow), a, robe_sy(py), py)
               for py in (BELT_BOTTOM, (BELT_BOTTOM + SKIRT_HEM) / 2, SKIRT_HEM)]
        b.joints[f"skirt_{side}_1"] = (pts[0], pts[1], "hips")
        b.joints[f"skirt_{side}_2"] = (pts[1], pts[2], f"skirt_{side}_1")


def round_weights(a, chains, spacing):
    """{name: weight} of the chains either side of angle a (radians), linear between
    them; beyond the last chain of an open set (the cape's edges past its side
    columns), wholly the nearest one."""
    out, dist = {}, {}
    for name, deg in chains.items():
        d = abs((a - math.radians(deg) + math.pi) % (2 * math.pi) - math.pi)
        dist[name] = d
        w = 1.0 - d / math.radians(spacing)
        if w > 0:
            out[name] = w
    if not out:
        return {min(dist, key=dist.get): 1.0}
    total = sum(out.values())
    return {k: w / total for k, w in out.items()}


def body_and_skirt(b, verts, hem_py, centres, spread):
    """Skin a garment: above the belt it follows the body (hips, spine, chest, as
    the torso and tabard do, so the tabard and brooch stay on it as she leans and
    twists); below the belt it hangs on the ring of skirt chains, down their length
    by centres (the fractions of the way from the belt to the hem where the hips,
    link 1 and link 2 peak) and round her between the two nearest chains; blended
    across the belt, so no kink."""
    if "skirt_L_1" not in b.joints:
        skirt_joints(b)
    top_z, length = H(BELT_BOTTOM), H(BELT_BOTTOM) - H(hem_py)
    hi, lo = H(BELT_TOP - BELT_BLEND), H(BELT_BOTTOM + BELT_BLEND)
    for v in verts:
        k = smoothstep((v.co.z - lo) / (hi - lo))
        ws = {}
        if k < 1.0:
            t = (top_z - v.co.z) / length
            down = [max(0.0, 1.0 - abs(t - c) / spread) for c in centres]
            if sum(down) <= 0:
                down = [0.0, 0.0, 1.0]
            total = sum(down)
            ws[b.bone_index("hips")] = (1.0 - k) * down[0] / total
            for side, w in round_weights(ellipse_coords(v.co, robe_sy(GROUND - v.co.z / S))[1], SKIRT_CHAINS,
                                         SKIRT_SPACING).items():
                for j in (1, 2):
                    i = b.bone_index(f"skirt_{side}_{j}")
                    ws[i] = ws.get(i, 0.0) + (1.0 - k) * w * down[j] / total
        if k > 0.0:
            for name, w in body_weights(v.co.z):
                i = b.bone_index(name)
                ws[i] = ws.get(i, 0.0) + w * k
        dv = v[b.deform]
        dv.clear()
        for i, w in ws.items():
            if w > 1e-4:
                dv[i] = w


def layer_radius(py, a, top_py, hem_py, radial_px, side_narrow=0.0, q=None):
    """A robe shell's mid-surface radius (px) at row py and angle a: the robe's
    radius plus the layer's flare (radial_px, (top, hem) px, eased in over its top
    40 %; side_narrow of the flare taken off at the sides) and its folds."""
    t = max(0.0, min(1.0, (py - top_py) / (hem_py - top_py)))
    if isinstance(radial_px, tuple):
        radial = radial_px[0] + (radial_px[1] - radial_px[0]) * smoothstep(t / .40)
        rad = radial_px[0] + (radial - radial_px[0]) * (1 - side_narrow * math.cos(a) ** 2)
    else:
        rad = radial_px
    fold = (1.0 + .8 * t) * math.sin(6 * a + .4) * t
    return robe_r(py if q is None else q) + rad + fold


def build_wrap_layer(b, part, colour, lining, top_py, hem_py, radial_px,
                     opening_top, opening_hem, detail=None, rows=14, cols=34, side_narrow=0.0):
    """Build one closed, open-front garment that remains continuous round the back;
    detail names the atlas art drawn on it ("coat", "mid"); side_narrow takes that
    share of its flare off at the sides (the sleeves' drapes carry the silhouette)."""
    centre = P(CX, GROUND)
    mids = []
    for j in range(rows):
        t = j / (rows - 1)
        py = top_py + (hem_py - top_py) * t
        half = math.radians(opening_top + (opening_hem - opening_top) * smoothstep(t))
        row = []
        for i in range(cols + 1):
            a = -math.pi / 2 + half + (2 * math.pi - 2 * half) * i / cols
            hem = 2.6 * (math.sin(i * 1.37) ** 2) * smoothstep((t - .84) / .16)
            q = py + hem
            r = layer_radius(py, a, top_py, hem_py, radial_px, side_narrow, q)
            row.append(ring_pt(centre, r, a, robe_sy(q), q))
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre, .76))
    verts, fronts, backs = cloth(b, mids, norms, .72 * S)
    faces = b.finish(verts, colour, part, smooth=False)
    b.paint(list(backs.values()), lining)
    if detail:
        b.atlas.grid(part, detail, outer_grid(mids, norms, .72 * S), fronts)
    b.set_sway(faces, H(BELT_BOTTOM), H(hem_py))
    body_and_skirt(b, verts, hem_py, (-.05, .40, .82), .48)
    return verts


MID_ROBE = (42.0, 110.0, (-1.2, 4.8), .1)          # top, hem py, flare px, side narrowing
OUTER_COAT = (42.0, 104.5, (1.8, 8.0), .35)


def build_coat_layers(b):
    """Two genuine robe shells: blue mid-layer and porcelain outer coat."""
    top, hem, flare, narrow = MID_ROBE
    mid = build_wrap_layer(b, "mid_robe", "blue", "blue_dark", top, hem, flare, 12.0, 38.0, "mid",
                           rows=16, cols=28, side_narrow=narrow)
    top, hem, flare, narrow = OUTER_COAT
    outer = build_wrap_layer(b, "outer_robe", "ivory", "cream_shade", top, hem, flare, 17.0, 47.0, "coat",
                             rows=16, cols=30, side_narrow=narrow)
    return mid, outer


def tabard_radial(py):
    """Place the tabard midway between the blue and porcelain robe shells."""
    mid_t = (py - 42.0) / (110.0 - 42.0)
    outer_t = (py - 42.0) / (104.5 - 42.0)
    mid = -1.2 + (4.8 - -1.2) * smoothstep(mid_t / .40)
    outer = 1.8 + (8.0 - 1.8) * smoothstep(outer_t / .40)
    return (mid + outer) * .5


TABARD_TOP = 50.0                          # py of its top edge, where the brooch's rings hold it


def tabard_point(px, py):
    """A point on the tabard's middle surface at sprite column px, row py."""
    p, _ = body_pt(px, py, robe_r(py) + tabard_radial(py), robe_sy(py))
    p.y -= .004
    return p


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
    faces = b.finish(verts, "blue", "cape", smooth=False)
    b.paint(list(backs.values()), "blue_dark")
    # only its hem rows go in the atlas (the gold hem); the rest is the plain blue swatch
    sleeve_panel(b, "cape", "cape", outer_grid(mids, norms, 1.0 * S), fronts, range(rows - 3, rows),
                 list(range(cols + 1)))
    b.set_sway(faces, H(top_py), H(hem_py))
    # three columns of links down it (cape_L_*, cape_*, cape_R_*: left, middle,
    # right across her back), so its sides can swing apart under Godot's spring
    # bones; each point blends down its length and across between the columns
    for col, prefix in ((round(cols * .2), "cape_L_"), (cols // 2, "cape_"), (round(cols * .8), "cape_R_")):
        js = [mids[round(k * (rows - 1) / 3)][col] for k in range(4)]
        for i in range(3):
            b.joints[f"{prefix}{i + 1}"] = (js[i], js[i + 1], "chest" if i == 0 else f"{prefix}{i}")
    across = {"L": math.degrees(CAPE_COLUMN_A[0]), "": 90.0, "R": math.degrees(CAPE_COLUMN_A[1])}
    spacing = across[""] - across["L"]
    for v in verts:
        t = (H(top_py) - v.co.z) / (H(top_py) - H(hem_py))
        down = [max(0.0, 1.0 - abs(t - c) / .36) for c in (-.08, .18, .54, .90)]
        if sum(down) <= 0:
            down = [0.0, 0.0, 0.0, 1.0]
        total = sum(down)
        a = ellipse_coords(v.co, .92)[1]
        cols_w = round_weights(a, across, spacing)
        dv = v[b.deform]
        dv.clear()
        dv[b.bone_index("chest")] = down[0] / total
        for side, w in cols_w.items():
            prefix = f"cape_{side}_" if side else "cape_"
            for i in (1, 2, 3):
                if down[i] * w > 1e-4:
                    dv[b.bone_index(f"{prefix}{i}")] = down[i] * w / total
    return verts


CAPE_COLUMN_A = (math.radians(22 + (158 - 22) * .2), math.radians(22 + (158 - 22) * .8))   # the side columns' angles at the top


MANTLE_TOP, MANTLE_HEM = 42.0, 59.0
MANTLE_DRAPE_BAND = .025  # m over which the mantle eases from lifted back to its own shape
MANTLE_OVER_ARM = .066     # m round each upper arm's axis the mantle is lifted clear of the sleeve


def drape_over_arms(p, segments=None, R=None):
    """A mantle point lifted out over an arm segment and its sleeve under it, as
    cloth drapes over a raised arm: moved out from the segment's axis to R (default
    MANTLE_OVER_ARM round the upper arms), never in toward the body (a point on
    the body's side of the arm moves up or down instead)."""
    band = MANTLE_DRAPE_BAND
    R = R or MANTLE_OVER_ARM
    if segments is None:
        segments = [(sh, el + (el - sh).normalized() * .07) for sh, el, _ in (ARM_R, ARM_L)]
    for sh, end in segments:
        ab = end - sh
        u = ab.normalized()
        t = max(0.0, min(1.0, (p - sh).dot(ab) / ab.length_squared))
        q = sh + ab * t
        off = p - q
        r = (off - u * off.dot(u)).length
        if r >= R + band:
            continue
        out = off - u * off.dot(u)
        body_out = Vector((p.x - P(CX, 0).x, p.y, 0)).normalized()
        if out.length < 1e-6 or Vector((out.x, out.y, 0)).dot(body_out) < 0:
            vert = Vector((0, 0, 1 if off.z >= 0 else -1))
            out = vert - u * vert.dot(u)          # up or down, square to the sloping arm
        # a smooth maximum: lifted to R inside, eased back to the cloth's own
        # place over the band outside, so it drapes rather than kinks
        r2 = R if r <= R - band else R + (r - R + band) ** 2 / (4 * band)
        p = q + out.normalized() * max(r, r2) + u * off.dot(u)
    return p


MANTLE_LIFTS_OVER_FOREARMS = False   # (tried: catches the rows by the elbow too; the elbows sit lower instead)
MANTLE_OVER_FOREARM = .070  # m round each forearm's axis the mantle's hem lifts clear of the bell


def lift_over_forearms(p):
    """The mantle's hem lifted where a raised forearm passes close under it (the
    forearm rising out from under the hem, its bell round it), rather than the bell
    squeezed in under the hem."""
    segs = [(el - (wr - el).normalized() * .02, wr) for _, el, wr in (ARM_R, ARM_L)]
    return drape_over_arms(p, segs, MANTLE_OVER_FOREARM)


def build_mantle(b):
    """A thick shoulder capelet with fitted arm gaps and a scalloped lower edge."""
    rows, cols = (14, 68) if MANTLE_DRAPES_OVER_ARMS or MANTLE_LIFTS_OVER_FOREARMS else (7, 34)
    top_py, hem_py = MANTLE_TOP, MANTLE_HEM
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
            p = ring_pt(centre, 17.0 + 12.0 * t, a, .74, py + scallop - mantle_arm_lift(a) * t)
            p = drape_over_arms(p) if MANTLE_DRAPES_OVER_ARMS else p
            row.append(lift_over_forearms(p) if MANTLE_LIFTS_OVER_FOREARMS else p)
        mids.append(row)
    norms = grid_normals(mids, outward=outward_from(centre, .74))
    verts, fronts, backs = cloth(b, mids, norms, .95 * S)
    faces = b.finish(verts, "ivory", "mantle", smooth=False)
    b.paint(list(backs.values()), "blue_dark")

    b.atlas.grid("mantle", "mantle", outer_grid(mids, norms, .95 * S), fronts)
    b.mantle_verts = verts

    return verts


# Short edge bones on the mantle's lower half, front and back between the arms
# (mantle_FL, mantle_FR, mantle_BL, mantle_BR), so its scalloped hem can lift and
# flutter under Godot's spring bones; over the arms it follows the upper arms.
MANTLE_EDGES = {"FL": -55.0, "FR": -125.0, "BL": 55.0, "BR": 125.0}
MANTLE_EDGE_SPREAD = 40.0   # degrees either side of an edge bone it still pulls the hem


def mantle_edges(b, verts):
    centre = P(CX, GROUND)
    mid_py = (MANTLE_TOP + MANTLE_HEM) / 2
    for side, deg in MANTLE_EDGES.items():
        a = math.radians(deg)
        p0 = ring_pt(centre, 17.0 + 12.0 * .5, a, .74, mid_py)
        p1 = ring_pt(centre, 17.0 + 12.0, a, .74, MANTLE_HEM)
        b.joints[f"mantle_{side}"] = (p0, p1, "chest")
    for v in verts:
        py = GROUND - v.co.z / S
        down = smoothstep((py - mid_py) / (MANTLE_HEM - mid_py))
        if down <= 0.0:
            continue
        a = ellipse_coords(v.co, .74)[1]
        for side, deg in MANTLE_EDGES.items():
            d = (a - math.radians(deg) + math.pi) % (2 * math.pi) - math.pi
            w = down * max(0.0, 1.0 - abs(d) / math.radians(MANTLE_EDGE_SPREAD))
            if w <= 0.0:
                continue
            # (it takes only the chest's share: the share following the upper arms
            # stays, so the mantle still lifts clear of a raised sleeve)
            dv = v[b.deform]
            chest = b.bone_index("chest")
            moved = dv.get(chest, 0.0) * w
            if moved > 0.0:
                dv[chest] -= moved
                i = b.bone_index(f"mantle_{side}")
                dv[i] = dv.get(i, 0.0) + moved


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
        chest = b.bone_index("chest")
        arms = {b.bone_index("upperarm_R"), b.bone_index("upperarm_L")}
        for i, w in near.items():
            i = chest if i in arms else i        # the cape hangs behind the arms: it stays on the chest
            dv[i] = dv.get(i, 0.0) + k * w


def build_saucer_collar(b):
    """A shallow porcelain saucer collar: its middle closes on the neck, a shallow
    well there holds the cup's foot, and from the well out its face rises a little
    to the rim, as a real saucer flares (the owner's reference); its underside
    stays low over the mantle it rests on and rises under the rim."""
    c = SAUCER_C
    neck_r = .039                          # just inside the neck's surface at this height
    w, d = SAUCER_WELL, WELL_DEPTH
    prof = [(neck_r, w), (WELL_R, w), (WELL_R + .002, w + d), (.075, w + d + .0003),
            (.110, .0112), (.132, .0135), (.151, .0165), (.151, .0115), (.138, .0045), (.122, -.008),
            (.100, -.0105), (.055, -.011), (neck_r, -.011)]     # (the underside stays low over the mantle it rests on)
    verts, _, _ = b.lathe(prof, 32, Matrix.Translation(c), sy=1.0, loop=True)
    faces = b.finish(verts, "ivory", "collar", smooth=False)
    b.atlas.flat("collar", "collar", [f for f in faces if f.normal.z > .35],
                 lambda co: (co.x - c.x, co.y - c.y), {"radius": .151})
    b.finish(b.ring(c + Vector((0, 0, .014)), (0, 0, 1), .143, .153, .006, 32),     # the gold rim
             "gold", "collar", smooth=False)


BROOCH_R = .036                            # the quatrefoil's outer radius


def quatrefoil(r, n=48):
    """Outline of four round lobes (centres 0.48 r out on the axes, radius 0.52 r):
    for each direction, the farthest lobe edge along it."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        d = Vector((math.cos(a), math.sin(a)))
        far = 0.0
        for q in range(4):
            cc = Vector((math.cos(q * math.pi / 2), math.sin(q * math.pi / 2))) * .48 * r
            dc = d.dot(cc)
            disc = dc * dc - cc.length_squared + (.52 * r) ** 2
            if disc >= 0:
                far = max(far, dc + math.sqrt(disc))
        pts.append((d.x * far, d.y * far))
    return pts


def torus(b, c, axis, R, r, segs=12, tube=6):
    prof = [(R + r * math.cos(2 * math.pi * k / tube), r * math.sin(2 * math.pi * k / tube)) for k in range(tube)]
    return b.lathe(prof, segs, frame(c, axis), loop=True)[0]


def build_brooch(b):
    """The concept's gold quatrefoil brooch at the throat, just under the saucer.
    The tabard hangs from it on two gold rings looped through its top edge, and a
    short gold pin behind it is sunk into the torso, so it is held to the body."""
    s = BROOCH_R
    top = SAUCER_C.z - .0105 - .001               # 1 mm under the saucer's underside
    zb = top - s
    # each ring faces the front, tipped back 30 degrees: its top is 1 mm up inside a
    # side lobe, its bottom loops back through the tabard's top edge
    ring_x, ring_R, ring_r, tip = .65 * s, .009, .002, math.radians(30)
    up = Vector((0, -math.sin(tip), math.cos(tip)))
    ring_z = zb - .49 * s + .0010 - ring_R * up.z - ring_r
    # the tabard's front surface down its middle, over the brooch's height
    zlo, front = zb - s - .002, 0.0
    for p0, p1 in zip(b.tabard_front, b.tabard_front[1:]):
        if p1.z < zlo:
            p1 = p0.lerp(p1, (p0.z - zlo) / (p0.z - p1.z))
        front = min(front, p0.y, p1.y)
        if p1.z <= zlo + 1e-9:
            break
    yb = front - .0005 - .003                     # its back 0.5 mm clear of the tabard's front
    centre = Vector((HEAD_C.x, yb, zb))
    b.brooch_centre = centre
    faces = b.finish(b.slab(quatrefoil(s), .006, frame(centre, (0, -1, 0), (1, 0, 0))),
                     "gold", "brooch", smooth=False)
    b.atlas.flat("brooch", "brooch", [f for f in faces if f.normal.y < -.7],
                 lambda co: (co.x - centre.x, centre.z - co.z), {"radius": s})
    torso_y = -TORSO_SY * torso_r(GROUND - zb / S) * S
    b.finish(b.tube([centre + Vector((0, .002, 0)), Vector((centre.x, torso_y + .003, zb))], .004, 8),
             "gold", "brooch", smooth=False)
    for sx in (-1, 1):
        rc = Vector((centre.x + sx * ring_x, yb - up.y * ring_R, ring_z))
        b.finish(torus(b, rc, Vector((1, 0, 0)).cross(up), ring_R, ring_r, 14), "gold", "brooch_ring")
    return ring_z


def build_belt_and_tabard(b):
    belt, _, _ = b.lathe([(17.0 * S, H(BELT_BOTTOM)), (17.3 * S, H(BELT_BOTTOM)),
                          (17.3 * S, H(BELT_TOP)), (17.0 * S, H(BELT_TOP))],
                         28, Matrix.Identity(4), sy=.72, loop=True)
    b.finish(belt, "brown_dark", "belt", smooth=False)
    buckle = P(CX, 69, -12.7 * S)
    b.finish(b.box(buckle, (.056, .018, .046)), "gold", "belt", smooth=False)
    b.finish(b.box(buckle - Vector((0, .011, 0)), (.032, .006, .023)), "brown_dark", "belt", smooth=False)

    rows, cols = 15, 6
    top_py, hem_py = TABARD_TOP, 103.0
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
            row.append(tabard_point(CX + (2 * u - 1) * half, q))
        mids.append(row)
    norms = grid_normals(mids, outward=lambda p: Vector((0, -1, 0)))
    verts, fronts, backs = cloth(b, mids, norms, .65 * S)
    b.tabard_front = [row[cols // 2] + n[cols // 2] * .65 * S / 2 for row, n in zip(mids, norms)]
    # tassels hang from its side corners (where the point begins) and its point
    jc = next(j for j in range(rows) if j / (rows - 1) >= .78)
    b.tabard_tassel_points = [mids[jc][0], mids[jc][cols], mids[-1][cols // 2]]
    faces = b.finish(verts, "blue", "tabard", smooth=False)
    b.paint(list(backs.values()), "blue_dark")
    b.atlas.grid("tabard", "tabard", outer_grid(mids, norms, .65 * S), fronts)
    b.set_sway(faces, H(BELT_BOTTOM), H(hem_py))
    # its top hangs from the brooch's rings on the chest
    chest = b.bone_index("chest")
    for v in verts:
        k = smoothstep((v.co.z - H(TABARD_TOP + 8)) / (H(TABARD_TOP) - H(TABARD_TOP + 8)))
        if k > 0:
            dv = v[b.deform]
            for i in list(dv.keys()):
                dv[i] *= 1 - k
            dv[chest] = dv.get(chest, 0.0) + k


# -- gear: the brooch's cords and the tassels ---------------------------------------

def ellipse_reach(R_px, sy, phi):
    """How far (m) along plan direction phi an ellipse of radius R px (depth scale
    sy) round the body's axis reaches."""
    c, s = math.cos(phi), math.sin(phi)
    return R_px * S / math.sqrt(c * c + (s / sy) ** 2)


def front_gap(phi, half_deg):
    """Is plan direction phi inside a garment's front opening (half_deg either side
    of straight ahead, -90 degrees)?"""
    d = (phi + math.pi / 2 + math.pi) % (2 * math.pi) - math.pi
    return abs(d) < math.radians(half_deg)


SURFACE = {}       # "tree": a BVH of everything built so far, which gear lies on


def outer_surface(py, phi):
    """The outermost surface (m from the body's axis) at row py in plan direction
    phi: a ray cast in from outside at the model built so far (every layer of
    cloth, the brooch, the cords), so gear lies exactly on what is there."""
    tree = SURFACE.get("tree")
    if tree is not None:
        c = P(CX, py)
        d = Vector((math.cos(phi), math.sin(phi), 0))
        hit = tree.ray_cast(Vector((c.x, c.y, c.z)) + d * .8, -d, .8)
        if hit[0] is not None:
            return (hit[0] - Vector((c.x, c.y, c.z))).length
    best = ellipse_reach(torso_r(py), TORSO_SY, phi)
    t_m = (py - MANTLE_TOP) / (MANTLE_HEM - MANTLE_TOP)
    if 0 <= t_m and py <= mantle_radius(py, phi)[1] and not front_gap(phi, 20 + 8 * min(1, t_m)):
        best = max(best, ellipse_reach(mantle_radius(py, phi)[0], .74, phi) + .95 * S / 2)
    for (top, hem, flare, narrow), (o0, o1) in ((OUTER_COAT, (17.0, 47.0)), (MID_ROBE, (12.0, 38.0))):
        t = (py - top) / (hem - top)
        if 0 <= t <= 1 and not front_gap(phi, o0 + (o1 - o0) * smoothstep(t)):
            a = phi       # (near enough: the layer's angle parameter and the plan angle agree on the sides)
            best = max(best, ellipse_reach(layer_radius(py, a, top, hem, flare, narrow), robe_sy(py), phi)
                       + .72 * S / 2)
    if ROBE_TOP <= py <= ROBE_HEM:
        best = max(best, ellipse_reach(robe_r(py), robe_sy(py), phi) + .70 * S / 2)
    if TABARD_TOP <= py <= 103:
        half = 6.8 - .8 * (py - TABARD_TOP) / (103 - TABARD_TOP)
        x = ellipse_reach(robe_r(py) + tabard_radial(py), robe_sy(py), phi) * math.cos(phi)
        if abs(x) < half * S:
            best = max(best, ellipse_reach(robe_r(py) + tabard_radial(py), robe_sy(py), phi) + .004 + .65 * S / 2)
    return best


def on_surface(px, py, lift):
    """The point on the outermost cloth at sprite column px (on the front), row py,
    lift m off it, and the outward direction there."""
    x = (px - CX) * S
    phi = -math.pi / 2
    for _ in range(6):                     # the direction whose surface point has this x
        rho = outer_surface(py, phi) + lift
        phi = math.atan2(-math.sqrt(max(rho * rho - x * x, 1e-8)), x)
    rho = outer_surface(py, phi) + lift
    c = P(CX, py)
    return Vector((c.x + rho * math.cos(phi), c.y + rho * math.sin(phi), c.z)), Vector((math.cos(phi), math.sin(phi), 0))


def tassel(b, top, part, length=.032, r=.0085, down=None):
    """A gold tassel hanging from top (along down, straight down by default): a knot
    ball, a short neck and a flared skirt. Returns its verts."""
    down = (down or Vector((0, 0, -1))).normalized()
    made = b.sphere(top + down * .004, .0065, 8, 5)
    b.finish(made, "gold", part)
    prof = [(0.0, 0.0), (.0035, -.002), (.004, -.010), (r * .8, -length * .55), (r, -length), (r * .5, -length - .002),
            (0.0, -length - .002)]
    verts, bands, _ = b.lathe(prof, 10, frame(top + down * .008, -down))
    b.finish(verts, "gold", part)
    b.paint(bands[3] + bands[4], "amber")
    return list(made) + list(verts)


CORD_R = .0026             # m, the brooch cords' thickness (radius)
CORD_CLEAR = .0025         # m between a cord and the cloth it hangs against
TASSEL_R = .0115           # m, a tassel's widest flare
CORD_END = 77.0            # the row where each cord ends and its tassel hangs


def catmull_rom(pts, per=4):
    """A smooth curve through pts, per points per span."""
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                             + (3 * p1 - p0 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def hang_cord(start, end_row):
    """A cord from start (in the brooch) hanging under gravity down to row end_row:
    a plumb line from start, except where the cloth stands out further and holds it
    off (it then lies on the cloth, CORD_CLEAR off it, pushed straight out from the
    body's axis), its distance from the axis smoothed into a soft upper hull so it
    bridges folds instead of dipping into them. No sideways pull: it only goes where
    gravity and the cloth under it put it."""
    top_row = GROUND - start.z / S
    n = 24
    rows = [top_row + 1.5 + (end_row - top_row - 1.5) * (k + 1) / n for k in range(n)]
    plumb, need, dirs = [], [], []
    for py in rows:
        c = P(CX, py)
        off = Vector((start.x - c.x, start.y - c.y, 0.0))      # the plumb line, in plan, from the axis
        phi = math.atan2(off.y, off.x)
        dirs.append(Vector((math.cos(phi), math.sin(phi), 0.0)))
        plumb.append(off.length)
        # (its end is held out by the tassel's knot resting on the cloth under it)
        knot = (.0065 - CORD_R) * smoothstep((len(need) / (n - 1) - .8) / .2)
        need.append(outer_surface(py, phi) + CORD_R + CORD_CLEAR + knot)
    want = [max(a, c) for a, c in zip(plumb, need)]
    r = list(want)
    for _ in range(40):                      # a smooth hull, never inside the cloth or the plumb line
        smooth = [(r[max(i - 1, 0)] + 2 * r[i] + r[min(i + 1, n - 1)]) / 4 for i in range(n)]
        r = [max(a, c) for a, c in zip(want, smooth)]
    pts = [start]
    for py, d, rad in zip(rows, dirs, r):
        c = P(CX, py)
        pts.append(Vector((c.x, c.y, c.z)) + d * rad)
    return catmull_rom(pts, 2)


def skin_along(b, verts, path, bones):
    """Skin verts down a chain of bones laid along path: each vert by the fraction
    of the way down the path nearest it, blended between neighbouring bones; its
    sway weight (UV2.x) is that fraction too."""
    acc = [0.0]
    for a, c in zip(path, path[1:]):
        acc.append(acc[-1] + (c - a).length)
    total = acc[-1]
    ids = [b.bone_index(nm) for nm in bones]
    nb = len(bones)
    fracs = {}
    for v in verts:
        best, f = math.inf, 0.0
        for i, (a, c) in enumerate(zip(path, path[1:])):
            ab = c - a
            t = max(0.0, min(1.0, (v.co - a).dot(ab) / max(ab.length_squared, 1e-12)))
            d = (v.co - (a + ab * t)).length
            if d < best:
                best, f = d, (acc[i] + ab.length * t) / total
        x = min(nb - 1e-6, f * nb) - .5             # bone k is centred at (k + .5) / nb
        k0 = max(0, min(nb - 1, int(math.floor(x))))
        k1 = min(nb - 1, k0 + 1)
        w1 = max(0.0, min(1.0, x - k0)) if x >= 0 else 0.0
        dv = v[b.deform]
        dv.clear()
        dv[ids[k0]] = 1.0 - w1
        if w1 > 1e-4 and k1 != k0:
            dv[ids[k1]] = w1
        fracs[v] = f
    for v in verts:
        for f in v.link_faces:
            for loop in f.loops:
                if loop.vert in fracs:
                    loop[b.sway].uv = (fracs[loop.vert], loop[b.sway].uv.y)


def chain_joints(b, path, names, parent):
    """Bones laid end to end along path, split evenly by length."""
    acc = [0.0]
    for a, c in zip(path, path[1:]):
        acc.append(acc[-1] + (c - a).length)

    def at(f):
        target = acc[-1] * f
        for i in range(1, len(acc)):
            if acc[i] >= target:
                t = (target - acc[i - 1]) / max(acc[i] - acc[i - 1], 1e-12)
                return path[i - 1].lerp(path[i], t)
        return path[-1]
    nb = len(names)
    for k, nm in enumerate(names):
        b.joints[nm] = (at(k / nb), at((k + 1) / nb), parent if k == 0 else names[k - 1])


def build_gear(b):
    """Two gold cords hanging from the brooch's side lobes down beside the tabard,
    each a smooth round tube in a gentle curve just off the cloth, tasselled, on
    its own chain (cord_1..3_R / _L) with a sway weight; and gold tassels at the
    tabard's side corners and point, each on a short bone of its own. settle()
    hangs all of them with gravity; their chains go to the colliders JSON for
    Godot spring bones."""
    from mathutils.bvhtree import BVHTree
    b.bm.normal_update()
    SURFACE["tree"] = BVHTree.FromBMesh(b.bm)
    s = BROOCH_R
    b.chains = {}
    for sx, side in ((-1, "R"), (1, "L")):          # the character's right is -X
        # hung from the underside of the side lobe's curve, outboard of the tabard's
        # ring there: its end sunk 4 mm up inside the lobe and within the brooch's
        # 6 mm thickness, so the cord comes straight out of the lobe's bottom edge
        lx = .86 * s
        lz = -math.sqrt((.52 * s) ** 2 - (lx - .48 * s) ** 2) + .004
        start = b.brooch_centre + Vector((sx * lx, -.0002, lz))
        path = hang_cord(start, CORD_END)
        verts = b.tube(path, CORD_R, 8)
        b.finish(verts, "gold", "cord")
        # the tassel hangs plumb from the cord's end, unless the cloth below stands
        # out into it: then it leans out just enough to rest on the cloth
        end = path[-1]
        foot_py = GROUND - (end.z - .036) / S
        ax_end, ax_foot = P(CX, GROUND - end.z / S), P(CX, foot_py)
        rho_end = (end - ax_end).to_2d().length
        d = (end - ax_end).to_2d().normalized().to_3d()
        phi = math.atan2(d.y, d.x)
        rho_foot = max(rho_end, outer_surface(foot_py, phi) + TASSEL_R + CORD_CLEAR)
        down = (Vector((ax_foot.x, ax_foot.y, ax_foot.z)) + d * rho_foot - end).normalized()
        tv = tassel(b, end - down * .001, "tassel", down=down)
        names = [f"cord_{k}_{side}" for k in (1, 2, 3)]
        chain_joints(b, path, names, "chest")
        skin_along(b, verts, path, names)
        skin_along(b, tv, [end, end + down * .04], names[-1:])
        b.chains["cord_" + side] = names
    for k, p in enumerate(b.tabard_tassel_points):
        tv = tassel(b, p, "tabard_tassel", .028, .0075)
        nm = f"tassel_{k}"
        b.joints[nm] = (p, p - Vector((0, 0, .036)), "hips")
        skin_along(b, tv, [p, p - Vector((0, 0, .036))], [nm])
        b.chains[nm] = [nm]
    SURFACE.clear()


# -- limbs, sleeves, book, and hands ---------------------------------------

# The built pose's arms: shoulder, elbow, wrist. "concept" holds them out as the
# concept does (the book out on her right, the left hand raised in blessing), so
# the bell sleeves' ivory outsides face the front (the owner's pick, an exception
# to the neutral pose of AGENTS.md); "neutral" is the forward pose.
# Everything else (sleeves, book, hands, mantle, colliders) follows the joints.
ARM_POSE = os.environ.get("TEACUP_ARM_POSE", "concept")
# How the book is held (the owner is choosing):
#   "search" (c): the full-size book turned about the grip until it clears the arm;
#   "d" (the owner's pick): the one-handed hold, the book standing on the palm, the
#       fingers curled round the outside of the covers, the thumb in the gutter;
#   "e": a smaller book (12 cm tall), the palm a third of the way up, pages to her head;
#   "f": the full-size book turned so its cover faces forward, the palm a third up;
#   "a" / "b": the wrist moved out and forward / the palm a quarter up (both still collide).
BOOK_HOLD = os.environ.get("TEACUP_BOOK", "d")      # the owner's pick
BOOK_GRIP = {"a": 1 / 3, "b": 1 / 4, "search": 1 / 3, "d": .03, "e": 1 / 3, "f": 1 / 3}[BOOK_HOLD]
BOOK_SCALE = .12 / .154 if BOOK_HOLD == "e" else 1.0
BOOK_FACES = "forward" if BOOK_HOLD == "f" else "head"
# how far open: each wing tips this much (tan of its angle off flat) toward the
# pages' side; the one-handed hold opens it to a V of about 110 degrees
BOOK_OPEN = .50 if BOOK_HOLD == "d" else .24
BOOK_WRIST_SHIFT = Vector((-.025, -.025, 0)) if BOOK_HOLD == "a" else Vector()   # out and forward
ARM_POSES = {
    "neutral": ((P(CX - 17, 50), P(CX - 27, 65, -.005), P(CX - 31, 57, -.100)),
                (P(CX + 17, 50), P(CX + 27, 65, -.005), P(CX + 35, 58, -.085))),
    # the concept's: upper arms down the body under the mantle, forearms out and up
    # (the elbows low enough that the bell round them passes under the mantle's hem)
    "concept": ((P(CX - 17, 50), P(CX - 28, 68, -.008), P(CX - 41, 56, -.035) + BOOK_WRIST_SHIFT),
                (P(CX + 17, 50), P(CX + 28, 69.5, -.008), P(CX + 42, 53, -.030))),
}
ARM_R, ARM_L = ARM_POSES[ARM_POSE]
# the book and right hand were placed for the neutral wrist; they keep the same
# offset from wherever the wrist is
BOOK_WRIST = ARM_POSES["neutral"][0][2]


SLEEVE_ROWS, SLEEVE_COLS = 18, 24
SLEEVE_HANG = .18          # m the drape's tip hangs below the bell's underside
SLEEVE_FLARE = .06         # how far out from the body the drape swings per metre it hangs
SLEEVE_OPEN = .030         # m short of the wrist where the bell opens (the under-sleeve cuff shows)
SLEEVE_TH = .6 * S
SLEEVE_START = .21         # of the way down the upper arm the sleeve begins, under the mantle
SLEEVE_REST_GAP = .006     # m between the arm's top and the sleeve resting on it (the rings just past the elbow, still tilted toward the upper arm, dip toward it)
ELBOW_R = .029             # the elbow ball, and the under-sleeve's radius there
# the upper arms run down under the mantle, so the sleeve is kept in under it; with
# arms raised through the mantle's side, the mantle would drape over them instead
MANTLE_DRAPES_OVER_ARMS = False
SLEEVE_UNDER_MANTLE = not MANTLE_DRAPES_OVER_ARMS
MANTLE_NEAR = 3.0         # px outside the mantle's line a sleeve point still counts as under its edge
HEM_OPEN = 0.0            # px the sleeve may stand out from the mantle's line per px below its hem
HEM_DROP = 3.0            # px under the mantle's hem a drape point outside it is dropped to
MANTLE_UNDER = 0.0         # px below the mantle's hem the sleeve is still kept in under it
# sleeve mid-surface off the coat's mid-surface: 6.5 mm between them, room for the
# upper arm to swing in a little and the chest to tilt over the coat in the clips
COAT_CLEAR = .72 * S / 2 + SLEEVE_TH / 2 + .0065
# under the mantle's: its half thickness measured across (it slopes about 35 degrees
# off upright), the sleeve's own (allowing for its tilt) and 3 mm
MANTLE_CLEAR = .95 * S / 2 / math.cos(math.radians(35)) + SLEEVE_TH / 2 * 1.3 + .003
# the sleeve's panels in the atlas, each unrolled on its own: the upper tube (seam
# under the arm), the bell's top over the forearm, and the drape below it
SLEEVE_CUT = .030          # m the top of the wrist opening sits back from its underside
SLEEVE_TURN = .26          # either side of the elbow (fraction of the sleeve) its rings turn over
SLEEVE_SIDE_COL = 5        # the bell / drape seams: columns 5 and 19 (105 degrees round from the top)


def arm_path(shoulder, elbow, end, n, corner=.035):
    """n points evenly along shoulder -> elbow -> end, the elbow rounded by a
    quadratic curve; also the fraction of the way along that the elbow falls."""
    u, f = (elbow - shoulder).normalized(), (end - elbow).normalized()
    e1, e2 = elbow - u * corner, elbow + f * corner
    dense = [shoulder.lerp(e1, k / 40) for k in range(40)]
    dense += [e1 * (1 - t) ** 2 + elbow * 2 * t * (1 - t) + e2 * t * t for t in (k / 20 for k in range(20))]
    dense += [e2.lerp(end, k / 40) for k in range(41)]
    acc = [0.0]
    for a, c in zip(dense, dense[1:]):
        acc.append(acc[-1] + (c - a).length)
    total = acc[-1]
    pts = []
    for k in range(n):
        target = total * k / (n - 1)
        i = next(i for i in range(1, len(acc)) if acc[i] >= target - 1e-12)
        t = (target - acc[i - 1]) / max(acc[i] - acc[i - 1], 1e-12)
        pts.append(dense[i - 1].lerp(dense[i], t))
    s_elbow = (acc[40 + 10]) / total
    return pts, s_elbow


def sleeve_radius(s, s_e):
    return interp([(0.0, .036), (s_e * .55, .041), (s_e, .043), (s_e + .4 * (1 - s_e), .064),
                   (1.0, .095)], s)


def arm_radius(s, s_e):
    """The radius of the arm under the sleeve at s: the upper arm, the elbow ball,
    the forearm's under-sleeve."""
    return interp([(0.0, .032), (s_e, ELBOW_R), (1.0, .024)], s)


def sleeve_hang(s, s_e):
    """How far the drape hangs below the bell's underside at s (0 at the shoulder,
    1 at the wrist opening): nothing above the elbow, falling quickly to most of its
    length just past it, so the drape hangs as a long panel the whole way along the
    forearm (its face looks the way the arm's side does), and deepening to its
    pointed tip at the wrist end."""
    start = s_e * .94
    along = smoothstep((s - start) / (.40 * (1 - start)))
    return SLEEVE_HANG * (.72 * along + .28 * smoothstep((s - .55 - .45 * s_e) / (.45 - .45 * s_e + 1e-6)))


def ellipse_coords(p, sy):
    """(radius px, angle) of p round the body's axis in an ellipse of depth scale sy."""
    c = P(CX, GROUND)
    dx, dy = (p.x - c.x) / S, (p.y - c.y) / S / sy
    return math.hypot(dx, dy), math.atan2(dy, dx)


def from_ellipse(p, r, a, sy):
    c = P(CX, GROUND)
    return Vector((c.x + r * S * math.cos(a), c.y + r * S * sy * math.sin(a), p.z))


MANTLE_ARM_LIFT = 2.5      # px the mantle's hem is shorter over each arm, so the sleeve passes under it
MANTLE_ARM_SPREAD = math.radians(28)


def mantle_arm_lift(a):
    """How much shorter the mantle's hem is at angle a: most over each elbow, easing
    off either side."""
    lift = 0.0
    for _, el, _ in (ARM_R, ARM_L):
        ae = ellipse_coords(el, .74)[1]
        d = (a - ae + math.pi) % (2 * math.pi) - math.pi
        lift += MANTLE_ARM_LIFT * math.exp(-(d / MANTLE_ARM_SPREAD) ** 2)
    return lift


def mantle_radius(py, a):
    """The mantle's mid-surface radius (px, depth scale .74) where it passes row py
    at angle a, and its hem's py there. Its lower rows are dropped by the scallops
    without widening, so the row t passing py is solved for (as build_mantle lays
    them: py = top + 17 t + scallop(a) * smoothstep((t - .65) / .35))."""
    span = MANTLE_HEM - MANTLE_TOP
    scallop = 1.7 * math.sin(5 * a) ** 2

    lift = mantle_arm_lift(a)

    def row_py(t):
        return MANTLE_TOP + (span - lift) * t + scallop * smoothstep((t - .65) / .35)
    hem = row_py(1.0)
    if py >= hem:
        t = 1.0 + (py - hem) / span
    else:
        lo, hi = 0.0, 1.0
        for _ in range(30):
            m = (lo + hi) / 2
            lo, hi = (m, hi) if row_py(m) < py else (lo, m)
        t = lo
    return 17.0 + 12.0 * max(0.0, t), hem


def keep_clear(p, hanging=False, on_upper_arm=True):
    """A sleeve point moved off the coat (it lies over the coat's shoulder and side)
    and in under the mantle where the mantle covers it, each with clearance. The
    hanging drape is left out of the mantle's pull: pulled in point by point, its
    two close layers would cross."""
    py = GROUND - p.z / S
    if OUTER_COAT[0] <= py <= OUTER_COAT[1]:
        sy = robe_sy(py)
        r, a = ellipse_coords(p, sy)
        need = layer_radius(py, a, *OUTER_COAT) + COAT_CLEAR / S
        if r < need:
            p = from_ellipse(p, need, a, sy)
    r, a = ellipse_coords(p, .74)
    rm, hem = mantle_radius(py, a)
    # (only points under the mantle, or near its line, are held in: a point well
    # outside it, such as the raised forearm's bell above the hem's height, is clear)
    if SLEEVE_UNDER_MANTLE and on_upper_arm and MANTLE_TOP <= py <= hem + MANTLE_UNDER and r < rm + MANTLE_NEAR:
        # under the mantle, inside it; below its hem the allowed radius opens out
        # steadily (HEM_OPEN px per px down), so no face slants through the hem's edge
        lim = rm - MANTLE_CLEAR / S + HEM_OPEN * max(0.0, py - hem - 1.0)
        if r > lim:
            if not hanging:
                p = from_ellipse(p, lim, a, .74)
            elif py < hem + HEM_DROP:
                # the drape's top just under the hem drops clear of its edge (both
                # layers alike, so they never cross)
                p = Vector((p.x, p.y, H(hem + HEM_DROP)))
    return p


def build_sleeve(b, side, joints):
    """One wide bell sleeve as a single cloth tube: from the shoulder, where it
    lies over the coat's shoulder and in under the mantle, to the wrist opening.
    Each row is a ring round the arm hanging under gravity: its top rests on the
    arm (SLEEVE_REST_GAP clear) and the slack falls below, more toward the wrist,
    where the underside is drawn down into the long pointed drape. The last row (the
    opening) runs over the forearm and down both edges of the drape: one gold hem
    round it all (atlas art). Ivory outside with line art, blue lining inside, a few
    big folds. The tube follows the arm, blending upper arm to forearm across the
    elbow; the drape hangs on its own chain sleeve_1 / sleeve_2 (children of the
    forearm), sway weight in UV2.x, pinned at the shoulder."""
    shoulder, elbow, wrist = joints
    upper, fore = "upperarm_" + side, "forearm_" + side
    axis_f = (wrist - elbow).normalized()
    end = wrist - axis_f * SLEEVE_OPEN
    centres, s_e = arm_path(shoulder.lerp(elbow, SLEEVE_START), elbow, end, SLEEVE_ROWS)
    down = Vector((0, 0, -1))
    u_dir, f_dir = (elbow - shoulder).normalized(), axis_f
    mids, info, radials, hung = [], [], [], []
    for j, c in enumerate(centres):
        s = j / (SLEEVE_ROWS - 1)
        # each ring's plane turns from square-to-the-upper-arm to square-to-the-forearm
        # over the rows either side of the elbow, never faster than its rows are
        # spaced, so the rings never cross on the inside of the bend
        k = smoothstep((s - (s_e - SLEEVE_TURN)) / (2 * SLEEVE_TURN))
        t = u_dir.slerp(f_dir, k) if hasattr(u_dir, "slerp") else u_dir.lerp(f_dir, k).normalized()
        d = (down - t * down.dot(t)).normalized()          # down, square to the arm
        sd = t.cross(d).normalized()                        # across the arm
        r = sleeve_radius(s, s_e)
        # the ring drops until its top rests on the arm's top
        rc = c + d * (r - arm_radius(s, s_e) - SLEEVE_REST_GAP - SLEEVE_TH / 2)
        hang_s = sleeve_hang(s, s_e)
        away = Vector((c.x - P(CX, 0).x, c.y, 0)).normalized()
        row, row_info, radial = [], [], []
        for i in range(SLEEVE_COLS):
            psi = 2 * math.pi * i / SLEEVE_COLS - math.pi   # 0 straight under the arm, the seam on top
            w = max(0.0, 1 - abs(psi) / math.radians(110)) ** 1.3
            hang = hang_s * w
            hf = min(1.0, hang / SLEEVE_HANG)
            # the drape's two layers fall near together (the lining shows only at its
            # edge), with a soft belly part way down
            # (only deep in the drape: round the forearm the bell keeps its full round sides)
            squeeze = 1 - .60 * smoothstep((hang - .02) / .10)
            top = max(0.0, -math.cos(psi)) ** 2             # where it rests on the arm: no folds
            fold = 1 + .06 * math.sin(3 * psi + .6) * min(1.0, s * 2) * (1 - top)
            p = rc + (d * math.cos(psi) * fold + sd * math.sin(psi) * fold * squeeze) * r + down * hang
            # a few big folds down the drape, both layers together, and the drape
            # flaring a little out from the body as it falls, as in the concept
            p += sd * .016 * math.sin(2 * math.pi * (1.3 * s + .15)) * min(1.0, hang / .06)
            # the opening slopes back on top, so its hem frames the bell rather than
            # facing straight out: the top of the last rows is cut back along the arm
            p -= t * SLEEVE_CUT * top * smoothstep((s - .82) / .18)
            p += away * SLEEVE_FLARE * hang
            row.append(keep_clear(p, hang > .004))
            row_info.append((s, hang))
            radial.append(d * math.cos(psi) + sd * math.sin(psi))
        mids.append(row)
        info.append(row_info)
        radials.append(radial)
        hung.append(rc)
    norms = grid_normals(mids, wrap=True)
    for j in range(SLEEVE_ROWS):                            # facing out from the arm (on the drape,
        for i in range(SLEEVE_COLS):                        # out from its middle: the ring's own direction)
            if norms[j][i].dot(radials[j][i]) < 0:
                norms[j][i] = -norms[j][i]
    verts, fronts, backs = cloth(b, mids, norms, SLEEVE_TH, wrap=True)
    part = "sleeve_" + side
    faces = b.finish(verts, "ivory", part, smooth=False)
    b.paint(list(backs.values()), "blue")
    # the outside in three panels, each unrolled on its own so none is stretched
    je = min(range(SLEEVE_ROWS), key=lambda j: abs(j / (SLEEVE_ROWS - 1) - s_e))
    n, sc = SLEEVE_COLS, SLEEVE_SIDE_COL
    outside = outer_grid(mids, norms, SLEEVE_TH)
    if os.environ.get("TEACUP_OLD_UNWRAP"):        # stage 3's unwrap, for the before/after checker
        b.atlas.grid(part + "_upper", "sleeve_upper", [row + [row[0]] for row in mids], fronts)
        return finish_sleeve(b, side, mids, info, hung, verts, faces, s_e, upper, fore)
    sleeve_panel(b, part + "_upper", "sleeve_upper", outside, fronts, range(0, je + 1),
                 [(n // 2 + k) % n for k in range(n + 1)])                       # seam under the arm
    sleeve_panel(b, part + "_bell", "sleeve_bell", outside, fronts, range(je, SLEEVE_ROWS),
                 [(n - sc + k) % n for k in range(2 * sc + 1)])                  # over the forearm
    # the drape below, in two panels split along its bottom crease: each layer lies
    # nearly flat, so each unrolls true
    sleeve_panel(b, part + "_drape_a", "sleeve_drape", outside, fronts, range(je, SLEEVE_ROWS),
                 list(range(sc, n // 2 + 1)))
    sleeve_panel(b, part + "_drape_b", "sleeve_drape", outside, fronts, range(je, SLEEVE_ROWS),
                 list(range(n // 2, n - sc + 1)))
    return finish_sleeve(b, side, mids, info, hung, verts, faces, s_e, upper, fore)


BELL_FROM, BELL_OVER = .08, .30   # past the elbow (fraction of the sleeve) the bell starts taking the forearm's
                                  # weight, and over how much more it takes it all (the rows between gather up)


def finish_sleeve(b, side, mids, info, hung, verts, faces, s_e, upper, fore):
    """A sleeve's drape chain, skin weights and sway."""
    # bones: the bell (bell_<side>, along the forearm from the elbow's ring to the
    # opening's), which slides down a raised forearm (settle()),
    # and the drape's chain on it from under the wrist opening down to its tip
    bell = "bell_" + side
    je = min(range(SLEEVE_ROWS), key=lambda j: abs(j / (SLEEVE_ROWS - 1) - s_e))
    b.joints[bell] = (hung[je], hung[-1], fore)
    tip = mids[-1][SLEEVE_COLS // 2]
    top = hung[-1] + (tip - hung[-1]).normalized() * sleeve_radius(1.0, s_e)
    mid = top.lerp(tip, .5)
    b.joints["sleeve_1_" + side] = (top, mid, bell)
    b.joints["sleeve_2_" + side] = (mid, tip, "sleeve_1_" + side)
    # weights from each vert's grid point
    from mathutils.kdtree import KDTree
    flat = [(j, i) for j in range(SLEEVE_ROWS) for i in range(SLEEVE_COLS)]
    kd = KDTree(len(flat))
    for k, (j, i) in enumerate(flat):
        kd.insert(mids[j][i], k)
    kd.balance()
    ids = {nm: b.bone_index(nm) for nm in ("chest", upper, fore, bell, "sleeve_1_" + side, "sleeve_2_" + side)}
    for v in verts:
        j, i = flat[kd.find(v.co)[1]]
        s, hang = info[j][i]
        h = hang / SLEEVE_HANG
        # the forearm takes the rows from just before the elbow (rows past it left on the
        # upper arm fold through the under-sleeve when the forearm stands up)
        k_fore = smoothstep((s - s_e + .03) / .12)
        k_pin = .5 * smoothstep((.08 - s) / .08)            # its very top shares the chest with the mantle
        k_drape = smoothstep(hang / (SLEEVE_HANG * .22))
        k_two = smoothstep((h - .35) / .45)
        k_bell = smoothstep((s - s_e - BELL_FROM) / BELL_OVER)   # the bell's share of the forearm's, out to the opening
        ws = {"chest": k_pin, upper: (1 - k_pin) * (1 - k_fore),
              fore: (1 - k_pin) * k_fore * (1 - k_bell), bell: (1 - k_pin) * k_fore * k_bell}
        ws = {nm: x * (1 - k_drape) for nm, x in ws.items()}
        ws["sleeve_1_" + side] = k_drape * (1 - k_two)
        ws["sleeve_2_" + side] = k_drape * k_two
        dv = v[b.deform]
        dv.clear()
        total = sum(ws.values())
        for nm, x in ws.items():
            if x > 1e-4:
                dv[ids[nm]] = x / total
    for f in faces:                                         # UV2.x: pinned at the shoulder, free at the tip
        for loop in f.loops:
            j, i = flat[kd.find(loop.vert.co)[1]]
            s, hang = info[j][i]
            loop[b.sway].uv = (min(1.0, .2 * s + .8 * hang / SLEEVE_HANG), 0.0)
    return verts


def sleeve_panel(b, name, kind, mids, fronts, rows, cols):
    """One panel of a sleeve in the atlas: its rows and (wrapping) columns of the
    sleeve's grid, unrolled on its own."""
    rows, n = list(rows), len(mids[0])
    sub = [[mids[j][i] for i in cols] for j in rows]
    sub_fronts = {}
    for jj, j in enumerate(rows[:-1]):
        for ii, i in enumerate(cols[:-1]):
            if (cols[ii + 1] - i) % n == 1 and (j, i) in fronts:
                sub_fronts[(jj, ii)] = fronts[(j, i)]
    b.atlas.grid(name, kind, sub, sub_fronts, no_fold=kind in ("sleeve_bell", "sleeve_drape"))


def build_arm(b, side, joints):
    """The arm under the sleeve: a small shoulder ball and a slim upper arm (both
    hidden), an elbow ball like the Toaster's, and a slim cream under-sleeve all
    the way down the forearm ending in a short white cuff over the glove's top,
    so no bare arm shows; then the sleeve."""
    shoulder, elbow, wrist = joints
    upper, fore = "upperarm_" + side, "forearm_" + side
    b.joints[upper] = (shoulder, elbow, "chest")
    b.joints[fore] = (elbow, wrist, upper)
    hand_end = wrist + (wrist - elbow).normalized() * .065
    b.joints["hand_" + side] = (wrist, hand_end, fore)
    axis = (wrist - elbow).normalized()
    b.finish(b.sphere(shoulder, .030, 10, 6), "cream", upper)
    b.finish(b.tube([shoulder, shoulder.lerp(elbow, .5), elbow], .031, 10, rs=[.028, .031, ELBOW_R]),
             "cream", upper)
    b.finish(b.sphere(elbow, ELBOW_R, 10, 6), "cream", fore)
    cuff0, cuff1 = wrist - axis * .044, wrist - axis * (GLOVE_CUFF - .004)
    b.finish(b.tube([elbow, elbow.lerp(cuff0, .5), cuff0 + axis * .004], .026, 10,
                    rs=[ELBOW_R, .026, .024]), "cream", fore)
    b.finish(b.tube([cuff0, cuff0.lerp(cuff1, .5), cuff1], .029, 12, rs=[.028, .031, .030]),
             "ivory", fore)
    build_sleeve(b, side, joints)


# Collider capsules (bone, head, tail, radius in the bone's rest frame) the
# sleeves are pushed out of: settle() uses them for clips, and Godot spring
# bones (SpringBoneSimulator3D) can reuse them later (source/v2/*_colliders.json).
def sleeve_colliders(b):
    out = []

    def cap(name, bone, head, tail, r):
        out.append({"name": name, "bone": bone, "head": list(head), "tail": list(tail), "radius": r})
    for side, (sh, el, wr) in (("R", ARM_R), ("L", ARM_L)):
        cap("forearm_" + side, "forearm_" + side, el, wr, ELBOW_R + .004)
        cap("upperarm_" + side, "upperarm_" + side, sh, el, .048)        # the upper arm in its sleeve
        h0, h1 = b.joints["hand_" + side][:2]
        cap("hand_" + side, "hand_" + side, h0, h1, .032)
        hip, knee = b.joints["thigh_" + side][:2]
        cap("thigh_" + side, "thigh_" + side, hip, knee, .085)      # the robe over the thigh
    sp = b.book_spine
    cap("book", "book", sp - b.book_axis * .07 + b.book_out * .04, sp + b.book_axis * .07 + b.book_out * .04, .055)
    cap("torso", "spine", P(CX, 92), P(CX, 50), .135)                 # the robes round the body
    cap("skirt", "hips", P(CX, 104), P(CX, 66), .240)                 # the coats' flared skirts
    t0, t1 = tabard_point(CX, TABARD_TOP + 2), tabard_point(CX, 98)
    cap("tabard", "hips", t0 + Vector((0, .02, 0)), t1 + Vector((0, .02, 0)), .02)   # its face, from behind
    return out


def open_hand(b, wrist, forward, palm_up, side, palm_at=None, spread=0.0):
    """Approved-character open glove construction, with correct thumb chirality;
    spread (degrees) fans the fingers apart and the thumb out wide."""
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
    from mathutils import Quaternion
    for k, off in enumerate((2.5, .85, -.85, -2.5)):
        o = thumb_side * off * S * (1 + spread / 60)
        length = (4.6 if 0 < k < 3 else 4.0) * S
        # each finger fanned out from the middle, about the palm's normal
        fan = Quaternion(up, math.radians(spread * off / 2.5) * (1 if side == "R" else -1))
        fk = fan @ f
        pts = [tip_base + o, tip_base + o + fk * length * .55 + up * .4 * S,
               tip_base + o + fk * length + up * 1.6 * S]
        b.finish(b.tube(pts, .95 * S, 5, rs=[1.0 * S, .95 * S, .8 * S]), "mauve", part)
    t0 = palm + thumb_side * 3.0 * S - f * .8 * S
    wide = 1 + spread / 40                  # the thumb swings out wider as the hand opens
    b.finish(b.tube([t0, t0 + thumb_side * 2.2 * S * wide + f * 1.4 * S + up * .8 * S,
                     t0 + thumb_side * 3.0 * S * wide + f * 3.4 * S / wide + up * 1.8 * S],
                    1.05 * S, 5, rs=[1.15 * S, 1.0 * S, .85 * S]), "mauve", part)
    return palm


def book_wing(b, spine, sign, axis, across, facing):
    """One cover/page wing; its inner pages face the cleric's head."""
    w, h = BOOK_W, BOOK_H
    xdir, normal, centre = wing_frame(spine, sign, axis, across, facing)
    if BOOK_HOLD == "d":                   # the cover's inner end sunk just inside the gold spine
        s0 = COVER_START
        cover = b.finish(b.box(spine + xdir * (s0 + 1.02 * w) / 2, (1.02 * w - s0, COVER_T, h), xdir=xdir, zdir=axis),
                         "blue_dark", "book", smooth=False)
    else:
        cover = b.finish(b.box(centre, (w, COVER_T, h), xdir=xdir, zdir=axis),
                         "blue_dark", "book", smooth=False)
    # the book laid open flat: u across the spread (the back cover to the left of
    # the spine, the front to its right), v down from the top edge
    def spread(co):
        return sign * (co - spine).dot(xdir), h / 2 - (co - spine).dot(axis)
    b.atlas.flat("book_cover", "book_cover", [f for f in cover if f.normal.dot(normal) < -.7], spread)
    covers = b.atlas.regions["book_cover"]["guides"].setdefault("covers", [])
    lo, hi = sorted((sign * .02 * w, sign * 1.02 * w))
    covers.append([lo, 0.0, hi, h])
    page_c = centre + normal * (COVER_T / 2 + PAGE_T / 2 + .0005 if BOOK_HOLD == "d" else .011)
    step = .0015 if BOOK_HOLD == "d" else .003          # (a thinner book in the one-handed hold)
    for k in range(4):
        if BOOK_HOLD == "d":
            # big pages almost filling the cover (the owner's mark): the top page 5 mm
            # in from the cover's top, bottom and outer edges, the layers under it a
            # little larger so their stacked edges show; the inner edges as before
            inner, outer = .0205 + .0015 * k, 1.02 * w - .0035 - .0005 * k
            pw_k, ph_k = outer - inner, h - .0045 - .002 * k
            q = page_c + normal * (step * k) + xdir * ((inner + outer) / 2 - .52 * w)
        else:
            pw_k, ph_k = w - .021 - .003 * k, h - .023 - .004 * k
            q = page_c + normal * (step * k) + xdir * (.0015 * k)
        page_faces = b.finish(b.box(q, (pw_k, PAGE_T, ph_k), xdir=xdir, zdir=axis),
                              "ivory" if k < 3 else "cream_warm", "book", smooth=False)
        if k == 3:
            b.atlas.flat("page", "page", [f for f in page_faces if f.normal.dot(normal) > .7], spread)
            if BOOK_HOLD == "d":           # the art over the whole page, the gutter's curve included
                a_in, a_out = BOOK_OPEN * (BOOK_PAGE_TOP - GUTTER_DIP) + .004, (q - spine).dot(xdir) + pw_k / 2 - .004
                pw, ph, mid = a_out - a_in, ph_k - .008, (a_in + a_out) / 2
            else:
                pw, ph, mid = w - .030, h - .035, (q - spine).dot(xdir)
            lo, hi = sorted((sign * (mid - pw / 2), sign * (mid + pw / 2)))
            b.atlas.regions["page"]["guides"].setdefault("pages", []).append([lo, (h - ph) / 2, hi, (h + ph) / 2])
        if BOOK_HOLD == "d":
            gutter_curve(b, spine, xdir, normal, q, pw_k, ph_k, "ivory",     # the paper's own colour
                         spread if k == 3 else None)
    # A narrow concealed binding joins the cover and every raised page layer
    # to the gold spine, keeping the open book a single physical assembly.
    # (inside the cover's outer face and under the top page, never standing out of either)
    bt = .0065 if BOOK_HOLD == "d" else .026         # (low under the gutter's curve in the one-handed hold)
    binding = spine + xdir * .010 + normal * (bt / 2 - (COVER_T / 2 - .0005))
    b.finish(b.box(binding, (.022, bt, h - .030), xdir=xdir, zdir=axis),
             "blue_dark", "book", smooth=False)
    return centre, xdir, normal


GUTTER_DIP = .005          # m the pages dip below their flat face where they meet in the gutter


def gutter_curve(b, spine, xdir, normal, q, width, height, colour, spread=None):
    """One page layer's inner edge bent down into the gutter: from the flat layer's
    inner edge (centre q, its width along xdir) it curves smoothly (flat where it
    leaves the page, steepening, GUTTER_DIP lower at the end) to the plane midway
    between the two wings, a hair past it, so the paper of both wings meets in the
    gutter and no cover shows between them."""
    a0 = (q - spine).dot(xdir) - width / 2 + .001           # just inside the flat layer
    b0 = (q - spine).dot(normal)
    b1 = b0 - GUTTER_DIP
    a1 = BOOK_OPEN * b1 - .0005                             # the mid plane (a = k b), a hair past it
    pts, nrm = [], []
    for i in range(7):
        u = i / 6
        a = a0 + (a1 - a0) * u
        bb = b0 - GUTTER_DIP * u * u
        da, db = (a1 - a0), -2 * GUTTER_DIP * u
        pts.append(spine + xdir * a + normal * bb)
        n = (normal * da - xdir * db).normalized()
        nrm.append(n if n.dot(normal) > 0 else -n)
    centre = spine + normal * b0
    faces = b.finish(b.strap(pts, centre, height, PAGE_T, normals=nrm), colour, "book", smooth=False)
    # its paper side shades smoothly, flowing on from the flat page with no seam or
    # facets; with spread (the top page) the page's own texture runs over it too
    top = [f for f in faces if f.normal.dot(normal) > .5]
    for f in top:
        f.smooth = True
    if spread:
        b.atlas.flat("page", "page", top, spread)


def book_frame(wrist):
    """The book's frame (axis up its spine, across it, facing her head) and the
    grip (fingers, palm centre, spine centre) for a book held a third of the way up
    its spine with the palm's base on the wrist."""
    up = Vector((0, 0, 1))
    spine = wrist + Vector((0, -.06, .05))
    for _ in range(4):                      # the grip and the book's facing settle together
        # its pages toward her head, or ("f") turned so its cover faces forward
        target = P(CX, 27, -.015) if BOOK_FACES == "head" else spine + Vector((.12, .40, .10))
        facing = (target - spine).normalized()
        axis = (up - facing * up.dot(facing)).normalized()
        across = facing.cross(axis).normalized()
        finger_dir = across if across.x > 0 else -across
        palm_at = wrist + finger_dir * PALM_HALF
        spine = palm_at + finger_dir * .020 + axis * BOOK_H * (.5 - BOOK_GRIP) + facing * .018
    return axis, across, facing, finger_dir, palm_at, spine


def book_boxes(spine, axis, across, facing, pad=.003):
    """Polygons (verts, faces) roughly enclosing the open book's two wings, pad m
    all round: what the book's placement is tested against the built model with."""
    verts, faces = [], []
    w, h = BOOK_W, BOOK_H
    for sign in (-1, 1):
        xdir = (across * sign + facing * .24).normalized()
        xdir = (xdir - axis * xdir.dot(axis)).normalized()
        normal = axis.cross(xdir).normalized()
        if normal.dot(facing) < 0:
            normal = -normal
        c = spine + xdir * w * .52 + normal * .010
        hx, hy, hz = w / 2 + pad, .016 + pad, h / 2 + pad
        base = len(verts)
        for sx, sy, sz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                           (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
            verts.append(c + xdir * sx * hx + normal * sy * hy + axis * sz * hz)
        faces += [[base + i for i in f] for f in ((0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2),
                                                   (2, 6, 7, 3), (3, 7, 4, 0))]
    return verts, faces


def place_book(b, wrist):
    """The book turned about the grip until it clears the built forearm, sleeve and
    body: turns about its spine (up to 60 degrees) and small tilts (up to 15) are
    tried, and the clear one nearest the upright, head-facing book is kept."""
    from mathutils import Quaternion
    from mathutils.bvhtree import BVHTree
    axis, across, facing, finger_dir, palm_at, spine = book_frame(wrist)
    b.bm.normal_update()
    model = BVHTree.FromBMesh(b.bm)
    best = None
    for roll in range(-15, 16, 5):           # (it stays near upright, turning mostly about its spine)
        for pitch in range(-15, 16, 5):
            for yaw in range(-30, 31, 10):
                q = (Quaternion(facing, math.radians(roll)) @ Quaternion(across, math.radians(pitch))
                     @ Quaternion(axis, math.radians(yaw)))
                a, c, f = q @ axis, q @ across, q @ facing
                fd = q @ finger_dir
                sp = palm_at + q @ (spine - palm_at)
                vs, fs = book_boxes(sp, a, c, f)
                hits = len(model.overlap(BVHTree.FromPolygons(vs, fs)))
                score = (hits, abs(roll) + abs(pitch) + abs(yaw))
                if best is None or score < best[0]:
                    best = (score, a, c, f, fd, sp)
    (hits, turn), axis, across, facing, finger_dir, spine = best
    b.book_turn = BOOK_TURN["turn"] = (hits, turn)
    return axis, across, facing, finger_dir, palm_at, spine


def wing_frame(spine, sign, axis, across, facing, open_k=None):
    """One wing of the open book: (xdir out along it, normal toward its pages, the
    cover's centre). open_k tips the wings toward the pages' side (tan of the angle
    each makes with flat)."""
    k = BOOK_OPEN if open_k is None else open_k
    xdir = (across * sign + facing * k).normalized()
    xdir = (xdir - axis * xdir.dot(axis)).normalized()
    normal = axis.cross(xdir).normalized()
    if normal.dot(facing) < 0:
        normal = -normal
    return xdir, normal, spine + xdir * BOOK_W * .52


GRIP_UP = 72.0             # degrees the fingers rise from level up the cover's back
GRIP_OUT = 0.0             # m from the spine to the palm's middle, along the cover: the
                           # spine runs up the middle of her palm (the owner's mark)
GRIP_BACK = .005           # m the palm stands off the covers' outer faces, clear of the spine
SPINE_R = .0065            # the gold spine's radius in this hold (a half cylinder)
COVER_START = .0045        # m from the spine where each cover's inner end sits (inside the spine)
SPINE_HINGE = .006         # m out along each cover where the spine's section meets its inner face
SPINE_SINK = 0.0           # m its flat side sits behind the spine line (its edges stay inside the covers)
GRIP_LOW = -.002           # m the palm's middle sits below the cover's foot (up its back if negative)


def cradle_frame(wrist):
    """The one-handed hold ("d"): the book standing upright with its pages toward
    her head, pinched at the foot of its spine. The hand is under the book beside
    the spine with the bottom edge of the cover on her left (+across) in its web:
    the palm faces that cover's outside, the fingers rise up its back, and the
    thumb, on the spine's side (f x n for her right hand), comes round under its
    foot and up its pages beside the gutter."""
    up = Vector((0, 0, 1))
    spine = wrist + Vector((0, -.04, BOOK_H / 2))
    for _ in range(8):
        facing = (P(CX, 27, -.015) - spine).normalized()
        axis = (up - facing * up.dot(facing)).normalized()
        across = facing.cross(axis).normalized()
        xb, nb, _ = wing_frame(spine, 1, axis, across, facing)
        a = math.radians(GRIP_UP)
        f = (axis * math.sin(a) + xb * math.cos(a)).normalized()     # wrist -> fingers
        thumb_side = f.cross(nb).normalized()                          # toward the spine
        palm_c = wrist + f * PALM_HALF
        # the palm 3.5 mm off the cover's outer face (so the glove cuff at the wrist clears its corner)
        spine = palm_c + nb * (COVER_T / 2 + GRIP_BACK + 1.2 * S) - xb * GRIP_OUT + axis * (BOOK_H / 2 + GRIP_LOW)
    return axis, across, facing, palm_c, spine, f, thumb_side


GRIP_DEBUG = {}


def cradle_hand(b, palm_c, spine, axis, across, facing, f, thumb_side):
    """The right hand pinching the open book at the foot of its spine: the palm
    under the +across cover facing its outside, the four fingers rising up that
    cover's back beside the spine (index finger nearest it, middle longest), 1.5 mm
    off it; the thumb round under the cover's foot and up its pages beside the
    gutter, holding them open 1.5 mm off the paper."""
    from mathutils import Quaternion
    part = "hand_R"
    xb, nb, cb = wing_frame(spine, 1, axis, across, facing)
    palm_n = nb                                    # the palm faces the cover
    b.finish(b.box(palm_c, (5.6 * S, 6.0 * S, 2.4 * S), xdir=thumb_side, zdir=palm_n), "mauve", part, smooth=False)
    for k in range(4):                              # index finger (k = 0) nearest the spine
        fr = (.75, .78, .75, .65)[k] * S
        length = (4.2, 4.8, 4.5, 3.6)[k] * S
        fan = Quaternion(palm_n, math.radians((1.0 - k) * 4.0))       # spread a little about the palm's normal
        fk = fan @ f
        # knuckles along the palm's far edge, the finger's middle 1.5 mm off the cover
        p0 = palm_c + f * 2.5 * S + thumb_side * (2.1 - 1.4 * k) * S + palm_n * (1.2 * S + .002 - fr)
        p1 = p0 + fk * length * .45
        p2 = p1 + fk * length * .33
        p3 = p2 + fk * length * .22
        b.finish(b.tube([p0, p1, p2, p3], fr, 6, rs=[fr * 1.1, fr, fr * .92, fr * .8]), "mauve", part)
        for q, r in ((p0, 1.12), (p1, 1.04), (p2, .96), (p3, .80)):    # knuckle, joints, rounded tip
            b.finish(b.sphere(q, fr * r, 6, 4), "mauve", part)
        GRIP_DEBUG.setdefault("fingers", []).append([p0, p1, p2, p3])
    # thumb: a thumb's length, from the palm's spine side tight round the -across
    # wing's foot beside the spine, its tip pressing the page block's bottom corner
    # by the gutter, 1.5 mm off the paper
    xa, na, ca = wing_frame(spine, -1, axis, across, facing)
    rt = .95 * S
    top = BOOK_PAGE_TOP + rt + .0015                                    # over the top page
    t0 = palm_c + thumb_side * 1.2 * S - f * 2.4 * S + palm_n * .008    # its root, in the palm
    t_a = spine + xa * .007 + na * .005 - axis * (BOOK_H / 2 + rt + .004)   # under the spine's foot
    t_b = spine + xa * .015 + na * (.007 + rt) - axis * (BOOK_H / 2 + rt * .5 + .0015)
    t1 = spine + xa * .020 + na * top - axis * (BOOK_H / 2 - .003)     # the joint
    t2 = spine + xa * .022 + na * top - axis * (BOOK_H / 2 - .009)
    t3 = spine + xa * .023 + na * top - axis * (BOOK_H / 2 - .013)     # the tip
    GRIP_DEBUG["thumb_segs"] = [round((q1 - q0).length, 4) for q0, q1 in zip([t0, t_a, t_b, t1, t2], [t_a, t_b, t1, t2, t3])]
    GRIP_DEBUG["thumb_len"] = sum((q1 - q0).length for q0, q1 in zip([t0, t_a, t_b, t1, t2], [t_a, t_b, t1, t2, t3]))
    # (on its own bone, thumb_R, so it lifts off the pages when she shuts the book)
    b.joints["thumb_R"] = (t0, t_a, "hand_R")
    thumb = b.tube([t0, t_a, t_b, t1, t2, t3], rt, 6, rs=[1.25 * S, 1.1 * S, 1.05 * S, rt, rt * .95, rt * .8])
    b.finish(thumb, "mauve", part)
    joint = b.sphere(t2, rt * 1.05, 6, 4)                               # the joint
    b.finish(joint, "mauve", part)
    reskin(b, list(thumb) + list(joint), "thumb_R")
    GRIP_DEBUG.update(palm=palm_c, thumb=[t0, t_a, t_b, t1, t2, t3], frame=(spine, axis, across, facing))
    return palm_c


def build_book_and_grip(b):
    """The open book held in the right hand by its spine: the palm lies flat on the
    spine's outside a third of the way up it, its base on the wrist (so the forearm
    is its real length and the glove only a short cuff past the under-sleeve), the
    fingers square to the spine, the pages facing her head as nearly as the arm and
    sleeve under it allow (place_book)."""
    wrist = ARM_R[2]
    fore_axis = (wrist - ARM_R[1]).normalized()
    if BOOK_HOLD == "d":                   # the one-handed hold, the book standing on the palm
        axis, across, facing, palm_at, spine, f, thumb_side = cradle_frame(wrist)
        foot, top = spine - axis * BOOK_H / 2, spine + axis * BOOK_H / 2
        # the book on its own bone up its spine from the foot in her palm (put away
        # by scaling it to nothing there), each cover on a hinge bone along the
        # spine (cover_R the wing on her right) that shuts it
        b.joints["book"] = (foot, top, "hand_R")
        right = min((-1, 1), key=lambda sg: wing_frame(spine, sg, axis, across, facing)[2].x)
        for sign in (-1, 1):
            side = "R" if sign == right else "L"
            b.joints["cover_" + side] = (foot, top, "book")
            b.bm.verts.ensure_lookup_table()
            first = len(b.bm.verts)
            book_wing(b, spine, sign, axis, across, facing)
            b.bm.verts.ensure_lookup_table()
            reskin(b, b.bm.verts[first:], "cover_" + side)
        b.book_spine, b.book_axis, b.book_out = spine, axis, facing
        # the gold spine: the book's rounded back only, a half cylinder bulging out
        # behind (away from her) with its long edges sunk into the covers' outer
        # faces, its flat side hidden under the pages' curve, as tall as the covers
        back = spine - facing * SPINE_SINK
        # its section: the half-round back, then forward to the covers' inner faces
        # and across between them, so it fills the hinge and the covers' ends lie inside it
        half = [(SPINE_R * math.cos(math.pi * i / 10), -SPINE_R * math.sin(math.pi * i / 10)) for i in range(11)]
        for sg in (-1, 1):
            xw, nw, _ = wing_frame(spine, sg, axis, across, facing)
            q = xw * SPINE_HINGE + nw * COVER_T / 2
            half.append((q.dot(across), q.dot(facing)))
        half[11:] = sorted(half[11:], key=lambda c: c[0])
        # (1.2 mm proud of the covers at each end: its end caps flush with their top
        # and bottom faces would lie on them and flicker where the covers run into it)
        b.finish(b.slab(half, BOOK_H + .0024, toy3d.frame(back, axis, across)), "gold", "book", smooth=False)
        palm = cradle_hand(b, palm_at, spine, axis, across, facing, f, thumb_side)
        glove_cuff(b, wrist, fore_axis, palm, "R", palm_r=1.1 * S)      # flat into the palm under the spine
        bend_joint(b, "R", palm, wing_frame(spine, 1, axis, across, facing)[1])
        return
    axis, across, facing, finger_dir, palm_at, spine = (place_book(b, wrist) if BOOK_HOLD == "search"
                                                        else book_frame(wrist))
    b.joints["book"] = (spine - axis * BOOK_H / 2, spine + axis * BOOK_H / 2, "hand_R")   # (no hinges in these holds)
    book_wing(b, spine, -1, axis, across, facing)
    book_wing(b, spine, 1, axis, across, facing)
    b.book_spine, b.book_axis, b.book_out = spine, axis, facing
    b.finish(b.tube([spine - axis * (BOOK_H / 2 + .005), spine + axis * (BOOK_H / 2 + .005)],
                    .013, 10), "gold", "book")
    palm = open_hand(b, wrist, finger_dir, facing, "R", palm_at=palm_at)
    glove_cuff(b, wrist, fore_axis, palm, "R")


BOOK_TURN = {}
BOOK_H = .154 * BOOK_SCALE  # the book's height and width
BOOK_W = .087 * BOOK_SCALE
# the book's thickness: the one-handed hold's book is thinner (8 mm covers, 4 mm
# page layers), so the thumb reaches its top page at a thumb's length
COVER_T = .008 if BOOK_HOLD == "d" else .012
PAGE_T = .004 if BOOK_HOLD == "d" else .006
BOOK_PAGE_TOP = (COVER_T / 2 + PAGE_T + .0005 + 3 * .0015 if BOOK_HOLD == "d" else .023)   # the top page's surface off the cover's middle
PALM_HALF = 3.0 * S        # the glove's palm, wrist to knuckles, is twice this
GLOVE_CUFF = .015          # m of glove cuff showing past the under-sleeve's white cuff


def glove_cuff(b, wrist, fore_axis, palm, side, palm_r=.019):
    """A short glove cuff from just inside the white cuff to the palm's base,
    narrowing to palm_r where it meets the palm."""
    b.finish(b.tube([wrist - fore_axis * GLOVE_CUFF, wrist, palm], .019, 8, rs=[.021, .020, palm_r]),
             "mauve", "hand_" + side)


def build_arms(b):
    build_arm(b, "R", ARM_R)
    build_arm(b, "L", ARM_L)
    build_book_and_grip(b)
    # Character-left hand is the blessing gesture; steam/sparkles remain in Godot.
    # palm up, the fingers on along the forearm and tipped up a little
    fore_l = (ARM_L[2] - ARM_L[1]).normalized()
    # the concept's blessing: palm up, fingers spread
    palm = open_hand(b, ARM_L[2], (fore_l + Vector((0, -.35, .25))).normalized(), (0, 0, 1), "L", spread=14.0)
    glove_cuff(b, ARM_L[2], fore_l, palm, "L")
    bend_joint(b, "L", palm, Vector((0, 0, 1)))


BEND_LENGTH = .05          # m: the bend bones' length, out of the palm


def bend_joint(b, side, palm, palm_n):
    """An effect bone (bend_R / bend_L, no mesh) from the palm's middle out along
    its normal: the path Godot draws her bent tea along."""
    b.joints["bend_" + side] = (palm, palm + palm_n.normalized() * BEND_LENGTH, "hand_" + side)


def reskin(b, verts, bone):
    """Skin verts wholly to one bone."""
    i = b.bone_index(bone)
    for v in verts:
        dv = v[b.deform]
        dv.clear()
        dv[i] = 1.0


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
    for k in (-1, 1):                        # gold studs on the strap either side of the buckle, half sunk
        stud = strap + side * k * .022 + Vector((0, -.011, .001))
        b.finish(b.sphere(stud, .0045, 8, 4, (1, .7, 1)), "gold", part)


def build_leg(b, side, sx):
    hip, knee, ankle = P(CX + sx * 8, 90), P(CX + sx * 9, 107, -.002), P(CX + sx * 11, 118)
    thigh, shin, foot = "thigh_" + side, "shin_" + side, "foot_" + side
    b.joints[thigh] = (hip, knee, "hips")
    b.joints[shin] = (knee, ankle, thigh)
    toe = ankle + Vector((0, -.070, -.004))
    b.joints[foot] = (ankle, toe, shin)
    b.finish(b.tube([hip, hip.lerp(knee, .48), knee], .029, 10,
                    rs=[.033, .030, .027]), "mauve", thigh)
    b.finish(b.sphere(knee, .028, 10, 6), "cream", shin)       # a plain knee ball closing the joint
    b.finish(b.tube([knee, knee.lerp(ankle, .5), ankle], .024, 10,
                    rs=[.027, .024, .021]), "cream", shin)
    b.finish(b.ring(ankle + Vector((0, 0, .010)), (0, 0, 1), .022, .038, .018, 12),
             "gold", foot, smooth=False)
    build_shoe(b, Vector((ankle.x, ankle.y, 0)), ankle, foot)


def build_mesh():
    b = Builder()
    b.atlas = Atlas()
    build_torso(b)
    robe = build_robe(b)
    build_coat_layers(b)
    mantle = build_mantle(b)
    build_saucer_collar(b)
    cape = build_cape(b)
    build_belt_and_tabard(b)
    build_brooch(b)
    build_gear(b)
    build_head(b)
    build_arms(b)
    build_leg(b, "R", -1)
    build_leg(b, "L", 1)
    toy3d.follow_limbs(b, robe, H(BELT_BOTTOM),
                       {"thigh_R": (P(CX - 8, 90), P(CX - 9, 107)),
                        "thigh_L": (P(CX + 8, 90), P(CX + 9, 107))},
                       body=("hips",), reach=13, fade=7, pin=7)
    # the mantle over each sleeve's top lifts with the upper arm under it
    toy3d.follow_limbs(b, mantle, H(MANTLE_TOP),
                       {"upperarm_R": ARM_R[:2], "upperarm_L": ARM_L[:2]},
                       body=("chest",), reach=21, fade=9, pin=5)
    mantle_edges(b, mantle)
    pin_cape_to_mantle(b, cape)
    b.atlas.finish(b)
    b.colliders = sleeve_colliders(b)
    b.chains.update({"sleeve_" + sd: ["sleeve_1_" + sd, "sleeve_2_" + sd] for sd in ("R", "L")})
    with open(COLLIDERS, "w", encoding="utf-8") as f:
        # "chains": what settle() hangs in the clips; "springs": every cloth chain
        # Godot's spring bones move (the skirts, cape columns and mantle edges stay
        # at rest in the clips)
        springs = dict(b.chains)
        springs.update({f"skirt_{sd}": [f"skirt_{sd}_1", f"skirt_{sd}_2"] for sd in SKIRT_CHAINS})
        springs.update({f"cape{sd}": [f"cape{sd}_{i}" for i in (1, 2, 3)] for sd in ("_L", "", "_R")})
        springs.update({f"mantle_{sd}": [f"mantle_{sd}"] for sd in MANTLE_EDGES})
        json.dump({"capsules": b.colliders, "chains": b.chains, "springs": springs,
                   "tea": {"bone": "tea", "max_tilt": TEA_MAX_TILT, "radius": TEA_R, "uv2_y": 3}}, f, indent=1)
    return b


def build_teacup_v2():
    """Build (and rig) the v2 model; returns (obj, tris per part, rest clip report)."""
    toy3d.configure(CHAR)
    for name in ("Cube", "Camera", "Light"):     # Blender's startup scene, in a fresh headless run
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    REST_CLEAR.clear()
    obj, tris, rest = toy3d.build(build_mesh)
    with open(COLLIDERS, encoding="utf-8") as f:
        obj["colliders"] = f.read()
    # scaled in clips: the book put away to nothing in her palm, the tea drained away
    obj.parent["scaled_bones"] = ["book", "tea"]
    return obj, tris, rest


def linear_material(obj):
    """The same material sampling its atlas Linear instead of Closest (the palette
    swatches are 128 px cells sampled in the middle, so their colours stay exact)."""
    base = bpy.data.materials[CHAR.object_name]
    mat = bpy.data.materials.get(CHAR.object_name + "Linear")
    if mat:
        bpy.data.materials.remove(mat)
    mat = base.copy()
    mat.name = CHAR.object_name + "Linear"
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE":
            node.interpolation = "Linear"
    return mat


def validate_mesh(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    nonmanifold = sum(1 for e in bm.edges if not e.is_manifold)
    loose = sum(1 for v in bm.verts if not v.link_faces)
    bm.free()
    bones = obj.parent.data.bones if obj.parent else ()
    # (a vert with no weight at all stays frozen at rest however the rig moves)
    unweighted = sum(1 for v in obj.data.vertices if sum(g.weight for g in v.groups) < 1e-4)
    return {"verts": len(obj.data.vertices), "tris": len(obj.data.polygons),
            "nonmanifold_edges": nonmanifold, "loose_verts": loose, "unweighted_verts": unweighted,
            "groups_without_bone": [g.name for g in obj.vertex_groups if g.name not in bones],
            "rest_clips": {k: v for k, v in toy3d.clip_report(obj).items() if v},
            "island_gaps": [(g, tuple(round(x, 4) for x in c), round(d, 4))
                            for g, c, d in toy3d.island_gaps(obj)]}


# -- sleeves in motion: settle() and the elbow test --------------------------------
#
# Pose format as tools/toyanim.py: {bone: {"rot": (x, y, z) degrees about world
# axes at the bone's head, "loc": (x, y, z)}}. settle() is the hook a future
# animate script passes to toyanim.animate: it poses the rig (IK included), then
# hangs each sleeve's chain with gravity from where the forearm put it and
# pushes it out of the collider capsules.

SLEEVE_MARGIN = .022       # how far outside a capsule a drape link's tip stays: the drape's inner layer, folds and a gap


def apply_pose(rig, pose):
    """As toyanim.apply_pose: reset every bone, then set the pose ("shrink" puts
    the book away and drains the tea)."""
    from mathutils import Euler
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    for name, chans in pose.items():
        pb = rig.pose.bones[name]
        rest = pb.bone.matrix_local.to_quaternion()
        if "rot" in chans:
            q = Euler([math.radians(a) for a in chans["rot"]], "XYZ").to_quaternion()
            pb.rotation_quaternion = rest.inverted() @ q @ rest
        if "loc" in chans:
            pb.location = rest.inverted() @ Vector(chans["loc"])
        if "shrink" in chans:
            pb.scale = tuple(1.0 - k for k in chans["shrink"])
    bpy.context.view_layer.update()


def colliders_of(rig):
    toy = json.loads(rig.children[0]["colliders"])
    toy = toy["capsules"] if isinstance(toy, dict) else toy
    out = []
    for c in toy:
        pb = rig.pose.bones[c["bone"]]
        m = pb.matrix @ pb.bone.matrix_local.inverted()
        out.append((m @ Vector(c["head"]), m @ Vector(c["tail"]), c["radius"]))
    return out


CHAIN_MARGIN = {"sleeve": SLEEVE_MARGIN, "cord": .004, "tassel": .004}
REST_CLEAR = {}            # (rig, bone, capsule) -> how far its tip lies from the capsule's axis at rest


def push_out(head, tip, caps, margin, allowed):
    """Move a link's tip out of every capsule (twice round, for corners), keeping
    its length from head; allowed[i] caps how far out capsule i may push it (no
    further than the tip already lies at rest)."""
    length = (tip - head).length
    for _ in range(2):
        for i, (a, c, r) in enumerate(caps):
            ab = c - a
            t = max(0.0, min(1.0, (tip - a).dot(ab) / max(ab.length_squared, 1e-12)))
            q = a + ab * t
            off = tip - q
            lim = min(r + margin, allowed[i])
            if off.length < lim:
                n = off.normalized() if off.length > 1e-6 else Vector((0, -1, 0))
                tip = q + n * lim
                tip = head + (tip - head).normalized() * length
    return tip


def chains_of(rig):
    toy = json.loads(rig.children[0]["colliders"])
    return toy.get("chains", {}) if isinstance(toy, dict) else {}


def rest_clear(rig, caps):
    """Each chain link's tip's distance from each capsule's axis in the rest pose."""
    apply_pose(rig, {})
    for names in chains_of(rig).values():
        for nm in names:
            tip = rig.pose.bones[nm].tail
            for i, (a, c, r) in enumerate(caps):
                ab = c - a
                t = max(0.0, min(1.0, (tip - a).dot(ab) / max(ab.length_squared, 1e-12)))
                REST_CLEAR[(rig.name, nm, i)] = (tip - (a + ab * t)).length


def settle(pose, rig=None, spin=0.0):
    """Every hanging chain (the sleeves' drapes, the brooch cords, the tassels)
    hangs with gravity: each link back to its built, hanging direction wherever
    its parent has carried its top, and pushed out of the collider capsules
    (forearms, hands, book, torso, coat skirt, tabard, thighs). spin (degrees) is
    how far her whole body is turned about the vertical as one (a turn on the
    spot): the cords and tassels lying on the coat turn their hang with it."""
    from mathutils import Quaternion
    rig = rig or bpy.data.objects[CHAR.object_name + "Rig"]
    turn = Quaternion(Vector((0, 0, 1)), math.radians(spin))
    chains = chains_of(rig)
    links = {nm for names in chains.values() for nm in names}
    pose = {k: dict(v) for k, v in pose.items() if k not in links}
    if not any(k[0] == rig.name for k in REST_CLEAR):
        rest_clear(rig, colliders_of(rig))
    apply_pose(rig, pose)
    if "bell_R" in rig.pose.bones:
        pose.update(slide_bells(rig))
        apply_pose(rig, pose)
    caps = colliders_of(rig)
    for chain, names in chains.items():
        kind = chain.split("_")[0]
        margin = CHAIN_MARGIN[kind]
        for link in names:
            pb = rig.pose.bones[link]
            bone = pb.bone
            rest_dir = (bone.tail_local - bone.head_local).normalized()
            if kind in ("cord", "tassel"):
                rest_dir = turn @ rest_dir
            head, cur_tail = pb.head.copy(), pb.tail.copy()
            allowed = [REST_CLEAR.get((rig.name, link, i), math.inf) for i in range(len(caps))]
            tip = push_out(head, head + rest_dir * bone.length, caps, margin, allowed)
            parent = pb.parent
            d_p = (parent.matrix.to_quaternion() @ parent.bone.matrix_local.to_quaternion().inverted())
            c = (cur_tail - head).normalized().rotation_difference((tip - head).normalized())
            q = d_p.inverted() @ c @ d_p
            if kind == "sleeve":        # a raised arm's drape is partly held by the bell (DRAPE_HOLD)
                q = q.slerp(Quaternion(), DRAPE_HOLD * arm_rise(rig, link[-1]))
                cap = math.radians(drape_swing(rig, link[-1]))   # and swings only so far off the bell
                if q.angle > cap:
                    q = Quaternion().slerp(q, cap / q.angle)
            pose[link] = {"rot": tuple(math.degrees(a) for a in q.to_euler("XYZ"))}
            apply_pose(rig, pose)
    if "tea" in rig.pose.bones:      # (a clip's tea level, "loc", and draining, "shrink", stay)
        pose["tea"] = dict(pose.get("tea", {}), **level_tea(rig))
        apply_pose(rig, pose)
    return pose


BELL_SLIDE = .055         # m a bell slides back down a forearm pointing straight up
# On a raised arm the drape, attached all along the forearm's underside, would fold
# back across it hung straight down from the wrist end: it is held this share of the
# way to where the bell carries it (the owner's pick, 2026-10-11: it still mostly
# falls, angled a little out from the arm)
DRAPE_HOLD = .45
# The drape is sewn along the forearm's underside, so it can't swing freely: each
# link turns at most DRAPE_SWING (degrees) from where the bell holds it while the
# forearm is level or raised (further, it folds back through the under-sleeve),
# loosening to DRAPE_SWING_LOW as the forearm hangs down (it then falls clear of
# the arm, away from the robes); Godot's spring bones keep the same limits
DRAPE_SWING, DRAPE_SWING_LOW = 20.0, 60.0


def drape_swing(rig, side):
    fa = rig.pose.bones["forearm_" + side]
    down = -(fa.tail - fa.head).normalized().z
    return DRAPE_SWING + (DRAPE_SWING_LOW - DRAPE_SWING) * smoothstep(down / .6)


def arm_rise(rig, side):
    """How far a forearm is raised from its built angle toward straight up (0..1)."""
    fa = rig.pose.bones["forearm_" + side]
    axis = (fa.tail - fa.head).normalized()
    axis0 = (fa.bone.tail_local - fa.bone.head_local).normalized()
    return smoothstep((axis.z - axis0.z) / (1.0 - axis0.z))


def slide_bells(rig):
    """Each bell sleeve under gravity: as the forearm rises past its built angle it
    slides back down it toward the elbow (up to BELL_SLIDE pointing straight up,
    gathering there, the cuff coming out). Returns the bell bones' poses (in their
    rest frames, so they ride the forearm). (Turning it about the forearm to hang
    its slack downward was tried: it barely helped raised arms and swung the bell
    into the robes on a forearm pointing down.)"""
    out = {}
    for side in ("R", "L"):
        pb = rig.pose.bones["bell_" + side]
        axis0 = (pb.bone.tail_local - pb.bone.head_local).normalized()
        out["bell_" + side] = {"loc": tuple(-axis0 * BELL_SLIDE * arm_rise(rig, side))}
    return out


def level_tea(rig):
    """The tea bone's pose: its surface turned back level with the world (only the
    cup's tilt is undone, not its turn), at most TEA_MAX_TILT off the cup's own tilt."""
    from mathutils import Quaternion
    parent = rig.pose.bones["tea"].parent
    d_p = parent.matrix.to_quaternion() @ parent.bone.matrix_local.to_quaternion().inverted()
    up = d_p @ Vector((0, 0, 1))                      # the cup's tilted up
    angle = up.angle(Vector((0, 0, 1)), 0.0)
    if angle < 1e-6:
        return {"rot": (0.0, 0.0, 0.0)}
    hinge = up.cross(Vector((0, 0, 1))).normalized()
    c = Quaternion(hinge, min(angle, math.radians(TEA_MAX_TILT)))   # world change toward level
    q = d_p.inverted() @ c @ d_p
    return {"rot": tuple(math.degrees(a) for a in q.to_euler("XYZ"))}


def elbow_test(obj, bends=(40, 60, 90, 120, 150)):
    """Bend both elbows (FK, IK off) to each angle between upper arm and forearm
    (0 straight), settle the sleeves and report clipping per bend."""
    from mathutils import Quaternion
    rig = obj.parent
    toy3d.mute_ik(rig, True)
    out = {}
    for bend in bends:
        pose = {}
        for side, (sh, el, wr) in (("R", ARM_R), ("L", ARM_L)):
            u, f = (el - sh).normalized(), (wr - el).normalized()
            hinge = u.cross(f).normalized()
            rest = math.degrees(u.angle(f))
            q = Quaternion(hinge, math.radians(bend - rest))
            pose["forearm_" + side] = {"rot": tuple(math.degrees(a) for a in q.to_euler("XYZ"))}
        settle(pose, rig)
        out[bend] = {k: v for k, v in toy3d.clip_report(obj, evaluated=True).items() if v}
    apply_pose(rig, {})
    toy3d.mute_ik(rig, False)
    bpy.context.view_layer.update()
    return out


# -- side-by-side comparison renders ------------------------------------------------

V1_SCRIPT = os.path.join(_TOOLS, "build_teacup_cleric_3d.py")
CONCEPT = os.path.join(toy3d.ROOT, "assets", "models", "teacup", "source", "concept_reference.png")
CZ = (GROUND - 64) * S                 # the 128 px frame's middle height
CXM = (64 - CX) * S
# name: camera, target, ortho scale (None = perspective), resolution
SHOTS = {
    "front": ((CXM, -5, CZ), (CXM, 0, CZ), 1.06, 768),
    "3q": ((-2.8, -4.4, 2.3), (0, 0, .43), 1.06, 768),
    "side": ((5, 0, CZ), (0, 0, CZ), 1.06, 768),
    "back": ((2.4, 5.2, 2.1), (0, 0, .43), 1.06, 768),
    "128": ((CXM, -5, CZ), (CXM, 0, CZ), 1.0, 128),
    "cup": ((-0.9, -3.0, 1.55), (.02, 0, .74), .42, 768),
    "book": ((-1.6, -3.2, 1.2), (-.21, -.14, .54), .36, 768),
    "sleeve_L": ((1.9, -3.0, .9), (.25, 0, .40), .50, 768),
    "sleeve_R": ((-1.9, -3.0, .9), (-.25, 0, .40), .50, 768),
    "tabard": ((0, -5, .42), (0, 0, .42), .56, 768),
    "hem": ((-.6, -5, .18), (0, 0, .18), .60, 768),
    "under_shoulder_R": ((-1.3, -1.0, -.6), (-.18, -.02, .52), .42, 768),
    "under_shoulder_L": ((1.3, -1.0, -.6), (.18, -.02, .52), .42, 768),
    "book_grip": ((-1.2, -2.4, .25), (-.24, -.12, .52), .30, 768),
    "handle": ((1.8, -1.2, .95), (.18, 0, .74), .30, 768),
    "tabard_front": ((0, -5, .48), (0, 0, .48), .30, 768),
    "cords": ((-1.4, -4.6, .62), (0, -.06, .45), .34, 768),
}
COMPOSITE = r'''
import sys
from PIL import Image, ImageDraw
out, label_h, *pairs = sys.argv[1:]
label_h = int(label_h)
ims = []
for p in pairs:
    title, path = p.split("=", 1)
    im = Image.open(path).convert("RGBA")
    if im.width < 300:
        im = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    ims.append((title, im))
h = max(im.height for _, im in ims)
W = sum(im.width for _, im in ims)
sheet = Image.new("RGBA", (W, h + label_h), (27, 30, 36, 255))
d = ImageDraw.Draw(sheet)
x = 0
for title, im in ims:
    sheet.alpha_composite(im, (x, label_h + (h - im.height) // 2))
    d.text((x + 12, 8), title, fill=(235, 235, 235, 255))
    x += im.width
sheet.convert("RGB").save(out)
'''


def build_v1():
    """Build the v1 approval model beside v2 (its own script, unchanged)."""
    ns = {"__name__": "teacup_v1", "__file__": V1_SCRIPT}
    exec(compile(open(V1_SCRIPT, encoding="utf-8").read(), V1_SCRIPT, "exec"), ns)
    # its palette images go to a scratch folder, never over v1's own outputs
    ns["CHAR"].src_dir = ns["CHAR"].out_dir = os.path.join(V2_DIR, "_compare", "v1")
    obj, _ = ns["build_preview"]()
    toy3d.configure(CHAR)
    return obj


def render_compare(v2, v1=None, tag="", shots=None, linear=True):
    """Render v1 and v2 (and v2 with Linear filtering) alone, each shot framed the
    same, then put them side by side: source/v2/compare_<shot><tag>.png (the
    front also shows the concept) and compare_linear_<shot>.png."""
    v1 = v1 or bpy.data.objects.get("TeacupCleric") or build_v1()
    toy3d.add_outline(v1)
    shoot_raw = toy3d.preview_camera(v2)
    sc = bpy.context.scene
    col = v2.users_collection[0]
    if bpy.data.objects.get(CHAR.object_name + "PreviewFill") is None:
        fill = bpy.data.objects.new(CHAR.object_name + "PreviewFill",
                                    bpy.data.lights.new(CHAR.object_name + "PreviewFill", "SUN"))
        col.objects.link(fill)
        fill.data.energy = .55
        fill.rotation_euler = (math.radians(-35), math.radians(15), math.radians(145))
    tmp = os.path.join(V2_DIR, "_compare")
    os.makedirs(tmp, exist_ok=True)
    closest = v2.data.materials[0]
    lin = linear_material(v2) if linear else None
    rig2 = v2.parent
    hidden = {}

    def show(only):
        for o in (v1, v2, rig2):
            if o is None:
                continue
            hide = o is not only and not (o is rig2 and only is v2)
            hidden[o.name] = hide
            o.hide_render = hide

    out = []
    for name in shots or SHOTS:
        loc, target, ortho, res = SHOTS[name]
        width = .009 if res == 128 else .006
        aa = 0.0 if res == 128 else 1.5
        files = []
        for who, obj, mat in (("v1", v1, None), ("v2", v2, closest), ("v2 linear", v2, lin)):
            if who == "v2 linear" and not lin:
                continue
            show(obj)
            if mat is not None:
                v2.data.materials[0] = mat
            path = os.path.join(tmp, f"{who.replace(' ', '_')}_{name}.png")
            shoot_raw(os.path.relpath(path, CHAR.src_dir), loc, target, ortho=ortho, res=res, width=width, aa=aa)
            files.append((who, path))
        v2.data.materials[0] = closest
        pairs = [f"{who}={p}" for who, p in files if who != "v2 linear"]
        if name == "front":
            pairs.insert(0, f"concept={CONCEPT_CROP}")
        dest = os.path.join(V2_DIR, f"compare_{name}{tag}.png")
        subprocess.run([ATLAS_PYTHON, "-c", COMPOSITE, dest, "28"] + pairs, check=True)
        out.append(dest)
        if lin:
            dest = os.path.join(V2_DIR, f"compare_linear_{name}{tag}.png")
            subprocess.run([ATLAS_PYTHON, "-c", COMPOSITE, dest, "28"]
                           + [f"v2 closest={files[1][1]}", f"v2 linear={files[2][1]}"], check=True)
            out.append(dest)
    for o in (v1, v2, rig2):
        if o is not None:
            o.hide_render = False
    return out


# The concept's stance, posed through the rig (FK) with the sleeves settled: the
# arms out to the sides, so the drapes' outer panels face the front as they will
# in an idle clip. The built pose stays neutral (AGENTS.md).
CONCEPT_POSE_NEUTRAL = {      # (the stance from the neutral pose, for TEACUP_ARM_POSE=neutral)
    "upperarm_R": {"rot": (0.0, 28.0, 0.0)}, "upperarm_L": {"rot": (0.0, -28.0, 0.0)},
    "forearm_R": {"rot": (0.0, 0.0, -42.0)}, "forearm_L": {"rot": (0.0, 0.0, 48.0)},
}


CONCEPT_POSE = CONCEPT_POSE_NEUTRAL if ARM_POSE == "neutral" else {}


def render_posed(v2):
    """concept | v2 in the concept's stance, front and three-quarter:
    source/v2/compare_posed.png."""
    rig = v2.parent
    toy3d.mute_ik(rig, True)
    settle(CONCEPT_POSE, rig)
    shoot = toy3d.preview_camera(v2)
    tmp = os.path.join(V2_DIR, "_compare")
    v1 = bpy.data.objects.get("TeacupCleric")
    if v1:
        v1.hide_render = True
    files = []
    for name in ("front", "3q"):
        loc, target, ortho, res = SHOTS[name]
        path = os.path.join(tmp, f"v2_posed_{name}.png")
        shoot(os.path.relpath(path, CHAR.src_dir), loc, target, ortho=ortho, res=res)
        files.append(path)
    if v1:
        v1.hide_render = False
    apply_pose(rig, {})
    toy3d.mute_ik(rig, False)
    bpy.context.view_layer.update()
    dest = os.path.join(V2_DIR, "compare_posed.png")
    subprocess.run([ATLAS_PYTHON, "-c", COMPOSITE, dest, "28", f"concept={CONCEPT_CROP}",
                    f"v2 posed (front)={files[0]}", f"v2 posed (3/4)={files[1]}"], check=True)
    return dest


# -- unwrap quality: per-face stretch and a checker render -----------------------------

CHECKER_CM = 1.0           # checker squares, cm on the surface at the region's density


def uv_stretch(obj):
    """Per atlas region, how far each face's unwrap departs from its true size:
    the larger of its two principal stretches (UV metres per surface metre, and
    the inverse), minus one. Returns {region: (median, 90th percentile, max, share
    of faces over 10 %)} as fractions."""
    import statistics
    with open(LAYOUT, encoding="utf-8") as f:
        regions = json.load(f)["regions"]
    me = obj.data
    uv = me.uv_layers["UVMap"].data
    out = {}
    for poly in me.polygons:
        idx = list(poly.loop_indices)
        if len(idx) != 3:
            continue
        pts = [(uv[i].uv.x * ATLAS_SIZE, (1 - uv[i].uv.y) * ATLAS_SIZE) for i in idx]
        cx, cy = sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3
        name = next((n for n, r in regions.items()
                     if r["box"][0] <= cx < r["box"][2] and r["box"][1] <= cy < r["box"][3]), None)
        if name is None:
            continue
        k = regions[name]["density"]
        a, b, c = (me.vertices[me.loops[i].vertex_index].co for i in idx)
        e1, e2 = b - a, c - a
        if e1.length < 1e-6 or e1.cross(e2).length < 1e-10:
            continue
        x = e1.normalized()
        y = (e2 - x * e2.dot(x)).normalized()
        p1, p2 = (e1.dot(x), 0.0), (e2.dot(x), e2.dot(y))
        q1 = ((pts[1][0] - pts[0][0]) / k, (pts[1][1] - pts[0][1]) / k)
        q2 = ((pts[2][0] - pts[0][0]) / k, (pts[2][1] - pts[0][1]) / k)
        det = p1[0] * p2[1] - p2[0] * p1[1]
        if abs(det) < 1e-14:
            continue
        # J maps surface (x, y) to atlas metres: [q1 q2] = J [p1 p2]
        j11 = (q1[0] * p2[1] - q2[0] * p1[1]) / det
        j12 = (q2[0] * p1[0] - q1[0] * p2[0]) / det
        j21 = (q1[1] * p2[1] - q2[1] * p1[1]) / det
        j22 = (q2[1] * p1[0] - q1[1] * p2[0]) / det
        t = j11 * j11 + j12 * j12 + j21 * j21 + j22 * j22
        d = abs(j11 * j22 - j12 * j21)
        root = math.sqrt(max(0.0, t * t / 4 - d * d))
        smax, smin = math.sqrt(t / 2 + root), math.sqrt(max(1e-12, t / 2 - root))
        out.setdefault(name, []).append(max(smax, 1 / smin) - 1)
    res = {}
    for n, v in sorted(out.items()):
        v.sort()
        res[n] = (round(statistics.median(v), 3), round(v[int(.9 * (len(v) - 1))], 3), round(v[-1], 3),
                  round(sum(1 for s in v if s > .10) / len(v), 3))
    return res


def checker_material(obj):
    """The model's material with its atlas swapped for a checker laid in UV space,
    CHECKER_CM squares at about 1060 px per metre: a stretched unwrap shows as
    stretched squares."""
    mat = bpy.data.materials.get(CHAR.object_name + "Checker")
    if mat:
        bpy.data.materials.remove(mat)
    mat = bpy.data.materials.new(CHAR.object_name + "Checker")
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexChecker")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    tex.inputs["Scale"].default_value = ATLAS_SIZE / (1060 * CHECKER_CM / 100) / 2
    tex.inputs["Color1"].default_value = (0.9, 0.9, 0.85, 1)
    tex.inputs["Color2"].default_value = (0.12, 0.25, 0.6, 1)
    nt.links.new(coord.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Roughness"].default_value = .8
    return mat


CHECKER_SHOTS = {
    "checker_sleeve_R": ((-2.6, -1.6, .9), (-.25, -.04, .44), .34, 768),
    "checker_sleeve_L": ((2.6, -1.6, .9), (.27, -.04, .44), .34, 768),
    "checker_under": ((-1.3, -1.0, -.6), (-.18, -.02, .52), .42, 768),
    "checker_back": ((-1.9, 2.2, 1.0), (-.24, 0, .44), .34, 768),
}


def render_checker(v2, tag):
    """Checker renders of the sleeves: source/v2/checker_<tag>.png."""
    shoot = toy3d.preview_camera(v2)
    tmp = os.path.join(V2_DIR, "_compare")
    v1 = bpy.data.objects.get("TeacupCleric")
    if v1:
        v1.hide_render = True
    base = v2.data.materials[0]
    v2.data.materials[0] = checker_material(v2)
    files = []
    for name, (loc, target, ortho, res) in CHECKER_SHOTS.items():
        path = os.path.join(tmp, f"{name}_{tag}.png")
        shoot(os.path.relpath(path, CHAR.src_dir), loc, target, ortho=ortho, res=res)
        files.append(f"{name.replace('checker_', '')}={path}")
    # and in the concept's stance, where the sleeves' outsides face the front
    rig = v2.parent
    toy3d.mute_ik(rig, True)
    settle(CONCEPT_POSE, rig)
    for name, (loc, target, ortho) in (("posed_front", ((0, -5, .48), (0, 0, .48), .78)),
                                       ("posed_3q", ((-2.6, -4.2, 1.9), (0, 0, .46), .78))):
        path = os.path.join(tmp, f"checker_{name}_{tag}.png")
        shoot(os.path.relpath(path, CHAR.src_dir), loc, target, ortho=ortho, res=768)
        files.append(f"{name}={path}")
    apply_pose(rig, {})
    toy3d.mute_ik(rig, False)
    v2.data.materials[0] = base
    if v1:
        v1.hide_render = False
    dest = os.path.join(V2_DIR, f"checker_{tag}.png")
    subprocess.run([ATLAS_PYTHON, "-c", COMPOSITE, dest, "28"] + files, check=True)
    return dest


CONCEPT_CROP = os.path.join(V2_DIR, "_compare", "concept.png")


def crop_concept():
    """The concept sheet's character, cropped and scaled to the front shot's frame."""
    code = ("import sys\nfrom PIL import Image\n"
            "im = Image.open(sys.argv[1]).convert('RGBA').crop((10, 170, 470, 640))\n"
            "im.resize((752, 768), Image.NEAREST).save(sys.argv[2])\n")
    os.makedirs(os.path.dirname(CONCEPT_CROP), exist_ok=True)
    subprocess.run([ATLAS_PYTHON, "-c", code, CONCEPT, CONCEPT_CROP], check=True)


def report(obj, tris):
    print("tris", sum(tris.values()), {k: v for k, v in sorted(tris.items())})
    print("validation", validate_mesh(obj))
    print("atlas density px/m (across, down)", atlas_density(obj))
    print("uv stretch (median, p90, max, share over 10%)", uv_stretch(obj))


if __name__ == "__main__" and bpy.app.background:
    obj, tris, _ = build_teacup_v2()
    report(obj, tris)
    print("book turn (box overlaps, degrees off upright)", BOOK_TURN.get("turn"))
    rest_settle = settle({}, obj.parent)
    print("settle at rest (should be ~0)", {k: [round(x, 2) for x in v["rot"]] for k, v in rest_settle.items()})
    apply_pose(obj.parent, {})
    print("elbow bends", elbow_test(obj))
    toy3d.mute_ik(obj.parent, True)
    settle(CONCEPT_POSE, obj.parent)
    print("stance", ARM_POSE, {k: v for k, v in toy3d.clip_report(obj, evaluated=True).items() if v})
    apply_pose(obj.parent, {})
    toy3d.mute_ik(obj.parent, False)
    print("arms raised sideways 55", {k: v for k, v in toy3d.pose_test(obj, 55, "side").items() if v})
    print("arms swung forward 40", {k: v for k, v in toy3d.pose_test(obj, 40, "forward").items() if v})
    if not os.environ.get("TEACUP_CHECKS_ONLY"):     # set it to skip the renders while iterating
        crop_concept()
        print("renders", render_compare(obj))
        if ARM_POSE == "neutral":
            print("posed", render_posed(obj))
        print("checker", render_checker(obj, os.environ.get("TEACUP_CHECKER_TAG", "after")))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(V2_DIR, "teacup_cleric_v2_compare.blend"))
