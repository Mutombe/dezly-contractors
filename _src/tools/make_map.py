"""Project Zimbabwe's boundaries into SVG space for the site maps.

    python _src/tools/make_map.py

Source: geoBoundaries gbOpen ZWE ADM0 and ADM1 (simplified), from ZIMSTAT and
OCHA ROSEA, licensed CC BY 3.0 IGO. The credit is printed under each map.

Writes _src/partials/zim-map.json with the viewBox, the national outline, the
province outlines with label anchors, and town positions (percent of the box).
"""
import json, math, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA = os.path.join(ROOT, '_src', 'data')
OUT = os.path.join(ROOT, '_src', 'partials', 'zim-map.json')

W = 600            # viewBox width; height follows the projection
LAT0 = -19.0       # standard parallel for the equirectangular projection
TOL = 0.45         # Douglas-Peucker tolerance, in viewBox units

TOWNS = {          # lat, lon (decimal degrees)
    'Harare': (-17.8292, 31.0522), 'Bulawayo': (-20.1500, 28.5833), 'Gweru': (-19.4500, 29.8167),
    'Mutare': (-18.9707, 32.6709), 'Masvingo': (-20.0637, 30.8277), 'Chiredzi': (-21.0500, 31.6667),
    'Kariba': (-16.5167, 28.8000), 'Hwange': (-18.3667, 26.5000), 'Victoria Falls': (-17.9318, 25.8307),
    'Kwekwe': (-18.9281, 29.8149), 'Chinhoyi': (-17.3667, 30.2000), 'Beitbridge': (-22.2167, 30.0000),
    'Bindura': (-17.3019, 31.3306), 'Marondera': (-18.1853, 31.5519),
}
SHORT = {'Mashonaland Central': 'Mash. Central', 'Mashonaland East': 'Mash. East', 'Mashonaland West': 'Mash. West',
         'Matabeleland North': 'Mat. North', 'Matabeleland South': 'Mat. South'}


def rings(geom):
    polys = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
    return [poly[0] for poly in polys]  # outer rings only


def load(name):
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        return json.load(f)['features']


adm0, adm1 = load('zwe-adm0.geojson'), load('zwe-adm1.geojson')
k = math.cos(math.radians(LAT0))
allpts = [p for f in adm0 for r in rings(f['geometry']) for p in r]
minx, maxx = min(p[0] for p in allpts) * k, max(p[0] for p in allpts) * k
miny, maxy = min(-p[1] for p in allpts), max(-p[1] for p in allpts)
S = W / (maxx - minx)
H = round((maxy - miny) * S)


def proj(lon, lat):
    return ((lon * k - minx) * S, (-lat - miny) * S)


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1e-9
    i, dmax = 0, -1
    for j in range(1, len(pts) - 1):
        d = abs(dy * pts[j][0] - dx * pts[j][1] + x2 * y1 - y2 * x1) / L
        if d > dmax:
            i, dmax = j, d
    if dmax <= tol:
        return [pts[0], pts[-1]]
    return dp(pts[:i + 1], tol)[:-1] + dp(pts[i:], tol)


def path(ring):
    pts = [proj(*p) for p in ring]
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    # A closed ring has no baseline, so split it at the point farthest from its start
    far = max(range(len(pts)), key=lambda j: math.dist(pts[0], pts[j]))
    pts = dp(pts[:far + 1], TOL)[:-1] + dp(pts[far:] + [pts[0]], TOL)[:-1]
    return 'M' + 'L'.join(f'{x:.1f} {y:.1f}' for x, y in pts) + 'Z'


def label_anchor(ring):
    """Area-weighted centroid of the projected ring."""
    pts = [proj(*p) for p in ring]
    a = cx = cy = 0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        c = x0 * y1 - x1 * y0
        a += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    a *= .5
    return cx / (6 * a), cy / (6 * a)


country = ''.join(path(r) for f in adm0 for r in rings(f['geometry']))
provinces = []
for f in adm1:
    name = f['properties']['shapeName']
    rs = rings(f['geometry'])
    big = max(rs, key=len)
    cx, cy = label_anchor(big)
    provinces.append({'name': name, 'short': SHORT.get(name, name), 'd': ''.join(path(r) for r in rs),
                      'x': round(cx, 1), 'y': round(cy, 1)})
towns = {}
for name, (lat, lon) in TOWNS.items():
    x, y = proj(lon, lat)
    towns[name] = {'x': round(x, 1), 'y': round(y, 1), 'px': round(x / W * 100, 2), 'py': round(y / H * 100, 2)}

out = {'w': W, 'h': H, 'country': country, 'provinces': provinces, 'towns': towns,
       'credit': 'Boundaries: ZIMSTAT and OCHA ROSEA via geoBoundaries, CC BY 3.0 IGO'}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, separators=(',', ':'))
print(f'viewBox 0 0 {W} {H}; country {len(country)} chars; provinces {sum(len(p["d"]) for p in provinces)} chars')
for n, t in towns.items():
    print(f'  {n:15s} {t["px"]:6.2f}% {t["py"]:6.2f}%   ({t["x"]}, {t["y"]})')
