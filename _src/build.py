"""Static build for the Dezly Contractors site.

    python _src/build.py

Reads _src/pages/*.html (with a front-matter comment), wraps each in the shared
head / header / footer partials, expands {{icon:name}} tokens and writes the
result to the project root.
"""
import json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, '_src')

ICON_DIR = os.path.join(SRC, 'icons')
_icon_cache = {}


def phosphor(name, weight='regular'):
    """Inline a Phosphor SVG (MIT licence) with a .ph class."""
    key = (name, weight)
    if key not in _icon_cache:
        path = os.path.join(ICON_DIR, f'{weight}-{name}.svg')
        with open(path, encoding='utf-8') as f:
            svg = f.read().strip()
        _icon_cache[key] = svg.replace('<svg ', '<svg class="ph" aria-hidden="true" focusable="false" ', 1)
    return _icon_cache[key]


# Industry patterns for the card mosaic (stroke = currentColor)
PATTERNS = {
    'contour': '<svg class="pattern" aria-hidden="true" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M300 150c0-60-60-90-120-80S80 140 120 190s150 40 180-40z"/><path d="M340 150c0-90-90-130-170-115S40 140 90 215s210 60 250-65z"/><path d="M380 150c0-120-120-170-220-150S0 140 60 240s270 80 320-90z"/><path d="M262 150c-4-30-40-48-80-44s-62 40-40 66 116 24 120-22z"/><path d="M226 148c-4-14-24-22-44-20s-30 20-18 32 64 8 62-12z"/></svg>',
    'rebar': '<svg class="pattern" aria-hidden="true" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" fill="none" stroke="currentColor" stroke-width="3"><g transform="rotate(-18 200 150)"><path d="M-100 40h600M-100 90h600M-100 140h600M-100 190h600M-100 240h600M-100 290h600"/><path d="M20 -100v500M80 -100v500M140 -100v500M200 -100v500M260 -100v500M320 -100v500M380 -100v500"/></g></svg>',
    'tread': '<svg class="pattern" aria-hidden="true" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" fill="currentColor"><g transform="rotate(-24 200 150)">' + ''.join(f'<rect x="{x}" y="60" width="16" height="44" rx="3"/><rect x="{x}" y="196" width="16" height="44" rx="3"/>' for x in range(-120, 520, 34)) + '</g></svg>',
    'blueprint': '<svg class="pattern" aria-hidden="true" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M0 0h400M0 30h400M0 60h400M0 90h400M0 120h400M0 150h400M0 180h400M0 210h400M0 240h400M0 270h400M0 300h400M0 0v300M30 0v300M60 0v300M90 0v300M120 0v300M150 0v300M180 0v300M210 0v300M240 0v300M270 0v300M300 0v300M330 0v300M360 0v300M390 0v300" opacity=".45"/><path stroke-width="3" d="M190 250V120l80-60 80 60v130zM230 250v-60h40v60M190 120h160"/><circle cx="270" cy="110" r="12" stroke-width="3"/></svg>',
    'waves': '<svg class="pattern" aria-hidden="true" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" fill="none" stroke="currentColor" stroke-width="2.4">' + ''.join(f'<path d="M-20 {y}c40-22 80-22 120 0s80 22 120 0 80-22 120 0 80 22 120 0"/>' for y in range(20, 320, 26)) + '</svg>',
    'beams': '<svg class="pattern" aria-hidden="true" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" fill="none" stroke="currentColor" stroke-width="3"><path d="M200 0v300M300 0v300M100 0v300M40 40h360M40 140h360M40 240h360"/><path d="M100 40l100 100M200 40l100 100M300 40l100 100M100 140l100 100M200 140l100 100M300 140l100 100" stroke-width="2"/></svg>',
    'strata': '<svg class="pattern" aria-hidden="true" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M0 60c60 10 120-20 200-5s140 20 200 0"/><path d="M0 110c80 20 140-15 210 0s130 15 190-5"/><path d="M0 160c70-10 150 25 220 10s120-15 180 5"/><path d="M0 210c60 15 140-10 200 5s150 10 200-10"/><path d="M0 260c90-15 160 20 230 5s110-10 170 5"/></svg>',
}

NAV = [('index.html', 'Home'), ('about.html', 'About Us'), ('services.html', 'Services'), ('projects.html', 'Projects'), ('contact.html', 'Contact')]


def read(p):
    with open(os.path.join(SRC, p), encoding='utf-8') as f:
        return f.read()


# ---------- Map tokens (data from _src/tools/make_map.py) ----------
# Main trunk routes, drawn town to town
ROUTES = [['Harare', 'Chinhoyi', 'Kariba'], ['Harare', 'Kwekwe', 'Gweru', 'Bulawayo'], ['Harare', 'Marondera', 'Mutare'],
          ['Harare', 'Masvingo', 'Beitbridge'], ['Bulawayo', 'Hwange', 'Victoria Falls'], ['Gweru', 'Masvingo', 'Chiredzi'],
          ['Harare', 'Bindura']]
LABELLED = ['Harare', 'Bulawayo', 'Mutare', 'Gweru', 'Masvingo', 'Victoria Falls', 'Kariba', 'Beitbridge', 'Chiredzi', 'Hwange']


def map_tokens():
    m = json.loads(read('partials/zim-map.json'))
    t = m['towns']
    prov = ''.join(f'<path d="{p["d"]}"/>' for p in m['provinces'])
    plabels = ''.join(f'<text x="{p["x"]}" y="{p["y"]}">{p["short"]}</text>' for p in m['provinces'] if p['name'] not in ('Harare', 'Bulawayo'))
    roads = ''.join('<polyline points="' + ' '.join(f'{t[n]["x"]},{t[n]["y"]}' for n in r) + '"/>' for r in ROUTES)
    towns = ''.join(f'<rect x="{v["x"] - 2.5}" y="{v["y"] - 2.5}" width="5" height="5"/>' for v in t.values())
    tlabels = ''.join(f'<text x="{t[n]["x"] + 7}" y="{t[n]["y"] + 3.5}">{n}</text>' for n in LABELLED)
    tok = {'zim-vb': f'0 0 {m["w"]} {m["h"]}', 'zim-ar': f'{m["w"]} / {m["h"]}', 'zim': m['country'], 'zim-prov': prov,
           'zim-plabels': plabels, 'zim-roads': roads, 'zim-towns': towns, 'zim-tlabels': tlabels, 'zim-credit': '<span class="d">' + m['credit'] + '</span><span class="m">Boundaries: geoBoundaries, CC BY 3.0 IGO</span>'}
    for n, v in t.items():
        tok[f'tx:{n}'], tok[f'ty:{n}'] = str(v['px']), str(v['py'])
        tok[f'sx:{n}'], tok[f'sy:{n}'] = str(v['x']), str(v['y'])
    return tok


def build():
    head, header, footer = read('partials/head.html'), read('partials/header.html'), read('partials/footer.html')
    mt = map_tokens()
    for name in sorted(os.listdir(os.path.join(SRC, 'pages'))):
        if not name.endswith('.html'):
            continue
        src = read('pages/' + name)
        m = re.match(r'\s*<!--(.*?)-->', src, re.S)
        meta = dict(re.findall(r'^\s*(\w+):\s*(.+?)\s*$', m.group(1), re.M)) if m else {}
        body = src[m.end():] if m else src
        nav = '\n'.join(f'        <a href="{"./" if h == "index.html" else h}"{" aria-current=\"page\"" if h == name else ""}>{t}</a>' for h, t in NAV)
        drawer = '\n'.join(f'    <a class="dl" href="{"./" if h == "index.html" else h}">{t}<span>0{i + 1}</span></a>' for i, (h, t) in enumerate(NAV))
        hdr = header.replace('{{nav}}', nav).replace('{{drawer}}', drawer)
        out = (head.replace('{{title}}', meta.get('title', 'Dezly Contractors'))
                   .replace('{{desc}}', meta.get('desc', ''))
                   .replace('{{page}}', name[:-5])
               + hdr + body + footer)
        out = re.sub(r'\{\{((?:zim[\w-]*)|(?:[ts][xy]:[\w ]+))\}\}', lambda k: mt[k.group(1)], out)
        out = re.sub(r'\{\{ph:([\w-]+)(?::(\w+))?\}\}', lambda k: phosphor(k.group(1), k.group(2) or 'regular'), out)
        out = re.sub(r'\{\{pattern:([\w-]+)\}\}', lambda k: PATTERNS[k.group(1)], out)
        with open(os.path.join(ROOT, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(out)
        print('built', name, len(out) // 1024, 'KB')


if __name__ == '__main__':
    build()
