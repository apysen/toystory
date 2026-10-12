"""Shared machinery for building the toys as 3D models in Blender.

Each character has a build script (tools/build_<name>_3d.py) that sets up a
`Character` with configure() and then builds its parts with a `Builder`; this
module holds everything that is the same for every toy:

  - sprite space: positions read straight off the 128 px idle frame (128 px =
    1 m, BattleSpace.PIXELS_PER_METRE) with the sprite's foot pivot on the
    origin, so the model stands at the card's size; the toy faces -Y
  - Builder: a single bmesh of closed parts, each painted with a palette swatch,
    tagged with its part name and skinned to its bone
  - one material: a 16x16 palette texture of the sprite's colours plus a
    matching emission texture, sampled nearest -> one draw call in Godot
  - the rig: deform bones from the parts' joints, IK controls for hands and
    feet and knee pole targets calibrated to leave the rest pose unchanged
  - checks, export (skinned GLB, deform bones only, IK baked) and previews

The agreed rules every character follows are kept in the build scripts'
docstrings and in Lamp's (tools/build_lamp_warden_3d.py), which this was
extracted from.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

try:
    ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
except NameError:
    ROOT = os.path.abspath(os.getcwd())

S = 1.0 / 128.0  # metres per sprite pixel


class Character:
    """What differs between toys. `name` is the file stem (assets/models/<folder>/<name>.glb)."""

    def __init__(self, name, folder, object_name, pivot, palette, part_bone=None, body_weights=None,
                 clip_checks=(), ik_limbs=(("forearm_R", "hand_R"), ("forearm_L", "hand_L"),
                                           ("shin_R", "foot_R"), ("shin_L", "foot_L")), detail=None,
                 detail_size=None):
        self.name = name
        self.object_name = object_name
        self.px, self.ground = pivot          # sprite foot pivot (x, y) in px
        self.palette = palette                # [(name, hex, emissive)], 16 entries
        self.swatch = {n: i for i, (n, _, _) in enumerate(palette)}
        self.part_bone = part_bone or {}      # part -> bone, or "body" to blend hips/spine/chest
        self.body_weights = body_weights      # z -> [(bone, weight)] for "body" parts
        self.clip_checks = list(clip_checks)  # part pairs that must never intersect
        self.ik_limbs = ik_limbs
        self.out_dir = os.path.join(ROOT, "assets", "models", folder)
        self.src_dir = os.path.join(self.out_dir, "source")
        # line art (a DETAIL_SIZE square PNG, drawn by a tools/draw_<name>_details.py
        # script) that the texture becomes an atlas of: the palette swatches in its
        # top-left PALETTE_PX corner, the art everywhere else; None keeps the plain
        # 16x16 palette
        self.detail = detail
        # the atlas's size in px (square); its palette corner scales with it
        self.detail_size = detail_size or DETAIL_SIZE


# The character being built (P, H, Builder and build use it). Every character
# configured is also kept by name, and each built object records its name, so
# functions given an object (checks, export, previews) use that object's own
# character even with several toys loaded in one Blender session. Both survive
# importlib.reload, which re-runs this module in the same namespace.
CFG: Character = globals().get("CFG")
CHARACTERS: dict = globals().get("CHARACTERS") or {}


def configure(character):
    global CFG
    CFG = character
    CHARACTERS[character.object_name] = character
    return character


def char_of(obj):
    """The character an object (the mesh or its rig) was built as."""
    name = obj.get("toy") or (obj.parent.get("toy") if obj.parent else None) or obj.name.removesuffix("Rig")
    return CHARACTERS.get(name, CFG)


def P(px, py, d=0.0):
    """Sprite pixel (px, py) at depth d metres -> world position."""
    return Vector(((px - CFG.px) * S, d, (CFG.ground - py) * S))


def H(py):
    """Height in metres of sprite row py."""
    return (CFG.ground - py) * S


DETAIL_SIZE = 1024   # px square of a detail atlas
PALETTE_PX = 256     # its top-left corner holds the 4x4 palette swatches


def atlas_size(character=None):
    """(atlas px, palette corner px) of a character's detail atlas."""
    size = (character or CFG).detail_size
    return size, PALETTE_PX * size // DETAIL_SIZE


def swatch_uv(name):
    i = CFG.swatch[name]
    size, pal = atlas_size()
    k = pal / size if CFG.detail else 1.0
    return Vector(((i % 4 + 0.5) / 4.0 * k, 1.0 - (i // 4 + 0.5) / 4.0 * k))


def detail_uv(x, y):
    """UV of pixel (x, y) of a character's detail atlas (origin top-left)."""
    size = atlas_size()[0]
    return Vector((x / size, 1.0 - y / size))


class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.sway = self.bm.loops.layers.uv.new("Sway")
        self.deform = self.bm.verts.layers.deform.new()
        self.part = self.bm.verts.layers.int.new("part")
        self.parts = []
        self.bones = []
        self.joints = {}  # bone -> (head, tail, parent bone)

    # -- part bookkeeping ----------------------------------------------------

    def bone_index(self, bone):
        if bone not in self.bones:
            self.bones.append(bone)
        return self.bones.index(bone)

    def finish(self, verts, colour, part, smooth=True):
        """Fix normals of a closed part, colour it, tag it and skin it to its bone."""
        faces = list({f for v in verts for f in v.link_faces})
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        if part not in self.parts:
            self.parts.append(part)
        pi = self.parts.index(part)
        bone = CFG.part_bone.get(part, part)
        for v in verts:
            v[self.part] = pi
            for name, w in (CFG.body_weights(v.co.z) if bone == "body" else [(bone, 1.0)]):
                v[self.deform][self.bone_index(name)] = w
        for f in faces:
            f.smooth = smooth
        self.paint(faces, colour)
        return faces

    def set_sway(self, faces, z_pin, z_free):
        """UV2.x: 0 at height z_pin rising to 1 at z_free."""
        for f in faces:
            for loop in f.loops:
                t = max(0.0, min(1.0, (z_pin - loop.vert.co.z) / (z_pin - z_free)))
                loop[self.sway].uv = (t ** 1.5, 0.0)

    def paint(self, faces, colour):
        uv = swatch_uv(colour)
        for f in faces:
            for loop in f.loops:
                loop[self.uv].uv = uv

    def map_detail(self, faces, region, uv_at, wrap=False):
        """Lay a region (x0, y0, x1, y1 px) of the detail atlas over faces:
        uv_at(co) gives each corner's place (u, v) in 0..1 across and down the
        region. With wrap, u runs round a tube: a face across the seam takes u
        past 1, so the region's art must carry on to u = 1.25."""
        x0, y0, x1, y1 = region
        span = (x1 - x0) / (1.25 if wrap else 1.0)
        for f in faces:
            uvs = [uv_at(loop.vert.co) for loop in f.loops]
            if wrap and max(u for u, _ in uvs) - min(u for u, _ in uvs) > 0.5:
                uvs = [(u + 1.0 if u < 0.5 else u, v) for u, v in uvs]
            for loop, (u, v) in zip(f.loops, uvs):
                loop[self.uv].uv = detail_uv(x0 + span * u, y0 + (y1 - y0) * max(0.0, min(1.0, v)))

    # -- primitives ----------------------------------------------------------

    def lathe(self, prof, segs, M, sy=1.0, loop=False, arc=None, warp=None):
        """Revolve (r, z) points around local Z. Returns (verts, bands, rings);
        bands[k] are the faces between profile points k and k+1."""
        bm = self.bm
        n = segs if arc is None else segs + 1
        rings, made = [], []
        for r, z in prof:
            if r <= 1e-6:
                p = Vector((0.0, 0.0, z))
                if warp:
                    p = warp(p, 0.0)
                v = bm.verts.new(M @ p)
                rings.append([v])
                made.append(v)
                continue
            ring = []
            for i in range(n):
                a = 2.0 * math.pi * i / segs if arc is None else arc[0] + (arc[1] - arc[0]) * i / segs
                p = Vector((r * math.cos(a), r * math.sin(a) * sy, z))
                if warp:
                    p = warp(p, a)
                v = bm.verts.new(M @ p)
                ring.append(v)
                made.append(v)
            rings.append(ring)
        pairs = list(zip(rings, rings[1:]))
        if loop:
            pairs.append((rings[-1], rings[0]))
        bands = []
        for A, B in pairs:
            band = []
            if len(A) > 1 or len(B) > 1:
                m = len(B) if len(A) == 1 else len(A)
                for i in range(m if arc is None else m - 1):
                    j = (i + 1) % m
                    if len(A) == 1:
                        q = (A[0], B[j], B[i])
                    elif len(B) == 1:
                        q = (A[i], A[j], B[0])
                    else:
                        q = (A[i], A[j], B[j], B[i])
                    band.append(bm.faces.new(q))
            bands.append(band)
        if arc is not None and loop:  # close the two open ends of a swept shell
            bm.faces.new([r[0] for r in rings])
            bm.faces.new([r[-1] for r in reversed(rings)])
        return made, bands, rings

    def tube(self, pts, r, segs=6, rs=None):
        """Capped tube through points; rs gives a radius per point."""
        bm = self.bm
        pts = [Vector(p) for p in pts]
        rings, made, prev_x = [], [], None
        for k, p in enumerate(pts):
            if k == 0:
                t = pts[1] - pts[0]
            elif k == len(pts) - 1:
                t = pts[-1] - pts[-2]
            else:
                t = (pts[k + 1] - p).normalized() + (p - pts[k - 1]).normalized()
            t.normalize()
            x = t.orthogonal() if prev_x is None else prev_x - t * prev_x.dot(t)
            x.normalize()
            prev_x = x
            y = t.cross(x)
            rr = rs[k] if rs else r
            ring = [bm.verts.new(p + (x * math.cos(a) + y * math.sin(a)) * rr)
                    for a in (2.0 * math.pi * i / segs for i in range(segs))]
            rings.append(ring)
            made += ring
        for A, B in zip(rings, rings[1:]):
            for i in range(segs):
                j = (i + 1) % segs
                bm.faces.new((A[i], A[j], B[j], B[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])
        return made

    def strap(self, pts, centre, w, h, normals=None):
        """Flat band through points, lying on a body whose vertical axis passes
        through centre (or with the surface's normals given): width w along the
        surface, thickness h off it."""
        bm = self.bm
        pts = [Vector(p) for p in pts]
        rings, made = [], []
        for k, p in enumerate(pts):
            t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            if normals:
                n = Vector(normals[k])
                n = (n - t * n.dot(t)).normalized()
            else:
                n = Vector((p.x - centre.x, p.y - centre.y, 0.0)).normalized()
            side = t.cross(n).normalized()
            ring = [bm.verts.new(p + side * sx * w / 2 + n * sz * h / 2)
                    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            rings.append(ring)
            made += ring
        for A, B in zip(rings, rings[1:]):
            for i in range(4):
                j = (i + 1) % 4
                bm.faces.new((A[i], A[j], B[j], B[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])
        return made

    def box(self, c, size, xdir=(1, 0, 0), zdir=(0, 0, 1)):
        M = frame(c, zdir, xdir) @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
        return bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)["verts"]

    def sphere(self, c, r, segs=8, rings=5, scale=(1, 1, 1)):
        prof = [(r * math.sin(math.pi * k / rings), -r * math.cos(math.pi * k / rings))
                for k in range(rings + 1)]
        M = Matrix.Translation(c) @ Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0))
        return self.lathe(prof, segs, M)[0]

    def ring(self, c, axis, r_in, r_out, h, segs=8):
        prof = [(r_out, -h / 2), (r_out, h / 2), (r_in, h / 2), (r_in, -h / 2)]
        return self.lathe(prof, segs, frame(c, axis), loop=True)[0]

    def slab(self, pts, th, M, zoff=0.0, warp=None):
        """Extrude a 2D outline (local XY, metres) by th along local Z."""
        bm = self.bm

        def at(x, y, z):
            p = Vector((x, y, z + zoff))
            return M @ (warp(p) if warp else p)

        top = [bm.verts.new(at(x, y, th / 2)) for x, y in pts]
        bot = [bm.verts.new(at(x, y, -th / 2)) for x, y in pts]
        bm.faces.new(top)
        bm.faces.new(list(reversed(bot)))
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((bot[i], bot[j], top[j], top[i]))
        return top + bot

    def sheet(self, grid_front, grid_back):
        """A thin closed cloth panel from two matching grids of points (rows of
        columns): front and back faces plus the four edge walls. Returns
        (verts, front_faces[j][i], back_faces)."""
        bm = self.bm
        F = [[bm.verts.new(p) for p in row] for row in grid_front]
        B = [[bm.verts.new(p) for p in row] for row in grid_back]
        rows, cols = len(F), len(F[0])
        fronts, backs = [], []
        for j in range(rows - 1):
            line = []
            for i in range(cols - 1):
                line.append(bm.faces.new((F[j][i], F[j][i + 1], F[j + 1][i + 1], F[j + 1][i])))
                backs.append(bm.faces.new((B[j][i], B[j + 1][i], B[j + 1][i + 1], B[j][i + 1])))
            fronts.append(line)
        for j in range(rows - 1):
            for i in (0, cols - 1):
                bm.faces.new((F[j][i], F[j + 1][i], B[j + 1][i], B[j][i]))
        for i in range(cols - 1):
            for j in (0, rows - 1):
                bm.faces.new((F[j][i], B[j][i], B[j][i + 1], F[j][i + 1]))
        return [v for row in F + B for v in row], fronts, backs


def frame(origin, zdir=(0, 0, 1), xhint=(1, 0, 0)):
    z = Vector(zdir).normalized()
    x = Vector(xhint) - z * Vector(xhint).dot(z)
    if x.length < 1e-6:
        x = z.orthogonal()
    x.normalize()
    y = z.cross(x)
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][0], m[i][1], m[i][2], m[i][3] = x[i], y[i], z[i], origin[i]
    return m


def vprof(points):
    """(r px, sprite y px) -> (r m, height m)."""
    return [(r * S, H(py)) for r, py in points]


def resample(pts, rows):
    """rows evenly spaced sprite heights along an (r, py) outline, py increasing,
    so cloth gets even rows to bend on."""
    y0, y1 = pts[0][1], pts[-1][1]
    out = []
    for k in range(rows):
        py = y0 + (y1 - y0) * k / (rows - 1)
        for (r0, a), (r1, c) in zip(pts, pts[1:]):
            if a <= py <= c + 1e-9:
                out.append((r0 + (r1 - r0) * (py - a) / (c - a), py))
                break
    return out


def smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def chain_weights(b, verts, top_z, length, centres, spread):
    """Skin cloth down a bone chain: each bone peaks at its centre (fraction
    of the way down the cloth) and fades out over spread."""
    ids = [(b.bone_index(name), c) for name, c in centres]
    for v in verts:
        t = (top_z - v.co.z) / length
        ws = [(i, max(0.0, 1.0 - abs(t - c) / spread)) for i, c in ids]
        total = sum(w for _, w in ws)
        if total <= 0:
            ws, total = [ids[-1][0:1] + (1.0,)], 1.0
        dv = v[b.deform]
        dv.clear()
        for i, w in ws:
            if w > 0:
                dv[i] = w / total


def follow_limbs(b, verts, top_z, arms, body=("hips", "spine", "chest"), reach=16.0, fade=10.0, pin=8.0,
                 probe=None):
    """Cloth over a limb (a mantle over the arms, a skirt over the thighs): verts
    close to the limb follow it, so raising an arm or kicking a leg moves the
    cloth on it, while the edge it hangs from (within pin px below top_z) stays
    on the body. arms: {bone: (joint, next joint)}. probe(co) gives the point
    to weigh a vert by instead of its own (gear lying on the cloth takes the
    cloth's weights at the point under it)."""
    body = {b.bone_index(n) for n in body}
    ids = {b.bone_index(bone): seg for bone, seg in arms.items()}

    def near(co, shoulder, elbow):
        seg = elbow - shoulder
        t = max(0.0, min(1.0, (co - shoulder).dot(seg) / seg.length_squared))
        return smoothstep((reach - (co - (shoulder + seg * t)).length / S) / fade)

    for v in verts:
        co = probe(v.co) if probe else v.co
        pinned = smoothstep((top_z - co.z) / (pin * S))
        ks = {i: near(co, *seg) * pinned for i, seg in ids.items()}
        total = sum(ks.values())
        if total > 1.0:
            ks = {i: k / total for i, k in ks.items()}
            total = 1.0
        dv = v[b.deform]
        for k in list(dv.keys()):
            if k in body:
                dv[k] *= 1.0 - total
        for i, k in ks.items():
            if k > 0.001:
                dv[i] = k


def hash01(i):
    """Repeatable pseudo-random 0..1 for index i (tears, spike lengths)."""
    x = math.sin(i * 12.9898 + 78.233) * 43758.5453
    return x - math.floor(x)


def grid_normals(mids, wrap=False, outward=None):
    """Per-point normals of a grid of points (rows of columns); outward(p) gives
    a rough outward direction so the whole grid faces the same way."""
    rows, cols = len(mids), len(mids[0])
    out = []
    for j in range(rows):
        row = []
        for i in range(cols):
            if wrap:
                a, c = mids[j][(i - 1) % cols], mids[j][(i + 1) % cols]
            else:
                a, c = mids[j][max(i - 1, 0)], mids[j][min(i + 1, cols - 1)]
            d, e = mids[max(j - 1, 0)][i], mids[min(j + 1, rows - 1)][i]
            n = (c - a).cross(e - d)
            row.append(n.normalized() if n.length > 1e-12 else Vector((0, 0, 1)))
        out.append(row)
    if outward and sum(n.dot(outward(mids[j][i])) for j, row in enumerate(out) for i, n in enumerate(row)) < 0:
        out = [[-n for n in row] for row in out]
    return out


def cloth(b, mids, norms, th, keep=None, wrap=False, holes=None):
    """A cloth panel th thick around a grid of mid-surface points (rows of
    columns, normals from grid_normals). keep(j, i) drops cells, which leaves
    tears: every edge of a kept cell that borders a dropped cell (or the
    panel's edge) gets a wall, so the panel stays a closed solid. holes is a
    set of cells to punch a ragged hole through (an irregular outline inside
    the cell, walled round); a dict {cell: n} makes a hole span n x n cells
    from that top-left cell. wrap joins the last column to the first (a hood).
    Returns (verts, fronts, backs): fronts maps each cell (j, i) to its front
    faces (the cloth round a hole is split among the cells it covers, so a
    cell's colour carries straight across the hole); backs holds every back face."""
    bm = b.bm
    rows, cols = len(mids), len(mids[0])
    ncols = cols if wrap else cols - 1
    kept = {(j, i) for j in range(rows - 1) for i in range(ncols) if keep is None or keep(j, i)}
    F, B = {}, {}

    def vert(j, i):
        i %= cols
        if (j, i) not in F:
            F[(j, i)] = bm.verts.new(mids[j][i] + norms[j][i] * th / 2)
            B[(j, i)] = bm.verts.new(mids[j][i] - norms[j][i] * th / 2)
        return (j, i)

    def has(j, i):
        if wrap:
            i %= cols
        return (j, i) in kept

    holes = holes if isinstance(holes, dict) else {h: 1 for h in (holes or ())}
    covered = {(j + dj, i + di) for (j, i), n in holes.items() for dj in range(n) for di in range(n)}
    extra = []
    fronts, backs = {}, {}
    for j, i in sorted(kept):
        c = [vert(j, i), vert(j, i + 1), vert(j + 1, i + 1), vert(j + 1, i)]
        if (j, i) in holes:
            n = holes[(j, i)]
            loop = ([(j, i + k) for k in range(n)] + [(j + k, i + n) for k in range(n)]
                    + [(j + n, i + n - k) for k in range(n)] + [(j + n - k, i) for k in range(n)])
            loop = [vert(*q) for q in loop]
            backs[(j, i)] = _ragged_hole(b, mids, norms, th, (j, i), n, loop, F, B, j * 131 + i * 17, extra,
                                         fronts)
        elif (j, i) in covered:
            pass
        else:
            fronts[(j, i)] = [bm.faces.new([F[k] for k in c])]
            backs[(j, i)] = bm.faces.new([B[k] for k in reversed(c)])
        for (p, q), nb in (((c[0], c[1]), (j - 1, i)), ((c[1], c[2]), (j, i + 1)),
                           ((c[2], c[3]), (j + 1, i)), ((c[3], c[0]), (j, i - 1))):
            if not has(*nb):
                bm.faces.new((F[p], F[q], B[q], B[p]))
    flat = {}
    for k, v in backs.items():
        if isinstance(v, list):
            flat.update({k + (n,): f for n, f in enumerate(v)})
        else:
            flat[k] = v
    return list(F.values()) + list(B.values()) + extra, fronts, flat


def _ragged_hole(b, mids, norms, th, origin, n, loop, F, B, seed, extra, fronts):
    """Fill the n x n cells from origin with cloth round an irregular hole:
    a jittered outline of points stitched to the block's edge loop (its grid
    points, in order) by walking both round by angle, the hole walled through.
    Each front face is filed under the cell it lies in. Returns the back faces."""
    bm = b.bm
    cols = len(mids[0])
    j0, i0 = origin

    def file(face, *uvs):  # file a front face under the cell its middle falls in
        u = sum(q[0] for q in uvs) / len(uvs)
        v = sum(q[1] for q in uvs) / len(uvs)
        cell = (j0 + min(int(v), n - 1), (i0 + min(int(u), n - 1)) % cols)
        fronts.setdefault(cell, []).append(face)

    def at(u, v):  # point and normal at (u, v) cells into the block
        cj, ci = min(int(v), n - 1), min(int(u), n - 1)
        fu, fv = u - ci, v - cj
        ja, jb, ia, ib = j0 + cj, j0 + cj + 1, (i0 + ci) % cols, (i0 + ci + 1) % cols
        w = ((1 - fu) * (1 - fv), fu * (1 - fv), fu * fv, (1 - fu) * fv)
        q = ((ja, ia), (ja, ib), (jb, ib), (jb, ia))
        p = sum((mids[a][c] * k for (a, c), k in zip(q, w)), Vector())
        nn = sum((norms[a][c] * k for (a, c), k in zip(q, w)), Vector()).normalized()
        return p, nn

    def angle(u, v):
        return math.atan2(v - n / 2, u - n / 2) % (2 * math.pi)

    inner = []
    for k in range(10):
        ang = 2 * math.pi * (k + 0.5 + 0.6 * (hash01(seed + k) - 0.5)) / 10
        rad = (0.24 + 0.2 * hash01(seed + 50 + k)) * n
        u, v = n / 2 + rad * math.cos(ang), n / 2 + rad * math.sin(ang)
        p, nn = at(u, v)
        pf, pb = bm.verts.new(p + nn * th / 2), bm.verts.new(p - nn * th / 2)
        extra += [pf, pb]
        inner.append((ang % (2 * math.pi), pf, pb, (u, v)))
    inner.sort(key=lambda q: q[0])
    # the block's edge loop, with each grid point's angle round the block centre
    m = len(loop)
    uv = ([(k, 0) for k in range(n)] + [(n, k) for k in range(n)]
          + [(n - k, n) for k in range(n)] + [(0, n - k) for k in range(n)])
    outer = sorted(((angle(u, v), loop[k], (u, v)) for k, (u, v) in enumerate(uv)), key=lambda q: q[0])

    backs = []
    # stitch: walk both loops once round, always advancing the one whose next
    # point comes first by angle
    oi = ii = 0
    two_pi = 2 * math.pi
    for _ in range(m + len(inner)):
        o0, o1 = outer[oi % m], outer[(oi + 1) % m]
        n0, n1 = inner[ii % len(inner)], inner[(ii + 1) % len(inner)]
        ao1 = o1[0] + two_pi * ((oi + 1) // m)
        an1 = n1[0] + two_pi * ((ii + 1) // len(inner))
        if ao1 <= an1 and oi < m:
            file(bm.faces.new((F[o0[1]], n0[1], F[o1[1]])), o0[2], n0[3], o1[2])
            backs.append(bm.faces.new((B[o0[1]], B[o1[1]], n0[2])))
            oi += 1
        else:
            file(bm.faces.new((F[o0[1]], n0[1], n1[1])), o0[2], n0[3], n1[3])
            backs.append(bm.faces.new((B[o0[1]], n1[2], n0[2])))
            ii += 1
    for k in range(len(inner)):                     # the hole's wall
        _, pf0, pb0, _ = inner[k]
        _, pf1, pb1, _ = inner[(k + 1) % len(inner)]
        bm.faces.new((pf0, pb0, pb1, pf1))
    return backs


def bandage(b, pts, rs, part, wraps, colours=("cream", "cream_shade"), segs=8, tilt=0.35):
    """A limb wrapped in strips of cloth: a ridged tube through pts with
    alternating bands slanting round it like a wound bandage."""
    pts = [Vector(p) for p in pts]
    n = wraps * 3
    path, radii = [], []
    for k in range(n + 1):
        t = k / n
        x = t * (len(pts) - 1)
        i = min(int(x), len(pts) - 2)
        path.append(pts[i].lerp(pts[i + 1], x - i))
        r = rs[i] + (rs[i + 1] - rs[i]) * (x - i)
        radii.append(r * (1.07 if k % 3 == 1 else 1.0))  # each wrap's edge stands proud
    faces = b.finish(b.tube(path, radii[0], segs, rs=radii), colours[0], part)
    axis = pts[-1] - pts[0]
    length = axis.length
    axis.normalize()
    side = axis.orthogonal().normalized()
    for f in faces:
        c = f.calc_center_median()
        t = (c - pts[0]).dot(axis) / length + tilt / wraps * (c - pts[0]).dot(side) / (radii[0] * 2)
        if int(math.floor(t * wraps * 2)) % 2:
            b.paint([f], colours[1])
    return faces


# -- hands ----------------------------------------------------------------------

def build_hand(b, grip, u, f, w, R, part, colour="steel", knuckle="steel_light", palm_colour=None):
    """A hand closed around a bar through grip along u, R clear of its axis.
    f runs from the wrist to the bar and the palm lies on side w, so the hand
    is right or left by which side w is. Fingers leave the knuckles heading
    along f and curl round the bar; the thumb comes round the wrist side over
    the top. palm_colour lets a glove differ from the fingers (fingerless)."""
    palm = grip + w * (R + 1.3 * S) - f * 0.6 * S
    b.finish(b.box(palm, (7.4 * S, 5.2 * S, 2.6 * S), xdir=u, zdir=w), palm_colour or colour, part, smooth=False)
    for k, off in enumerate((2.7, 0.9, -0.9, -2.7)):  # index finger nearest the thumb
        fr = (1.05 if 0 < k < 3 else 0.95) * S
        arc = [grip + u * off * S + (w * math.cos(t) + f * math.sin(t)) * (R + fr)
               for t in (math.radians(a) for a in (25, 70, 115, 160, 205))]
        b.finish(b.tube(arc, fr, 5, rs=[fr, fr, fr, fr * 0.92, fr * 0.82]), colour, part)
        b.finish(b.sphere(arc[1], fr * 1.15, 5, 3), knuckle, part)
    thumb = [grip + u * (3.6 + 0.6 * i) * S + (w * math.cos(t) - f * math.sin(t)) * (R + 1.0 * S)
             for i, t in enumerate(math.radians(a) for a in (10, 60, 110))]
    b.finish(b.tube(thumb, 1.15 * S, 5, rs=[1.2 * S, 1.1 * S, 0.9 * S]), colour, part)
    return palm


def grip_frame(elbow, grip, axis, side):
    """(u, f, w) for a hand of `side` ("R"/"L", the character's own) closing on a
    bar along `axis` at `grip`, with the forearm coming from `elbow`."""
    u = Vector(axis).normalized()
    if u.z < 0:
        u = -u
    f = grip - elbow
    f = (f - u * f.dot(u)).normalized()
    w = f.cross(u) if side == "R" else u.cross(f)  # palm side of the bar
    return u, f, w


# -- mesh, material, rig ------------------------------------------------------------

def finish_mesh(b):
    """Triangulate, count triangles per part and make the Blender mesh."""
    bm = b.bm
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="BEAUTY", ngon_method="BEAUTY")
    tris = {g: 0 for g in b.parts}
    for f in bm.faces:
        tris[b.parts[f.verts[0][b.part]]] += 1
    mesh = bpy.data.meshes.new(CFG.object_name)
    bm.to_mesh(mesh)
    bm.free()
    try:
        mesh.set_sharp_from_angle(angle=math.radians(40))
    except AttributeError:
        pass
    return mesh, tris


def detail_atlas(emissive_only):
    """Pixels (Blender order: rows bottom-up, RGBA floats) of a character's atlas:
    its detail art with the palette swatches in the top-left corner; for the glow
    texture, black but for the glowing swatches."""
    import numpy as np
    size, pal = atlas_size()
    art = bpy.data.images.load(CFG.detail, check_existing=False)
    try:
        px = np.array(art.pixels[:], dtype=np.float32).reshape(size, size, 4)
    finally:
        bpy.data.images.remove(art)
    px[..., 3] = 1.0
    if emissive_only:
        px[...] = (0.0, 0.0, 0.0, 1.0)
    cell = pal // 4
    for k, (_, hexv, emissive) in enumerate(CFG.palette):
        rgb = [int(hexv[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
        if emissive_only and not emissive:
            rgb = [0.0, 0.0, 0.0]
        top = size - (k // 4) * cell                 # rows count up from the bottom
        px[top - cell:top, (k % 4) * cell:(k % 4 + 1) * cell, :3] = rgb
    return px.ravel()


def make_material():
    def image(name, emissive_only):
        # always a new image: the GLB embeds the packed PNG, and repacking an image
        # left over from an earlier build in the same session can keep its old bytes
        # (a stale palette under new UVs paints parts the wrong colours)
        old = bpy.data.images.get(name)
        if old:
            bpy.data.images.remove(old)
        if CFG.detail:
            img = bpy.data.images.new(name, CFG.detail_size, CFG.detail_size, alpha=False)
            img.pixels = detail_atlas(emissive_only)
        else:
            img = bpy.data.images.new(name, 16, 16, alpha=False)
            px = []
            for row in range(16):
                for col in range(16):
                    _, hexv, emissive = CFG.palette[(3 - row // 4) * 4 + col // 4]
                    rgb = [int(hexv[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
                    if emissive_only and not emissive:
                        rgb = [0.0, 0.0, 0.0]
                    px += rgb + [1.0]
            img.pixels = px
        img.filepath_raw = os.path.join(CFG.src_dir, name + ".png")
        img.file_format = "PNG"
        img.save()
        img.pack()
        return img

    mat = bpy.data.materials.get(CFG.object_name) or bpy.data.materials.new(CFG.object_name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    base = nt.nodes.new("ShaderNodeTexImage")
    glow = nt.nodes.new("ShaderNodeTexImage")
    base.image, glow.image = image(CFG.name + "_palette", False), image(CFG.name + "_emission", True)
    base.interpolation = glow.interpolation = "Closest"
    nt.links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(glow.outputs["Color"], bsdf.inputs["Emission Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Emission Strength"].default_value = 0.6
    bsdf.inputs["Roughness"].default_value = 0.75
    return mat


def build(build_mesh, collection_name=None):
    """Clears the previous build, runs `build_mesh()` (-> Builder), makes the
    object, material and rig. Returns (obj, tris per part, rest clip report)."""
    collection_name = collection_name or CFG.object_name
    os.makedirs(CFG.src_dir, exist_ok=True)
    gdignore = os.path.join(CFG.src_dir, ".gdignore")
    if not os.path.exists(gdignore):
        open(gdignore, "w").close()
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for name in (CFG.object_name, CFG.object_name + "Rig"):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    bpy.context.view_layer.update()     # (else the view layer can still list the removed objects, as None)
    for coll in (bpy.data.meshes, bpy.data.armatures):
        for d in [d for d in coll if d.name.startswith(CFG.object_name) and d.users == 0]:
            coll.remove(d)
    col = bpy.data.collections.get(collection_name)
    if col is None:
        col = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(col)

    b = build_mesh()
    mesh, tris = finish_mesh(b)
    mesh.materials.append(make_material())
    obj = bpy.data.objects.new(CFG.object_name, mesh)
    col.objects.link(obj)
    obj["toy"] = CFG.object_name
    obj["parts"] = b.parts
    for bone in b.bones:
        obj.vertex_groups.new(name=bone)
    build_rig(obj, b.joints, col)
    stray = [g.name for g in obj.vertex_groups if g.name not in obj.parent.data.bones]
    assert not stray, f"parts skinned to bones that don't exist: {stray}"
    show_colours()
    return obj, tris, clip_report(obj)


KNEE_POLE_DIST = 0.3  # m from the knee to its pole target, along the knee's bend


def build_rig(obj, joints, col):
    """Armature: deform bones from joints, plus IK controls ik_* and knee pole
    targets pole_knee_* (children of root, not deforming, not exported) that
    drive the limbs, so feet stay planted, hands can be placed directly and
    knees can be pointed where a clip needs them."""
    data = bpy.data.armatures.new(CFG.object_name + "Rig")
    data.display_type = "STICK"
    rig = bpy.data.objects.new(CFG.object_name + "Rig", data)
    col.objects.link(rig)
    rig.show_in_front = True
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    rig.select_set(True)
    vl.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (head, tail, _) in joints.items():
        eb = data.edit_bones.new(name)
        eb.head, eb.tail = head, tail
    for name, (_, _, parent) in joints.items():
        if parent:
            data.edit_bones[name].parent = data.edit_bones[parent]
    for _, end in CFG.ik_limbs:
        src = data.edit_bones[end]
        eb = data.edit_bones.new("ik_" + end)
        eb.head, eb.tail, eb.roll = src.head, src.tail, src.roll
        eb.parent = data.edit_bones["root"]
        eb.use_deform = False
    for s in ("R", "L"):  # knee pole: out along the knee's rest bend
        if f"thigh_{s}" not in data.edit_bones:
            continue
        hip, knee, ankle = (data.edit_bones[f"thigh_{s}"].head.copy(), data.edit_bones[f"thigh_{s}"].tail.copy(),
                            data.edit_bones[f"shin_{s}"].tail.copy())
        axis = (ankle - hip).normalized()
        bend = knee - (hip + axis * (knee - hip).dot(axis))
        eb = data.edit_bones.new(f"pole_knee_{s}")
        eb.head = knee + bend.normalized() * KNEE_POLE_DIST
        eb.tail = eb.head + Vector((0, 0, 0.05))
        eb.parent = data.edit_bones["root"]
        eb.use_deform = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for mid, end in CFG.ik_limbs:
        ik = rig.pose.bones[mid].constraints.new("IK")
        ik.target, ik.subtarget, ik.chain_count = rig, "ik_" + end, 2
        cr = rig.pose.bones[end].constraints.new("COPY_ROTATION")
        cr.target, cr.subtarget = rig, "ik_" + end
        if mid.startswith("shin"):
            ik.pole_target, ik.pole_subtarget = rig, "pole_knee_" + mid[-1]
            calibrate_pole(rig, ik, mid)
    obj.parent = rig
    obj.modifiers.new("Armature", "ARMATURE").object = rig
    return rig


def calibrate_pole(rig, ik, shin):
    """Pick the IK pole angle that leaves the leg exactly at its rest pose."""
    thigh = rig.pose.bones[shin].parent
    rest = rig.data.bones[shin].matrix_local

    def error(deg):
        ik.pole_angle = math.radians(deg)
        bpy.context.view_layer.update()
        return (rig.pose.bones[shin].matrix.col[1].xyz - rest.col[1].xyz).length + \
               (thigh.matrix.col[0].xyz - rig.data.bones[thigh.name].matrix_local.col[0].xyz).length
    best = min(range(-180, 180, 5), key=error)
    fine = min((best + 0.25 * k for k in range(-20, 21)), key=error)
    ik.pole_angle = math.radians(fine)
    bpy.context.view_layer.update()


def mute_ik(rig, mute):
    for pb in rig.pose.bones:
        for c in pb.constraints:
            c.mute = mute


# -- checks, export, previews -------------------------------------------------------

def clip_report(obj, evaluated=False):
    """Intersecting triangle pairs per clip-check pair; evaluated=True tests the
    posed (armature-deformed) mesh."""
    from mathutils.bvhtree import BVHTree
    parts = list(obj["parts"])
    eo = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else None
    me = eo.to_mesh() if evaluated else obj.data
    tag = me.attributes["part"].data
    per = {}
    for poly in me.polygons:
        vs, fs = per.setdefault(parts[tag[poly.vertices[0]].value], ([], []))
        fs.append(list(range(len(vs), len(vs) + len(poly.vertices))))
        vs.extend(me.vertices[i].co.copy() for i in poly.vertices)
    if evaluated:
        eo.to_mesh_clear()
    trees = {g: BVHTree.FromPolygons(vs, fs) for g, (vs, fs) in per.items()}
    return {f"{a}/{c}": len(trees[a].overlap(trees[c])) for a, c in char_of(obj).clip_checks
            if a in trees and c in trees}


def _dist(tree, co):
    hit = tree.find_nearest(co)
    return hit[3] if hit[3] is not None else math.inf


def island_gaps(obj, tol=0.0015):
    """Groups of pieces that float off the model. Each loose piece of the rest mesh
    (a box, a ring, a strap, a cloth panel) joins every piece it touches or sinks
    into; the largest group is the body. Returns [(parts, centre, gap in m)] for
    every other group (a head on no neck, a satchel off its belt), largest gap
    first. Empty means everything on the model is attached to the body."""
    import bmesh as _bm
    from mathutils.bvhtree import BVHTree
    bm = _bm.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    parts = list(obj["parts"])
    tag = bm.verts.layers.int.get("part")
    cos = [v.co.copy() for v in bm.verts]
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        seen.add(v.index)
        while stack:
            u = stack.pop()
            isl.append(u)
            for e in u.link_edges:
                w = e.other_vert(u)
                if w.index not in seen:
                    seen.add(w.index)
                    stack.append(w)
        faces = {f for u in isl for f in u.link_faces}
        tree = BVHTree.FromPolygons(cos, [[u.index for u in f.verts] for f in faces])
        lo = Vector([min(u.co[a] for u in isl) for a in range(3)])
        hi = Vector([max(u.co[a] for u in isl) for a in range(3)])
        islands.append((isl, tree, lo, hi))

    def gap(a, b):
        (ia, ta, la, ha), (ib, tb, lb, hb) = islands[a], islands[b]
        if any(la[k] > hb[k] + tol or lb[k] > ha[k] + tol for k in range(3)):
            return math.inf
        if ta.overlap(tb):
            return 0.0
        return min(min(_dist(tb, u.co) for u in ia), min(_dist(ta, u.co) for u in ib))

    n = len(islands)
    group = list(range(n))

    def root(i):
        while group[i] != i:
            group[i] = group[group[i]]
            i = group[i]
        return i
    for a in range(n):
        for b in range(a + 1, n):
            if root(a) != root(b) and gap(a, b) <= tol:
                group[root(a)] = root(b)
    groups = {}
    for i in range(n):
        groups.setdefault(root(i), []).append(i)
    body = max(groups.values(), key=lambda g: sum(len(islands[i][0]) for i in g))
    out = []
    for g in groups.values():
        if g is body:
            continue
        verts = [u for i in g for u in islands[i][0]]
        names = sorted({parts[u[tag]] for u in verts}) if tag else ["?"]
        centre = sum((u.co for u in verts), Vector()) / len(verts)
        lo = Vector([min(u.co[a] for u in verts) for a in range(3)])
        hi = Vector([max(u.co[a] for u in verts) for a in range(3)])
        near = math.inf
        for j in body:
            _, tj, lj, hj = islands[j]
            if any(lo[k] > hj[k] + 0.05 or lj[k] > hi[k] + 0.05 for k in range(3)):
                continue
            near = min(near, min(_dist(tj, u.co) for u in verts))
        out.append((names, centre, near))
    bm.free()
    return sorted(out, key=lambda r: -r[2])


def show_colours():
    """Solid-mode viewports draw the palette texture instead of flat grey."""
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D" and space.shading.type == "SOLID":
                        space.shading.color_type = "TEXTURE"


def rig_actions(rig):
    """The actions keyed for this rig (their slot names it), so another toy's
    clips loaded in the same session never end up in this one's GLB."""
    return [a for a in bpy.data.actions if any(sl.identifier == "OB" + rig.name for sl in getattr(a, "slots", []))]


def export_glb(obj):
    """Mesh plus its armature -> a skinned GLB (Skeleton3D in Godot) with each of
    the rig's own actions as an animation, sampled per frame so the IK is baked
    in. The clips go out as one NLA track each (named after the clip), which
    leaves every other action in the file out of the export."""
    toy = char_of(obj)
    path = os.path.join(toy.out_dir, toy.name + ".glb")
    rig = obj.parent
    rig.animation_data_create()
    ad = rig.animation_data
    active = ad.action
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    for act in sorted(rig_actions(rig), key=lambda a: a.name):
        track = ad.nla_tracks.new()
        track.name = act.name.split("|")[-1]            # "StaplerRogue|idle" -> "idle"
        strip = track.strips.new(track.name, int(act.frame_range[0]), act)
        if hasattr(strip, "action_slot") and act.slots:
            strip.action_slot = act.slots[0]
    ad.action = None
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                                  export_apply=True, export_yup=True, export_skins=True,
                                  export_def_bones=True, export_animations=True,
                                  export_animation_mode="NLA_TRACKS", export_force_sampling=True,
                                  export_frame_step=1)
    finally:
        for t in list(ad.nla_tracks):
            ad.nla_tracks.remove(t)
        ad.action = active
    return path


# Bones a model's spring-bone cloth collides with in the game, when the rig has them:
# the limbs and the trunk, each a capsule along its bone. (Not Lamp's staff: its bone
# doesn't run along the pole; his lantern hangs out from the staff's bracket and its
# swing limit keeps it off the pole.)
SPRING_COLLIDERS = ("hips", "spine", "chest", "upperarm_L", "forearm_L", "upperarm_R", "forearm_R",
                    "thigh_L", "shin_L", "thigh_R", "shin_R")


def export_springs(obj, chains, radius_share=0.6):
    """<out_dir>/<name>_springs.json beside the GLB: what the game's spring bones
    (UnitSprings) are built from, in Godot's frame (x, z, -y; metres, rest pose).
    "springs" the cloth chains ({name: [bones root to tip]}), "bones" each chain bone's
    head and tail, and "capsules" a collider round each limb and the trunk
    (SPRING_COLLIDERS), along its bone, as thick as the mesh skinned mostly to it is
    at `radius_share` of its points (cloth hanging off a bone can't fatten it much).
    The game slims a capsule for a chain that rests inside it."""
    import json
    rig = obj.parent
    toy = char_of(obj)

    def godot(v):
        return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]

    bones = {}
    for chain in chains.values():
        for bone in chain:
            b = rig.data.bones[bone]
            bones[bone] = {"head": godot(b.head_local), "tail": godot(b.tail_local)}
    mesh = obj.data
    index = {g.index: g.name for g in obj.vertex_groups}
    near = {name: [] for name in SPRING_COLLIDERS}
    for v in mesh.vertices:
        best = max(v.groups, key=lambda g: g.weight, default=None)
        if best is None or best.weight < 0.6:
            continue
        name = index.get(best.group)
        if name in near:
            b = rig.data.bones[name]
            a, t = b.head_local, b.tail_local
            ab = t - a
            u = max(0.0, min(1.0, (v.co - a).dot(ab) / max(ab.length_squared, 1e-9)))
            near[name].append((v.co - (a + ab * u)).length)
    capsules = []
    for name, dists in near.items():
        if name not in rig.data.bones or len(dists) < 8:
            continue
        dists.sort()
        b = rig.data.bones[name]
        capsules.append({"name": name, "bone": name, "head": godot(b.head_local), "tail": godot(b.tail_local),
                         "radius": round(dists[int(len(dists) * radius_share)], 4)})
    path = os.path.join(toy.out_dir, toy.name + "_springs.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"springs": chains, "bones": bones, "capsules": capsules}, f, indent=1)
    return path


def add_outline(obj, width=0.006):
    """Inverted-hull outline in the sprite's outline colour, for previews."""
    name = char_of(obj).object_name + "Outline"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (0.003, 0.003, 0.004, 1.0)
    try:
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (0.003, 0.003, 0.004, 1.0)
        nt.links.new(em.outputs["Emission"], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    except AttributeError:
        pass
    mat.use_backface_culling = True
    if name not in obj.data.materials:
        obj.data.materials.append(mat)
    mod = obj.modifiers.get("Outline") or obj.modifiers.new("Outline", "SOLIDIFY")
    mod.thickness, mod.offset = width, 1.0
    mod.use_flip_normals, mod.use_rim = True, False
    mod.material_offset = 1
    mod.show_viewport = False


def preview_camera(obj):
    """Preview camera, lights and outline; returns shoot(name, loc, target, ...)."""
    sc = bpy.context.scene
    col = obj.users_collection[0]
    toy = char_of(obj)
    tag = toy.object_name
    cam = bpy.data.objects.get(tag + "PreviewCam")
    if cam is None:
        cam = bpy.data.objects.new(tag + "PreviewCam", bpy.data.cameras.new(tag + "PreviewCam"))
        col.objects.link(cam)
    if bpy.data.objects.get(tag + "PreviewSun") is None:
        sun = bpy.data.objects.new(tag + "PreviewSun", bpy.data.lights.new(tag + "PreviewSun", "SUN"))
        col.objects.link(sun)
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))
    if bpy.data.objects.get(tag + "PreviewRim") is None:
        rim = bpy.data.objects.new(tag + "PreviewRim", bpy.data.lights.new(tag + "PreviewRim", "SUN"))
        col.objects.link(rim)
        rim.data.energy = 1.2
        rim.rotation_euler = (math.radians(-55), math.radians(20), math.radians(-150))
    sc.camera = cam
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = True
    add_outline(obj)
    outline = obj.modifiers["Outline"]

    def shoot(name, loc, target, ortho=None, res=768, width=0.006, aa=1.5, lens=50):
        cam.location = loc
        cam.data.type = "ORTHO" if ortho else "PERSP"
        if ortho:
            cam.data.ortho_scale = ortho
        cam.data.lens = lens
        cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        outline.thickness = width
        sc.render.resolution_x = sc.render.resolution_y = res
        sc.render.filter_size = aa
        sc.render.filepath = os.path.join(toy.src_dir, name)
        bpy.ops.render.render(write_still=True)
        sc.render.resolution_x = sc.render.resolution_y = 768

    return shoot


def render_previews(obj):
    """Front, sprite-matched 128 px, 3/4 diorama and back renders into source/."""
    shoot = preview_camera(obj)
    toy = char_of(obj)
    cx = (64 - toy.px) * S          # the 128 px frame's centre, in metres
    cz = (toy.ground - 64) * S
    shoot("preview_front.png", (cx, -5, cz), (cx, 0, cz), ortho=1.06)
    shoot("preview_128.png", (cx, -5, cz), (cx, 0, cz), ortho=1.0, res=128, width=0.009, aa=0.0)
    shoot("preview_3q.png", (-1.5, -2.4, 1.3), (0, 0, 0.42))
    shoot("preview_side.png", (5, 0, cz), (0, 0, cz), ortho=1.06)
    shoot("preview_back.png", (1.2, 2.6, 1.0), (0, 0, 0.42))


def pose_test(obj, raise_deg=55, swing="side"):
    """Swing both upper arms (side raise, or forward/back about the shoulders)
    and report clipping on the deformed mesh; leaves the rig at rest."""
    from mathutils import Quaternion
    rig = obj.parent
    mute_ik(rig, True)

    def turn(bone, axis, deg):
        pb = rig.pose.bones[bone]
        pb.rotation_mode = "QUATERNION"
        rest = pb.bone.matrix_local.to_quaternion()
        pb.rotation_quaternion = rest.inverted() @ Quaternion(axis, math.radians(deg)) @ rest

    if swing == "side":
        turn("upperarm_R", (0, 1, 0), raise_deg)   # the character's right is -X
        turn("upperarm_L", (0, 1, 0), -raise_deg)
    else:
        sign = -1 if swing == "forward" else 1     # it faces -Y
        for bone in ("upperarm_R", "upperarm_L"):
            turn(bone, (1, 0, 0), sign * raise_deg)
    bpy.context.view_layer.update()
    clips = clip_report(obj, evaluated=True)
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
    mute_ik(rig, False)
    bpy.context.view_layer.update()
    return clips
