/* Dezly Contractors · interactions and motion */
(() => {
  const html = document.documentElement;
  html.classList.add('js');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const touch = matchMedia('(hover: none)').matches;
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];

  /* ---------- Loader: full on first visit, brief after ---------- */
  const loader = $('.loader');
  let seen = false;
  try { seen = sessionStorage.getItem('dz-seen') === '1'; sessionStorage.setItem('dz-seen', '1'); } catch (e) { /* storage unavailable */ }
  const minTime = reduce ? 0 : (seen ? 300 : 1500);
  const t0 = performance.now();
  let done = false;
  const finish = () => {
    if (done) return; done = true;
    setTimeout(() => {
      if (loader) loader.classList.add('is-done');
      html.classList.add('is-loaded');
      setTimeout(() => $$('.hero [data-split], .phero [data-split]').forEach(el => el.classList.add('is-in')), 200);
    }, Math.max(0, minTime - (performance.now() - t0)));
  };
  if (document.readyState === 'complete') finish(); else addEventListener('load', finish);
  setTimeout(finish, 3500);

  /* ---------- Split headings into lines; .d and .m copies split separately ---------- */
  const splitOne = (el) => {
    const parts = el.innerHTML.split(/<br\s*\/?>/i);
    el.innerHTML = parts.map((p, i) => `<span class="line" style="--i:${i}"><span>${p.trim()}</span></span>`).join('');
  };
  $$('[data-split]').forEach(el => {
    const kids = $$(':scope > .d, :scope > .m', el);
    if (kids.length) kids.forEach(splitOne); else splitOne(el);
  });

  /* ---------- Auto stagger siblings (85ms) ---------- */
  const groups = new Map();
  $$('[data-reveal]').forEach(el => {
    if (el.style.getPropertyValue('--d')) return;
    const p = el.parentElement;
    const n = groups.get(p) || 0;
    el.style.setProperty('--d', `${Math.min(n, 6) * 85}ms`);
    groups.set(p, n + 1);
  });

  /* ---------- SVG draw lengths ---------- */
  $$('.draw').forEach(svg => {
    $$('path, line, circle, rect', svg).forEach((el, k) => {
      if (el.classList.contains('solid')) return;
      let len = 400;
      try { len = Math.ceil(el.getTotalLength()); } catch (e) { /* not measurable */ }
      el.style.setProperty('--len', len); el.style.setProperty('--k', k);
    });
  });

  /* ---------- Reveal: observer + sweep for fast scrolls ---------- */
  const reveal = (el) => {
    if (el.classList.contains('is-in')) return;
    el.classList.add('is-in');
    if (el.matches('[data-count]')) count(el);
    if (el.matches('.donut')) donut(el);
  };
  const targets = $$('[data-reveal], [data-split], .io, [data-count], .donut').filter(el => !el.closest('.hero, .phero') || !el.matches('[data-split]'));
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } }), { threshold: .15, rootMargin: '0px 0px -6% 0px' });
  targets.forEach(el => io.observe(el));
  let sweepT;
  const sweep = () => { clearTimeout(sweepT); sweepT = setTimeout(() => { const vh = innerHeight; targets.forEach(el => { if (!el.classList.contains('is-in') && el.getBoundingClientRect().top < vh * .94) reveal(el); }); }, 120); };
  addEventListener('scroll', sweep, { passive: true });

  function count(el) {
    const raw = el.dataset.count, end = parseFloat(raw), dec = (raw.split('.')[1] || '').length, suf = el.dataset.suffix || '';
    if (reduce) { el.textContent = end.toFixed(dec) + suf; return; }
    const s = performance.now();
    const tick = (t) => { const p = Math.min(1, (t - s) / 1600); el.textContent = (end * (1 - Math.pow(1 - p, 4))).toFixed(dec) + suf; if (p < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }
  function donut(el) {
    const C = 2 * Math.PI * 54; let off = 0;
    $$('circle.seg', el).forEach(s => {
      const v = parseFloat(s.dataset.v) / 100 * C;
      s.style.strokeDashoffset = -off;
      requestAnimationFrame(() => { s.style.strokeDasharray = `${Math.max(0, v - 3)} ${C}`; });
      off += v;
    });
  }

  /* ---------- Header ---------- */
  const header = $('.header');
  let lastY = scrollY;
  const onScroll = () => {
    const y = scrollY;
    header.classList.toggle('is-solid', y > 24);
    header.classList.toggle('is-hidden', y > 480 && y > lastY && !html.classList.contains('menu-open'));
    lastY = y;
  };
  addEventListener('scroll', onScroll, { passive: true }); onScroll();

  /* ---------- Mobile menu: opens, locks scroll, closes ---------- */
  const burger = $('.burger');
  const setMenu = (open) => {
    html.classList.toggle('menu-open', open);
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  };
  burger.addEventListener('click', () => setMenu(!html.classList.contains('menu-open')));
  $$('.drawer a').forEach(a => a.addEventListener('click', () => setMenu(false)));
  addEventListener('keydown', e => { if (e.key === 'Escape') setMenu(false); });
  matchMedia('(min-width: 901px)').addEventListener('change', e => { if (e.matches) setMenu(false); });

  /* ---------- Hero slideshow ---------- */
  const slides = $$('.slides img');
  if (slides.length > 1) {
    const dots = $$('.dots button'), bar = $('.counter .track i'), cur = $('.counter b');
    let i = 0, timer;
    const go = (n) => {
      slides[i].classList.remove('is-on'); dots[i] && dots[i].classList.remove('is-on');
      i = (n + slides.length) % slides.length;
      slides[i].classList.add('is-on'); dots[i] && dots[i].classList.add('is-on');
      if (cur) cur.textContent = String(i + 1).padStart(2, '0');
      if (bar) { bar.classList.remove('run'); void bar.offsetWidth; bar.classList.add('run'); }
      clearTimeout(timer); if (!reduce) timer = setTimeout(() => go(i + 1), 6000);
    };
    dots.forEach((d, k) => d.addEventListener('click', () => go(k)));
    go(0);
  }

  /* ---------- Offer plates: one active ---------- */
  const offers = $$('.offers .pw');
  const activate = (c) => { offers.forEach(x => x.classList.toggle('is-active', x === c)); };
  if (!touch) offers.forEach(c => { c.addEventListener('mouseenter', () => activate(c)); c.addEventListener('focusin', () => activate(c)); });

  /* ---------- Touch: hover becomes "in view at the vertical centre" ---------- */
  if (touch) {
    const hoverables = $$('.pw, .tile, .mcard, .media, .info-card').filter(el => !el.closest('.offers'));
    const band = () => {
      const vh = innerHeight, top = vh * .36, bot = vh * .64;
      hoverables.forEach(el => { const r = el.getBoundingClientRect(), c = r.top + r.height / 2; el.classList.toggle('is-hover', c > top && c < bot); });
      if (offers.length) {
        let best = null, bd = Infinity;
        offers.forEach(o => { const r = o.getBoundingClientRect(), d = Math.abs(r.top + r.height / 2 - vh / 2); if (d < bd) { bd = d; best = o; } });
        if (best && bd < vh * .3) activate(best);
      }
    };
    let raf = 0;
    addEventListener('scroll', () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; band(); }); }, { passive: true });
    band();
  }

  /* ---------- Parallax (transform only) ---------- */
  const px = $$('[data-parallax]');
  if (px.length && !reduce) {
    let tk = false;
    const run = () => {
      const vh = innerHeight;
      px.forEach(el => { const r = el.getBoundingClientRect(); if (r.bottom < -100 || r.top > vh + 100) return; const k = parseFloat(el.dataset.parallax) || .05; el.style.transform = `translate3d(0, ${(-(r.top + r.height / 2 - vh / 2) * k).toFixed(1)}px, 0) scale(1.08)`; });
      tk = false;
    };
    addEventListener('scroll', () => { if (!tk) { tk = true; requestAnimationFrame(run); } }, { passive: true }); run();
  }

  /* ---------- Pointer depth on floating objects ---------- */
  if (!reduce && !touch) {
    $$('[data-tilt]').forEach(zone => {
      const items = $$('[data-depth]', zone);
      zone.addEventListener('pointermove', e => {
        const r = zone.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
        items.forEach(it => { const d = parseFloat(it.dataset.depth); it.style.translate = `${(x * d).toFixed(1)}px ${(y * d).toFixed(1)}px`; });
      });
      zone.addEventListener('pointerleave', () => items.forEach(it => { it.style.translate = ''; }));
    });
  }

  /* ---------- Map ---------- */
  $$('.map-stage').forEach(stage => {
    const pins = $$('.pin', stage), card = $('.map-card', stage);
    pins.forEach((p, k) => { p.style.left = p.dataset.x + '%'; p.style.top = p.dataset.y + '%'; p.style.setProperty('--i', k); });
    if (!card) return;
    const img = $('.map-card__img img', card), tag = $('.tag', card), ttl = $('.t-h4', card), loc = $('.t-small', card), val = $('.row b', card);
    const real = pins.filter(p => p.dataset.title);
    let active = real[0];
    const place = () => {
      if (!active) return;
      const w = stage.clientWidth, h = stage.clientHeight, cw = card.offsetWidth;
      const x = Math.min(Math.max(parseFloat(active.dataset.x) / 100 * w, cw / 2 + 4), w - cw / 2 - 4);
      const yPct = parseFloat(active.dataset.y);
      card.style.setProperty('--x', x + 'px'); card.style.setProperty('--y', (yPct / 100 * h) + 'px');
      card.classList.toggle('below', yPct < 48);
    };
    const show = (p) => {
      if (!p || !p.dataset.title) return;
      active = p; pins.forEach(x => x.classList.toggle('is-active', x === p));
      const pre = new Image(); pre.src = p.dataset.img;
      img.style.opacity = 0;
      const swap = () => { img.src = p.dataset.img; img.style.opacity = 1; };
      pre.decode ? pre.decode().then(swap, swap) : setTimeout(swap, 200);
      tag.textContent = p.dataset.tag; ttl.textContent = p.dataset.title; loc.textContent = p.dataset.loc; if (val) val.textContent = p.dataset.val;
      place();
    };
    let k = 0, auto = setInterval(() => { if (!reduce && stage.getBoundingClientRect().top < innerHeight) { k = (k + 1) % real.length; show(real[k]); } }, 4200);
    pins.forEach(p => { const h = () => { clearInterval(auto); show(p); }; p.addEventListener('mouseenter', h); p.addEventListener('click', h); p.addEventListener('focus', h); });
    addEventListener('resize', place);
    show(real[0]);
    const form = $('.searchbar');
    if (form) form.addEventListener('submit', e => {
      e.preventDefault();
      const sec = form.sector.value, reg = form.region.value;
      const m = real.find(p => (sec === 'all' || p.dataset.sector === sec) && (reg === 'all' || p.dataset.region === reg));
      clearInterval(auto); if (m) show(m);
    });
  });

  /* ---------- Project filter ---------- */
  $$('.filters').forEach(f => {
    const btns = $$('button', f), cards = $$('.pgrid > .pw');
    btns.forEach(b => b.addEventListener('click', () => {
      btns.forEach(x => { x.classList.toggle('is-on', x === b); x.setAttribute('aria-pressed', String(x === b)); });
      cards.forEach(c => c.classList.toggle('is-hidden', b.dataset.f !== 'all' && !c.dataset.cat.split(' ').includes(b.dataset.f)));
    }));
  });

  /* ---------- Quote form: compose an email ---------- */
  const form = $('#quote');
  if (form) form.addEventListener('submit', e => {
    e.preventDefault();
    const d = new FormData(form);
    const body = [...d.entries()].map(([k, v]) => `${k}: ${v}`).join('\n');
    $('.form-note', form).classList.add('is-on');
    location.href = `mailto:${form.dataset.to}?subject=${encodeURIComponent('Project enquiry from ' + (d.get('Name') || 'the website'))}&body=${encodeURIComponent(body)}`;
  });

  $$('[data-year]').forEach(el => { el.textContent = new Date().getFullYear(); });
})();
