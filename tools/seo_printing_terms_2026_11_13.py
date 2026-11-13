#!/usr/bin/env python3
"""Put «طباعة …» at the front of the titles people search by service.
Ammar 13 Nov 2026: «مطبعة عم تطلع، طباعة ما عم تطلع. بدي يطلع بالبحث… متل طباعة كروت، طباعة هدايا دعائية».
Search Console on 13 Nov: «مطبعة» position 8.7, but «طباعة كروت شخصية» 54, «طباعة بروشورات» 46, «طباعة رول أب» 79.

Pages that already rank on their current wording keep it inside the new title (استيكر لاصق، أكياس ورقية مطبوعة،
دفاتر ملاحظات مطبوعة). Pages ranking in the top ten are not touched (دروع تكريم، مذكرة داخلية، دفتر سلك).

    python3 tools/seo_printing_terms_2026_11_13.py [--dry]
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, 'content/catalog.json')
PAGES = os.path.join(ROOT, 'content/pages-raw.json')
TAIL = ' | مطبعة مدارك'
P = '/product-category/'

CATS = {
    'promotional-ar/': 'طباعة هدايا دعائية وهدايا شركات بشعارك',
    'promotional-ar/pens/': 'طباعة أقلام دعائية بشعار الشركة',
    'promotional-ar/pens/klp/': 'طباعة أقلام بلاستيكية بالشعار',
    'promotional-ar/pens/metal-kalem/': 'طباعة وحفر أقلام معدنية بالشعار',
    'notebooks/': 'طباعة دفاتر وأجندات 2027 بشعارك',
    'promotional-ar/drinkware/': 'طباعة أكواب وترامس بشعار الشركة',
    'promotional-ar/drinkware/mugs-cups/': 'طباعة على الأكواب والفناجين بشعارك',
    'promotional-ar/drinkware/thermoses/': 'طباعة ترامس حرارية بشعارك',
    'promotional-ar/electronics/': 'طباعة شعارك على هدايا إلكترونية دعائية',
    'promotional-ar/electronics/fla/': 'طباعة فلاش USB بشعار الشركة',
    'promotional-ar/electronics/power-banks/': 'طباعة باور بانك بشعارك: هدايا إلكترونية',
    'promotional-ar/anh/': 'طباعة ميداليات مفاتيح بشعارك',
    'promotional-ar/bags/': 'طباعة حقائب دعائية بشعارك',
    'promotional-ar/clocks/': 'طباعة ساعات حائط دعائية بشعارك',
    'promotional-ar/umbrellas/': 'طباعة مظلات دعائية بشعارك',
    'tekstil-ar/': 'طباعة تيشيرتات وملابس بشعار الشركة',
    'packaging/': 'طباعة علب وتغليف هدايا بشعارك',
    'packaging/gift-boxes/': 'طباعة علب هدايا وعلب أقلام بشعارك',
    'flag-ar/flags-poles/': 'طباعة أعلام وساريات بشعارك',
    'flag-ar/desk-flags/': 'طباعة أعلام مكتبية بشعارك',
    'offset-ar/paper-carbon-forms/': 'طباعة دفاتر فواتير وسند قبض وإيصالات كربون',
    'offset-ar/paper-restaurant/': 'طباعة مطبوعات المطاعم: دفاتر طلبات ومفارش',
    'offset-ar/paper-printed-notepads/': 'طباعة دفاتر ملاحظات ومكعبات ورق بشعارك',
}
PRODUCTS = {
    'KART-N': 'طباعة كروت شخصية (بزنس كارد) 1000 كرت',
    'BRO': 'طباعة بروشورات 1000 عدد: مطويات وفلايرات بتصميمك',
    'ETK': 'استيكر لاصق: طباعة ستيكرات 1000 عدد بتصميمك',
    'DOSYA': 'طباعة فولدرات: ملفات بجيب 350 جرام',
    'KCN': 'طباعة أكياس ورقية بشعارك',
    'MD-PR-0015': 'أكياس ورقية مطبوعة: طباعة بشعارك للمحلات',
    'MD-PR-0014': 'طباعة أظرف بشعار الشركة (كيس ودبلوماسي)',
    'MD-PR-0005': 'طباعة ورق رسمي للمراسلات (ليترهيد)',
    'MD-PR-0002': 'طباعة دفاتر مستندات رسمية بكربون',
    'MD-PR-0001': 'طباعة دفاتر كربون: عقود وطلبات وبيع',
    'MD-PR-0004': 'طباعة دفتر إيصالات بكعب',
    'MD-PR-0003': 'طباعة دفتر طلبات مطعم',
    'MD-PR-0010': 'طباعة مفرش ورقي للمطاعم بشعارك',
    'MD-PR-0011': 'طباعة فرشة أرضية ورقية للسيارات',
    'MD-PR-0012': 'دفاتر ملاحظات مطبوعة: طباعة بشعار الشركة',
    'MD-PR-0013': 'طباعة مكعب ملاحظات بشعارك',
    'MD-PR-0008': 'طباعة بطاقة كرتونية A4 (بريستول)',
    'MD-PR-0006': 'طباعة نماذج متصلة (فواتير كمبيوتر)',
    'MD-FL-12': 'طباعة علم شراعي (Feather) بتصميمك',
    'MD-FL-13': 'طباعة علم قطرة (Teardrop) بتصميمك',
    'MD-FL-16': 'طباعة علم سارية خارجي (قماش)',
    'MD-FL-01': 'طباعة علم مكتبي: طقم كامل',
    'MD-FL-19': 'طباعة راية معلّقة بتصميمك',
    'MD-FL-21': 'طباعة راية تذكارية بشعارك',
}
HOME = 'مطبعة مدارك: طباعة هدايا دعائية وكروت ومطبوعات بشعارك'


def retitle(seo, new):
    old = seo['title']
    if old == new:
        return False
    seo['title'] = new
    seo['tags'] = [t.replace(f'content="{old}"', f'content="{new}"') if ('og:title' in t or 'twitter:title' in t) else t for t in seo['tags']]
    oj, nj = json.dumps(old, ensure_ascii=False)[1:-1], json.dumps(new, ensure_ascii=False)[1:-1]
    seo['ld'] = [ld.replace(f'"name":"{oj}"', f'"name":"{nj}"') for ld in seo.get('ld', [])]
    print(' ', old, '->', new, f'({len(new)})')
    return True


def main():
    cat = json.load(open(CAT, encoding='utf-8'))
    nc = sum(retitle(c['seo'], CATS[c['path'][len(P):]] + TAIL) for c in cat['categories'] if c['path'][len(P):] in CATS)
    np_ = sum(retitle(p['seo'], PRODUCTS[p['sku']] + TAIL) for p in cat['products'] if p['sku'] in PRODUCTS)
    found_c = {c['path'][len(P):] for c in cat['categories']} & set(CATS)
    found_p = {p['sku'] for p in cat['products']} & set(PRODUCTS)
    if len(found_c) != len(CATS) or len(found_p) != len(PRODUCTS):
        raise SystemExit(f'missing: {set(CATS) - found_c} {set(PRODUCTS) - found_p}')
    raw = open(PAGES, encoding='utf-8').read()
    pages = json.loads(raw)
    nh = sum(retitle(p['seo'], HOME) for p in pages if p['path'] == '/')
    print('categories', nc, 'products', np_, 'home', nh)
    if '--dry' not in sys.argv:
        json.dump(cat, open(CAT, 'w', encoding='utf-8'), ensure_ascii=False)
        json.dump(pages, open(PAGES, 'w', encoding='utf-8'), ensure_ascii=False)


if __name__ == '__main__':
    main()
