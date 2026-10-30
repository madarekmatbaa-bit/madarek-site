#!/usr/bin/env python3
"""New products and the offers section (Ammar, 31 Oct 2026):
«الفواحات والألبسة اعمل لهم منتجات جديدة وانشرهم … وعمل مكان للعروض … 3 أشياء مع بعض ولا مجموعة مطبوعات».

Writes the products into content/catalog.json (replacing earlier copies by SKU), the offers category, the menu
entries, and the pictures under media/wp-content/uploads/2026/10/. Run it again after editing the lists below.

Prices:
- car fragrances: $90 per 1,000 (Ammar; portal quotes 0.09 each), sizes 7×7 and 8×7 cm, one scent per 1,000.
- clothing: the price the portal quoted per piece without the logo (QUO-000094, -000150, -000162, -000084, -000079).
- offers: the New Year 2027 posts (claude/newyear-2027-offer-posts-2026-10-11.md), the Libya/site version:
  sets per piece for 100 sets without logo printing, 10% off; identity offers as posted.
"""
import json
import os
import re
import sys
import urllib.parse as up

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://www.madarekmatbaa.com'
UP = '/wp-content/uploads/2026/10/'
MEDIA = os.path.join(ROOT, 'media') + UP
SRC = os.path.join(ROOT, 'data/new-products-src')     # portal pictures fetched for these products
DATE = '2026-10-31T00:30:00'
WA = 'https://wa.me/905510059096'
BG = (237, 234, 229)
FONT = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'

OFFERS = {'id': 380, 'name': 'العروض والباقات', 'slug': 'offers', 'path': '/product-category/offers/'}

FRAGRANCE = {
    'sku': 'MD-TR-1-0966', 'name': 'فواحات سيارة مطبوعة بشعاركم', 'cats': [340, 77], 'id': 39001,
    'img': 'MD-TR-1-0966', 'kind_line': 'إكسسوارات السيارات', 'cat_path': '/product-category/promotional-ar/car-accessories/',
    'short': ('فواحات (معطرات) سيارة من كرتون معطّر، مطبوعة بالألوان بشعاركم ومقصوصة على شكل التصميم، '
              'بمقاسين 7×7 و8×7 سم، ومعها خيط للتعليق. كل 1,000 قطعة برائحة وحدة.'),
    'sizes': [('7×7 سم', 'V01'), ('8×7 سم', 'V02')],
    'qty': [1000, 2000, 3000, 5000, 10000], 'per1000': 90.0,
}

# portal code, name, price per piece (None = by quote), what it is
CLOTHES = [
    ('MD-TR-1-1003', 'بولو نص كم بشعاركم', 8.00, 'كنزة بولو بنص كم وياقة وأزرار، بألوان متعددة.'),
    ('MD-TR-1-1007', 'بولو كم طويل بشعاركم', 9.00, 'كنزة بولو بكم طويل وياقة وأزرار، بألوان متعددة.'),
    ('MD-TR-1-1002', 'تيشيرت قطن بشعاركم', None, 'تيشيرت قطن بنص كم ورقبة دائرية، بألوان متعددة.'),
    ('MD-TR-1-1005', 'هودي بغطاء رأس بشعاركم', 14.00, 'سويت شيرت بغطاء رأس وجيب أمامي، بألوان متعددة.'),
    ('MD-TR-1-1008', 'جاكيت فليس بشعاركم', 16.00, 'جاكيت فليس بسحّاب كامل، دافئ وخفيف، بألوان متعددة.'),
    ('MD-TR-1-1004', 'فيست (صدرية) بشعاركم', 13.00, 'فيست بلا أكمام بسحّاب، يناسب فرق العمل الميدانية.'),
    ('MD-TR-1-1001', 'قبعة قطن بشعاركم', 2.50, 'قبعة قطن بواجهة أمامية للشعار ومشبك خلفي للمقاس.'),
]

# code, name, regular, price, items [(name, qty or '', site sku or None)], note, picture recipe
SETS = [
    ('MD-OF-0001', 'باقة الأساسي: دفتر وقلم وميدالية', 4.69, 4.22,
     [('دفتر ملاحظات جلد حراري 13×21 سم', '', 'MD-TR-1-0684'), ('قلم حبر جاف معدن', '', 'MD-TR-1-0375'),
      ('ميدالية مفاتيح', '', None)], ('trio', ['md-tr-1-0684.jpg', 'md-tr-1-0375.jpg', 'MD-TR-1-0864'])),
    ('MD-OF-0002', 'باقة المميز: دفتر وقلم رولر وميدالية', 6.31, 5.68,
     [('دفتر ملاحظات جلد حراري 13×21 سم', '', 'MD-TR-1-0682'), ('قلم رولر معدن', '', 'MD-TR-1-0360'),
      ('ميدالية مفاتيح معدن', '', 'MD-TR-1-0871')], ('trio', ['md-tr-1-0682.jpg', 'md-tr-1-0360.jpg', 'md-tr-1-0871.jpg'])),
    ('MD-OF-0003', 'باقة VIP: دفتر وقلم وميدالية فاخرة', 8.94, 8.05,
     [('دفتر ملاحظات جلد حراري 13×21 سم', '', 'MD-TR-1-0679'), ('قلم حبر جاف معدن', '', 'MD-TR-1-0389'),
      ('ميدالية مفاتيح معدن', '', 'MD-TR-1-0854')], ('trio', ['md-tr-1-0679.jpg', 'md-tr-1-0389.jpg', 'md-tr-1-0854.jpg'])),
    ('MD-OF-0004', 'طقم هدايا فاخر بعلبة', 12.48, 11.23,
     [('طقم هدايا فاخر مع علبة', '', 'MD-TR-1-0249')], ('relabel', ['md-tr-1-0249.jpg'])),
]
IDENTITY = [
    # Syria prices from the posts of 12 Oct (Ammar 31 Oct: «الباقة أغلى من هيك … تبع سوريا»): 213 and 1,581
    ('MD-OF-0005', 'عرض الهوية البصرية: 2,500 قطعة', 213.0,
     [('ورق رسمي 100 غرام', 1000, 'ANT'), ('كرت شخصي 700 غرام', 1000, 'KART-N'), ('ظرف A4', 500, 'MD-PR-0014')],
     'شامل التصميم.', ['ant-mockup.jpg', 'kart-n-mockup.jpg', 'md-tr-2-0047-m.jpg']),
    ('MD-OF-0006', 'باقة الهوية الكاملة: 10,000 قطعة', 1581.0,
     [('ورق رسمي', 2000, 'ANT'), ('ظرف رسائل', 1000, 'ZARF'), ('ظرف A4', 500, 'MD-PR-0014'),
      ('كرت شخصي', 3000, 'KART-N'), ('بروشور مطوي', 1000, 'BRO'), ('فولدر بجيب', 1000, 'DOSYA'),
      ('دفتر سلك', 500, 'DFB'), ('كيس ورقي', 1000, 'KCN')],
     'شامل التصميم.', ['ant-mockup.jpg', 'zarf-mockup.jpg', 'md-tr-2-0047-m.jpg', 'kart-n-mockup.jpg', None,
                       'bro-mockup.jpg', 'dosya-mockup.jpg', 'dfb-mockup.jpg', 'kcn-mockup.jpg']),
]


# ---------------------------------------------------------------- helpers
def slug_path(name, code=None):
    s = name.replace('(', ' ').replace(')', ' ').replace(':', ' ').replace('،', ' ').replace(',', '')
    s = re.sub(r'\s+', '-', s.strip())
    if code:
        s += '-' + code.lower()
    q = up.quote(s.lower(), safe='-')
    return '/product/' + re.sub(r'%[0-9A-F]{2}', lambda m: m.group(0).lower(), q) + '/'


def money(x):
    return f'${x:,.2f}'


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def label(img, code, scale=1.0):
    """The code at the bottom of every product picture: blue dot + navy code."""
    d = ImageDraw.Draw(img)
    w = img.size[0] / 900 * scale
    d.rectangle([int(30 * w), int(822 * w), int(340 * w), int(872 * w)], fill=BG)
    f = ImageFont.truetype(FONT, int(16.5 * w))
    cx, cy = 51 * w, 845 * w
    d.ellipse([cx - 5 * w, cy - 5 * w, cx + 5 * w, cy + 5 * w], fill=(50, 99, 219))
    x = 66 * w
    for ch in code:
        d.text((x, cy), ch, font=f, fill=(13, 36, 76), anchor='lm')
        x += d.textlength(ch, font=f) + 1.6 * w


def frame():
    """The empty brand frame (cream, waves, logo) from a text-card picture."""
    a = np.asarray(Image.open(MEDIA + 'md-tr-1-0218.jpg').convert('RGB')).copy()
    a[114:472, 380:895] = BG
    a[820:875, 25:340] = BG
    return a


FRAME = None


def cutout(path):
    """Product only (RGBA), by difference with the empty frame."""
    im = Image.open(path).convert('RGB').resize((900, 900), Image.LANCZOS)
    a = np.asarray(im).astype(int)
    d = np.abs(a - FRAME.astype(int)).max(axis=2)
    m = d > 30
    m[815:885, 20:345] = False
    m[0:115, 640:900] = False
    m = ndimage.binary_opening(m, structure=np.ones((3, 3)), iterations=1)
    lab, n = ndimage.label(m)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        keep = [i + 1 for i, s in enumerate(sizes) if s > max(400, sizes.max() * 0.02)]
        m = np.isin(lab, keep)
    m = ndimage.binary_fill_holes(ndimage.binary_closing(m, iterations=2))
    alpha = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    rgba = im.convert('RGBA')
    rgba.putalpha(alpha)
    return rgba.crop(rgba.getbbox())


def place(canvas, item, box, shadow=True):
    x0, y0, x1, y1 = box
    w, h = item.size
    s = min((x1 - x0) / w, (y1 - y0) / h)
    it = item.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    px = x0 + ((x1 - x0) - it.size[0]) // 2
    py = y0 + ((y1 - y0) - it.size[1]) // 2
    if shadow:
        sh = Image.new('RGBA', it.size, (13, 36, 76, 0))
        sh.putalpha(it.split()[3].point(lambda v: int(v * 0.16)))
        sh = sh.filter(ImageFilter.GaussianBlur(10))
        canvas.alpha_composite(sh, (px + 6, py + 12))
    canvas.alpha_composite(it, (px, py))


def portal_img(code):
    return os.path.join(SRC, code + '.webp')


SIZES = {}


def save(img, name):
    img.convert('RGB').save(MEDIA + name, 'JPEG', quality=90)
    SIZES[SITE + UP + name] = img.size[0]
    return SITE + UP + name


def img_trio(code, files):
    c = Image.fromarray(FRAME).convert('RGBA')
    parts = [cutout(MEDIA + f if f.endswith('.jpg') else portal_img(f)) for f in files]
    place(c, parts[0], (70, 150, 500, 760))
    place(c, parts[1], (520, 130, 850, 500))
    place(c, parts[2], (540, 480, 850, 800))
    label(c, code)
    return save(c, code.lower() + '.jpg')


def hang_tag(w, h, fill, angle):
    """A printed car fragrance on its string: card with rounded corners, logo, waves, hole."""
    L = Image.new('RGBA', (w + 120, h + 340), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    cx, top = (w + 120) // 2, 250
    d.line([(cx, 0), (cx, top + 34)], fill=(150, 158, 175, 255), width=3)
    card = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, w - 1, h - 1], 34, fill=fill)
    for k in range(4):
        y0 = h * .62 + k * 14
        pts = [(x, y0 + 14 * np.sin(x / w * 3.2 + k * .4)) for x in range(0, w + 1, 2)]
        cd.line(pts, fill=(80, 196, 200, 150), width=2)
    lg = white_logo(int(w * .56))
    card.alpha_composite(lg, ((w - lg.size[0]) // 2, int(h * .30)))
    cd.ellipse([w // 2 - 13, 22, w // 2 + 13, 48], fill=(0, 0, 0, 0))
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 34, fill=255)
    ImageDraw.Draw(m).ellipse([w // 2 - 13, 22, w // 2 + 13, 48], fill=0)
    card.putalpha(Image.fromarray(np.minimum(np.asarray(card.split()[3]), np.asarray(m))))
    sh = Image.new('RGBA', card.size, (13, 36, 76, 0))
    sh.putalpha(card.split()[3].point(lambda v: int(v * .22)))
    L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)), (60 + 10, top + 16))
    L.alpha_composite(card, (60, top))
    d.ellipse([cx - 5, top + 30, cx + 5, top + 40], fill=(150, 158, 175, 255))
    return L.rotate(angle, resample=Image.BICUBIC, center=(cx, 0))


def img_fragrance(code):
    c = Image.fromarray(FRAME).convert('RGBA')
    a = hang_tag(250, 250, (13, 36, 76, 255), 4)        # 7×7 cm
    b = hang_tag(286, 250, (50, 99, 219, 255), -4)      # 8×7 cm
    c.alpha_composite(b, (40, 150))
    c.alpha_composite(a, (430, 118))
    label(c, code)
    return save(c, code.lower() + '-mockup.jpg')


def img_relabel(code, src, name=None):
    im = Image.open(src).convert('RGB')
    label(im, code)
    return save(im, (name or code.lower()) + '.jpg')


def rounded(im, r):
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], r, fill=255)
    out = im.convert('RGBA')
    out.putalpha(m)
    return out


def tile(name, size):
    im = Image.open(MEDIA + name).convert('RGB')
    w = im.size[0]
    im = im.crop((int(w * .06), int(w * .12), int(w * .94), int(w * .88)))   # leave out logo and code
    s = min(im.size)
    im = im.crop(((im.size[0] - s) // 2, (im.size[1] - s) // 2, (im.size[0] + s) // 2, (im.size[1] + s) // 2))
    return rounded(im.resize((size, size), Image.LANCZOS), 18)


def white_logo(width):
    a = np.asarray(Image.fromarray(FRAME).crop((715, 28, 870, 112)).convert('L')).astype(int)
    m = np.clip((200 - a) * 3, 0, 255).astype(np.uint8)
    lg = Image.new('RGBA', (m.shape[1], m.shape[0]), (255, 255, 255, 255))
    lg.putalpha(Image.fromarray(m))
    lg = lg.crop(lg.getbbox())
    return lg.resize((width, int(lg.size[1] * width / lg.size[0])), Image.LANCZOS)


def logo_tile(size):
    t = Image.new('RGBA', (size, size), (13, 36, 76, 255))
    lg = white_logo(int(size * .58))
    t.alpha_composite(lg, ((size - lg.size[0]) // 2, (size - lg.size[1]) // 2))
    return rounded(t, 18)


def img_identity(code, files):
    c = Image.fromarray(FRAME).convert('RGBA')
    tiles = []
    if len(files) == 3:
        size, gap = 300, 20
        tiles = [(tile(files[0], size), (450 + gap // 2, 140)), (tile(files[1], size), (450 - gap // 2 - size, 140)),
                 (tile(files[2], size), (300, 140 + size + gap))]
    else:
        size, gap, x0, y0 = 200, 16, 134, 170
        for i, f in enumerate(files):
            x = x0 + (2 - i % 3) * (size + gap)
            y = y0 + (i // 3) * (size + gap)
            tiles.append((logo_tile(size) if f is None else tile(f, size), (x, y)))
    for t, (x, y) in tiles:
        sh = Image.new('RGBA', t.size, (13, 36, 76, 0))
        sh.putalpha(t.split()[3].point(lambda v: int(v * .14)))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9)), (x + 4, y + 10))
        c.alpha_composite(t, (x, y))
    label(c, code)
    return save(c, code.lower() + '.jpg')


# ---------------------------------------------------------------- catalog entries
WEBSITE = ORG = None


def seo_for(name, path, desc, image, crumbs, price=None, low=None, high=None, count=None, sku=None):
    w = SIZES.get(image, 900)
    url = SITE + path
    title = f'{name} | مطبعة مدارك'
    tags = [
        '<meta content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" name="robots"/>',
        f'<meta content="{esc(desc)}" name="description"/>', '<meta content="ar_AR" property="og:locale"/>',
        '<meta content="article" property="og:type"/>', f'<meta content="{esc(title)}" property="og:title"/>',
        f'<meta content="{esc(desc)}" property="og:description"/>', f'<meta content="{up.unquote(url)}" property="og:url"/>',
        '<meta content="مطبعة مدارك - Madarek Matbaa" property="og:site_name"/>',
        '<meta content="https://www.facebook.com/madarek.matbaa" property="article:publisher"/>',
        f'<meta content="{DATE}+00:00" property="article:modified_time"/>',
        f'<meta content="{image}" property="og:image"/>', f'<meta content="{w}" property="og:image:width"/>',
        f'<meta content="{w}" property="og:image:height"/>', '<meta content="image/jpeg" property="og:image:type"/>',
        '<meta content="summary_large_image" name="twitter:card"/>', '<meta content="@MadarekMatbaa" name="twitter:site"/>',
        f'<link href="{up.unquote(url)}" rel="canonical"/>']
    items = [{'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': SITE + p} for i, (n, p) in enumerate(crumbs)]
    items.append({'@type': 'ListItem', 'position': len(items) + 1, 'name': name})
    page = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'WebPage', '@id': url, 'url': url, 'name': title, 'isPartOf': {'@id': SITE + '/#website'},
         'primaryImageOfPage': {'@id': url + '#primaryimage'}, 'image': {'@id': url + '#primaryimage'}, 'thumbnailUrl': image,
         'datePublished': DATE + '+00:00', 'dateModified': DATE + '+00:00', 'description': desc,
         'breadcrumb': {'@id': url + '#breadcrumb'}, 'inLanguage': 'ar'},
        {'@type': 'ImageObject', 'inLanguage': 'ar', '@id': url + '#primaryimage', 'url': image, 'contentUrl': image,
         'width': w, 'height': w, 'caption': name},
        {'@type': 'BreadcrumbList', '@id': url + '#breadcrumb', 'itemListElement': items}, WEBSITE, ORG]}
    lds = [json.dumps(page, ensure_ascii=False)]
    if sku:
        prod = {'@context': 'https://schema.org/', '@type': 'Product', '@id': url + '#product', 'name': name, 'url': url,
                'description': desc, 'image': image, 'sku': sku, 'brand': {'@type': 'Brand', 'name': 'Madarek'}}
        seller = {'@type': 'Organization', 'name': 'مطبعة مدارك - Madarek Matbaa', 'url': SITE}
        if low is not None:
            prod['offers'] = [{'@type': 'AggregateOffer', 'lowPrice': f'{low:.2f}', 'highPrice': f'{high:.2f}', 'offerCount': count,
                               'priceValidUntil': '2027-12-31', 'availability': 'https://schema.org/InStock', 'url': url,
                               'seller': seller, 'priceCurrency': 'USD'}]
        elif price is not None:
            prod['offers'] = [{'@type': 'Offer', 'price': f'{price:.2f}', 'priceCurrency': 'USD', 'priceValidUntil': '2027-12-31',
                               'availability': 'https://schema.org/InStock', 'url': url, 'seller': seller}]
        lds.append(json.dumps(prod, ensure_ascii=False))
    return {'title': title, 'tags': tags, 'ld': lds}


ORDER_STEPS = ('<ol>\n<li>أرسل كود المنتج {code} والكمية وبلد التسليم عبر <a href="' + WA + '" target="_blank" rel="noopener">واتساب</a>.</li>\n'
               '<li>بعد ذلك أرسل شعارك أو تصميمك، أو اطلب من فريقنا تجهيزه.</li>\n'
               '<li>نرسل لك عرض السعر ونموذج التصميم للموافقة.</li>\n'
               '<li>أخيراً نبدأ التنفيذ بعد تثبيت الطلبية، ونتابع معك حتى التسليم.</li>\n</ol>')
SHIP = ('<h2>الشحن والتسليم</h2>\n<p>ننفّذ الطلبات من مراكزنا في تركيا وسوريا والصين، ثم نشحنها إلى سوريا وليبيا والعراق ودول الخليج. '
        'للتواصل المباشر زر صفحة <a href="/contact-us/">تواصل معنا</a>.</p>')


def attr_table(rows):
    out = ['<table class="woocommerce-product-attributes shop_attributes">']
    for k, v in rows:
        out.append(f'<tr class="woocommerce-product-attributes-item"><th class="woocommerce-product-attributes-item__label">{k}</th>'
                   f'<td class="woocommerce-product-attributes-item__value"><p>{v}</p></td></tr>')
    out.append('</table>')
    return '\n'.join(out)


def base_entry(pid, sku, name, path, cats, crumbs, image_urls, alt):
    return {'id': str(pid), 'name': name, 'slug': path.strip('/').split('/')[-1], 'path': path, 'sku': sku, 'type': 'simple',
            'images': [{'src': u, 'alt': alt, 'name': name} for u in image_urls], 'cats': cats, 'date': DATE,
            'menu_order': 0, 'breadcrumbs': crumbs, 'related': [], 'prev_next': [], 'form': [], 'attributes': [], 'variations': []}


def fragrance_entry():
    F = FRAGRANCE
    sku, name = F['sku'], F['name']
    path = slug_path(name)
    img = img_fragrance(sku)
    photo = img_relabel(sku, portal_img(F['img']), 'md-tr-1-0966-fawaha')
    crumbs = [['الرئيسية', '/'], ['الهدايا الدعائية', '/product-category/promotional-ar/'], [F['kind_line'], F['cat_path']]]
    e = base_entry(F['id'], sku, name, path, F['cats'], crumbs, [img, photo], name)
    e['type'] = 'variable'
    sizes, qty = F['sizes'], F['qty']
    qlab = [f'{q:,}' for q in qty]
    e['attributes'] = [{'name': 'المقاس', 'taxonomy': None, 'has_variations': True, 'terms': [s for s, _ in sizes]},
                       {'name': 'الكمية', 'taxonomy': None, 'has_variations': True, 'terms': qlab}]
    e['form'] = [{'label': 'المقاس', 'name': 'المقاس', 'options': [[s, s] for s, _ in sizes], 'default': sizes[0][0]},
                 {'label': 'الكمية', 'name': 'الكمية', 'options': [[q, q] for q in qlab], 'default': qlab[0]}]
    vid = F['id'] * 10
    for s, v in sizes:
        for q, ql in zip(qty, qlab):
            pr = round(F['per1000'] * q / 1000, 2)
            vid += 1
            e['variations'].append({'id': vid, 'attrs': {'المقاس': s, 'الكمية': ql}, 'price': pr, 'regular': pr,
                                    'sku': f'{sku}-{v}-{q}', 'image': img, 'image_alt': name,
                                    'desc': f'<p>رقم الخيار: {sku}-{v} · سعر القطعة: {pr / q:.3f}$</p>'})
    lo, hi = min(v['price'] for v in e['variations']), max(v['price'] for v in e['variations'])
    e['price'] = {'price': lo, 'regular': lo, 'sale': lo, 'min': lo, 'max': hi, 'on_sale': False}
    e['short'] = (f'<p>{F["short"]}</p>\n<p>شوف جدول الخيارات والأسعار تحت، واذكر رقم الخيار لما تطلب عرض السعر. '
                  'السعر للكمية كاملة مع الطباعة والقص، دون الشحن.</p>')
    head = ''.join(f'<th>{q}</th>' for q in qlab)
    rows = ''.join(f'<tr><td><strong>{sku}-{v}</strong></td><td>{s}</td>' +
                   ''.join(f'<td>{money(round(F["per1000"] * q / 1000, 2))}</td>' for q in qty) + '</tr>' for s, v in sizes)
    options = ('<h3>الخيارات والأسعار</h3>\n<p>كل خيار إلو رقم ثابت، اذكره لما تطلب عرض السعر. الأرقام بالجدول هي سعر الكمية كاملة '
               'بالدولار حسب عدد القطع (فوق كل عمود)، وتشمل الطباعة والقص، ولا تشمل الشحن.</p>\n'
               f'<div class="mdk-options responsive-table"><table><thead><tr><th>رقم الخيار</th><th>المقاس</th>{head}</tr></thead>'
               f'<tbody>{rows}</tbody></table></div>')
    desc = (f'<p><strong>{name}</strong> من <a href="/">مطبعة مدارك</a>: هدية صغيرة يعلّقها عميلك بسيارته، فيبقى شعارك قدامه كل يوم. '
            f'يبدأ السعر من {money(lo)} لكل 1,000 قطعة، أي 9 سنت للقطعة.</p>\n'
            f'<figure class="md-fig"><img src="{img}" alt="{esc(name)}" width="300" height="300" loading="lazy"></figure>\n'
            f'<h2>مواصفات {name}</h2>\n<p>{F["short"]} نطبعها على الوجهين، ونقصّها على شكل الشعار أو بشكل سيارة أو دائرة ضمن المقاس.</p>\n'
            '<h2>الروائح</h2>\n<p>نجهّز كل 1,000 قطعة برائحة وحدة، مثل اللافندر والمسك والليمون. لذلك إذا طلبت 3,000 قطعة تقدر تختار 3 روائح.</p>\n'
            f'<h2>كيف تطلب {name}؟</h2>\n' + ORDER_STEPS.format(code=sku) + '\n' + SHIP + '\n'
            '<h2>أسئلة شائعة</h2>\n<h3>ما الحد الأدنى للطلب؟</h3>\n<p>1,000 قطعة من التصميم الواحد.</p>\n'
            '<h3>هل السعر شامل الطباعة؟</h3>\n<p>نعم، السعر شامل الطباعة بالألوان والقص والخيط، ولا يشمل الشحن.</p>')
    e['description'] = desc
    e['tabs'] = [{'id': 'tab-description', 'title': 'الوصف', 'cls': 'woocommerce-Tabs-panel panel entry-content wc-tab woocommerce-Tabs-panel--description', 'html': desc},
                 {'id': 'tab-wd_custom_tab', 'title': 'الخيارات والأسعار', 'cls': 'woocommerce-Tabs-panel panel entry-content wc-tab woocommerce-Tabs-panel--wd_custom_tab', 'html': options},
                 {'id': 'tab-additional_information', 'title': 'معلومات إضافية', 'cls': 'woocommerce-Tabs-panel panel entry-content wc-tab woocommerce-Tabs-panel--additional_information',
                  'html': attr_table([('المقاس', '7×7 سم, 8×7 سم'), ('الكمية', ', '.join(qlab)), ('الخامة', 'كرتون معطّر'), ('الطباعة', 'ألوان على الوجهين')])}]
    md = f'{name} من مطبعة مدارك بقصّة حسب تصميمك، بمقاسين 7×7 و8×7 سم. السعر {money(lo)} لكل 1,000 قطعة. اطلب عرض سعر عبر واتساب.'
    e['seo'] = seo_for(name, path, md, img, crumbs, low=lo, high=hi, count=len(e['variations']), sku=sku)
    return e


def clothes_entry(i, code, name, price, what):
    path = slug_path(name, code)
    img = img_relabel(code, portal_img(code), code.lower())
    crumbs = [['الرئيسية', '/'], ['الألبسة والمنسوجات', '/product-category/tekstil-ar/']]
    e = base_entry(39010 + i, code, name, path, [79], crumbs, [img], name)
    e['price'] = {'price': price, 'regular': price, 'sale': price, 'min': None, 'max': None, 'on_sale': False}
    pline = (f'سعر القطعة يبدأ من {money(price)} دون الشعار، ويتغيّر حسب الكمية والمقاسات وطريقة الشعار.' if price is not None
             else 'السعر حسب الكمية والمقاسات وطريقة الشعار، واطلب عرض السعر عبر واتساب.')
    e['short'] = f'<p>{what} نطبع شعاركم عليه بطباعة DTF أو نطرّزه.</p>\n<p>{pline}</p>'
    pdesc = f' يبدأ السعر من {money(price)} للقطعة.' if price is not None else ''
    sizes = ('مقاس واحد يناسب الجميع، ونحدد معك عدد القطع لكل لون.' if 'قبعة' in name
             else 'المقاسات من S إلى XXL، ونحدد معك عدد القطع لكل مقاس ولون.')
    desc = (f'<p><strong>{name}</strong> من <a href="/">مطبعة مدارك</a> لفرق العمل والفعاليات والهدايا.{pdesc}</p>\n'
            f'<figure class="md-fig"><img src="{img}" alt="{esc(name)}" width="300" height="300" loading="lazy"></figure>\n'
            f'<h2>مواصفات {name}</h2>\n<p>{what} {sizes}</p>\n'
            '<h2>الشعار</h2>\n<p>نطبع الشعار بطباعة DTF أو نطرّزه حسب القماش والمكان (الصدر أو الظهر أو الكم). '
            'ونرسل لك نموذجاً للاعتماد قبل التنفيذ.</p>\n'
            f'<h2>كيف تطلب {name}؟</h2>\n' + ORDER_STEPS.format(code=code) + '\n' + SHIP + '\n'
            '<h2>أسئلة شائعة</h2>\n<h3>هل السعر شامل الشعار؟</h3>\n<p>لا، السعر للقطعة دون الشعار، ونضيف كلفة الطباعة أو التطريز في عرض السعر.</p>\n'
            '<h3>هل يمكن خلط المقاسات والألوان؟</h3>\n<p>نعم، نوزع الكمية على المقاسات والألوان التي تحتاجها.</p>')
    e['description'] = desc
    e['tabs'] = [{'id': 'tab-description', 'title': 'الوصف', 'cls': 'woocommerce-Tabs-panel panel entry-content wc-tab woocommerce-Tabs-panel--description', 'html': desc}]
    md = (f'{name} من مطبعة مدارك بطباعة أو تطريز الشعار.' + (f' يبدأ السعر من {money(price)} للقطعة.' if price is not None else '') +
          ' اطلب عرض سعر عبر واتساب والشحن إلى سوريا وليبيا والعراق والخليج.')
    e['seo'] = seo_for(name, path, md, img, crumbs, price=price, sku=code)
    return e


def link_of(sku, by):
    p = by.get(sku) if sku else None
    return p['path'] if p else None


def offer_entry(i, code, name, items, image, by, regular=None, price=None, note='', kind='set'):
    path = slug_path(name, code)
    crumbs = [['الرئيسية', '/'], [OFFERS['name'], OFFERS['path']]]
    e = base_entry(39020 + i, code, name, path, [OFFERS['id']], crumbs, [image], name)
    on_sale = regular is not None and regular > price
    e['price'] = {'price': price, 'regular': regular if on_sale else price, 'sale': price, 'min': None, 'max': None, 'on_sale': on_sale}
    lis = []
    for n, q, s in items:
        href = link_of(s, by)
        q = f'{q:,} ' if q else ''
        lis.append(f'<li>{q}{f"<a href={chr(34)}{href}{chr(34)}>{n}</a>" if href else n}</li>')
    ul = '<ul>\n' + '\n'.join(lis) + '\n</ul>'
    if kind == 'set':
        what = 'سعر الطقم الواحد للكمية 100 طقم وأكثر، دون طباعة الشعار والشحن.'
        why = 'عرض رأس السنة 2027 بخصم 10%.'
        intro = f'<p><strong>{name}</strong> من <a href="/">مطبعة مدارك</a>: هدية جاهزة لعملائك وموظفيك. {why} {what}</p>'
        e['short'] = f'<p>{why} {what}</p>\n<p>يحتوي الطقم على:</p>\n{ul}'
    else:
        what = f'السعر للباقة كاملة {note}'
        intro = f'<p><strong>{name}</strong> من <a href="/">مطبعة مدارك</a>: كل مطبوعات شركتك بهوية وحدة وبسعر واحد. {what}</p>'
        e['short'] = f'<p>{what}</p>\n<p>تحتوي الباقة على:</p>\n{ul}'
    desc = (intro + f'\n<figure class="md-fig"><img src="{image}" alt="{esc(name)}" width="300" height="300" loading="lazy"></figure>\n'
            f'<h2>محتويات {name.split(":")[0]}</h2>\n{ul}\n'
            '<h2>التخصيص</h2>\n<p>نجهّز التصميم بهوية شركتك ونرسل لك نموذجاً للاعتماد قبل التنفيذ.' +
            (' طباعة الشعار على القطع تُحسب في عرض السعر حسب طريقة الطباعة.' if kind == 'set' else '') + '</p>\n'
            f'<h2>كيف تطلب {name.split(":")[0]}؟</h2>\n' + ORDER_STEPS.format(code=code) + '\n' + SHIP)
    e['description'] = desc
    e['tabs'] = [{'id': 'tab-description', 'title': 'الوصف', 'cls': 'woocommerce-Tabs-panel panel entry-content wc-tab woocommerce-Tabs-panel--description', 'html': desc}]
    md = f'{name} من مطبعة مدارك بسعر {money(price)}. ' + (what if kind == 'identity' else 'عرض رأس السنة بخصم 10%. ') + ' اطلب عبر واتساب.'
    e['seo'] = seo_for(name, path, re.sub(r'\s+', ' ', md).strip(), image, crumbs, price=price, sku=code)
    return e


def offers_category(cat79):
    desc = ('<p>عروض <strong>مطبعة مدارك</strong> الحالية: أطقم هدايا جاهزة من دفتر وقلم وميدالية بخصم رأس السنة، وباقات مطبوعات الهوية '
            'البصرية بسعر واحد للباقة كاملة.</p><h2>كيف تطلب العرض؟</h2><p>أرسل كود العرض والكمية وبلد التسليم عبر '
            f'<a href="{WA}" target="_blank" rel="noopener">واتساب</a>، ونرسل لك عرض السعر ونموذج التصميم للموافقة. '
            'للتفاصيل زر صفحة <a href="/contact-us/">تواصل معنا</a>.</p>')
    md = 'عروض مطبعة مدارك: أطقم هدايا الشركات بخصم رأس السنة، وباقات مطبوعات الهوية البصرية بسعر واحد. اطلب عبر واتساب.'
    title = 'عروض وباقات هدايا الشركات | مطبعة مدارك'
    url = SITE + OFFERS['path']
    seo = json.loads(json.dumps(cat79['seo']))
    seo['title'] = title
    tags = []
    for t in seo['tags']:
        t = re.sub(r'content="[^"]*" name="description"', f'content="{md}" name="description"', t)
        t = re.sub(r'content="[^"]*" property="og:description"', f'content="{md}" property="og:description"', t)
        t = re.sub(r'content="[^"]*" property="og:title"', f'content="{title}" property="og:title"', t)
        t = t.replace(SITE + '/product-category/tekstil-ar/', url)
        tags.append(t)
    seo['tags'] = tags
    seo['ld'] = [x.replace('tekstil-ar', 'offers').replace('ملابس دعائية بشعارك | مطبعة مدارك', title) for x in seo['ld']]
    return {'id': OFFERS['id'], 'name': OFFERS['name'], 'slug': OFFERS['slug'], 'path': OFFERS['path'], 'parent': 0, 'count': 0,
            'description': desc, 'image': '', 'image_alt': '', 'seo': seo, 'breadcrumbs': [['الرئيسية', '/']]}


def main():
    global FRAME, WEBSITE, ORG
    FRAME = frame()
    path = os.path.join(ROOT, 'content/catalog.json')
    cat = json.load(open(path, encoding='utf-8'))
    by = {p['sku']: p for p in cat['products']}
    d = json.loads(by['MD-TR-1-0951']['seo']['ld'][0])
    WEBSITE = next(n for n in d['@graph'] if n['@type'] == 'WebSite')
    ORG = next(n for n in d['@graph'] if n['@type'] == 'Organization')

    new = [fragrance_entry()]
    new += [clothes_entry(i, *c) for i, c in enumerate(CLOTHES)]
    for i, (code, name, reg, price, items, (how, files)) in enumerate(SETS):
        image = img_trio(code, files) if how == 'trio' else img_relabel(code, MEDIA + files[0])
        new.append(offer_entry(i, code, name, items, image, by, reg, price, kind='set'))
    for j, (code, name, price, items, note, files) in enumerate(IDENTITY):
        new.append(offer_entry(10 + j, code, name, items, img_identity(code, files), by, None, price, note, kind='identity'))

    skus = {e['sku'] for e in new}
    cat['products'] = [p for p in cat['products'] if p['sku'] not in skus] + new
    cats = [c for c in cat['categories'] if c['id'] != OFFERS['id']]
    cats.insert(0, offers_category(next(c for c in cat['categories'] if c['id'] == 79)))
    cat['categories'] = cats
    for c in cat['categories']:
        c['count'] = sum(1 for p in cat['products'] if c['id'] in p['cats'])
    json.dump(cat, open(path, 'w', encoding='utf-8'), ensure_ascii=False)

    nav_path = os.path.join(ROOT, 'content/nav.json')
    nav = json.load(open(nav_path, encoding='utf-8'))
    item = {'name': OFFERS['name'], 'path': OFFERS['path']}
    nav['cat_nav'] = [item] + [x for x in nav['cat_nav'] if x['path'] != OFFERS['path']]
    menu = [x for x in nav['menu'] if x['path'] != OFFERS['path']]
    shop = next(i for i, x in enumerate(menu) if x['path'] == '/shop/')
    menu.insert(shop + 1, {'name': 'العروض', 'path': OFFERS['path']})
    nav['menu'] = menu
    json.dump(nav, open(nav_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(new)} products written:', ', '.join(e['sku'] for e in new))


if __name__ == '__main__':
    sys.exit(main())
