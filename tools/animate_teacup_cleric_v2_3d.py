"""Keyframe the 3D Teacup Cleric v2's battle clips at 60 fps (Blender).

Live, through the Blender MCP, after build_teacup_cleric_v2_3d.py has built the model:
    exec(open("tools/animate_teacup_cleric_v2_3d.py").read())   then  animate_teacup()
which also adds a "Teacup Cleric" tab to the 3D view's sidebar (N) with a button
that plays each clip.
Headless (builds, animates, checks every frame, exports the game's GLB and events
to assets/models/teacup/teacup_cleric*; TEACUP_SHEETS=1 also renders contact sheets):
    D:/Blender/blender.exe --background --python tools/animate_teacup_cleric_v2_3d.py

Clips use the game's names (docs/character_abilities_stats.md), as the owner
agreed them (revision 3 of the plan, 2026-10-11):
  loop      idle (the concept's stance, breathing, the book bobbing, the blessing
            hand drifting, the cup swaying a few degrees with the tea level),
            move (a fast scurry: short quick steps under the robe, the upper body
            still, the cup tipped back against the lean)
  play once attack (Tea Lash, 3.8 s: sizes up the target, stamps side-on, gathers
            the tea over her cup, snaps a rope of it up, whirls it, coils back and
            lunges, punching a dart of tea out; hit 2.37 s), hurt (a flinch, the
            tea slopping over the rim), broken (her knees give and she folds onto
            her left hand, the book slipping half shut, the cup tipping about 64
            degrees and pouring all its tea out),
            warm_pour (Warm Pour, 4.8 s: the book put away, both hands raise a
            ribbon of tea in a figure of eight and open to send it to the ally;
            hit 2.9 s), steady_sip (Steady Sip, 3.5 s, quiet: two fingers lift a
            thread of tea and guide it round the ally into the ward; hit 2 s),
            tea_break (signature Tea Break, 6 s: the book put away, she sinks and
            sweeps a column of tea up out of her cup, turns once on the spot as it
            rings her, flings her arms wide as it bursts over the area (hit 3.8 s),
            curtsies as it streams back, and takes the book out again)
She bends tea like water (Godot draws it along the bend_R / bend_L bones over her
palms); steam and sparkles are Godot effects. The book is put away by scaling
its bone to nothing in her palm. Poses and keying work as in tools/toyanim.py.
"""
import importlib
import json
import math
import os
import subprocess
import sys

import bpy
from mathutils import Euler, Matrix, Vector

try:
    _TOOLS = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _TOOLS = os.path.join(os.getcwd(), "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
sys.dont_write_bytecode = True   # no __pycache__ in tools/ (check_structure)
import toyanim  # noqa: E402
importlib.reload(toyanim)
from toyanim import FPS, wave, smooth, keyed, mix, knee_ahead, lowered, step  # noqa: E402

BUILD = {"__name__": "teacup_v2_build", "__file__": os.path.join(_TOOLS, "build_teacup_cleric_v2_3d.py")}
exec(compile(open(BUILD["__file__"], encoding="utf-8").read(), BUILD["__file__"], "exec"), BUILD)
toy3d = BUILD["toy3d"]
OBJECT = BUILD["CHAR"].object_name


# -- the cup on its saucer ------------------------------------------------------------
#
# The cup (her head) stands in the saucer collar's shallow well. Turning it about
# the head bone (below the saucer) would swing its foot down into the saucer, so
# a nod or tilt rocks it on its foot instead: turned about the foot's middle and
# lifted by as much as the foot's low edge drops. CUP_FOOT is read off the rig.

CUP_FOOT = {}            # "pivot": the head bone's head, "foot": the foot's middle, "r": its radius
CUP_CLEAR = 0.0003       # m the rocking foot's low edge stays above the well floor


def read_cup(obj):
    parts = list(obj["parts"])
    tag = obj.data.attributes["part"].data
    head = parts.index("head")
    cup = [v.co for v in obj.data.vertices if tag[v.index].value == head]
    z0 = min(v.z for v in cup)
    low = [v for v in cup if v.z < z0 + .004]
    mid = sum(low, Vector()) / len(low)
    CUP_FOOT.update(pivot=obj.parent.data.bones["head"].head_local.copy(), foot=Vector((mid.x, mid.y, z0)),
                    r=max(math.hypot(v.x - mid.x, v.y - mid.y) for v in low))


def cup(nod=0.0, tilt=0.0, turn=0.0):
    """The head pose for the cup nodded (+ forward), tilted (+ to her left) and
    turned (+ to her left), in degrees, rocking on its foot in the saucer. A left
    tilt past about 5 degrees meets the collar (the handle's side)."""
    q = Euler([math.radians(a) for a in (nod, tilt, turn)], "XYZ").to_quaternion()
    arm = CUP_FOOT["foot"] - CUP_FOOT["pivot"]
    tip = math.radians(math.hypot(nod, tilt))
    lift = CUP_FOOT["r"] * math.sin(tip) + (CUP_CLEAR if tip else 0.0)
    return {"head": {"rot": (nod, tilt, turn), "loc": tuple(arm - q @ arm + Vector((0, 0, lift)))}}


def cloth(cape=(0, 0, 0)):
    """The cape's three links swung back (degrees); its side columns follow the
    middle one in the clips (the build's link_cape_columns)."""
    return {f"cape_{i + 1}": {"rot": (c, 0, 0)} for i, c in enumerate(cape)}


def tea(level=0.0, drained=0.0):
    """The tea moved along the cup's axis (- lower, metres; the offset turns with
    the cup) and drained away (0 full to 1 gone, shrinking into its middle)."""
    return {"tea": {"loc": (0, 0, level), "shrink": (drained,) * 3}}


# -- arms -----------------------------------------------------------------------------------
#
# A hand is placed by its wrist (the IK target) at a point given in her body's
# frame, then turned with the body: the body's lean (x), tilt (y) and twist (z)
# about BODY_PIVOT, so a twisted stance carries both hands round with it. Its
# orientation is given by where the fingers point and the palm faces (body frame);
# None keeps the hand as built.

ARM_REST = {}            # side -> (wrist, hand axis, palm normal), read off the rig
BODY_PIVOT = Vector((0, 0, 0.40))


def read_arms(rig):
    for side in ("R", "L"):
        b = rig.data.bones["hand_" + side]
        axis = (b.tail_local - b.head_local).normalized()
        if side == "L":                          # the blessing hand is built palm up
            palm = Vector((0, 0, 1))
        else:                                    # the book hand's palm faces the cover beside it
            bk = rig.data.bones["book"]
            palm = (bk.head_local - b.head_local)
        palm = (palm - axis * palm.dot(axis)).normalized()
        ARM_REST[side] = (b.head_local.copy(), axis, palm)


def body_turn(body):
    return Euler([math.radians(a) for a in body], "XYZ").to_quaternion()


def arm(side, at=None, fingers=None, palm=None, body=(0, 0, 0), world=None):
    """The hand's IK pose: its wrist at `at` (body frame; None = where it was
    built), fingers along `fingers` with the palm toward `palm` (body frame; None =
    as built), everything turned with the body's (lean, tilt, twist). `world`
    instead places the wrist at a world point (a hand planted on the floor; a
    lowered() mixed in still carries it, so give the point before that offset)."""
    wrist, axis0, palm0 = ARM_REST[side]
    q = body_turn(body)
    at = Vector(at) if at is not None else wrist
    world = Vector(world) if world is not None else BODY_PIVOT + q @ (at - BODY_PIVOT)
    if fingers is None:
        r = q
    else:
        f = Vector(fingers).normalized()
        n = Vector(palm)
        n = (n - f * n.dot(f)).normalized()
        m0 = Matrix((axis0, palm0, axis0.cross(palm0))).transposed()
        m1 = Matrix((f, n, f.cross(n))).transposed()
        r = q @ (m1 @ m0.transposed()).to_quaternion()
    return {f"ik_hand_{side}": {"loc": tuple(world - wrist), "rot": tuple(math.degrees(a) for a in r.to_euler("XYZ"))}}


def body(lean=0.0, tilt=0.0, twist=0.0, hips_share=0.3):
    """The body's lean, tilt and twist (degrees) shared down the spine: hips_share
    of it in the hips, the rest split between spine and chest."""
    h, s = hips_share, (1 - hips_share) / 2
    return {"hips": {"rot": (lean * h, tilt * h, twist * h)}, "spine": {"rot": (lean * s, tilt * s, twist * s)},
            "chest": {"rot": (lean * s, tilt * s, twist * s)}}


def feet(r=(0, 0, 0), l=(0, 0, 0), turn_r=0.0, turn_l=0.0):
    """Planted feet moved by (x, y, z) from rest, turned (degrees, + to her left)."""
    return mix({"ik_foot_R": {"loc": r, "rot": (0, 0, turn_r)}, "ik_foot_L": {"loc": l, "rot": (0, 0, turn_l)}},
               knee_ahead("R", r[0]), knee_ahead("L", l[0]))


BOOK = {}                # "axis": the spine, "sign": which way cover_R swings shut, "angle": how far,
                         # "lift": the axis the thumb lifts off the pages about (along cover_R)


def read_book(obj):
    rig = obj.parent
    bk = rig.data.bones["book"]
    axis = (bk.tail_local - bk.head_local).normalized()
    dirs = {}
    for s in ("R", "L"):
        gi = obj.vertex_groups["cover_" + s].index
        vs = [v.co for v in obj.data.vertices if any(g.group == gi for g in v.groups)]
        c = sum(vs, Vector()) / len(vs) - bk.head_local
        dirs[s] = (c - axis * c.dot(axis)).normalized()
    BOOK.update(axis=axis, angle=dirs["R"].angle(dirs["L"]), lift=dirs["R"],
                sign=1 if dirs["R"].cross(dirs["L"]).dot(axis) > 0 else -1)


THUMB_LIFT = 45.0        # degrees the thumb lifts straight off the pages (about cover_R's own line) to let it shut
THUMB_FIRST = 0.15       # of the shutting the thumb lifts in before the cover moves


def book(shut=0.0, away=0.0):
    """The book shut (0 open to 1 shut: the thumb lifts off the pages first, then
    cover_R swings onto cover_L in her fingers) and put away (0 in her hand to 1
    gone)."""
    from mathutils import Quaternion
    swing = max(0.0, (shut - THUMB_FIRST) / (1 - THUMB_FIRST))
    cover = Quaternion(BOOK["axis"], BOOK["sign"] * BOOK["angle"] * swing)
    thumb = Quaternion(BOOK["lift"], math.radians(THUMB_LIFT * smooth(shut / THUMB_FIRST)))
    pose = {"cover_R": {"rot": tuple(math.degrees(a) for a in cover.to_euler("XYZ"))},
            "thumb_R": {"rot": tuple(math.degrees(a) for a in thumb.to_euler("XYZ"))}}
    if away:
        pose["book"] = {"shrink": (away,) * 3}
    return pose


# -- idle --------------------------------------------------------------------------------

IDLE_FRAMES = 180        # a three-second loop


def idle(p):
    """The concept's stance (the built pose): a slow breath, the book bobbing a
    little in her right hand, the blessing hand drifting, the cup swaying about
    three degrees (the tea keeps level, settle()), the cape stirring."""
    breath = wave(p, 1, -math.pi / 2)
    lift = 0.5 + 0.5 * breath
    return mix(lowered(-0.002 * (1 - lift)),
               cup(nod=1.2 * wave(p, 1, -1.4), tilt=-3.0 * wave(p, 1, -0.8), turn=4.0 * wave(p, 1, 0.2)),
               cloth((1 + 0.8 * wave(p, 1, -0.5), 1.5 + 1.2 * wave(p, 1, -1.0), 2 + 1.6 * wave(p, 1, -1.5))), {
        "hips": {"rot": (0, 0.6 * wave(p, 1, 0.3), 0)},
        "spine": {"rot": (0.5 - 0.4 * breath, 0, 0)},
        "chest": {"rot": (0.8 - 0.9 * breath, 0, 0.8 * wave(p, 1, 1.0))},
        # (the hands drift out and up from rest, never in or down: the upper sleeves
        # lie close over the coat, and an arm swung in presses them into it)
        "ik_hand_R": {"loc": (0, 0.002 * wave(p, 1, -1.6), 0.004 + 0.004 * wave(p, 1, -1.0))},
        "ik_hand_L": {"loc": (0.003 + 0.003 * wave(p, 1, 0.5), 0.003 * wave(p, 2, 0.0), 0.006 + 0.006 * wave(p, 1, -0.3))},
    }, knee_ahead("R", 0), knee_ahead("L", 0))


# -- move: the scurry -----------------------------------------------------------------------
#
# Her legs are short (about 22 cm hip to ankle), so a planted foot reaches only
# about 8 cm ahead or behind at the game's 1.8 m/s: a quick scurry with a short
# contact and a little flight between steps, the hips lowered to give the knees
# room, the upper body held still above it.

RUN_SPEED = 1.8          # m/s, the game's travel pace (move.speed)
SCURRY_FRAMES = 15       # 0.25 s a loop: two steps, eight a second
SCURRY_STANCE = 0.36     # share of a foot's cycle it is planted
SCURRY_STRIDE = RUN_SPEED * SCURRY_STANCE * SCURRY_FRAMES / FPS    # m a planted foot slides back
SCURRY_LIFT = 0.03       # m a foot lifts at mid-swing
SCURRY_DROP = 0.025      # m the hips sit lower than at rest
SCURRY_LEAN = 5.0        # degrees she leans into the run (hips, spine, chest)


def scurry(p):
    """Quick short steps (the feet under the hips, knees forward), the hips
    bobbing twice a loop and twisting a little with the legs while the chest
    turns back against them, a slight lean with the cup tipped back against it;
    the book and blessing hand carried with the body, bouncing a little behind
    it; the cape swept back."""
    bob = -SCURRY_DROP + 0.004 * wave(p, 2, -0.5)
    twist = 3.0 * wave(p, 1, 0.0)
    lean = SCURRY_LEAN
    carry = lowered(bob, -0.01)
    lag = 0.002 * wave(p, 2, -1.4)
    return mix(carry, cup(nod=-lean + 0.8 * wave(p, 2, -1.8), turn=-0.4 * twist), cloth((10 + 2 * wave(p, 2, -1.0),
               8 + 2 * wave(p, 2, -1.6), 6 + 3 * wave(p, 2, -2.2))), {
        "hips": {"rot": (0.4 * lean, 0, twist)},
        "spine": {"rot": (0.3 * lean, 0, -0.5 * twist)},
        "chest": {"rot": (0.3 * lean, 0, -0.5 * twist)},
        "ik_foot_R": step(p, SCURRY_STRIDE, SCURRY_LIFT, SCURRY_STANCE),
        "ik_foot_L": step((p + 0.5) % 1.0, SCURRY_STRIDE, SCURRY_LIFT, SCURRY_STANCE),
        "ik_hand_R": {"loc": (0, -0.004, lag)},
        "ik_hand_L": {"loc": (0, -0.004, lag)},
    }, knee_ahead("R", 0), knee_ahead("L", 0))


# -- attack: Tea Lash -------------------------------------------------------------------------
#
# Long and theatrical, with build-up and oomph (the owner: the animations are part
# of the charm), and sharp and aggressive in its strikes (her attack style): she
# sizes up the target and draws a breath, stamps into a low side-on stance, hovers
# her left hand raised beside the cup gathering the tea while it trembles, snaps it
# up pulling a rope of tea after it (Godot draws it along bend_L), whirls it once beside
# her shoulder, coils right back with it, trembling, and uncoils in a lunge,
# punching the dart out in a straight line; an overshoot and shudder, a snap back
# and flick, and the cup's tea, low while it was out, refills with a bubble. The
# book stays in her right hand, held forward while she is side-on.

SIDE_ON = -32.0          # degrees she turns her left side to the target
COIL = -46.0             # wound right back for the throw
LASH_STAMP = 48          # the stamp into the stance
LASH_HOVER = 62          # her hand over the cup, gathering
LASH_DRAW = 88           # snapped up: the rope of tea leaves the cup
LASH_WHIRL = (96, 120)   # the rope whirled once over her shoulder
LASH_COIL = 128          # wound back, trembling
LASH_HIT = 142           # the punch lands: the dart leaves her hand (the game flies it)
LASH_REFILL = 198        # the cup's tea back up, bubbling
LASH_FRAMES = 228
TEA_OUT = BUILD["TEA_LOWEST"]   # m the tea drops while it is out of the cup
BOOK_FORWARD = (-0.32, -0.12, 0.53)    # the book hand held forward while she is side-on or lunging, clear of the cape
WHIRL_C, WHIRL_R = Vector((0.30, -0.04, 0.76)), 0.04  # the whirl's circle out beside her shoulder (body frame;
                                                      # the arm raised and open, not bent in by her head)
# Her bending hand works the tea from a distance, the arm raised out to her side as in
# Tea Break's sweep (fingers up, palm turned toward the cup): over the cup's rim the
# elbow folds tight and the wrist cocks back unnaturally (the owner's note).
RAISED = ((-0.1, -0.2, 1), (-1, 0, 0))


def lash_stance(twist, lean=0.0, dz=-0.03, dy=0.0, front=-0.05, back=0.035, nod=None):
    """Side-on: feet staggered (left ahead), the twist almost all in the hips so
    the body turns as one and the cords hanging from her chest stay over the coat
    (the lean spread up the spine as usual), the cup turned back to the target,
    the book hand carried round and held forward."""
    k = min(1.0, abs(twist) / abs(SIDE_ON))
    book_at = ARM_REST["R"][0].lerp(Vector(BOOK_FORWARD), min(1.0, max(k, lean / 10)))
    return mix(body(lean), body(twist=twist, hips_share=0.85), lowered(dz, dy),
               feet(r=(-0.01, back, 0), l=(0.015, front, 0), turn_r=-20 * k, turn_l=-10 * k),
               cup(nod=0.3 * lean if nod is None else nod, turn=-0.85 * twist), arm("R", book_at, body=(lean, 0, twist)))


def lash_hand(at, fingers=None, palm=None, twist=SIDE_ON, lean=0.0):
    return arm("L", at, fingers, palm, body=(lean, 0, twist))


def attack_keys():
    back = ((0.1, 0.2, 1), (0, -1, 0))       # wound back out at her side, palm to the target
    strike = ((0, -0.2, 1), (0, -1, 0))      # palm thrust at the target
    return [
        (0, {}),
        # sizing up the target: the cup turns to it, a breath in, rising a little
        (24, mix(lowered(0.006), body(-2, 0, -4), cup(nod=-3, turn=6), arm("R", body=(-2, 0, -4)),
                 arm("L", (0.34, -0.02, 0.57), body=(-2, 0, -4)))),
        # the stamp into the low side-on stance
        (LASH_STAMP - 8, mix(lash_stance(SIDE_ON * 0.6, dz=0.004, front=-0.02, back=0.01),
                             lash_hand((0.3, -0.06, 0.62), twist=SIDE_ON * 0.6))),
        (LASH_STAMP, mix(lash_stance(SIDE_ON, dz=-0.038), lash_hand((0.26, -0.07, 0.66)))),
        (LASH_STAMP + 6, mix(lash_stance(SIDE_ON, dz=-0.032), lash_hand((0.25, -0.07, 0.68)))),
        # the hand raised beside the cup, gathering the tea (circles added in attack())
        (LASH_HOVER, mix(lash_stance(SIDE_ON, dz=-0.03, nod=2), lash_hand((0.27, -0.08, 0.76), *RAISED))),
        (LASH_DRAW - 6, mix(lash_stance(SIDE_ON, dz=-0.034, nod=3), lash_hand((0.265, -0.08, 0.745), *RAISED))),
        # snap: the rope of tea whips up out of the cup
        (LASH_DRAW, mix(lash_stance(SIDE_ON, dz=-0.026), tea(TEA_OUT), lash_hand((0.28, -0.08, 0.84), *RAISED))),
        # the whirl beside her shoulder (its circle added in attack()), then coiling back out at her side
        (LASH_WHIRL[0], mix(lash_stance(SIDE_ON, dz=-0.024), tea(TEA_OUT), lash_hand(WHIRL_C, *RAISED))),
        (LASH_WHIRL[1], mix(lash_stance(SIDE_ON - 6, -2, -0.028), tea(TEA_OUT),
                            lash_hand(WHIRL_C, *RAISED, SIDE_ON - 6, -2))),
        (LASH_COIL, mix(lash_stance(COIL, -6, -0.042, 0.012, back=0.045), tea(TEA_OUT),
                        lash_hand((0.32, 0.06, 0.7), *back, COIL, -6))),
        (LASH_HIT - 5, mix(lash_stance(COIL - 2, -7, -0.044, 0.014, back=0.045), tea(TEA_OUT),
                           lash_hand((0.33, 0.07, 0.695), *back, COIL - 2, -7))),
        # the uncoil: a lunge forward off the back foot, the dart punched out
        (LASH_HIT, mix(lash_stance(-4, 12, -0.05, -0.035), tea(TEA_OUT),
                       lash_hand((0.27, -0.3, 0.62), *strike, -4, 12))),
        (LASH_HIT + 5, mix(lash_stance(0, 15, -0.054, -0.042), tea(TEA_OUT),
                           lash_hand((0.27, -0.32, 0.605), *strike, 0, 15))),
        (LASH_HIT + 14, mix(lash_stance(-3, 11, -0.048, -0.034), tea(TEA_OUT),
                            lash_hand((0.27, -0.3, 0.62), *strike, -3, 11))),
        # the snap back and a flick of the wrist
        (LASH_HIT + 24, mix(lash_stance(-18, 2, -0.03), tea(TEA_OUT),
                            lash_hand((0.27, -0.06, 0.7), (0.3, -0.5, 0.8), (0.4, 0, 1), -18, 2))),
        (LASH_HIT + 32, mix(lash_stance(-16, 1, -0.026), tea(TEA_OUT), lash_hand((0.28, -0.05, 0.69), twist=-16, lean=1))),
        (176, mix(lash_stance(-6, 0, -0.01), tea(TEA_OUT * 0.6), arm("L", (0.345, -0.03, 0.56), body=(0, 0, -6)))),
        # (settling back the blessing hand stays a little out and up: dropping in it presses its sleeve into the coat)
        (184, mix(lash_stance(-3, 0, -0.007), tea(TEA_OUT * 0.35), arm("L", (0.34, -0.03, 0.556), body=(0, 0, -3)))),
        (LASH_REFILL - 8, mix(lowered(-0.004), tea(TEA_OUT * 0.15), arm("R"), arm("L"))),
        (LASH_REFILL, mix(lowered(-0.002), tea(0.003), arm("R"), arm("L"))),
        (LASH_REFILL + 8, mix(tea(-0.001), arm("R"), arm("L"))),
        (LASH_FRAMES, mix(arm("R"), arm("L"))),
    ]


def attack(f):
    pose = keyed(KEYS["attack"], f)
    if LASH_HOVER <= f < LASH_DRAW - 6:              # gathering: small circles over the cup, the tea trembling
        u = (f - LASH_HOVER) / (LASH_DRAW - 6 - LASH_HOVER)
        a = 2 * math.pi * 2 * u
        env = math.sin(math.pi * u)
        pose = mix(pose, {"ik_hand_L": {"loc": (0.01 * env * math.cos(a), 0.01 * env * math.sin(a), 0)}},
                   tea(0.0012 * env * math.sin(2 * math.pi * 7 * u)))
    if LASH_WHIRL[0] <= f < LASH_WHIRL[1]:           # one whirl round over her shoulder
        u = (f - LASH_WHIRL[0]) / (LASH_WHIRL[1] - LASH_WHIRL[0])
        a = 2 * math.pi * smooth(u)
        off = Vector((0, -WHIRL_R * math.sin(a), WHIRL_R * (1 - math.cos(a))))
        pose = mix(pose, {"ik_hand_L": {"loc": tuple(body_turn((0, 0, SIDE_ON)) @ off)}})
    if LASH_COIL <= f < LASH_HIT - 5:                # held tension: a tremble
        u = (f - LASH_COIL) / (LASH_HIT - 5 - LASH_COIL)
        t = 0.0025 * math.sin(2 * math.pi * 5 * u)
        pose = mix(pose, {"ik_hand_L": {"loc": (t, t * 0.5, -t)},
                          "chest": {"rot": (0, 0, 0.6 * math.sin(2 * math.pi * 5 * u))}})
    if LASH_HIT < f < LASH_HIT + 16:                 # the shudder of the strike
        u = (f - LASH_HIT) / 16
        t = 0.004 * math.sin(2 * math.pi * 3 * u) * (1 - u)
        pose = mix(pose, {"ik_hand_L": {"loc": (0, t, t * 0.5)}})
    if LASH_REFILL - 10 < f < LASH_REFILL + 16:      # the refill bubbles up
        u = (f - (LASH_REFILL - 10)) / 26
        pose = mix(pose, tea(0.0015 * math.sin(2 * math.pi * 3 * u) * (1 - u)))
    return pose


# -- hurt and broken ----------------------------------------------------------------------------

SPILL = 5                # the jolt: the tea slops over the rim
POUR = 70                # the cup has tipped far enough: the tea starts pouring out
EMPTY = 100              # all poured out
BROKEN_FRAMES = 150
SLUMP_DROP = 0.155       # m her hips sink in the slump


def hurt_broken_keys():
    """(hurt keys, broken keys)."""
    # knocked back: she flinches away, the cup tipping back (the tea slops over its far
    # rim, drawn by Godot; the game lowers the tea for good), the book drawn in a
    # little, the blessing hand flung up
    recoil = mix(body(-7, 0, 3), lowered(-0.01, 0.012), cup(nod=-6, tilt=-3),
                 arm("R", (-0.32, -0.06, 0.55), body=(-7, 0, 3)),
                 arm("L", (0.35, -0.01, 0.6), body=(-7, 0, 3)), cloth((4, 6, 8)))
    hurt = [(0, {}), (SPILL, recoil), (14, mix(body(-2, 0, 1), lowered(-0.004, 0.004), cup(nod=-2), arm("R"), arm("L"))),
            (36, mix(arm("R"), arm("L")))]

    # the slump: her knees give and she folds forward onto her left hand, the book
    # slipping half shut in her right; the cup tips about 60 degrees with her and all
    # its tea pours out over the rim (Godot draws the stream and a puddle)
    buckle = mix(body(16, 0, -4, 0.6), lowered(-0.06, -0.01), feet(r=(-0.01, 0, 0), l=(0.01, 0, 0)),
                 cup(nod=4), arm("R", (-0.37, -0.14, 0.52), body=(16, 0, -4)),
                 arm("L", (0.40, -0.18, 0.5), (0.2, -0.6, -0.6), (0, 0, -1), body=(16, 0, -4)))
    # on the way down the blessing hand swings out wide, clear of the robes, before it plants
    reach = mix(body(40, 0, -5, 0.55), lowered(-0.12, -0.02), feet(r=(-0.013, 0.005, 0), l=(0.013, 0.005, 0)),
                cup(nod=7), arm("R", world=(-0.35, -0.2, 0.34 + 0.12), body=(40, 0, -5)),
                arm("L", (0, 0, 0), (0.3, -0.8, -0.5), (0, 0, -1), body=(40, 0, -5), world=(0.38, -0.40, 0.16 + 0.12)))
    # folded 56 degrees, mostly at the hips, sunk low enough that her left hand lies
    # flat on the floor ahead of her (wider or nearer and the long sleeve drags
    # through the robes); the cup tips about 64 degrees with her
    slump = mix(body(56, 0, -6, 0.7), lowered(-SLUMP_DROP, -0.03), feet(r=(-0.015, 0.01, 0), l=(0.015, 0.01, 0)),
                cup(nod=8), cloth((2, 4, 6)),
                arm("R", world=(-0.34, -0.22, 0.30 + SLUMP_DROP), body=(56, 0, -6)),
                arm("L", (0, 0, 0), (0.3, -1, -0.2), (0, 0, -1), body=(56, 0, -6),
                    world=(0.26, -0.36, 0.035 + SLUMP_DROP)))
    slump_bounce = mix(slump, {"hips": {"loc": (0, 0, 0.006)}})
    broken = [(0, {}), (8, recoil), (24, recoil), (56, buckle), (78, reach), (96, slump), (108, slump_bounce), (124, slump),
              (BROKEN_FRAMES, slump)]
    return hurt, broken


def broken(f):
    drained = smooth((f - POUR) / (EMPTY - POUR))
    shut = 0.5 * smooth((f - 24) / (96 - 24))           # the book slips half shut as she goes down
    return mix(keyed(KEYS["broken"], f), tea(TEA_OUT * drained, drained * 0.999), book(shut))


# -- the Arts: bending tea to heal ------------------------------------------------------------------
#
# Her heals are slow and elegant (spirals, curves, wrapping), the owner's style for
# them, and long, as the Toaster's are. Godot draws the bent tea along bend_R /
# bend_L and the heal's light on the allies; the clips lower or drain the tea in
# her cup while it is out and refill it after. For the two-handed Arts she snaps
# the book shut and puts it away behind her right hip (the in-game inventory
# move, the owner's pick), and takes it back out at the end.

# the book hand out at her right side, level with her hip and just behind it (body
# frame), turned as built so the shrinking book stays clear of her forearm: further
# back or lower, the long bell sleeve drags through the robes and cape
STASH = (-0.40, 0.04, 0.54)
PALMS_UP = {"R": ((0.25, -1, 0.15), (0, 0, 1)), "L": ((-0.25, -1, 0.15), (0, 0, 1))}   # fingers ahead, palms up


def ramp(f, f0, f1):
    """0 before f0 rising smoothly to 1 at f1."""
    return smooth((f - f0) / (f1 - f0))


def book_track(f, shut_at, away_at, back_at=None, open_at=None):
    """The book over a clip: shut over shut_at (f0, f1), put away over away_at,
    then back in her hand over back_at and opened over open_at."""
    shut = ramp(f, *shut_at)
    away = ramp(f, *away_at)
    if back_at:
        away *= 1 - ramp(f, *back_at)
    if open_at:
        shut *= 1 - ramp(f, *open_at)
    return book(shut, away)


def palms(side, at, body_=(0, 0, 0)):
    return arm(side, at, *PALMS_UP[side], body=body_)


def both(r, l, body_=(0, 0, 0)):
    """Both hands palm up at body-frame points r and l."""
    return mix(palms("R", r, body_), palms("L", l, body_))


def figure_eight(f, f0, f1, size=(0.03, 0.012, 0.015)):
    """Both hands tracing a slow figure of eight together (a lemniscate across,
    dipping and rising), faded in and out over f0..f1."""
    if not f0 < f < f1:
        return {}
    u = (f - f0) / (f1 - f0)
    a = 2 * math.pi * u
    env = math.sin(math.pi * u)
    d = (size[0] * env * math.sin(a), size[1] * env * math.sin(2 * a) / 2, size[2] * env * math.sin(2 * a))
    return {"ik_hand_R": {"loc": d}, "ik_hand_L": {"loc": d}}


# -- Warm Pour (about 4.8 s): two-handed, the tea flowing across to the ally ------------------------

POUR_RISE = 66           # her hands lift: the ribbon of tea rises out of the cup
POUR_SEND = 130          # her arms open toward the ally: the ribbon flows across
POUR_HIT = 174           # it wraps the ally: the heal lands
POUR_END = 210           # the ribbon fades into light on the ally
POUR_REFILL = 262        # the cup's tea back up
POUR_FRAMES = 288


def warm_pour_keys():
    low = both((-0.28, -0.22, 0.55), (0.28, -0.22, 0.57))
    return [
        (0, {}),
        (24, mix(arm("R", (-0.31, -0.06, 0.54)), arm("L"))),
        (38, mix(arm("R", STASH, body=(0, 0, 4)), arm("L", (0.34, -0.04, 0.56), body=(0, 0, 4)), body(0, 0, 4))),
        (46, mix(arm("R", STASH, body=(0, 0, 4)), arm("L", (0.34, -0.04, 0.56), body=(0, 0, 4)), body(0, 0, 4))),
        (POUR_RISE - 6, mix(low, lowered(-0.006))),
        # the hands rise slowly, the ribbon spiralling round them (figure of eight in warm_pour())
        (100, mix(both((-0.25, -0.24, 0.57), (0.25, -0.24, 0.59)), lowered(-0.004), cup(nod=3))),
        (POUR_SEND - 4, mix(both((-0.24, -0.25, 0.61), (0.24, -0.25, 0.63)), lowered(-0.002), cup(nod=4))),
        # the arms open toward the ally, the ribbon flowing across
        (POUR_HIT - 10, mix(both((-0.26, -0.32, 0.63), (0.26, -0.32, 0.65), (5, 0, 0)), body(5),
                            lowered(-0.012, -0.01), cup(nod=6))),
        (POUR_HIT, mix(both((-0.27, -0.33, 0.62), (0.27, -0.33, 0.64), (6, 0, 0)), body(6),
                       lowered(-0.014, -0.012), cup(nod=7))),
        (POUR_END, mix(both((-0.27, -0.31, 0.6), (0.27, -0.31, 0.62), (4, 0, 0)), body(4),
                       lowered(-0.01, -0.008), cup(nod=5))),
        (228, mix(both((-0.3, -0.2, 0.56), (0.3, -0.2, 0.58)), lowered(-0.004))),
        (234, mix(arm("R", STASH, body=(0, 0, 4)), arm("L", (0.34, -0.04, 0.56), body=(0, 0, 4)), body(0, 0, 4))),
        (242, mix(arm("R", STASH, body=(0, 0, 4)), arm("L", (0.34, -0.04, 0.56), body=(0, 0, 4)), body(0, 0, 4))),
        (256, mix(arm("R", (-0.31, -0.06, 0.54)), arm("L"))),
        (POUR_FRAMES, mix(arm("R"), arm("L"))),
    ]


def warm_pour(f):
    tea_out = TEA_OUT * ramp(f, POUR_RISE - 4, POUR_RISE + 14) * (1 - ramp(f, POUR_REFILL - 14, POUR_REFILL))
    pose = mix(keyed(KEYS["warm_pour"], f), figure_eight(f, POUR_RISE, POUR_SEND - 2), tea(tea_out),
               book_track(f, (4, 20), (34, 40), (236, 242), (246, 262)))
    if POUR_REFILL - 6 < f < POUR_REFILL + 18:           # the refill bubbles up
        u = (f - (POUR_REFILL - 6)) / 24
        pose = mix(pose, tea(0.0015 * math.sin(2 * math.pi * 3 * u) * (1 - u)))
    return pose


# -- Steady Sip (about 3.5 s): one-handed, small and quiet (0 Noise) ----------------------------------

SIP_LIFT = 66            # two fingers lift a single thread of tea out of the cup
SIP_HIT = 120            # the thread settles round the ally into the ward
SIP_FRAMES = 210


def steady_sip_keys():
    lead = ((0.2, -1, 0.3), (0, 0, 1))
    near = (-0.31, -0.1, 0.57)                  # the book drawn in a little, held near her
    return [
        (0, {}),
        (30, mix(arm("R", near), arm("L", (0.3, -0.05, 0.62)), cup(nod=2))),
        # her hand raised beside the cup (as in Tea Lash), then lifting the thread up and out
        (52, mix(arm("R", near), arm("L", (0.26, -0.08, 0.75), *RAISED), cup(nod=3))),
        (SIP_LIFT, mix(arm("R", near), arm("L", (0.26, -0.08, 0.755), *RAISED), cup(nod=3))),
        (88, mix(arm("R", near), arm("L", (0.28, -0.12, 0.8), *RAISED), cup(nod=1))),
        (SIP_HIT - 6, mix(arm("R", near), arm("L", (0.26, -0.27, 0.7), *lead), cup(nod=4), lowered(-0.004))),
        (SIP_HIT + 8, mix(arm("R", near), arm("L", (0.27, -0.28, 0.69), *lead), cup(nod=4), lowered(-0.004))),
        (170, mix(arm("R", (-0.315, -0.07, 0.55)), arm("L", (0.31, -0.06, 0.58)))),
        (SIP_FRAMES, mix(arm("R"), arm("L"))),
    ]


def steady_sip(f):
    thread = -0.005 * ramp(f, SIP_LIFT, SIP_LIFT + 12) * (1 - ramp(f, 150, 180))   # a sip's worth drawn off
    pose = mix(keyed(KEYS["steady_sip"], f), tea(thread))
    if SIP_HIT - 22 < f < SIP_HIT - 4:                    # the thread circles the ally once at chest height
        u = (f - (SIP_HIT - 22)) / 18
        a = 2 * math.pi * u
        env = math.sin(math.pi * u)
        pose = mix(pose, {"ik_hand_L": {"loc": (0.008 * env * math.cos(a), 0.008 * env * math.sin(a), 0)}})
    return pose


# -- Tea Break (signature, about 6 s): the tea rises, rings her and bursts over the allies -------------

BREAK_RISE = 72          # both hands sweep up: a column of tea climbs out of her cup
BREAK_SPIN = (132, 216)  # she turns once slowly on the spot; the column unwinds into a ring round her
BREAK_RING = 140         # the ring forms, orbiting her
BREAK_BURST = 216        # arms flung wide: the ring bursts outward over the area
BREAK_HIT = 228          # ribbons peel off and wrap each ally: the heal and cleanse
BREAK_RETURN = 280       # the last of the tea streams back into her cup
BREAK_FRAMES = 360


def spin(pose, deg):
    """Turn her whole body deg about her centre line without the root (whose
    motion the game strips): the hips turn, and the hand, foot and knee targets
    swing round with them; marked so settle() keeps the cloth from lagging by
    the whole angle."""
    from mathutils import Quaternion
    q = Quaternion(Vector((0, 0, 1)), math.radians(deg))
    out = {k: dict(v) for k, v in pose.items()}
    hips = out.setdefault("hips", {})
    hips["rot"] = toyanim.add(hips.get("rot", (0.0, 0.0, 0.0)), (0, 0, deg))
    hips["spin"] = (deg, 0.0, 0.0)
    rig = bpy.data.objects[OBJECT].parent
    rests = {"ik_hand_R": ARM_REST["R"][0], "ik_hand_L": ARM_REST["L"][0],
             "ik_foot_R": rig.data.bones["foot_R"].head_local, "ik_foot_L": rig.data.bones["foot_L"].head_local}
    rests.update({f"pole_knee_{sd}": toyanim.KNEE_REST[sd][3] for sd in "RL"})
    for name, rest in rests.items():
        ch = out.setdefault(name, {})
        pt = rest + Vector(ch.get("loc", (0, 0, 0)))
        ch["loc"] = tuple(q @ pt - rest)
        if not name.startswith("pole"):
            r0 = Euler([math.radians(a) for a in ch.get("rot", (0, 0, 0))], "XYZ").to_quaternion()
            ch["rot"] = tuple(math.degrees(a) for a in (q @ r0).to_euler("XYZ"))
    return out


def shuffle(u, lift=0.016):
    """Little steps while she turns on the spot (u over the turn): each foot lifts
    twice, in turn."""
    def bump(c):
        d = abs(u - c)
        return lift * math.cos(math.pi * d / 0.1) ** 2 if d < 0.05 else 0.0
    return {"ik_foot_R": {"loc": (0, 0, bump(0.15) + bump(0.65))},
            "ik_foot_L": {"loc": (0, 0, bump(0.4) + bump(0.9))}}


def tea_break_keys():
    wide = both((-0.34, -0.03, 0.64), (0.34, -0.03, 0.66))             # arms out, the ring orbiting
    return [
        (0, {}),
        (22, mix(arm("R", (-0.31, -0.06, 0.54)), arm("L"))),
        (34, mix(arm("R", STASH, body=(0, 0, 4)), arm("L", (0.34, -0.04, 0.56), body=(0, 0, 4)), body(0, 0, 4))),
        (40, mix(arm("R", STASH, body=(0, 0, 4)), arm("L", (0.34, -0.04, 0.56), body=(0, 0, 4)), body(0, 0, 4))),
        # sunk low, hands low in front (by her knees the long sleeves drag through the robes)
        (58, mix(lowered(-0.06), body(10), feet(r=(-0.012, 0, 0), l=(0.012, 0, 0)), cup(nod=6),
                 both((-0.32, -0.22, 0.54), (0.32, -0.22, 0.55), (10, 0, 0)))),
        (BREAK_RISE - 6, mix(lowered(-0.064), body(12), feet(r=(-0.012, 0, 0), l=(0.012, 0, 0)), cup(nod=7),
                             both((-0.32, -0.24, 0.54), (0.32, -0.24, 0.55), (12, 0, 0)))),
        # both hands sweep up over her head, rising with them, the cup tipped back to watch
        (100, mix(lowered(-0.01), body(2), cup(nod=-2), both((-0.26, -0.18, 0.66), (0.26, -0.18, 0.68)))),
        (124, mix(lowered(0.008), body(-3), cup(nod=-2),
                  arm("R", (-0.22, -0.06, 0.82), (0.1, -0.2, 1), (1, 0, 0)),
                  arm("L", (0.22, -0.06, 0.83), (-0.1, -0.2, 1), (-1, 0, 0)))),
        (BREAK_SPIN[0], mix(lowered(0.006), body(-3), cup(nod=-2),
                            arm("R", (-0.23, -0.06, 0.81), (0.1, -0.2, 1), (1, 0, 0)),
                            arm("L", (0.23, -0.06, 0.82), (-0.1, -0.2, 1), (-1, 0, 0)))),
        # the turn (spin in tea_break()): arms lowered out wide, the ring orbiting her
        (156, mix(wide, lowered(-0.004))),
        (196, mix(wide, lowered(-0.004))),
        (BREAK_BURST - 8, mix(both((-0.3, -0.02, 0.6), (0.3, -0.02, 0.62)), lowered(-0.012), body(-2), cup(nod=-1))),
        # the burst: arms flung wide and forward
        (BREAK_BURST, mix(both((-0.36, -0.12, 0.64), (0.36, -0.12, 0.66)), lowered(0.004), body(4), cup(nod=3))),
        (BREAK_HIT, mix(both((-0.37, -0.13, 0.63), (0.37, -0.13, 0.65)), lowered(0.002), body(5), cup(nod=4))),
        (262, mix(both((-0.36, -0.08, 0.52), (0.36, -0.08, 0.54)), lowered(-0.004), body(2))),
        # the curtsy: her right foot draws back behind her left, knees bend, a little bow,
        # hands held low out to her sides
        (BREAK_RETURN, mix(both((-0.38, -0.04, 0.52), (0.38, -0.04, 0.54)), lowered(-0.035, 0.006), body(7),
                           feet(r=(0.03, 0.05, 0), turn_r=12), cup(nod=7))),
        (300, mix(both((-0.38, -0.04, 0.52), (0.38, -0.04, 0.54)), lowered(-0.04, 0.006), body(8),
                  feet(r=(0.03, 0.05, 0), turn_r=12), cup(nod=8))),
        (316, mix(arm("R", STASH, body=(0, 0, 4)), arm("L", (0.34, -0.04, 0.56), body=(0, 0, 4)), body(0, 0, 4),
                  lowered(-0.01))),
        (326, mix(arm("R", STASH, body=(0, 0, 4)), arm("L", (0.34, -0.04, 0.56), body=(0, 0, 4)), body(0, 0, 4))),
        (340, mix(arm("R", (-0.31, -0.06, 0.54)), arm("L"))),
        (BREAK_FRAMES, mix(arm("R"), arm("L"))),
    ]


def tea_break(f):
    drained = ramp(f, BREAK_RISE - 2, BREAK_RISE + 34) * (1 - ramp(f, BREAK_RETURN, BREAK_RETURN + 30))
    pose = mix(keyed(KEYS["tea_break"], f), tea(TEA_OUT * drained, drained * 0.999),
               book_track(f, (6, 20), (30, 36), (318, 324), (328, 344)))
    if BREAK_RETURN + 24 < f < BREAK_RETURN + 48:      # the last of it settles with a bubble
        u = (f - (BREAK_RETURN + 24)) / 24
        pose = mix(pose, tea(0.0015 * math.sin(2 * math.pi * 3 * u) * (1 - u)))
    if BREAK_SPIN[0] < f < BREAK_SPIN[1]:
        u = (f - BREAK_SPIN[0]) / (BREAK_SPIN[1] - BREAK_SPIN[0])
        turn = 360 * smooth(u)
        rate = 360 * (smooth(u + 0.01) - smooth(u - 0.01)) / 2 / ((BREAK_SPIN[1] - BREAK_SPIN[0]) * 0.01)
        trail = {f"cape_{i}": {"rot": (min(14.0, 2.0 * rate) * i / 3, 0, -min(10.0, 1.5 * rate) * i / 3)}
                 for i in (1, 2, 3)}
        pose = spin(mix(pose, trail, shuffle(u)), turn)
    return pose


KEYS = {}                # clip -> its key poses, built once the rig's rest is read

# name: (frames, loops, pose at frame)
CLIPS = {
    "idle": (IDLE_FRAMES, True, lambda f: idle(f / IDLE_FRAMES)),
    "move": (SCURRY_FRAMES, True, lambda f: scurry(f / SCURRY_FRAMES)),
    "attack": (LASH_FRAMES, False, attack),
    "hurt": (36, False, lambda f: keyed(KEYS["hurt"], f)),
    "broken": (BROKEN_FRAMES, False, broken),
    "warm_pour": (POUR_FRAMES, False, warm_pour),
    "steady_sip": (SIP_FRAMES, False, steady_sip),
    "tea_break": (BREAK_FRAMES, False, tea_break),
}

# Moments the game times itself by (seconds), and the run's authored pace: Tea
# Lash's stamp, draw (the rope of tea leaves the cup), hit (the dart leaves her hand; the
# game flies it and splashes it on arrival) and refill; hurt's spill (the tea
# slops over the rim and the game lowers her tea level); broken's pour and empty.
CLIP_EVENTS = {
    "attack": {"stamp": LASH_STAMP / FPS, "draw": LASH_DRAW / FPS, "hit": LASH_HIT / FPS,
               "refill": LASH_REFILL / FPS},
    "hurt": {"spill": SPILL / FPS},
    "broken": {"pour": POUR / FPS, "empty": EMPTY / FPS},
    "warm_pour": {"rise": POUR_RISE / FPS, "send": POUR_SEND / FPS, "hit": POUR_HIT / FPS, "end": POUR_END / FPS,
                  "refill": POUR_REFILL / FPS},
    "steady_sip": {"lift": SIP_LIFT / FPS, "hit": SIP_HIT / FPS},
    "tea_break": {"rise": BREAK_RISE / FPS, "ring": BREAK_RING / FPS, "burst": BREAK_BURST / FPS,
                  "hit": BREAK_HIT / FPS, "return": BREAK_RETURN / FPS},
    "move": {"speed": RUN_SPEED},
}


# -- physical fix-ups ---------------------------------------------------------------------------------

CLOTH_LAG = 0.3          # share of the body's turn the cape lags behind (more cuts it into the coat)
CAPE_LEAN_FREE = 10.0    # degrees of forward lean the cape hangs straight down through; past it,
                         # bent far over, the cape lies along her back
CAPE_DROOP = 0.2         # share of the lean past that its lower links droop back down by


def settle(pose):
    """The cape hangs with gravity: it cancels the lean and turn of the body it
    hangs from (lagging a little behind turns) and only swings back, away from the
    legs; bent far over, it lies along her back and its lower part droops off it;
    the cup rocks on its foot for its blended angle; then the build's settle()
    hangs the sleeves, cords and tassels against their colliders and keeps the tea
    level."""
    pose = {k: dict(v) for k, v in pose.items()}

    def rot(bone):
        return pose.get(bone, {}).get("rot", (0.0, 0.0, 0.0))

    spun = pose.get("hips", {}).pop("spin", (0.0,))[0]    # a turn on the spot (spin()): no lag for it
    body = [sum(rot(b)[i] for b in ("hips", "spine", "chest")) for i in range(3)]
    body[2] -= spun
    droop = CAPE_DROOP * max(0.0, body[0] - CAPE_LEAN_FREE)
    for bone in ("cape_1", "cape_2", "cape_3"):
        x, y, z = rot(bone)
        x = max(x, 0.0)
        if bone == "cape_1":
            x, y, z = x - min(body[0], CAPE_LEAN_FREE), y - body[1], z - CLOTH_LAG * body[2]
        else:
            x -= droop
        pose.setdefault(bone, {})["rot"] = (x, y, z)
    if "head" in pose:          # the cup rocks on its foot for whatever angle the keys blended to
        pose["head"] = cup(*pose["head"].get("rot", (0.0, 0.0, 0.0)))["head"]
    pose = BUILD["settle"](pose, spin=spun)
    return follow_cape(pose)


def follow_cape(pose):
    """The cape's side columns (cape_L_*, cape_R_*) placed link by link where the
    middle column carries them, as one rigid piece of cloth: the cape moves as it
    was animated (turned about their own off-centre tops they would swing into the
    coat), and Godot's spring bones swing each column on its own from there."""
    rig = bpy.data.objects[OBJECT].parent
    BUILD["apply_pose"](rig, pose)
    for i in (1, 2, 3):
        mid = rig.pose.bones[f"cape_{i}"]
        carried = mid.matrix @ mid.bone.matrix_local.inverted()
        for side in ("L", "R"):
            pb = rig.pose.bones[f"cape_{side}_{i}"]
            pb.matrix = carried @ pb.bone.matrix_local
            bpy.context.view_layer.update()
            rest = pb.bone.matrix_local.to_quaternion()
            q = rest @ pb.rotation_quaternion @ rest.inverted()
            pose[pb.name] = {"rot": tuple(math.degrees(a) for a in q.to_euler("XYZ")),
                             "loc": tuple(rest @ pb.location)}
    return pose


def animate_teacup(obj=None):
    obj = obj or bpy.data.objects[OBJECT]
    toyanim.read_rest(obj.parent)
    read_cup(obj)
    read_arms(obj.parent)
    read_book(obj)
    KEYS["attack"] = attack_keys()
    KEYS["hurt"], KEYS["broken"] = hurt_broken_keys()
    KEYS["warm_pour"], KEYS["steady_sip"], KEYS["tea_break"] = warm_pour_keys(), steady_sip_keys(), tea_break_keys()
    toyanim.animate(obj.parent, CLIPS, settle)
    toyanim.write_events(os.path.join(GAME_DIR, GAME_NAME + "_events.json"), CLIP_EVENTS)
    if not bpy.app.background:   # a "Teacup Cleric" tab in the 3D view's sidebar (N) to play each clip
        toyanim.register_clip_panel(obj.parent, CLIPS, "Teacup Cleric")
    return obj.parent


# v2 is the game's Teacup: it goes out as assets/models/teacup/teacup_cleric.glb
# (with its events beside it), while its previews and sheets stay in source/v2
GAME_DIR = os.path.join(toy3d.ROOT, "assets", "models", "teacup")
GAME_NAME = "teacup_cleric"


def export_game(obj=None):
    """The skinned GLB the game loads (assets/models/teacup/teacup_cleric.glb), and
    beside it the cloth chains for its spring bones (export_springs)."""
    obj = obj or bpy.data.objects[OBJECT]
    toy = BUILD["CHAR"]
    name, out = toy.name, toy.out_dir
    toy.name, toy.out_dir = GAME_NAME, GAME_DIR
    try:
        path = toy3d.export_glb(obj)
    finally:
        toy.name, toy.out_dir = name, out
    export_springs(obj)
    return path


def export_springs(obj=None):
    """assets/models/teacup/teacup_cleric_springs.json, what Godot's spring bones
    (UnitSprings) are built from, in Godot's frame (x, z, -y; metres, rest pose):
    "springs" every cloth chain {name: [bones root to tip]}, "bones" each chain bone's
    head and tail, and "capsules" the colliders round her body ({bone, head, tail,
    radius}) that build_teacup_cleric_v2_3d.py's settle() hangs the cloth against."""
    obj = obj or bpy.data.objects[OBJECT]
    rig = obj.parent
    src = json.load(open(BUILD["COLLIDERS"], encoding="utf-8"))

    def godot(v):
        return [round(v[0], 5), round(v[2], 5), round(-v[1], 5)]

    bones = {}
    for chain in src["springs"].values():
        for bone in chain:
            b = rig.data.bones[bone]
            bones[bone] = {"head": godot(b.head_local), "tail": godot(b.tail_local)}
    capsules = [{"name": c["name"], "bone": c["bone"], "head": godot(c["head"]), "tail": godot(c["tail"]),
                 "radius": c["radius"]} for c in src["capsules"]]
    path = os.path.join(GAME_DIR, GAME_NAME + "_springs.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"springs": src["springs"], "bones": bones, "capsules": capsules}, f, indent=1)
    return path


def clip_check(obj=None, every=1):
    obj = obj or bpy.data.objects[OBJECT]
    return toyanim.clip_check(obj, CLIPS, toy3d.clip_report, every)


SHEET_VIEWS = {          # contact-sheet cameras: (location, target, ortho scale)
    "3q": ((-2.6, -4.2, 1.9), (0, 0, .46), .9),
    "side": ((5, 0, .46), (0, 0, .46), .9),
}


def contact_sheets(obj=None, clips=None, frames_per_clip=8, res=320):
    """A strip of evenly spaced frames per clip and view: source/v2/anim/<clip>.png."""
    obj = obj or bpy.data.objects[OBJECT]
    rig = obj.parent
    shoot = toy3d.preview_camera(obj)
    folder = os.path.join(BUILD["V2_DIR"], "anim")
    os.makedirs(folder, exist_ok=True)
    out = []
    for name in clips or CLIPS:
        frames, loops, _ = CLIPS[name]
        picks = [round(i * (frames - (1 if loops else 0)) / (frames_per_clip - 1)) for i in range(frames_per_clip)]
        pairs = []
        for view, (loc, target, ortho) in SHEET_VIEWS.items():
            for f in picks:
                toyanim.play(rig, name, f)
                path = os.path.join(folder, "_frames", f"{name}_{view}_{f:03d}.png")
                shoot(path, loc, target, ortho=ortho, res=res)
                pairs.append(f"{view} {f / FPS:.2f}s={path}")
        dest = os.path.join(folder, f"{name}.png")
        subprocess.run([BUILD["ATLAS_PYTHON"], "-c", SHEET, dest, str(frames_per_clip)] + pairs, check=True)
        out.append(dest)
    toyanim.play(rig, "idle", 0)
    return out


SHEET = r'''
import sys
from PIL import Image, ImageDraw
out, cols, *pairs = sys.argv[1:]
cols = int(cols)
ims = [(t, Image.open(p).convert("RGB")) for t, p in (q.split("=", 1) for q in pairs)]
w, h = ims[0][1].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (w * cols, (h + 22) * rows), (27, 30, 36))
d = ImageDraw.Draw(sheet)
for i, (t, im) in enumerate(ims):
    x, y = (i % cols) * w, (i // cols) * (h + 22)
    d.text((x + 6, y + 5), t, fill=(235, 235, 235))
    sheet.paste(im, (x, y + 22))
sheet.save(out)
'''


if __name__ == "__main__" and bpy.app.background:
    o, _, _ = BUILD["build_teacup_v2"]()
    animate_teacup(o)
    print("clipping per clip", {k: v for k, v in clip_check(o, 1).items() if v})
    print("glb", export_game(o))
    if os.environ.get("TEACUP_SHEETS"):
        print("sheets", contact_sheets(o))
