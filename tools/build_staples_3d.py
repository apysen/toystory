"""Build the 3D staples Stapler Rogue fires (Blender): VFX models, not characters.

Live, through the Blender MCP:  exec(open("tools/build_staples_3d.py").read())  then  build_staples()
Headless (builds, renders previews, exports):
    D:/Blender/blender.exe --background --python tools/build_staples_3d.py

Two staples, each a square wire bent into a U, flying legs first (-Y in Blender,
+Z in Godot) with the crown level across the top of the flight:
  Staple       Staple Shot and Staple Burst: steel grey with a white top edge, like
               the strips clipped to his belt, sized up a little so it reads at
               battle distance
  StapleHeavy  Pin's charged shot: the same staple, bigger and thicker

Like the toys, each is a closed solid on one material that samples swatches of a
16x16 palette (and a matching glow texture), nearest-filtered. There is no rig:
EffectsLayer flies them. Writes assets/models/vfx/staples.glb; previews
go in assets/models/vfx/source/ (Godot-ignored).
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

try:
    _TOOLS = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _TOOLS = os.path.join(os.getcwd(), "tools")
sys.dont_write_bytecode = True   # no __pycache__ in tools/ (check_structure)

ROOT = os.path.dirname(_TOOLS)
OUT_DIR = os.path.join(ROOT, "assets", "models", "vfx")
SRC_DIR = os.path.join(OUT_DIR, "source")
NAME = "staples"

# name, hex, emissive: Stapler's steel and its highlight
PALETTE = [("grey", "b6aaa6", False), ("grey_dark", "857a76", False), ("white", "faf2ee", False)]

# (crown width, leg length, wire width across, wire thickness) in metres
STAPLE = (0.05, 0.03, 0.007, 0.0045)
HEAVY = (0.08, 0.05, 0.011, 0.007)
CORNER = 0.6   # the crown's corners round off over this share of the wire width
TIP = 0.45     # share of the wire width the legs' chisel points run back


def swatch_uv(colour):
    """UV of the middle of a colour's swatch (4x4 swatches on the 16x16 palette)."""
    k = [p[0] for p in PALETTE].index(colour)
    return ((k % 4) * 0.25 + 0.125, 1.0 - ((k // 4) * 0.25 + 0.125))


def sweep(bm, uv, path, w, h, colour, top_colour=None):
    """A bar of w x h cross-section along `path` (points in the XY plane, the bar's
    height along Z), open at both ends for the chisel points to close. The top
    face takes `top_colour`. Returns (first ring, last ring)."""
    rings = []
    for i, p in enumerate(path):
        a = path[max(i - 1, 0)]
        b = path[min(i + 1, len(path) - 1)]
        t = (b - a).normalized()
        side = Vector((-t.y, t.x, 0.0)) * (w / 2)
        up = Vector((0, 0, h / 2))
        rings.append([bm.verts.new(p + o) for o in (side + up, -side + up, -side - up, side - up)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(4):
            f = bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
            faces.append((f, top_colour if (k == 0 and top_colour) else colour))
    for f, c in faces:
        for loop in f.loops:
            loop[uv].uv = swatch_uv(c)
    return rings[0], rings[-1]


def staple_path(crown, leg, w):
    """The wire's centre line: one leg tip, up the leg, round the crown, down the
    other leg (legs point -Y, the way it flies)."""
    half = crown / 2 - w / 2
    r = w * CORNER * 2
    pts = [Vector((-half, -leg, 0))]
    for k in range(5):  # left corner: centre (-half + r, -r), from 180 to 90 degrees
        a = math.pi - math.pi / 2 * k / 4
        pts.append(Vector((-half + r + r * math.cos(a), -r + r * math.sin(a), 0)))
    for k in range(5):  # right corner: centre (half - r, -r), from 90 to 0 degrees
        a = math.pi / 2 - math.pi / 2 * k / 4
        pts.append(Vector((half - r + r * math.cos(a), -r + r * math.sin(a), 0)))
    pts.append(Vector((half, -leg, 0)))
    return pts


def build_one(name, size, colour, top_colour):
    crown, leg, w, h = size
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    path = staple_path(crown, leg, w)
    ends = sweep(bm, uv, path, w, h, colour, top_colour)
    # chisel points close each leg: a wedge running forward from the leg's end ring
    for ring, x in zip(ends, (path[0].x, path[-1].x)):
        inner = 1 if x < 0 else -1
        tip = Vector((x + inner * w * 0.3, -leg - w * TIP * 2, 0))
        top, bot = bm.verts.new(tip + Vector((0, 0, h / 2))), bm.verts.new(tip - Vector((0, 0, h / 2)))
        # ring order is (+side+up, -side+up, -side-up, +side-up); wind each face outward
        quads = [(ring[0], ring[1], top), (ring[2], ring[3], bot), (ring[1], ring[2], bot, top),
                 (ring[3], ring[0], top, bot)]
        for k, q in enumerate(quads):
            f = bm.faces.new(q)
            for loop in f.loops:
                loop[uv].uv = swatch_uv(top_colour if k == 0 else colour)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    return obj


def palette_image(name, emissive_only):
    """Always a new image (see toy3d.make_material: a reused, packed image can keep
    stale bytes)."""
    old = bpy.data.images.get(name)
    if old:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, 16, 16, alpha=False)
    px = []
    for row in range(16):          # Blender rows run bottom-up
        for col in range(16):
            k = (3 - row // 4) * 4 + col // 4
            _, hexv, emissive = PALETTE[k] if k < len(PALETTE) else ("", "000000", False)
            rgb = [int(hexv[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
            if emissive_only and not emissive:
                rgb = [0.0, 0.0, 0.0]
            px += rgb + [1.0]
    img.pixels = px
    os.makedirs(SRC_DIR, exist_ok=True)
    img.filepath_raw = os.path.join(SRC_DIR, name + ".png")
    img.file_format = "PNG"
    img.save()
    img.pack()
    return img


def material():
    mat = bpy.data.materials.get("Staples") or bpy.data.materials.new("Staples")
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    base, glow = nt.nodes.new("ShaderNodeTexImage"), nt.nodes.new("ShaderNodeTexImage")
    base.image, glow.image = palette_image(NAME + "_palette", False), palette_image(NAME + "_emission", True)
    base.interpolation = glow.interpolation = "Closest"
    nt.links.new(base.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(glow.outputs["Color"], bsdf.inputs["Emission Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Emission Strength"].default_value = 1.5
    bsdf.inputs["Metallic"].default_value = 0.6
    bsdf.inputs["Roughness"].default_value = 0.4
    return mat


def build_staples():
    """(Re)build both staples in a "Staples" collection. Returns the objects."""
    col = bpy.data.collections.get("Staples")
    if col is None:
        col = bpy.data.collections.new("Staples")
        bpy.context.scene.collection.children.link(col)
    for n in ("Staple", "StapleHeavy"):
        old = bpy.data.objects.get(n)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    mat = material()
    objs = [build_one("Staple", STAPLE, "grey", "white"),
            build_one("StapleHeavy", HEAVY, "grey", "white")]
    for o in objs:
        o.data.materials.append(mat)
        col.objects.link(o)
    objs[1].location.x = 0.12   # side by side in Blender; each exports at its own origin
    return objs


def export(objs):
    path = os.path.join(OUT_DIR, NAME + ".glb")
    os.makedirs(SRC_DIR, exist_ok=True)
    gdignore = os.path.join(SRC_DIR, ".gdignore")
    if not os.path.exists(gdignore):
        open(gdignore, "w").close()
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    keep = [o.location.copy() for o in objs]
    for o in objs:
        o.location = (0, 0, 0)
        o.select_set(True)
    try:
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                                  export_animations=False, export_skins=False)
    finally:
        for o, loc in zip(objs, keep):
            o.location = loc
    return path


def render_previews(objs, res=384):
    """Close-ups of each staple (top, side, three-quarter, and from behind as it
    flies away) to source/, with everything else in the scene hidden from the render."""
    sc = bpy.context.scene
    cam = bpy.data.objects.get("StaplesCam")
    if cam is None:
        cam = bpy.data.objects.new("StaplesCam", bpy.data.cameras.new("StaplesCam"))
        sc.collection.objects.link(cam)
        sun = bpy.data.objects.new("StaplesSun", bpy.data.lights.new("StaplesSun", "SUN"))
        sc.collection.objects.link(sun)
        sun.data.energy = 3.0
        sun.rotation_euler = (math.radians(45), math.radians(-20), math.radians(-35))
    hidden = {o: o.hide_render for o in sc.objects if o not in objs and o.type not in ("CAMERA", "LIGHT")}
    for o in hidden:
        o.hide_render = True
    sc.camera = cam
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.view_settings.view_transform = "Standard"
    cam.data.type = "ORTHO"
    paths = []
    try:
        for o in objs:
            target = o.location + Vector((0, -o.dimensions.y / 2, 0))
            cam.data.ortho_scale = max(o.dimensions) * 1.6
            for tag, d in (("top", (0, 0, 1)), ("side", (1, 0, 0.0001)), ("three_quarter", (0.6, 0.7, 0.5)),
                           ("behind", (0.15, 1, 0.35))):
                dv = Vector(d).normalized()
                cam.location = target + dv * 1.0
                cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
                p = os.path.join(SRC_DIR, f"{o.name.lower()}_{tag}.png")
                sc.render.filepath = p
                bpy.ops.render.render(write_still=True)
                paths.append(p)
    finally:
        for o, h in hidden.items():
            o.hide_render = h
    return paths


if __name__ == "__main__" and bpy.app.background:
    staples = build_staples()
    render_previews(staples)
    print("glb", export(staples))
