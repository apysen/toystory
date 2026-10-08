"""Generate placeholder retro SFX for the slice (stdlib only).

python3 tools/gen_sfx.py  ->  assets/audio/sfx/*.wav

These are stand-ins until real object recordings exist
(vertical_slice_plan.md section 23).
"""
import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "audio", "sfx")


def write(name, samples):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    peak = max(1e-6, max(abs(s) for s in samples))
    scale = 0.8 / peak
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s * scale)) * 32767)) for s in samples))


def env(i, n, attack=0.005, release=None):
    t = i / RATE
    a = min(1.0, t / attack) if attack > 0 else 1.0
    r = 1.0 - i / n if release is None else math.exp(-t / release)
    return a * r


def square(f, t):
    return 1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0


def crush(x, steps=8):
    return round(x * steps) / steps


def tone(dur, f0, f1=None, wave_fn=square, release=None, bits=8):
    n = int(RATE * dur)
    f1 = f0 if f1 is None else f1
    out, phase = [], 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * i / n
        phase += f / RATE
        out.append(crush(wave_fn(1.0, phase), bits) * env(i, n, release=release))
    return out


def noise(dur, release=None, lp=0.0):
    n = int(RATE * dur)
    out, prev = [], 0.0
    for i in range(n):
        x = random.uniform(-1, 1)
        prev = prev * lp + x * (1 - lp)
        out.append(prev * env(i, n, release=release))
    return out


def mix(*parts, offsets=None):
    offsets = offsets or [0] * len(parts)
    n = max(len(p) + int(o * RATE) for p, o in zip(parts, offsets))
    out = [0.0] * n
    for p, o in zip(parts, offsets):
        k = int(o * RATE)
        for i, s in enumerate(p):
            out[k + i] += s
    return out


def main():
    random.seed(7)
    sq = lambda a, ph: 1.0 if (ph % 1.0) < 0.5 else -1.0
    tri = lambda a, ph: 4 * abs((ph % 1.0) - 0.5) - 1
    # UI
    write("ui_move", tone(0.04, 880, wave_fn=sq))
    write("ui_select", mix(tone(0.05, 660, wave_fn=sq), tone(0.06, 990, wave_fn=sq), offsets=[0, 0.05]))
    write("ui_cancel", tone(0.09, 520, 300, wave_fn=sq))
    write("ui_confirm", mix(tone(0.05, 784, wave_fn=sq), tone(0.08, 1175, wave_fn=sq), offsets=[0, 0.05]))
    # Combat
    write("hit", mix(noise(0.08, release=0.03), tone(0.08, 180, 60, wave_fn=sq, release=0.04)))
    write("crit", mix(noise(0.16, release=0.06), tone(0.18, 260, 50, wave_fn=sq, release=0.08), tone(0.1, 1400, 900, wave_fn=sq), offsets=[0, 0, 0.02]))
    write("miss", tone(0.12, 900, 1600, wave_fn=tri, release=0.05))
    write("broken", mix(tone(0.4, 400, 70, wave_fn=sq), noise(0.3, release=0.12, lp=0.6), offsets=[0, 0.05]))
    write("heal", mix(*[tone(0.08, f, wave_fn=tri) for f in (523, 659, 784, 1047)], offsets=[0, 0.06, 0.12, 0.18]))
    write("collision", mix(noise(0.12, release=0.05, lp=0.7), tone(0.12, 90, 40, wave_fn=sq, release=0.05)))
    # Object actions
    write("staple", mix(noise(0.02, release=0.006), tone(0.03, 2400, 1800, wave_fn=sq, release=0.01), noise(0.03, release=0.01), offsets=[0, 0.005, 0.04]))
    write("toaster_pop", mix(tone(0.15, 300, 1200, wave_fn=tri, release=0.08), noise(0.05, release=0.02), offsets=[0, 0]))
    write("toaster_heat", mix(noise(0.5, lp=0.85), tone(0.5, 110, 140, wave_fn=sq)))
    write("vacuum_suction", mix(tone(0.6, 70, 140, wave_fn=sq), noise(0.6, lp=0.5)))
    write("vacuum_blow", mix(tone(0.5, 160, 60, wave_fn=sq), noise(0.5, lp=0.3)))
    write("lamp_flash", mix(tone(0.05, 3000, wave_fn=sq), tone(0.25, 1500, 400, wave_fn=tri, release=0.1), offsets=[0, 0.03]))
    write("teacup_pour", mix(*[tone(0.05, 600 + 90 * k, 900 + 90 * k, wave_fn=tri) for k in range(5)], offsets=[0.06 * k for k in range(5)]))
    write("umbrella_snap", mix(noise(0.04, release=0.01, lp=0.2), tone(0.08, 500, 1500, wave_fn=sq, release=0.03), offsets=[0, 0.02]))
    write("rubber_snap", tone(0.1, 1600, 200, wave_fn=sq, release=0.04))
    write("tape_rip", noise(0.25, lp=0.1))
    write("cutter_slice", mix(noise(0.15, lp=0.05), tone(0.2, 2200, 600, wave_fn=tri, release=0.07)))
    write("telegraph", mix(tone(0.12, 440, wave_fn=sq), tone(0.12, 440, wave_fn=sq), offsets=[0, 0.2]))
    # Human Gaze
    write("gaze", mix(tone(1.0, 220, 196, wave_fn=tri, release=0.5), tone(1.0, 330, 294, wave_fn=tri, release=0.5), tone(0.15, 1760, wave_fn=sq), offsets=[0.1, 0.1, 0]))
    write("gaze_end", tone(0.4, 196, 330, wave_fn=tri, release=0.2))
    write("phase", mix(tone(0.08, 523, wave_fn=sq), tone(0.08, 784, wave_fn=sq), tone(0.15, 1047, wave_fn=sq), offsets=[0, 0.08, 0.16]))
    write("victory", mix(*[tone(0.14, f, wave_fn=sq) for f in (523, 659, 784, 1047, 784, 1047)], offsets=[0.12 * k for k in range(6)]))
    write("defeat", mix(*[tone(0.2, f, wave_fn=tri) for f in (392, 349, 311, 262)], offsets=[0.18 * k for k in range(4)]))


if __name__ == "__main__":
    main()
