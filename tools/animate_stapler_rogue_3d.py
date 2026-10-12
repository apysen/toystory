"""Keyframe the 3D Stapler Rogue's battle clips at 60 fps (Blender).

Live, through the Blender MCP, after build_stapler_rogue_3d.py has built the model:
    exec(open("tools/animate_stapler_rogue_3d.py").read())   then  animate_stapler()
which also adds a "Stapler Rogue" tab to the 3D view's sidebar (N) with a
button that plays each clip.
Headless (builds, animates, exports the GLB):
    D:/Blender/blender.exe --background --python tools/animate_stapler_rogue_3d.py

Clips use the game's names (docs/character_abilities_stats.md) and follow the
concept sheet assets/concept/animations/stapler.png where it has them:
  loop      idle (the concept's wide stance, one pistol up), move (the concept's
            Dash/Evade as his travel: a Naruto run)
  play once attack (Staple Shot: one quick shot), staple_burst (Staple Burst:
            the concept's twin shots, alternating), pin (Pin: the concept's
            pinning shot, a steadied, charged heavy shot), staple_storm (his
            signature, Staple Storm: a leaping spin into volleys fired all round),
            hurt, broken
Poses and keying work as in tools/toyanim.py.
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
import toyanim  # noqa: E402
importlib.reload(toyanim)
from toyanim import (FPS, wave, smooth, keyed, add, mix, step, feet_in, knee_ahead, lowered)  # noqa: E402

BUILD = {"__name__": "stapler_build", "__file__": os.path.join(_TOOLS, "build_stapler_rogue_3d.py")}
exec(compile(open(BUILD["__file__"], encoding="utf-8").read(), BUILD["__file__"], "exec"), BUILD)
toy3d = BUILD["toy3d"]

# rest positions off the rig (metres)
CENTRE_X = -0.031
WRIST = {"R": Vector((-0.225, -0.081, 0.404)), "L": Vector((0.162, -0.081, 0.404))}
SHOULDER = {"R": Vector((-0.141, 0.0, 0.523)), "L": Vector((0.078, 0.0, 0.523))}
FOOT = {"R": Vector((-0.172, -0.01, 0.078)), "L": Vector((0.125, -0.01, 0.078))}
AIM_YAW = {"R": 16.0, "L": -16.0}   # turns the rest pistols (angled out) to point straight ahead


def hand(side, at, yaw=0.0, pitch=0.0, roll=0.0):
    """Wrist at world point `at`, pistol aimed straight ahead turned by yaw
    (degrees, + to his left), pitch (+ muzzle down) and roll."""
    return {f"ik_hand_{side}": {"loc": tuple(Vector(at) - WRIST[side]),
                                "rot": (pitch, roll, AIM_YAW[side] + yaw)}}


def recoil(side, back=0.03, kick=18.0):
    """Added to an aimed hand: the shot shoves it back and flips the muzzle up."""
    return {f"ik_hand_{side}": {"loc": (0, back, 0.4 * back), "rot": (-kick, 0, 0)}}


def cloth(cloak=(0, 0, 0), scarf=(0, 0)):
    out = {f"cloak_{i + 1}": {"rot": (c, 0, 0)} for i, c in enumerate(cloak)}
    out.update({f"scarf_{i + 1}": {"rot": s if isinstance(s, tuple) else (s, 0, 0)} for i, s in enumerate(scarf)})
    return out


def spin(pose, deg):
    """Turn the whole body deg about his centre line without the root (whose
    motion the game strips): the hips turn, and the hand, foot and knee
    targets swing round the centre with them."""
    rot = Matrix.Rotation(math.radians(deg), 3, "Z")
    out = {k: dict(v) for k, v in pose.items()}
    out.setdefault("hips", {})["rot"] = add(out.get("hips", {}).get("rot", (0, 0, 0)), (0, 0, deg))
    out["hips"]["spin"] = (deg,)          # settle leaves the spin out of the cloth's lag
    for name, rest in (("ik_hand_R", WRIST["R"]), ("ik_hand_L", WRIST["L"]), ("ik_foot_R", FOOT["R"]),
                       ("ik_foot_L", FOOT["L"])) + tuple((f"pole_knee_{s}", toyanim.KNEE_REST[s][3])
                                                       for s in "RL" if s in toyanim.KNEE_REST):
        ch = out.setdefault(name, {})
        p = rest + Vector(ch.get("loc", (0, 0, 0)))
        c = Vector((CENTRE_X, 0.0, p.z))
        ch["loc"] = tuple(c + rot @ (p - c) - rest)
        if not name.startswith("pole"):
            ch["rot"] = add(ch.get("rot", (0, 0, 0)), (0, 0, deg))
    return out


# -- stance --------------------------------------------------------------------

# the concept's wide stance: right foot out and forward, left foot back, knees bent
WIDE = {"ik_foot_R": {"loc": (-0.03, -0.035, 0), "rot": (0, 0, -8)},
        "ik_foot_L": {"loc": (0.035, 0.04, 0), "rot": (0, 0, 10)}}
GUN_UP_R = hand("R", (-0.175, -0.16, 0.5), yaw=4, pitch=-14)       # raised beside him, aimed up and out
GUN_LOW_L = hand("L", (0.155, -0.13, 0.37), yaw=-10, pitch=22)     # low by his hip, muzzle down
AIM_R = hand("R", (-0.135, -0.2, 0.5))                               # straight out at the target
AIM_L = hand("L", (0.072, -0.2, 0.5))


def idle(p):
    """Two-second breathing loop in the concept's stance: wide and low, the
    right pistol raised, the left hanging ready, cloak and scarf stirring."""
    breath = wave(p, 1, -math.pi / 2)
    lift = 0.5 + 0.5 * breath
    return mix(WIDE, GUN_UP_R, GUN_LOW_L, lowered(-0.022 - 0.003 * (1 - lift)), cloth(
        (2 + 1.0 * wave(p, 1, -0.5), 2 + 1.5 * wave(p, 1, -1.0), 2.5 + 2 * wave(p, 1, -1.5)),
        ((2 * wave(p, 1, -0.6), 0, 3 * wave(p, 1, -0.3)), (3 * wave(p, 1, -1.2), 0, 5 * wave(p, 1, -0.9)))), {
        "hips": {"rot": (2, 0, -6)},
        "spine": {"rot": (1 - 0.6 * breath, 0, -3)},
        "chest": {"rot": (2 - 1.4 * breath, 0, -4 + 0.8 * wave(p, 1, 1.0))},
        "head": {"rot": (-2 + 1.5 * wave(p, 1, -1.4), 1.5 * wave(p, 1, -1.1), 8 + 3 * wave(p, 1, 0.4))},
        "ik_hand_R": {"loc": (0, 0, 0.004 * breath), "rot": (1.5 * wave(p, 1, -0.4), 0, 0)},
        "ik_hand_L": {"loc": (0, 0.002 * wave(p, 1, -0.5), 0.003 * wave(p, 1, -0.5))},
    }, knee_ahead("R", -0.03), knee_ahead("L", 0.035))


# -- travel: the dash-run --------------------------------------------------------

RUN_SPEED = 1.8         # m/s, the game's travel pace
DASH_FRAMES = 20        # two strides a loop: six steps a second
DASH_STANCE = 0.35      # share of a stride a foot is on the floor; the rest is flight
DASH_STRIDE = RUN_SPEED * DASH_STANCE * DASH_FRAMES / FPS
DASH_LIFT = 0.055
NARROW_R, NARROW_L = 0.085, 0.10   # m each foot moves in, under its hip
TOE_IN = 32


# Naruto run: the body pitched 65 degrees forward, arms swept straight back
DASH_LEAN = {"hips": 20.0, "spine": 22.0, "chest": 23.0}   # degrees forward each, 65 in all (the hips
                                                            # least, so the thighs don't fold into the belt)
DASH_DROP = -0.05                                           # m the hips sink
PIVOT = {"hips": Vector((CENTRE_X, 0.0, 0.344)), "spine": Vector((CENTRE_X, 0.0, 0.438)),
         "chest": Vector((CENTRE_X, 0.0, 0.516))}


def leaned(point, lean=DASH_LEAN, drop=DASH_DROP):
    """Where a rest point on the upper body ends up with the body pitched forward
    by `lean` (chest about its joint, then spine, then hips) and the hips dropped."""
    p = Vector(point)
    for bone in ("chest", "spine", "hips"):
        rot = Matrix.Rotation(math.radians(lean[bone]), 3, "X")
        p = PIVOT[bone] + rot @ (p - PIVOT[bone])
    return p + Vector((0, 0, drop))


def swept_back(side, bob):
    """A hand flung straight back from its leaned shoulder, the pistol trailing."""
    total = math.radians(sum(DASH_LEAN.values()))
    along = Vector((0.0, math.sin(total), -math.cos(total)))           # down his back, shoulders to hips
    back = (Vector((0.0, 1.0, 0.0)) * DASH_ARMS[0] + along * DASH_ARMS[1]).normalized()
    out = Vector((-1.0 if side == "R" else 1.0, 0.0, 0.0))
    at = leaned(SHOULDER[side]) + back * 0.2 + out * DASH_ARMS[2] + Vector((0, 0, bob))
    # swinging the arm back rolls the pistol over with it: it hangs under the hand,
    # purple top to the ground, barrel trailing back and angled down
    return hand(side, at, yaw=-2 * AIM_YAW[side], pitch=180 - DASH_GUN_DIP)


def dash(p):
    """The concept's dash as a Naruto run: pitched 65 degrees forward, head up
    looking ahead, both arms swept straight back with the pistols trailing,
    long bounding strides under him, cloak and scarf streaming out behind
    along his back."""
    stride = math.cos(2 * math.pi * p)                    # +1: right foot forward
    flight = 0.5 - 0.5 * math.cos(4 * math.pi * p)        # 0 at each foot strike, 1 mid-flight
    rise = 0.018 * flight
    body = (-0.004 * math.sin(2 * math.pi * (p + 0.1)), 0, DASH_DROP + rise)
    bob = rise + 0.004 * wave(p, 2, -0.6)
    pose = {
        "hips": {"loc": body, "rot": (DASH_LEAN["hips"], 2 * math.sin(2 * math.pi * (p + 0.1)), 6 * stride)},
        "spine": {"rot": (DASH_LEAN["spine"], 0, -3 * stride)},
        "chest": {"rot": (DASH_LEAN["chest"] + 1.5 * wave(p, 2, -0.8), 0, -6 * stride)},
        "head": {"rot": (-DASH_HEAD_UP - 2 * wave(p, 2, -1.6), 0, 3 * stride)},
        "ik_foot_R": step(p % 1.0, DASH_STRIDE, DASH_LIFT, DASH_STANCE),
        "ik_foot_L": step((p + 0.5) % 1.0, DASH_STRIDE, DASH_LIFT, DASH_STANCE),
    }
    # the feet push off from behind him, which keeps the hips from folding
    back = {"ik_foot_R": {"loc": (0, DASH_FEET_BACK, 0)}, "ik_foot_L": {"loc": (0, DASH_FEET_BACK, 0)}}
    return mix(pose, back, swept_back("R", bob), swept_back("L", bob),
               # the cloak's first bone lies along his back; the rest lift and flutter behind
               cloth((DASH_CLOAK[0] + 3 * wave(p, 2, -0.5), DASH_CLOAK[1] + 4 * wave(p, 2, -1.1),
                      DASH_CLOAK[2] + 6 * wave(p, 2, -1.7)),
                     ((40 + 4 * wave(p, 2, -0.6), 0, -6 + 4 * wave(p, 1, -0.4)),
                      (15 + 6 * wave(p, 2, -1.3), 0, -8 + 5 * wave(p, 1, -1.0)))),
               feet_in(NARROW_R, NARROW_L, TOE_IN))


DASH_HEAD_UP = 10.0               # degrees the head tips back from the lean (more pushes the hood into the cloak)
DASH_CLOAK = (80.0, 6.0, 6.0)     # cloak bones' swing: the first lifts just off his back
DASH_ARMS = (0.45, 0.75, 0.15)    # arm direction: share straight back, share down his back; m out to the side
DASH_FEET_BACK = 0.13             # m the feet land behind the hips: he pushes off from behind
DASH_GUN_DIP = 20.0               # degrees the trailing pistols' barrels point down from straight back


# -- Staple Shot -------------------------------------------------------------------

SHOT_AIM = mix(WIDE, AIM_R, GUN_LOW_L, lowered(-0.025), {"hips": {"rot": (2, 0, -10)}, "chest": {"rot": (0, 0, -6)},
                                                          "head": {"rot": (2, 0, 10)}})
SHOT_FIRE = mix(SHOT_AIM, recoil("R"), {"chest": {"rot": (-4, 0, -2)}, "head": {"rot": (-3, 0, 0)}},
                cloth((4, 5, 6)))
SHOT_HOLD = mix(SHOT_AIM, recoil("R", 0.008, 4))
ATTACK = [(0, {}), (9, mix(SHOT_AIM, recoil("R", -0.01, -4))), (15, SHOT_AIM), (18, SHOT_FIRE), (26, SHOT_HOLD),
          (34, SHOT_AIM), (54, {})]
SHOT_FRAME = 18

# -- Staple Burst: twin shots, alternating -----------------------------------------------

TWIN = mix(WIDE, AIM_R, AIM_L, lowered(-0.03), {"hips": {"rot": (3, 0, 0)}, "chest": {"rot": (2, 0, 0)}})


def twin_fire(side):
    sway = -3 if side == "R" else 3
    return mix(TWIN, recoil(side, 0.028, 16), {"chest": {"rot": (-3, 0, sway)}}, cloth((4, 5, 6)))


BURST_SHOTS = (15, 24, 33, 42)  # right, left, right, left
BURST = [(0, {}), (10, TWIN), (BURST_SHOTS[0], twin_fire("R")), (20, TWIN), (BURST_SHOTS[1], twin_fire("L")), (29, TWIN),
         (BURST_SHOTS[2], twin_fire("R")), (38, TWIN), (BURST_SHOTS[3], twin_fire("L")), (50, TWIN), (72, {})]

# -- Pin: steadied, charged, one heavy shot ---------------------------------------------------

PIN_AIM = mix(WIDE, hand("R", (-0.15, -0.21, 0.49), yaw=0, pitch=2), hand("L", (0.16, -0.07, 0.37), pitch=10),
              lowered(-0.03), {"hips": {"rot": (2, 0, -5)}, "spine": {"rot": (4, 0, -2)},
                               "chest": {"rot": (5, 0, -3)}, "head": {"rot": (3, 0, 6)}})


def pin_charge(t):
    return mix(PIN_AIM, lowered(-0.012 * t), {"ik_hand_R": {"loc": (0.0015 * math.sin(t * 40), 0, 0)},
                                              "chest": {"rot": (2 * t, 0, 0)}}, cloth((2 * t, 3 * t, 4 * t)))


PIN_FIRE = mix(PIN_AIM, recoil("R", 0.05, 24), lowered(0.006, 0.02), {
    "hips": {"rot": (-6, 0, 0)}, "chest": {"rot": (-8, 0, -3)}, "head": {"rot": (-3, 0, 0)}},
    cloth((12, 16, 20), (6, 8)))
PIN = [(0, {}), (12, PIN_AIM), (24, pin_charge(0.5)), (36, pin_charge(1.0)), (42, pin_charge(1.0)),
       (45, PIN_FIRE), (56, mix(PIN_AIM, recoil("R", 0.02, 10))), (66, PIN_AIM), (90, {})]
PIN_FRAME = 45

# -- Staple Storm (signature): a leaping spin, then volleys all round ------------------------------

CROUCH = mix(lowered(-0.045, 0.01), hand("R", (-0.2, -0.17, 0.4), pitch=25), hand("L", (0.14, -0.17, 0.4), pitch=25),
             {"hips": {"rot": (3, 0, 0)}, "spine": {"rot": (8, 0, 0)}, "chest": {"rot": (12, 0, 0)},
              "head": {"rot": (-4, 0, 0)}},
             feet_in(0.03, 0.03), cloth((6, 8, 10)))
ARMS_OUT = mix(hand("R", (-0.29, -0.13, 0.56), yaw=-55, pitch=-6), hand("L", (0.23, -0.13, 0.56), yaw=55, pitch=-6))
AIRBORNE = mix(lowered(0.1), ARMS_OUT, {
    "ik_foot_R": {"loc": (0.05, 0, 0.13), "rot": (25, 0, 0)}, "ik_foot_L": {"loc": (-0.05, 0.02, 0.11), "rot": (20, 0, 0)},
    "chest": {"rot": (-4, 0, 0)}}, cloth((20, 25, 30), (-10, -15)))
LAND = mix(lowered(-0.04), WIDE, AIM_R, AIM_L, {"hips": {"rot": (3, 0, 0)}, "spine": {"rot": (5, 0, 0)},
                                                  "chest": {"rot": (6, 0, 0)}},
           cloth((10, 12, 14)))
VOLLEY = mix(LAND, lowered(0.03), {"hips": {"rot": (-4, 0, 0)}, "chest": {"rot": (-6, 0, 0)}})


STORM_VOLLEYS = (70, 79)  # both pistols at once


def staple_storm(f):
    keys = [(0, {}), (12, CROUCH), (20, CROUCH), (28, AIRBORNE), (52, AIRBORNE), (60, LAND), (66, VOLLEY),
            (STORM_VOLLEYS[0], mix(VOLLEY, recoil("R", 0.03, 20), recoil("L", 0.03, 20))), (75, VOLLEY),
            (STORM_VOLLEYS[1], mix(VOLLEY, recoil("R", 0.03, 20), recoil("L", 0.03, 20))), (86, VOLLEY), (110, {})]
    turn = 360 * smooth((f - 22) / 32)        # one full turn in the air
    rate = 360 * (smooth((f - 21) / 32) - smooth((f - 23) / 32)) / 2   # degrees a frame
    trail = cloth((0, 0, 0), ((0, 0, 0), (0, 0, 0)))
    for i in (1, 2, 3):                       # the cloak and scarf trail the turn
        trail[f"cloak_{i}"]["rot"] = (min(18.0, 1.2 * rate) * i / 3, 0, -min(12.0, 0.8 * rate) * i / 3)
    pose = mix(keyed(keys, f), trail)
    return spin(pose, turn) if 0 < turn < 360 else pose


# -- reactions ------------------------------------------------------------------------------------

RECOIL_HIT = {
    "hips": {"loc": (0, 0.018, -0.01), "rot": (-6, 0, 0)},
    "chest": {"rot": (-14, 0, 5)},
    "head": {"rot": (-7, 0, -8)},
    "ik_hand_R": {"loc": (-0.01, 0.03, 0.02), "rot": (-15, 0, 0)},
    "ik_hand_L": {"loc": (0.01, 0.03, 0.02), "rot": (-15, 0, 0)},
    "cloak_1": {"rot": (2, 0, 0)}, "cloak_2": {"rot": (3, 0, 0)}, "cloak_3": {"rot": (4, 0, 0)},
}
HURT = [(0, {}), (5, RECOIL_HIT), (15, {"chest": {"rot": (3, 0, -1)}, "head": {"rot": (4, 0, 2)},
                                       "hips": {"loc": (0, -0.004, 0)}}), (30, {})]

# sinking with the feet planted folds the thighs up into the skirt: the slump
# comes mostly from the back, the hands hang out at his sides clear of the gear,
# and the head droops with the chest rather than nodding into the scarf
BUCKLE = mix(lowered(-0.04, -0.01), {
    "hips": {"rot": (4, 0, 0)}, "spine": {"rot": (10, 0, 0)}, "chest": {"rot": (16, 0, -5)}, "head": {"rot": (6, 0, -6)},
    "ik_hand_R": {"loc": (-0.025, -0.04, -0.06), "rot": (30, 0, 0)},
    "ik_hand_L": {"loc": (0.025, -0.04, -0.06), "rot": (30, 0, 0)}},
    cloth((8, 10, 12)))
SLUMP = mix(lowered(-0.06, -0.02), {
    "hips": {"rot": (6, 0, 4)}, "spine": {"rot": (16, 0, 0)}, "chest": {"rot": (24, 0, -6)}, "head": {"rot": (8, 0, -12)},
    "ik_hand_R": {"loc": (-0.03, -0.1, -0.11), "rot": (60, 0, -20)},
    "ik_hand_L": {"loc": (0.03, -0.08, -0.1), "rot": (55, 0, 15)}},
    cloth((14, 18, 22)))
SLUMP_BOUNCE = mix(SLUMP, {"hips": {"loc": (0, 0, 0.006)}})
BROKEN = [(0, {}), (8, RECOIL_HIT), (30, BUCKLE), (52, SLUMP), (62, SLUMP_BOUNCE), (76, SLUMP), (90, SLUMP)]

# name: (frames, loops, pose at frame)
CLIPS = {
    "idle": (120, True, lambda f: idle(f / 120)),
    "move": (DASH_FRAMES, True, lambda f: dash(f / DASH_FRAMES)),
    "attack": (54, False, lambda f: keyed(ATTACK, f)),
    "staple_burst": (72, False, lambda f: keyed(BURST, f)),
    "pin": (90, False, lambda f: keyed(PIN, f)),
    "staple_storm": (110, False, staple_storm),
    "hurt": (30, False, lambda f: keyed(HURT, f)),
    "broken": (90, False, lambda f: keyed(BROKEN, f)),
}

# Moments the game times itself by (seconds): when the Staple Shot fires, when
# Pin's heavy staple fires, when each of Staple Burst's four shots fires (right,
# left, right, left), Staple Storm's two volleys, and the ground speed the dash
# was authored for.
CLIP_EVENTS = {
    "attack": {"hit": SHOT_FRAME / FPS},
    "pin": {"hit": PIN_FRAME / FPS},
    "staple_burst": {f"shot_{k + 1}": f / FPS for k, f in enumerate(BURST_SHOTS)},
    "staple_storm": {f"volley_{k + 1}": f / FPS for k, f in enumerate(STORM_VOLLEYS)},
    "move": {"speed": RUN_SPEED},
}

# -- physical fix-ups ------------------------------------------------------------------------------

CLOTH_LAG = 0.8    # share of the body's turn the cloak and scarf lag behind


def settle(pose):
    """Cloth hangs with gravity: the cloak and scarf cancel the lean and turn
    of the body they hang from (lagging behind turns), and the cloak only ever
    swings back, away from the legs."""
    pose = {k: dict(v) for k, v in pose.items()}

    def rot(bone):
        return pose.get(bone, {}).get("rot", (0.0, 0.0, 0.0))

    body = [sum(rot(b)[i] for b in ("hips", "spine", "chest")) for i in range(3)]
    body[2] -= pose.get("hips", {}).pop("spin", (0.0,))[0]
    for bone in ("cloak_1", "cloak_2", "cloak_3", "scarf_1", "scarf_2"):
        x, y, z = rot(bone)
        if bone.startswith("cloak"):
            x = max(x, 0.0)
        if bone in ("cloak_1", "scarf_1"):
            x, y, z = x - body[0], y - body[1], z - CLOTH_LAG * body[2]
        pose.setdefault(bone, {})["rot"] = (x, y, z)
    return pose


def animate_stapler(obj=None):
    obj = obj or bpy.data.objects["StaplerRogue"]
    toyanim.animate(obj.parent, CLIPS, settle)
    toyanim.write_events(os.path.join(BUILD["CHAR"].out_dir, "stapler_rogue_events.json"), CLIP_EVENTS)
    if not bpy.app.background:   # a "Stapler Rogue" tab in the 3D view's sidebar (N) to play each clip
        toyanim.register_clip_panel(obj.parent, CLIPS, "Stapler Rogue")
    return obj.parent


def clip_check(obj=None, every=1):
    obj = obj or bpy.data.objects["StaplerRogue"]
    return toyanim.clip_check(obj, CLIPS, toy3d.clip_report, every)


# The cloth chains the game's spring bones swing (UnitSprings), written beside the GLB.
SPRINGS = {"cloak": ["cloak_1", "cloak_2", "cloak_3"], "scarf": ["scarf_1", "scarf_2"]}


if __name__ == "__main__" and bpy.app.background:
    o, _, _ = BUILD["build_stapler"]()
    animate_stapler(o)
    print("clipping per clip", {k: v for k, v in clip_check(o, 2).items() if v})
    print("glb", toy3d.export_glb(o))
    print("springs", toy3d.export_springs(o, SPRINGS))
