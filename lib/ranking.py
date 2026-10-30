"""The order products are listed in: most likely to sell first, kinds mixed (Ammar, 30 Oct 2026).

Every product gets a kind (business cards, agendas, metal pens, paper bags, desk flags, calculators …).
A kind's weight = a fixed prior + what the portal's quotes and orders asked for (data/sales_rank.json,
refreshed with tools/sales_rank.py). The listing takes products from all kinds in proportion to those
weights, so a page starts with what usually sells and keeps mixing kinds (no "best seller" label).
Inside a kind: products quoted by code first, then one of each look-alike before the next, and products
whose picture is still a text card last.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# portal line name -> site kind(s); first match wins (tools/sales_rank.py runs these in the portal)
PORTAL_RULES = [
    ('bcard', r'كرت شخصي|كروت|بطاقة شخصية|بطاقات عمل|كرت بزنس|كرت ?[0-9٠-٩]', {'bcard': 1}),
    ('card', r'كرت(?!ون)', {'bcard': 0.5, 'brochure': 0.5}),
    ('forms', r'إيصال|ايصال|كتيب متابعة|كربون|نماذج', {'c365': 1}),
    ('restaurant', r'منيو|كاسة كرتون|مفرش', {'c369': 1}),
    ('food', r'بيتزا|شاورما|همبرغر|فاهيتا|كنتاكي|صندوق وجبة|زكزاك', {}),
    ('phone', r'حامل موبايل|حامل هاتف|ستاند موبايل', {'c335': 1}),
    ('apparel', r'تي?شي?رت|جاكيت|قبعة|طاقية|طواقي|بولو|كنزة|هودي|فيست|قميص|جيليه|شال|مريول|سوت|الكراج', {'apparel': 1}),
    ('fragrance', r'فواح', {'fragrance': 1}),
    ('giftset', r'علب(ة|) دعا|سيت|\+|ضمن بوكس|دفتر.*قلم.*ميدالية', {'giftset': 1}),
    ('agenda', r'أجندة|اجندة|مذكرات', {'agenda': 1}),
    ('notecube', r'مكعب', {'notecube': 1}),
    ('notebook', r'دفتر|مذكرة|نوت ?بوك|دفاتر', {'notebook': 1}),
    ('pencil', r'رصاص', {'c350': 1}),
    ('pen_metal', r'قلم معدن|[أا]قلام معدن|ماتالايز|ليزر', {'c224': 1}),
    ('pen_plastic', r'(قلم|[أا]قلام) بلاستي?ك|uv', {'c80': 1}),
    ('pen', r'قلم|[أا]قلام', {'c224': 0.5, 'c80': 0.5}),
    ('paperbag', r'كيس (كرتون|كرافت|ورقي)|[أا]كياس كرتون|^[أا]كياس$', {'paperbag': 1}),
    ('clothbag', r'قماش|توت باغ|حقيبة', {'c333': 1}),
    ('sticker', r'ستيكر|ستكر|استيكر|لصاقة|ملصقات|dtf', {'sticker': 1}),
    ('envelope', r'ظرف|ظروف|[أا]ظرف', {'envelope': 1}),
    ('letterhead', r'ورق رسمي|ورق مراسلات|أوراق مكتبية', {'letterhead': 1}),
    ('folder', r'ملف جيب|ملف بجيب|فولدر|مصنف', {'folder': 1}),
    ('brochure', r'بروشور|فلاير|ملف تعريفي|كتيب|كتالوك|مجلة|امساكية|المطبوعات|كفالة', {'brochure': 1}),
    ('deskflag', r'علم مكتبي|[أا]علام مكتبية|قواعد مفردة', {'deskflag': 1}),
    ('maqam', r'مقام', {'flag_maqam': 1}),
    ('feather', r'شراع', {'flag_feather': 1}),
    ('rollup', r'رول ?[اأ]ب|بوب ?ابز', {'rollup': 1}),
    ('bigflag', r'علم', {'flag_big': 1}),
    ('keychain', r'ميدالي', {'c276': 1}),
    ('desk', r'مناديل|محارم|تقويم', {'c363': 1}),
    ('giftbox', r'بوكس|علبة', {'giftbox': 1}),
    ('clock', r'ساع(ة|ات) حائط', {'c357': 1}),
    ('thermos', r'ترمس', {'c354': 1}),
    ('mug', r'كوب|ماغ|^مج|\sمج', {'c355': 1}),
    ('car', r'حاجب شمس|سيارة', {'car': 1}),
    ('umbrella', r'مظلة', {'c341': 1}),
    ('badge', r'باج|^ID$|بروش|دبوس|شارة|شارات|حامل(ة|) بطاق|هوية تعريفية', {'badge': 1}),
    ('powerbank', r'باور ?بنك|باوربانك', {'c351': 1}),
    ('usb', r'USB', {'c308': 1}),
    ('tools', r'أداة', {'c334': 1}),
    ('care', r'مرآة', {'c336': 1}),
    ('home', r'شمعة', {'c342': 1}),
    ('award', r'درع|شهاد', {'c304': 1}),
]

# site product -> kind: by name first, then by its category
NAMED = [
    ('fragrance', r'فواحات|فواحة|معطر سيارة'),
    ('bcard', r'كرت شخصي|بطاقات? (عمل|شخصية)'),
    ('paperbag', r'أكياس ورقية|الأكياس الورقية'),
    ('envelope', r'ظروف|أظرف'),
    ('letterhead', r'ورق رسمي|الورق رسمي'),
    ('folder', r'ملف بجيب|ملفات الجيب'),
    ('brochure', r'بروشور'),
    ('sticker', r'استيكر|ستيكر'),
    ('notecube', r'مكعب'),
    ('agenda', r'أجندة'),
    ('flag_maqam', r'مقام|تشريفات|مراسم'),
    ('flag_feather', r'شراعي|قطرة|شكل L'),
    ('rollup', r'رول أب'),
    ('flag_big', r'علم سارية|قواعد الأعلام'),
]
BY_CAT = {380: 'offers', 296: 'notebook', 368: 'notebook', 345: 'deskflag', 302: 'giftbox', 332: 'giftset', 340: 'car',
          79: 'apparel', 370: 'paperbag'}
NOTEBOOK = re.compile(r'دفتر|مذكرة|دفاتر')

# what each kind is expected to sell before any portal data (relative); kinds not listed get 1
PRIOR = {
    'offers': 6, 'fragrance': 2, 'bcard': 3, 'agenda': 3, 'notebook': 2.5, 'c224': 2.5, 'c80': 2.5, 'paperbag': 2.5, 'giftbox': 2.5,
    'giftset': 2.5, 'brochure': 2, 'envelope': 2, 'letterhead': 2, 'folder': 2, 'sticker': 1.5, 'notecube': 1.5,
    'deskflag': 2, 'flag_maqam': 2, 'flag_feather': 1.5, 'rollup': 1.5, 'flag_big': 1.2, 'c346': 0.8,
    'c276': 2, 'c354': 2, 'c355': 2, 'c356': 1.5, 'c341': 1.5, 'car': 1.5, 'apparel': 1.2,
    'c351': 1.8, 'c308': 1.8, 'c352': 1, 'c353': 1, 'c357': 1.5, 'c358': 1, 'c363': 1.5, 'c359': 1, 'c360': 1.2,
    'c361': 1.2, 'c362': 0.3, 'c333': 1.5, 'c334': 0.8, 'c335': 1.2, 'c336': 0.7, 'c338': 0.5, 'c342': 0.6,
    'c344': 1, 'c348': 1.8, 'c349': 1.5, 'c350': 1.2, 'c304': 1.2, 'c365': 1.2, 'c369': 0.8, 'c367': 0.7,
}
DEMAND_SCALE = 12      # the most asked-for kind gets this much on top of its prior
MIX = 0.8              # < 1 keeps smaller kinds in view sooner
CODE = re.compile(r'MD-TR-\d-\d{4}')


def load():
    path = os.path.join(ROOT, 'data/sales_rank.json')
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}


def _depth(cid, cats):
    d = 0
    while cats[cid].get('parent'):
        cid = cats[cid]['parent']
        d += 1
    return d


def kind_of(p, cats):
    name = p['name']
    for k, pat in NAMED:
        if re.search(pat, name):
            return k
    ids = [c for c in p['cats'] if c in cats]
    for c in ids:
        if c in BY_CAT:
            return BY_CAT[c]
    if NOTEBOOK.search(name) and ids == [75]:
        return 'notebook'
    if not ids:
        return 'other'
    deep = max(ids, key=lambda c: (_depth(c, cats), -c))
    return 'c%d' % deep


def _place(p, cats):
    """The product's most specific categories (a category page lists a product if it holds one of these)."""
    ids = set(c for c in p['cats'] if c in cats)
    under = set()
    for c in ids:
        a = cats[c].get('parent')
        while a:
            under.add(a)
            a = cats[a].get('parent')
    return tuple(sorted(ids - under))


def codes_of(p):
    out = set(CODE.findall(p.get('sku') or '')) | set(CODE.findall(p['name']))
    for v in p.get('variations') or []:
        out |= set(CODE.findall(str(v.get('sku') or '')))
    return out


def _family(name):
    n = CODE.sub('', name)
    n = re.sub(r'[\d٠-٩]+', '', n)
    return re.sub(r'\s+', ' ', n).strip()


def order(products, categories, data=None):
    """products in the order listings show them."""
    data = load() if data is None else data
    cats = {c['id']: c for c in categories}
    demand, codes = data.get('demand', {}), data.get('codes', {})
    no_photo = set(str(i) for i in data.get('no_photo', []))
    top = max(demand.values()) if demand else 1
    base = {p['id']: i for i, p in enumerate(products)}

    # one queue per kind and listing place: products that always show up together share a queue, so every
    # category page gets the kind's best products first (not only the shop page)
    kinds = {}
    for p in products:
        kinds.setdefault((kind_of(p, cats), _place(p, cats)), []).append(p)
    split = {}
    for k, _ in kinds:
        split[k] = split.get(k, 0) + 1

    lead = set(data.get('lead', []))

    def code_score(p):
        # data/sales_rank.json "lead": products the team is pushing now (the new year's agenda …)
        return sum(codes.get(c, 0) for c in codes_of(p)) + (1000 if p.get('sku') in lead else 0)

    queues = {}
    for k, plist in kinds.items():
        photo = [p for p in plist if str(p['id']) not in no_photo]
        card = [p for p in plist if str(p['id']) in no_photo]
        photo.sort(key=lambda p: (-code_score(p), base[p['id']]))
        # one of each line (gift boxes, pen boxes, pen cases …) before the next, and inside a line one of
        # each look-alike; asked-for products keep their place at the front, the kind's main line leads
        lines = {}
        for p in photo:
            f = _family(p['name'])
            lines.setdefault(' '.join(f.split()[:2]), {}).setdefault(f, []).append(p)
        seqs = []
        for fams in lines.values():
            seqs.append(_round_robin(sorted(fams.values(), key=lambda g: (-max(map(code_score, g)), -len(g), base[g[0]['id']]))))
        seqs.sort(key=lambda g: (-max(map(code_score, g)), -len(g), base[g[0]['id']]))
        card.sort(key=lambda p: base[p['id']])
        queues[k] = (_round_robin(seqs), card)

    keyed = []
    nth = {}
    def newest(q):
        return max((p.get('date') or '' for p in q[0] + q[1]), default='')
    # the kind's biggest queue first, then the one with the newest products
    order_q = sorted(queues.items(), key=lambda kv: kv[0][1])
    order_q.sort(key=lambda kv: newest(kv[1]), reverse=True)
    order_q.sort(key=lambda kv: (kv[0][0], -len(kv[1][0])))
    for (k, place), (seq, card) in order_q:
        w = weight(k, demand, top) / split[k] ** 0.5
        # a fixed offset per kind so kinds with equal weight do not always come in the same order; the
        # queues of one kind start apart so their first products are not side by side
        j = nth[k] = nth.get(k, -1) + 1
        off = 0.45 + (sum(map(ord, k)) % 11) / 100 + j / split[k]
        for i, p in enumerate(seq):
            keyed.append((0, (i + off) / w, -w, k, i, p))
        # text-card pictures after every product with a photo
        for i, p in enumerate(card):
            keyed.append((1, (i + off) / w, -w, k, i, p))
    keyed.sort(key=lambda t: t[:5])
    return [t[5] for t in keyed]


def _round_robin(groups):
    out, depth = [], 0
    while any(len(g) > depth for g in groups):
        out += [g[depth] for g in groups if len(g) > depth]
        depth += 1
    return out


def weight(k, demand, top):
    return (PRIOR.get(k, 1) + DEMAND_SCALE * demand.get(k, 0) / (top or 1)) ** MIX
