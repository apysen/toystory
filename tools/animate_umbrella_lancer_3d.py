"""Keyframe the 3D Umbrella Lancer's battle clips at 60 fps (Blender).

Live, through the Blender MCP (the owner's rule: build and animate in the open session):
    exec(open("tools/animate_umbrella_lancer_3d.py").read())   then  animate_umbrella()
which also adds an "Umbrella Lancer" tab to the 3D view's sidebar (N) with a button
that plays each clip.

Clips use the game's names (docs/character_abilities_stats.md), as the owner agreed
them (docs/umbrella_animation_plan.md, 2026-10-12):
  loop      idle (planted, the umbrella shouldered pike-style on his left pauldron,
            right arm resting at his side), move (Mary Poppins: he hangs from the open
            umbrella 20 cm off the floor, legs dangling, canopy tilted to his
            heading), hover (the same float standing still), lunge_run (the
            couched charge, played as long as Lunge's dash takes)
  play once move_start (a Peach-style launch: crouch, spring, the umbrella pops open
            and he catches under it), move_end (floats down toe first, the umbrella
            snaps shut and goes back on his shoulder), attack (Tip Thrust: a knight's
            salute, en garde, a fencer's lunge), lunge (the lead-in to the charge,
            ending couched) and lunge_strike (the spike lands, a skid, re-shoulder),
            canopy (opened high and wide over himself and his neighbours), raincheck
            (signature: snapped open, twirled under the rain, planted as a shield,
            closed with a bow), hurt, broken (the umbrella pops open on its own and
            lands over him like a little tent)
The umbrella (lance) hangs off the root bone, not the hand: every pose carries it in
his left fist (settle), so broken can let go of it. Poses and keying work as in
tools/toyanim.py, plus these pseudo-bones that settle() turns into real channels:
  "_gL", "_gR"  a fist's grip: "at" (point), "fwd" (where the umbrella's tip, or the
                fist's bar, points) and "wr" (from the grip toward the wrist), all in
                the rest body's space, carried by hips, spine and chest
  "_open"       how far the canopy is open, degrees ("v")
  "_spin"       the umbrella turned about its own shaft in his fist, degrees ("v")
  "_free"       the umbrella out of his hand: "w" (0 held .. 1 free) and its world
                "at", "fwd", "wr"
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

try:
    _TOOLS = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _TOOLS = os.path.join(os.getcwd(), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
sys.dont_write_bytecode = True   # no __pycache__ in tools/ (check_structure)
import toyanim  # noqa: E402
importlib.reload(toyanim)
from toyanim import FPS, wave, smooth, keyed, mix, knee_ahead, step  # noqa: E402

BUILD = {"__name__": "umbrella_build", "__file__": os.path.join(_TOOLS, "build_umbrella_lancer_3d.py")}
exec(compile(open(BUILD["__file__"], encoding="utf-8").read(), BUILD["__file__"], "exec"), BUILD)
toy3d = BUILD["toy3d"]
OBJECT = BUILD["CHAR"].object_name
CANOPY_RIBS = BUILD["CANOPY_RIBS"]


# -- the rig at rest -------------------------------------------------------------------------

REST = {}                # side -> (wrist, grip, the fist's bar, grip -> wrist) at rest
BODY = {}                # hips, spine, chest heads
SHOULDER = {}            # side -> the shoulder's rest place
REACH = 0.136            # m from shoulder to wrist he can reach (his arm, 13.9 cm, all but straight)
RIBS = []                # (rest rotation, hinge axis in the rib's frame, sign) per rib
CANOPY = {}              # what the runner's slide is worked out from


def read_rest(rig):
    for side in ("R", "L"):
        h = rig.data.bones["hand_" + side]
        axis = BUILD["FIST_AXIS"].copy()                 # the bar the fist closes on (the umbrella's tip way)
        ref = (h.head_local - h.tail_local).normalized()  # grip -> wrist, square to the bar
        ref = (ref - axis * ref.dot(axis)).normalized()
        REST[side] = (h.head_local.copy(), h.tail_local.copy(), axis, ref)
        SHOULDER[side] = rig.data.bones["upperarm_" + side].head_local.copy()
    for b in ("hips", "spine", "chest"):
        BODY[b] = rig.data.bones[b].head_local.copy()
    # each rib swings out from the shaft about the line across it through its hinge
    # (as build's open_canopy)
    lance = rig.data.bones["lance"]
    axis = (lance.tail_local - lance.head_local).normalized()
    RIBS.clear()
    for i in range(CANOPY_RIBS):
        bone = rig.data.bones[f"rib_{i}"]
        rest = bone.matrix_local.to_3x3()
        d = (bone.tail_local - bone.head_local).normalized()
        out = (d - axis * d.dot(axis)).normalized()
        local = rest.inverted() @ axis.cross(out).normalized()
        sign = 1.0
        if (rest @ (Quaternion(local, 0.5) @ Vector((0, 1, 0)))).dot(out) < d.dot(out):
            sign = -1.0
        RIBS.append((rest.to_quaternion(), local, sign))
    rb, st, runner = rig.data.bones["rib_0"], rig.data.bones["stretcher_0"], rig.data.bones["runner"]
    rel_foot = st.head_local - lance.head_local
    CANOPY.update(axis=axis, lance=lance.head_local.copy(), rib_head=rb.head_local.copy(),
                  rib_rest=rb.matrix_local.to_3x3(), rib_len=rb.length, st_len=st.length,
                  foot_along=rel_foot.dot(axis), foot_r=(rel_foot - axis * rel_foot.dot(axis)).length,
                  runner_rest=runner.matrix_local.to_quaternion())


# the poses below are worked out from the rig's rest, so read it as the script loads
# (building him first in a session that doesn't have him yet)
if bpy.data.objects.get(OBJECT) is None:
    BUILD["build_umbrella"]()
toyanim.read_rest(bpy.data.objects[OBJECT].parent)
read_rest(bpy.data.objects[OBJECT].parent)


def canopy(deg):
    """The ribs turned out `deg` degrees from the shaft (0 furled) and the runner slid
    up to where its stretchers, their true length, meet them: a real umbrella opening."""
    pose = {}
    for i, (rest, local, sign) in enumerate(RIBS):
        q = rest @ Quaternion(local, sign * math.radians(deg)) @ rest.inverted()
        pose[f"rib_{i}"] = {"rot": tuple(math.degrees(a) for a in q.to_euler("XYZ"))}
    c = CANOPY
    rest, local, sign = RIBS[0]
    q = Quaternion(local, sign * math.radians(deg))
    mid = c["rib_head"] + c["rib_rest"] @ (q @ Vector((0, c["rib_len"] * 0.5, 0)))
    rel = mid - c["lance"]
    along, radial = rel.dot(c["axis"]), (rel - c["axis"] * rel.dot(c["axis"])).length
    foot = along - math.sqrt(max(c["st_len"] ** 2 - (radial - c["foot_r"]) ** 2, 0.0))
    pose["runner"] = {"loc": tuple(c["axis"] * (foot - c["foot_along"]))}
    return pose


# -- the body's frame ----------------------------------------------------------------------------

def body_xform(pose):
    """Where a point or direction fixed to his chest goes in this pose (hips, spine and
    chest turned about their heads, the hips moved), and back."""
    def q(b):
        return Euler([math.radians(a) for a in pose.get(b, {}).get("rot", (0, 0, 0))], "XYZ").to_quaternion()
    qh, qs, qc = q("hips"), q("spine"), q("chest")
    loc = Vector(pose.get("hips", {}).get("loc", (0, 0, 0)))
    h, s, c = BODY["hips"], BODY["spine"], BODY["chest"]

    def pt(p):
        p = Vector(p)
        p = qc @ (p - c) + c
        p = qs @ (p - s) + s
        return qh @ (p - h) + h + loc

    def vec(v):
        return qh @ (qs @ (qc @ Vector(v)))

    def ipt(p):
        p = Vector(p) - loc
        p = qh.inverted() @ (p - h) + h
        p = qs.inverted() @ (p - s) + s
        return qc.inverted() @ (p - c) + c

    def ivec(v):
        return qc.inverted() @ (qs.inverted() @ (qh.inverted() @ Vector(v)))
    return pt, vec, ipt, ivec


def turn_to(side, forward, wrist_toward):
    """The rotation that turns the fist's rest frame to close on a bar along `forward`
    with its wrist toward `wrist_toward`."""
    _, _, f0, r0 = REST[side]
    f1 = Vector(forward).normalized()
    r1 = Vector(wrist_toward)
    r1 = (r1 - f1 * r1.dot(f1)).normalized()
    m0 = Matrix((f0, r0, f0.cross(r0))).transposed()
    m1 = Matrix((f1, r1, f1.cross(r1))).transposed()
    return (m1 @ m0.transposed()).to_quaternion()


def ik_grip(side, at, q):
    wrist0, grip0, _, _ = REST[side]
    wrist = Vector(at) - q @ (grip0 - wrist0)
    return {f"ik_hand_{side}": {"loc": tuple(wrist - wrist0), "rot": tuple(math.degrees(a) for a in q.to_euler("XYZ"))}}


def fist(side, at, fwd, wr):
    """A fist's grip in the rest body's space (it moves with his chest)."""
    return {"_g" + side: {"at": tuple(at), "fwd": tuple(fwd), "wr": tuple(wr)}}


def fist_world(side, body, at, fwd, wr):
    """A fist placed in the world for a key whose body is `body` (a pose with hips,
    spine and chest), written in that body's space."""
    _, _, ipt, ivec = body_xform(body)
    return fist(side, ipt(at), ivec(fwd), ivec(wr))


def tilted(v, axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg)) @ Vector(v)


# -- the umbrella's places in his left fist ------------------------------------------------------
#
# Shouldered (idle): it rests on his left pauldron pointing back and rising about 5
# degrees, between two of the hat's drops (the brim is only about 11 cm above the
# pauldron, so he tips his head a little to his right, HAT_TIP). Off the shoulder it
# always travels outside the brim: out to his side still pointing back (OUT_BACK), then
# swung up in the plane beside him (OVER) to stand upright at his side (UPRIGHT), where
# it opens. His arms are short (the wrist reaches 14 cm from the shoulder), so the fist
# stays near his shoulder.

CARRY_REST_ON = Vector((0.104, 0.0, 0.562))           # where the shaft lies on the pauldron
CARRY_DIR = Vector((0.25, 0.96, 0.08)).normalized()  # back, a little out, rising ~5 degrees
CARRY_GRIP = 0.125                                    # m in front of the pauldron the fist holds it
HAT_TIP = {"head": {"rot": (0, -12, 0)}}             # the head (and hat) tipped to his right, clear of it


def carry(tilt=0.0):
    """The shouldered umbrella; `tilt` lifts its far end by degrees."""
    d = CARRY_DIR.copy()
    if tilt:
        d = tilted(d, d.cross(Vector((0, 0, 1))), tilt)
    return fist("L", CARRY_REST_ON - d * CARRY_GRIP, d, (0.05, -0.2, -1.0))


OUT_BACK = fist("L", (0.235, -0.02, 0.43), (0.06, 0.98, 0.18), (-0.7, 0.0, -0.7))
OVER = fist("L", (0.25, -0.05, 0.48), (0.02, 0.62, 0.78), (-0.9, 0.0, -0.4))
UPRIGHT = fist("L", (0.255, -0.06, 0.515), (-0.07, 0.0, 1.0), (-1.0, 0.0, -0.35))
# held up as high as his arm goes outside the brim, a little in front of the drop at his side
RAISED = fist("L", (0.26, -0.08, 0.522), (-0.12, 0.02, 1.0), (-1.0, 0.1, -0.5))

# the right arm resting at his side, hanging naturally a little out from it (the
# owner's pick: as in the float, in every clip but where it has work to do)


def arm_down(swing=0.0):
    """The right arm hanging at rest, the fist `swing` m forward (-) or back (+). It
    hangs with gravity under his shoulder, turning only with his heading (settle);
    the grip in his body's space is what it blends from where a pose gives the arm
    something to do."""
    return mix(fist("R", (-0.19, -0.01 + swing, 0.345), (0.0, -1.0, 0.15), (0.35, 0.0, 1.0)),
               {"_hangR": {"w": (1.0, 0.0, 0.0)}})


HANG_R = arm_down()
OPEN = 72.0              # degrees the canopy opens


def opened(deg):
    return {"_open": {"v": (deg, 0.0, 0.0)}}


# -- idle --------------------------------------------------------------------------------------

STANCE = mix({"ik_foot_R": {"loc": (-0.012, 0.012, 0), "rot": (0, 0, -8)},
              "ik_foot_L": {"loc": (0.016, -0.016, 0), "rot": (0, 0, 10)}},
             knee_ahead("R", -0.012), knee_ahead("L", 0.016))
IDLE_FRAMES = 180


def idle(p):
    """Three-second breathing loop: planted, weight on his right leg, the umbrella
    shouldered and settling a little on each breath, the right arm at rest, the
    head looking about under the brim."""
    breath = wave(p, 1, -math.pi / 2)
    sink = -0.003 * (0.5 - 0.5 * breath)
    return mix(STANCE, {
        "hips": {"loc": (-0.004, 0, sink), "rot": (0, 1.5, -4)},
        "spine": {"rot": (0.5 - 0.5 * breath, -0.5, -2)},
        "chest": {"rot": (1 - 1.0 * breath, -1, -2 + 0.6 * wave(p, 1, 1.0))},
        # glancing about to his right, away from the shouldered umbrella (to his left the hat meets it)
        "head": {"rot": (-1 + 1.0 * wave(p, 1, -1.4), 0.8 * wave(p, 1, -1.1), -4 - 4 * (0.5 + 0.5 * wave(p, 1, 0.4)))},
    }, HAT_TIP, carry(1.0 * breath), arm_down(0.004 * wave(p, 1, 0.4)))


IDLE0 = idle(0.0)


# -- floating ----------------------------------------------------------------------------------
#
# Mary Poppins: he hangs from the open umbrella 20 cm off the floor (the owner's pick),
# his left arm out to his side, the fist just under the brim's edge and the shaft rising
# outside it, tilted a few degrees in over his head (the owner's pick). Everything he
# holds rides with his body, so a bob lifts the umbrella with him.

FLOAT_UP = 0.20
RUN_SPEED = 1.8          # the game's travel pace (m/s); nothing touches the floor, so it only sets the loop
MOVE_FRAMES = 60
HOVER_FRAMES = 90


def aloft(h, swing_r=0.0, swing_l=0.0, point=38.0, tuck=0.012):
    """The body `h` m off the floor, the legs dangling under it, toes pointed; `swing_*`
    carry each foot forward (-) or back (+), `tuck` bends the knees."""
    return {"hips": {"loc": (0, 0, h)},
            "ik_foot_R": {"loc": (0.004, 0.018 + swing_r, h - tuck), "rot": (point, 0, -4)},
            "ik_foot_L": {"loc": (-0.004, 0.018 + swing_l, h - tuck - 0.004), "rot": (point - 4, 0, 4)},
            "pole_knee_R": {"loc": (0, 0, h)}, "pole_knee_L": {"loc": (0, 0, h)}}


def floating(p, travel):
    """One float cycle: a gentle bob and sway, the legs swinging loosely, the cape
    stirring; `travel` 1 leans into his heading, tilts the canopy toward it and
    trails the legs and cape, 0 hangs still."""
    bob = 0.008 * wave(p, 1)
    roll = 1.6 * wave(p, 1, 0.9)
    swing = 0.024 * wave(p, 1, 0.4)
    lean = 3.0 * travel
    shaft = (-0.07, -0.13 * travel, 1.0)
    return mix(aloft(FLOAT_UP + bob, swing + 0.01 * travel, -swing + 0.012 * travel, tuck=0.012 + 0.008 * abs(swing) / 0.024), {
        "hips": {"rot": (lean, roll, 0)},
        "spine": {"rot": (1.0 * travel, -0.4 * roll, 0)},
        "chest": {"rot": (0.5 + 0.6 * wave(p, 1, 2.0), -0.3 * roll, 0)},
        "head": {"rot": (-lean - 1.0 + 1.2 * wave(p, 1, 1.4), 0, 2.5 * wave(p, 1, -0.6) * (1 - travel))},
        "cape_1": {"rot": (4 + 8 * travel + 2.0 * wave(p, 2, 0.3), 0, 0)},
        "cape_2": {"rot": (3 + 6 * travel + 2.5 * wave(p, 2, -0.4), 0, 0)},
        "cape_3": {"rot": (2 + 6 * travel + 3.0 * wave(p, 2, -1.1), 0, 0)},
        "tabard_2": {"rot": (2 * travel, 0, 0)},
    }, fist("L", UPRIGHT["_gL"]["at"], shaft, UPRIGHT["_gL"]["wr"]),
        arm_down(-0.012 * wave(p, 1, 0.4)),
        opened(OPEN))


def move(p):
    return floating(p, 1.0)


def hover(p):
    return floating(p, 0.0)


# -- launch and landing --------------------------------------------------------------------------

LIFT_FRAME = 13          # his toes leave the floor (the game puffs dust)
MOVE_START_FRAMES = 36


def move_start(f):
    """Peach's float: he crouches and springs straight up; the umbrella swings off his
    shoulder out to his side and up, pops open at the top of the jump, and he catches
    under it and hangs."""
    crouch = {"hips": {"loc": (0, 0.004, -0.024), "rot": (7, 0, 0)}, "spine": {"rot": (4, 0, 0)},
              "chest": {"rot": (2, 0, 0)}, "head": {"rot": (-6, 0, 0)}}
    push = {"hips": {"loc": (0, -0.004, 0.035)}, "spine": {"rot": (-2, 0, 0)}, "head": {"rot": (-6, 0, 0)},
            "ik_foot_R": {"loc": (-0.012, 0.012, 0.022), "rot": (30, 0, -8)},
            "ik_foot_L": {"loc": (0.016, -0.016, 0.022), "rot": (30, 0, 10)}}
    keys = [(0, IDLE0),
            (8, mix(STANCE, crouch, OUT_BACK, HANG_R)),
            (LIFT_FRAME, mix(STANCE, push, OVER, HANG_R,
                             {"pole_knee_R": {"loc": (0, 0, 0.02)}, "pole_knee_L": {"loc": (0, 0, 0.02)}})),
            (20, mix(aloft(0.27, 0.03, 0.04, 30, 0.05), UPRIGHT, HANG_R, opened(8),
                     {"cape_1": {"rot": (2, 0, 0)}, "head": {"rot": (-8, 0, 0)}})),
            (25, mix(aloft(0.245, 0.02, 0.03, 36, 0.03), UPRIGHT, HANG_R, opened(OPEN + 9),
                     {"cape_1": {"rot": (6, 0, 0)}})),
            (MOVE_START_FRAMES, move(0.0))]
    return keyed(keys, f)


LAND_FRAME = 17          # his toes touch the floor
MOVE_END_FRAMES = 42


def move_end(f):
    """He floats down, reaching for the floor toe first, sinks into his knees as the
    umbrella snaps shut, and swings it back onto his shoulder."""
    absorb = mix(STANCE, {"hips": {"loc": (0, 0.004, -0.02), "rot": (5, 0, 0)}, "spine": {"rot": (2, 0, 0)},
                          "head": {"rot": (3, 0, 0)}})
    keys = [(0, hover(0.0)),
            (11, mix(aloft(0.07, -0.004, 0.006, 30, 0.002), UPRIGHT, HANG_R, opened(OPEN))),
            (LAND_FRAME, mix({"hips": {"loc": (0, 0, 0.012)},
                              "ik_foot_R": {"loc": (-0.012, 0.012, 0.016), "rot": (22, 0, -8)},
                              "ik_foot_L": {"loc": (0.016, -0.016, 0.02), "rot": (24, 0, 10)},
                              "pole_knee_R": {"loc": (0, 0, 0.012)}, "pole_knee_L": {"loc": (0, 0, 0.012)}},
                             UPRIGHT, HANG_R, opened(OPEN - 6))),
            (22, mix(absorb, UPRIGHT, HANG_R, opened(0))),
            (28, mix(STANCE, {"hips": {"loc": (0, 0, -0.01)}}, OVER, HANG_R)),
            (33, mix(STANCE, OUT_BACK, HANG_R, {"head": {"rot": (0, -6, 0)}})),
            (MOVE_END_FRAMES, IDLE0)]
    return keyed(keys, f)


# -- Tip Thrust ----------------------------------------------------------------------------------

def body_of(*parts):
    """Just the body channels of a pose (for placing a fist in the world)."""
    p = mix(*parts)
    return {b: p[b] for b in ("hips", "spine", "chest") if b in p}


SIZE_UP = mix(STANCE, {"hips": {"rot": (0, 1, -3)}, "chest": {"rot": (3, 0, -2)}, "head": {"rot": (5, 0, 4)}},
              HAT_TIP)
SALUTE_BODY = mix(STANCE, {"spine": {"rot": (-1, 0, 0)}, "chest": {"rot": (-2, 0, 0)}, "head": {"rot": (8, 0, 0)}})
SALUTE = mix(SALUTE_BODY, fist("L", (0.262, -0.1, 0.525), (-0.04, -0.06, 1.0), (-1.0, 0.0, -0.35)), HANG_R)
# en garde: side on, his left (the umbrella's) side toward the target, knees bent, the
# head turned back to look down the shaft
GUARD_FEET = mix({"ik_foot_L": {"loc": (0.01, -0.07, 0), "rot": (0, 0, -6)},
                  "ik_foot_R": {"loc": (-0.02, 0.05, 0), "rot": (0, 0, -40)}},
                 knee_ahead("L", 0.01), knee_ahead("R", -0.02))
GUARD_BODY = {"hips": {"loc": (0, 0, -0.026), "rot": (2, 0, -22)}, "spine": {"rot": (1, 0, -4)},
              "chest": {"rot": (2, 0, -4)}}
GUARD_HEAD = {"head": {"rot": (2, 0, 28)}}
LEVEL = Vector((-0.04, -1.0, 0.06))      # the umbrella pointed at the target


def guard(dy=0.0, dz=0.0, grip=(0.1, -0.15, 0.37)):
    body = mix(GUARD_BODY, {"hips": {"loc": (0, dy, dz)}})
    at = Vector(grip) + Vector((0, dy, dz))
    return mix(GUARD_FEET, body, GUARD_HEAD, fist_world("L", body, at, LEVEL, (0.2, 0.5, 1.0)), HANG_R)


THRUST_BODY = {"hips": {"loc": (0, -0.09, -0.05), "rot": (8, 0, -20)}, "spine": {"rot": (6, 0, -4)},
               "chest": {"rot": (6, 0, -4)}}
THRUST = mix(THRUST_BODY, {"head": {"rot": (-8, 0, 26)}},
             {"ik_foot_L": {"loc": (0.01, -0.17, 0), "rot": (0, 0, -6)},
              "ik_foot_R": {"loc": (-0.02, 0.05, 0), "rot": (0, 0, -40)}},
             knee_ahead("L", 0.01), knee_ahead("R", -0.02),
             fist_world("L", THRUST_BODY, (0.09, -0.31, 0.385), LEVEL, (0.2, 0.5, 1.0)), HANG_R,
             {"cape_1": {"rot": (6, 0, 0)}, "cape_2": {"rot": (4, 0, 0)}, "tabard_1": {"rot": (-6, 0, 0)}})
STEP_IN = mix(guard(-0.03, -0.035, (0.1, -0.2, 0.37)),
              {"ik_foot_L": {"loc": (0.0, -0.06, 0.035)}})
HIT_FRAME = 132
ATTACK_FRAMES = 204


def attack(f):
    """Tip Thrust: he sizes up the target, swings the umbrella off his shoulder into
    a knight's salute, settles en garde side on, draws back, and drives a fencer's lunge
    (the spike lands on hit), holds it, recovers and re-shoulders."""
    keys = [(0, IDLE0), (20, mix(SIZE_UP, carry(), HANG_R)),
            (34, mix(STANCE, OUT_BACK, HANG_R)),
            (44, mix(SALUTE_BODY, OVER, HANG_R)),
            (54, SALUTE), (66, mix(SALUTE, {"head": {"rot": (4, 0, 0)}})),
            (84, guard()), (98, guard(0, -0.004)), (108, guard(0, 0.0)),
            (118, guard(0.035, -0.036, (0.12, -0.07, 0.37))),
            (126, STEP_IN), (HIT_FRAME, THRUST),
            (142, mix(THRUST, {"hips": {"loc": (0, 0.004, 0.002)}})),
            (162, guard(0, -0.01)), (176, mix(SALUTE_BODY, UPRIGHT, HANG_R)),
            (186, mix(STANCE, OVER, HANG_R)), (194, mix(STANCE, OUT_BACK, HANG_R)),
            (ATTACK_FRAMES, IDLE0)]
    return keyed(keys, f)


# -- Lunge: lead-in, charge, strike --------------------------------------------------------------
#
# Split at the game's handoffs (the owner's pick): the lead-in ends couched, the run loop
# plays as long as the dash takes at a fixed speed, and the strike lands as he arrives.
# The umbrella is couched like a jousting lance: low at his left hip, pointed ahead.

CHARGE_SPEED = 2.6       # m/s the charge is authored for (lunge_run.speed)
RUN_FRAMES = 14          # one stride of each foot
RUN_STANCE = 0.4
RUN_STRIDE = CHARGE_SPEED * RUN_STANCE * RUN_FRAMES / FPS
RUN_LIFT = 0.05
RUN_BODY = {"hips": {"loc": (0, 0, -0.024), "rot": (9, 0, 0)}, "spine": {"rot": (6, 0, 0)}, "chest": {"rot": (4, 0, 0)}}
COUCH_AT = Vector((0.15, -0.13, 0.385))      # world, under the running body
COUCH_DIR = Vector((-0.1, -1.0, 0.0))


def couched(body, at=COUCH_AT, dy=0.0):
    return fist_world("L", body, Vector(at) + Vector((0, dy, 0)), COUCH_DIR, (0.0, 0.4, 1.0))


def lunge_run(p):
    """One stride of the couched charge: leaning in, knees driving, the right fist
    pumping, the umbrella held level at his hip, the cape streaming."""
    r, l = step(p, RUN_STRIDE, RUN_LIFT, RUN_STANCE), step((p + 0.5) % 1.0, RUN_STRIDE, RUN_LIFT, RUN_STANCE)
    bounce = 0.008 * abs(math.cos(2 * math.pi * p))
    body = mix(RUN_BODY, {"hips": {"loc": (0, 0, bounce - 0.008), "rot": (0, 0, 3 * wave(p, 1))},
                          "chest": {"rot": (0, 0, -3 * wave(p, 1))}})
    pump = wave(p, 1)
    return mix(body, {"ik_foot_R": r, "ik_foot_L": l, "head": {"rot": (-14, 0, 0)},
                      "cape_1": {"rot": (16, 0, 0)}, "cape_2": {"rot": (12 + 3 * wave(p, 2), 0, 0)},
                      "cape_3": {"rot": (12 + 4 * wave(p, 2, -0.7), 0, 0)}},
               knee_ahead("R", 0.0), knee_ahead("L", 0.0),
               couched(body, dy=0.004 * pump),
               fist("R", (-0.16, -0.04 + 0.05 * pump, 0.39 + 0.015 * abs(pump)), (0.0, -1.0, 0.4), (0.2, 0.4, 1.0)))


LUNGE_FRAMES = 90
PAW = mix(STANCE, {"hips": {"loc": (0, 0.01, -0.02), "rot": (8, 0, 0)}, "spine": {"rot": (4, 0, 0)},
                   "chest": {"rot": (2, 0, 0)}, "head": {"rot": (-10, 0, 0)}})


def lunge(f):
    """The lead-in: he sizes up the target, swings the umbrella off his shoulder,
    upright, then down level and couches it at his hip, leans in and paws the floor
    with his right foot like a bull, then coils into the charge."""
    level_side = fist("L", (0.25, -0.09, 0.45), (-0.02, -1.0, 0.06), (-1.0, 0.3, 0.3))
    paw_body = body_of(PAW)

    def paw(dy, dz):
        return mix(PAW, couched(paw_body, (0.15, -0.1, 0.385)), HANG_R,
                   {"ik_foot_R": {"loc": (0, dy, dz), "rot": (12 if dz else 0, 0, 0)}})
    keys = [(0, IDLE0), (14, mix(SIZE_UP, carry(), HANG_R)),
            (26, mix(STANCE, OUT_BACK, HANG_R)), (36, mix(STANCE, OVER, HANG_R)),
            (44, mix(SALUTE_BODY, UPRIGHT, HANG_R)),
            (54, mix(STANCE, level_side, HANG_R)),
            (62, paw(0.0, 0.0)), (67, paw(-0.02, 0.025)), (72, paw(0.06, 0.0)), (77, paw(-0.02, 0.025)),
            (82, paw(0.06, 0.0)), (LUNGE_FRAMES, lunge_run(0.0))]
    return keyed(keys, f)


STRIKE_HIT = 12
STRIKE_FRAMES = 88


def lunge_strike(f):
    """He arrives: a last plant and the spike driven home on hit, a skid as the charge
    runs out, then he straightens and re-shoulders."""
    plant_body = mix(RUN_BODY, {"hips": {"loc": (0, -0.02, -0.02), "rot": (4, 0, 0)}})
    plant = mix(plant_body, {"head": {"rot": (-12, 0, 0)}, "cape_1": {"rot": (16, 0, 0)}, "cape_2": {"rot": (12, 0, 0)},
                             "cape_3": {"rot": (12, 0, 0)},
                             "ik_foot_L": {"loc": (0.01, -0.1, 0)}, "ik_foot_R": {"loc": (-0.01, 0.08, 0.01), "rot": (20, 0, 0)}},
                knee_ahead("R", 0.0), knee_ahead("L", 0.0), couched(plant_body, dy=-0.02), HANG_R)
    hit_body = mix(RUN_BODY, {"hips": {"loc": (0, -0.05, -0.03), "rot": (6, 0, 0)}})
    hit = mix(hit_body, {"head": {"rot": (-14, 0, 0)}, "cape_1": {"rot": (14, 0, 0)}, "cape_2": {"rot": (10, 0, 0)},
                         "cape_3": {"rot": (10, 0, 0)},
                         "ik_foot_L": {"loc": (0.01, -0.13, 0)}, "ik_foot_R": {"loc": (-0.01, 0.07, 0.008), "rot": (24, 0, 0)}},
              knee_ahead("R", 0.0), knee_ahead("L", 0.0),
              fist_world("L", hit_body, (0.13, -0.27, 0.39), COUCH_DIR, (0.0, 0.4, 1.0)), HANG_R)
    skid_body = {"hips": {"loc": (0, -0.03, -0.03), "rot": (-6, 0, 0)}, "spine": {"rot": (-2, 0, 0)}}
    skid = mix(skid_body, {"head": {"rot": (2, 0, 0)},
                           "ik_foot_L": {"loc": (0.01, -0.12, 0.0), "rot": (-14, 0, 0)},
                           "ik_foot_R": {"loc": (-0.01, 0.0, 0.0), "rot": (0, 0, -10)}},
               knee_ahead("R", 0.0), knee_ahead("L", 0.0),
               fist_world("L", skid_body, (0.16, -0.14, 0.4), (-0.1, -1.0, 0.15), (0.0, 0.4, 1.0)), HANG_R)
    keys = [(0, lunge_run(0.0)), (6, plant), (STRIKE_HIT, hit), (16, hit), (30, skid),
            (44, mix(STANCE, fist("L", (0.25, -0.09, 0.45), (-0.02, -1.0, 0.06), (-1.0, 0.3, 0.3)), HANG_R)),
            (56, mix(SALUTE_BODY, UPRIGHT, HANG_R)), (66, mix(STANCE, OVER, HANG_R)),
            (74, mix(STANCE, OUT_BACK, HANG_R)), (STRIKE_FRAMES, IDLE0)]
    return keyed(keys, f)


# -- Canopy --------------------------------------------------------------------------------------

CANOPY_OPEN = 72         # frame it stands open over him and his neighbours
CANOPY_FRAMES = 192
TIPTOE = {"hips": {"loc": (0, 0, 0.018)},
          "ik_foot_R": {"loc": (-0.012, 0.012, 0.018), "rot": (22, 0, -8)},
          "ik_foot_L": {"loc": (0.016, -0.016, 0.018), "rot": (22, 0, 10)},
          "pole_knee_R": {"loc": (0, 0, 0.018)}, "pole_knee_L": {"loc": (0, 0, 0.018)}}


def canopy_art(f):
    """Canopy (quiet): he looks round at his neighbours, swings the umbrella off his
    shoulder and up, springs it open and raises it high and wide over them on tiptoe,
    holds it (open), then closes it and re-shoulders."""
    look = mix(STANCE, {"head": {"rot": (0, 0, 16)}, "chest": {"rot": (0, 0, 4)}}, HAT_TIP)
    high = mix(TIPTOE, {"chest": {"rot": (-2, -2, 0)}, "head": {"rot": (-10, 0, -6)}}, RAISED, HANG_R,
               opened(OPEN))
    keys = [(0, IDLE0), (16, mix(look, carry(), HANG_R)),
            (30, mix(STANCE, OUT_BACK, HANG_R)), (40, mix(STANCE, OVER, HANG_R)),
            (48, mix(STANCE, UPRIGHT, HANG_R)),
            (53, mix(STANCE, UPRIGHT, HANG_R, opened(OPEN + 10), {"head": {"rot": (-6, 0, 0)}})),
            (58, mix(STANCE, UPRIGHT, HANG_R, opened(OPEN - 3))),
            (CANOPY_OPEN, high),
            (100, mix(high, {"hips": {"rot": (0, 0, 4)}, "head": {"rot": (0, 0, 12)}})),
            (124, mix(high, {"hips": {"rot": (0, 0, -3)}, "head": {"rot": (0, 0, -10)}})),
            (140, high),
            (152, mix(STANCE, UPRIGHT, HANG_R, opened(0))),
            (164, mix(STANCE, OVER, HANG_R)), (174, mix(STANCE, OUT_BACK, HANG_R)),
            (CANOPY_FRAMES, IDLE0)]
    return keyed(keys, f)


# -- Raincheck -----------------------------------------------------------------------------------

RC_OPEN, RC_SHIELD, RC_END = 66, 166, 250
RAINCHECK_FRAMES = 312
SPIN_FROM, SPIN_TO = 76, 148
# planted before him as a shield: the canopy's dome angled into the rain toward the
# target (the game turns him to the nearest enemy that can shoot first), the shaft
# pointing ahead and up about 40 degrees so he shows under it, braced in a wide stance
SHIELD_BODY = {"hips": {"loc": (0, 0.01, -0.03), "rot": (6, 0, -6)}, "spine": {"rot": (3, 0, -2)},
               "chest": {"rot": (2, 0, -2)}}
SHIELD_FEET = mix({"ik_foot_L": {"loc": (0.03, -0.05, 0), "rot": (0, 0, 6)},
                   "ik_foot_R": {"loc": (-0.03, 0.05, 0), "rot": (0, 0, -18)}},
                  knee_ahead("L", 0.03), knee_ahead("R", -0.03))
SHIELD = mix(SHIELD_BODY, SHIELD_FEET, {"head": {"rot": (-4, 0, 8)}},
             fist_world("L", SHIELD_BODY, (0.13, -0.13, 0.37), (-0.12, -0.78, 0.66), (0.0, 0.7, 0.7)),
             HANG_R, opened(OPEN))


def spin(f):
    """The twirl: two turns of the shaft in his fist, easing in and out."""
    return {"_spin": {"v": (720.0 * smooth((f - SPIN_FROM) / (SPIN_TO - SPIN_FROM)), 0.0, 0.0)}}


def raincheck(f):
    """Raincheck (signature): he looks up at the sky, swings the umbrella up and snaps it
    open with a flourish (open), twirls it overhead under the game's rain, then plants it
    angled before him like a shield (shield) and braces behind it, closes it (end) and
    bows, and re-shoulders."""
    # (looking up with the chest: tipping the head back lowers the brim onto the umbrella)
    sky = mix(STANCE, {"spine": {"rot": (-2, 0, 0)}, "chest": {"rot": (-4, 0, 0)}}, HAT_TIP)
    twirl = mix(TIPTOE, {"chest": {"rot": (-3, 0, 0)}, "head": {"rot": (-12, 0, 6)}}, RAISED, HANG_R,
                opened(OPEN))
    bow_body = mix(STANCE, {"hips": {"rot": (6, 0, 0)}, "spine": {"rot": (10, 0, 0)}, "chest": {"rot": (10, 0, 0)}})
    # the right arm swept out to his side in the flourish of the bow
    bow = mix(bow_body, {"head": {"rot": (10, 0, 0)}}, OUT_BACK,
              fist("R", (-0.2, -0.07, 0.4), (-0.3, -1.0, 0.2), (0.6, 0.2, 0.8)))
    keys = [(0, IDLE0), (18, mix(sky, carry(), HANG_R)),
            (32, mix(STANCE, OUT_BACK, HANG_R)), (42, mix(STANCE, OVER, HANG_R)),
            (52, mix(STANCE, UPRIGHT, HANG_R, {"head": {"rot": (-8, 0, 0)}})),
            (60, mix(STANCE, UPRIGHT, HANG_R, {"head": {"rot": (-10, 0, 0)}, "chest": {"rot": (2, 0, 0)}})),
            (RC_OPEN, mix(STANCE, UPRIGHT, HANG_R, opened(OPEN + 10), {"head": {"rot": (-10, 0, 0)},
                                                                         "chest": {"rot": (-3, 0, 0)}})),
            (72, mix(STANCE, UPRIGHT, HANG_R, opened(OPEN - 3))),
            (SPIN_FROM, twirl),
            (112, mix(twirl, {"hips": {"rot": (0, 0, 6)}, "head": {"rot": (0, 0, 8)}})),
            (SPIN_TO, mix(twirl, {"hips": {"rot": (0, 0, -4)}})),
            (156, mix(STANCE, UPRIGHT, HANG_R, opened(OPEN))),
            (RC_SHIELD, SHIELD),
            (172, mix(SHIELD, {"hips": {"loc": (0, 0.006, -0.004)}})),
            (200, mix(SHIELD, {"chest": {"rot": (-1, 0, 0)}})), (230, SHIELD),
            (240, mix(STANCE, UPRIGHT, HANG_R, opened(OPEN))),
            (RC_END, mix(STANCE, UPRIGHT, HANG_R, opened(0))),
            (258, mix(STANCE, OVER, HANG_R)), (266, mix(STANCE, OUT_BACK, HANG_R)),
            (280, bow), (290, bow),
            (300, mix(STANCE, OUT_BACK, HANG_R)), (RAINCHECK_FRAMES, IDLE0)]
    pose = keyed(keys, f)
    if f >= SPIN_FROM:
        pose = mix(pose, spin(f))
    return pose


# -- reactions -----------------------------------------------------------------------------------

HURT_FRAMES = 36


def hurt(f):
    """A flinch: the hat jolts, the umbrella wobbles on his shoulder."""
    recoil = mix(STANCE, {"hips": {"loc": (0, 0.014, -0.008), "rot": (-5, 0, 0)}, "chest": {"rot": (-9, 0, 4)},
                          "head": {"rot": (-7, -12, -6)}, "cape_1": {"rot": (4, 0, 0)}}, carry(-6), HANG_R)
    keys = [(0, IDLE0), (5, recoil),
            (14, mix(STANCE, {"chest": {"rot": (3, 0, -1)}, "head": {"rot": (4, -12, 2)},
                              "hips": {"loc": (0, -0.003, 0)}}, carry(2), HANG_R)),
            (24, mix(STANCE, HAT_TIP, carry(-1), HANG_R)), (HURT_FRAMES, IDLE0)]
    return keyed(keys, f)


BROKEN_FRAMES = 150
POP_FRAME, LET_GO, TENT_LAND = 44, 50, 92
# where the umbrella comes to rest: its handle on the floor behind him to his left, the
# canopy half open and leaning over him like a little tent
TENT = {"at": (0.22, 0.38, 0.03), "fwd": (-0.18, -0.32, 0.86), "wr": (0.0, 0.0, 1.0)}
TENT_OPEN = 66.0


def free(at, fwd, wr=(0.0, 0.0, 1.0), w=1.0):
    return {"_free": {"w": (w, 0, 0), "at": tuple(at), "fwd": tuple(fwd), "wr": tuple(wr)}}


def broken(f):
    """His knees buckle and he sits down hard, slumping forward; the umbrella slides
    off his shoulder, pops open by itself, flies up out of his hand and lands over him
    like a little tent."""
    sag_body = {"hips": {"loc": (0, -0.01, -0.06), "rot": (6, 0, 0)}, "spine": {"rot": (6, 0, 0)},
                "chest": {"rot": (6, 0, -3)}}
    sag = mix(sag_body, {"head": {"rot": (6, 0, -4)},
                         "ik_foot_R": {"loc": (-0.012, 0.012, 0), "rot": (0, 0, -8)},
                         "ik_foot_L": {"loc": (0.016, -0.016, 0), "rot": (0, 0, 10)}},
              knee_ahead("R", -0.012), knee_ahead("L", 0.016),
              fist("L", (0.235, -0.02, 0.43), (0.12, 0.9, -0.4), (-0.7, 0.0, -0.7)), HANG_R)
    sit_body = {"hips": {"loc": (0, 0.02, -0.2), "rot": (-4, 0, 0)}, "spine": {"rot": (14, 0, 0)},
                "chest": {"rot": (16, 0, -4)}}
    sit = mix(sit_body, {"head": {"rot": (12, 0, -8)},
                         "ik_foot_R": {"loc": (-0.03, -0.12, 0.0), "rot": (-30, 0, -14)},
                         "ik_foot_L": {"loc": (0.03, -0.13, 0.0), "rot": (-30, 0, 16)},
                         "pole_knee_R": {"loc": (-0.04, -0.1, 0.1)}, "pole_knee_L": {"loc": (0.04, -0.1, 0.1)},
                         "cape_1": {"rot": (4, 0, 0)},
                         # the tabard laid along his raised thighs, its point drooping off his knees
                         "tabard_1": {"rot": (-50, 0, 0)}, "tabard_2": {"rot": (30, 0, 0)}},
              fist_world("L", sit_body, (0.13, -0.1, 0.15), (0.0, -1.0, -0.3), (-0.3, 0.3, 1.0)),
              fist_world("R", sit_body, (-0.13, -0.1, 0.15), (0.0, -1.0, -0.3), (0.3, 0.3, 1.0)))
    keys = [(0, IDLE0),
            (6, mix(STANCE, {"hips": {"loc": (0, 0.014, -0.008), "rot": (-5, 0, 0)}, "chest": {"rot": (-9, 0, 4)},
                             "head": {"rot": (-7, -12, -6)}}, carry(-4), HANG_R)),
            (20, mix(STANCE, {"hips": {"loc": (0, 0.01, -0.02)}, "chest": {"rot": (-4, 0, 0)}}, HAT_TIP,
                     carry(-8), HANG_R)),
            (POP_FRAME - 4, sag), (POP_FRAME, mix(sag, opened(20))),
            (LET_GO, mix(sag, opened(56))),
            (80, sit), (96, mix(sit, {"hips": {"loc": (0, 0, 0.008)}})), (108, sit),
            (BROKEN_FRAMES, mix(sit, {"spine": {"rot": (2, 0, 0)}, "head": {"rot": (3, 0, 0)}}))]
    pose = keyed(keys, f)
    if f >= LET_GO:
        # out of his hand: up and turning over his head, then down onto him, a bounce
        s = sag
        held = settle(mix(s, opened(56)))["_held"]
        flight = [(LET_GO, mix(free(held["at"], held["fwd"], held["wr"]), opened(56))),
                  (66, mix(free((0.22, 0.12, 0.62), (-0.1, -0.7, 0.75)), opened(TENT_OPEN + 14))),
                  (TENT_LAND, mix(free(TENT["at"], TENT["fwd"], TENT["wr"]), opened(TENT_OPEN))),
                  (100, mix(free(Vector(TENT["at"]) + Vector((0, 0, 0.02)), TENT["fwd"], TENT["wr"]),
                            opened(TENT_OPEN + 4))),
                  (108, mix(free(TENT["at"], TENT["fwd"], TENT["wr"]), opened(TENT_OPEN))),
                  (BROKEN_FRAMES, mix(free(TENT["at"], TENT["fwd"], TENT["wr"]), opened(TENT_OPEN)))]
        fl = keyed(flight, f)
        pose["_free"] = fl["_free"]
        pose["_open"] = fl["_open"]
    return pose


# -- clips -------------------------------------------------------------------------------------

CLIPS = {
    "idle": (IDLE_FRAMES, True, lambda f: idle(f / IDLE_FRAMES)),
    "move_start": (MOVE_START_FRAMES, False, move_start),
    "move": (MOVE_FRAMES, True, lambda f: move(f / MOVE_FRAMES)),
    "hover": (HOVER_FRAMES, True, lambda f: hover(f / HOVER_FRAMES)),
    "move_end": (MOVE_END_FRAMES, False, move_end),
    "attack": (ATTACK_FRAMES, False, attack),
    "lunge": (LUNGE_FRAMES, False, lunge),
    "lunge_run": (RUN_FRAMES, True, lambda f: lunge_run(f / RUN_FRAMES)),
    "lunge_strike": (STRIKE_FRAMES, False, lunge_strike),
    "canopy": (CANOPY_FRAMES, False, canopy_art),
    "raincheck": (RAINCHECK_FRAMES, False, raincheck),
    "hurt": (HURT_FRAMES, False, hurt),
    "broken": (BROKEN_FRAMES, False, broken),
}
GROUPS = {"travel": ["idle", "move_start", "move", "hover", "move_end"],
          "attack": ["attack", "lunge", "lunge_run", "lunge_strike"],
          "arts": ["canopy", "raincheck"], "reactions": ["hurt", "broken"]}

# Moments the game times itself by (seconds)
CLIP_EVENTS = {
    "move_start": {"lift": LIFT_FRAME / FPS},
    "move": {"speed": RUN_SPEED},
    "move_end": {"land": LAND_FRAME / FPS},
    "attack": {"hit": HIT_FRAME / FPS},
    "lunge": {"charge": LUNGE_FRAMES / FPS},
    "lunge_run": {"speed": CHARGE_SPEED},
    "lunge_strike": {"hit": STRIKE_HIT / FPS},
    "canopy": {"open": CANOPY_OPEN / FPS},
    "raincheck": {"open": RC_OPEN / FPS, "shield": RC_SHIELD / FPS, "end": RC_END / FPS},
}


# -- physical fix-ups ----------------------------------------------------------------------------

CAPE_TURN_LAG = 0.25     # share of the body's turn the cape hangs back from
TABARD_KNEE = 300.0      # degrees per metre a foot rises (off the hips' height) the tabard lifts with the knee


def settle(pose):
    """The fists close where the pose puts them (moving with his chest; the right arm
    hangs with gravity at rest) and the umbrella rides in the left one (or flies free);
    the canopy opens; the cape lies on his back through every lean (swinging only
    back, lagging turns); the tabard swings forward with
    the leading leg and a raised knee."""
    pose = {k: dict(v) for k, v in pose.items()}
    pt, vec, _, _ = body_xform(pose)
    held = None
    hang = min(1.0, max(0.0, pose.pop("_hangR", {}).get("w", (0, 0, 0))[0]))
    for side in ("R", "L"):
        g = pose.pop("_g" + side, None)
        if g is None:
            continue
        at, fwd, wr = pt(g["at"]), vec(g["fwd"]).normalized(), vec(g["wr"])
        if side == "R" and hang > 0:
            # hanging: under the shoulder wherever the body puts it, turned only with
            # his heading, not tipped with his lean
            yaw = Quaternion((0, 0, 1), math.radians(sum(
                pose.get(b, {}).get("rot", (0, 0, 0))[2] for b in ("hips", "spine", "chest"))))
            sh = SHOULDER["R"]
            at = at.lerp(pt(sh) + yaw @ (Vector(g["at"]) - sh), hang)
            fwd = fwd.lerp(yaw @ Vector(g["fwd"]).normalized(), hang).normalized()
            wr = wr.lerp(yaw @ Vector(g["wr"]), hang)
        q = turn_to(side, fwd, wr)
        # out of reach: the grip (and what it holds) comes in toward the shoulder
        wrist0, grip0, _, _ = REST[side]
        sh = pt(SHOULDER[side])
        wrist = at - q @ (grip0 - wrist0)
        if (wrist - sh).length > REACH:
            at = at + (sh + (wrist - sh).normalized() * REACH - wrist)
        pose.update(ik_grip(side, at, q))
        if side == "L":
            held = (at, fwd, wr)
    spin_deg = pose.pop("_spin", {}).get("v", (0, 0, 0))[0]
    fr = pose.pop("_free", None)
    if held:
        at, fwd, wr = held
        if fr and fr["w"][0] > 0:
            w = min(1.0, fr["w"][0])
            at = at.lerp(Vector(fr["at"]), w)
            fwd = fwd.lerp(Vector(fr["fwd"]).normalized(), w).normalized()
            wr = wr.lerp(Vector(fr["wr"]), w)
        q = Quaternion(fwd, math.radians(spin_deg)) @ turn_to("L", fwd, wr)
        pose["lance"] = {"rot": tuple(math.degrees(a) for a in q.to_euler("XYZ")),
                         "loc": tuple(at - REST["L"][1])}
        pose["_held"] = {"at": tuple(at), "fwd": tuple(fwd), "wr": tuple(wr)}
    deg = pose.pop("_open", {}).get("v", (0, 0, 0))[0]
    pose.update(canopy(deg))

    def rot(bone):
        return pose.get(bone, {}).get("rot", (0.0, 0.0, 0.0))

    body = [sum(rot(b)[i] for b in ("hips", "spine", "chest")) for i in range(3)]
    # it lies on his back and the skirt through every lean forward (it hangs close, so
    # hanging plumb would swing its hem into the skirt); leaning back, it hangs off his
    # shoulders as the hips carry it, not tipped forward into the skirt by the back. It
    # swings back further only where a clip lifts it (trailing in the float and the charge).
    x, y, z = rot("cape_1")
    back = max(0.0, -(rot("spine")[0] + rot("chest")[0]))
    pose.setdefault("cape_1", {})["rot"] = (max(x, 0.0) + back, y - body[1], z - CAPE_TURN_LAG * body[2])
    hz = pose.get("hips", {}).get("loc", (0, 0, 0))[2]
    swing = 0.0
    for side in ("R", "L"):                  # with the leading leg, and a knee raised
        fx, fy, fz = pose.get("ik_foot_" + side, {}).get("loc", (0, 0, 0))
        swing = max(swing, 120.0 * max(0.0, -fy) + TABARD_KNEE * max(0.0, fz - max(hz, 0.0)))
    swing = min(swing, 40.0)
    hx, hy, hz = rot("hips")
    tx, ty, tz = rot("tabard_1")
    # (it hangs plumb through a forward lean; leaning back, it lies on the skirt)
    pose.setdefault("tabard_1", {})["rot"] = (tx - swing - max(hx, 0.0), ty - hy, tz)
    return pose


def _apply(pose):
    """settle() for keying: drops the bookkeeping it leaves for broken's hand-off."""
    pose = settle(pose)
    pose.pop("_held", None)
    return pose


def animate_umbrella(obj=None, clips=None):
    obj = obj or bpy.data.objects[OBJECT]
    rig = obj.parent
    toyanim.read_rest(rig)
    read_rest(rig)
    chosen = {k: CLIPS[k] for k in (clips or CLIPS)}
    if clips:          # just these: key them, keep the rest
        for name, (frames, loops, pose_at) in chosen.items():
            toyanim.key_clip(rig, name, frames, loops, pose_at, _apply)
        rig.animation_data.action = bpy.data.actions[toyanim.action_name(rig, "idle")]
    else:
        toyanim.animate(rig, CLIPS, _apply)
    toyanim.write_events(os.path.join(BUILD["CHAR"].out_dir, "umbrella_lancer_events.json"), CLIP_EVENTS)
    if not bpy.app.background:   # an "Umbrella Lancer" tab in the 3D view's sidebar (N) to play each clip
        toyanim.register_clip_panel(rig, CLIPS, "Umbrella Lancer")
    return rig


def clip_check(obj=None, every=1, clips=None):
    obj = obj or bpy.data.objects[OBJECT]
    chosen = {k: CLIPS[k] for k in (clips or CLIPS)}
    return toyanim.clip_check(obj, chosen, toy3d.clip_report, every)


def grip_check(obj=None, clips=None, tol=0.003):
    """Frames where a fist falls short of its grip (the arm can't reach it), or the
    umbrella isn't in the left fist while it's held: {clip: (worst m, frame, what)}."""
    obj = obj or bpy.data.objects[OBJECT]
    rig = obj.parent
    out = {}
    for name in (clips or CLIPS):
        frames, _, pose_at = CLIPS[name]
        worst = (0.0, 0, "")
        for f in range(frames + 1):
            toyanim.play(rig, name, f)
            pb = rig.pose.bones
            for side in ("R", "L"):
                d = (pb["hand_" + side].head - pb["ik_hand_" + side].head).length
                if d > worst[0]:
                    worst = (d, f, "reach_" + side)
            if "_free" not in pose_at(f):
                d = (pb["hand_L"].tail - pb["lance"].head).length
                if d > worst[0]:
                    worst = (d, f, "lance")
        if worst[0] > tol:
            out[name] = (round(worst[0], 4), worst[1], worst[2])
    toyanim.play(rig, "idle", 0)
    return out


def render_group(obj, group, frames_per_clip=8, res=256, cam=None):
    """Contact-sheet frames for a group of clips into source/anim/ (stitched outside Blender)."""
    shoot = toy3d.preview_camera(obj)
    chosen = {k: CLIPS[k] for k in GROUPS[group]}
    cam = cam or ((-2.3, -3.6, 1.7), (0.0, 0.0, 0.62))
    return toyanim.render_strips(obj, chosen, shoot, frames_per_clip, res, "anim", cam)


# The cloth chains the game's spring bones swing (UnitSprings), written beside the GLB.
SPRINGS = {"cape": ["cape_1", "cape_2", "cape_3"], "tabard": ["tabard_1", "tabard_2"]}
SPRINGS.update({f"drop_{i}": [f"hat_tip_{i}"] for i in range(8)})      # the hat's gold drops ("drop" kind)


if __name__ == "__main__" and bpy.app.background:
    o = bpy.data.objects[OBJECT]          # (built as the script loaded)
    animate_umbrella(o)
    print("clipping per clip", {k: v for k, v in clip_check(o, 2).items() if v})
    print("grips", grip_check(o))
    print("glb", toy3d.export_glb(o))
    print("springs", toy3d.export_springs(o, SPRINGS))
