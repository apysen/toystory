"""Paint the HD surface library for the study-floor diorama (numpy + scipy + Pillow).

python tools/gen_textures.py            -> every surface
python tools/gen_textures.py wood card  -> some

Writes assets/textures/surfaces/<name>_{albedo,normal,rough}.png. Each surface is
a tileable set of maps built from one height field, so albedo, normals and
roughness agree about where the grain, seams and scuffs are. Albedos stay light
where the level tints them per piece (book cloth, paint).

The noise helpers and the wood, timber, fabric, metal and plaster surfaces are
ported from the Kowloon project's scripts/make_textures.py, retuned for a
child's study seen at toy scale.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "textures", "surfaces")
N = 512


# --- noise ----------------------------------------------------------------------

def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def spectral(shape, beta: float, seed: int, stretch=(1.0, 1.0), lo: float = 1.0, hi: float | None = None):
    """Periodic fractal noise: white noise shaped by a 1/f^beta spectrum."""
    h, w = shape
    white = rng(seed).standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None] * h / stretch[1]
    fx = np.fft.fftfreq(w)[None, :] * w / stretch[0]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    amp = 1.0 / np.power(f, beta)
    amp[f < lo] = 0.0
    if hi is not None:
        amp[f > hi] = 0.0
    return norm(np.real(np.fft.ifft2(np.fft.fft2(white) * amp)))


def norm(a):
    a = a - a.min()
    m = a.max()
    return a / m if m > 0 else a


def smooth(a, lo, hi):
    t = np.clip((a - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def worley(shape, count: int, seed: int):
    """Periodic cellular noise: (F1, F2, cell index) in pixels."""
    h, w = shape
    pts = rng(seed).random((count, 2)) * [w, h]
    tree = cKDTree(pts, boxsize=[w, h])
    yy, xx = np.mgrid[0:h, 0:w]
    q = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], -1)
    d, i = tree.query(q, k=2)
    return d[:, 0].reshape(h, w), d[:, 1].reshape(h, w), i[:, 0].reshape(h, w)


def normal_map(height, strength: float):
    """OpenGL-convention normal map (green up), which is what Godot expects."""
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5 * strength
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5 * strength
    nx, ny, nz = -dx, dy, np.ones_like(height)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5


def color(hexstr: str):
    hexstr = hexstr.lstrip("#")
    return np.array([int(hexstr[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def lerp(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2:
        t = t[..., None]
    return a + (b - a) * t


def save(name: str, albedo, height, strength, rough):
    os.makedirs(OUT, exist_ok=True)

    def img(a, mode="RGB"):
        return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), mode)

    img(albedo).save(os.path.join(OUT, f"{name}_albedo.png"), optimize=True)
    img(normal_map(height, strength)).save(os.path.join(OUT, f"{name}_normal.png"), optimize=True)
    img(np.clip(rough, 0, 1), "L").save(os.path.join(OUT, f"{name}_rough.png"), optimize=True)
    print("wrote", name)


# --- surfaces ---------------------------------------------------------------------

def wood():
    """Varnished floorboards running along U, 8 planks per tile."""
    s = (N, N)
    planks = 8
    ph = N / planks
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    row = (yy // ph).astype(int)
    g = rng(51)
    offs = g.random(planks) * N
    lengths = (0.55 + g.random(planks) * 0.45) * N
    tone = g.random(planks)
    local_x = (xx + offs[row]) % lengths[row]
    butt = 1.0 - smooth(np.minimum(local_x, lengths[row] - local_x), 0.5, 2.0)
    ty = yy % ph
    gap = 1.0 - smooth(np.minimum(ty, ph - ty), 0.6, 2.2)
    # Grain runs along the planks: smooth wobble, streaks long in x and fine in y.
    warp = spectral(s, 3.2, 52) * 8
    grain = np.sin((yy + warp + row * 37.0) * 0.3) * 0.5 + 0.5
    grain = grain * 0.6 + 0.2
    fine = spectral(s, 1.2, 54, stretch=(1, 30), lo=4)
    knot = 1.0 - smooth(worley(s, 10, 55)[0], 3, 9)
    alb = lerp(color("#7d5233"), color("#c8945f"), (0.55 * grain + 0.45 * fine) * (0.7 + 0.3 * tone[row]))
    alb = alb * (0.85 + 0.15 * tone[row][..., None])
    alb = lerp(alb, color("#4a2c18"), knot * 0.7)
    alb = lerp(alb, color("#2a180c"), np.maximum(gap, butt) * 0.85)
    wear = smooth(spectral(s, 2.0, 56), 0.45, 1.0)
    alb = lerp(alb, color("#b98e66"), wear * 0.18)
    height = fine * 0.25 + grain * 0.12 - np.maximum(gap, butt) * 1.0 - knot * 0.15
    rough = 0.38 + 0.3 * wear + 0.1 * fine + np.maximum(gap, butt) * 0.4
    save("wood", alb, height, 5.0, rough)


def timber():
    """Furniture timber (the desk): one continuous varnished board, grain along U."""
    s = (N, N)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    warp = spectral(s, 3.4, 131, stretch=(1, 3)) * 40
    spacing = spectral(s, 2.6, 137, stretch=(1, 6)) * 4.0
    rings = np.sin((yy + warp) * 2 * math.pi * 14 / N + spacing) * 0.5 + 0.5
    rings = smooth(rings, 0.55, 1.0) * 0.7 + rings * 0.3
    fine = spectral(s, 1.0, 132, stretch=(1, 40), lo=6)
    figure = spectral(s, 1.8, 133, stretch=(1, 10))
    pores = smooth(spectral(s, 0.4, 134, stretch=(1, 20), lo=40), 0.7, 0.9)
    alb = lerp(color("#c9935c"), color("#7b4d2c"), np.clip(rings * 0.3 + fine * 0.35 + figure * 0.35, 0, 1))
    alb = lerp(alb, color("#4a2c18"), pores * 0.15)
    wear = smooth(spectral(s, 2.0, 136), 0.55, 1.0)
    alb = lerp(alb, color("#d8b48a"), wear * 0.1)
    height = fine * 0.08 - pores * 0.12
    rough = 0.3 + 0.25 * wear + 0.1 * pores
    save("timber", alb, height, 1.5, rough)


def paint():
    """Painted wall and skirting: smooth emulsion with roller texture and scuffs."""
    s = (N, N)
    undulate = spectral(s, 2.4, 11)
    roller = spectral(s, 0.9, 12, lo=30)
    scuff = smooth(spectral(s, 1.3, 13, stretch=(10, 1)), 0.78, 0.9)
    alb = np.ones((N, N, 3)) * color("#f2ede4")
    alb = alb * (0.95 + 0.03 * undulate[..., None] + 0.02 * roller[..., None])
    alb = lerp(alb, color("#b9b0a2"), scuff * 0.35)
    height = undulate * 0.4 + roller * 0.3
    rough = 0.75 + 0.1 * roller - scuff * 0.1
    save("paint", alb, height, 2.0, rough)


def fabric():
    """Woven rug: chunky weave with a little pile and wear."""
    s = (N, N)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    wx = np.sin(xx * math.pi / 4.0) * 0.5 + 0.5
    wy = np.sin(yy * math.pi / 4.0) * 0.5 + 0.5
    weave = np.where(((xx // 4 + yy // 4) % 2) == 0, wx, wy)
    pile = spectral(s, 1.0, 101, lo=20)
    wear = spectral(s, 2.2, 102)
    alb = np.ones((N, N, 3)) * color("#f1ebe0")
    alb = alb * (0.86 + 0.1 * weave[..., None] + 0.04 * pile[..., None])
    alb = alb * (0.92 + 0.08 * wear[..., None])
    height = weave * 0.6 + pile * 0.4
    rough = 0.97 - 0.05 * weave
    save("fabric", alb, height, 4.0, rough)


def metal():
    """Painted steel (the filing cabinet): satin enamel with fine orange peel and chips."""
    s = (N, N)
    peel = spectral(s, 1.0, 91, lo=25)
    chip = smooth(spectral(s, 1.5, 92, lo=4), 0.85, 0.86)
    alb = np.ones((N, N, 3)) * color("#e9ebe8")
    alb = alb * (0.96 + 0.04 * peel[..., None])
    alb = lerp(alb, color("#3d3a36"), chip * 0.8)
    height = peel * 0.15 - chip * 0.4
    rough = 0.42 + 0.06 * peel + chip * 0.3
    save("metal", alb, height, 2.0, rough)


def chrome():
    """Brushed chrome for the chair column and casters."""
    s = (N, N)
    brush = spectral(s, 0.8, 141, stretch=(1, 60), lo=10)
    smudge = smooth(spectral(s, 2.0, 142), 0.6, 0.95)
    alb = np.ones((N, N, 3)) * color("#d7dbe0")
    alb = alb * (0.92 + 0.08 * brush[..., None])
    height = brush * 0.1
    rough = 0.18 + 0.08 * brush + smudge * 0.25
    save("chrome", alb, height, 1.0, rough)


def card():
    """Corrugated kraft cardboard: fibres, faint flute ridges and a few scuffs."""
    s = (N, N)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    flute = np.sin(xx * 2 * math.pi * 32 / N) * 0.5 + 0.5
    fibre = spectral(s, 0.7, 151, stretch=(3, 1), lo=20)
    blot = smooth(spectral(s, 2.0, 152), 0.5, 1.0)
    scuff = smooth(spectral(s, 1.2, 153, stretch=(1, 8)), 0.8, 0.9)
    alb = lerp(color("#a87a48"), color("#c99b63"), 0.6 * fibre + 0.4 * (1 - blot))
    alb = lerp(alb, color("#8a6038"), scuff * 0.4)
    height = flute * 0.25 + fibre * 0.2 - scuff * 0.2
    rough = 0.9 - 0.05 * fibre
    save("card", alb, height, 2.5, rough)


def cloth():
    """Book cloth: fine linen weave, near-white so each book tints its own colour."""
    s = (N, N)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    weave = (np.sin(xx * math.pi / 1.5) * np.sin(yy * math.pi / 1.5)) * 0.5 + 0.5
    slub = spectral(s, 1.0, 161, stretch=(30, 1), lo=8)
    rub = smooth(spectral(s, 2.0, 162), 0.6, 1.0)
    alb = np.ones((N, N, 3)) * color("#f3efe8")
    alb = alb * (0.88 + 0.08 * weave[..., None] + 0.04 * slub[..., None])
    alb = lerp(alb, color("#ffffff"), rub * 0.12)
    height = weave * 0.3 + slub * 0.2
    rough = 0.85 - rub * 0.15
    save("cloth", alb, height, 2.0, rough)


def pages():
    """Page edges seen from the side of a closed book: fine horizontal lines."""
    s = (N, N)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    lines = np.sin(yy * math.pi / 1.2 + spectral(s, 1.5, 171, stretch=(20, 1)) * 3) * 0.5 + 0.5
    age = spectral(s, 2.2, 172)
    alb = lerp(color("#efe6cf"), color("#d9caa6"), age * 0.6)
    alb = alb * (0.92 + 0.08 * lines[..., None])
    height = lines * 0.3
    rough = 0.9
    save("pages", alb, height, 1.5, np.ones(s) * rough)


def spill():
    """Spilled juice: deep amber with glossy ripples."""
    s = (N, N)
    ripple = spectral(s, 2.6, 181)
    depth = spectral(s, 1.8, 182)
    alb = lerp(color("#6b2f12"), color("#b65a1c"), depth * 0.6)
    height = ripple * 0.3
    rough = 0.04 + 0.04 * ripple
    save("spill", alb, height, 1.0, rough)


SURFACES = {
    "wood": wood, "timber": timber, "paint": paint, "fabric": fabric, "metal": metal,
    "chrome": chrome, "card": card, "cloth": cloth, "pages": pages, "spill": spill,
}


if __name__ == "__main__":
    for name in sys.argv[1:] or list(SURFACES):
        SURFACES[name]()
