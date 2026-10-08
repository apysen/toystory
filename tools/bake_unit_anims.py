"""Bake the slice's missing battle animations from existing art (Pillow).

python tools/bake_unit_anims.py            -> every unit
python tools/bake_unit_anims.py pencil     -> one unit

Writes Aseprite "hash" sheets (PNG + JSON with frameTags) that SpriteLib loads:

  enemies/<name>/<name>_sheet.*         idle (enemies only had a still)
  drafts/<name>_<anim>/<name>_<anim>_*  move/attack/hurt for enemies,
                                        broken, gaze_in, gaze_out for everyone
  drafts/<name>_<anim>/..._preview.png  labelled frame strip for review

Every operation moves whole pixels - shifts, row-band leans and nearest-neighbour
squash - so the pixel density matches the source art
(vertical_slice_plan.md section 21). Frames keep the source's left edge and
foot pivot; a frame that needs room grows to the right only, the way
lamp_hurt does, so UnitView mirrors it correctly.

These are drafts for review, like the hand-posed player drafts: a final
hand-drawn sheet replaces a draft by adding the tag to the main sheet.
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")
DRAFTS = os.path.join(ROOT, "drafts")

# name -> (group, base frame source). Players use idle frame 0 of their sheet.
UNITS = {
    "lamp": "player", "stapler": "player", "toaster": "player", "teacup": "player",
    "umbrella": "player", "vacuum_256": "player",
    "pencil": "enemies", "rubber": "enemies", "bookend": "enemies", "tape": "enemies",
    "roomba": "enemies", "cutter": "enemies",
}
ENEMIES = [n for n, g in UNITS.items() if g == "enemies"]
NATIVE_LEFT = {"lamp"}


# --- Loading ---------------------------------------------------------------------

def load_meta(group, name):
    path = os.path.join(ROOT, group, name, name + "_meta.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def base_frame(group, name):
    """Idle frame 0 (players) or the still (enemies), as RGBA."""
    folder = os.path.join(ROOT, group, name)
    sheet = os.path.join(folder, name + "_sheet.png")
    meta = load_meta(group, name)
    w, h = meta["frame_width"], meta["frame_height"]
    if group == "player" and os.path.exists(sheet):
        return Image.open(sheet).convert("RGBA").crop((0, 0, w, h)), meta
    return Image.open(os.path.join(folder, name + ".png")).convert("RGBA"), meta


def facing(name, meta):
    f = meta.get("faces", meta.get("base_facing", ""))
    if f in ("left", "right"):
        return -1 if f == "left" else 1
    return -1 if name in NATIVE_LEFT else 1


# --- Pixel-safe operations ---------------------------------------------------------

def blank(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def shift(img, dx, dy, canvas=None):
    w, h = canvas or img.size
    out = blank(w, h)
    out.alpha_composite(img, (max(dx, 0), max(dy, 0)), (max(-dx, 0), max(-dy, 0)))
    return out


def lean(img, pivot_y, amount):
    """Shifts each row sideways in proportion to its height above the feet: the top
    moves `amount` pixels, the feet stay put. Whole-pixel row shifts keep it crisp."""
    w, h = img.size
    out = blank(w, h)
    for y in range(h):
        k = (pivot_y - y) / max(pivot_y, 1)
        dx = round(amount * max(k, 0))
        row = img.crop((0, y, w, y + 1))
        out.alpha_composite(row, (max(dx, 0), y), (max(-dx, 0), 0))
    return out


def squash(img, pivot, sx, sy):
    """Nearest-neighbour scale about the foot pivot."""
    w, h = img.size
    px, py = pivot
    out = blank(w, h)
    src = img.load()
    dst = out.load()
    for y in range(h):
        sy_src = py + (y - py) / sy
        iy = int(round(sy_src))
        if iy < 0 or iy >= h:
            continue
        for x in range(w):
            ix = int(round(px + (x - px) / sx))
            if 0 <= ix < w:
                dst[x, y] = src[ix, iy]
    return out


def tint(img, rgb, strength):
    out = img.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a:
                px[x, y] = (round(r + (rgb[0] - r) * strength), round(g + (rgb[1] - g) * strength),
                            round(b + (rgb[2] - b) * strength), a)
    return out


def desaturate(img, amount, darken=0.0):
    out = img.copy()
    px = out.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a:
                l = 0.3 * r + 0.59 * g + 0.11 * b
                r, g, b = (c + (l - c) * amount for c in (r, g, b))
                px[x, y] = (round(r * (1 - darken)), round(g * (1 - darken)), round(b * (1 - darken)), a)
    return out


def opaque_bbox(img):
    return img.getchannel("A").getbbox()


def lightest(img):
    best, best_l = (255, 255, 255), -1
    for r, g, b, a in img.get_flattened_data():
        if a:
            l = 0.3 * r + 0.59 * g + 0.11 * b
            if l > best_l:
                best, best_l = (r, g, b), l
    return best


def darkest(img):
    best, best_l = (0, 0, 0), 999
    for r, g, b, a in img.get_flattened_data():
        if a:
            l = 0.3 * r + 0.59 * g + 0.11 * b
            if l < best_l:
                best, best_l = (r, g, b), l
    return best


def smear(img, center, radius, start, end, color, outline, width=3):
    """A pixel arc in front of the attacker, with a 1px dark edge."""
    out = img.copy()
    d = ImageDraw.Draw(out)
    box = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
    d.arc([box[0] - 1, box[1] - 1, box[2] + 1, box[3] + 1], start, end, fill=outline + (255,), width=width + 2)
    d.arc(box, start, end, fill=color + (255,), width=width)
    return out


# --- Animations --------------------------------------------------------------------

def anim_idle(img, pivot):
    """Breathing: the upper body sinks a pixel and comes back."""
    w, h = img.size
    waist = pivot[1] - (pivot[1] - (opaque_bbox(img) or (0, 0, w, h))[1]) // 2
    upper = img.crop((0, 0, w, waist))
    lower = img.crop((0, waist, w, h))
    frames = []
    for dy in (0, 0, 1, 1, 1, 0):
        f = blank(w, h)
        f.alpha_composite(lower, (0, waist))
        f.alpha_composite(upper, (0, dy))
        frames.append(f)
    return frames, [160, 120, 160, 160, 120, 160]


def anim_move(img, pivot, face):
    w, h = img.size
    frames = []
    for dy, la in ((0, 2), (-3, 4), (-5, 4), (-2, 2)):
        f = lean(img, pivot[1], la * face)
        frames.append(shift(f, 0, dy))
    return frames, [100, 100, 100, 100]


def anim_attack(img, pivot):
    """Wind-up, lunge with a smear, follow-through, recover. Right-facing art: the
    canvas grows right so the lunge isn't clipped."""
    w, h = img.size
    bb = opaque_bbox(img)
    light, dark = lightest(img), darkest(img)
    canvas = (w + 16, h)
    frames = []
    for dx, la, with_smear in ((-2, -5, False), (8, 6, True), (5, 3, False), (1, 0, False)):
        f = shift(lean(img, pivot[1], la), dx, 0, canvas)
        if with_smear:
            r = max(12, (bb[3] - bb[1]) // 3)
            cy = bb[1] + (bb[3] - bb[1]) * 2 // 5
            f = smear(f, (bb[2] + dx - r + 4, cy), r, -70, 70, light, dark)
        frames.append(f)
    return frames, [110, 90, 100, 120]


def anim_hurt(img, pivot):
    """Recoils back with a baked white flash on the first frame, then a red tinge."""
    frames = []
    for la, dx, flash, red in ((-6, -1, 0.85, 0.0), (-4, -1, 0.0, 0.3), (-1, 0, 0.0, 0.0)):
        f = shift(lean(img, pivot[1], la), dx, 0)
        if flash:
            f = tint(f, (255, 255, 255), flash)
        elif red:
            f = tint(f, (255, 70, 70), red)
        frames.append(f)
    return frames, [70, 90, 110]


def anim_broken(img, pivot):
    """Totters back, pitches forward, then crumples flat and greys out; the last
    frame holds. Squashing in place reads for every silhouette, where a topple
    stood wide poses on their weapons."""
    frames = []
    for la, sx, sy, sat, dark in ((-4, 1.0, 1.0, 0.0, 0.0), (6, 1.0, 0.96, 0.15, 0.0), (3, 1.06, 0.8, 0.35, 0.05),
                                  (0, 1.12, 0.62, 0.6, 0.1), (0, 1.18, 0.46, 0.85, 0.18), (0, 1.18, 0.46, 0.85, 0.18)):
        f = squash(lean(img, pivot[1], la), pivot, sx, sy)
        frames.append(desaturate(f, sat, dark))
    return frames, [90, 110, 80, 80, 100, 400]


def anim_gaze_in(img, pivot):
    """Squashes down toward the floor just before the puff swaps in the object."""
    frames = [squash(img, pivot, sx, sy) for sx, sy in ((1.0, 0.9), (1.1, 0.7), (1.2, 0.45))]
    return frames, [50, 50, 60]


def anim_gaze_out(img, pivot):
    """Springs back up out of the object: squashed, overshoot, settle."""
    frames = [squash(img, pivot, sx, sy) for sx, sy in ((1.2, 0.5), (0.92, 1.12), (1.04, 0.96), (1.0, 1.0))]
    return frames, [60, 70, 70, 80]


# --- Writing -------------------------------------------------------------------------

def write_sheet(folder, base, tag, frames, durations, note=""):
    os.makedirs(folder, exist_ok=True)
    fw, fh = frames[0].size
    sheet = blank(fw * len(frames), fh)
    data = {"frames": {}, "meta": {"app": "tools/bake_unit_anims.py", "image": base + "_sheet.png",
                                    "size": {"w": fw * len(frames), "h": fh}, "frameTags": [
                                        {"name": tag, "from": 0, "to": len(frames) - 1, "direction": "forward"}]}}
    if note:
        data["meta"]["note"] = note
    for i, (f, ms) in enumerate(zip(frames, durations)):
        sheet.alpha_composite(f, (i * fw, 0))
        data["frames"]["%s %d.aseprite" % (base, i)] = {
            "frame": {"x": i * fw, "y": 0, "w": fw, "h": fh}, "rotated": False, "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": fw, "h": fh}, "sourceSize": {"w": fw, "h": fh}, "duration": ms}
    sheet.save(os.path.join(folder, base + "_sheet.png"))
    with open(os.path.join(folder, base + "_sheet.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1)
    write_preview(folder, base, frames)


def write_preview(folder, base, frames):
    fw, fh = frames[0].size
    pad, label = 4, 14
    strip = Image.new("RGBA", (len(frames) * (fw + pad) + pad, fh + label + pad * 2), (196, 190, 180, 255))
    d = ImageDraw.Draw(strip)
    font = ImageFont.load_default()
    for i, f in enumerate(frames):
        x = pad + i * (fw + pad)
        strip.alpha_composite(f, (x, pad))
        d.text((x, fh + pad + 1), str(i), fill=(40, 36, 44, 255), font=font)
    strip.save(os.path.join(folder, base + "_preview.png"))


def bake(name):
    group = UNITS[name]
    img, meta = base_frame(group, name)
    pivot = tuple(meta["foot_pivot"])
    face = facing(name, meta)
    made = []
    if group == "enemies":
        frames, ms = anim_idle(img, pivot)
        write_sheet(os.path.join(ROOT, group, name), name, "idle", frames, ms)
        made.append("idle")
        assert face > 0, "enemy attack and hurt are authored for right-facing art"
        frames, ms = anim_move(img, pivot, face)
        write_sheet(os.path.join(DRAFTS, name + "_move"), name + "_move", "move", frames, ms)
        frames, ms = anim_attack(img, pivot)
        write_sheet(os.path.join(DRAFTS, name + "_attack"), name + "_attack", "attack", frames, ms,
                    "Wider frames so the lunge isn't clipped; left edge and foot pivot match the still.")
        frames, ms = anim_hurt(img, pivot)
        write_sheet(os.path.join(DRAFTS, name + "_hurt"), name + "_hurt", "hurt", frames, ms,
                    "Frame 0 carries the white hit flash, so the view doesn't tint it again.")
        made += ["move", "attack", "hurt"]
    frames, ms = anim_broken(img, pivot)
    write_sheet(os.path.join(DRAFTS, name + "_broken"), name + "_broken", "broken", frames, ms,
                "Crumples flat and greys out; the last frame holds before the fade.")
    frames, ms = anim_gaze_in(img, pivot)
    write_sheet(os.path.join(DRAFTS, name + "_gaze_in"), name + "_gaze_in", "gaze_in", frames, ms)
    frames, ms = anim_gaze_out(img, pivot)
    write_sheet(os.path.join(DRAFTS, name + "_gaze_out"), name + "_gaze_out", "gaze_out", frames, ms)
    made += ["broken", "gaze_in", "gaze_out"]
    print(name, ", ".join(made))


def main():
    names = sys.argv[1:] or list(UNITS)
    for n in names:
        bake(n)


if __name__ == "__main__":
    main()
