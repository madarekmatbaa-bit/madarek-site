#!/usr/bin/env python3
"""Build the static madarekmatbaa.com into dist/.

    python3 build.py            # full build
    python3 build.py --no-media # skip copying /wp-content/uploads (faster while editing)

Inputs: content/catalog.json, content/pages-raw.json, content/nav.json (from tools/snapshot.py),
data/order_menu.json (default product order), data/ref/*.xml (live sitemaps, for lastmod).
Same URLs as the WordPress site, same SEO heads (copied from the live pages).
"""
import hashlib
import html as H
import json
import os
import re
import shutil
import sys
import urllib.parse as up
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'dist')
CACHE = os.path.join(ROOT, 'cache')
MEDIA = os.path.join(ROOT, 'media')  # holds wp-content/uploads/...
SITE = 'https://www.madarekmatbaa.com'
PER_PAGE = 12
WA_SALES = '905510059096'
NO_MEDIA = '--no-media' in sys.argv

sys.path.insert(0, os.path.join(ROOT, 'lib'))
import images  # noqa: E402

images.setup(MEDIA, CACHE)


def J(path):
    return json.load(open(os.path.join(ROOT, path), encoding='utf-8'))


catalog = J('content/catalog.json')
pages_raw = J('content/pages-raw.json')
nav = J('content/nav.json')
order = {pid: i for i, pid in enumerate(J('data/order_menu.json'))}
icons = J('assets/icons.json')

SOCIAL = [
    {'icon': 'facebook', 'label': 'فيسبوك', 'url': 'https://www.facebook.com/madarek.matbaa'},
    {'icon': 'x', 'label': 'إكس', 'url': 'https://twitter.com/MadarekMatbaa'},
    {'icon': 'instagram', 'label': 'إنستغرام', 'url': 'https://www.instagram.com/madarek.matbaa/'},
    {'icon': 'youtube', 'label': 'يوتيوب', 'url': 'https://www.youtube.com/@madarekmatbaa'},
    {'icon': 'pinterest', 'label': 'بنترست', 'url': 'https://tr.pinterest.com/madarekmatbaa/'},
    {'icon': 'linkedin', 'label': 'لينكدإن', 'url': 'https://www.linkedin.com/in/madarekmatbaa/'},
    {'icon': 'whatsapp', 'label': 'واتساب', 'url': 'https://wa.me/905516498048'},
    {'icon': 'tiktok', 'label': 'تيك توك', 'url': 'https://www.tiktok.com/@madarek.matbaa'},
]

# ---------------------------------------------------------------- helpers
ABS = re.compile(r'https?://(?:www\.)?madarekmatbaa\.com(?=[/"\'\s<)]|$)')


def relink(html):
    """Make links inside page bodies root-relative so the preview host works too.
    (SEO tags and JSON-LD keep the absolute production URLs.)"""
    if not html:
        return html
    out, pos = [], 0
    for m in re.finditer(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>', html, re.S):
        out.append(ABS.sub('', html[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(ABS.sub('', html[pos:]))
    s = ''.join(out)
    return s.replace('href=""', 'href="/"')


def money(x):
    return ('<span class="woocommerce-Price-amount amount"><bdi><span class="woocommerce-Price-currencySymbol">$</span>'
            f'{x:,.2f}</bdi></span>')


def price_html(pr, variable):
    if pr.get('price') is None and pr.get('min') is None:
        return ''
    if variable and pr.get('min') is not None and pr.get('max') is not None and pr['min'] != pr['max']:
        return (f'{money(pr["min"])} <span aria-hidden="true">–</span> {money(pr["max"])}'
                f'<span class="screen-reader-text">نطاق السعر: من ${pr["min"]:,.2f} إلى ${pr["max"]:,.2f}</span>')
    if pr.get('on_sale') and pr.get('regular') and pr.get('price') and pr['regular'] > pr['price']:
        return f'<del aria-hidden="true">{money(pr["regular"])}</del> <ins>{money(pr["price"])}</ins>'
    v = pr.get('price') if pr.get('price') is not None else pr.get('min')
    return money(v)


def money_short(x):
    """$684 / $7.19 / $11,580 (Poppins renders the digits)."""
    s = f'{x:,.0f}' if abs(x - round(x)) < 0.005 else f'{x:,.2f}'
    return f'<bdi>${s}</bdi>'


def price_short(p):
    pr = p['price']
    if p['type'] == 'variable' and pr.get('min') is not None and pr.get('max') is not None and pr['min'] != pr['max']:
        return f'<span class="m-from">من</span> {money_short(pr["min"])}'
    if pr.get('on_sale') and pr.get('regular') and pr.get('price') is not None and pr['regular'] > pr['price']:
        return f'{money_short(pr["price"])} <del>{money_short(pr["regular"])}</del>'
    v = pr.get('price') if pr.get('price') is not None else pr.get('min')
    return money_short(v) if v is not None else ''


def price_big(p):
    pr = p['price']
    if p['type'] == 'variable' and pr.get('min') is not None and pr.get('max') is not None and pr['min'] != pr['max']:
        return f'<span class="m-from">يبدأ من</span> <b>{money_short(pr["min"])}</b>'
    if pr.get('on_sale') and pr.get('regular') and pr.get('price') is not None and pr['regular'] > pr['price']:
        return f'<b>{money_short(pr["price"])}</b> <del>{money_short(pr["regular"])}</del>'
    v = pr.get('price') if pr.get('price') is not None else pr.get('min')
    return f'<b>{money_short(v)}</b>' if v is not None else ''


def ar_count(n, one='منتج واحد', two='منتجان', few='منتجات', many='منتجاً', other='منتج'):
    """Arabic plural for product counts (0, 1, 2, 3-10, 11-99, 100+)."""
    if n == 0:
        return 'لا منتجات'
    if n == 1:
        return one
    if n == 2:
        return two
    m = n % 100
    if 3 <= m <= 10:
        return f'{n} {few}'
    if 11 <= m <= 99:
        return f'{n} {many}'
    return f'{n} {other}'


def low_price(p):
    pr = p['price']
    return pr['min'] if p['type'] == 'variable' and pr.get('min') is not None else pr.get('price')


def file_for(path):
    """URL path (percent-encoded, trailing slash) -> dist file."""
    rel = up.unquote(path).strip('/')
    return os.path.join(OUT, rel, 'index.html') if rel else os.path.join(OUT, 'index.html')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def plural_results(n):
    m = n % 100
    return 'نتائج' if 3 <= m <= 10 else 'نتيجة'


def count_text(total, page, per=PER_PAGE):
    shown = min(page * per, total) - (page - 1) * per
    if total <= per:
        return ar_count(total)
    if page == 1:
        return f'عرض {shown} من {ar_count(total)}'
    a = (page - 1) * per + 1
    return f'عرض {a}-{a + shown - 1} من {ar_count(total)}'


def seo_paged(seo, base_path, page, pages):
    """Yoast heads for /page/N/: same title/description, canonical to itself, prev/next."""
    tags = []
    for t in seo['tags']:
        if re.search(r'rel="(canonical|prev|next)"', t):
            continue
        tags.append(t)
    url = SITE + base_path + (f'page/{page}/' if page > 1 else '')
    tags.append(f'<link href="{url}" rel="canonical"/>')
    if page > 1:
        prev = SITE + base_path + (f'page/{page - 1}/' if page > 2 else '')
        tags.append(f'<link href="{prev}" rel="prev"/>')
    if page < pages:
        tags.append(f'<link href="{SITE}{base_path}page/{page + 1}/" rel="next"/>')
    return {'title': seo['title'], 'tags': tags, 'ld': seo['ld'] if page == 1 else []}


# ---------------------------------------------------------------- assets
def build_assets():
    css_order = ['base.css', 'legacy-theme.css', 'legacy-tidy.css', 'legacy-block.css', 'legacy-shop.css', 'm.css']
    css = '\n'.join(open(os.path.join(ROOT, 'assets/css', f), encoding='utf-8').read() for f in css_order)
    # the shop shelf and its CSS anchored on Elementor ids; point them at our sections
    css = css.replace('.elementor-element-49de9f4', '.sh-nav').replace('.elementor-element-195c2fd1', '.sh-hero')
    css = minify_css(css)
    js = open(os.path.join(ROOT, 'assets/js/site.js'), encoding='utf-8').read()
    shelf = open(os.path.join(ROOT, 'assets/js/legacy-shop.js'), encoding='utf-8').read()
    shelf = shelf.replace('.elementor-element-49de9f4', '.sh-nav').replace('.elementor-element-195c2fd1', '.sh-hero')
    shelf = shelf.replace('"https://www.madarekmatbaa.com/wp-content/', '"/wp-content/')
    js = js + '\n;' + shelf
    names = {}
    for name, body in (('site.css', css), ('site.js', js)):
        h = hashlib.sha1(body.encode()).hexdigest()[:10]
        stem, ext = name.rsplit('.', 1)
        out = f'{stem}.{h}.{ext}'
        write(os.path.join(OUT, 'assets', out), body)
        names[name] = '/assets/' + out
    shutil.copytree(os.path.join(ROOT, 'assets/fonts'), os.path.join(OUT, 'assets/fonts'), dirs_exist_ok=True)
    shutil.copytree(os.path.join(ROOT, 'assets/brand'), os.path.join(OUT, 'assets/brand'), dirs_exist_ok=True)
    if REEL:
        shutil.copytree(os.path.join(ROOT, 'assets', REEL_DIR), os.path.join(OUT, 'assets', REEL_DIR),
                        dirs_exist_ok=True, ignore=shutil.ignore_patterns('*.mp4', '*.png'))
    return names


# ---------------------------------------------------------------- home hero film (realistic box, see tools/reel_frames.py)
REEL_DIR = 'reel-v3'
_reel_manifest = os.path.join(ROOT, 'assets', REEL_DIR, 'manifest.json')
# off: Ammar 29 Oct «رجع القديم» — the home page keeps the original drawn box story.
# Set REEL_ON = True to bring the realistic film back (frames stay in assets/reel-v3).
REEL_ON = False
REEL = json.load(open(_reel_manifest)) if REEL_ON and os.path.exists(_reel_manifest) else None
# one continuous film (Ammar 28 Oct: the pieces only come out and spread, no return and no bag).
# Clips (frame folders c0..c1): 0 lid lifts · 1 the pieces come out printed and lie around the box
# segments [from, to, kind, a, b]: h = hold clip a (b: 0 first / 1 last frame), p = play clip a,
# r = play clip a backwards, w = "print" clip a's last frame over to clip b's first frame (r, w not used now)
REEL_TIMELINE = [[0, .07, 'h', 0, 0], [.07, .25, 'p', 0], [.25, .5, 'p', 1], [.5, 1.01, 'h', 1, 1]]
# words: hero, 01 box, 02 printing, 03 details, 04 delivery: [in-start, in-end, out-start, out-end]
REEL_CHAPTERS = [[-1, -1, .05, .09], [.08, .12, .21, .25], [.26, .30, .45, .50], [.50, .54, .70, .74],
                 [.76, .80, 2, 2]]
REEL_LABEL_WINDOW = [.51, .72]
# label anchors on the last frame of clip 1 (pieces lying printed around the box), fractions of the 16:9 frame
REEL_LABELS = [
    {'name': 'ملف بجيب', 'note': '300 غ', 'x': .163, 'y': .38},
    {'name': 'ورق رسمي', 'note': '80 غ', 'x': .214, 'y': .605},
    {'name': 'كاسة ورقية', 'note': 'مطبوعة', 'x': .467, 'y': .305},
    {'name': 'دفتر سلك', 'note': '', 'x': .536, 'y': .45},
    {'name': 'كرت شخصي', 'note': '350 غ', 'x': .44, 'y': .535},
    {'name': 'ظرف DL', 'note': '110 غ', 'x': .488, 'y': .64},
]


def reel_html(story_html):
    """Replace the illustrated CSS box story with the realistic film, keeping the same words and links."""
    s = BeautifulSoup(story_html, 'html.parser')
    copy = s.select_one('.ms-copy')
    model = {'base': f'/assets/{REEL_DIR}/', 'clips': [c['n'] for c in REEL['clips']], 'd': REEL['d'], 'm': REEL['m'], 'mcrop': REEL.get('mcrop', [0, 0, 1, 1]),
             'labels': REEL_LABELS, 'words': Markup(str(copy)), 'timeline': REEL_TIMELINE,
             'chapters': REEL_CHAPTERS, 'label_window': REEL_LABEL_WINDOW}
    return env.get_template('partials/reel.html').render(reel=model)


def minify_css(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'\s+', ' ', css)
    css = re.sub(r'\s*([{};,>])\s*', r'\1', css)
    css = re.sub(r';}', '}', css)
    return css.strip()


# ---------------------------------------------------------------- catalog model
cats = {c['id']: c for c in catalog['categories']}
kids = {}
for c in catalog['categories']:
    kids.setdefault(c['parent'], []).append(c['id'])


def descendants(cid):
    out = {cid}
    for k in kids.get(cid, []):
        out |= descendants(k)
    return out


products = sorted(catalog['products'], key=lambda p: order.get(p['id'], 10 ** 6))
by_path = {p['path']: p for p in products}
cat_by_path = {c['path']: c for c in catalog['categories']}
cat_products = {}
for c in catalog['categories']:
    ds = descendants(c['id'])
    cat_products[c['id']] = [p for p in products if set(p['cats']) & ds]
cat_count = {cid: len(v) for cid, v in cat_products.items()}

def catlinks(p):
    return [{'name': cats[c]['name'], 'path': cats[c]['path']} for c in p['cats'] if c in cats]


def primary_cat(p):
    # deepest category the product sits in
    best = None
    for c in p['cats']:
        if c not in cats:
            continue
        depth = 0
        x = cats[c]
        while x['parent']:
            depth += 1
            x = cats[x['parent']]
        if best is None or depth > best[0]:
            best = (depth, c)
    return best[1] if best else None


def thumb_of(src):
    return images.variant(src, 430, 430) if src else ''


def discount(p):
    pr = p['price']
    best = 0
    if p['type'] == 'variable':
        for v in p['variations']:
            if v.get('regular') and v.get('price') is not None and v['regular'] > v['price']:
                best = max(best, (v['regular'] - v['price']) / v['regular'])
    elif pr.get('on_sale') and pr.get('regular') and pr.get('price') is not None and pr['regular'] > pr['price']:
        best = (pr['regular'] - pr['price']) / pr['regular']
    return round(best * 100) if best >= 0.01 else 0


def card_model(p):
    imgs = p['images']
    return {
        'id': p['id'], 'name': p['name'], 'path': p['path'],
        'thumb': thumb_of(imgs[0]['src']) if imgs else '',
        'thumb2': thumb_of(imgs[1]['src']) if len(imgs) > 1 else '',
        'alt': (imgs[0]['alt'] or p['name']) if imgs else p['name'],
        'catlinks': catlinks(p), 'price_html': price_html(p['price'], p['type'] == 'variable'),
        'price_short': price_short(p), 'badge': discount(p),
        'catname': cats[primary_cat(p)]['name'] if primary_cat(p) else '',
    }


cards = {p['id']: card_model(p) for p in products}


def search_index():
    """Shared JSON for load-more, sorting and search (one fetch, cached by the browser)."""
    rows = []
    for p in products:
        cm = cards[p['id']]
        rows.append({
            'i': p['id'], 'n': p['name'], 'u': p['path'], 't': cm['thumb'], 't2': cm['thumb2'], 'a': cm['alt'],
            'c': p['cats'], 'p': low_price(p), 'd': p.get('date') or '', 's': p.get('sku') or '',
            'h': cm['price_short'], 'b': cm['badge'], 'cn': cm['catname'],
        })
    cl = {c['id']: [c['name'], c['path']] for c in catalog['categories']}
    tree = {c['id']: sorted(descendants(c['id'])) for c in catalog['categories']}
    return {'p': rows, 'c': cl, 'd': tree}


# ---------------------------------------------------------------- templates
env = Environment(loader=FileSystemLoader(os.path.join(ROOT, 'templates')), autoescape=select_autoescape(['html']),
                  trim_blocks=False, lstrip_blocks=False)


PHOSPHOR = J('assets/phosphor.json')


def ico(name, cls=''):
    from markupsafe import Markup
    return Markup(f'<svg class="ico{(" " + cls) if cls else ""}" viewBox="0 0 256 256" fill="currentColor" aria-hidden="true" focusable="false">{PHOSPHOR[name]}</svg>')


env.globals['ico'] = ico

CONTACTS = [
    {'market': 'ليبيا والعراق والخليج', 'person': 'الآنسة هبة', 'phone': '+90 551 005 90 96', 'wa': '905510059096'},
    {'market': 'سوريا', 'person': 'عمار رجب', 'phone': '+963 980 243 748', 'wa': '963980243748'},
    {'market': 'إسطنبول', 'person': 'الأستاذ سامر', 'phone': '+90 507 488 63 77', 'wa': '905074886377'},
]
MEGA_BLURB = 'منتجات بشعار مؤسستك بأسعار واضحة وكود لكل منتج.'


def mega_model():
    out = []
    for it in nav['cat_nav']:
        c = cat_by_path.get(it['path'])
        if not c or cat_count.get(c['id'], 0) == 0:
            continue

        def kids(items):
            res = []
            for k in items:
                kc = cat_by_path.get(k['path'])
                if not kc or cat_count.get(kc['id'], 0) == 0:
                    continue
                res.append({'name': kc['name'], 'path': kc['path'], 'children': kids(k.get('children', []))})
            return res
        img = c.get('image') or ''
        if not img and cat_products.get(c['id']):
            first = cat_products[c['id']][0]
            img = first['images'][0]['src'] if first['images'] else ''
        out.append({'name': c['name'], 'path': c['path'], 'count': cat_count[c['id']], 'children': kids(it.get('children', [])),
                    'img': thumb_of(img) if img else '', 'blurb': MEGA_BLURB, 'id': c['id']})
    return out


NAV_PAGES = [m for m in nav['menu'] if m['path'] not in ('/', '/shop/')]
MEGA = mega_model()


def render(tpl, out_path, **ctx):
    base = dict(nav=nav, icons=icons, social=SOCIAL, asset=lambda n: ASSETS[n], tracking=True, body_class='',
                full=False, search_redirect=False, path='', active_menu='', mega=MEGA, nav_pages=NAV_PAGES,
                contacts=CONTACTS, total_products=len(products))
    base.update(ctx)
    html = env.get_template(tpl).render(**base)
    write(out_path, html)


def active_menu_for(path):
    if path == '/':
        return '/'
    for m in nav['menu']:
        if m['path'] != '/' and path.startswith(m['path']):
            return m['path']
    if path.startswith('/product'):
        return '/shop/'
    return ''


# ---------------------------------------------------------------- footer partial (verbatim markup from the old site)
def build_footer():
    s = BeautifulSoup(open(os.path.join(ROOT, 'data/ref/footer.html'), encoding='utf-8').read(), 'lxml')
    f = s.select_one('footer.mdk-footer')
    seen = set()
    for a in f.select('.mdk-social a'):
        names = [c[7:] for c in (a.get('class') or []) if c.startswith('social-')]
        key = {'twitter': 'x'}.get(names[0], names[0]) if names else ''
        if key in seen or key not in icons:
            a.decompose()
            continue
        seen.add(key)
        a['class'] = ['wd-social-icon', f'social-{key}']
        a.clear()
        a.append(BeautifulSoup(f'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="{icons[key]}"/></svg>', 'html.parser'))
        a['aria-label'] = next(x['label'] for x in SOCIAL if x['icon'] == key)
    for w in f.select('.mdk-social .wd-social-icons'):
        w.unwrap()
    html = relink(str(f))
    write(os.path.join(ROOT, 'templates/partials/footer.html'),
          '<footer class="wd-footer footer-container"><div class="mdk-fwrap">' + html + '</div></footer>\n')


# ---------------------------------------------------------------- pages
DROP_PAGES = {'/cart/', '/checkout/', '/my-account/', '/wishlist/'}


def widget_to_html(kind, html):
    s = BeautifulSoup(html, 'html.parser')
    box = s.select_one('.elementor-widget-container') or s
    for el in box.select('.wd-social-icons'):
        el.decompose()
    return str(box.decode_contents()) if hasattr(box, 'decode_contents') else str(box)


def home_products_tabs(raw, head=''):
    s = BeautifulSoup(raw, 'html.parser')
    tabs = []
    for li in s.select('.products-tabs-title li'):
        atts = json.loads(li['data-atts'])
        cid = int(atts['taxonomies'][0])
        plist = cat_products.get(cid, [])
        by_date = atts.get('orderby') == 'date'
        if by_date:
            plist = sorted(plist, key=lambda p: (p.get('date') or '', p['id']), reverse=True)
        tabs.append({'name': li.get_text(strip=True), 'cat': cats[cid], 'order': 'date' if by_date else 'menu_order',
                     'items': [cards[p['id']] for p in plist[:8]]})
    return env.get_template('partials/ptabs.html').render(tabs=tabs, head=head)


def build_pages():
    out = []
    for pg in pages_raw:
        path = pg['path']
        if path in DROP_PAGES or path == '/shop/':
            continue
        parts = []
        designed = False
        for x in pg['parts']:
            if x[0] == 'html' and path == '/' and REEL and 'class="mdk-story"' in x[1]:
                parts.append(reel_html(x[1]))
                designed = True
            elif x[0] == 'html':
                parts.append(x[1])
                designed = designed or 'mdk' in x[1]
            elif x[0] == 'content':
                parts.append(x[1])
            elif x[0] == 'widget':
                if x[1] == 'wd_products_tabs.default':
                    head = parts.pop() if parts and 'mdk-head' in parts[-1] and len(parts[-1]) < 600 else ''
                    parts.append(home_products_tabs(x[2], head))
                elif x[1] == 'wd_title.default':
                    continue  # becomes the page h1 below
                elif x[1] == 'image.default':
                    s = BeautifulSoup(x[2], 'html.parser')
                    img = s.find('img')
                    if img:
                        for k in ('srcset', 'sizes', 'class'):
                            img.attrs.pop(k, None)
                        img['loading'] = 'lazy'
                        parts.insert(0, f'<figure class="doc-fig">{img}</figure>')
                else:
                    parts.append(widget_to_html(x[1], x[2]))
        body = relink('\n'.join(parts))
        h1 = pg['title'].replace('​', '').strip()
        common = dict(seo=pg['seo'], path=path, active_menu=active_menu_for(path), body=body,
                      search_redirect=(path == '/'))
        if designed:
            render('page.html', file_for(path), full=True, body_class='page', **common)
        else:
            render('doc.html', file_for(path), h1=h1, body_class='page page-doc', **common)
        out.append(path)
    return out


# ---------------------------------------------------------------- shop + categories
def search_cat_options():
    out = []

    def walk(items, depth):
        for it in items:
            c = cat_by_path.get(it['path'])
            if c:
                out.append({'id': c['id'], 'label': ('— ' * depth) + c['name']})
            walk(it.get('children', []), depth + 1)
    walk(nav['cat_nav'], 0)
    return out


SEARCH_CATS = None


def nav_item_count(item):
    c = cat_by_path.get(item['path'])
    return cat_count.get(c['id'], 0) if c else 0


def top_cats(current):
    chain = []
    x = current
    while x:
        chain.append(x['id'])
        x = cats.get(x['parent']) if x['parent'] else None
    out = []
    for it in nav['cat_nav']:
        c = cat_by_path.get(it['path'])
        if not c or cat_count.get(c['id'], 0) == 0:
            continue
        cls = []
        if current and c['id'] == current['id']:
            cls += ['current-cat', 'wd-active']
        elif current and c['id'] in chain:
            cls += ['current-cat-parent', 'current-cat-ancestor', 'wd-active']
        out.append({'name': c['name'], 'path': c['path'], 'count': cat_count[c['id']], 'cls': ' '.join(cls),
                    'current': bool(current and c['id'] == current['id']),
                    'ancestor': bool(current and c['id'] in chain and c['id'] != current['id'])})
    return out


def find_nav(path, items=None):
    for it in (items if items is not None else nav['cat_nav']):
        if it['path'] == path:
            return it
        r = find_nav(path, it.get('children', []))
        if r:
            return r
    return None


def sub_rows(current):
    """Same rows the old mdk-subnav script built from the category menu."""
    if not current:
        return []
    chain = []
    x = current
    while x:
        chain.insert(0, x)
        x = cats.get(x['parent']) if x['parent'] else None
    chain_ids = {c['id'] for c in chain}
    rows = []
    for c in chain:
        it = find_nav(c['path'])
        kids_nav = [k for k in (it or {}).get('children', []) if cat_by_path.get(k['path'])]
        if not kids_nav:
            continue
        chips = [{'name': 'الكل', 'path': c['path'], 'count': cat_count.get(c['id'], 0), 'on': c['id'] == current['id'],
                  'current': c['id'] == current['id'], 'img': ''}]
        for k in kids_nav:
            kc = cat_by_path[k['path']]
            if cat_count.get(kc['id'], 0) == 0:
                continue
            img = kc.get('image') or ''
            if not img and cat_products.get(kc['id']):
                f0 = cat_products[kc['id']][0]
                img = f0['images'][0]['src'] if f0['images'] else ''
            chips.append({'name': kc['name'], 'path': kc['path'], 'count': cat_count[kc['id']], 'on': kc['id'] in chain_ids,
                          'current': kc['id'] == current['id'], 'img': images.variant(img, 80, 80) if img else ''})
        rows.append({'name': c['name'], 'chips': chips})
    for r in rows[1:]:
        for k in r['chips']:
            k['img'] = ''
    return rows


def build_listing(base_path, h1, seo, crumbs, plist, current=None, about=''):
    total = len(plist)
    pages = max(1, -(-total // PER_PAGE))
    made = []
    for page in range(1, pages + 1):
        items = [cards[p['id']] for p in plist[(page - 1) * PER_PAGE: page * PER_PAGE]]
        url = base_path + (f'page/{page}/' if page > 1 else '')
        render('shop.html', file_for(url), seo=seo_paged(seo, base_path, page, pages) if pages > 1 else seo,
               path=url, active_menu='/shop/', h1=h1, crumbs=crumbs, items=items, total=total, page=page, pages=pages,
               per_page=PER_PAGE, page_url=lambda n: base_path + (f'page/{n}/' if n > 1 else ''),
               count_text=count_text(total, page), topcats=top_cats(current), subrows=sub_rows(current),
               search_cats=SEARCH_CATS, cat_id=current['id'] if current else None,
               about=about if page == 1 else '', body_class='archive woocommerce-shop' + (' is-shop' if not current else ''))
        made.append(url)
    return made


def build_shop():
    global SEARCH_CATS
    SEARCH_CATS = search_cat_options()
    made = []
    shop = next(p for p in pages_raw if p['path'] == '/shop/')
    about = ''
    for x in shop['parts']:
        if x[0] == 'widget' and x[1] == 'wd_shop_archive_archive_description.default':
            about = relink(widget_to_html(x[1], x[2]))
    made += build_listing('/shop/', 'كل المنتجات', shop['seo'], [('الرئيسية', '/'), ('كل المنتجات', '/shop/')],
                          products, None, about)
    for c in catalog['categories']:
        crumbs = [(t, p) for t, p in c['breadcrumbs']] + [(c['name'], c['path'])]
        about = f'<div class="term-description">{relink(c["description"])}</div>' if c['description'].strip() else ''
        made += build_listing(c['path'], c['name'], c['seo'], crumbs, cat_products[c['id']], c, about)
    return made


# ---------------------------------------------------------------- products
def norm(s):
    return re.sub(r'[\s\-_]+', ' ', (s or '')).strip().lower()


def quote_lines(title, sel_rows, var):
    lines = ['مرحباً مدارك، أريد عرض سعر:', title] + sel_rows
    if var:
        d = BeautifulSoup(var.get('desc') or '', 'html.parser').get_text()
        m = re.search(r'MD-[A-Z]{2}-\d{4}-\d{2}', d)
        code = m.group(0) if m else (var.get('sku') or '')
        if code:
            lines.append('رقم الخيار: ' + code)
        if var.get('price') is not None:
            lines.append('السعر المعروض: $' + fmt_num(var['price']))
    return lines


def fmt_num(x):
    return ('%.2f' % x).rstrip('0').rstrip('.') if x != int(x) else str(int(x))


def wa(lines):
    return f'https://wa.me/{WA_SALES}?text=' + up.quote('\n'.join(lines), safe='')


def gallery_of(p):
    out = []
    for im in p['images']:
        src = im['src']
        main = images.fit(src, 700)
        th = images.fit(src, 244)
        out.append({'full': images.local_url(src), 'main': main['url'], 'w': main['w'], 'h': main['h'],
                    'thumb': th['url'], 'tw': th['w'], 'th': th['h'], 'alt': im['alt'] or p['name']})
    return out


def product_model(p, idx):
    variable = p['type'] == 'variable' and p['form']
    pc = primary_cat(p)
    siblings = cat_products.get(pc, products) if pc else products
    pos = next((i for i, x in enumerate(siblings) if x['id'] == p['id']), None)
    prev = siblings[pos - 1] if pos else None
    nxt = siblings[pos + 1] if pos is not None and pos + 1 < len(siblings) else None
    related = [cards[by_path[r]['id']] for r in p['related'] if r in by_path and by_path[r]['id'] != p['id']][:8]
    m = {
        'id': p['id'], 'name': p['name'], 'path': p['path'], 'sku': p['sku'], 'crumbs': p['breadcrumbs'],
        'price_html': price_html(p['price'], p['type'] == 'variable'), 'short': relink(p['short']),
        'price_big': price_big(p),
        'catlinks': catlinks(p), 'gallery': gallery_of(p), 'related': related,
        'prev': {'name': prev['name'], 'path': prev['path']} if prev else None,
        'next': {'name': nxt['name'], 'path': nxt['path']} if nxt else None,
        'back': cats[pc]['path'] if pc else '/shop/',
        'tabs': [dict(t, html=clean_specs(t['html']) if t['id'] == 'tab-additional_information' else relink(t['html']),
                      title={'معلومات إضافية': 'المواصفات'}.get(t['title'], t['title'])) for t in p['tabs']],
        'form': None, 'sel': None,
    }
    url = SITE + p['path']
    if variable:
        rows = p['form']
        keys = [norm(r['name']) for r in rows]
        labels = [norm(r['label']) for r in rows]
        vs = []
        for v in p['variations']:
            a = {norm(k): val for k, val in v['attrs'].items()}
            vals = []
            for k, lb in zip(keys, labels):
                vals.append(a.get(k, a.get(lb, '')))
            vimg = ''
            if v.get('image') and p['images'] and images.local_url(v['image']) != images.local_url(p['images'][0]['src']):
                vimg = images.fit(v['image'], 700)['url']
            vs.append({'a': vals, 'p': v['price'], 's': v.get('sku') or '', 'd': v.get('desc') or '', 'img': vimg,
                       'pb': money_short(v['price']) if v['price'] is not None else ''})
        defaults = [r['default'] for r in rows]
        sel = None
        if all(defaults):
            for v in vs:
                if all(x == '' or x == d for x, d in zip(v['a'], defaults)):
                    sel = v
                    break
        m['form'] = rows
        m['sel'] = sel
        m['pv_json'] = json.dumps({'rows': [r['label'] for r in rows], 'v': vs, 'title': p['name'], 'url': url,
                                   'phone': WA_SALES}, ensure_ascii=False).replace('</', '<\\/')
        sel_rows = [f'{r["label"]}: {next(o[1] for o in r["options"] if o[0] == d)}' for r, d in zip(rows, defaults)] if sel else []
        lines = quote_lines(p['name'], sel_rows, {'desc': sel['d'], 'sku': sel['s'], 'price': sel['p']} if sel else None)
        m['quote_ready'] = bool(sel)
        m['quote_label'] = 'اطلب عرض سعر لهذا الخيار عبر واتساب' if sel else 'اطلب عرض سعر عبر واتساب'
    else:
        lines = quote_lines(p['name'], [], None)
        m['quote_ready'] = True
        m['quote_label'] = 'اطلب عرض سعر عبر واتساب'
    m['quote_href'] = wa(lines + [url])
    m['quote_sy'] = f'https://wa.me/963980243748?text=' + up.quote('\n'.join(lines + [url]), safe='')
    m['show_quote'] = bool(variable) or 'md-quote' not in (p['short'] or '')
    return m


def clean_specs(html):
    """WooCommerce attribute table -> label + value chips."""
    s = BeautifulSoup(html, 'html.parser')
    rows = []
    for tr in s.select('tr'):
        th, td = tr.find('th'), tr.find('td')
        if not th or not td:
            continue
        vals = [x.get_text(' ', strip=True) for x in td.select('.wd-attr-term')] or [v.strip() for v in td.get_text(' ', strip=True).split(',') if v.strip()]
        rows.append((th.get_text(' ', strip=True), vals))
    if not rows:
        return html
    out = ['<dl class="m-specs">']
    for lab, vals in rows:
        out.append(f'<div><dt>{H.escape(lab)}</dt><dd>' + ''.join(f'<span>{H.escape(v)}</span>' for v in vals) + '</dd></div>')
    out.append('</dl>')
    return ''.join(out)


def fb_id(p):
    return f"{p['sku']}_{p['id']}" if p.get('sku') else f"wc_post_id_{p['id']}"


def build_products():
    made = []
    for i, p in enumerate(products):
        m = product_model(p, i)
        pc = primary_cat(p)
        track = {'id': p['id'], 'name': p['name'], 'value': low_price(p) or 0, 'fb_id': fb_id(p),
                 'category': cats[pc]['name'] if pc else ''}
        render('product.html', file_for(p['path']), seo=p['seo'], p=m, path=p['path'], active_menu='/shop/',
               body_class='single-product product-template-default woocommerce', track_product=track)
        made.append(p['path'])
    return made


# ---------------------------------------------------------------- sitemaps, robots, redirects, feeds
def live_lastmods():
    lm = {}
    for f in ('page-sitemap.xml', 'product-sitemap.xml', 'product_cat-sitemap.xml'):
        p = os.path.join(ROOT, 'data/ref', f)
        if os.path.exists(p):
            t = open(p, encoding='utf-8').read()
            for loc, mod in re.findall(r'<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', t):
                lm[loc] = mod
    return lm


def indexable(seo):
    return not any('noindex' in t for t in seo['tags'] if 'name="robots"' in t)


def build_sitemaps(page_paths):
    lm = live_lastmods()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
    head = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" '
            'xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd '
            'http://www.google.com/schemas/sitemap-image/1.1 http://www.google.com/schemas/sitemap-image/1.1/sitemap-image.xsd" '
            'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')

    def url_xml(loc, mod, imgs=()):
        x = f'\t<url>\n\t\t<loc>{loc}</loc>\n\t\t<lastmod>{mod}</lastmod>\n'
        for i in imgs:
            x += f'\t\t<image:image>\n\t\t\t<image:loc>{H.escape(i)}</image:loc>\n\t\t</image:image>\n'
        return x + '\t</url>\n'

    files = {}
    # pages (home first, as Yoast does)
    pg = {p['path']: p for p in pages_raw}
    body = ''
    order_pages = ['/'] + [p for p in page_paths if p != '/'] + ['/shop/']
    for path in order_pages:
        p = pg.get(path)
        if not p or not indexable(p['seo']):
            continue
        loc = SITE + path
        body += url_xml(loc, lm.get(loc, now))
    files['page-sitemap.xml'] = head + body + '</urlset>\n'
    body = ''
    for p in products:
        if not indexable(p['seo']):
            continue
        loc = SITE + p['path']
        imgs = [SITE + images.local_url(i['src']) for i in p['images']]
        body += url_xml(loc, lm.get(loc, now), imgs)
    files['product-sitemap.xml'] = head + body + '</urlset>\n'
    body = ''
    for c in catalog['categories']:
        if cat_count.get(c['id'], 0) == 0 or not indexable(c['seo']):
            continue
        loc = SITE + c['path']
        body += url_xml(loc, lm.get(loc, now))
    files['product_cat-sitemap.xml'] = head + body + '</urlset>\n'
    idx = '<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for name, xml in files.items():
        mods = re.findall(r'<lastmod>([^<]+)</lastmod>', xml)
        idx += f'\t<sitemap>\n\t\t<loc>{SITE}/{name}</loc>\n\t\t<lastmod>{max(mods) if mods else now}</lastmod>\n\t</sitemap>\n'
        write(os.path.join(OUT, name), xml)
    write(os.path.join(OUT, 'sitemap_index.xml'), idx + '</sitemapindex>\n')
    return {k: v.count('<url>') for k, v in files.items()}


def build_robots():
    write(os.path.join(OUT, 'robots.txt'),
          'User-agent: *\nDisallow: /search/\nDisallow: /*?add-to-cart=\n\nSitemap: ' + SITE + '/sitemap_index.xml\n')


def build_redirects():
    lines = []
    seen = set()
    for src, dst in J('data/redirects_wp.json'):
        # match both the raw UTF-8 path and the percent-encoded form browsers send
        for s in (src, up.quote(up.unquote(src), safe='/').lower(), up.quote(up.unquote(src), safe='/')):
            if s in seen or ' ' in s:
                continue
            seen.add(s)
            lines.append(f'{s} {dst} 301')
    # WordPress-only pages that no longer exist
    for src, dst in [('/cart/', '/shop/'), ('/checkout/', '/shop/'), ('/my-account/', '/'), ('/my-account/*', '/'),
                     ('/wishlist/', '/shop/'), ('/woodmart_slider/*', '/'), ('/wp-admin/*', '/'), ('/wp-login.php', '/'),
                     ('/feed/', '/'), ('/comments/feed/', '/'), ('/sitemap.xml', '/sitemap_index.xml'),
                     ('/wp-sitemap.xml', '/sitemap_index.xml'), ('/product_tag/*', '/shop/'), ('/category/*', '/'),
                     ('/mailpoet_page-sitemap.xml', '/sitemap_index.xml'), ('/woodmart_slider-sitemap.xml', '/sitemap_index.xml')]:
        lines.append(f'{src} {dst} 301')
    write(os.path.join(OUT, '_redirects'), '\n'.join(lines) + '\n')
    return len(lines)


def build_headers():
    write(os.path.join(OUT, '_headers'), """https://:project.pages.dev/*
  X-Robots-Tag: noindex

/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: interest-cohort=()

/assets/*
  Cache-Control: public, max-age=31536000, immutable

/wp-content/uploads/*
  Cache-Control: public, max-age=2592000

/data/*
  Cache-Control: public, max-age=600
""")


def build_feeds():
    """Product feeds for Meta (Commerce Manager) and Google Merchant Center, RSS 2.0 with g: fields."""
    def item(p, gid, google):
        imgs = [SITE + images.local_url(i['src']) for i in p['images']]
        pc = primary_cat(p)
        desc = BeautifulSoup(p['short'] or p['description'] or '', 'html.parser').get_text(' ', strip=True) or p['name']
        price = low_price(p)
        if price is None:
            return ''
        x = ['<item>', f'<g:id>{H.escape(gid)}</g:id>', f'<g:title>{H.escape(p["name"][:150])}</g:title>',
             f'<g:description>{H.escape(desc[:4900])}</g:description>', f'<g:link>{SITE}{p["path"]}</g:link>',
             f'<g:image_link>{H.escape(imgs[0]) if imgs else ""}</g:image_link>']
        for extra in imgs[1:10]:
            x.append(f'<g:additional_image_link>{H.escape(extra)}</g:additional_image_link>')
        x += ['<g:availability>in stock</g:availability>', '<g:condition>new</g:condition>',
              f'<g:price>{price:.2f} USD</g:price>', '<g:brand>Madarek</g:brand>',
              '<g:identifier_exists>no</g:identifier_exists>']
        if p.get('sku'):
            x.append(f'<g:mpn>{H.escape(p["sku"])}</g:mpn>')
        if pc:
            trail = []
            c = cats[pc]
            while c:
                trail.insert(0, c['name'])
                c = cats.get(c['parent']) if c['parent'] else None
            x.append(f'<g:product_type>{H.escape(" > ".join(trail))}</g:product_type>')
        if not google:
            x.append(f'<g:item_group_id>{p["id"]}</g:item_group_id>')
        x.append('</item>')
        return '\n'.join(x)

    for name, google in (('google', True), ('meta', False)):
        items = [item(p, f'gla_{p["id"]}' if google else fb_id(p), google) for p in products]
        xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n<channel>\n'
               f'<title>مطبعة مدارك — المنتجات</title>\n<link>{SITE}/shop/</link>\n<description>Madarek product feed</description>\n'
               + '\n'.join(i for i in items if i) + '\n</channel>\n</rss>\n')
        write(os.path.join(OUT, 'feeds', f'{name}.xml'), xml)


# ---------------------------------------------------------------- main
def main():
    global ASSETS
    if os.path.isdir(OUT):
        for name in os.listdir(OUT):
            if name == 'wp-content' and NO_MEDIA:
                continue
            p = os.path.join(OUT, name)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(OUT, exist_ok=True)
    ASSETS = build_assets()
    made_pages = build_pages()
    made_shop = build_shop()
    made_products = build_products()
    render('search.html', os.path.join(OUT, 'search/index.html'),
           seo={'title': 'البحث | مطبعة مدارك', 'tags': ['<meta name="robots" content="noindex, follow">'], 'ld': []},
           path='/search/', body_class='search-page')
    render('404.html', os.path.join(OUT, '404.html'),
           seo={'title': 'الصفحة غير موجودة | مطبعة مدارك', 'tags': ['<meta name="robots" content="noindex, follow">'], 'ld': []},
           path='/404', body_class='error404')
    write(os.path.join(OUT, 'data/catalog.json'), json.dumps(search_index(), ensure_ascii=False, separators=(',', ':')))
    sm = build_sitemaps(made_pages)
    build_robots()
    nred = build_redirects()
    build_headers()
    build_feeds()
    nimg = images.export(OUT, copy_media=not NO_MEDIA)
    print(f'pages {len(made_pages)} · listing pages {len(made_shop)} · products {len(made_products)} · '
          f'sitemaps {sm} · redirects {nred} · images {nimg}')


ASSETS = {}
if __name__ == '__main__':
    main()
