#!/usr/bin/env python3
"""Product titles of two words («مبراة | مطبعة مدارك») say nothing to a searcher. Add what the page sells:
«طباعة … بشعارك» for print work and «… بشعارك» with the code for gifts (Ammar 10 Nov 2026: «قوي ال seo»).

    python3 tools/seo_short_titles_2026_11_10.py [--dry]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, 'content/catalog.json')
TAIL = ' | مطبعة مدارك'
PRINT = {'KART-N': 'طباعة كروت شخصية (بزنس كارد) بشعارك', 'ANT': 'طباعة ورق رسمي بشعار الشركة', 'ZARF': 'طباعة ظروف ورقية بشعار الشركة',
         'DFB': 'طباعة دفتر سلك بشعارك', 'MD-PR-0009': 'طباعة ملف بجيب (فولدر) بشعارك', 'MD-FL-27': 'طباعة رول أب بتصميمك',
         'MD-FL-20': 'طباعة علم يدوي بشعارك'}


def main():
    cat = json.load(open(CAT, encoding='utf-8'))
    n = 0
    for p in cat['products']:
        seo = p['seo']
        old = seo['title']
        if len(old) >= 25 or not old.endswith(TAIL):
            continue
        name = old[:-len(TAIL)]
        new = (PRINT.get(p['sku']) or f"{name} بشعارك {p['sku']}") + TAIL
        seo['title'] = new
        seo['tags'] = [t.replace(f'content="{old}"', f'content="{new}"') if 'og:title' in t or 'twitter:title' in t else t for t in seo['tags']]
        seo['ld'] = [ld.replace('"name":"' + json.dumps(old, ensure_ascii=False)[1:-1] + '"', '"name":"' + json.dumps(new, ensure_ascii=False)[1:-1] + '"')
                     for ld in seo.get('ld', [])]
        n += 1
        print(p['sku'], '|', old, '->', new)
    print(n, 'titles')
    if '--dry' not in sys.argv:
        json.dump(cat, open(CAT, 'w', encoding='utf-8'), ensure_ascii=False)


if __name__ == '__main__':
    main()
