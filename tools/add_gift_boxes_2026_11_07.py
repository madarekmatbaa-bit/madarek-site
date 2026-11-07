#!/usr/bin/env python3
"""Nine luxury gift boxes (Ammar, 4 and 7 Nov 2026).

«الصور تبعها بدنا نبعثها على الموقع مشان تترفع على الموقع والبوابة، وتكون من الأشياء اللي دائما بنشغل منهم من الأولانيات»
and «نسخة سادة وخليها من المنتجات يلي بتطلع على الموقع فوق».

The boxes are the ones drawn in 3D for the Ministry of Defence offer (claude/mod-martyr-exhibition-gift-box-2026-11-04.md),
in a plain version: no state emblem, no ministry text. Pictures: renders with a transparent background
(mod-box/r3d/out/plain and out/final, *.png) put on the site's brand frame with the product code.
Prices: none yet (the portal quotes them), so the site shows «اطلب عرض سعر» and the portal feed marks them on_request.
They are pinned to the top of every listing they are in (data/sales_rank.json «pinned», lib/ranking.py).

    python3 tools/add_gift_boxes_2026_11_07.py [RENDERS_DIR]
"""
import json
import os
import re
import sys
import urllib.parse as up

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import add_products_2026_10_31 as ap  # noqa: E402  helpers: frame, label, seo_for, base_entry, ORDER_STEPS, SHIP …

ROOT = ap.ROOT
SITE = ap.SITE
UP = '/wp-content/uploads/2026/11/'
MEDIA = os.path.join(ROOT, 'media') + UP
RENDERS = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/mod-box/r3d/out'
GIFT_SETS = '/product-category/promotional-ar/gift-sets/'
CRUMBS = [['الرئيسية', '/'], ['التغليف والتعبئة', '/product-category/packaging/'],
          ['علب الهدايا', '/product-category/packaging/gift-boxes/']]

# code, name, pictures (render files), what it is, how the logo goes on, extra rows for «معلومات إضافية»
BOXES = [
    ('MD-GB-0001', 'صندوق هدايا «المجد» المطرّز', ['plain/emb_closed.png', 'final/emb_open.png'],
     'صندوق هدايا صلب بكسوة مخملية خضراء، تزيّن غطاءه زخارف ذهبية مطرّزة في الزوايا وإطار ذهبي، ومن الداخل إطار ذهبي حول التجويف.',
     'نطرّز شعاركم واسم المناسبة بخيط ذهبي في وسط الغطاء.',
     [('الكسوة', 'مخمل'), ('الزخرفة', 'تطريز بخيط ذهبي'), ('الشعار', 'تطريز ذهبي')]),
    ('MD-GB-0002', 'صندوق هدايا «الوقار» بالطباعة الذهبية', ['plain/goldprint.png'],
     'صندوق هدايا صلب بكسوة خضراء ناعمة الملمس، بدرزة على حواف الغطاء وإطار ذهبي مزدوج.',
     'نطبع الشعار والعبارة بطباعة ذهبية حرارية، ويتوفر بطباعة UV ملوّنة.',
     [('الكسوة', 'قماش ناعم الملمس بدرزة على الحواف'), ('الشعار', 'طباعة ذهبية حرارية أو طباعة UV ملوّنة')]),
    ('MD-GB-0003', 'صندوق هدايا «العهد» بلوحة الروماك', ['final/romak.png'],
     'صندوق هدايا صلب بكسوة من الجلد الأخضر، تتوسط غطاءه لوحة ذهبية لامعة من الروماك.',
     'نحفر شعاركم ونص الإهداء على اللوحة بالليزر.',
     [('الكسوة', 'جلد'), ('اللوحة', 'روماك ذهبي'), ('الشعار', 'حفر بالليزر على اللوحة')]),
    ('MD-GB-0004', 'صندوق «الأصالة» الدمشقي بالموزاييك', ['plain/mosaic.png'],
     'صندوق من الخشب المطعّم بالموزاييك الدمشقي، تتوسط غطاءه لوحة من الصدف.',
     'نحفر الشعار على لوحة الصدف.',
     [('الخامة', 'خشب مطعّم بالموزاييك'), ('اللوحة', 'صدف'), ('الشعار', 'حفر على لوحة الصدف')]),
    ('MD-GB-0005', 'صندوق هدايا «السموّ» الأبيض', ['final/whitebox.png'],
     'علبة هدايا مقوّاة ثقيلة باللون الأبيض بغطاء متصل، وبطانة مخملية من الداخل باللون الذي تختارونه.',
     'نطبع شعاركم على الغطاء.',
     [('الخامة', 'كرتون مقوّى ثقيل'), ('البطانة', 'مخمل باللون الذي تختارونه')]),
    ('MD-GB-0006', 'علبة هدايا «الوفاء» الجلدية', ['final/pu.png'],
     'علبة هدايا مكسوّة بجلد أخضر محبّب، بزوايا معدنية ذهبية.',
     'نضع شعاركم على الغطاء بالطباعة أو الحفر.',
     [('الكسوة', 'جلد محبّب'), ('الزوايا', 'معدن ذهبي')]),
    ('MD-GB-0007', 'علبة هدايا «الرفعة» القماشية', ['final/carton.png'],
     'علبة كرتوناج صلبة مكسوّة بقماش كتّاني أخضر.',
     'نطبع شعاركم على الغطاء.',
     [('الخامة', 'كرتوناج صلب'), ('الكسوة', 'قماش كتّاني')]),
    ('MD-GB-0008', 'حقيبة هدايا «الفخر» الجلدية', ['final/bag.png'],
     'حافظة هدايا من جلد الشامواه بلسان علوي، تحمل الهدية ويستعملها الضيف بعدها لحفظ أوراقه.',
     'نضع شعاركم على الوجه الأمامي.',
     [('الخامة', 'جلد شامواه'), ('الإغلاق', 'لسان علوي')]),
    ('MD-GB-0009', 'كيس هدايا «الإهداء» الفاخر', ['final/paperbag.png'],
     'كيس هدايا من الكرتون الفاخر بمقابض من الحبل الذهبي، يرافق العلبة عند التسليم.',
     'نطبع الشعار بطباعة ذهبية.',
     [('الخامة', 'كرتون فاخر'), ('المقابض', 'حبل ذهبي'), ('الشعار', 'طباعة ذهبية')]),
]
PID0 = 39040
TAB = 'woocommerce-Tabs-panel panel entry-content wc-tab woocommerce-Tabs-panel--'


def slug_path(name, code):
    s = re.sub(r'[«»():،,]', ' ', re.sub(r'[ً-ْ]', '', name))
    s = re.sub(r'\s+', '-', s.strip()) + '-' + code.lower()
    q = up.quote(s.lower(), safe='-')
    return '/product/' + re.sub(r'%[0-9A-F]{2}', lambda m: m.group(0).lower(), q) + '/'


def picture(render, code, name):
    """A render with a transparent background on the brand frame, with the code under it."""
    c = Image.fromarray(ap.FRAME).convert('RGBA')
    im = Image.open(os.path.join(RENDERS, render)).convert('RGBA')
    # the box and its darker shadow decide the size; the faint shadow around it may run past the frame
    a = im.split()[3].point(lambda v: 255 if v > 90 else 0)
    x0, y0, x1, y1 = a.getbbox()
    tx0, ty0, tx1, ty1 = 95, 150, 835, 790
    s = min((tx1 - tx0) / (x1 - x0), (ty1 - ty0) / (y1 - y0))
    big = im.resize((round(im.size[0] * s), round(im.size[1] * s)), Image.LANCZOS)
    ox = round((tx0 + tx1) / 2 - (x0 + x1) / 2 * s)
    oy = round((ty0 + ty1) / 2 - (y0 + y1) / 2 * s)
    layer = Image.new('RGBA', c.size, (0, 0, 0, 0))
    layer.paste(big, (ox, oy))
    # the shadow fades out before the code label, which sits on the plain background
    keep = Image.new('L', c.size, 255)
    ImageDraw.Draw(keep).rectangle([0, 775, 410, 900], fill=0)
    keep = np.asarray(keep.filter(ImageFilter.GaussianBlur(22))) / 255
    al = np.asarray(layer.split()[3]).astype(float)
    al = np.where(al >= 250, al, al * keep)        # the box itself (opaque) stays whole
    layer.putalpha(Image.fromarray(al.round().astype(np.uint8)))
    c.alpha_composite(layer)
    ap.label(c, code)
    os.makedirs(MEDIA, exist_ok=True)
    c.convert('RGB').save(MEDIA + name, 'JPEG', quality=90)
    ap.SIZES[SITE + UP + name] = c.size[0]
    return SITE + UP + name


def entry(i, code, name, renders, what, logo, rows):
    ap.DATE = f'2026-11-07T08:{20 - i:02d}:00'     # newest first in the home tab: A1 … A9
    path = slug_path(name, code)
    imgs = [picture(r, code, code.lower() + ('' if k == 0 else f'-{k + 1}') + '.jpg') for k, r in enumerate(renders)]
    e = ap.base_entry(PID0 + i, code, name, path, [328, 302], CRUMBS, imgs, name)
    e['date'] = ap.DATE
    e['price'] = {'price': None, 'regular': None, 'sale': None, 'min': None, 'max': None, 'on_sale': False}
    price_line = 'السعر حسب المقاس والكمية وطريقة الشعار، ونرسله لكم في عرض السعر.'
    e['short'] = f'<p>{what} {logo}</p>\n<p>{price_line} اطلب العرض عبر واتساب.</p>'
    desc = (f'<p><strong>{name}</strong> من <a href="/">مطبعة مدارك</a> لهدايا كبار الضيوف في المؤتمرات والمعارض والمناسبات الرسمية، '
            'ولهدايا الشركات لعملائها وموظفيها.</p>\n'
            f'<figure class="md-fig"><img src="{imgs[0]}" alt="{ap.esc(name)}" width="300" height="300" loading="lazy"></figure>\n'
            f'<h2>مواصفات {name}</h2>\n<p>{what}</p>\n'
            f'<h2>الشعار والتخصيص</h2>\n<p>{logo} ونتفق معكم على المقاس واللون قبل التنفيذ، ونرسل نموذج التصميم للموافقة. '
            'الصور توضيحية، وتُنفَّذ العلبة بشعاركم.</p>\n'
            '<h2>محتوى الهدية</h2>\n<p>نجهّز محتوى العلبة إذا رغبتم من منتجاتنا: دفاتر وأقلام وعطور وإلكترونيات دعائية، '
            f'أو نختاره معكم من <a href="{GIFT_SETS}">أطقم الهدايا</a>.</p>\n'
            f'<h2>كيف تطلب {name}؟</h2>\n' + ap.ORDER_STEPS.format(code=code) + '\n' + ap.SHIP + '\n'
            '<h2>أسئلة شائعة</h2>\n<h3>كم السعر؟</h3>\n<p>' + price_line + '</p>\n'
            '<h3>هل تُنفَّذ العلبة باسم مناسبتنا؟</h3>\n<p>نعم، نضع شعاركم واسم المناسبة أو نص الإهداء، ونرسل التصميم للموافقة قبل التنفيذ.</p>')
    e['description'] = desc
    e['tabs'] = [{'id': 'tab-description', 'title': 'الوصف', 'cls': TAB + 'description', 'html': desc},
                 {'id': 'tab-additional_information', 'title': 'معلومات إضافية', 'cls': TAB + 'additional_information',
                  'html': ap.attr_table(rows + [('السعر', 'حسب الكمية، بعرض سعر')])}]
    md = f'{name} من مطبعة مدارك بشعاركم: {what.split("،")[0].rstrip(".")}. اطلب عرض سعر عبر واتساب.'
    e['seo'] = ap.seo_for(name, path, md, imgs[0], CRUMBS, sku=code)
    return e


def main():
    ap.FRAME = ap.frame()
    path = os.path.join(ROOT, 'content/catalog.json')
    cat = json.load(open(path, encoding='utf-8'))
    by = {p['sku']: p for p in cat['products']}
    d = json.loads(by['MD-TR-1-0951']['seo']['ld'][0])
    ap.WEBSITE = next(n for n in d['@graph'] if n['@type'] == 'WebSite')
    ap.ORG = next(n for n in d['@graph'] if n['@type'] == 'Organization')

    new = [entry(i, *b) for i, b in enumerate(BOXES)]
    skus = {e['sku'] for e in new}
    cat['products'] = [p for p in cat['products'] if p['sku'] not in skus] + new
    for c in cat['categories']:
        c['count'] = sum(1 for p in cat['products'] if c['id'] in p['cats'])
    json.dump(cat, open(path, 'w', encoding='utf-8'), ensure_ascii=False)

    rank_path = os.path.join(ROOT, 'data/sales_rank.json')
    rank = json.load(open(rank_path, encoding='utf-8'))
    rank['pinned'] = [e['sku'] for e in new]
    json.dump(rank, open(rank_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(new)} products written:', ', '.join(e['sku'] for e in new))


if __name__ == '__main__':
    sys.exit(main())
