"""Keyframe the 3D Lamp Warden's battle clips at 60 fps (Blender).

Live, through the Blender MCP, after build_lamp_warden_3d.py has built the model:
    exec(open("tools/animate_lamp_warden_3d.py").read())   then  animate_all()
which also adds a "Lamp Warden" tab to the 3D view's sidebar (N) with a button
that plays each clip. Curves, stepping, knee poles and keying are shared with
the other toys in tools/toyanim.py.
Headless (builds, animates, exports the GLB):
    D:/Blender/blender.exe --background --python tools/animate_lamp_warden_3d.py

Clips use the game's names (docs/character_abilities_stats.md) and follow the
concept sheet assets/concept/animations/lamp.png where it has them:
  loop      idle, move (run)
  play once attack (Pole Strike), intercept_run + intercept_guard (Watchful),
            spotlight (Spotlight), flashbulb (Flashbulb), guard_beam (Guard Beam),
            hurt, broken
Each clip is either a function of the
loop phase or a list of key poses joined by smooth curves, and is sampled on
every frame, so motion is smooth at 60 fps and loops join seamlessly.

A pose maps bone names to channels:
  "rot": (x, y, z) degrees about the world axes, at the bone's head.
         He faces -Y: x > 0 leans/tips forward (for bones hanging down, like
         the cape, it swings them back), y > 0 tilts toward +X (his left),
         z > 0 turns him toward his left.
  "loc": (x, y, z) metres in world space (hips and the ik_* controls).
ik_hand_* and ik_foot_* carry the hands and feet; IK bends the arms and legs
to reach them, so the hands follow the body only if the pose moves them too.
"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

try:
    _TOOLS = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _TOOLS = os.path.join(os.getcwd(), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
sys.dont_write_bytecode = True   # no __pycache__ in tools/ (check_structure)
import toyanim  # noqa: E402
importlib.reload(toyanim)
from toyanim import (FPS, wave, smooth, keyed, add, mix, scaled, step, plant_path, knee_ahead,  # noqa: E402
                     feet_in, lowered)

BUILD = {"__name__": "lamp_build", "__file__": os.path.join(_TOOLS, "build_lamp_warden_3d.py")}
exec(compile(open(BUILD["__file__"], encoding="utf-8").read(), BUILD["__file__"], "exec"), BUILD)
toy3d = BUILD["toy3d"]


# -- clips -------------------------------------------------------------------

def idle(p):
    """Two-second breathing loop; the lamp head, lantern and cloth trail the breath."""
    breath = wave(p, 1, -math.pi / 2)  # -1 exhaled at the loop start, +1 inhaled halfway
    lift = 0.5 + 0.5 * breath
    return {
        "hips": {"loc": (0, 0, -0.003 * (1 - lift))},
        "spine": {"rot": (-0.8 * breath, 0, 0)},
        "chest": {"rot": (-1.6 * breath, 0, 0.8 * wave(p, 1, 1.0))},
        "neck_lower": {"rot": (1.5 * wave(p, 1, -0.6), 0, 0)},
        "neck_upper": {"rot": (-2.5 * wave(p, 1, -1.1), 0, 1.2 * wave(p, 1, -0.8))},
        "head": {"rot": (2.0 * wave(p, 1, -1.6), 1.5 * wave(p, 1, -1.2), 3.0 * wave(p, 1, 0.4))},
        "lantern": {"rot": (2.0 * wave(p, 2, -1.0), 3.0 * wave(p, 1, -1.4), 0)},
        "cape_1": {"rot": (1.0 + 1.0 * wave(p, 1, -0.5), 0, 0)},
        "cape_2": {"rot": (1.5 + 1.5 * wave(p, 1, -1.0), 0, 1.0 * wave(p, 1, -0.7))},
        "cape_3": {"rot": (2.0 + 2.0 * wave(p, 1, -1.5), 0, 1.5 * wave(p, 1, -1.2))},
        "tabard_1": {"rot": (-0.8 - 0.8 * wave(p, 1, -0.8), 0, 0)},
        "tabard_2": {"rot": (-1.2 - 1.2 * wave(p, 1, -1.3), 0, 0)},
        "ik_hand_R": {"loc": (0, 0, 0.003 * breath)},
        "ik_hand_L": {"loc": (0, 0.002 * wave(p, 1, -0.5), 0.004 * wave(p, 1, -0.5))},
    }


# Travel: a sprint authored for the game's run speed, so the feet match the floor.
# The game moves every unit at RUN_SPEED; UnitModel scales playback to the real
# speed for anything slower (a half-tilted stick).
RUN_SPEED = 1.8         # m/s
SPRINT_FRAMES = 20      # two strides a loop: six steps a second
SPRINT_STANCE = 0.35    # share of a stride a foot is on the floor; the rest is flight
SPRINT_STRIDE = RUN_SPEED * SPRINT_STANCE * SPRINT_FRAMES / FPS  # a planted foot slides this far back
SPRINT_LIFT = 0.06


def sprint(p):
    """Run loop in place (concept: walk, sped up like intercept_run): leaning
    into it, bounding strides with a moment of flight, the staff arm pumping,
    shield carried forward, cape and lantern streaming back. Legs stay under
    the hips with the knees forward, and the leading knee kicks the tabard."""
    stride = math.cos(2 * math.pi * p)                    # +1: right foot forward
    flight = 0.5 - 0.5 * math.cos(4 * math.pi * p)        # 0 at each foot strike, 1 mid-flight
    sway = -0.006 * math.sin(2 * math.pi * (p + 0.1))
    body = (sway, 0, -0.022 + 0.02 * flight)
    kick = abs(math.cos(2 * math.pi * p - 0.5))
    pose = {
        "hips": {"loc": body, "rot": (10, 2 * math.sin(2 * math.pi * (p + 0.1)), 8 * stride)},
        "spine": {"rot": (4, 0, -3 * stride)},
        "chest": {"rot": (6 + 1.5 * wave(p, 2, -0.8), 0, -9 * stride)},
        "neck_lower": {"rot": (3 * wave(p, 2, -0.9), 0, 0)},
        "neck_upper": {"rot": (4 * wave(p, 2, -1.2), 0, 0)},
        "head": {"rot": (-4 * wave(p, 2, -1.6), 0, 0)},
        "lantern": {"rot": (22 + 10 * wave(p, 2, -1.3), 6 * wave(p, 1, -1.0), 0)},
        "cape_1": {"rot": (18 + 5 * wave(p, 2, -0.5), 0, 3 * wave(p, 1, -0.6))},
        "cape_2": {"rot": (22 + 6 * wave(p, 2, -1.1), 0, 5 * wave(p, 1, -1.0))},
        "cape_3": {"rot": (26 + 8 * wave(p, 2, -1.7), 0, 7 * wave(p, 1, -1.5))},
        "tabard_1": {"rot": (-14 - 8 * kick, 0, 4 * wave(p, 1, -0.5))},
        "tabard_2": {"rot": (-8 - 8 * kick, 0, 5 * wave(p, 1, -1.0))},
        # the staff arm pumps forward fully but only a little back, clear of the cape
        "ik_hand_R": {"loc": add(body, (-0.02, (0.045 if stride < 0 else 0.02) * stride, 0.012 * wave(p, 2))),
                      "rot": (-6 - 12 * stride, 0, 0)},
        "ik_hand_L": {"loc": add(body, (-0.02, -0.035 - 0.02 * stride, 0.015)), "rot": (4 * stride, 0, -10)},
        "ik_foot_R": step(p % 1.0, SPRINT_STRIDE, SPRINT_LIFT, SPRINT_STANCE),
        "ik_foot_L": step((p + 0.5) % 1.0, SPRINT_STRIDE, SPRINT_LIFT, SPRINT_STANCE),
    }
    return mix(pose, run_feet())


# Running feet land under the hips about 4 cm apart, toes nearly straight ahead
# (as Stapler's). The rest stance is wide, splayed and off-centre to his left,
# so each side moves in and turns by its own amount.
WALK_NARROW_R, WALK_NARROW_L = 0.095, 0.125   # m each foot moves in from rest
WALK_TOE_R, WALK_TOE_L = 37, 43               # degrees each foot turns in


def run_feet(toe_r=WALK_TOE_R, toe_l=WALK_TOE_L):
    """Both feet narrowed under the hips and turned forward, knees over them."""
    return mix(feet_in(WALK_NARROW_R, WALK_NARROW_L, toe_r), {"ik_foot_L": {"rot": (0, 0, toe_r - toe_l)}})
STAFF_AXIS = (BUILD["SP"](31, 24, -0.085) - BUILD["STAFF_GRIP"]).normalized()


def slide(d):
    """Slide the staff up through the hand by d metres, so he grips it lower."""
    return {"staff": {"loc": tuple(STAFF_AXIS * d)}}


def cloth(cape=(0, 0, 0), tabard=(0, 0)):
    out = {f"cape_{i + 1}": {"rot": (c, 0, 0)} for i, c in enumerate(cape)}
    out.update({f"tabard_{i + 1}": {"rot": (t, 0, 0)} for i, t in enumerate(tabard)})
    return out


# wide, braced stance from the concept's ready and attack rows
WIDE = {"ik_foot_R": {"loc": (-0.03, -0.015, 0), "rot": (0, 0, -6)},
        "ik_foot_L": {"loc": (0.03, 0.015, 0), "rot": (0, 0, 6)}}
SHIELD_UP = {"ik_hand_L": {"loc": (-0.02, -0.06, 0.035), "rot": (0, 0, -15)}}


# Pole Strike (concept: lamp strike): chokes down on the staff, cocks the lantern
# back over the shoulder, sweeps it over the top and down in front, follows through
STRIKE_READY = mix(WIDE, lowered(-0.02), {"chest": {"rot": (4, 0, 2)},
                                          "ik_hand_L": {"loc": (-0.015, -0.04, 0.03), "rot": (0, 0, -12)}})
STRIKE_WINDUP = mix(WIDE, lowered(-0.03, 0.012), slide(0.4), cloth((4, 5, 6)), {
    "hips": {"rot": (0, 0, -6)}, "spine": {"rot": (-3, 0, -4)}, "chest": {"rot": (-8, 0, -10)},
    "neck_lower": {"rot": (-4, 0, 0)}, "head": {"rot": (-8, 0, -6)},
    "ik_hand_R": {"loc": (-0.005, 0.02, 0.15), "rot": (-55, 0, -12)},
    "ik_hand_L": {"loc": (0.0, -0.03, 0.03), "rot": (0, 0, -10)},
    "lantern": {"rot": (18, 0, 0)},
})
STRIKE_SWING = mix(WIDE, lowered(-0.035, -0.035), slide(0.4), cloth((12, 14, 16), (-6, -9)), {
    "hips": {"rot": (5, 0, 6)}, "spine": {"rot": (5, 0, 3)}, "chest": {"rot": (10, 0, 8)},
    "neck_lower": {"rot": (10, 0, 0)}, "head": {"rot": (-3, 0, 6)},
    "ik_hand_R": {"loc": (-0.025, -0.10, 0.12), "rot": (62, 0, 8)},
    "ik_hand_L": {"loc": (0.02, -0.03, 0.0)},
    "lantern": {"rot": (-30, 0, 0)},
})
STRIKE_FOLLOW = mix(WIDE, lowered(-0.038, -0.04), slide(0.4), cloth((14, 17, 20), (-4, -7)), {
    "hips": {"rot": (6, 0, 7)}, "spine": {"rot": (5, 0, 4)}, "chest": {"rot": (13, 0, 10)},
    "neck_lower": {"rot": (12, 0, 0)}, "head": {"rot": (-6, 0, 7)},
    "ik_hand_R": {"loc": (-0.03, -0.12, 0.07), "rot": (84, 0, 10)},
    "ik_hand_L": {"loc": (0.02, -0.035, -0.01)},
    "lantern": {"rot": (20, 0, 0)},
})
STRIKE_RECOVER = mix(WIDE, lowered(-0.015, -0.01), slide(0.3), cloth((5, 7, 9)), {
    "chest": {"rot": (3, 0, 3)},
    "ik_hand_R": {"loc": (-0.045, -0.04, 0.03), "rot": (40, -12, 0)},
    "lantern": {"rot": (-6, 0, 0)},
})
STRIKE_LEVEL = mix(lowered(-0.006), slide(0.12), {"ik_hand_R": {"loc": (-0.005, -0.01, 0.006), "rot": (3, 0, 0)}})
ATTACK = [(0, {}), (8, STRIKE_READY), (20, STRIKE_WINDUP), (27, STRIKE_SWING), (33, STRIKE_FOLLOW),
          (46, STRIKE_RECOVER), (57, STRIKE_LEVEL), (68, {})]

# Watchful (concept: guard / intercept), in two clips so the game can turn him
# toward the enemy between them:
#   intercept_run    sprints RUN_DIST forward (-Y) on the root bone and plants;
#                    the game moves the unit to where the root ends up
#   intercept_guard  starts planted at the origin: a two-foot shuffle (covers
#                    the game turning him to face the enemy), shield swung round
#                    square in front of him, brace, take the hit, shove, hold
RUN_DIST = 0.5
RUN_END = 28  # frame the last foot plants


# three quick strides: right, left, right, then the left foot squares up wide
# every step lands as the sprint's do, under the hips with the toes forward,
# and the guard keeps that stance
PLANTS_R = [(2, 10, (WALK_NARROW_R, -0.17)), (14, 22, (WALK_NARROW_R, -0.49))]
PLANTS_L = [(8, 16, (-WALK_NARROW_L, -0.33)), (20, RUN_END, (-WALK_NARROW_L, -0.53))]
TOES_R = [(2, 10, (WALK_TOE_R, 0))]   # the toe turn eases in over the first step
TOES_L = [(8, 16, (-WALK_TOE_L, 0))]


def run_in(f):
    """The sprint in: root eases forward, feet plant along the way, body leans
    into the run with the shield arm already coming round."""
    u = smooth(f / RUN_END)
    root_y = -RUN_DIST * u
    pose = {"root": {"loc": (0, root_y, 0)}}
    for name, plants, toes in (("ik_foot_R", PLANTS_R, TOES_R), ("ik_foot_L", PLANTS_L, TOES_L)):
        world, pitch = plant_path(plants, f)
        toe = plant_path(toes, f)[0].x  # the toe turn eased over the same steps
        pose[name] = {"loc": (world.x, world.y - root_y, world.z), "rot": (pitch, 0, toe)}
    speed = math.sin(math.pi * min(1.0, f / RUN_END))  # 0 at start and plant, 1 mid-run
    pose = mix(pose, knee_ahead("R", pose["ik_foot_R"]["loc"][0]), knee_ahead("L", pose["ik_foot_L"]["loc"][0]))
    bob = 0.012 * abs(math.sin(math.pi * f / 8))
    return mix(pose, lowered(-0.012 * speed - bob),
               cloth((6 + 14 * speed, 8 + 16 * speed, 10 + 18 * speed), (-6 - 22 * speed, -4 - 12 * speed)), {
        "hips": {"rot": (8 * speed, 0, 0)},
        "spine": {"rot": (4 * speed, 0, 0)},
        "chest": {"rot": (8 * speed, 0, 3 * math.sin(math.pi * f / 8))},
        "neck_lower": {"rot": (6 * speed, 0, 0)},
        "head": {"rot": (-4 * speed, 0, 0)},
        "ik_hand_R": {"loc": (-0.01, 0.03 * speed, 0.01 * speed), "rot": (-10 * speed, 0, 0)},
        "ik_hand_L": {"loc": (-0.12 * u, -0.07 * u, 0.04 * u), "rot": (0, 0, -15 * u)},
        "lantern": {"rot": (25 * speed, 0, 0)},
    })


# shield held square in front of his body, the staff hand drawn back out of the way
SHIELD_FRONT = {"ik_hand_L": {"loc": (-0.28, -0.19, 0.11), "rot": (0, 0, -25)},
                "ik_hand_R": {"loc": (-0.03, 0.0, 0.0), "rot": (6, 0, 0)}}
PLANTED = {"root": {"loc": (0, -RUN_DIST, 0)},
           "ik_foot_R": {"loc": (WALK_NARROW_R, RUN_DIST - 0.49, 0), "rot": (0, 0, WALK_TOE_R)},
           "ik_foot_L": {"loc": (-WALK_NARROW_L, RUN_DIST - 0.53, 0), "rot": (0, 0, -WALK_TOE_L)}}
# the guard's braced stance, stepped out to from the run's: wide, shield foot
# forward, toes turned a little out (feet as offsets from rest, at the origin)
GUARD_FEET = {"ik_foot_R": {"loc": (0.03, 0.045, 0), "rot": (0, 0, 20)},
              "ik_foot_L": {"loc": (-0.055, -0.07, 0), "rot": (0, 0, -26)}}


def at_origin(pose):
    """The same pose with the root's travel taken out: where intercept_guard
    starts, after the game has moved the unit to the end of the run."""
    pose = {k: dict(v) for k, v in pose.items()}
    pose.pop("root", None)
    return pose


GUARD_KEYS = []


def _build_guard_keys():
    """The guard's key poses; built once the knee poles are known (they point
    the knees ahead over the narrowed stance)."""
    global BRACE, IMPACT, PUSH, GUARD_HOLD
    stance = mix(GUARD_FEET, knee_ahead("R", GUARD_FEET["ik_foot_R"]["loc"][0]),
                 knee_ahead("L", GUARD_FEET["ik_foot_L"]["loc"][0]))
    BRACE = mix(stance, SHIELD_FRONT, lowered(-0.045), cloth((8, 10, 12), (-14, -10)), {
        "hips": {"rot": (6, 0, 0)}, "spine": {"rot": (3, 0, 0)}, "chest": {"rot": (7, 0, 0)},
        "neck_lower": {"rot": (8, 0, 0)}, "head": {"rot": (-6, 0, 0)},
        "lantern": {"rot": (-8, 0, 0)},
    })
    IMPACT = mix(BRACE, lowered(-0.006, 0.02), {
        "hips": {"rot": (-5, 0, 0)}, "chest": {"rot": (-6, 0, 0)}, "head": {"rot": (-8, 0, 0)},
        "ik_hand_L": {"loc": (0, 0.025, 0.004), "rot": (-6, 0, 0)},
        "lantern": {"rot": (14, 0, 0)},
        "cape_1": {"rot": (-4, 0, 0)},
    })
    PUSH = mix(BRACE, lowered(0.0, -0.025), {
        "hips": {"rot": (3, 0, 0)}, "chest": {"rot": (5, 0, 0)},
        "ik_hand_L": {"loc": (0, -0.035, 0.0), "rot": (5, 0, 0)},
        "lantern": {"rot": (-12, 0, 0)},
        "cape_1": {"rot": (4, 0, 0)}, "cape_2": {"rot": (4, 0, 0)},
    })
    GUARD_HOLD = mix(BRACE, {"chest": {"rot": (-1, 0, 0)}, "lantern": {"rot": (6, 0, 0)}})
    plant = at_origin(run_in(RUN_END))
    brace = at_origin(BRACE)

    def stepping(t, r, l):
        """The body t of the way from the run's plant to the brace, each foot
        r / l of the way out to its guard spot (lifted while between)."""
        body = {b: c for b, c in mix(scaled(plant, 1 - t), scaled(brace, t)).items()
                if not b.startswith(("ik_foot_", "pole_knee_"))}
        for side, u in (("R", r), ("L", l)):
            foot = f"ik_foot_{side}"
            pose = mix(scaled({foot: plant[foot]}, 1 - u), scaled({foot: brace[foot]}, u))
            if 0 < u < 1:
                pose = mix(pose, {foot: {"loc": (0, 0, 0.03), "rot": (12, 0, 0)}})
                if side == "L":  # the knee stepping forward kicks the tabard ahead of it
                    pose = mix(pose, cloth(tabard=(-14, -10)))
            body = mix(body, pose, knee_ahead(side, pose[foot]["loc"][0]))
        return body

    # two quick steps out into the wide stance: staff foot back, then shield foot forward
    GUARD_KEYS[:] = [(0, plant), (3, stepping(0.2, 0.5, 0)), (6, stepping(0.45, 1, 0)),
                     (9, stepping(0.75, 1, 0.5)), (12, brace), (18, at_origin(IMPACT)),
                     (28, at_origin(PUSH)), (40, at_origin(GUARD_HOLD)), (48, brace)]


_build_guard_keys()


# Spotlight, his signature (a curtain call with both his lights): sinks and
# drives the staff butt into the floor (the game ripples a ring of light out),
# hoists the staff high overhead, cape billowing, the lantern firing a beam into
# the sky that his lamp head tips back to follow; a beat later a stage light
# drops onto the area and he snaps his lamp head round to aim at it too, staff
# raised forward and shield squared (the concept's pose), holds, and recovers
SPOT_SINK = mix(WIDE, lowered(-0.04, 0.01), slide(0.08), cloth((4, 5, 6)), {
    "hips": {"rot": (4, 0, 0)}, "spine": {"rot": (3, 0, 0)}, "chest": {"rot": (5, 0, 0)},
    "neck_lower": {"rot": (0, -4, 0)}, "head": {"rot": (-2, 0, 0)},
    "ik_hand_R": {"loc": (0.0, -0.01, 0.1), "rot": (4, 0, 0)},
    "ik_hand_L": {"loc": (0.03, 0.0, 0.0)},
    "lantern": {"rot": (-10, 0, 0)},
})
SPOT_STAMP = mix(WIDE, lowered(-0.055, 0.0), cloth((8, 10, 12), (-6, -4)), {
    "hips": {"rot": (6, 0, 0)}, "spine": {"rot": (4, 0, 0)}, "chest": {"rot": (8, 0, 0)},
    "neck_lower": {"rot": (0, -6, 0)}, "head": {"rot": (-6, 0, 0)},
    "ik_hand_R": {"loc": (0.0, -0.01, 0.052), "rot": (0, 0, 0)},   # the butt lands on the floor
    "ik_hand_L": {"loc": (0.04, 0.0, -0.01)},
    "lantern": {"rot": (18, 0, 0)},
})
SPOT_HOIST = mix(WIDE, lowered(-0.01, 0.01), slide(0.26), cloth((12, 17, 22), (-4, -2)), {
    "hips": {"rot": (-3, 0, 0)}, "spine": {"rot": (-4, 0, 0)}, "chest": {"rot": (-8, 0, 0)},
    "neck_lower": {"rot": (0, 12, 0)}, "neck_upper": {"rot": (0, -10, 0)}, "head": {"rot": (-70, 0, 0)},
    "ik_hand_R": {"loc": (-0.02, 0.0, 0.28), "rot": (-4, 0, -4)},   # out to his right, the forearm clear of the mantle
    "ik_hand_L": {"loc": (0.05, 0.0, 0.02), "rot": (0, 0, 8)},
    "lantern": {"rot": (-8, 0, 0)},
})
SPOT_RISE = mix(SPOT_HOIST, lowered(0.006), cloth((-3, -4, -5)), {"head": {"rot": (-6, 0, 0)}, "lantern": {"rot": (6, 0, 0)}})


def spot_aim(push=0.0):
    """The concept's pose: staff raised forward, shield squared, the lamp arm
    thrown out to aim at the area; `push` leans him into it while it holds."""
    return mix(WIDE, SHIELD_UP, lowered(-0.035, -0.01 * push), slide(0.22), cloth((10, 12, 14), (-6, -4)), {
        "hips": {"rot": (2, 0, 3)}, "spine": {"rot": (1, 0, 2)}, "chest": {"rot": (3 + 2 * push, 0, 3)},
        "neck_lower": {"rot": (0, -65, 0)}, "neck_upper": {"rot": (0, 38, 0)}, "head": {"rot": (-45, 0, -12)},
        "ik_hand_R": {"loc": (0.0, -0.07, 0.18), "rot": (40, 0, -9)},
        "lantern": {"rot": (5 * push, 0, 0)},
    })


SPOTLIGHT = [(0, {}), (12, SPOT_SINK), (22, SPOT_STAMP), (28, SPOT_STAMP), (44, SPOT_HOIST), (54, SPOT_RISE),
             (66, spot_aim()), (70, spot_aim(0.4)), (96, spot_aim(1.0)), (108, spot_aim(0.7)), (132, {})]

# Flashbulb (a short cone of blinding light from his lamp head): folds the lamp
# arm back like cocking a flash, throws the arm out straight
# with the shade levelled down the cone and pops (the game flares the glow),
# shield arm drawn back at his side, then the head kicks back.
# The lamp arm swings forward about y (it is turned to point back by HEAD_AHEAD
# after its own tilt), so the throw tilts neck_lower about -90 and opens
# neck_upper; the head's x then aims the shade
FLASH_SHIELD = {"ik_hand_L": {"loc": (0.055, 0.03, 0.01), "rot": (0, 0, 6)}}  # held back and out, clear of the belt
FLASH_COCK = mix(WIDE, lowered(-0.03, 0.015), cloth((4, 5, 6)), {
    "hips": {"rot": (-3, 0, 0)}, "spine": {"rot": (-3, 0, 0)}, "chest": {"rot": (-6, 0, 0)},
    "neck_lower": {"rot": (0, 15, 0)},   # tucking the shade down too sinks it into the mantle
    "ik_hand_L": {"loc": (0.02, 0.0, 0.0)},
    "ik_hand_R": {"loc": (0, 0.0, 0.01)},   # drawn back, the upper arm meets the belt
    "lantern": {"rot": (-8, 0, 0)},
})
FLASH_THROW = mix(WIDE, FLASH_SHIELD, lowered(-0.035, -0.02), cloth((10, 12, 14), (-8, -6)), {
    "hips": {"rot": (5, 0, 0)}, "spine": {"rot": (4, 0, 0)}, "chest": {"rot": (8, 0, 0)},
    "neck_lower": {"rot": (0, -90, 0)}, "neck_upper": {"rot": (0, 50, 0)}, "head": {"rot": (-75, 0, -15)},
    "ik_hand_R": {"loc": (0, -0.01, 0)},
    "lantern": {"rot": (12, 0, 0)},
})
FLASH_KICK = mix(WIDE, FLASH_SHIELD, lowered(-0.03, 0.0), cloth((14, 16, 18), (-4, -3)), {
    "hips": {"rot": (1, 0, 0)}, "spine": {"rot": (0, 0, 0)}, "chest": {"rot": (1, 0, 0)},
    "neck_lower": {"rot": (0, -60, 0)}, "neck_upper": {"rot": (0, 30, 0)}, "head": {"rot": (-100, 0, -10)},
    "ik_hand_R": {"loc": (0, 0.0, 0.01)},
    "lantern": {"rot": (-14, 0, 0)},
})
FLASH_SETTLE = mix(lowered(-0.01), cloth((4, 5, 6)), {
    "neck_lower": {"rot": (0, -12, 0)}, "head": {"rot": (-20, 0, 0)},   # tipped up, the rim clears the collar clasp
    "ik_hand_L": {"loc": (0.01, 0.01, 0.0)},
    "lantern": {"rot": (8, 0, 0)},
})
FLASHBULB = [(0, {}), (14, FLASH_COCK), (24, FLASH_THROW), (27, FLASH_THROW), (34, FLASH_KICK),
             (48, FLASH_SETTLE), (62, {})]

# Guard Beam (a beam of light that shields one ally): brings the staff up and
# levels it one-handed at the ally (the game turns him to face them first), the
# lantern hanging out ahead at the tip; the game runs the beam from the lantern
# and wraps the ally in a light bubble while he holds it, then lowers the staff
BEAM_LIFT = mix(WIDE, lowered(-0.02, 0.01), slide(0.1), cloth((4, 5, 6)), {
    "chest": {"rot": (-4, 0, -3)},
    "ik_hand_R": {"loc": (0.0, -0.02, 0.09), "rot": (18, 0, -4)},
    "ik_hand_L": {"loc": (0.04, 0.02, 0.01)},   # out to the side, clear of the belt
    "lantern": {"rot": (-10, 0, 0)},
})


def beam_point(push=0.0):
    """Staff levelled about 35 degrees above the floor, pointing ahead; `push`
    leans him a little further into it while the beam holds."""
    return mix(WIDE, lowered(-0.03, -0.015 - 0.01 * push), slide(0.2), cloth((8, 10, 12), (-6, -4)), {
        "hips": {"rot": (3, 0, -3)}, "spine": {"rot": (2, 0, -2)}, "chest": {"rot": (5 + 2 * push, 0, -4)},
        "neck_lower": {"rot": (6, 0, 0)}, "head": {"rot": (-6, 0, 0)},
        "ik_hand_R": {"loc": (0.04, -0.15 - 0.01 * push, 0.12), "rot": (55, 0, 6)},
        "ik_hand_L": {"loc": (0.05, 0.03, 0.01), "rot": (0, 0, 6)},
        "lantern": {"rot": (6 * push, 0, 0)},
    })


GUARD_BEAM = [(0, {}), (10, BEAM_LIFT), (20, beam_point()), (24, beam_point(0.3)), (44, beam_point(1.0)),
              (56, beam_point(0.6)), (66, BEAM_LIFT), (78, {})]

RECOIL = {
    "hips": {"loc": (0, 0.015, -0.008), "rot": (-5, 0, 0)},
    "chest": {"rot": (-14, 0, 4)},
    "neck_lower": {"rot": (-6, 0, 0)},
    "neck_upper": {"rot": (-10, 0, 0)},
    "head": {"rot": (-18, 0, -6)},
    "ik_hand_R": {"loc": (0, 0.025, 0.006)},
    "ik_hand_L": {"loc": (0, 0.03, 0.012)},
    "lantern": {"rot": (20, 0, 0)},
    "cape_1": {"rot": (1, 0, 0)}, "cape_2": {"rot": (2, 0, 0)}, "cape_3": {"rot": (3, 0, 0)},
    "tabard_1": {"rot": (-3, 0, 0)}, "tabard_2": {"rot": (-4, 0, 0)},
}
HURT = [(0, {}), (5, RECOIL), (15, {"chest": {"rot": (3, 0, -1)}, "neck_lower": {"rot": (4, 0, 0)},
                                   "neck_upper": {"rot": (-3, 0, 0)}, "head": {"rot": (-5, 0, 2)},
                                   "hips": {"loc": (0, -0.004, 0)}, "lantern": {"rot": (-12, 0, 0)}}), (30, {})]

SLUMP = {
    "hips": {"loc": (0, -0.02, -0.1), "rot": (14, 0, 4)},
    "spine": {"rot": (10, 0, 0)},
    "chest": {"rot": (20, 0, -6)},
    "neck_lower": {"rot": (30, 0, 0)},
    "head": {"rot": (-20, 0, -12)},
    "ik_hand_R": {"loc": (-0.04, -0.11, -0.12), "rot": (40, 0, -20)},
    "ik_hand_L": {"loc": (0.06, -0.06, -0.11), "rot": (20, 0, 0)},
    "lantern": {"rot": (-6, 0, 0)},
    "cape_1": {"rot": (14, 0, 0)}, "cape_2": {"rot": (18, 0, 0)}, "cape_3": {"rot": (22, 0, 0)},
    "tabard_1": {"rot": (-14, 0, 0)}, "tabard_2": {"rot": (-18, 0, 0)},
}
BUCKLE = {
    "hips": {"loc": (0, -0.01, -0.055), "rot": (8, 0, 0)},
    "spine": {"rot": (6, 0, 0)},
    "chest": {"rot": (13, 0, -4)},
    "neck_lower": {"rot": (20, 0, 0)},
    "head": {"rot": (-10, 0, -6)},
    "ik_hand_R": {"loc": (-0.03, -0.04, -0.06), "rot": (20, 0, -10)},
    "ik_hand_L": {"loc": (0.04, -0.03, -0.06)},
    "lantern": {"rot": (-14, 0, 0)},
    "cape_1": {"rot": (8, 0, 0)}, "cape_2": {"rot": (10, 0, 0)}, "cape_3": {"rot": (12, 0, 0)},
    "tabard_1": {"rot": (-8, 0, 0)}, "tabard_2": {"rot": (-10, 0, 0)},
}
SLUMP_BOUNCE = dict(SLUMP, hips={"loc": (0, -0.02, -0.094), "rot": (13, 0, 4)}, lantern={"rot": (-12, 0, 0)})
BROKEN = [(0, {}), (8, RECOIL), (30, BUCKLE), (52, SLUMP), (62, SLUMP_BOUNCE), (76, SLUMP), (90, SLUMP)]

# name: (frames, loops, pose at frame)
# The rest pose keeps the sprite's three-quarter look: the lamp arm leans out
# to his left (brass elbow beside him) and the shade points ~48 degrees to his
# right. Clips with a direction square the whole lamp up with his body: the
# swivel mount turns the arm round until the elbow sits straight behind the
# head (~83 degrees), then the head turns back to face where he is going (-Y),
# tipped up a touch so the rim clears the collar.
HEAD_AHEAD = {"neck_lower": {"rot": (0, 0, 83)}, "head": {"rot": (-4, 0, -35)}}


def ahead(pose_at):
    """Face where he is going, and keep facing it through body turns: the head
    cancels whatever yaw the hips, spine and chest put into the pose."""
    def pose(f):
        p = pose_at(f)
        turn = sum(p.get(b, {}).get("rot", (0, 0, 0))[2] for b in ("hips", "spine", "chest"))
        return mix(p, HEAD_AHEAD, {"head": {"rot": (0, 0, -turn)}})
    return pose


CLIPS = {
    "idle": (120, True, lambda f: idle(f / 120)),
    "move": (SPRINT_FRAMES, True, ahead(lambda f: sprint(f / SPRINT_FRAMES))),
    "attack": (68, False, ahead(lambda f: keyed(ATTACK, f))),
    "intercept_run": (RUN_END, False, ahead(run_in)),
    "intercept_guard": (48, False, ahead(lambda f: keyed(GUARD_KEYS, f))),
    "spotlight": (132, False, ahead(lambda f: keyed(SPOTLIGHT, f))),
    "flashbulb": (62, False, ahead(lambda f: keyed(FLASHBULB, f))),
    "guard_beam": (78, False, ahead(lambda f: keyed(GUARD_BEAM, f))),
    "hurt": (30, False, lambda f: keyed(HURT, f)),
    "broken": (90, False, lambda f: keyed(BROKEN, f)),
}


# Moments the game times itself by, in seconds from the clip's start: when a
# strike connects, when the guard is braced and when its impact jolt lands,
# when Flashbulb pops and Guard Beam's beam starts and ends, and
# the ground speed the travel loop was authored for. animate_all writes these to
# <glb>_events.json beside the model; UnitModel reads them.
CLIP_EVENTS = {
    "attack": {"hit": 27 / FPS},             # STRIKE_SWING: the lantern sweeps through
    "intercept_guard": {"brace": 12 / FPS, "impact": 18 / FPS},
    "spotlight": {"stamp": 22 / FPS, "beam_up": 48 / FPS, "land": 66 / FPS},  # staff hits; sky beam; light drops
    "flashbulb": {"flash": 27 / FPS},             # the lamp arm at full stretch
    "guard_beam": {"beam": 22 / FPS, "release": 56 / FPS},  # staff levelled; starts to lower
    "move": {"speed": RUN_SPEED},
}


# -- keying ------------------------------------------------------------------

CLOTH_LAG = 0.8      # share of the body's turn the cape lags behind
LANTERN_HANG = 0.7   # share of the staff's tilt the lantern cancels; the rest swings it out
ARM_SPREAD = 0.003   # m the hands drift outward per degree of forward lean
STAFF_LEAN_CARRY = 0.0015  # m the staff hand also moves out and forward per degree of lean, so the
                           # upper arm, hanging forward to it, stays off the belt


def settle(pose):
    """Physical fix-ups applied to every pose:
      - cloth hangs with gravity: the cape and tabard cancel the lean of the
        body they hang from, then swing only away from the legs (cape back,
        tabard forward); the cape also lags the body's turns. The tabard never
        swings back relative to the robe, so a robe pushed forward by the hips
        leaning back carries it along
      - leaning forward drops the shoulders, so the hands drift outward and
        the upper arms clear the belt
      - the lantern hangs from its knob whatever the staff does: it cancels the
        hand's and staff's tilt, then adds its own swing"""
    pose = {k: dict(v) for k, v in pose.items()}

    def rot(bone):
        return pose.get(bone, {}).get("rot", (0.0, 0.0, 0.0))

    body = [sum(rot(b)[i] for b in ("hips", "spine", "chest")) for i in range(3)]
    hips = rot("hips")
    for bone in ("cape_1", "cape_2", "cape_3", "tabard_1", "tabard_2"):
        x, y, z = rot(bone)
        x = max(x, 0.0) if bone.startswith("cape") else min(x, 0.0)
        if bone == "cape_1":
            x, y, z = x - body[0], y - body[1], z - CLOTH_LAG * body[2]
        elif bone == "tabard_1":
            x, y = min(x - hips[0], 0.0), y - hips[1]
        pose.setdefault(bone, {})["rot"] = (x, y, z)
    hand, staff = rot("ik_hand_R"), rot("staff")
    x, y, z = rot("lantern")
    pose.setdefault("lantern", {})["rot"] = (x - LANTERN_HANG * (hand[0] + staff[0]),
                                             y - LANTERN_HANG * (hand[1] + staff[1]), z)
    lean = max(0.0, rot("spine")[0] + rot("chest")[0])
    for bone, side in (("ik_hand_R", -1), ("ik_hand_L", 1)):
        x, y, z = pose.get(bone, {}).get("loc", (0.0, 0.0, 0.0))
        pose.setdefault(bone, {})["loc"] = (x + side * ARM_SPREAD * lean, y, z)
    full_lean = max(0.0, lean + rot("hips")[0])
    x, y, z = pose["ik_hand_R"]["loc"]
    pose["ik_hand_R"]["loc"] = (x - STAFF_LEAN_CARRY * full_lean, y - STAFF_LEAN_CARRY * full_lean, z)
    return pose


def animate_all(obj=None):
    """Key every clip on the rig, write the events file and (in a live session)
    add a "Lamp Warden" tab to the 3D view's sidebar (N) to play each clip."""
    obj = obj or bpy.data.objects["LampWarden"]
    rig = obj.parent
    toyanim.read_rest(rig)
    _build_guard_keys()           # its stance points the knees with the rig's knee poles
    toyanim.animate(rig, CLIPS, settle)
    toyanim.write_events(os.path.join(BUILD["OUT_DIR"], "lamp_warden_events.json"), CLIP_EVENTS)
    if not bpy.app.background:
        toyanim.register_clip_panel(rig, CLIPS, "Lamp Warden")
    return rig


def play(rig, name, frame):
    toyanim.play(rig, name, frame)


def clip_check(obj=None, every=6):
    """Worst clipping per clip over frames sampled every `every` frames."""
    obj = obj or bpy.data.objects["LampWarden"]
    return toyanim.clip_check(obj, CLIPS, toy3d.clip_report, every)


def render_strips(obj, frames_per_clip=6, res=256):
    """3/4 view renders of evenly spaced frames: source/anim/<clip>_<frame>.png."""
    return toyanim.render_strips(obj, CLIPS, toy3d.preview_camera(obj), frames_per_clip, res)


def render_turnaround(obj, res=320):
    """Rest pose from the concept's five turnaround angles: source/anim/turn_<n>.png."""
    rig = obj.parent
    play(rig, "idle", 0)
    shoot = toy3d.preview_camera(obj)
    paths = []
    for n, deg in enumerate((-35, 0, 35, 180, 215)):
        a = math.radians(deg)
        loc = (2.6 * math.sin(a), -2.6 * math.cos(a), 0.9)
        rel = os.path.join("anim", f"turn_{n}.png")
        shoot(rel, loc, (0, 0, 0.45), res=res, width=0.005)
        paths.append(rel)
    return paths


# The cloth chains the game's spring bones swing (UnitSprings), written beside the GLB.
SPRINGS = {"cape": ["cape_1", "cape_2", "cape_3"], "tabard": ["tabard_1", "tabard_2"], "lantern": ["lantern"]}


if __name__ == "__main__" and bpy.app.background:
    o, _, _ = BUILD["build"]()
    animate_all(o)
    print("clipping per clip", clip_check(o))
    print("glb", toy3d.export_glb(o))
    print("springs", toy3d.export_springs(o, SPRINGS))
