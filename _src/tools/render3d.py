"""Dezly Contractors — 3D object renderer.

Ray-marches signed distance functions with numpy and writes transparent WebP
renders used across the site (assets/img/obj-*.webp).

Run:  python _src/tools/render3d.py            (renders all)
      python _src/tools/render3d.py hat nut    (renders a subset)
"""
import sys, os
import numpy as np
from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'img')
SIZE = 560            # final canvas before crop
SS = 2                # supersample factor

# ---------------------------------------------------------------- helpers
def norm(v):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-9)

def length(v):
    return np.linalg.norm(v, axis=-1)

def rot(ax, ay, az):
    ax, ay, az = np.radians([ax, ay, az])
    Rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    Ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)

def sd_rbox(p, b, r):
    q = np.abs(p) - (np.array(b) - r)
    return length(np.maximum(q, 0)) + np.minimum(np.max(q, axis=-1), 0) - r

def sd_hex2d(x, z, r):
    k = np.array([-0.866025404, 0.5, 0.577350269])
    px, pz = np.abs(x), np.abs(z)
    d = np.minimum(k[0] * px + k[1] * pz, 0)
    px = px - 2 * d * k[0]
    pz = pz - 2 * d * k[1]
    cx = np.clip(px, -k[2] * r, k[2] * r)
    return np.hypot(px - cx, pz - r) * np.sign(pz - r)

def extrude(d2, y, h):
    w = np.stack([d2, np.abs(y) - h], -1)
    return np.minimum(np.maximum(w[..., 0], w[..., 1]), 0) + length(np.maximum(w, 0))

def sd_capcone(p, h, r1, r2):
    qx = np.hypot(p[..., 0], p[..., 2]); qy = p[..., 1]
    k1 = np.array([r2, h]); k2 = np.array([r2 - r1, 2 * h])
    cax = qx - np.minimum(qx, np.where(qy < 0, r1, r2)); cay = np.abs(qy) - h
    t = np.clip(((k1[0] - qx) * k2[0] + (k1[1] - qy) * k2[1]) / (k2 @ k2), 0, 1)
    cbx = qx - k1[0] + k2[0] * t; cby = qy - k1[1] + k2[1] * t
    s = np.where((cbx < 0) & (cay < 0), -1.0, 1.0)
    return s * np.sqrt(np.minimum(cax ** 2 + cay ** 2, cbx ** 2 + cby ** 2))

# Material ids
M_YEL, M_INK, M_STEEL, M_BLUE, M_WHITE, M_GLASS, M_ZINC = 0, 1, 2, 3, 4, 5, 6

# ---------------------------------------------------------------- shapes
# Each returns (distance, material_id)

def shape_nut(p):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    outer = extrude(sd_hex2d(x, z, 0.86) + 0.07, y, 0.30) - 0.07
    # chamfer: intersect with a double cone-ish sphere
    outer = np.maximum(outer, length(p * np.array([1, 1.9, 1])) - 1.12)
    hole_r = 0.44 + 0.018 * np.sin(y * 40.0)          # thread ridges
    hole = np.hypot(x, z) - hole_r
    d = np.maximum(outer, -hole)
    m = np.where(np.hypot(x, z) < 0.53, M_INK, M_ZINC)
    return d, m

def shape_beam(p):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    L = 0.95
    top = sd_rbox(p - np.array([0, 0.52, 0]), (0.56, 0.075, L), 0.025)
    bot = sd_rbox(p - np.array([0, -0.52, 0]), (0.56, 0.075, L), 0.025)
    web = sd_rbox(p, (0.075, 0.5, L), 0.02)
    d = smin(smin(top, web, 0.06), bot, 0.06)
    # end face shows raw ink-coloured cut
    m = np.where(np.abs(z) > L - 0.012, M_INK, M_YEL)
    return d, m

def shape_hat(p):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    q = p - np.array([0, -0.15, 0])
    e = q / np.array([0.86, 0.80, 1.0])
    dome = (length(e) - 1.0) * 0.82
    dome = np.maximum(dome, -q[..., 1])
    ridge = np.maximum((length(q / np.array([0.9, 0.86, 1.05])) - 1.0) * 0.85, np.abs(q[..., 0]) - 0.11)
    ridge = np.maximum(ridge, -q[..., 1] - 0.05)
    # brim: wider at front (peak), thin
    bq = q - np.array([0, 0.0, 0.10])
    br = np.hypot(bq[..., 0] / 1.08, bq[..., 2] / 1.22)
    brim = extrude((br - 1.0) * 1.05, bq[..., 1] - 0.0, 0.035) - 0.02
    d = smin(smin(dome, ridge, 0.05), brim, 0.08)
    m = np.full(d.shape, M_YEL)
    # dezly-blue band near brim
    m = np.where((q[..., 1] > 0.05) & (q[..., 1] < 0.12) & (br < 0.93), M_BLUE, m)
    return d, m

def shape_pipe(p):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    R, r = 0.72, 0.30
    c = p + np.array([0.36, 0.36, 0])                     # torus centre
    tor = np.hypot(np.hypot(c[..., 0], c[..., 1]) - R, c[..., 2]) - r
    tor = np.maximum(tor, np.maximum(-c[..., 0], -c[..., 1]))
    # straight stubs
    s1 = np.maximum(np.hypot(c[..., 0] - R, c[..., 2]) - r, np.abs(c[..., 1] + 0.18) - 0.18)
    s2 = np.maximum(np.hypot(c[..., 1] - R, c[..., 2]) - r, np.abs(c[..., 0] + 0.18) - 0.18)
    pipe = np.minimum(np.minimum(tor, s1), s2)
    # flanges
    f1 = np.maximum(np.hypot(c[..., 0] - R, c[..., 2]) - 0.42, np.abs(c[..., 1] + 0.36) - 0.06) - 0.012
    f2 = np.maximum(np.hypot(c[..., 1] - R, c[..., 2]) - 0.42, np.abs(c[..., 0] + 0.36) - 0.06) - 0.012
    fl = np.minimum(f1, f2)
    d = np.minimum(pipe, fl)
    # bores
    b1 = np.maximum(np.hypot(c[..., 0] - R, c[..., 2]) - 0.2, c[..., 1] + 0.1)
    b2 = np.maximum(np.hypot(c[..., 1] - R, c[..., 2]) - 0.2, c[..., 0] + 0.1)
    d = np.maximum(d, -np.minimum(b1, b2))
    m = np.where(fl < pipe + 0.002, M_STEEL, M_BLUE)
    m = np.where(np.minimum(b1, b2) > -0.03, np.where(np.minimum(b1, b2) < 0.03, M_INK, m), m)
    return d, m

def shape_cone(p):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    cone = sd_capcone(p - np.array([0, 0.12, 0]), 0.78, 0.46, 0.07) - 0.02
    base = sd_rbox(p - np.array([0, -0.70, 0]), (0.68, 0.05, 0.68), 0.05)
    d = smin(cone, base, 0.03)
    yy = y - 0.12
    band = ((yy > -0.25) & (yy < -0.05)) | ((yy > 0.22) & (yy < 0.38))
    m = np.where(band, M_WHITE, M_YEL)
    m = np.where(y < -0.63, M_INK, m)
    return d, m

def shape_house(p):
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    body = sd_rbox(p - np.array([0, -0.28, 0]), (0.66, 0.42, 0.52), 0.04)
    # roof: triangular prism along z
    q = p - np.array([0, 0.14, 0])
    tri = np.maximum(np.abs(q[..., 2]) - 0.62,
                     np.maximum(np.abs(q[..., 0]) * 0.70 + q[..., 1] * 0.72 - 0.56, -q[..., 1]))
    roof = tri - 0.03
    chim = sd_rbox(p - np.array([0.40, 0.42, -0.22]), (0.09, 0.26, 0.09), 0.02)
    d = smin(smin(body, roof, 0.02), chim, 0.02)
    # door cut-in
    door = sd_rbox(p - np.array([0.0, -0.48, 0.52]), (0.12, 0.24, 0.05), 0.02)
    d = np.maximum(d, -door)
    m = np.where(roof < body - 0.0, M_YEL, M_GLASS)
    m = np.where(chim < 0.01, M_YEL, m)
    return d, m

SHAPES = {
    #  name    fn           pose (x, y, z)        scale
    'nut':   (shape_nut,   (58, 24, -18),        1.10),
    'beam':  (shape_beam,  (22, -38, -16),       0.92),
    'hat':   (shape_hat,   (16, -30, 6),         1.00),
    'pipe':  (shape_pipe,  (-14, 28, 8),         1.18),
    'cone':  (shape_cone,  (14, -20, -8),        1.00),
    'house': (shape_house, (14, -34, 0),         1.02),
}

# ---------------------------------------------------------------- studio
def env(d):
    y = d[..., 1]
    sky = np.array([0.95, 0.97, 1.0]); hor = np.array([0.30, 0.32, 0.38]); flo = np.array([0.10, 0.09, 0.08])
    t = np.clip(y, -1, 1)[..., None]
    c = np.where(t > 0, hor + (sky - hor) * np.sqrt(np.clip(t, 0, 1)), hor + (flo - hor) * np.sqrt(np.clip(-t, 0, 1)))
    c = c * (0.78 + 0.22 * np.clip(d[..., 0:1] + 0.3, 0, 1))          # darker left
    strip1 = np.exp(-((y - 0.18) / 0.06) ** 2) * 1.6
    strip2 = np.exp(-((d[..., 0] - 0.75) / 0.08) ** 2) * 1.1 * (d[..., 2] > -0.2)
    soft = np.exp(-(((d[..., 0] + 0.45) ** 2 + (y - 0.35) ** 2) / 0.10)) * 1.5 * (d[..., 2] > 0)
    return c + (strip1 + strip2 + soft)[..., None] * np.array([1.0, 0.98, 0.95])

LIGHTS = [  # dir, sharpness, strength, colour
    ((-0.55, 0.75, 0.65), 22, 4.2, (1.0, 0.98, 0.95)),
    ((0.85, 0.25, -0.45), 10, 1.6, (0.75, 0.88, 1.0)),   # cool rim (Dezly azure)
    ((0.0, 1.0, 0.1), 6, 0.6, (1, 1, 1)),
    ((0.6, -0.4, 0.7), 9, 0.5, (1.0, 0.85, 0.55)),       # warm bounce
]

def fresnel(f0, ndv):
    return f0 + (1 - f0) * (1 - ndv) ** 5

def shade(P, N, V, mat, ao):
    ndv = np.clip(np.sum(N * V, -1), 0, 1)[..., None]
    R = norm(2 * np.sum(N * V, -1, keepdims=True) * N - V)
    E = env(R)
    key = norm(np.array(LIGHTS[0][0]))
    ndl = np.clip(N @ key, 0, 1)[..., None]
    H = norm(key + V)
    ndh = np.clip(np.sum(N * H, -1), 0, 1)[..., None]
    rim = np.zeros_like(N)
    for dvec, sh, st, col in LIGHTS[1:]:
        L = norm(np.array(dvec)); rim += (np.clip(N @ L, 0, 1)[..., None] ** (sh / 6)) * st * 0.12 * np.array(col)
    out = np.zeros_like(N); alpha = np.ones(N.shape[:-1])
    m = mat[..., None]

    # yellow lacquer (painted steel / ABS)
    base = np.array([1.0, 0.74, 0.04])
    c = base * (0.52 + 0.80 * ndl) + base * rim * 2.2
    c += E * fresnel(0.05, ndv) * 0.9 + 1.6 * ndh ** 110
    out = np.where(m == M_YEL, c, out)
    # ink lacquer
    base = np.array([0.012, 0.010, 0.05])
    c = base * (0.35 + 0.9 * ndl) + E * fresnel(0.04, ndv) * 0.75 + 1.4 * ndh ** 90
    c += np.array([0.0, 0.25, 0.45]) * (1 - ndv) ** 3 * 0.35
    out = np.where(m == M_INK, c, out)
    # brushed steel
    f = fresnel(np.array([0.62, 0.64, 0.68]), ndv)
    c = E * f * 0.95 + 0.08 * ndl + 2.0 * ndh ** 140
    out = np.where(m == M_STEEL, c, out)
    # zinc-yellow plated steel (construction-grade fasteners)
    f = fresnel(np.array([1.0, 0.76, 0.22]), ndv)
    c = E * f * 0.95 + np.array([1.0, 0.75, 0.2]) * 0.14 * ndl + 2.2 * ndh ** 120
    c = c * np.array([1.05, 0.96, 0.80])
    out = np.where(m == M_ZINC, c, out)
    # Dezly azure lacquer
    base = np.array([0.0, 0.42, 0.85])
    c = base * (0.30 + 0.85 * ndl) + base * rim * 2 + E * fresnel(0.04, ndv) * 0.85 + 1.8 * ndh ** 160
    c += np.array([0.3, 0.8, 1.0]) * (1 - ndv) ** 2.5 * 0.35
    out = np.where(m == M_BLUE, c, out)
    # white reflective band
    base = np.array([0.92, 0.93, 0.95])
    c = base * (0.30 + 0.80 * ndl) + E * fresnel(0.05, ndv) * 0.6 + 1.2 * ndh ** 80
    out = np.where(m == M_WHITE, c, out)
    # frosted azure glass
    fr = fresnel(0.06, ndv)
    tint = np.array([0.35, 0.80, 1.0])
    c = tint * (0.22 + 0.35 * ndl) + E * fr * 1.6 + 2.6 * ndh ** 260 + np.array([0.2, 0.75, 1.0]) * (1 - ndv) ** 1.6 * 1.1
    out = np.where(m == M_GLASS, c, out)
    alpha = np.where(mat == M_GLASS, np.clip(0.26 + 0.6 * fr[..., 0] + 0.6 * (1 - ndv[..., 0]) ** 2, 0, 1), alpha)

    out = out * (0.55 + 0.45 * ao[..., None])
    out = 1 - np.exp(-1.75 * out)
    return out, alpha

# ---------------------------------------------------------------- render
def render(name):
    fn, pose, scale = SHAPES[name]
    R = rot(*pose); Ri = R.T
    W = SIZE * SS
    ys, xs = np.mgrid[0:W, 0:W]
    u = (xs + 0.5) / W * 2 - 1; v = 1 - (ys + 0.5) / W * 2
    ro = np.array([0, 0, 5.0])
    rd = norm(np.stack([u * 0.33 * 1.0, v * 0.33, -np.ones_like(u)], -1)).reshape(-1, 3)
    n = rd.shape[0]

    def f(P):
        q = (P @ R) / scale         # world -> object (P @ R == R^T applied)
        d, m = fn(q)
        return d * scale, m

    t = np.full(n, 2.5); hit = np.zeros(n, bool); alive = np.ones(n, bool)
    for _ in range(260):
        idx = np.nonzero(alive)[0]
        if idx.size == 0: break
        P = ro + rd[idx] * t[idx, None]
        d, _ = f(P)
        h = d < 0.0008
        hit[idx[h]] = True
        t[idx] += d * 0.75
        dead = h | (t[idx] > 7.5)
        alive[idx[dead]] = False

    img = np.zeros((n, 4))
    idx = np.nonzero(hit)[0]
    P = ro + rd[idx] * t[idx, None]
    e = 0.0015
    ks = np.array([[1, -1, -1], [-1, -1, 1], [-1, 1, -1], [1, 1, 1]], float)
    N = sum(k * f(P + k * e)[0][:, None] for k in ks)
    N = norm(N)
    _, mat = f(P)
    ao = np.ones(idx.size); s = 1.0
    for i in range(1, 6):
        h = 0.06 * i
        ao -= (h - f(P + N * h)[0]) * s * 2.4; s *= 0.5
    ao = np.clip(ao, 0.25, 1)
    col, a = shade(P, N, -rd[idx], mat, ao)
    img[idx, :3] = np.clip(col, 0, 1) * a[:, None]      # premultiplied
    img[idx, 3] = a
    img = img.reshape(W, W, 4)
    img = img.reshape(SIZE, SS, SIZE, SS, 4).mean((1, 3))  # premultiplied downsample
    rgb = np.where(img[..., 3:] > 1e-4, img[..., :3] / np.maximum(img[..., 3:], 1e-4), 0)
    out = np.dstack([rgb, img[..., 3]])
    im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), 'RGBA')
    bbox = im.getchannel('A').point(lambda v: 255 if v > 3 else 0).getbbox()
    im = im.crop(bbox)
    side = int(max(im.size) * 1.14)
    sq = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - im.size[0]) // 2, (side - im.size[1]) // 2))
    sq = sq.resize((400, 400), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f'obj-{name}.webp')
    sq.save(path, 'WEBP', quality=90, method=6)
    print('wrote', path)

if __name__ == '__main__':
    names = sys.argv[1:] or list(SHAPES)
    for nm in names:
        render(nm)
