const { chromium } = require('playwright');
const base = process.argv[2] || 'http://localhost:8765';
(async () => {
  const br = await chromium.launch();
  const widths = [360, 390, 768, 1024, 1025, 1060, 1100, 1150, 1199, 1200, 1250, 1280, 1300, 1301, 1366, 1400, 1401, 1440, 1480, 1536, 1600, 1680, 1920, 2560];
  for (const p of ['/', '/en/', '/tr/']) {
    const out = [];
    for (const w of widths) {
      const pg = await br.newPage({viewport:{width:w, height:700}});
      await pg.goto(base + p, {waitUntil:'load'}); await pg.waitForTimeout(250);
      const r = await pg.evaluate(() => {
        const vis = el => el && el.offsetParent !== null && getComputedStyle(el).visibility !== 'hidden';
        const boxes = [];
        const add = (sel, name) => document.querySelectorAll(sel).forEach((el,i) => { if (vis(el)) { const b = el.getBoundingClientRect(); if (b.width>0) boxes.push({name: name + (i||''), l:b.left, r:b.right, t:b.top, b:b.bottom}); } });
        add('.m-logo', 'logo'); add('.m-nav-list > li', 'nav'); add('.m-search', 'search'); add('.m-search-btn', 'sbtn'); add('.m-hdr-cta', 'cta'); add('.m-hdr .m-lang', 'lang'); add('.m-burger', 'burger');
        const hits = [];
        for (let i=0;i<boxes.length;i++) for (let j=i+1;j<boxes.length;j++) { const a=boxes[i], c=boxes[j]; if (a.l < c.r-1 && c.l < a.r-1 && a.t < c.b-1 && c.t < a.b-1) hits.push(a.name+'×'+c.name); }
        const hdr = document.querySelector('.m-hdr-in').getBoundingClientRect();
        const outside = boxes.filter(x => x.l < hdr.left-1 || x.r > hdr.right+1).map(x=>x.name);
        return {hits, outside, sw: document.documentElement.scrollWidth > window.innerWidth};
      });
      if (r.hits.length || r.outside.length || r.sw) out.push(`${w}: overlap ${r.hits.join(',')} | outside ${r.outside.join(',')} | hscroll ${r.sw}`);
      await pg.close();
    }
    console.log(p, out.length ? '\n  ' + out.join('\n  ') : 'OK at all widths');
  }
  await br.close();
})();
