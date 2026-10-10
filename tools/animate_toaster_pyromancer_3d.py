"""Keyframe the 3D Toaster Pyromancer's battle clips at 60 fps (Blender).

Live, through the Blender MCP, after build_toaster_pyromancer_3d.py has built the model:
    exec(open("tools/animate_toaster_pyromancer_3d.py").read())   then  animate_toaster()
which also adds a "Toaster Pyromancer" tab to the 3D view's sidebar (N) with a
button that plays each clip.
Headless (builds, animates, exports the GLB):
    D:/Blender/blender.exe --background --python tools/animate_toaster_pyromancer_3d.py

Clips use the game's names (docs/character_abilities_stats.md); the abilities are
as the owner chose them:
  loop      idle (the concept's wide stance, one flame raised beside his head,
            the other low by his hip), move (a rocket glide: arms pointed back,
            palms behind him jetting fire like rockets, skimming the floor)
  play once attack (Toast Pop: he slaps his own lever down, the toast sinks and
            heats, then the front slice rockets out at the target and a fresh
            one rises back into the slot), eject (Eject: the lever slap, then he
            leans in, tips his head at the target and both slices blast out
            point-blank), flash_bake (Flash Bake: both flaming hands drawn back to
            his hip, then thrust forward palms out for a cone of fire), overheat
            (his signature, Overheat: the lever slam, a shuddering build-up, arms
            raised, he flies up high, erupts at the top launching the toast, hangs
            there a moment, then floats slowly back down and lands sagging),
            hurt, broken
The fire itself is drawn in Godot at the flame bones (over his palms) and the vent
bones (his eyes); the clips only move those bones, the game burns them upright.
The toast that flies is a Godot effect too: a slice that has fired drops out of
sight inside the toaster (its bone sinks into the body) and later rises back up.
Poses and keying work as in tools/toyanim.py.
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
from toyanim import (FPS, wave, smooth, keyed, mix, knee_ahead, lowered)  # noqa: E402

BUILD = {"__name__": "toaster_build", "__file__": os.path.join(_TOOLS, "build_toaster_pyromancer_3d.py")}
exec(compile(open(BUILD["__file__"], encoding="utf-8").read(), BUILD["__file__"], "exec"), BUILD)
toy3d = BUILD["toy3d"]

# rest positions off the rig (metres)
WRIST = {"R": Vector((-0.184, -0.09, 0.379)), "L": Vector((0.184, -0.09, 0.379))}

PALM_UP = (0, 0, 0)
PALM_DOWN = (0, 180, 0)              # rolled over, to slap the lever
PALM_OUT = (-90, 0, -180)            # palm to the front, fingers up: pushing fire out


def hand(side, at, rot=PALM_UP):
    """Wrist at world point `at`, the hand turned by rot (world degrees from palm up,
    given for his right hand; the left mirrors it, so both roll outward alike)."""
    x, y, z = rot
    return {f"ik_hand_{side}": {"loc": tuple(Vector(at) - WRIST[side]), "rot": (x, y, z) if side == "R" else (x, -y, -z)}}


def cloth(cape=(0, 0, 0)):
    return {f"cape_{i + 1}": {"rot": (c, 0, 0)} for i, c in enumerate(cape)}


def toast(front=0.0, back=0.0):
    """The slices moved up (+) or sunk (-) in their slots, in metres (the offset
    turns with the toaster, so it always runs along the slots)."""
    return {"toast_front": {"loc": (0, 0, front)}, "toast_back": {"loc": (0, 0, back)}}


TOAST_GONE = -0.095      # a slice sunk this far is right down inside the toaster, as the lever
                         # pressed down puts it: its top just under the slot, its bottom clear of the base
LEVER_DOWN = {"lever": {"loc": (0, 0, -0.032)}}


# -- stance ----------------------------------------------------------------------------

# the concept's wide stance: feet apart and turned out, knees a little bent
WIDE = mix({"ik_foot_R": {"loc": (-0.03, -0.02, 0), "rot": (0, 0, -10)},
            "ik_foot_L": {"loc": (0.035, 0.03, 0), "rot": (0, 0, 12)}},
           lowered(-0.012))
FLAME_HIGH_L = hand("L", (0.2, -0.07, 0.55))         # raised beside his head, palm up
FLAME_LOW_R = hand("R", (-0.215, -0.085, 0.37))      # low by his hip, palm up, the arm clear of the belt


def idle(p):
    """Two-second breathing loop in the concept's stance: wide, the left flame
    raised beside his head and the right low by his hip, the toast bobbing a
    touch in its slots, the cape stirring."""
    breath = wave(p, 1, -math.pi / 2)
    lift = 0.5 + 0.5 * breath
    return mix(WIDE, FLAME_HIGH_L, FLAME_LOW_R, lowered(-0.003 * (1 - lift)),
               cloth((2 + 1.0 * wave(p, 1, -0.5), 2 + 1.5 * wave(p, 1, -1.0), 2.5 + 2 * wave(p, 1, -1.5))),
               toast(0.002 * wave(p, 2, -0.3), 0.002 * wave(p, 2, -1.3)), {
        "hips": {"rot": (1, 0, -5)},
        "spine": {"rot": (1 - 0.6 * breath, 0, -2)},
        "chest": {"rot": (1 - 1.2 * breath, 0, -3 + 0.8 * wave(p, 1, 1.0))},
        "head": {"rot": (-1 + 1.2 * wave(p, 1, -1.4), 1.5 * wave(p, 1, -1.1), 6 + 2.5 * wave(p, 1, 0.4))},
        "ik_hand_L": {"loc": (0, 0, 0.005 * breath)},
        "ik_hand_R": {"loc": (0, 0.002 * wave(p, 1, -0.5), 0.003 * wave(p, 1, -0.5))},
    }, knee_ahead("R", -0.03), knee_ahead("L", 0.035))


# -- travel: the rocket glide ---------------------------------------------------------------

RUN_SPEED = 1.8         # m/s, the game's travel pace (the glide has no steps to match it)
GLIDE_FRAMES = 60       # one second a loop
SHOULDER = {"R": Vector((-0.121, 0.0, 0.484)), "L": Vector((0.121, 0.0, 0.484))}
GLIDE_ARMS = (0.55, 0.7, 0.55)   # arm direction: share out to the side, back, down
GLIDE_REACH = 0.205              # m from shoulder to wrist: the arm nearly straight
GLIDE_SWING = 195.0              # degrees the hand rolls over with the arm swung back and tips
                                 # up at the wrist, fingers pointing straight back: the jets fire behind him


def swept_back(side, lift):
    """An arm swung straight back and a little down and out from its shoulder.
    The hand goes with it as it would physically: swinging a palm-up hand back
    rolls it over, so it ends palm down, and the wrist tips the fingers up to
    point straight back (the game jets its fire back along the hand)."""
    out, back, down = GLIDE_ARMS
    d = Vector(((-out if side == "R" else out), back, -down)).normalized()
    return hand(side, SHOULDER[side] + d * GLIDE_REACH + Vector((0, 0, lift)), (GLIDE_SWING, 0, 0))


def glide(p):
    """Rocketing over the floor: both arms swung straight back and down at his
    sides, the hands rolled over with them (palms down, fingers trailing), the
    fire the game draws there jetting out behind him like rockets; no steps, the
    feet planted close, one a little ahead, skimming the floor; leaning into the
    thrust, hovering and shaking with it; the cape streaming back and up."""
    bob = 0.004 * wave(p, 2, -0.4)
    shake = 0.0015 * math.sin(2 * math.pi * p * 9)
    body = (shake, 0, -0.016 + bob)
    return mix({
        "hips": {"loc": body, "rot": (4, 0, 0)},
        "spine": {"rot": (4, 0, 0)},
        "chest": {"rot": (5 + 0.8 * wave(p, 3, -0.8), 0, 0)},
        "head": {"rot": (-7 + 1.2 * wave(p, 2, -1.4), 0, 0)},
        "ik_foot_R": {"loc": (0.025, -0.035, 0), "rot": (0, 0, 6)},
        "ik_foot_L": {"loc": (-0.025, 0.035, 0), "rot": (0, 0, -6)},
    }, swept_back("R", body[2]), swept_back("L", body[2]),
        cloth((38 + 3 * wave(p, 3, -0.5), 30 + 4 * wave(p, 3, -1.1), 24 + 6 * wave(p, 3, -1.7))),
        toast(0.002 * wave(p, 4, -0.3), 0.002 * wave(p, 4, -1.3)),
        knee_ahead("R", 0.025), knee_ahead("L", -0.025))


# -- the lever slap (Toast Pop, Eject, Overheat) ---------------------------------------------

# reaching up to his lever: the head tips to meet the hand, the chest leans away to
# lift that shoulder, the hand comes over the tab palm down
SLAP_R = hand("R", (-0.25, -0.1, 0.405))            # the far hand out from his side as he leans away
SLAP_READY = mix(WIDE, SLAP_R, hand("L", (0.235, -0.03, 0.695), PALM_DOWN), {
    "chest": {"rot": (0, -4, 0)},
    "head": {"rot": (0, 10, 0)},
})
SLAP = mix(SLAP_READY, LEVER_DOWN, toast(TOAST_GONE, TOAST_GONE), {"ik_hand_L": {"loc": (0, 0, -0.03)}},
           {"head": {"rot": (2, 0, 0)}})
# on the way up the hand comes round in front of the lever, clear of its tab
SLAP_REACH = mix(SLAP_READY, {"ik_hand_L": {"loc": (0.01, -0.1, -0.06)}})
HEATING = mix(WIDE, SLAP_R, LEVER_DOWN, toast(TOAST_GONE, TOAST_GONE), hand("L", (0.2, -0.08, 0.44)))
SLAP_HIGH = mix(SLAP_READY, {"ik_hand_L": {"loc": (0, 0, 0.025)}, "chest": {"rot": (0, -2, 0)}})   # the wind-up
SLAP_FOLLOW = mix(SLAP, {"ik_hand_L": {"loc": (0, 0, -0.006)}, "head": {"rot": (3, 0, 0)}})      # driving it home
# sizing up the target: chin up, the raised flame lifted
NOTICE = mix(WIDE, FLAME_HIGH_L, FLAME_LOW_R, {"ik_hand_L": {"loc": (0, 0, 0.015)}, "head": {"rot": (-3, 0, 0)},
                                              "chest": {"rot": (-2, 0, 0)}})


def slap_keys(t):
    """Keys from frame t: the hand round in front of the lever, raised high, slapped
    down hard (the lever and both slices go down at t + 18), driven home, then
    drawn back to his side while it heats (from t + 32)."""
    return [(t, SLAP_REACH), (t + 10, SLAP_HIGH), (t + 18, SLAP), (t + 22, SLAP_FOLLOW), (t + 32, HEATING)]


def heel_bounce(pose, f, amount=0.003):
    """Bouncing on his heels with impatience as the toaster ticks."""
    return mix(pose, lowered(-amount * abs(math.sin(f * 0.33))))


def rattle(pose, f, amount=3.0):
    """The toaster shaking on his shoulders as it heats."""
    return mix(pose, {"head": {"rot": (0.4 * amount * math.sin(f * 2.1), 0, amount * math.sin(f * 1.7))},
                      "chest": {"rot": (0, 0, 0.4 * amount * math.sin(f * 1.3))}})


# -- Toast Pop -----------------------------------------------------------------------------

POP = mix(WIDE, FLAME_LOW_R, hand("L", (0.2, -0.08, 0.44)), lowered(-0.006, 0.012), toast(0.15, 0.02), {
    "head": {"rot": (-7, 0, 0)}, "chest": {"rot": (-3, 0, 0)},
})
BRACE = mix(HEATING, lowered(-0.012, 0.008), {"chest": {"rot": (-4, 0, 0)}, "head": {"rot": (-3, 0, 0)}})
POP_SLAM = 52           # the lever slapped down: the vents start to glow
POP_FRAME = 136         # the front slice leaves the slot: the game launches the flying toast
POP_RELOAD = 172        # a fresh slice starts rising, toasted


def attack(f):
    """Toast Pop: he sizes up the target, winds up and slaps his lever down, the
    toaster heats with a building rattle while he bounces on his heels, braces,
    and the front slice rockets out; his head follows it, then a fresh browned
    slice rises back into the slot and he settles, pleased."""
    keys = [(0, {}), (14, NOTICE), (26, mix(NOTICE, {"head": {"rot": (2, 0, 4)}}))] + slap_keys(POP_SLAM - 18) + [
        (100, HEATING), (124, BRACE), (132, BRACE), (POP_FRAME, POP),
        (137, mix(POP, toast(TOAST_GONE - 0.15, 0.0))),
        (148, mix(WIDE, FLAME_LOW_R, hand("L", (0.2, -0.08, 0.45)), toast(TOAST_GONE, 0.0),
                  {"head": {"rot": (-8, 0, 0)}})),
        (POP_RELOAD, mix(WIDE, FLAME_LOW_R, FLAME_HIGH_L, toast(TOAST_GONE, 0.0))),
        (190, mix(WIDE, FLAME_LOW_R, FLAME_HIGH_L, {"chest": {"rot": (-3, 0, 0)}, "head": {"rot": (-2, 0, 0)}})),
        (204, mix(WIDE, FLAME_LOW_R, FLAME_HIGH_L, {"chest": {"rot": (1, 0, 0)}})), (222, {})]
    pose = keyed(keys, f)
    # only the front slice goes down with the lever (it is the one launched); the
    # back one stays up, jostled by the pop
    pose["toast_back"] = keyed([(0, {}), (POP_FRAME - 2, {}), (POP_FRAME, toast(0, 0.02)), (146, {})],
                               f).get("toast_back", {"loc": (0, 0, 0)})
    if POP_SLAM < f < POP_FRAME - 2:
        k = smooth((f - POP_SLAM) / (POP_FRAME - POP_SLAM))
        pose = heel_bounce(rattle(pose, f, 1.0 + 2.5 * k), f, 0.003 * k)
    return pose


# -- Eject ----------------------------------------------------------------------------------

STRAIN = mix(HEATING, lowered(-0.015), {"spine": {"rot": (4, 0, 0)}, "chest": {"rot": (3, 0, -4)}})
# folded forward almost flat, the toaster level and its slots aimed at the target
# like a cannon: the lean comes mostly from his back, the hips pushed back over
# his heels to balance it, the hands out by his knees
FOLD = {"hips": {"rot": (15, 0, 0)}, "spine": {"rot": (30, 0, 0)}, "chest": {"rot": (30, 0, 0)},
        "head": {"rot": (5, 0, 0)}}
AIM = mix(WIDE, FOLD, lowered(-0.05, 0.05), hand("R", (-0.24, -0.16, 0.26)), hand("L", (0.24, -0.16, 0.26)),
          LEVER_DOWN, toast(TOAST_GONE, TOAST_GONE), cloth((6, 8, 10)))
# the blast: both slices out, the recoil throwing him up a little out of the fold
BLAST = mix(AIM, toast(0.15 - TOAST_GONE, 0.15 - TOAST_GONE), lowered(0.01, 0.015),
            {"spine": {"rot": (-4, 0, 0)}, "chest": {"rot": (-5, 0, 0)}, "head": {"rot": (-3, 0, 0)}})
BLASTED = mix(AIM, lowered(0.01, 0.015), {"spine": {"rot": (-4, 0, 0)}, "chest": {"rot": (-5, 0, 0)}})
BACK = 0.05             # m the recoil knocks him back (a half step, and back again)
EMPTY = mix(WIDE, FLAME_LOW_R, hand("L", (0.2, -0.08, 0.44)), toast(TOAST_GONE, TOAST_GONE))


def knocked(pose, dy, foot_r=(0, 0, 0), foot_l=(0, 0, 0)):
    """The pose moved back by dy, the feet with it (each with its own extra offset)."""
    return mix(pose, lowered(0, dy), {"ik_foot_R": {"loc": (foot_r[0], dy + foot_r[1], foot_r[2])},
                                      "ik_foot_L": {"loc": (foot_l[0], dy + foot_l[1], foot_l[2])}})


EJECT_SLAM = 40
EJECT_FRAME = 170       # both slices blast out
EJECT_RELOAD = 252


def eject(f):
    """Eject: the lever slap, a long heat-up that strains him, twisting side to
    side, then he folds forward almost flat, the toaster's slots aimed at the
    target, and freezes; both slices blast out point-blank and the recoil knocks
    him back a half step; he straightens up, smoking, shakes his head, steps back
    to his spot, and fresh slices rise."""
    keys = [(0, {}), (12, NOTICE)] + slap_keys(EJECT_SLAM - 18) + [
        (90, STRAIN), (120, mix(STRAIN, {"chest": {"rot": (0, 0, 8)}})), (150, AIM), (166, AIM),
        (EJECT_FRAME, BLAST), (171, BLASTED),
        (180, knocked(BLASTED, BACK * 0.6, (0, 0.01, 0.03), (0, -0.01, 0))),
        (188, knocked(BLASTED, BACK)),
        (204, knocked(mix(EMPTY, {"chest": {"rot": (-3, 0, 0)}}), BACK)),
        (212, knocked(mix(EMPTY, {"head": {"rot": (2, 0, 6)}}), BACK)),
        (220, knocked(mix(EMPTY, {"head": {"rot": (2, 0, -6)}}), BACK)),
        (226, knocked(mix(EMPTY, {"head": {"rot": (1, 0, 4)}}), BACK)),
        (232, knocked(EMPTY, BACK)),
        (240, knocked(EMPTY, BACK * 0.5, (0, -BACK * 0.5, 0.03), (0, BACK * 0.5, 0))),
        (EJECT_RELOAD, EMPTY), (272, mix(WIDE, FLAME_LOW_R, FLAME_HIGH_L)), (290, {})]
    pose = keyed(keys, f)
    if EJECT_SLAM < f < EJECT_FRAME:
        k = smooth((f - EJECT_SLAM) / (EJECT_FRAME - EJECT_SLAM))
        pose = rattle(pose, f, 0.6 if f > 150 else 1.5 + 3.5 * k)   # frozen on aim but for a tremble
        if f < 140:
            pose = heel_bounce(pose, f, 0.004 * k)
    return pose


# -- Flash Bake ---------------------------------------------------------------------------------

STANCE = mix(WIDE, FLAME_LOW_R, FLAME_HIGH_L)
STOMP_UP = mix(STANCE, lowered(0.006), {"ik_foot_R": {"loc": (-0.01, 0, 0.045), "rot": (-10, 0, 0)},
                                        "chest": {"rot": (0, 3, 0)}})
PLANTED = {"ik_foot_R": {"loc": (-0.025, 0, 0)}}       # stamped down wider
# both hands drawn back beside his hips, the fire gathering in his palms
CHARGE = mix(WIDE, PLANTED, hand("R", (-0.255, -0.04, 0.44)), hand("L", (0.255, -0.04, 0.44)),
             lowered(-0.02), {"chest": {"rot": (-3, 0, 0)}, "head": {"rot": (-2, 0, 0)}}, cloth((4, 5, 6)))
CHARGE_DEEP = mix(CHARGE, lowered(-0.012), {"chest": {"rot": (2, 0, -3)}})
BAKE_THRUST = mix(WIDE, PLANTED, hand("R", (-0.2, -0.18, 0.44), PALM_OUT), hand("L", (0.2, -0.18, 0.44), PALM_OUT),
                  lowered(-0.018, -0.015), {"spine": {"rot": (3, 0, 0)}, "chest": {"rot": (6, 0, 0)},
                                           "head": {"rot": (-3, 0, 0)}}, cloth((10, 12, 14)))
SLIDE = 0.04            # m the fire pushes him back across the floor
RECOVER = mix(WIDE, hand("R", (-0.235, -0.1, 0.4)), hand("L", (0.235, -0.1, 0.4)))
BAKE_STOMP, BAKE_CHARGE, FIRE_START, FIRE_END = 18, 44, 104, 146


def shake(pose, a):
    """The hands shaken out, rolled by a degrees (outward for +)."""
    return mix(pose, {"ik_hand_R": {"rot": (0, a, 0)}, "ik_hand_L": {"rot": (0, -a, 0)}})


def flash_bake(f):
    """Flash Bake: a stamp to plant his feet, both hands drawn back to his hips
    while the fire gathers in his palms and he sinks lower, trembling; the thrust, palms
    out, and the cone of fire pushing him back across the floor; then he shakes
    his hands out and the flames settle."""
    out = mix(RECOVER, PLANTED)
    keys = [(0, {}), (10, STOMP_UP), (BAKE_STOMP, mix(STANCE, PLANTED, lowered(-0.012))),
            (30, CHARGE), (BAKE_CHARGE, CHARGE),
            (90, CHARGE_DEEP), (98, CHARGE_DEEP), (FIRE_START, BAKE_THRUST),
            (FIRE_END, knocked(BAKE_THRUST, SLIDE)),
            (160, knocked(out, SLIDE)), (166, knocked(shake(out, 25), SLIDE)), (172, knocked(shake(out, -20), SLIDE)),
            (178, knocked(shake(out, 15), SLIDE)), (186, knocked(out, SLIDE)),
            (198, knocked(STANCE, SLIDE * 0.5, (0, -SLIDE * 0.5, 0.025))), (210, STANCE), (226, {})]
    pose = keyed(keys, f)
    if BAKE_CHARGE <= f < FIRE_START:    # trembling harder as the fire gathers
        pose = rattle(pose, f, 0.5 + 2.0 * smooth((f - BAKE_CHARGE) / (FIRE_START - BAKE_CHARGE)))
    elif FIRE_START <= f <= FIRE_END:    # the push of the fire leaving his hands
        pose = mix(pose, {"ik_hand_R": {"loc": (0, 0.004 * math.sin(f * 1.9), 0)},
                          "ik_hand_L": {"loc": (0, 0.004 * math.sin(f * 2.3), 0)},
                          "chest": {"rot": (0.8 * math.sin(f * 1.5), 0, 0)}})
    return pose


# -- Overheat (signature) ---------------------------------------------------------------------------

SHUDDER = mix(WIDE, LEVER_DOWN, toast(TOAST_GONE, TOAST_GONE), lowered(-0.02), hand("R", (-0.225, -0.1, 0.38)),
              hand("L", (0.225, -0.1, 0.38)), {"spine": {"rot": (4, 0, 0)}, "chest": {"rot": (6, 0, 0)},
                                               "head": {"rot": (5, 0, 0)}})
ARMS_UP = mix(LEVER_DOWN, toast(TOAST_GONE, TOAST_GONE), hand("R", (-0.225, -0.09, 0.625)),
              hand("L", (0.225, -0.09, 0.625)), {"chest": {"rot": (-4, 0, 0)}, "head": {"rot": (-5, 0, 0)}},
              cloth((10, 12, 14)))   # flames raised high, out and a little forward, clear of the cape
HOVER_UP = 0.32          # m he flies up before he erupts


def aloft(height, arms, cape=(6, 8, 10)):
    """Off the ground by `height`: the body and both raised or spread hands lifted
    with it, the feet hanging under him, toes down."""
    return mix(arms, lowered(height), {
        "ik_foot_R": {"loc": (0.01, 0, height - 0.012), "rot": (28, 0, 0)},
        "ik_foot_L": {"loc": (-0.01, 0.012, height - 0.018), "rot": (24, 0, 0)},
    }, cloth(cape))


AIRBORNE = aloft(HOVER_UP, ARMS_UP)
# the eruption at the top of his flight: arms flung out and down, the toast blasted
# sky-high, head thrown back
ERUPT = aloft(HOVER_UP + 0.012, mix(hand("R", (-0.25, -0.08, 0.43)), hand("L", (0.25, -0.08, 0.43)),
                                    toast(0.2, 0.2), {"chest": {"rot": (-8, 0, 0)}, "head": {"rot": (-8, 0, 0)}}),
              (12, 15, 18))
# then floating slowly back down, arms spread palms down, the cape lifting round him
FLOAT = mix(hand("R", (-0.245, -0.07, 0.4), PALM_DOWN), hand("L", (0.245, -0.07, 0.4), PALM_DOWN),
            toast(TOAST_GONE, TOAST_GONE), {"chest": {"rot": (-2, 0, 0)}, "head": {"rot": (-2, 0, 0)}})
LANDED = mix(WIDE, lowered(-0.008), hand("R", (-0.225, -0.07, 0.34)), hand("L", (0.225, -0.07, 0.34)),
             toast(TOAST_GONE, TOAST_GONE), {"spine": {"rot": (8, 0, 0)}, "chest": {"rot": (11, 0, 0)},
                                              "head": {"rot": (5, 0, 0)}}, cloth((8, 10, 12)))   # sagging from the back
SAG = mix(LANDED, {"spine": {"rot": (2, 0, 0)}, "chest": {"rot": (3, 0, 0)}, "head": {"rot": (2, 0, 3)}})
SLAM_FRAME, RISE_FRAME, ERUPT_FRAME, LAND_FRAME = 32, 110, 150, 264
OVERHEAT_RELOAD = 296    # fresh slices start rising back into the slots
DESCENT_FRAME = 192      # he hangs at the top a moment after the toast flies, then floats down
OVERHEAT_FRAMES = 322


def overheat(f):
    keys = [(0, {}), (10, NOTICE)] + slap_keys(SLAM_FRAME - 18)[:4] + [
            (44, SHUDDER), (86, SHUDDER), (98, ARMS_UP),
            (RISE_FRAME, ARMS_UP), (142, AIRBORNE), (146, AIRBORNE), (ERUPT_FRAME, ERUPT),
            (151, mix(ERUPT, toast(TOAST_GONE - 0.2, TOAST_GONE - 0.2))),
            (162, aloft(HOVER_UP, FLOAT, (4, 6, 8))), (DESCENT_FRAME, aloft(HOVER_UP - 0.006, FLOAT, (4, 6, 8))),
            (232, aloft(0.13, FLOAT, (8, 10, 12))), (252, aloft(0.03, FLOAT, (8, 10, 12))),
            (LAND_FRAME, LANDED), (280, SAG), (OVERHEAT_RELOAD, mix(SAG, toast(TOAST_GONE, TOAST_GONE))),
            (310, mix(WIDE, lowered(-0.006))), (OVERHEAT_FRAMES, {})]
    pose = keyed(keys, f)
    if SLAM_FRAME < f < ERUPT_FRAME:     # shaking harder as it builds
        pose = rattle(pose, f, 1.5 + 3.0 * smooth((f - SLAM_FRAME) / (ERUPT_FRAME - SLAM_FRAME)))
    elif LAND_FRAME < f < LAND_FRAME + 40:           # trembling, smoking, sagging
        pose = rattle(pose, f, 1.2 * (1 - smooth((f - LAND_FRAME) / 40)))
    return pose


# -- reactions --------------------------------------------------------------------------------------

RECOIL_HIT = mix({
    "hips": {"loc": (0, 0.018, -0.01), "rot": (-6, 0, 0)},
    "chest": {"rot": (-12, 0, 5)},
    "head": {"rot": (-8, 0, -7)},
    "ik_hand_R": {"loc": (-0.01, 0.03, 0.02)},
    "ik_hand_L": {"loc": (0.01, 0.03, 0.02)},
}, toast(0.02, 0.01), cloth((3, 4, 5)))
HURT = [(0, {}), (5, RECOIL_HIT), (15, {"chest": {"rot": (3, 0, -1)}, "head": {"rot": (4, 0, 2)},
                                       "hips": {"loc": (0, -0.004, 0)}}), (30, {})]

# the slump comes mostly from the back, the hands hang out at his sides clear of
# the belt, the head droops with the chest; the toast pops up and drops back,
# half sunk, as the toaster goes cold
BUCKLE = mix(lowered(-0.012, -0.01), {
    "hips": {"rot": (4, 0, 0)}, "spine": {"rot": (9, 0, 0)}, "chest": {"rot": (14, 0, -5)}, "head": {"rot": (6, 0, -6)},
    "ik_hand_R": {"loc": (-0.055, -0.05, -0.03), "rot": (40, 0, 0)},
    "ik_hand_L": {"loc": (0.06, -0.05, -0.03), "rot": (40, 0, 0)}},
    toast(0.06, 0.05), cloth((6, 8, 10)))
SLUMP = mix(lowered(-0.012, -0.02), {
    "hips": {"rot": (2, 0, 4)}, "spine": {"rot": (14, 0, 0)}, "chest": {"rot": (20, 0, -6)}, "head": {"rot": (8, 0, -8)},
    "ik_hand_R": {"loc": (-0.05, -0.08, -0.07), "rot": (60, 0, -20)},
    "ik_hand_L": {"loc": (0.06, -0.08, -0.07), "rot": (55, 0, 15)}},
    toast(-0.02, -0.03), cloth((10, 14, 18)))
SLUMP_BOUNCE = mix(SLUMP, {"hips": {"loc": (0, 0, 0.006)}})
BROKEN = [(0, {}), (8, RECOIL_HIT), (24, RECOIL_HIT), (56, BUCKLE), (96, SLUMP), (108, SLUMP_BOUNCE), (124, SLUMP),
          (150, SLUMP)]   # a slow, heavy collapse; the game fades his vents out

# name: (frames, loops, pose at frame)
CLIPS = {
    "idle": (120, True, lambda f: idle(f / 120)),
    "move": (GLIDE_FRAMES, True, lambda f: glide(f / GLIDE_FRAMES)),
    "attack": (222, False, attack),
    "eject": (290, False, eject),
    "flash_bake": (226, False, flash_bake),
    "overheat": (OVERHEAT_FRAMES, False, overheat),
    "hurt": (30, False, lambda f: keyed(HURT, f)),
    "broken": (150, False, lambda f: keyed(BROKEN, f)),
}

# Moments the game times itself by (seconds): each lever slam (the vents start to
# glow), when Toast Pop's slice leaves the slot (the hit follows its flight) and
# when a fresh, toasted slice starts rising, when Eject's two slices blast out,
# Flash Bake's stamp, charge and the cone's start and end, Overheat's lever slam,
# lift-off, eruption, landing and fresh slices, and the game's travel pace (the glide has no
# steps; UnitModel only scales its loop).
CLIP_EVENTS = {
    "attack": {"slam": POP_SLAM / FPS, "hit": POP_FRAME / FPS, "reload": POP_RELOAD / FPS},
    "eject": {"slam": EJECT_SLAM / FPS, "hit": EJECT_FRAME / FPS, "reload": EJECT_RELOAD / FPS},
    "flash_bake": {"stomp": BAKE_STOMP / FPS, "charge": BAKE_CHARGE / FPS, "fire": FIRE_START / FPS,
                   "fire_end": FIRE_END / FPS},
    "overheat": {"slam": SLAM_FRAME / FPS, "rise": RISE_FRAME / FPS, "erupt": ERUPT_FRAME / FPS,
                 "land": LAND_FRAME / FPS, "reload": OVERHEAT_RELOAD / FPS},
    "move": {"speed": RUN_SPEED},
}

# -- physical fix-ups ---------------------------------------------------------------------------------

CLOTH_LAG = 0.8    # share of the body's turn the cape lags behind


CAPE_LEAN_FREE = 20.0   # degrees of forward lean the cape hangs straight down through; past it,
                        # bent far over, the cape lies along his back
CAPE_DROOP = 0.4        # share of the lean past that its lower links droop back down by


def settle(pose):
    """The cape hangs with gravity: it cancels the lean and turn of the body it
    hangs from (lagging behind turns), and only ever swings back, away from the
    legs; bent far over, it lies along his back and its lower part droops off it."""
    pose = {k: dict(v) for k, v in pose.items()}

    def rot(bone):
        return pose.get(bone, {}).get("rot", (0.0, 0.0, 0.0))

    body = [sum(rot(b)[i] for b in ("hips", "spine", "chest")) for i in range(3)]
    droop = CAPE_DROOP * max(0.0, body[0] - CAPE_LEAN_FREE)
    for bone in ("cape_1", "cape_2", "cape_3"):
        x, y, z = rot(bone)
        x = max(x, 0.0)
        if bone == "cape_1":
            x, y, z = x - min(body[0], CAPE_LEAN_FREE), y - body[1], z - CLOTH_LAG * body[2]
        else:
            x -= droop
        pose.setdefault(bone, {})["rot"] = (x, y, z)
    return pose


def animate_toaster(obj=None):
    obj = obj or bpy.data.objects["ToasterPyromancer"]
    toyanim.read_rest(obj.parent)
    toyanim.animate(obj.parent, CLIPS, settle)
    toyanim.write_events(os.path.join(BUILD["CHAR"].out_dir, "toaster_pyromancer_events.json"), CLIP_EVENTS)
    if not bpy.app.background:   # a "Toaster Pyromancer" tab in the 3D view's sidebar (N) to play each clip
        toyanim.register_clip_panel(obj.parent, CLIPS, "Toaster Pyromancer")
    return obj.parent


def clip_check(obj=None, every=1):
    obj = obj or bpy.data.objects["ToasterPyromancer"]
    return toyanim.clip_check(obj, CLIPS, toy3d.clip_report, every)


if __name__ == "__main__" and bpy.app.background:
    o, _, _ = BUILD["build_toaster"]()
    animate_toaster(o)
    print("clipping per clip", {k: v for k, v in clip_check(o, 2).items() if v})
    print("glb", toy3d.export_glb(o))
