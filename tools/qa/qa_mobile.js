// Phone check with real mobile emulation (touch, device viewport): page width, menu, search, language, swipe, scroll.
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const base = process.argv[2], pages = JSON.parse(fs.readFileSync(process.argv[3], 'utf8')), shots = process.argv[4] || 'mob';
  fs.mkdirSync(shots, { recursive: true });
  const b = await chromium.launch(); const issues = []; let n = 0;
  for (const W of [360, 390, 412]) {
    const ctx = await b.newContext({ viewport: { width: W, height: 800 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2,
      userAgent: 'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36' });
    await ctx.route(/googletagmanager|facebook\.net|google-analytics|doubleclick/, r => r.abort());
    for (const [name, path] of Object.entries(pages)) {
      const pg = await ctx.newPage(); const errs = []; pg.on('pageerror', e => errs.push(e.message.slice(0, 100)));
      const bad = (what) => issues.push(`${W} ${name} ${what}`);
      const width = async (stage) => { const r = await pg.evaluate(() => ({ iw: innerWidth, sw: document.documentElement.scrollWidth, sx: scrollX })); if (r.iw > W + 1 || r.sw > W + 1 || Math.abs(r.sx) > 1) bad(`${stage}: page ${r.sw}px wide (screen ${W}), layout ${r.iw}, scrollX ${r.sx}`); };
      try {
        await pg.goto(base + path, { waitUntil: 'load', timeout: 30000 }); await pg.waitForTimeout(400); n++;
        await width('load');
        // swipe sideways on the content: the page must not move
        await pg.evaluate(() => window.scrollTo(-500, 400)); await pg.waitForTimeout(100); await width('after sideways scroll');
        await pg.evaluate(() => window.scrollTo(0, 0));
        // menu
        const burger = await pg.$('.m-burger');
        if (burger && await burger.isVisible()) {
          await burger.tap(); await pg.waitForTimeout(450);
          const st = await pg.evaluate(() => { const m = document.getElementById('mnav'); if (!m) return null; const r = m.getBoundingClientRect(); return { l: Math.round(r.left), r: Math.round(r.right), vis: getComputedStyle(m).visibility, hid: m.hidden }; });
          if (!st || st.hid || st.vis === 'hidden' || st.l < -1 || st.r > W + 1) bad('menu ' + JSON.stringify(st));
          await width('menu open');
          if (W === 390) await pg.screenshot({ path: `${shots}/${name}-menu.png` });
          await pg.keyboard.press('Escape'); await pg.waitForTimeout(350);
          const closed = await pg.evaluate(() => { const m = document.getElementById('mnav'); return !m || m.hidden || getComputedStyle(m).visibility === 'hidden' || m.getBoundingClientRect().right <= 0 || m.getBoundingClientRect().left >= innerWidth || !document.documentElement.classList.contains('mnav-open'); });
          if (!closed) bad('menu does not close with Escape');
          const lock = await pg.evaluate(() => getComputedStyle(document.body).overflow + '/' + getComputedStyle(document.documentElement).overflow);
          if (/hidden/.test(lock)) bad('scroll still locked after closing the menu: ' + lock);
        } else bad('no menu button');
        // search
        const sb = await pg.$('.m-search-btn');
        if (sb && await sb.isVisible()) {
          await sb.tap(); await pg.waitForTimeout(350);
          const inp = await pg.$('#so input[type=search], #so input');
          if (inp) { await inp.fill(name.startsWith('en') ? 'pen' : name.startsWith('tr') ? 'kalem' : 'قلم'); await pg.waitForTimeout(900);
            const sr = await pg.evaluate(() => { const so = document.getElementById('so'); const items = so ? so.querySelectorAll('a[href*="/product"], a[href*="/urun/"]').length : 0; return { items }; });
            if (!sr.items) bad('search shows no results'); }
          else bad('search box missing');
          await width('search open');
          await pg.keyboard.press('Escape'); await pg.waitForTimeout(250);
        }
        // language list
        const lb = await pg.$('.m-lang-btn');
        if (lb && await lb.isVisible()) { await lb.tap(); await pg.waitForTimeout(250);
          const lp = await pg.evaluate(() => { const p = document.getElementById('langpop'); if (!p || p.hidden) return null; const r = p.getBoundingClientRect(); return { l: Math.round(r.left), r: Math.round(r.right), n: p.querySelectorAll('a').length }; });
          if (!lp || lp.l < 0 || lp.r > W || lp.n !== 3) bad('language list ' + JSON.stringify(lp));
          await pg.keyboard.press('Escape'); }
        // scroll to the end (lazy parts) and check again
        await pg.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 40)); } });
        await pg.waitForTimeout(300); await width('scrolled to end');
        if (W === 390) { await pg.evaluate(() => window.scrollTo(0, 0)); await pg.waitForTimeout(200); await pg.screenshot({ path: `${shots}/${name}-top.png` }); }
        if (errs.length) bad('script error: ' + errs[0]);
      } catch (e) { bad('FAIL ' + String(e).slice(0, 140)); }
      await pg.close();
    }
    await ctx.close();
  }
  console.log('page loads', n, 'issues', issues.length); console.log(issues.join('\n'));
  await b.close();
})();
