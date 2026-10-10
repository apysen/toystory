"""Build the 3D slice of toast Toaster Pyromancer launches (Blender): a VFX model,
not a character.

Live, through the Blender MCP:  exec(open("tools/build_toast_3d.py").read())  then  build_toast()
Headless (builds and exports):
    D:/Blender/blender.exe --background --python tools/build_toast_3d.py

One slice, the same shape and size as the slices in his slots
(build_toaster_pyromancer_3d.toast_outline, TOAST_SIZE), already toasted: a dark
crust round a browned crumb on both faces, the colours unit_model.gdshader gives a
slice in his slots once it has toasted (TOASTED there). Its origin is the middle of
the slice so it tumbles about its centre; it faces -Y in Blender (+Z in Godot).

Like the toys it is a closed solid on one material that samples swatches of a
16x16 palette, nearest-filtered. There is no rig: EffectsLayer flies it. Writes
assets/models/vfx/toast.glb.
"""
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
sys.dont_write_bytecode = True   # no __pycache__ in tools/ (check_structure)

ROOT = os.path.dirname(_TOOLS)
OUT_DIR = os.path.join(ROOT, "assets", "models", "vfx")
SRC_DIR = os.path.join(OUT_DIR, "source")
NAME = "toast"

# name, hex, emissive: the toaster's crust (b8692a) and crumb (f0c27c), toasted
PALETTE = [("crust", "934516", False), ("crumb", "c08040", False)]

TOAST_SIZE = (0.15, 0.11, 0.018)   # width, height, thickness (as the toaster's slices)


def toast_outline(width, height):
    """A slice of bread seen face on: straight sides, a top that bulges into two
    shoulders, as (x, z) round its middle bottom (build_toaster_pyromancer_3d)."""
    pts = [(-width / 2, 0.0), (width / 2, 0.0)]
    for k in range(13):
        t = k / 12
        a = math.pi * t
        x = width / 2 * math.cos(a) * (1.0 + 0.08 * math.sin(a))
        z = height * 0.72 + height * 0.28 * math.sin(a) + height * 0.06 * math.sin(2 * a) ** 2
        pts.append((x * 1.06, z))
    return pts


def swatch_uv(colour):
    """UV of the middle of a colour's swatch (4x4 swatches on the 16x16 palette)."""
    k = [p[0] for p in PALETTE].index(colour)
    return ((k % 4) * 0.25 + 0.125, 1.0 - ((k // 4) * 0.25 + 0.125))


def slab(bm, uv, pts, th, M, colour, zoff=0.0):
    """Extrude an outline (local XY) by th along local Z, coloured; returns its faces."""
    top = [bm.verts.new(M @ Vector((x, y, th / 2 + zoff))) for x, y in pts]
    bot = [bm.verts.new(M @ Vector((x, y, -th / 2 + zoff))) for x, y in pts]
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(bot)))]
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    for f in faces:
        for loop in f.loops:
            loop[uv].uv = swatch_uv(colour)
    return faces


def build_one():
    width, height, th = TOAST_SIZE
    pts = toast_outline(width, height)
    inner = [(x * 0.84, 0.01 + z * 0.86) for x, z in pts]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    # the slab's local X runs across, local Y up and local Z toward the front (-Y),
    # centred on the slice's middle
    M = Matrix.Translation((0, 0, -height / 2)) @ Matrix(((1.0, 0.0, 0.0, 0.0), (0.0, 0.0, -1.0, 0.0),
                                                           (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
    slab(bm, uv, pts, th, M, "crust")
    for zoff in (th / 2 + 0.0008, -th / 2 - 0.0008):   # the crumb, a crust rim round it
        slab(bm, uv, inner, 0.0016, M, "crumb", zoff)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new("Toast")
    bm.to_mesh(mesh)
    bm.free()
    return bpy.data.objects.new("Toast", mesh)


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
    mat = bpy.data.materials.get("Toast") or bpy.data.materials.new("Toast")
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
    return mat


def build_toast():
    """(Re)build the slice in a "Toast" collection. Returns it."""
    col = bpy.data.collections.get("ToastVFX")
    if col is None:
        col = bpy.data.collections.new("ToastVFX")
        bpy.context.scene.collection.children.link(col)
    old = bpy.data.objects.get("Toast")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    o = build_one()
    o.data.materials.append(material())
    col.objects.link(o)
    return o


def export(o):
    path = os.path.join(OUT_DIR, NAME + ".glb")
    os.makedirs(SRC_DIR, exist_ok=True)
    gdignore = os.path.join(SRC_DIR, ".gdignore")
    if not os.path.exists(gdignore):
        open(gdignore, "w").close()
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    keep = o.location.copy()
    o.location = (0, 0, 0)
    o.select_set(True)
    try:
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                                  export_animations=False, export_skins=False)
    finally:
        o.location = keep
    return path


if __name__ == "__main__" and bpy.app.background:
    print("glb", export(build_toast()))
