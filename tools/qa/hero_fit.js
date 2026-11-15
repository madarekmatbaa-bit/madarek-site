// The opening film of the home page: its text and its 3D scene must never share a pixel, and the text must stay
// between the header and the bottom of the screen.
// (Ammar 14 Nov 2026, from his phone: «داخل ببعضها». The box sat over the buttons at 412x748, and the earlier checks
// used an 800 px tall phone, which no browser with its bars on screen really has. Laptops are the same: a 1366x768
// screen shows about 650 px of page.)
//   node tools/qa/hero_fit.js <base url> [languages: ar,en,tr] [sizes: 412x748,1440x900]
// Sizes are what the browser really shows with its bars: small and common phones, an unfolded phone, tablets both ways,
// laptops, desktop.
// At each size the film is stepped from start to end; every point inside the visible text is hit-tested against the scene.
// Wherever the bottom bar shows (up to 1024 px wide) the scene must also stay above it (Ammar 14 Nov, again from his phone:
// «فايت ببعضه»). Shadows on the floor do not count. Screens under 540 px tall are left out of this one: on a 320x480
// phone the opening text alone fills the screen, and the bar covers the foot of the box.
const { chromium } = require('playwright');
const base = process.argv[2] || 'http://127.0.0.1:8765';
const LANGS = (process.argv[3] || 'ar,en,tr').split(',').map(l => l === 'ar' ? '' : l);
const SIZES = process.argv[4] ? process.argv[4].split(',').map(s => s.split('x').map(Number)) : [[320, 480], [360, 560], [360, 640], [375, 553],
  [390, 664], [393, 760], [412, 748], [430, 780], [673, 700], [768, 900], [820, 1180], [1024, 650], [1180, 720], [1280, 600], [1366, 650], [1440, 790],
  [1536, 730], [1920, 950]];
// .08 and .11 are where the lid slides out while the next chapter's text comes in; .91 to .945 are where the bag comes in
// (it used to pass behind the bottom bar there, between two of the older steps)
const STEPS = [0, .02, .04, .06, .08, .1, .11, .14, .2, .3, .4, .5, .56, .62, .66, .7, .72, .74, .78, .84, .9, .91, .92, .93, .945, .96, 1];
(async () => {
  const b = await chromium.launch(); const bad = []; let n = 0;
  for (const lang of LANGS) {
    for (const [w, h] of SIZES) {
      const c = await b.newContext({ viewport: { width: w, height: h }, hasTouch: w < 1025, isMobile: w < 1025 });
      await c.route(/googletagmanager|facebook\.net|google-analytics|doubleclick|googlesyndication/, r => r.abort());
      const p = await c.newPage();
      await p.goto(base + '/' + (lang ? lang + '/' : ''), { waitUntil: 'load' }); await p.waitForTimeout(1500);
      await p.addStyleTag({ content: '.mdk-story .ms-stage,.mdk-story .ms-stage *{pointer-events:auto!important}.mdk-story .ms-stage,.mdk-story .ms-ch-hero>*{animation:none!important}' });
      for (const s of STEPS) {
        const hit = await p.evaluate(async s => {
          const st = document.querySelector('.mdk-story'), pin = st.querySelector('.ms-pin'), world = st.querySelector('.ms-world');
          scrollTo(0, Math.round(st.offsetTop + (st.offsetHeight - pin.clientHeight) * s));
          await new Promise(r => setTimeout(r, 500));
          const seen = e => { for (let x = e; x && x !== st; x = x.parentElement) { const cs = getComputedStyle(x); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < .3) return false } return true };
          const texts = [...st.querySelectorAll('.ms-ch h1,.ms-ch h2,.ms-ch p,.ms-ch .ms-kick,.ms-ch .ms-btn,.ms-ch .ms-cats a,.ms-ch .ms-stats div')].filter(seen);
          // the text against the header above it and the edge of the screen below it
          const hd = document.querySelector('.m-hdr'), hb = hd && !hd.classList.contains('is-hidden') ? hd.getBoundingClientRect().bottom : 0;
          for (const t of texts) {
            const r = t.getBoundingClientRect(); if (r.height < 2) continue;
            if (r.top < hb - 1) return (t.textContent || '').trim().slice(0, 24) + ' <- under the header';
            if (r.bottom > innerHeight + 1) return (t.textContent || '').trim().slice(0, 24) + ' <- past the bottom of the screen';
          }
          // the scene against the bottom bar
          const bar = document.querySelector('.mdk-lbar');
          if (bar && innerHeight >= 540 && getComputedStyle(bar).display !== 'none') {
            const bt = bar.getBoundingClientRect().top;
            // faces of the box, the lid and the bag, the flat pieces, the name tags, and the cup (a picture, not a face)
            for (const e of world.querySelectorAll('.ms-face,.ms-plane,.ms-label,.ms-world>.ms-el>img')) {
              if (['30px', '24px', '40%'].includes(e.style.borderRadius) || e.closest('.ms-gshadow,.sh') || !seen(e)) continue;   // floor shadows
              const r = e.getBoundingClientRect();
              if (r.width > 2 && r.right > 2 && r.left < innerWidth - 2 && r.top < innerHeight && r.bottom > bt + 1) return 'the bottom bar <- ' + (e.className || e.tagName) + ' by ' + Math.round(r.bottom - bt) + 'px';
            }
          }
          for (const t of texts) {
            // where the words really are: each line of text has its own box (a heading's own box is as wide as its column)
            let boxes = [t.getBoundingClientRect()];
            if (!t.classList.contains('ms-btn')) { const rg = document.createRange(); rg.selectNodeContents(t); boxes = [...rg.getClientRects()]; }
            for (const r of boxes) {
              if (r.width < 2 || r.height < 2 || r.bottom < 0 || r.top > innerHeight) continue;
              for (let y = r.top + 2; y < r.bottom; y += 6) for (let x = r.left + 2; x < r.right; x += 6) {
                // .prw is the moving window of the print reveal: it has a box where nothing is painted, so only what is inside it counts.
                // A face seen almost edge-on can be reported at a point far outside it (the browser's 3D hit test loses its
                // footing there: on 320x480 a side of the standing box, 8 px wide and 30 px lower, was reported under the
                // figures), so a hit counts only when the point is inside the face's own box on screen.
                const inside = e => { const q = e.getBoundingClientRect(); return x >= q.left - 1 && x <= q.right + 1 && y >= q.top - 1 && y <= q.bottom + 1 };
                const under = document.elementsFromPoint(x, y).find(e => world.contains(e) && e !== world && !e.classList.contains('prw') && !e.closest('.ms-gshadow,.sh') && seen(e) && inside(e));
                if (under) return (t.textContent || '').trim().slice(0, 24) + ' <- ' + (under.className || under.tagName);
              }
            }
          }
          return '';
        }, s);
        n++;
        if (hit) bad.push(`${lang || 'ar'} ${w}x${h} at ${s}: ${hit}`);
      }
      await c.close();
    }
  }
  await b.close();
  bad.forEach(x => console.log(x));
  console.log(`hero fit: ${n} frames, overlaps ${bad.length}`);
  process.exit(bad.length ? 1 : 0);
})();
