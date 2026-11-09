"""QA checklist runner for the Dezly site.

    python _src/tools/qa.py [page.html ...]

Proves (rather than assumes):
  - zero console errors and zero failed requests per page
  - no horizontal overflow at 1280 and 390
  - hero fits one screen at six viewport sizes
  - no small text that is one line on desktop and two or more on mobile
  - no paragraph over four lines at 390
  - zero em/en dashes and banned words in the built HTML
  - every internal link, asset and CSS url() resolves
  - images not stretched
  - page renders with JavaScript disabled
  - mobile menu opens, locks scroll and closes
"""
import os, re, sys, glob, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHROME = r'C:/Program Files/Google/Chrome/Application/chrome.exe'
PAGES = sys.argv[1:] or sorted(p.name for p in ROOT.glob('*.html'))
BANNED = ['seamless', 'robust', 'leverage', 'elevate', 'unlock', 'bespoke', 'cutting edge', 'cutting-edge',
          'comprehensive', 'tailored', 'holistic', 'not just', 'world-class', 'state-of-the-art', 'synergy']
HERO_SIZES = [(1440, 900), (1366, 768), (1280, 720), (1280, 640), (1440, 1080), (390, 844)]
fails = []

def fail(msg):
    fails.append(msg); print('  FAIL', msg)

LINES_JS = r"""
() => {
  const sel = 'p, li, a.btn, button.btn, .t-h3, .t-h4, .t-label, .t-small, .tile__t, .pill, .chip, .stat b, .filters button, .choice label, .legend div, .gantt__row > span, .map-card .t-h4';
  const heading = el => el.matches('.t-h1, .t-h2, .quote, .big-copy');
  const out = [];
  document.querySelectorAll(sel).forEach((el, i) => {
    if (heading(el) || el.closest('.marquee, .loader, .drawer, svg')) return;
    const cs = getComputedStyle(el);
    if (el.offsetParent === null && cs.position !== 'fixed') return;
    const r = document.createRange(); r.selectNodeContents(el);
    const tops = [];
    [...r.getClientRects()].forEach(q => { if (q.width < 1 || q.height < 1) return; const t = Math.round(q.top + q.height / 2); if (!tops.some(x => Math.abs(x - t) < q.height * .5)) tops.push(t); });
    const txt = el.textContent.replace(/\s+/g, ' ').trim();
    if (!txt) return;
    out.push({ i, lines: tops.length, tag: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''), txt: txt.slice(0, 70), para: el.tagName === 'P' });
  });
  return out;
}
"""

def static_checks():
    print('== static')
    for name in PAGES:
        html = (ROOT / name).read_text(encoding='utf-8')
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S)
        if '\u2014' in text or '\u2013' in text or '&mdash;' in text or '&ndash;' in text:
            fail(f'{name}: em/en dash present')
        low = re.sub(r'<[^>]+>', ' ', text).lower()
        for w in BANNED:
            if w in low: fail(f'{name}: banned phrase "{w}"')
        for ref in re.findall(r'(?:href|src)="([^"#]+)', html):
            if re.match(r'(https?:|mailto:|tel:|data:)', ref): continue
            if not (ROOT / ref).exists(): fail(f'{name}: missing {ref}')
    css = (ROOT / 'assets/css/style.css').read_text(encoding='utf-8')
    for u in re.findall(r"url\('?([^')\"]+)'?\)", css):
        if u.startswith('data:') or u.startswith('#'): continue
        if not (ROOT / 'assets/css' / u).resolve().exists(): fail(f'css url missing {u}')

def main():
    static_checks()
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME)
        for name in PAGES:
            url = 'http://127.0.0.1:5500/' + name
            print('==', name)
            res = {}
            for (w, h) in [(1440, 900), (390, 844)]:
                pg = b.new_page(viewport={'width': w, 'height': h})
                errs = []
                pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
                pg.on('pageerror', lambda e: errs.append(str(e)))
                pg.on('requestfailed', lambda r: errs.append('reqfail ' + r.url))
                pg.on('response', lambda r: r.status >= 400 and errs.append(f'{r.status} {r.url}'))
                pg.goto(url, wait_until='networkidle')
                pg.wait_for_timeout(400)
                for e in errs: fail(f'{name}@{w}: {e}')
                ov = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
                if ov > 0: fail(f'{name}@{w}: horizontal overflow {ov}px')
                res[w] = {d['i']: d for d in pg.evaluate(LINES_JS)}
                # stretched images
                bad = pg.evaluate("""() => [...document.images].filter(i => i.offsetParent && i.naturalWidth && !['cover','contain'].includes(getComputedStyle(i).objectFit)).filter(i => { const r = i.getBoundingClientRect(); return r.width > 4 && Math.abs(r.width / r.height - i.naturalWidth / i.naturalHeight) > .02; }).map(i => i.src.split('/').pop())""")
                for x in bad: fail(f'{name}@{w}: stretched image {x}')
                if w == 390:
                    pg.click('.burger'); pg.wait_for_timeout(800)
                    st = pg.evaluate("() => ({open: document.documentElement.classList.contains('menu-open'), lock: getComputedStyle(document.body).overflow, vis: getComputedStyle(document.querySelector('.drawer')).visibility})")
                    if not (st['open'] and st['lock'] == 'hidden' and st['vis'] == 'visible'): fail(f'{name}: mobile menu did not open/lock {st}')
                    pg.click('.burger'); pg.wait_for_timeout(800)
                    if pg.evaluate("document.documentElement.classList.contains('menu-open')"): fail(f'{name}: mobile menu did not close')
                pg.close()
            d, m = res[1440], res[390]
            for i, md in m.items():
                if i in d and d[i]['lines'] == 1 and md['lines'] >= 2:
                    fail(f'{name}: 1 line desktop -> {md["lines"]} mobile  [{md["tag"]}] "{md["txt"]}"')
                if md['para'] and md['lines'] > 4:
                    fail(f'{name}: {md["lines"]} lines at 390  [{md["tag"]}] "{md["txt"]}"')
            for i, dd in d.items():
                if dd['para'] and dd['lines'] > 4:
                    fail(f'{name}: {dd["lines"]} lines at 1440  [{dd["tag"]}] "{dd["txt"]}"')
            # hero fit
            for (w, h) in HERO_SIZES:
                pg = b.new_page(viewport={'width': w, 'height': h})
                pg.goto(url, wait_until='networkidle'); pg.wait_for_timeout(2600)
                r = pg.evaluate("""() => { const f = document.querySelector('.hero .frame, .phero .frame'); if (!f) return null;
                  const fr = f.getBoundingClientRect(); const kids = [...f.querySelectorAll('.hero__body > *, .gcard, .counter, .phero__in > div > *')].filter(k => k.offsetParent);
                  const maxB = Math.max(...kids.map(k => k.getBoundingClientRect().bottom));
                  const body = f.querySelector('.hero__body'), card = f.querySelector('.hero__foot .container');
                  const overlap = body && card ? body.getBoundingClientRect().bottom - card.getBoundingClientRect().top : -999;
                  return { frameBottom: fr.bottom, maxB, ih: innerHeight, overlap }; }""")
                if r is None: continue
                if r['frameBottom'] > r['ih'] + 1 and r['ih'] >= 560: fail(f'{name}@{w}x{h}: hero frame bottom {r["frameBottom"]:.0f} > {r["ih"]}')
                if r['maxB'] > min(r['frameBottom'], r['ih']) + 1: fail(f'{name}@{w}x{h}: hero content spills ({r["maxB"]:.0f})')
                if r['overlap'] > -8: fail(f'{name}@{w}x{h}: hero copy collides with footer card ({r["overlap"]:.0f}px)')
                pg.close()
            # no JS
            ctx = b.new_context(java_script_enabled=False, viewport={'width': 1280, 'height': 800})
            pg = ctx.new_page(); pg.goto(url, wait_until='networkidle')
            hidden = pg.evaluate("""() => [...document.querySelectorAll('[data-reveal], h1, h2')].filter(e => getComputedStyle(e).opacity === '0').length""")
            if hidden: fail(f'{name}: {hidden} elements hidden with JS off')
            heroimg = pg.evaluate("""() => { const i = document.querySelector('.slides img, .phero .frame > img'); return i ? getComputedStyle(i).opacity : '1'; }""")
            if heroimg == '0': fail(f'{name}: hero image invisible with JS off')
            ctx.close()
        b.close()
    print('\nRESULT:', 'PASS' if not fails else f'{len(fails)} failure(s)')

if __name__ == '__main__':
    main()
