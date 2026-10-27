"""Turn the WordPress export (data/*.json + data/html/*.html) into the clean
content files the new site builds from (content/*.json, content/pages/*.html).

Run once per export:  python3 tools/snapshot.py
After the switch, product data comes from the portal instead (see lib/catalog.py).
"""
import json, os, re, html as H, urllib.parse as up
from bs4 import BeautifulSoup, Comment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')
C = os.path.join(ROOT, 'content')
os.makedirs(os.path.join(C, 'pages'), exist_ok=True)
SITE = 'https://www.madarekmatbaa.com'


def J(name):
    return json.load(open(os.path.join(D, name + '.json')))


def path_of(url):
    p = up.urlsplit(url).path
    return p if p.endswith('/') else p + '/'


def soup(fn):
    return BeautifulSoup(open(fn, encoding='utf-8').read(), 'lxml')


# ---------- SEO head (verbatim from the live page) ----------
KEEP_META_NAMES = {'description', 'robots', 'twitter:card', 'twitter:site', 'twitter:title',
                   'twitter:description', 'twitter:image', 'twitter:label1', 'twitter:data1',
                   'twitter:label2', 'twitter:data2'}


def seo_head(s):
    out = {'title': s.title.get_text() if s.title else ''}
    tags = []
    if s.head is None:
        return {'title': '', 'tags': [], 'ld': []}
    for m in s.head.find_all('meta'):
        n = m.get('name') or ''
        p = m.get('property') or ''
        if n in KEEP_META_NAMES or p.startswith('og:') or p.startswith('article:') or p.startswith('product:'):
            tags.append(str(m))
    for l in s.head.find_all('link'):
        rel = ' '.join(l.get('rel') or [])
        if rel in ('canonical', 'prev', 'next'):
            tags.append(str(l))
    ld = []
    for sc in s.find_all('script', attrs={'type': 'application/ld+json'}):
        t = sc.string or sc.get_text()
        t = t.strip()
        if t:
            ld.append(t)
    out['tags'] = tags
    out['ld'] = ld
    return out


# ---------- categories ----------
store_cats = {c['id']: c for c in J('store_cats')}
wp_cats = J('wp_cats')
cats = []
for c in wp_cats:
    fn = os.path.join(D, 'html', f"cat-{c['id']}.html")
    s = soup(fn)
    sc = store_cats.get(c['id'], {})
    # breadcrumbs as rendered
    bc = [(a.get_text(strip=True), path_of(a['href'])) for a in s.select('.wd-breadcrumbs a')]
    cats.append({
        'id': c['id'], 'name': H.unescape(c['name']), 'slug': c['slug'], 'path': path_of(c['link']),
        'parent': c['parent'], 'count': c['count'], 'description': c['description'],
        'image': (sc.get('image') or {}).get('src') if sc.get('image') else None,
        'image_alt': (sc.get('image') or {}).get('alt') if sc.get('image') else None,
        'seo': seo_head(s), 'breadcrumbs': bc,
    })

# ---------- products ----------
wp_products = {p['id']: p for p in J('wp_products')}
variations = J('variations')
products = []
for p in J('store_products'):
    fn = os.path.join(D, 'html', f"product-{p['id']}.html")
    s = soup(fn)
    bc = [(a.get_text(strip=True), path_of(a['href'])) for a in s.select('.wd-breadcrumbs a')]
    related = []
    rel = s.select_one('[data-widget_type="wd_products.default"]')
    if rel:
        for a in rel.select('.wd-entities-title a'):
            related.append(path_of(a['href']))
    nav = s.select_one('[data-widget_type="wd_single_product_nav.default"]')
    prev_next = [path_of(a['href']) for a in nav.select('a.wd-product-nav-thumb, .wd-product-nav-btn a')] if nav else []
    pr = p['prices']
    mu = 10 ** pr.get('currency_minor_unit', 2)
    price = {
        'price': int(pr['price']) / mu if pr.get('price') else None,
        'regular': int(pr['regular_price']) / mu if pr.get('regular_price') else None,
        'sale': int(pr['sale_price']) / mu if pr.get('sale_price') else None,
        'min': int(pr['price_range']['min_amount']) / mu if pr.get('price_range') else None,
        'max': int(pr['price_range']['max_amount']) / mu if pr.get('price_range') else None,
        'on_sale': p.get('on_sale', False),
    }
    var = []
    v = variations.get(str(p['id']))
    if isinstance(v, list):
        for x in v:
            var.append({'id': x['variation_id'], 'attrs': {up.unquote(k.replace('attribute_', '')): val for k, val in x['attributes'].items()},
                        'price': x.get('display_price'), 'regular': x.get('display_regular_price'),
                        'sku': x.get('sku'), 'image': (x.get('image') or {}).get('url'), 'image_alt': (x.get('image') or {}).get('alt'),
                        'desc': (x.get('variation_description') or '').strip()})
    elif isinstance(v, dict):
        for x in v['store_variations']:
            xp = x['prices']
            var.append({'id': x['id'], 'attrs': {a['name']: a['value'] for a in x.get('variation_attributes', x.get('attributes', [])) if 'value' in a} if x.get('variation_attributes') else {},
                        'price': int(xp['price']) / mu, 'regular': int(xp['regular_price']) / mu, 'sku': x.get('sku'),
                        'image': x['images'][0]['src'] if x.get('images') else None,
                        'image_alt': x['images'][0]['alt'] if x.get('images') else None,
                        'desc': (x.get('description') or '').strip()})
            if not var[-1]['attrs']:
                # store API variation names: "variation" holds "Attr: Val, Attr: Val"
                pass
    # store API attribute list (for selects)
    attrs = []
    for a in p.get('attributes', []):
        attrs.append({'name': a['name'], 'taxonomy': a.get('taxonomy'), 'has_variations': a.get('has_variations'),
                      'terms': [t['name'] for t in a.get('terms', [])]})
    # options exactly as the live form renders them (label, option order, default selection)
    form = []
    for tr in s.select('form.variations_form table.variations tr'):
        sel = tr.find('select')
        if not sel:
            continue
        lab = tr.find('label')
        opts = [(o.get('value'), o.get_text(strip=True)) for o in sel.find_all('option') if o.get('value')]
        cur = sel.find('option', selected=True)
        form.append({'label': lab.get_text(strip=True) if lab else '', 'name': up.unquote(sel.get('data-attribute_name', '').replace('attribute_', '')),
                     'options': opts, 'default': cur.get('value') if cur and cur.get('value') else ''})
    # product tabs as rendered (reviews dropped: no reviews and the form needs WordPress)
    tabs = []
    for li in s.select('.wc-tabs li'):
        a = li.find('a')
        tid = a['href'].lstrip('#') if a else ''
        if not tid or tid == 'tab-reviews':
            continue
        pn = s.find(id=tid)
        if not pn:
            continue
        tabs.append({'id': tid, 'title': a.get_text(strip=True), 'cls': ' '.join(pn.get('class') or []), 'html': pn.decode_contents()})
    products.append({
        'id': p['id'], 'name': H.unescape(p['name']), 'slug': p['slug'], 'path': path_of(p['permalink']),
        'sku': p['sku'], 'type': p['type'], 'price': price,
        'images': [{'src': i['src'], 'alt': i.get('alt') or '', 'name': i.get('name')} for i in p['images']],
        'cats': [c['id'] for c in p['categories']],
        'short': p['short_description'], 'description': p['description'],
        'attributes': attrs, 'variations': var, 'store_variations_index': p.get('variations', []),
        'date': wp_products.get(p['id'], {}).get('date'), 'menu_order': wp_products.get(p['id'], {}).get('menu_order', 0),
        'seo': seo_head(s), 'breadcrumbs': bc, 'related': related, 'prev_next': prev_next,
        'form': form, 'tabs': tabs,
    })

# fill variation attrs for store-API fetched ones from the product's variations index
for p in products:
    idx = {v['id']: v['attributes'] for v in p['store_variations_index']}
    for v in p['variations']:
        if not v['attrs'] and v['id'] in idx:
            v['attrs'] = {a['name']: a['value'] for a in idx[v['id']]}
    del p['store_variations_index']

# ---------- pages ----------
wp_pages = J('wp_pages')
pages = []
for pg in wp_pages + [{'id': 'shop', 'slug': 'shop', 'link': SITE + '/shop/', 'title': {'rendered': 'المتجر'}, 'parent': 0}]:
    fn = os.path.join(D, 'html', f"page-{pg['id']}.html")
    if not os.path.exists(fn):
        continue
    raw = open(fn, encoding='utf-8').read()
    if len(raw) < 2000:
        continue  # redirect stub (checkout)
    s = BeautifulSoup(raw, 'lxml')
    path = path_of(pg['link'])
    main = s.select_one('.wd-content-layout') or s.select_one('main')
    parts = []
    if main:
        for e in main.select('[data-widget_type]'):
            if e.find_parent(attrs={'data-widget_type': True}):
                continue
            wt = e['data-widget_type']
            if wt == 'html.default':
                box = e.select_one('.elementor-widget-container') or e
                parts.append(('html', box.decode_contents()))
            else:
                parts.append(('widget', wt, e.decode_contents()))
        if not parts:
            ec = main.select_one('.entry-content') or main
            parts.append(('content', ec.decode_contents()))
    pages.append({'id': pg['id'], 'slug': pg['slug'], 'path': path, 'parent': pg.get('parent', 0),
                  'title': H.unescape(pg['title']['rendered']) if isinstance(pg.get('title'), dict) else '',
                  'template': pg.get('template', ''), 'seo': seo_head(s), 'parts': parts})

# ---------- navigation as the live site renders it ----------
def tree(ul):
    out = []
    for li in ul.find_all('li', recursive=False):
        a = li.find('a')
        t = a.select_one('.nav-link-text')
        item = {'name': (t or a).get_text(strip=True), 'path': path_of(a['href']) if a['href'].startswith('http') else a['href']}
        sub = li.find('ul')
        if sub:
            item['children'] = tree(sub)
        out.append(item)
    return out


REF = os.path.join(ROOT, 'data', 'ref')
hdr = BeautifulSoup(open(os.path.join(REF, 'header.html'), encoding='utf-8').read(), 'lxml')
menu = tree(hdr.select_one('.wd-nav-main'))
for m in menu:
    if m['path'] == '/':
        m['path'] = '/'
cat_nav = tree(BeautifulSoup(open(os.path.join(D, 'html', 'cat-296.html'), encoding='utf-8').read(), 'lxml').select_one('.wd-nav-product-cat'))
json.dump({'menu': menu, 'cat_nav': cat_nav}, open(os.path.join(C, 'nav.json'), 'w'), ensure_ascii=False, indent=1)

# one page per path (the shop page was exported twice)
seen = set()
pages = [p for p in pages if not (p['path'] in seen or seen.add(p['path']))]

json.dump({'categories': cats, 'products': products}, open(os.path.join(C, 'catalog.json'), 'w'), ensure_ascii=False)
json.dump(pages, open(os.path.join(C, 'pages-raw.json'), 'w'), ensure_ascii=False)
print('categories', len(cats), 'products', len(products), 'pages', len(pages))
from collections import Counter
print('variations', sum(len(p['variations']) for p in products), 'no-attrs', sum(1 for p in products for v in p['variations'] if not v['attrs']))
print('page parts', Counter(x[0] if x[0] != 'widget' else x[1] for p in pages for x in p['parts']))
