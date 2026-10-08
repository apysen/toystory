"""Generate the placeholder "Under the Desk" battle theme (stdlib + ffmpeg).

python tools/gen_music.py  ->  assets/audio/music/under_the_desk_theme.ogg

A quiet, sneaky chiptune loop for the study floor: plucked bass, a ticking
clock hat, soft pad chords and a tiptoe lead. Music matches the room rather
than any character (vertical_slice_plan.md section 23). Stand-in until a real
track exists; the loop point is the end of the file.
"""
import math
import os
import random
import struct
import subprocess
import wave

RATE = 22050
BPM = 104
BEAT = 60.0 / BPM
STEP = BEAT / 4  # sixteenth note
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "audio", "music")
NAME = "under_the_desk_theme"

A4 = 440.0
NOTE_INDEX = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}


def freq(note):
    """'A3', 'C#4' -> Hz."""
    name, octave = note[:-1], int(note[-1])
    return A4 * 2 ** ((NOTE_INDEX[name] + 12 * (octave - 4)) / 12)


# Four bars per phrase, one chord per bar: Am - F - C - E (section A),
# Dm - Am - F - E (section B). Each chord: (bass root, pad notes).
SECTION_A = [("A2", ["A3", "C4", "E4"]), ("F2", ["F3", "A3", "C4"]), ("C3", ["G3", "C4", "E4"]), ("E2", ["G#3", "B3", "E4"])]
SECTION_B = [("D3", ["F3", "A3", "D4"]), ("A2", ["A3", "C4", "E4"]), ("F2", ["F3", "A3", "C4"]), ("E2", ["G#3", "B3", "D4"])]

# Lead motifs, one per bar: (step, length in steps, note). None bars rest.
LEAD_A = [
    [(0, 2, "E5"), (3, 1, "D5"), (4, 2, "C5"), (8, 2, "B4"), (11, 1, "C5"), (12, 3, "A4")],
    [(0, 2, "A4"), (3, 1, "C5"), (4, 2, "F5"), (8, 4, "E5"), (12, 2, "C5")],
    [(0, 2, "G4"), (3, 1, "C5"), (4, 2, "E5"), (8, 2, "G5"), (11, 1, "E5"), (12, 3, "D5")],
    [(0, 3, "B4"), (4, 1, "G#4"), (6, 1, "B4"), (8, 6, "E5")],
]
LEAD_B = [
    [(0, 4, "F5"), (6, 1, "E5"), (8, 2, "D5"), (12, 3, "A4")],
    [(0, 2, "C5"), (3, 1, "B4"), (4, 4, "A4"), (12, 2, "E5")],
    [(0, 2, "F5"), (2, 2, "E5"), (4, 2, "C5"), (8, 4, "A4")],
    [(0, 2, "G#4"), (4, 2, "B4"), (8, 2, "D5"), (12, 4, "E5")],
]
# Pizzicato bass pattern in sixteenth steps: (step, octave shift).
BASS_STEPS = [(0, 0), (6, 0), (8, 1), (10, 0), (14, 1)]


def square(phase, duty=0.5):
    return 1.0 if (phase % 1.0) < duty else -1.0


def triangle(phase):
    p = phase % 1.0
    return 4 * p - 1 if p < 0.5 else 3 - 4 * p


def add(buf, start_s, samples):
    i0 = int(start_s * RATE)
    for i, s in enumerate(samples):
        j = i0 + i
        if j < len(buf):
            buf[j] += s


def pluck(f, dur, vol):
    n = int(dur * RATE)
    return [vol * triangle(f * i / RATE) * math.exp(-i / RATE / 0.12) for i in range(n)]


def lead_note(f, dur, vol):
    n = int(dur * RATE)
    out = []
    for i in range(n):
        t = i / RATE
        vib = 1 + 0.004 * math.sin(2 * math.pi * 5.5 * max(0.0, t - 0.08))
        a = min(1.0, t / 0.01)
        r = min(1.0, (n - i) / (0.04 * RATE))
        out.append(vol * a * r * square(f * vib * t, 0.25))
    return out


def pad(notes, dur, vol):
    n = int(dur * RATE)
    fs = [freq(x) for x in notes]
    out = []
    for i in range(n):
        t = i / RATE
        a = min(1.0, t / 0.25)
        r = min(1.0, (n - i) / (0.3 * RATE))
        s = sum(triangle(f * t) + 0.3 * triangle(f * 1.003 * t) for f in fs) / len(fs)
        out.append(vol * a * r * s)
    return out


def tick(vol, rng):
    n = int(0.03 * RATE)
    return [vol * (rng.random() * 2 - 1) * math.exp(-i / RATE / 0.006) for i in range(n)]


def render():
    rng = random.Random(7)
    bars = SECTION_A + SECTION_A + SECTION_B + SECTION_A
    leads = [None, None, None, None] + LEAD_A + LEAD_B + LEAD_A
    bar_s = BEAT * 4
    total = int(len(bars) * bar_s * RATE)
    buf = [0.0] * total
    for b, (root, chord) in enumerate(bars):
        t0 = b * bar_s
        add(buf, t0, pad(chord, bar_s, 0.11))
        rf = freq(root)
        for step, octave in BASS_STEPS:
            add(buf, t0 + step * STEP, pluck(rf * (2 ** octave), STEP * 2.2, 0.32))
        # Clock tick on every beat, a softer one on the off-beats.
        for s in range(16):
            if s % 4 == 0:
                add(buf, t0 + s * STEP, tick(0.10, rng))
            elif s % 2 == 0:
                add(buf, t0 + s * STEP, tick(0.04, rng))
        motif = leads[b]
        if motif:
            for step, length, note in motif:
                add(buf, t0 + step * STEP, lead_note(freq(note), length * STEP * 0.92, 0.10))
    return buf


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    samples = render()
    peak = max(1e-6, max(abs(s) for s in samples))
    scale = 0.7 / peak
    wav_path = os.path.join(OUT_DIR, NAME + ".wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s * scale)) * 32767)) for s in samples))
    ogg_path = os.path.join(OUT_DIR, NAME + ".ogg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav_path, "-c:a", "libvorbis", "-q:a", "4", ogg_path], check=True)
    os.remove(wav_path)
    print("wrote", os.path.normpath(ogg_path), "%.1fs" % (len(samples) / RATE))


if __name__ == "__main__":
    main()
