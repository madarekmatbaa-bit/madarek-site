#!/usr/bin/env python3
"""Default product order on the site = what is most likely to sell (Ammar, 30 Oct 2026: «المنتجات المتوقع
أن تنباع أكثر… بدون ما تحط أكثر مبيعا… ويتخربطوا»).

Demand comes from the portal (quotes and orders, portal.madarekmatbaa.net). The numbers are kept in
data/sales_rank.json; lib/ranking.py turns them into the order every listing uses (build.py).

Refresh the numbers:
    python3 tools/sales_rank.py js > /tmp/rank.js     # paste into the browser console on the portal (logged in)
    # copy the printed JSON to a file, then:
    python3 tools/sales_rank.py update --demand demand.json

`update` also marks products whose picture is only a text card (no photo yet), so they go to the end of
their kind; run it again after new products are added.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import ranking  # noqa: E402

# a quote line's weight by its state: orders are sales, accepted quotes nearly so
STATE = {'O': 3.0, 'accepted': 2.5, 'approved': 2.5, 'sent': 1.0, 'draft': 0.8, 'lost': 0.6, 'expired': 0.6,
         'cancelled': 0.3}

JS = r"""(async () => {
  const RULES = %s, STATE = %s;
  const get = u => fetch(u, {credentials: 'include'}).then(r => r.json());
  const rows = [];
  async function walk(list, key, one) {
    const done = new Set();
    for (let page = 1; page < 100; page++) {
      const l = await get(list + '?page=' + page), items = (l[key] || []).filter(x => !done.has(x.id));
      for (const x of items) {
        done.add(x.id);
        const lines = Array.isArray(x.lines) ? x.lines : ((await get(one + x.id)).lines || []);
        for (const ln of lines) rows.push([key === 'orders' ? 'O' : 'Q', x.status, ln.code || '', ln.nameAr || '', ln.qty || 0]);
      }
      if (!items.length || page * (l.pageSize || 1e9) >= (l.total || 0)) break;
    }
  }
  await walk('/api/quotes', 'quotes', '/api/quotes/');
  await walk('/api/orders', 'orders', '/api/orders/');
  const seen = new Set(), kinds = {}, codes = {}, other = {};
  for (const r of rows) {
    const k = JSON.stringify(r); if (seen.has(k)) continue; seen.add(k);
    const w = r[0] === 'O' ? STATE.O : (STATE[r[1]] ?? 0.5);
    const code = (r[2].match(/^(MD-TR-\d-\d{4})/) || [])[1];
    if (code) { const c = codes[code] || (codes[code] = [0, r[3]]); c[0] += w; continue; }
    const rule = RULES.find(x => new RegExp(x[1], 'i').test(r[3]));
    if (!rule) { other[r[3]] = (other[r[3]] || 0) + w; continue; }
    for (const [key, share] of Object.entries(rule[2])) kinds[key] = (kinds[key] || 0) + w * share;
  }
  for (const k in kinds) kinds[k] = Math.round(kinds[k] * 100) / 100;
  for (const k in codes) codes[k][0] = Math.round(codes[k][0] * 100) / 100;
  return JSON.stringify({lines: rows.length, distinct: seen.size, kinds, codes, other});
})()"""


def cmd_js(a):
    rules = [[name, pat, split] for name, pat, split in ranking.PORTAL_RULES]
    print(JS % (json.dumps(rules, ensure_ascii=False), json.dumps(STATE)))


def text_card_ids():
    """Products whose first picture is the brand text card (heading + gold bar, nothing in the lower half)."""
    import images
    from PIL import Image
    images.setup(os.path.join(ROOT, 'media'), os.path.join(ROOT, 'cache'))
    cat = json.load(open(os.path.join(ROOT, 'content/catalog.json'), encoding='utf-8'))
    out = []
    for p in cat['products']:
        if not p.get('images'):
            out.append(p['id'])
            continue
        try:
            im = Image.open(images._file(images.local_url(p['images'][0]['src']))).convert('RGB').resize((200, 200))
        except OSError:
            continue
        px = im.load()
        g = px[100, 6]
        bg = sum(g) / 3
        gold = sum(1 for y in range(20, 80) for x in range(110, 195)
                   if abs(px[x, y][0] - 209) < 35 and abs(px[x, y][1] - 178) < 35 and px[x, y][2] < 110)
        ink = sum(1 for y in range(110, 172) for x in range(20, 180) if abs(sum(px[x, y]) / 3 - bg) > 45)
        if gold >= 6 and ink / (62 * 160) < 0.03:
            out.append(p['id'])
    return out


def cmd_update(a):
    path = os.path.join(ROOT, 'data/sales_rank.json')
    cur = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
    if a.demand:
        d = json.load(open(a.demand, encoding='utf-8'))
        if isinstance(d, str):
            d = json.loads(d)
        # a line quoted by code counts for the kind of the site product with that code (by name otherwise)
        cat = json.load(open(os.path.join(ROOT, 'content/catalog.json'), encoding='utf-8'))
        cats = {c['id']: c for c in cat['categories']}
        site = {c: ranking.kind_of(p, cats) for p in cat['products'] for c in ranking.codes_of(p)}
        kinds = dict(d['kinds'])
        for code, (w, name) in d['codes'].items():
            if code in site:
                split = {site[code]: 1}
            else:
                rule = next((r for r in ranking.PORTAL_RULES if re.search(r[1], name, re.I)), None)
                split = rule[2] if rule else {}
            for k, share in split.items():
                kinds[k] = kinds.get(k, 0) + w * share
        cur['demand'] = {k: round(v, 2) for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])}
        cur['codes'] = {k: round(v[0], 2) for k, v in sorted(d['codes'].items(), key=lambda kv: -kv[1][0]) if k in site}
        cur['lines'] = d.get('distinct')
    cur.setdefault('lead', ['MD-AG-0001', 'KART-N', 'MD-FL-01', 'MD-FL-06', 'MD-FL-12'])
    cur['no_photo'] = sorted(text_card_ids(), key=int)
    cur['note'] = ('demand: quote/order lines from the portal by kind (orders x3, accepted x2.5, sent x1, '
                   'lost x0.6, cancelled x0.3); codes: the same per product code; no_photo: text-card pictures. '
                   'Refresh with tools/sales_rank.py.')
    json.dump(cur, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"{path}: {len(cur.get('demand', {}))} kinds, {len(cur.get('codes', {}))} codes, "
          f"{len(cur['no_photo'])} without a photo")


def cmd_show(a):
    sys.argv = [sys.argv[0]]
    cat = json.load(open(os.path.join(ROOT, 'content/catalog.json'), encoding='utf-8'))
    ordered = ranking.order(cat['products'], cat['categories'])
    want = a.cat
    cats = {c['id']: c for c in cat['categories']}

    def under(p):
        if not want:
            return True
        for cid in p['cats']:
            while cid:
                if cid == want:
                    return True
                cid = cats[cid].get('parent')
        return False
    for p in [p for p in ordered if under(p)][:a.n]:
        print(f"{ranking.kind_of(p, cats):14} {p['sku'] or '':14} {p['name'][:60]}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('js')
    u = sub.add_parser('update')
    u.add_argument('--demand')
    s = sub.add_parser('show')
    s.add_argument('--cat', type=int)
    s.add_argument('-n', type=int, default=40)
    a = ap.parse_args()
    return {'js': cmd_js, 'update': cmd_update, 'show': cmd_show}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main() or 0)
