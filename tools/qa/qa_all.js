// Whole-site check at phone width: horizontal overflow, script errors, broken first images, text cut in buttons.
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const base = process.argv[2], list = fs.readFileSync(process.argv[3], 'utf8').trim().split('\n'), W = +(process.argv[4] || 360);
  const out = process.argv[5] || 'qa_all.json';
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: W, height: 800 } });
  await ctx.route(/googletagmanager|facebook\.net|google-analytics|doubleclick/, r => r.abort());
  const res = []; let i = 0;
  async function worker() {
    const pg = await ctx.newPage();
    let errs = [];
    pg.on('pageerror', e => errs.push(e.message.slice(0, 120)));
    while (i < list.length) {
      const p = list[i++]; errs = [];
      try {
        await pg.goto(base + p, { waitUntil: 'load', timeout: 30000 });
        await pg.waitForTimeout(150);
        const r = await pg.evaluate(() => {
          const de = document.documentElement, W = de.clientWidth, o = { hs: de.scrollWidth - W, wide: [], img: 0, clip: [] };
          if (o.hs > 1) {
            const clipped = e => { for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) { const s = getComputedStyle(a); if (s.overflowX !== 'visible' || s.position === 'fixed') return true; } return false; };
            for (const e of document.querySelectorAll('body *')) { const s = getComputedStyle(e); if (s.position === 'fixed') continue; const r = e.getBoundingClientRect(); if (r.width && (r.left < -1 || r.right > W + 1) && !clipped(e)) o.wide.push((e.tagName + '.' + (typeof e.className === 'string' ? e.className : '')).slice(0, 50) + ' ' + Math.round(r.width)); if (o.wide.length > 4) break; }
          }
          for (const im of document.querySelectorAll('img')) { if (im.loading !== 'lazy' && im.complete && im.naturalWidth === 0 && im.getAttribute('src')) o.img++; }
          for (const e of document.querySelectorAll('a.m-btn, button, .m-nav-link, .m-card-title, h1')) { if (e.offsetParent === null) continue; const s = getComputedStyle(e); if (e.scrollWidth > e.clientWidth + 2 && s.overflowX === 'hidden' && s.textOverflow !== 'ellipsis') o.clip.push((e.className || e.tagName).toString().slice(0, 30)); }
          return o;
        });
        if (r.hs > 1 || errs.length || r.img || r.clip.length) res.push({ p, ...r, errs });
      } catch (e) { res.push({ p, fail: String(e).slice(0, 120) }); }
    }
    await pg.close();
  }
  await Promise.all(Array.from({ length: 6 }, worker));
  fs.writeFileSync(out, JSON.stringify(res, null, 1));
  console.log('checked', list.length, 'at', W, 'px; problems', res.length);
  const groups = {};
  for (const r of res) { const k = (r.fail ? 'FAIL' : '') + (r.hs > 1 ? 'overflow:' + (r.wide[0] || '').split(' ')[0] : '') + (r.errs && r.errs.length ? ' err:' + r.errs[0].slice(0, 60) : '') + (r.img ? ' img' : '') + (r.clip && r.clip.length ? ' clip:' + r.clip[0] : ''); (groups[k] = groups[k] || []).push(r.p); }
  for (const [k, v] of Object.entries(groups)) console.log(v.length, k, '| e.g.', decodeURIComponent(v[0]));
  await b.close();
})();
