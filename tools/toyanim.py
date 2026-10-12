"""Shared machinery for keyframing the toys' battle clips at 60 fps (Blender).

Extracted from tools/animate_lamp_warden_3d.py (which still has its own copy);
each character's animate script defines its poses and clips and uses these:

A pose maps bone names to channels:
  "rot": (x, y, z) degrees about the world axes, at the bone's head. Toys face
         -Y: x > 0 leans/tips forward (bones hanging down swing back), y > 0
         tilts toward +X (their left), z > 0 turns them toward their left.
  "loc": (x, y, z) metres in world space (hips, root and the ik_* / pole_*
         controls), as an offset from rest.
  "shrink": (k, k, k) how far the bone is scaled down about its head, 0 full
         size to 1 gone (a prop put away, a drink drained; absent is full size, so
         it keys and mixes like the others); keyed only on the bones the rig lists
         in its "scaled_bones" property.
ik_hand_* and ik_foot_* carry the hands and feet; IK bends the limbs to reach
them, so the hands follow the body only if the pose moves them too.

Clips are a function of the frame (loops of the loop phase), often a list of
key poses joined by smooth curves (keyed), sampled on every frame so motion is
smooth at 60 fps and loops join seamlessly.
"""
import json
import math
import os

import bpy
from mathutils import Euler, Vector

FPS = 60


# -- curves --------------------------------------------------------------------

def wave(p, k=1, phase=0.0):
    """Sine with k whole cycles over the loop phase p in [0, 1)."""
    return math.sin(2 * math.pi * k * p + phase)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def keyed(keys, frame):
    """Pose at frame from [(frame, pose), ...]: each channel follows a smooth
    cubic through its key values (missing channels are at rest), easing in
    and out of the first and last keys."""
    frames = [k for k, _ in keys]
    i = max(0, min(len(keys) - 2, next((n for n in range(len(frames) - 1) if frame < frames[n + 1]),
                                       len(frames) - 2)))
    f0, f1 = frames[i], frames[i + 1]
    u = max(0.0, min(1.0, (frame - f0) / (f1 - f0)))
    names = {(bone, ch) for _, pose in keys for bone, chans in pose.items() for ch in chans}

    def val(n, bone, ch):
        return Vector(keys[n][1].get(bone, {}).get(ch, (0.0, 0.0, 0.0)))

    def tangent(n, bone, ch):
        if n == 0 or n == len(keys) - 1:
            return Vector((0, 0, 0))
        return (val(n + 1, bone, ch) - val(n - 1, bone, ch)) / (frames[n + 1] - frames[n - 1])

    h00, h10 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u
    h01, h11 = -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    span = f1 - f0
    out = {}
    for bone, ch in names:
        v = (val(i, bone, ch) * h00 + tangent(i, bone, ch) * span * h10
             + val(i + 1, bone, ch) * h01 + tangent(i + 1, bone, ch) * span * h11)
        out.setdefault(bone, {})[ch] = tuple(v)
    return out


def add(*vs):
    return tuple(sum(c) for c in zip(*vs))


def mix(*poses):
    """Sum poses channel by channel."""
    out = {}
    for pose in poses:
        for bone, chans in pose.items():
            for ch, v in chans.items():
                out.setdefault(bone, {})[ch] = add(out.get(bone, {}).get(ch, (0.0, 0.0, 0.0)), v)
    return out


def scaled(pose, k):
    return {b: {ch: tuple(c * k for c in v) for ch, v in chans.items()} for b, chans in pose.items()}


# -- feet ----------------------------------------------------------------------

def step(q, stride, lift, stance=0.6):
    """One foot over a stride cycle (q = 0 heel strike): planted and sliding back
    for `stance` of the cycle, then lifted and carried forward. Returns the
    ik_foot pose."""
    if q < stance:
        u = q / stance
        fwd = stride / 2 - stride * u
        z = 0.0
        pitch = -12 * (1 - smooth(u / 0.2)) + 18 * smooth((u - 0.75) / 0.25)
    else:
        u = (q - stance) / (1 - stance)
        fwd = -stride / 2 + stride * (0.5 - 0.5 * math.cos(math.pi * u))
        z = lift * math.sin(math.pi * u)
        pitch = 18 * (1 - smooth(u / 0.4)) - 12 * smooth((u - 0.6) / 0.4)
    # pitching about the ankle would dig toe or heel into the floor: lift it
    z += 0.07 * math.sin(math.radians(max(pitch, 0))) + 0.02 * math.sin(math.radians(max(-pitch, 0)))
    return {"loc": (0, -fwd, z), "rot": (pitch, 0, 0)}


def plant_path(plants, frame, lift=0.05):
    """World offset (and pitch) of a foot stepping between plants:
    [(lift_frame, land_frame, (x, y)), ...], starting from its rest (0, 0)."""
    pos, pitch = Vector((0.0, 0.0, 0.0)), 0.0
    for up, land, (x, y) in plants:
        target = Vector((x, y, 0.0))
        if frame <= up:
            break
        if frame >= land:
            pos = target
            continue
        u = (frame - up) / (land - up)
        pos = pos.lerp(target, 0.5 - 0.5 * math.cos(math.pi * u))
        pos.z = lift * math.sin(math.pi * u)
        pitch = 20 * math.sin(math.pi * u) - 10 * smooth((u - 0.6) / 0.4)
        break
    return pos, pitch


KNEE_REST = {}  # side -> (rest hip, knee, ankle, pole), filled from the rig by read_rest


def read_rest(rig):
    for side in ("R", "L"):
        KNEE_REST[side] = (rig.data.bones[f"thigh_{side}"].head_local.copy(),
                           rig.data.bones[f"thigh_{side}"].tail_local.copy(),
                           rig.data.bones[f"shin_{side}"].tail_local.copy(),
                           rig.data.bones[f"pole_knee_{side}"].head_local.copy())


def knee_ahead(side, shift):
    """Pole offset that points this knee straight ahead, on the line from its
    hip to a foot moved `shift` metres in X."""
    if side not in KNEE_REST:
        return {}
    hip, knee, ankle, pole = KNEE_REST[side]
    t = (hip.z - knee.z) / (hip.z - ankle.z)
    x = hip.x + t * (ankle.x + shift - hip.x)
    target = Vector((x, knee.y - 0.3, knee.z))
    return {f"pole_knee_{side}": {"loc": tuple(target - pole)}}


def feet_in(shift_r, shift_l, toe=0.0):
    """Both feet moved toward the centre (shift > 0 is inward) with the knees
    pointing straight ahead over them."""
    return mix({"ik_foot_R": {"loc": (shift_r, 0, 0), "rot": (0, 0, toe)},
                "ik_foot_L": {"loc": (-shift_l, 0, 0), "rot": (0, 0, -toe)}},
               knee_ahead("R", shift_r), knee_ahead("L", -shift_l))


def lowered(dz, dy=0.0, dx=0.0):
    """Move the body, carrying both hands with it (their IK targets are world-space)."""
    v = (dx, dy, dz)
    return {"hips": {"loc": v}, "ik_hand_R": {"loc": v}, "ik_hand_L": {"loc": v}}


# -- keying --------------------------------------------------------------------

def apply_pose(rig, pose, settle=None):
    """Reset every bone, then set the pose (world-axis rotations and offsets)."""
    if settle:
        pose = settle(pose)
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


def action_name(rig, clip):
    """Actions are named "<toy>|<clip>" so two toys' "idle"s can share a Blender
    session; the export names each animation by the clip alone."""
    return rig.name.removesuffix("Rig") + "|" + clip


def key_clip(rig, name, frames, loops, pose_at, settle=None):
    """One action per clip with every bone keyed on every frame."""
    old = bpy.data.actions.get(action_name(rig, name))
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(action_name(rig, name))
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act
    scaled = set(rig.get("scaled_bones", ()))
    for f in range(frames + 1):
        apply_pose(rig, pose_at(f if not (loops and f == frames) else 0), settle)
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
            pb.keyframe_insert("location", frame=f, group=pb.name)
            if pb.name in scaled:
                pb.keyframe_insert("scale", frame=f, group=pb.name)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, frames
    act.use_cyclic = loops
    return act


def animate(rig, clips, settle=None):
    """Key every clip ({name: (frames, loops, pose_at)}), dropping the rig's
    old clips that are no longer listed."""
    bpy.context.scene.render.fps = FPS
    read_rest(rig)
    keep = {action_name(rig, n) for n in clips}
    for act in [a for a in bpy.data.actions if a.name not in keep
                and any(sl.identifier == "OB" + rig.name for sl in getattr(a, "slots", []))]:
        bpy.data.actions.remove(act)
    for name, (frames, loops, pose_at) in clips.items():
        key_clip(rig, name, frames, loops, pose_at, settle)
    rig.animation_data.action = bpy.data.actions[action_name(rig, "idle")]
    bpy.context.scene.frame_set(0)


def write_events(path, events):
    """Moments the game times itself by, in seconds: <glb>_events.json."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: {e: round(t, 4) for e, t in v.items()} for k, v in events.items()}, f, indent=2)
    return path


def play(rig, name, frame):
    rig.animation_data.action = bpy.data.actions[action_name(rig, name)]
    bpy.context.scene.frame_set(frame)


def clip_check(obj, clips, report, every=1):
    """Worst clipping per clip over every `every`th frame: {clip: {pair: (count, frame)}}."""
    rig = obj.parent
    out = {}
    for name, (frames, _, _) in clips.items():
        worst = {}
        for f in range(0, frames + 1, every):
            play(rig, name, f)
            for k, v in report(obj, evaluated=True).items():
                if v > worst.get(k, (0, 0))[0]:
                    worst[k] = (v, f)
        out[name] = worst
    play(rig, "idle", 0)
    return out


def render_strips(obj, clips, shoot, frames_per_clip=6, res=256, folder="anim",
                  cam=((-1.5, -2.4, 1.3), (0, 0, 0.42))):
    """3/4 view renders of evenly spaced frames: source/<folder>/<clip>_<frame>.png."""
    rig = obj.parent
    paths = {}
    for name, (frames, loops, _) in clips.items():
        picks = [round(i * (frames - (1 if loops else 0)) / (frames_per_clip - 1)) for i in range(frames_per_clip)]
        paths[name] = []
        for f in picks:
            play(rig, name, f)
            rel = os.path.join(folder, f"{name}_{f:03d}.png")
            shoot(rel, cam[0], cam[1], res=res, width=0.005)
            paths[name].append(rel)
    play(rig, "idle", 0)
    return paths


# -- viewing clips in Blender ------------------------------------------------------------

class TOY_OT_play_clip(bpy.types.Operator):
    """Show this clip on the toy and play it (loops in the viewport)"""
    bl_idname = "toy.play_clip"
    bl_label = "Play clip"
    rig: bpy.props.StringProperty()
    clip: bpy.props.StringProperty()

    def execute(self, context):
        rig = bpy.data.objects.get(self.rig)
        act = bpy.data.actions.get(action_name(rig, self.clip)) if rig else None
        if act is None:
            self.report({"WARNING"}, f"No clip '{self.clip}' on {self.rig}")
            return {"CANCELLED"}
        # the toys all stand on the origin: show this one, hide the others
        mine = {c.name for c in rig.users_collection}
        for other in bpy.data.objects:
            if other.get("toy") and other.parent and other.parent is not rig:
                for col in other.parent.users_collection:
                    if col.name not in mine:
                        lc = _layer_collection(context.view_layer.layer_collection, col.name)
                        if lc:
                            lc.hide_viewport = True
        for col in rig.users_collection:
            col.hide_viewport = False
            lc = _layer_collection(context.view_layer.layer_collection, col.name)
            if lc:
                lc.hide_viewport = False
        rig.animation_data_create()
        rig.animation_data.action = act
        if act.slots:
            rig.animation_data.action_slot = act.slots[0]
        sc = context.scene
        sc.render.fps = FPS
        sc.frame_start, sc.frame_end = int(act.frame_range[0]), int(act.frame_range[1])
        sc.frame_set(sc.frame_start)
        if not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {"FINISHED"}


class TOY_OT_stop_clip(bpy.types.Operator):
    """Stop playback on the current frame"""
    bl_idname = "toy.stop_clip"
    bl_label = "Stop"

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_cancel(restore_frame=False)
        return {"FINISHED"}


def _layer_collection(lc, name):
    if lc.name == name:
        return lc
    for child in lc.children:
        found = _layer_collection(child, name)
        if found:
            return found
    return None


def register_clip_panel(rig, clips, title):
    """A sidebar tab (N panel in the 3D view) named `title` with a button per
    clip that shows it on `rig` and plays it, plus Stop. Re-running replaces it."""
    for cls in (TOY_OT_play_clip, TOY_OT_stop_clip):
        if not hasattr(bpy.types, cls.__name__):
            bpy.utils.register_class(cls)
    key = "".join(c for c in rig.name if c.isalnum())
    old = getattr(bpy.types, f"TOY_PT_{key}", None)
    if old:
        bpy.utils.unregister_class(old)
    names = list(clips)

    def draw(self, context):
        layout = self.layout
        act = rig.animation_data.action if rig.animation_data else None
        layout.label(text="Showing: " + (act.name.split("|")[-1] if act else "rest pose"))
        row = layout.row(align=True)
        row.operator("toy.stop_clip", icon="PAUSE")
        col = layout.column(align=True)
        for name in names:
            frames, loops = clips[name][0], clips[name][1]
            label = f"{name}  ({frames / FPS:.2f}s{', loop' if loops else ''})"
            op = col.operator("toy.play_clip", text=label, icon="PLAY")
            op.rig, op.clip = rig.name, name

    panel = type(f"TOY_PT_{key}", (bpy.types.Panel,), {
        "bl_idname": f"TOY_PT_{key}", "bl_label": title + " clips", "bl_space_type": "VIEW_3D",
        "bl_region_type": "UI", "bl_category": title, "draw": draw})
    bpy.utils.register_class(panel)
    return panel
