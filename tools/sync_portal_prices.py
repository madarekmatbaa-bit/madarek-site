#!/usr/bin/env python3
"""Put portal list prices on the site (Ammar 5 Nov 2026: «اكد انه منتجات اللي على الموقع واسعارها نفس المنتجات والاسعار اللي على البوابه»).

    python3 tools/sync_portal_prices.py data/portal_prices_2026_11_05.json [--dry]

The file has two maps of portal variant code -> portal unit price (Turkey, all markets):
  main        the price the product page shows: product price, «يبدأ … من $…», meta description, Google data, and the
              code's row in the «الخيارات والأسعار» table
  table_only  only the code's row in the table (the product price already matched)
Shown prices follow the site's rule: from $1 up two decimals; under $1 rounded up to the cent. Table rows keep the
portal figure (three decimals under $1).
"""
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, 'content/catalog.json')


def shown(v):
    return round(v, 2) if v >= 1 else math.ceil(v * 100 - 1e-9) / 100


def money(v):
    return f'{v:.2f}'


def table_money(v):
    s = f'{v:.3f}'.rstrip('0')
    return s + '0' * max(0, 2 - len(s.split('.')[1]))


def olds(v):
    """the ways an old price may be written in the text"""
    return {f'{v:.2f}', f'{v:g}', f'{v:.3f}'.rstrip('0').rstrip('.')}


def set_row(html, code, value):
    """the price cell of the table row that holds this code"""
    n = 0

    def row(m):
        nonlocal n
        tr = m.group(0)
        if f'>{code}<' not in tr:
            return tr
        cells = list(re.finditer(r'<td>\$[\d,]+(?:\.\d+)?</td>', tr))
        if not cells:
            return tr
        c = cells[-1]
        n += 1
        return tr[:c.start()] + f'<td>${table_money(value)}</td>' + tr[c.end():]
    return re.sub(r'<tr>.*?</tr>', row, html, flags=re.S), n


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv
    data = json.load(open(args[0], encoding='utf-8'))
    cat = json.load(open(CAT, encoding='utf-8'))
    by_sku = {p['sku']: p for p in cat['products'] if p.get('sku')}
    report = []
    for kind in ('main', 'table_only'):
        for code, portal in data.get(kind, {}).items():
            sku = re.sub(r'-V\d{2}$', '', code)
            p = by_sku.get(sku)
            if not p or p['type'] != 'simple':
                report.append(f'{code}: not a simple product on the site')
                continue
            rows = 0
            for f in ('short', 'description'):
                if p.get(f):
                    p[f], k = set_row(p[f], code, portal)
                    rows += k
            for t in p.get('tabs') or []:
                if isinstance(t, dict) and t.get('html'):
                    t['html'], k = set_row(t['html'], code, portal)
                    rows += k
            if kind == 'table_only':
                report.append(f'{code}: table {rows}')
                continue
            old = p['price']['price']
            new = shown(portal)
            p['price'].update(price=new, regular=new, sale=new)
            txt = 0
            for o in olds(old):
                pat = re.compile(r'(من\s*\$)' + re.escape(o) + r'(?![\d])')
                for f in ('short', 'description'):
                    if p.get(f):
                        p[f], k = pat.subn(r'\g<1>' + money(new), p[f])
                        txt += k
                for t in p.get('tabs') or []:
                    if isinstance(t, dict) and t.get('html'):
                        t['html'], k = pat.subn(r'\g<1>' + money(new), t['html'])
                        txt += k
                seo = p['seo']
                tags = []
                for tag in seo['tags']:
                    tag, k = pat.subn(r'\g<1>' + money(new), tag)
                    txt += k
                    tags.append(tag)
                seo['tags'] = tags
                lds = []
                for ld in seo['ld']:
                    ld, k = pat.subn(r'\g<1>' + money(new), ld)
                    txt += k
                    ld, k = re.subn(r'("price"\s*:\s*")' + re.escape(o) + r'"', r'\g<1>' + money(new) + '"', ld)
                    txt += k
                    lds.append(ld)
                seo['ld'] = lds
            report.append(f'{code}: {old} -> {money(new)} (portal {portal}) | rows {rows} | text {txt}')
    print('\n'.join(report))
    if not dry:
        json.dump(cat, open(CAT, 'w', encoding='utf-8'), ensure_ascii=False)
        print('written', CAT)


if __name__ == '__main__':
    main()
