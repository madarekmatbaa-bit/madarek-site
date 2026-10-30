"""One-off: map old URLs that still get Google traffic (Search Console, 16 months) to live pages.
Writes data/redirects_gsc.json as [[old_path, new_path], ...]."""
import json, os, re, sys, urllib.parse as up
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, 'dist')
cat = json.load(open(os.path.join(ROOT, 'content/catalog.json')))

def exists(path):
    p = up.unquote(path).strip('/')
    return os.path.exists(os.path.join(DIST, p, 'index.html')) or os.path.exists(os.path.join(DIST, p))

by_sku = {}
for p in cat['products']:
    if p.get('sku'):
        by_sku[p['sku'].lower()] = up.unquote(p['path'])
    for v in p.get('variations') or []:
        if v.get('sku'):
            by_sku.setdefault(v['sku'].lower(), up.unquote(p['path']))

PC = '/product-category/'
PREFIX = [  # (regex on old product slug, target)
    (r'^ek-', PC + 'kristal/'),
    (r'^(gari|def)-', PC + 'notebooks/'),
    (r'^klb-', PC + 'packaging/'),
    (r'^gbp-', PC + 'packaging/gift-boxes/'),
    (r'^klm-', PC + 'promotional-ar/pens/metal-kalem/'),
    (r'^(klp-|klp$|\d+-klp$)', PC + 'promotional-ar/pens/klp/'),
    (r'^kv-', PC + 'promotional-ar/desk-accessories/card-holders/'),
    (r'^kb$', PC + 'promotional-ar/desk-accessories/card-holders/'),
    (r'(^|-)sat(pl|mt|mp)?-', PC + 'promotional-ar/clocks/wall-clocks/'),
    (r'^t-3', PC + 'promotional-ar/drinkware/thermoses/'),
    (r'^(sap|yek|tshy)-', PC + 'tekstil-ar/'),
    (r'^(kby|masa-bayragi)$', PC + 'flag-ar/desk-flags/'),
    (r'^mak$', PC + 'flag-ar/flags-poles/'),
    (r'^fd2$', PC + 'offset-ar/paper-carbon-forms/'),
    (r'^usb-', PC + 'promotional-ar/electronics/fla/'),
    (r'(^|-)ant-', PC + 'promotional-ar/anh/'),
    (r'^sbl-', PC + 'promotional-ar/desk-accessories/desk-organizers/'),
    (r'^(irak|libya-kargo|السعودية|الشحن-إلى-.*)$', '/shipping/'),
]
KEYWORDS = [  # Arabic slugs of products that were removed or merged: send to their category
    (['قمصان', 'مريلة'], PC + 'tekstil-ar/'),
    (['ساعة-حائط', 'satpl', 'satmt', 'satmp'], PC + 'promotional-ar/clocks/wall-clocks/'),
    (['ميدالية', '-ant-'], PC + 'promotional-ar/anh/'),
    (['علم-مكتبي', 'علم-مكتبي-مزدوج'], PC + 'flag-ar/desk-flags/'),
    (['علم', 'سارية', 'أعلام', 'وتد-تثبيت', 'رأس-مدبب', 'قاعدة-حاجز'], PC + 'flag-ar/flags-poles/'),
    (['لوحة-اسم', 'حامل-بلكسي'], PC + 'promotional-ar/desk-accessories/desk-organizers/'),
    (['قلم-رصاص'], PC + 'promotional-ar/pens/pencils-highlighters/'),
    (['كيس-ورقي'], PC + 'offset-ar/paper-bags/'),
    (['علبة-أقلام', 'حامل-أقلام'], PC + 'promotional-ar/desk-accessories/pen-holders/'),
    (['دفاتر-طلبات'], PC + 'offset-ar/paper-carbon-forms/'),
    (['دفتر'], PC + 'notebooks/'),
    (['فناجين'], PC + 'promotional-ar/drinkware/mugs-cups/'),
    (['بطاقة-ورقية'], PC + 'offset-ar/paper-folders-cards/'),
    (['مكعب-ملاحظات'], PC + 'stationery/'),
]
CATS = {
    'promotional-ar/kristal': 'kristal/', 'promotional-ar/klp': 'promotional-ar/pens/klp/',
    'promotional-ar/def': 'notebooks/', 'promotional-ar/metal-kalem': 'promotional-ar/pens/metal-kalem/',
    'promotional-ar/أقلام-معدنية': 'promotional-ar/pens/metal-kalem/', 'promotional-ar/fla': 'promotional-ar/electronics/fla/',
    'promotional-ar/vipbox': 'packaging/gift-boxes/',
    # categories with no products left
    'promotional-ar/badges': 'promotional-ar/', 'promotional-ar/kids-gifts': 'promotional-ar/',
    'promotional-ar/dog': 'promotional-ar/pens/eco-pens/', 'promotional-ar/klabox': 'packaging/',
    'promotional-ar/kr': 'promotional-ar/desk-accessories/card-holders/',
    'promotional-ar/saat-pla': 'promotional-ar/clocks/wall-clocks/', 'promotional-ar/saat02': 'promotional-ar/clocks/wall-clocks/',
    'promotional-ar/saat03': 'promotional-ar/clocks/wall-clocks/', 'promotional-ar/sbl': 'promotional-ar/desk-accessories/',
    'حلول-الشحن': '/shipping/', 'offset-ar/commercial-print': 'offset-ar/',
    'offset-ar/notebooks': 'notebooks/', 'offset-ar/stationery': 'stationery/',
}

def target_for(path):
    u = up.unquote(path)
    m = re.match(r'^/product-category/(.+?)/?$', u)
    if m:
        key = m.group(1)
        for k, v in CATS.items():
            if key == k or key.startswith(k + '/'):
                return v if v.startswith('/') else PC + v
        return None
    m = re.match(r'^/product/(.+?)/?$', u)
    if not m:
        return None
    slug = m.group(1)
    code = re.search(r'md-tr-\d+-\d{4}', slug)
    if code and code.group(0) in by_sku:
        return by_sku[code.group(0)]
    if slug.startswith('ylk') or 'علم-شراعي' in slug:
        return '/product/' + 'علم-شراعي-feather/'
    if slug.startswith('rull'):
        return '/product/رول-أب/'
    for rx, dst in PREFIX:
        if re.search(rx, slug):
            return dst
    for words, dst in KEYWORDS:
        if any(w in slug for w in words):
            return dst
    return None

if __name__ == '__main__':
    paths = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    out, miss, live = [], [], 0
    for p in paths:
        if exists(p):
            live += 1
            continue
        t = target_for(p)
        if t and exists(t):
            out.append([p, t])
        else:
            miss.append((p, t))
    # category redirects that must exist even without traffic
    for k, v in CATS.items():
        src = PC + k + '/'
        dst = v if v.startswith('/') else PC + v
        if not any(o[0] == src for o in out) and exists(dst):
            out.append([src, dst])
            out.append([src + '*', dst])
    json.dump(out, open(os.path.join(ROOT, 'data/redirects_gsc.json'), 'w'), ensure_ascii=False, indent=0)
    print('live', live, 'redirects', len(out), 'unmapped', len(miss))
    for m in miss:
        print('  MISS', m)
