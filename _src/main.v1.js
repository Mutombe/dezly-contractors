/* Dezly Contractors — interactions & motion */
(() => {
  const html = document.documentElement;
  html.classList.remove('no-js');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];

  /* ---------- Preloader (full on first visit, quick after) ---------- */
  const loader = $('.loader');
  let seen = false;
  try { seen = sessionStorage.getItem('dz-seen') === '1'; sessionStorage.setItem('dz-seen', '1'); } catch (e) { /* storage blocked */ }
  const minTime = reduce ? 0 : (seen ? 350 : 1550);
  const start = performance.now();
  const finish = () => {
    const wait = Math.max(0, minTime - (performance.now() - start));
    setTimeout(() => {
      if (loader) loader.classList.add('is-done');
      html.classList.add('is-loaded');
      setTimeout(() => $$('.hero [data-split], .phero [data-split]').forEach(el => el.classList.add('is-in')), 250);
    }, wait);
  };
  if (document.readyState === 'complete') finish(); else window.addEventListener('load', finish);
  setTimeout(finish, 4000); // safety net

  /* ---------- Split headings into lines (by <br>) ---------- */
  $$('[data-split]').forEach(el => {
    const parts = el.innerHTML.split(/<br\s*\/?>/i);
    el.innerHTML = parts.map((p, i) => `<span class="line" style="--i:${i}"><span>${p.trim()}</span></span>`).join('');
  });

  /* ---------- SVG draw lengths ---------- */
  $$('.draw').forEach(svg => {
    $$('path, line, circle, rect, polyline', svg).forEach((el, k) => {
      if (el.classList.contains('solid')) return;
      let len = 400;
      try { len = Math.ceil(el.getTotalLength()); } catch (e) { /* not measurable */ }
      el.style.setProperty('--len', len);
      el.style.setProperty('--k', k);
    });
  });

  /* ---------- In-view observer ---------- */
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      const el = e.target;
      if (el.closest('.hero, .phero') && el.matches('[data-split]') && !html.classList.contains('is-loaded')) return;
      el.classList.add('is-in');
      if (el.matches('[data-count]')) count(el);
      if (el.matches('.donut')) donut(el);
      io.unobserve(el);
    });
  }, { threshold: 0.18, rootMargin: '0px 0px -6% 0px' });
  $$('[data-reveal], [data-split], .io, [data-count], .donut').forEach(el => io.observe(el));

  /* ---------- Counters ---------- */
  function count(el) {
    const end = parseFloat(el.dataset.count);
    const dec = (el.dataset.count.split('.')[1] || '').length;
    const pre = el.dataset.prefix || '', suf = el.dataset.suffix || '';
    if (reduce) { el.textContent = pre + end.toFixed(dec) + suf; return; }
    const dur = 1800, t0 = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / dur), v = end * (1 - Math.pow(1 - p, 4));
      el.textContent = pre + v.toFixed(dec) + suf;
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  /* ---------- Donut charts ---------- */
  function donut(el) {
    const segs = $$('circle.seg', el);
    const C = 2 * Math.PI * 54;
    let off = 0;
    segs.forEach(s => {
      const v = parseFloat(s.dataset.v) / 100 * C;
      s.style.strokeDashoffset = -off;
      requestAnimationFrame(() => { s.style.strokeDasharray = `${Math.max(0, v - 3)} ${C}`; });
      off += v;
    });
  }

  /* ---------- Header ---------- */
  const header = $('.header');
  let lastY = 0;
  const onScroll = () => {
    const y = window.scrollY;
    if (header) {
      header.classList.toggle('is-solid', y > 40);
      header.classList.toggle('is-hidden', y > 400 && y > lastY && !html.classList.contains('menu-open'));
    }
    lastY = y;
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- Mobile drawer ---------- */
  const burger = $('.burger');
  if (burger) {
    burger.addEventListener('click', () => {
      const open = html.classList.toggle('menu-open');
      burger.setAttribute('aria-expanded', open);
      document.body.style.overflow = open ? 'hidden' : '';
    });
    $$('.drawer a').forEach(a => a.addEventListener('click', () => { html.classList.remove('menu-open'); document.body.style.overflow = ''; }));
  }

  /* ---------- Hero slideshow ---------- */
  const slides = $$('.hero__slides img');
  if (slides.length) {
    const dots = $$('.hero__dots button');
    const bar = $('.hero__meta .track i');
    const cur = $('.hero__meta b');
    let i = 0, timer;
    const go = (n) => {
      slides[i].classList.remove('is-on'); dots[i] && dots[i].classList.remove('is-on');
      i = (n + slides.length) % slides.length;
      slides[i].classList.add('is-on'); dots[i] && dots[i].classList.add('is-on');
      if (cur) cur.textContent = String(i + 1).padStart(2, '0');
      if (bar) { bar.classList.remove('run'); void bar.offsetWidth; bar.classList.add('run'); }
      clearTimeout(timer);
      if (!reduce) timer = setTimeout(() => go(i + 1), 6000);
    };
    dots.forEach((d, k) => d.addEventListener('click', () => go(k)));
    go(0);
  }

  /* ---------- Offer cards: one active at a time ---------- */
  $$('.offer-grid').forEach(grid => {
    const cards = $$('.offer', grid);
    cards.forEach(c => {
      const on = () => { cards.forEach(x => x.classList.remove('is-active')); c.classList.add('is-active'); };
      c.addEventListener('mouseenter', on); c.addEventListener('focusin', on);
    });
  });

  /* ---------- Parallax ---------- */
  const px = $$('[data-parallax]');
  if (px.length && !reduce) {
    let ticking = false;
    const run = () => {
      const vh = window.innerHeight;
      px.forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.bottom < -100 || r.top > vh + 100) return;
        const k = parseFloat(el.dataset.parallax) || 0.1;
        const c = (r.top + r.height / 2 - vh / 2);
        el.style.transform = `translate3d(0, ${(-c * k).toFixed(1)}px, 0)`;
      });
      ticking = false;
    };
    window.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(run); } }, { passive: true });
    run();
  }

  /* ---------- Pointer tilt on floating objects ---------- */
  if (!reduce && window.matchMedia('(hover: hover)').matches) {
    $$('[data-tilt]').forEach(zone => {
      const items = $$('[data-depth]', zone);
      zone.addEventListener('pointermove', (e) => {
        const r = zone.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
        items.forEach(it => { const d = parseFloat(it.dataset.depth); it.style.translate = `${(x * d).toFixed(1)}px ${(y * d).toFixed(1)}px`; });
      });
      zone.addEventListener('pointerleave', () => items.forEach(it => { it.style.translate = ''; }));
    });
  }

  /* ---------- Touch: mirror hover as in-view on .way cards ---------- */
  if (window.matchMedia('(hover: none)').matches) {
    const ways = $$('.way');
    const check = () => {
      const vh = window.innerHeight, top = vh * .38, bot = vh * .62;
      ways.forEach(w => { const r = w.getBoundingClientRect(), c = r.top + r.height / 2; w.classList.toggle('is-inview', c > top && c < bot); });
    };
    window.addEventListener('scroll', check, { passive: true }); check();
  }

  /* ---------- Map: pins + floating card ---------- */
  $$('.map-stage').forEach(stage => {
    const pins = $$('.pin', stage);
    const card = $('.map-card', stage);
    if (!card) return;
    pins.forEach((p, k) => { p.style.left = p.dataset.x + '%'; p.style.top = p.dataset.y + '%'; p.style.setProperty('--i', k); });
    const img = $('.map-card__img img', card), tag = $('.map-card__img .tag', card);
    const ttl = $('h4', card), loc = $('.loc', card), sp = $$('.specs span em', card), val = $('.row b', card);
    const show = (p) => {
      if (!p || !p.dataset.title) return;
      pins.forEach(x => x.classList.remove('is-active')); p.classList.add('is-active');
      const cx = Math.min(Math.max(parseFloat(p.dataset.x), 16), 84), cy = parseFloat(p.dataset.y);
      card.style.left = cx + '%'; card.style.top = cy + '%';
      card.classList.toggle('below', cy < 48);
      img.style.opacity = 0;
      setTimeout(() => { img.src = p.dataset.img; img.alt = p.dataset.title; img.style.opacity = 1; }, 220);
      tag.textContent = p.dataset.tag; ttl.textContent = p.dataset.title; loc.textContent = p.dataset.loc;
      const s = (p.dataset.specs || '').split('|'); sp.forEach((e, k) => { e.textContent = s[k] || ''; });
      val.innerHTML = p.dataset.val;
    };
    const real = pins.filter(p => p.dataset.title);
    let k = 0, auto = setInterval(() => { if (!reduce) { k = (k + 1) % real.length; show(real[k]); } }, 4200);
    pins.forEach(p => {
      const h = () => { clearInterval(auto); show(p); };
      p.addEventListener('mouseenter', h); p.addEventListener('click', h); p.addEventListener('focus', h);
    });
    show(real[0]);
    // filters on searchbar
    const form = $('.searchbar');
    if (form) form.addEventListener('submit', (e) => {
      e.preventDefault();
      const sec = form.querySelector('[name=sector]').value;
      const reg = form.querySelector('[name=region]').value;
      const match = real.find(p => (sec === 'all' || p.dataset.sector === sec) && (reg === 'all' || p.dataset.region === reg));
      clearInterval(auto);
      if (match) show(match);
    });
  });

  /* ---------- Project filter ---------- */
  $$('.filters').forEach(f => {
    const btns = $$('button', f), cards = $$('.pcard');
    btns.forEach(b => b.addEventListener('click', () => {
      btns.forEach(x => { x.classList.remove('is-on'); x.setAttribute('aria-pressed', 'false'); });
      b.classList.add('is-on'); b.setAttribute('aria-pressed', 'true');
      const v = b.dataset.f;
      cards.forEach(c => c.classList.toggle('is-hidden', v !== 'all' && !c.dataset.cat.split(' ').includes(v)));
    }));
  });

  /* ---------- Contact form → compose email ---------- */
  const form = $('#quote');
  if (form) form.addEventListener('submit', (e) => {
    e.preventDefault();
    const d = new FormData(form);
    const body = [...d.entries()].map(([k, v]) => `${k}: ${v}`).join('\n');
    const to = form.dataset.to;
    $('.form-note', form).classList.add('is-on');
    window.location.href = `mailto:${to}?subject=${encodeURIComponent('Project enquiry — ' + (d.get('Name') || ''))}&body=${encodeURIComponent(body)}`;
  });

  /* ---------- Year ---------- */
  $$('[data-year]').forEach(el => { el.textContent = new Date().getFullYear(); });
})();
