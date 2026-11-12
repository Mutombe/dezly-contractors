"""Topographic contour textures for section grounds.

    python _src/tools/make_contours.py

Builds a smooth terrain field (a few gaussian hills plus long ridges), traces
iso-lines with marching squares and writes three tinted SVGs to assets/img.
"""
import math, os
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
W, H, N = 1200, 800, 4          # output size and grid step (px)
rng = np.random.default_rng(7)

xs, ys = np.meshgrid(np.arange(0, W + N, N), np.arange(0, H + N, N))
z = np.zeros_like(xs, dtype=float)
for cx, cy, s, a in [(860, 260, 260, 1.0), (1040, 560, 200, .8), (620, 620, 300, .7), (300, 180, 340, .55), (180, 640, 220, .45)]:
    z += a * np.exp(-(((xs - cx) ** 2) + ((ys - cy) ** 2)) / (2 * s * s))
z += .06 * np.sin(xs / 140 + ys / 210) + .04 * np.sin(xs / 90 - ys / 60 + 1.3)

levels = np.linspace(z.min() + .04, z.max() - .02, 18)


def march(level):
    """Marching squares; returns line segments in px."""
    segs = []
    g = z > level
    rows, cols = z.shape
    def lerp(a, b, va, vb):
        t = (level - va) / (vb - va)
        return a + (b - a) * t
    for r in range(rows - 1):
        for c in range(cols - 1):
            tl, tr, br, bl = g[r, c], g[r, c + 1], g[r + 1, c + 1], g[r + 1, c]
            idx = tl * 8 + tr * 4 + br * 2 + bl
            if idx in (0, 15):
                continue
            x0, y0 = c * N, r * N
            vtl, vtr, vbr, vbl = z[r, c], z[r, c + 1], z[r + 1, c + 1], z[r + 1, c]
            top = (lerp(x0, x0 + N, vtl, vtr), y0)
            right = (x0 + N, lerp(y0, y0 + N, vtr, vbr))
            bottom = (lerp(x0, x0 + N, vbl, vbr), y0 + N)
            left = (x0, lerp(y0, y0 + N, vtl, vbl))
            table = {1: [(left, bottom)], 2: [(bottom, right)], 3: [(left, right)], 4: [(top, right)],
                     5: [(left, top), (bottom, right)], 6: [(top, bottom)], 7: [(left, top)], 8: [(left, top)],
                     9: [(top, bottom)], 10: [(left, bottom), (top, right)], 11: [(top, right)], 12: [(left, right)],
                     13: [(bottom, right)], 14: [(left, bottom)]}
            segs += table[idx]
    return segs


def chain(segs):
    """Join segments into polylines."""
    key = lambda p: (round(p[0], 2), round(p[1], 2))
    ends = {}
    for i, (a, b) in enumerate(segs):
        ends.setdefault(key(a), []).append((i, 0)); ends.setdefault(key(b), []).append((i, 1))
    used, lines = set(), []
    for i in range(len(segs)):
        if i in used:
            continue
        used.add(i); line = [segs[i][0], segs[i][1]]
        for direction in (1, 0):
            while True:
                tip = line[-1] if direction else line[0]
                nxt = [(j, e) for j, e in ends.get(key(tip), []) if j not in used]
                if not nxt:
                    break
                j, e = nxt[0]; used.add(j)
                p = segs[j][1 - e]
                line.append(p) if direction else line.insert(0, p)
        lines.append(line)
    return lines


def thin(line, step=3):
    return line[::step] + [line[-1]] if len(line) > step * 2 else line


paths = []
for k, lv in enumerate(levels):
    for line in chain(march(lv)):
        if len(line) < 6:
            continue
        pts = thin(line)
        d = 'M' + 'L'.join(f'{x:.0f} {y:.0f}' for x, y in pts)
        paths.append((d, k % 5 == 4))   # every fifth line is an index contour

for name, colour in [('contours-ink', '#06050f'), ('contours-white', '#ffffff')]:
    body = ''.join(f'<path d="{d}" stroke-width="{1.6 if idx else .9}"/>' for d, idx in paths)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" fill="none" stroke="{colour}" '
           f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
    with open(os.path.join(ROOT, 'assets', 'img', name + '.svg'), 'w', encoding='utf-8') as f:
        f.write(svg)
    print(name, len(svg) // 1024, 'KB')
