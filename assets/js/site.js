/* Madarek site — page behaviour in one small file (no jQuery, no WordPress). */
(function () {
  'use strict';
  var d = document, de = d.documentElement, W = window;
  function $(s, r) { return (r || d).querySelector(s); }
  function $$(s, r) { return [].slice.call((r || d).querySelectorAll(s)); }
  function on(el, ev, fn, o) { if (el) el.addEventListener(ev, fn, o || false); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var reduce = W.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var finePointer = W.matchMedia && matchMedia('(hover: hover) and (pointer: fine)').matches;

  /* ---------- shared catalog (load more, sorting, search) ---------- */
  var catalogP = null;
  function catalog() {
    if (!catalogP) catalogP = fetch('/data/catalog.json', { credentials: 'same-origin' }).then(function (r) { return r.json(); });
    return catalogP;
  }
  function card(p) {
    return '<article class="m-card" data-id="' + p.i + '"><a class="m-card-media" href="' + esc(p.u) + '" tabindex="-1" aria-hidden="true"><img src="' + esc(p.t) + '" width="430" height="430" alt="' + esc(p.a) + '" loading="lazy" decoding="async">' +
      (p.t2 ? '<img class="m-card-alt" src="' + esc(p.t2) + '" width="430" height="430" alt="" loading="lazy" decoding="async">' : '') +
      '</a><div class="m-card-body"><p class="m-card-cat">' + esc(p.cn) + '</p><h3 class="m-card-title"><a href="' + esc(p.u) + '">' + esc(p.n) + '</a></h3><p class="m-card-price">' + (p.h || '') +
      (p.b ? '<span class="m-card-off">-' + p.b + '%</span>' : '') + '</p></div></article>';
  }
  function listFor(data, cat, orderby) {
    var set = null;
    if (cat && data.d[cat]) { set = {}; data.d[cat].forEach(function (i) { set[i] = 1; }); }
    var rows = data.p.map(function (p, i) { p._o = i; return p; }).filter(function (p) {
      if (!set) return true;
      for (var k = 0; k < p.c.length; k++) if (set[p.c[k]]) return true;
      return false;
    });
    return sortRows(rows, orderby);
  }
  function sortRows(rows, orderby) {
    var r = rows.slice();
    if (orderby === 'date') r.sort(function (a, b) { return a.d < b.d ? 1 : a.d > b.d ? -1 : b.i - a.i; });
    else if (orderby === 'price') r.sort(function (a, b) { return (a.p == null ? 1e12 : a.p) - (b.p == null ? 1e12 : b.p); });
    else if (orderby === 'price-desc') r.sort(function (a, b) { return (b.p == null ? -1 : b.p) - (a.p == null ? -1 : a.p); });
    else r.sort(function (a, b) { return a._o - b._o; });
    return r;
  }
  function arCount(n) {
    if (n === 0) return 'لا منتجات';
    if (n === 1) return 'منتج واحد';
    if (n === 2) return 'منتجان';
    var m = n % 100;
    if (m >= 3 && m <= 10) return n + ' منتجات';
    if (m >= 11) return n + ' منتجاً';
    return n + ' منتج';
  }
  function countText(total, shown) { return total <= shown ? arCount(total) : 'عرض ' + shown + ' من ' + arCount(total); }

  /* ---------- Arabic-aware search ---------- */
  function norm(s) {
    return String(s || '').toLowerCase()
      .replace(/[ً-ْـ]/g, '')
      .replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').replace(/ؤ/g, 'و').replace(/ئ/g, 'ي')
      .replace(/[٠-٩]/g, function (x) { return String(x.charCodeAt(0) - 0x0660); })
      .replace(/[×x]/g, 'x').replace(/[^؀-ۿa-z0-9x.]+/g, ' ').trim();
  }
  function search(data, q, cat) {
    var toks = norm(q).split(' ').filter(Boolean);
    if (!toks.length) return [];
    var set = null;
    if (cat && data.d[cat]) { set = {}; data.d[cat].forEach(function (i) { set[i] = 1; }); }
    var out = [];
    data.p.forEach(function (p, i) {
      if (set && !p.c.some(function (c) { return set[c]; })) return;
      if (!p._n) {
        p._n = norm(p.n); p._s = norm(p.s);
        p._c = norm(p.c.map(function (c) { return data.c[c] ? data.c[c][0] : ''; }).join(' '));
      }
      var hay = p._n + ' ' + p._s + ' ' + p._c, score = 0;
      for (var k = 0; k < toks.length; k++) {
        var t = toks[k];
        if (hay.indexOf(t) < 0) return;
        if (p._n.indexOf(t) === 0) score += 6; else if (p._n.indexOf(t) > 0) score += 3;
        if (p._s.indexOf(t) >= 0) score += 5;
        if (p._c.indexOf(t) >= 0) score += 1;
      }
      out.push({ p: p, s: score, i: i });
    });
    out.sort(function (a, b) { return b.s - a.s || a.i - b.i; });
    return out.map(function (x) { return x.p; });
  }
  function resultsHTML(r, q) {
    if (!r.length) return '<p class="m-res-empty">لا توجد نتائج لـ «' + esc(q) + '». جرّب كلمة أقصر أو كود المنتج.</p>';
    return r.slice(0, 8).map(function (p) {
      return '<a class="m-res" href="' + esc(p.u) + '"><img src="' + esc(p.t) + '" alt="" loading="lazy"><span class="m-res-t"><b>' + esc(p.n) + '</b><small>' + esc(p.cn) + '</small></span><span class="m-res-p">' + (p.h || '') + '</span></a>';
    }).join('') + (r.length > 8 ? '<a class="m-res-all" href="/search/?s=' + encodeURIComponent(q) + '">كل النتائج (' + r.length + ')</a>' : '');
  }
  function liveSearch(input, box, onShow) {
    var t = 0, idx = -1;
    on(input, 'input', function () {
      clearTimeout(t);
      t = setTimeout(function () {
        var q = input.value.trim(); idx = -1;
        if (q.length < 2) { box.innerHTML = ''; if (onShow) onShow(false); return; }
        catalog().then(function (data) { box.innerHTML = resultsHTML(search(data, q), q); if (onShow) onShow(true); });
      }, 120);
    });
    on(input, 'keydown', function (e) {
      var items = $$('a', box); if (!items.length) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        idx = (idx + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
        items.forEach(function (a, k) { a.classList.toggle('is-on', k === idx); });
        items[idx].scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter' && idx >= 0) { e.preventDefault(); location.href = items[idx].href; }
    });
    on(input, 'focus', catalog);
  }

  /* ---------- header: hide on scroll down, show on scroll up ---------- */
  (function () {
    var h = $('#hdr'); if (!h) return;
    var last = W.scrollY, ticking = false;
    function upd() {
      var y = W.scrollY, busy = de.classList.contains('mnav-open') || h.querySelector('.is-open') || h.contains(d.activeElement);
      h.classList.toggle('is-stuck', y > 8);
      if (y > 240 && y > last + 4 && !busy) h.classList.add('is-hidden');
      else if (y < last - 4 || y <= 240) h.classList.remove('is-hidden');
      last = y; ticking = false;
    }
    on(W, 'scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(upd); } }, { passive: true });
  })();

  /* ---------- mega menu ---------- */
  (function () {
    var li = $('[data-mega]'); if (!li) return;
    var link = $('.m-nav-link', li), mega = $('.m-mega', li), timer = 0;
    function set(open) { li.classList.toggle('is-open', open); link.setAttribute('aria-expanded', open ? 'true' : 'false'); }
    function show(i) {
      $$('.m-mega-cats a[data-i]', mega).forEach(function (a) { a.classList.toggle('is-on', a.getAttribute('data-i') === i); });
      $$('.m-mega-panel', mega).forEach(function (p) { p.hidden = p.getAttribute('data-i') !== i; });
    }
    if (finePointer) {
      on(li, 'mouseenter', function () { clearTimeout(timer); timer = setTimeout(function () { set(true); }, 90); });
      on(li, 'mouseleave', function () { clearTimeout(timer); timer = setTimeout(function () { set(false); }, 160); });
    }
    on(li, 'focusin', function () { set(true); });
    on(li, 'focusout', function (e) { if (!li.contains(e.relatedTarget)) set(false); });
    on(d, 'keydown', function (e) { if (e.key === 'Escape' && li.classList.contains('is-open')) { set(false); link.focus(); } });
    $$('.m-mega-cats a[data-i]', mega).forEach(function (a) {
      var t = 0;
      on(a, 'mouseenter', function () { clearTimeout(t); t = setTimeout(function () { show(a.getAttribute('data-i')); }, 60); });
      on(a, 'mouseleave', function () { clearTimeout(t); });
      on(a, 'focus', function () { show(a.getAttribute('data-i')); });
    });
  })();

  /* ---------- search: desktop dropdown + mobile sheet ---------- */
  (function () {
    var form = $('.m-search');
    if (form) {
      var input = $('input', form), pop = $('.m-search-pop', form);
      liveSearch(input, pop, function (show) { pop.hidden = !show; });
      on(d, 'click', function (e) { if (!form.contains(e.target)) pop.hidden = true; });
      on(input, 'keydown', function (e) { if (e.key === 'Escape') { pop.hidden = true; input.blur(); } });
      on(input, 'focus', function () { if (pop.innerHTML) pop.hidden = false; });
    }
    var sheet = $('#so'), btn = $('.m-search-btn');
    if (sheet && btn) {
      var si = $('input', sheet);
      liveSearch(si, $('.m-results', sheet));
      function open() { sheet.hidden = false; de.classList.add('sheet-open'); setTimeout(function () { si.focus(); }, 30); }
      function close() { sheet.hidden = true; de.classList.remove('sheet-open'); btn.focus({ preventScroll: true }); }
      on(btn, 'click', open);
      on($('[data-close-sheet]', sheet), 'click', close);
      on(d, 'keydown', function (e) { if (e.key === 'Escape' && !sheet.hidden) close(); });
    }
  })();

  /* ---------- mobile drawer ---------- */
  (function () {
    var nav = $('#mnav'), burger = $('.m-burger'); if (!nav || !burger) return;
    var lastFocus = null;
    function set(open) {
      de.classList.toggle('mnav-open', open);
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      nav.setAttribute('aria-hidden', open ? 'false' : 'true');
      if (open) { lastFocus = d.activeElement; setTimeout(function () { var x = $('[data-close]', nav); if (x) x.focus({ preventScroll: true }); }, 60); }
      else if (lastFocus) lastFocus.focus({ preventScroll: true });
    }
    on(burger, 'click', function () { set(!de.classList.contains('mnav-open')); });
    $$('[data-close]').forEach(function (b) { on(b, 'click', function () { set(false); }); });
    on(d, 'keydown', function (e) { if (e.key === 'Escape' && de.classList.contains('mnav-open')) set(false); });
    $$('.mnav-tabs button', nav).forEach(function (b) {
      on(b, 'click', function () {
        $$('.mnav-tabs button', nav).forEach(function (x) { x.setAttribute('aria-selected', x === b ? 'true' : 'false'); });
        $$('.mnav-list', nav).forEach(function (l) { l.hidden = l.getAttribute('data-list') !== b.getAttribute('data-tab'); });
      });
    });
    $$('.mnav-op', nav).forEach(function (b) {
      on(b, 'click', function () { var li = b.parentNode, o = !li.classList.contains('open'); li.classList.toggle('open', o); b.setAttribute('aria-expanded', o ? 'true' : 'false'); });
    });
  })();

  /* ---------- category listing ---------- */
  (function () {
    var grid = $('#grid'); if (!grid) return;
    var more = $('#more'), sel = $('.m-sort select'), countEl = $('.m-count');
    var cat = grid.getAttribute('data-cat') || '', per = +grid.getAttribute('data-per') || 12;
    var page = +grid.getAttribute('data-page') || 1, shown = grid.children.length, orderby = 'menu_order', rows = null;
    var start = (page - 1) * per, total = +grid.getAttribute('data-total');
    function ensure() { return catalog().then(function (data) { if (!rows) rows = listFor(data, cat, orderby); return rows; }); }
    function updCount() { if (countEl && start === 0) countEl.textContent = countText(total, shown); }
    if (more) on(more, 'click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      more.setAttribute('aria-busy', 'true');
      ensure().then(function (r) {
        var next = r.slice(start + shown, start + shown + per);
        grid.insertAdjacentHTML('beforeend', next.map(card).join(''));
        shown += next.length;
        more.removeAttribute('aria-busy');
        if (start + shown >= r.length) more.parentNode.hidden = true;
        updCount();
      });
    });
    if (sel) on(sel, 'change', function () {
      orderby = sel.value; rows = null; start = 0;
      ensure().then(function (r) {
        grid.innerHTML = r.slice(0, per).map(card).join('');
        shown = Math.min(per, r.length);
        if (more) more.parentNode.hidden = shown >= r.length;
        var pag = $('.m-pager'); if (pag) pag.remove();
        updCount();
      });
    });
  })();

  /* ---------- search page ---------- */
  (function () {
    var box = $('#sr'); if (!box) return;
    var qs = new URLSearchParams(location.search), q = (qs.get('s') || '').trim(), cat = qs.get('cat') || qs.get('product_cat') || '';
    var input = $('#sq'), count = $('#sc'), more = $('#sm'), per = 24, shown = 0, rows = [];
    if (input) input.value = q;
    if (!q) { count.textContent = 'اكتب اسم المنتج أو الكود.'; if (input) input.focus(); return; }
    d.title = 'نتائج البحث عن «' + q + '» | مطبعة مدارك';
    count.textContent = 'جارٍ البحث…';
    catalog().then(function (data) {
      if (cat && !/^\d+$/.test(cat)) { for (var id in data.c) if (data.c[id][1].indexOf('/' + cat + '/') >= 0) { cat = id; break; } }
      rows = search(data, q, cat);
      count.textContent = rows.length ? (arCount(rows.length) + ' لـ «' + q + '»') : ('لا توجد نتائج لـ «' + q + '». جرّب كلمة أقصر أو كود المنتج.');
      page();
    });
    function page() {
      var next = rows.slice(shown, shown + per);
      box.insertAdjacentHTML('beforeend', next.map(card).join(''));
      shown += next.length;
      more.hidden = shown >= rows.length;
    }
    on(more, 'click', page);
  })();

  /* ---------- home: product tabs ---------- */
  $$('[data-ptabs]').forEach(function (box) {
    var tabs = $$('.ptabs-nav button', box), panels = $$('.ptabs-panel', box);
    var prev = $('.ptabs-prev', box), next = $('.ptabs-next', box), state = panels.map(function () { return 0; }), cur = 0;
    function arrows() {
      var p = panels[cur], total = +(p.getAttribute('data-total') || 99);
      prev.disabled = state[cur] === 0; next.disabled = (state[cur] + 1) * 8 >= total;
    }
    function show(i) {
      cur = i;
      tabs.forEach(function (t, k) { t.setAttribute('aria-selected', k === i ? 'true' : 'false'); t.tabIndex = k === i ? 0 : -1; });
      panels.forEach(function (p, k) { p.hidden = k !== i; });
      arrows();
    }
    tabs.forEach(function (t, i) {
      on(t, 'click', function () { show(i); });
      on(t, 'keydown', function (e) {
        var k = e.key === 'ArrowLeft' ? 1 : e.key === 'ArrowRight' ? -1 : 0;
        if (k) { e.preventDefault(); var n = (i + k + tabs.length) % tabs.length; tabs[n].focus(); show(n); }
      });
    });
    function go(dir) {
      var p = panels[cur], g = $('.m-grid', p), want = state[cur] + dir;
      if (want < 0) return;
      p.classList.add('is-busy');
      catalog().then(function (data) {
        var r = listFor(data, p.getAttribute('data-cat'), p.getAttribute('data-order') === 'date' ? 'date' : 'menu_order');
        p.setAttribute('data-total', r.length);
        var slice = r.slice(want * 8, want * 8 + 8);
        if (slice.length) { g.innerHTML = slice.map(card).join(''); state[cur] = want; }
        p.classList.remove('is-busy');
        arrows();
      });
    }
    on(prev, 'click', function () { go(-1); });
    on(next, 'click', function () { go(1); });
  });

  /* ---------- product page ---------- */
  (function () {
    var gallery = $('.m-gallery');
    if (gallery) {
      var track = $('.m-g-track', gallery), figs = $$('figure', track), thumbs = $$('.m-g-thumbs button', gallery), counter = $('.m-g-count bdi', gallery), idx = 0;
      function mark(i) {
        idx = i;
        thumbs.forEach(function (t, k) { t.setAttribute('aria-current', k === idx ? 'true' : 'false'); });
        if (counter) counter.textContent = (idx + 1) + ' / ' + figs.length;
      }
      function goTo(i) {
        i = (i + figs.length) % figs.length;
        track.scrollTo({ left: figs[i].offsetLeft - track.offsetLeft, behavior: reduce ? 'auto' : 'smooth' });
        mark(i);
      }
      thumbs.forEach(function (t, k) { on(t, 'click', function () { goTo(k); }); });
      on($('.m-g-prev', gallery), 'click', function () { goTo(idx - 1); });
      on($('.m-g-next', gallery), 'click', function () { goTo(idx + 1); });
      var st = 0;
      on(track, 'scroll', function () {
        clearTimeout(st);
        st = setTimeout(function () { var i = Math.round(Math.abs(track.scrollLeft) / (track.clientWidth || 1)); if (i !== idx && figs[i]) mark(i); }, 80);
      }, { passive: true });
      var lb = $('#lb');
      if (lb) {
        var lbImg = $('img', lb);
        function lbClose() { lb.hidden = true; lbImg.removeAttribute('src'); }
        $$('a[data-lb]', gallery).forEach(function (a) {
          on(a, 'click', function (e) { e.preventDefault(); lbImg.src = a.href; lbImg.alt = ($('img', a) || {}).alt || ''; lb.hidden = false; $('button', lb).focus(); });
        });
        on(lb, 'click', function (e) { if (e.target === lb || e.target.closest('button')) lbClose(); });
        on(d, 'keydown', function (e) { if (e.key === 'Escape' && !lb.hidden) lbClose(); });
      }
    }

    // section nav follows the reader
    var toc = $$('.m-toc a');
    if (toc.length && 'IntersectionObserver' in W) {
      var secs = toc.map(function (a) { return $(a.getAttribute('href')); }).filter(Boolean), seen = {};
      var io = new IntersectionObserver(function (ents) {
        ents.forEach(function (en) { seen[en.target.id] = en.isIntersecting; });
        var act = null;
        for (var i = 0; i < secs.length; i++) if (seen[secs[i].id]) { act = secs[i].id; break; }
        if (!act && secs[0].getBoundingClientRect().top > 0) act = secs[0].id;
        if (act) toc.forEach(function (a) { a.classList.toggle('is-on', a.getAttribute('href') === '#' + act); });
      }, { rootMargin: '0px 0px -55% 0px' });
      secs.forEach(function (s) { io.observe(s); });
    }

    // options -> variation -> price + WhatsApp quote
    var form = $('.m-opts-form'), data = $('#pv'), quote = $('#quote'), note = $('.m-quote-note');
    if (!form || !data || !quote) return;
    var pv = JSON.parse(data.textContent), rows = $$('.mdk-opts', form);
    var box = $('.m-sel', form), dsc = $('.m-sel-d', form), prc = $('.m-sel-p', form), reset = $('.m-reset', form), label = $('span', quote);
    var mainImg = $('.m-g-track figure img'), mainSrc = mainImg ? mainImg.getAttribute('src') : '';
    function selected() { return rows.map(function (r) { var b = $('.mdk-opt.is-on', r); return b ? b.getAttribute('data-v') : ''; }); }
    function fits(v, sel, skip) { for (var j = 0; j < sel.length; j++) { if (j === skip || !sel[j]) continue; if (v.a[j] && v.a[j] !== sel[j]) return false; } return true; }
    function find(sel) {
      if (sel.some(function (x) { return !x; })) return null;
      for (var i = 0; i < pv.v.length; i++) if (fits(pv.v[i], sel, -1)) return pv.v[i];
      return null;
    }
    function money(x) { return '$' + (Math.round(x * 100) / 100).toString(); }
    function update() {
      var sel = selected();
      rows.forEach(function (r, j) {
        $$('.mdk-opt', r).forEach(function (b) {
          var val = b.getAttribute('data-v'), ok = pv.v.some(function (v) { return (!v.a[j] || v.a[j] === val) && fits(v, sel, j); });
          var isOn = sel[j] === val;
          b.classList.toggle('is-off', !ok); b.classList.toggle('is-on', isOn);
          b.setAttribute('aria-checked', isOn ? 'true' : 'false');
          if (ok) b.removeAttribute('aria-disabled'); else b.setAttribute('aria-disabled', 'true');
        });
      });
      var v = find(sel);
      box.classList.toggle('is-on', !!v);
      dsc.innerHTML = v ? v.d : ''; prc.innerHTML = v ? v.pb : '';
      reset.hidden = !sel.some(Boolean);
      if (mainImg) mainImg.src = v && v.img ? v.img : mainSrc;
      var lines = ['مرحباً مدارك، أريد عرض سعر:', pv.title];
      sel.forEach(function (x, j) { if (x) lines.push(pv.rows[j] + ': ' + x); });
      if (v) {
        var tmp = d.createElement('div'); tmp.innerHTML = v.d || '';
        var m = (tmp.textContent || '').match(/MD-[A-Z]{2}-\d{4}-\d{2}/), code = m ? m[0] : (v.s || '');
        if (code) lines.push('رقم الخيار: ' + code);
        if (v.p != null) lines.push('السعر المعروض: ' + money(v.p));
      }
      lines.push(pv.url);
      var text = encodeURIComponent(lines.join('\n'));
      quote.href = 'https://wa.me/' + pv.phone + '?text=' + text;
      var alt = $('.m-quote-alt'); if (alt) alt.href = 'https://wa.me/963980243748?text=' + text;
      label.textContent = v ? 'اطلب عرض سعر لهذا الخيار عبر واتساب' : 'اطلب عرض سعر عبر واتساب';
      note.textContent = v ? '' : 'اختر المواصفات والكمية لتشاهد السعر، ثم أرسل الطلب.';
    }
    rows.forEach(function (r, j) {
      on(r, 'click', function (e) {
        var b = e.target.closest('.mdk-opt'); if (!b) return;
        if (b.classList.contains('is-off')) rows.forEach(function (o, k) { if (k !== j) $$('.mdk-opt', o).forEach(function (x) { x.classList.remove('is-on'); }); });
        var was = b.classList.contains('is-on');
        $$('.mdk-opt', r).forEach(function (x) { x.classList.remove('is-on'); });
        if (!was) b.classList.add('is-on');
        update();
      });
    });
    on(reset, 'click', function () { $$('.mdk-opt', form).forEach(function (x) { x.classList.remove('is-on'); }); update(); });
    update();
  })();

  /* ---------- bottom bar (mobile): the old mdk-lbar, reading its items from .lbar-src ---------- */
  (function(){ var NS='http://www.w3.org/2000/svg', R0=31, F0=11, BY=2, DUR=460; var ICONS={shop:['M5 8.5h14l-1.1 11.5H6.1z','M9 8.5V7.2a3 3 0 0 1 6 0v1.3'],home:['M3.5 11.2 12 4l8.5 7.2','M6 9.6V20h12V9.6','M10.2 20v-5.2h3.6V20'],quote:['M12 3.6a8.3 8.3 0 0 0-7.2 12.4l-1.2 4.4 4.5-1.2A8.3 8.3 0 1 0 12 3.6z','M8.6 10.4h6.8','M8.6 13.4h4.4']}; function sv(t,a){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);return e} function icon(n){var s=sv('svg',{viewBox:'0 0 24 24','aria-hidden':'true',focusable:'false'});ICONS[n].forEach(function(dd){s.appendChild(sv('path',{d:dd}))});return s} function clamp(v){return Math.max(0,Math.min(1,v))} function eio(t){return t>=.5?1-Math.pow(-2*t+2,3)/2:4*t*t*t} function eout(t){return 1-Math.pow(1-t,3)} function ein(t){return t*t*t} function sock(cx,t){if(.02>=t)return '';var R=R0*t,f=F0*t,dd=Math.sqrt((R+f)*(R+f)-f*f),k=R/(R+f);return ' L'+(cx-dd).toFixed(2)+',0 A'+f.toFixed(2)+','+f.toFixed(2)+' 0 0 1 '+(cx-dd*k).toFixed(2)+','+(f*k).toFixed(2)+' A'+R.toFixed(2)+','+R.toFixed(2)+' 0 0 0 '+(cx+dd*k).toFixed(2)+','+(f*k).toFixed(2)+' A'+f.toFixed(2)+','+f.toFixed(2)+' 0 0 1 '+(cx+dd).toFixed(2)+',0'} function activeFor(items){var p=location.pathname;for(var i=0;items.length>i;i++){var it=items[i];if(it.ext)continue;if(it.k==='home'&&(p==='/'||p===''))return i;if(it.k==='shop'&&/^\/(shop|product-category|product)(\/|$)/.test(p))return i}return -1} function init(){ var src=document.querySelector('.lbar-src');if(!src||document.querySelector('.mdk-lbar'))return; var items=[];[].forEach.call(src.querySelectorAll('a[data-k]'),function(a){var href=a.getAttribute('href')||'#';var ext=/^https?:/.test(href)&&href.indexOf(location.host)===-1;items.push({k:a.getAttribute('data-k'),label:a.textContent.trim(),href:href,ext:ext,target:a.getAttribute('target')})}); if(!items.length)return; var bar=document.createElement('nav');bar.className='mdk-lbar';bar.setAttribute('aria-label','التنقل السريع'); var bg=sv('svg',{'class':'bg',preserveAspectRatio:'none','aria-hidden':'true'});var path=sv('path',{});bg.appendChild(path);bar.appendChild(bg); var safe=document.createElement('div');safe.className='safe';bar.appendChild(safe); var row=document.createElement('div');row.className='row';bar.appendChild(row); var bub=document.createElement('div');bub.className='bub';bar.appendChild(bub); items.forEach(function(it,i){var a=document.createElement('a');a.href=it.href;if(it.target)a.target=it.target;if(it.ext)a.rel='noopener';a.appendChild(icon(it.k));var s=document.createElement('span');s.textContent=it.label;a.appendChild(s);row.appendChild(a);it.a=a;var bi=icon(it.k);bub.appendChild(bi);it.bi=bi; a.addEventListener('click',function(e){ if(it.ext){a.classList.remove('tap');void a.offsetWidth;a.classList.add('tap');return} if(i===cur||e.metaKey||e.ctrlKey||e.shiftKey)return; e.preventDefault();var went=false,go=function(){if(went)return;went=true;location.href=it.href}; if(reduce){setActive(i);go();return} animate(cur,i,go);setTimeout(go,DUR+260); }); }); document.body.appendChild(bar);document.documentElement.classList.add('mdk-lbar-on'); var Wd=0,X=[],cur=-1,raf=0; function measure(){Wd=bar.clientWidth;bg.setAttribute('viewBox','0 0 '+Wd+' 62');var r0=bar.getBoundingClientRect().left;X=items.map(function(it){var r=it.a.getBoundingClientRect();return r.left-r0+r.width/2})} function draw(socks,bx,by,sx,sy,showBub){var list=socks.filter(function(s){return s[1]>.02}).sort(function(a,b){return a[0]-b[0]});var dd='M0,62 L0,0';list.forEach(function(s){dd+=sock(s[0],s[1])});dd+=' L'+Wd+',0 L'+Wd+',62 Z';path.setAttribute('d',dd); bub.style.transform='translate3d('+bx.toFixed(2)+'px,'+by.toFixed(2)+'px,0) scale('+sx.toFixed(3)+','+sy.toFixed(3)+')';bub.classList.toggle('vis',!!showBub)} function setIcon(i){items.forEach(function(it,j){it.bi.classList.toggle('on',j===i);it.a.classList.toggle('on',j===i);if(j===i)it.a.setAttribute('aria-current','page');else it.a.removeAttribute('aria-current')})} function setActive(i){cur=i;setIcon(i);if(0>i){draw([],Wd/2,BY,1,1,false);return}draw([[X[i],1]],X[i],BY,1,1,true)} function frame(a,b,t){ var oT=0>a?0:1-ein(clamp(t/.62)),nT=eout(clamp((t-.3)/.7)),e=eio(t); var bx,by,sx=1,sy=1; if(0>a){bx=X[b];by=BY+(1-eout(clamp(t/.8)))*40;var sc=.35+.65*eout(clamp(t/.8));sx=sy=sc} else{bx=X[a]+(X[b]-X[a])*e;var arc=Math.sin(Math.PI*e);by=BY-16*arc;sx=1+.16*arc;sy=1-.12*arc} draw([[X[b],nT]].concat(0>a?[]:[[X[a],oT]]),bx,by,sx,sy,true); } function animate(a,b,done){cancelAnimationFrame(raf);var t0=performance.now();items.forEach(function(it,j){it.a.classList.toggle('on',j===b)});var swapped=false; function step(now){var t=clamp((now-t0)/DUR);if(!swapped&&t>=.45){swapped=true;items.forEach(function(it,j){it.bi.classList.toggle('on',j===b)})}frame(a,b,t);if(1>t)raf=requestAnimationFrame(step);else{cur=b;setIcon(b);if(done)setTimeout(done,40)}} if(0>a){items.forEach(function(it,j){it.bi.classList.toggle('on',j===b)});swapped=true} raf=requestAnimationFrame(step)} bar.classList.add('init');measure();setActive(activeFor(items));requestAnimationFrame(function(){requestAnimationFrame(function(){bar.classList.remove('init')})}); var lw=window.innerWidth;window.addEventListener('resize',function(){if(window.innerWidth===lw)return;lw=window.innerWidth;measure();setActive(cur)}); window.addEventListener('pageshow',function(ev){if(ev.persisted){measure();setActive(activeFor(items))}}); } if(document.readyState!=='loading')init();else document.addEventListener('DOMContentLoaded',init); })();

  /* ---------- fold long text + FAQ accordions ---------- */
  (function(){
    var LESS='إخفاء';
    function bgOf(el){
      for(var n=el;n&&n.nodeType===1;n=n.parentElement){
        var c=getComputedStyle(n).backgroundColor;
        if(c&&c!=='transparent'&&!/rgba\([^)]*,\s*0\)$/.test(c))return c;
      }
      return '#fff';
    }
    function fold(el,h,label){
      if(!el||el.dataset.mdkFold)return; el.dataset.mdkFold=1;
      if(h*1.6>el.scrollHeight)return;
      el.classList.add('mdk-fold','is-folded'); el.style.maxHeight=h+'px';
      el.style.setProperty('--mdk-fold-bg',bgOf(el));
      var b=document.createElement('button'); b.type='button'; b.className='mdk-fold-btn'; b.textContent=label; b.setAttribute('aria-expanded','false');
      b.addEventListener('click',function(){
        if(el.classList.contains('is-folded')){
          el.style.maxHeight=el.scrollHeight+'px'; el.classList.remove('is-folded');
          b.textContent=LESS; b.setAttribute('aria-expanded','true');
          setTimeout(function(){if(!el.classList.contains('is-folded'))el.style.maxHeight='none'},550);
        }else{
          el.style.maxHeight=el.scrollHeight+'px'; el.offsetHeight;
          el.style.maxHeight=h+'px'; el.classList.add('is-folded');
          b.textContent=label; b.setAttribute('aria-expanded','false');
          var t=el.getBoundingClientRect().top; if(t<0)window.scrollBy({top:t-120,behavior:'smooth'});
        }
      });
      el.parentNode.insertBefore(b,el.nextSibling);
    }
    function faq(box){
      if(!box||box.dataset.mdkQa)return;
      var hs=[].filter.call(box.children,function(c){return c.tagName==='H3'&&!c.className});
      if(hs.length<3)return; box.dataset.mdkQa=1;
      hs.forEach(function(h,i){
        var qa=document.createElement('div'); qa.className='mdk-qa';
        var a=document.createElement('div'); a.className='mdk-qa-a'; var inner=document.createElement('div'); a.appendChild(inner);
        var n=h.nextElementSibling;
        var last=i===hs.length-1, c=0; while(n&&!(n.tagName==='H3'&&!n.className)&&!/^H[12]$/.test(n.tagName)&&!(last&&c>0)){var nx=n.nextElementSibling; inner.appendChild(n); n=nx; c++;}
        box.insertBefore(qa,h); qa.appendChild(h); qa.appendChild(a);
        var btn=document.createElement('button'); btn.type='button'; btn.className='mdk-qa-q';
        while(h.firstChild)btn.appendChild(h.firstChild); h.appendChild(btn);
        var id='mdkqa'+Math.random().toString(36).slice(2,8); a.id=id; btn.setAttribute('aria-controls',id);
        function set(o){qa.classList.toggle('open',o); btn.setAttribute('aria-expanded',o?'true':'false')}
        set(i===0);
        btn.addEventListener('click',function(){set(!qa.classList.contains('open'))});
      });
    }
    function run(){
      var mob=window.innerWidth<768;
      fold(document.querySelector('#tab-description .m-prose'),mob?520:560,'اقرأ الوصف كاملاً');
      fold(document.querySelector('.m-about-body'),mob?320:360,'اقرأ المزيد');
      [].forEach.call(document.querySelectorAll('.g-faq,.mdk-split>div'),faq);
    }
    if(document.readyState!=='loading')run(); else document.addEventListener('DOMContentLoaded',run);
  })();
})();
