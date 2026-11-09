"""Static build for the Dezly Contractors site.

    python _src/build.py

Reads _src/pages/*.html (with a front-matter comment), wraps each in the shared
head / header / footer partials, expands {{icon:name}} tokens and writes the
result to the project root.
"""
import os, re

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


def build():
    head, header, footer = read('partials/head.html'), read('partials/header.html'), read('partials/footer.html')
    zim = read('partials/zim-path.txt').strip()
    for name in sorted(os.listdir(os.path.join(SRC, 'pages'))):
        if not name.endswith('.html'):
            continue
        src = read('pages/' + name)
        m = re.match(r'\s*<!--(.*?)-->', src, re.S)
        meta = dict(re.findall(r'^\s*(\w+):\s*(.+?)\s*$', m.group(1), re.M)) if m else {}
        body = src[m.end():] if m else src
        nav = '\n'.join(f'        <a href="{h}"{" aria-current=\"page\"" if h == name else ""}>{t}</a>' for h, t in NAV)
        drawer = '\n'.join(f'    <a class="dl" href="{h}">{t}<span>0{i + 1}</span></a>' for i, (h, t) in enumerate(NAV))
        hdr = header.replace('{{nav}}', nav).replace('{{drawer}}', drawer)
        out = (head.replace('{{title}}', meta.get('title', 'Dezly Contractors'))
                   .replace('{{desc}}', meta.get('desc', ''))
                   .replace('{{page}}', name[:-5])
               + hdr + body + footer)
        out = out.replace('{{zim}}', zim)
        out = re.sub(r'\{\{ph:([\w-]+)(?::(\w+))?\}\}', lambda k: phosphor(k.group(1), k.group(2) or 'regular'), out)
        out = re.sub(r'\{\{pattern:([\w-]+)\}\}', lambda k: PATTERNS[k.group(1)], out)
        with open(os.path.join(ROOT, name), 'w', encoding='utf-8', newline='\n') as f:
            f.write(out)
        print('built', name, len(out) // 1024, 'KB')


if __name__ == '__main__':
    build()
