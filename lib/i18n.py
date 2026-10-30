"""Translated copies of the built Arabic site: /en/ (English) and /tr/ (Turkish).

The Arabic site is the only source. After build.py writes it to dist/, every page is parsed,
its Arabic text is swapped for the translation memory (data/i18n/<lang>.json), links point to
the translated pages, contact numbers switch to the language's sales rep, and the head gets
lang/dir, canonical, hreflang and og:locale for that language.

Text with no translation yet is written to data/i18n/missing-<lang>.json (tools/translate.py
fills it) and stays Arabic on the page until the next build. A product or page whose name has no
translation yet is not published in that language at all (no temporary URLs).

Translation units: a block's inline content is translated as one unit, so word order can change.
Inline tags become numbered markers the translator keeps in place:
    ⟦1⟧أجندة 2027⟦/1⟧ من ⟦2⟧مطبعة مدارك⟦/2⟧   ->   ⟦1⟧2027 Planner⟦/1⟧ by ⟦2⟧Madarek Matbaa⟦/2⟧
Opaque things (icons, images, line breaks) are ⟦3/⟧.
"""
import copy
import hashlib
import json
import os
import re
import unicodedata
import urllib.parse as up

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

SITE = 'https://www.madarekmatbaa.com'

LANGS = {
    'en': {
        'name': 'English', 'short': 'EN', 'locale': 'en_US', 'dir': 'ltr', 'root': '/en/',
        'seg': {'product': 'product', 'category': 'category', 'shop': 'shop', 'search': 'search', 'page': 'page'},
        'contact': {'wa': '905510059096', 'tel': '+905510059096', 'phone': '+90 551 005 90 96',
                    'person': 'Ms. Heba', 'label': 'Sales', 'note': 'WhatsApp · Gulf, Iraq, Libya & worldwide'},
        'logo': '/assets/brand/madarek-logo-en-navy.svg', 'logo_white': '/assets/brand/madarek-logo-en-white.svg',
        'brand': 'Madarek Matbaa', 'and': 'and',
    },
    'tr': {
        'name': 'Türkçe', 'short': 'TR', 'locale': 'tr_TR', 'dir': 'ltr', 'root': '/tr/',
        'seg': {'product': 'urun', 'category': 'kategori', 'shop': 'urunler', 'search': 'arama', 'page': 'sayfa'},
        'contact': {'wa': '905071146377', 'tel': '+905071146377', 'phone': '+90 507 114 63 77',
                    'person': 'Ali', 'label': 'Satış', 'note': 'WhatsApp · İstanbul'},
        'logo': '/assets/brand/madarek-logo-en-navy.svg', 'logo_white': '/assets/brand/madarek-logo-en-white.svg',
        'brand': 'Madarek Matbaa', 'and': 've',
    },
}
AR_LANG = {'name': 'العربية', 'short': 'ع', 'locale': 'ar_AR', 'root': '/'}

# every company number that can appear in the Arabic pages
COMPANY_NUMBERS = ['905510059096', '963980243748', '905074886377', '905071146377', '905516498048',
                   '905016778152', '218910988383']
COMPANY_PHONES = ['+90 551 005 90 96', '+963 980 243 748', '+90 507 488 63 77', '+90 507 114 63 77',
                  '+90 551 649 80 48', '+90 501 677 81 52', '+218 91 098 8383']

AR = re.compile('[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]')
AR_LETTER = re.compile('[ء-ي٠-٩ٮ-ۓۺ-ۿݐ-ݿﭐ-﷿ﹰ-﻿]')
AR_PUNCT = {'،': ',', '؛': ';', '؟': '?', '٪': '%', 'ـ': ''}
WS = re.compile(r'\s+')
MARK = re.compile(r'⟦(/?)(\d+)(/?)⟧')
# codes, prices and numbers are masked so one translation serves every product that shares the wording
VAL = re.compile(r'(?<![A-Za-z0-9])(?:[A-Z]{2,}(?:-[A-Z0-9]+)+|[A-Z][A-Z0-9]+|\$\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?\$|'
                 r'\d+(?:[.,]\d+)?(?:\s?[x×]\s?\d+(?:[.,]\d+)?)*)(?![A-Za-z0-9])')
VMARK = re.compile(r'⟨(\d+)⟩')


def mask(s):
    vals = []

    def sub(m):
        vals.append(m.group(0))
        return f'⟨{len(vals) - 1}⟩'
    parts = re.split(r'(⟦/?\d+/?⟧)', s)  # inline-tag markers keep their own numbers
    return ''.join(p if MARK.fullmatch(p) else VAL.sub(sub, p) for p in parts), vals


def unmask(t, vals):
    found = sorted(int(i) for i in VMARK.findall(t))
    if found != list(range(len(vals))):
        return None
    return VMARK.sub(lambda m: vals[int(m.group(1))], t)

INLINE = {'a', 'abbr', 'b', 'bdi', 'bdo', 'cite', 'data', 'del', 'dfn', 'em', 'i', 'ins', 'kbd', 'mark', 'q',
          's', 'samp', 'small', 'span', 'strong', 'sub', 'sup', 'time', 'u', 'var', 'font'}
OPAQUE = {'svg', 'img', 'br', 'wbr', 'input', 'select', 'textarea', 'iframe', 'video', 'audio', 'canvas',
          'object', 'picture', 'math'}
VOID_INLINE = {'br', 'img', 'wbr', 'svg'}
SKIP = {'script', 'style', 'noscript', 'template', 'code', 'pre', 'textarea'}
NO_ATTR = {'href', 'src', 'srcset', 'action', 'poster', 'data-src', 'data-srcset', 'id', 'class', 'for', 'name',
           'style', 'content', 'sizes', 'rel', 'type', 'role', 'lang', 'dir', 'hreflang', 'data-i', 'data-k'}
META_TEXT = re.compile(r'^(description|keywords|twitter:title|twitter:description|twitter:image:alt|'
                       r'og:title|og:description|og:image:alt|og:site_name|apple-mobile-web-app-title)$')


def has_ar(s):
    return bool(s) and AR.search(s) is not None


def norm(s):
    return WS.sub(' ', s).strip()


def key(s):
    return hashlib.sha1(norm(s).encode('utf-8')).hexdigest()[:16]


def slugify(text, lang):
    s = text.replace('&', f' {LANGS[lang]["and"]} ').replace('×', 'x').replace('+', ' plus ')
    s = s.replace('ı', 'i').replace('İ', 'i')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    if len(s) > 70:
        s = s[:70].rsplit('-', 1)[0]
    return s or 'item'


# ---------------------------------------------------------------- translation memory
class Memory:
    """data/i18n/<lang>.json: {key: [arabic, translation]} (+ rules for numbered strings)."""

    def __init__(self, root, lang):
        self.lang = lang
        self.path = os.path.join(root, 'data/i18n', f'{lang}.json')
        self.data = json.load(open(self.path, encoding='utf-8')) if os.path.exists(self.path) else {}
        self.missing = {}
        self.used = set()
        self.bad = {}

    def get(self, src):
        s = norm(src)
        if not s or not has_ar(s):
            return src
        if not AR_LETTER.search(s):  # only Arabic punctuation
            return ''.join(AR_PUNCT.get(c, c) for c in src)
        r = rule(s, self)
        if r is not None:
            return r
        m, vals = mask(s)
        k = key(m)
        hit = self.data.get(k)
        if hit:
            out = unmask(hit[1], vals)
            if out is not None:
                self.used.add(k)
                return out
            self.bad[k] = hit
        self.missing[k] = m
        return None

    def save_missing(self, root):
        p = os.path.join(root, 'data/i18n', f'missing-{self.lang}.json')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(dict(sorted(self.missing.items())), open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        return len(self.missing)


def _count(n, lang):
    n = int(n)
    if lang == 'en':
        return f'{n} product' + ('' if n == 1 else 's')
    return f'{n} ürün'


AR_UNITS = r'(?:منتجاً|منتجات|منتج)'
RULES = [
    (re.compile(rf'^عرض (\d+)-(\d+) من (\d+) {AR_UNITS}$'),
     {'en': lambda m, M: f'Showing {m[1]}–{m[2]} of {_count(m[3], "en")}',
      'tr': lambda m, M: f'{m[3]} üründen {m[1]}–{m[2]} arası'}),
    (re.compile(rf'^عرض (\d+) من (\d+) {AR_UNITS}$'),
     {'en': lambda m, M: f'Showing {m[1]} of {_count(m[2], "en")}',
      'tr': lambda m, M: f'{m[2]} üründen {m[1]} tanesi'}),
    (re.compile(rf'^(\d+) {AR_UNITS}$'), {'en': lambda m, M: _count(m[1], 'en'), 'tr': lambda m, M: _count(m[1], 'tr')}),
    (re.compile(r'^منتج واحد$'), {'en': lambda m, M: '1 product', 'tr': lambda m, M: '1 ürün'}),
    (re.compile(r'^منتجان$'), {'en': lambda m, M: '2 products', 'tr': lambda m, M: '2 ürün'}),
    (re.compile(r'^نطاق السعر: من (\$[\d,.]+) إلى (\$[\d,.]+)$'),
     {'en': lambda m, M: f'Price range: {m[1]} to {m[2]}', 'tr': lambda m, M: f'Fiyat aralığı: {m[1]} – {m[2]}'}),
    (re.compile(r'^الصورة (\d+)$'), {'en': lambda m, M: f'Image {m[1]}', 'tr': lambda m, M: f'Görsel {m[1]}'}),
    (re.compile(r'^أقسام (.+)$'), {'en': lambda m, M: _sub(M, m[1], 'Sections: {}'), 'tr': lambda m, M: _sub(M, m[1], '{} bölümleri')}),
    (re.compile(r'^ابحث في (.+)$'), {'en': lambda m, M: _sub(M, m[1], 'Search {}'), 'tr': lambda m, M: _sub(M, m[1], '{} içinde ara')}),
    (re.compile(r'^عن (.+)$'), {'en': lambda m, M: _sub(M, m[1], 'About {}'), 'tr': lambda m, M: _sub(M, m[1], '{} hakkında')}),
]


def _sub(mem, part, tpl):
    t = mem.get(part)
    return None if t is None else tpl.format(t)


def rule(s, mem):
    for rx, out in RULES:
        m = rx.match(s)
        if m and mem.lang in out:
            return out[mem.lang](m, mem)
    return None


# ---------------------------------------------------------------- inline runs <-> marked text
def has_block(tag):
    for c in tag.children:
        if isinstance(c, Tag):
            if c.name in OPAQUE or c.name in SKIP:
                continue
            if c.name not in INLINE:
                return True
            if has_block(c):
                return True
    return False


def is_inline(node):
    if isinstance(node, NavigableString):
        return True
    return node.name in VOID_INLINE or (node.name in INLINE and not has_block(node))


def tokenize(nodes):
    slots, n = {}, [0]

    def rec(node):
        if isinstance(node, Comment):
            return ''
        if isinstance(node, NavigableString):
            return str(node).replace('⟦', '[').replace('⟧', ']')
        n[0] += 1
        i = n[0]
        if node.name in OPAQUE or node.name in SKIP or node.get('translate') == 'no' or node.name not in INLINE:
            slots[i] = ('void', node)
            return f'⟦{i}/⟧'
        slots[i] = ('pair', node.name, dict(node.attrs))
        return f'⟦{i}⟧' + ''.join(rec(c) for c in node.children) + f'⟦/{i}⟧'
    return ''.join(rec(x) for x in nodes), slots


def peel(s):
    """Split off leading/trailing icons and a tag that wraps the whole unit, so the same words
    share one translation whatever markup sits around them."""
    pre, post = '', ''
    while True:
        m = re.match(r'^(⟦\d+/⟧\s*)', s)
        if m:
            pre += m.group(1)
            s = s[m.end():]
            continue
        m = re.search(r'(\s*⟦\d+/⟧)$', s)
        if m:
            post = m.group(1) + post
            s = s[:m.start()]
            continue
        m = re.match(r'^⟦(\d+)⟧(.*)⟦/\1⟧$', s, re.S)
        if m and valid_marks(m.group(2), m.group(2)) and '⟦/' + m.group(1) + '⟧' not in m.group(2):
            pre += f'⟦{m.group(1)}⟧'
            post = f'⟦/{m.group(1)}⟧' + post
            s = m.group(2)
            continue
        return pre, s, post


def renum(s):
    """Number the markers 1, 2, 3 … in reading order (so equal wording gets one key); returns the map back."""
    fwd, back = {}, {}
    for _, i, _ in MARK.findall(s):
        if i not in fwd:
            fwd[i] = str(len(fwd) + 1)
            back[fwd[i]] = i
    return MARK.sub(lambda m: f'⟦{m.group(1)}{fwd[m.group(2)]}{m.group(3)}⟧', s), back


def valid_marks(src, out):
    a = sorted(MARK.findall(src))
    b = sorted(MARK.findall(out))
    if a != b:
        return False
    stack = []
    for close, i, void in MARK.findall(out):
        if void:
            continue
        if close:
            if not stack or stack[-1] != i:
                return False
            stack.pop()
        else:
            stack.append(i)
    return not stack


def rebuild(soup, text, slots):
    out = []
    stack = [out]
    for part in re.split(r'(⟦/?\d+/?⟧)', text):
        if not part:
            continue
        m = MARK.fullmatch(part)
        target = stack[-1]
        add = target.append
        if not m:
            add(NavigableString(part))
            continue
        close, i, void = m.group(1), int(m.group(2)), m.group(3)
        if void:
            add(copy.copy(slots[i][1]))
        elif close:
            stack.pop()
        else:
            _, name, attrs = slots[i]
            t = soup.new_tag(name, attrs=attrs)
            add(t)
            stack.append(t)
    return out


# ---------------------------------------------------------------- page translator
def load_overrides(root):
    """data/i18n/overrides.json: hand-written SEO title/description per language and Arabic path
    (e.g. English pages aimed at Gulf buyers). {lang: {"/arabic/path/": {"title": …, "description": …}}}"""
    p = os.path.join(root, 'data/i18n/overrides.json')
    raw = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    return {l: {up.unquote(k): v for k, v in d.items() if not k.startswith('_')} for l, d in raw.items() if not l.startswith('_')}


class Translator:
    def __init__(self, lang, memory, pathmap, overrides=None):
        self.lang = lang
        self.L = LANGS[lang]
        self.mem = memory
        self.paths = pathmap  # PathMap
        self.over = (overrides or {}).get(lang, {})

    # ---- text
    def text(self, s):
        if not s or not has_ar(s):
            return s
        lead = s[:len(s) - len(s.lstrip())]
        trail = s[len(s.rstrip()):]
        t = self.mem.get(s)
        return None if t is None else lead + t + trail

    def run(self, soup, nodes):
        text, slots = tokenize(nodes)
        bare = MARK.sub('', text)
        if not has_ar(bare):
            return False
        if not slots:
            t = self.text(text)
            if t is None:
                return False
            new = [NavigableString(t)]
        else:
            core = norm(text)
            pre, inner0, post = peel(core)
            inner, back = renum(inner0)
            t = self.mem.get(inner) if has_ar(MARK.sub('', inner)) else inner
            if t is None:
                return False
            if not valid_marks(inner, t):
                m_inner = mask(inner)[0]
                self.mem.bad[key(m_inner)] = [m_inner, t]
                self.mem.data.pop(key(m_inner), None)
                self.mem.missing[key(m_inner)] = m_inner
                return False
            t = pre + MARK.sub(lambda m: f'⟦{m.group(1)}{back[m.group(2)]}{m.group(3)}⟧', t) + post
            lead = text[:len(text) - len(text.lstrip())]
            trail = text[len(text.rstrip()):]
            new = ([NavigableString(lead)] if lead else []) + rebuild(soup, t, slots) + ([NavigableString(trail)] if trail else [])
        first = nodes[0]
        for x in new:
            first.insert_before(x)
        for x in nodes:
            x.extract()
        return True

    def walk(self, soup, el):
        if el.name in SKIP or el.get('translate') == 'no':
            return
        run = []
        for ch in list(el.children):
            if is_inline(ch):
                run.append(ch)
                continue
            if run:
                self.run(soup, run)
                run = []
            if isinstance(ch, Tag):
                self.walk(soup, ch)
        if run:
            self.run(soup, run)

    def attrs(self, root):
        for t in root.find_all(True):
            if t.name in ('script', 'style') or t.get('translate') == 'no':
                continue
            for a, v in list(t.attrs.items()):
                if a in NO_ATTR or not isinstance(v, str) or not has_ar(v):
                    continue
                tv = self.text(v)
                if tv is not None:
                    t[a] = tv

    # ---- links
    def url(self, u):
        """Arabic-site URL (absolute or root-relative) -> this language's URL; others unchanged."""
        if not u or u.startswith(('#', 'mailto:', 'javascript:', 'data:')):
            return u
        absu = u.startswith(SITE)
        rel = u[len(SITE):] if absu else u
        if absu and rel == '':
            rel = '/'
        if not rel.startswith('/') or rel.startswith('//'):
            return u
        path_q, hsep, frag = rel.partition('#')
        path, qsep, query = path_q.partition('?')
        if path == '/' and frag and not query:
            return u  # site-wide schema ids (#organization, #website) stay one entity
        new = self.paths.lang_path(path, self.lang)
        if new is None:
            return u
        return (SITE if absu else '') + new + (qsep + query if qsep else '') + (hsep + frag if hsep else '')

    def wa(self, href):
        p = up.urlsplit(href)
        qs = up.parse_qs(p.query)
        text = qs.get('text', [''])[0]
        lines = []
        for line in text.split('\n'):
            if line.startswith(('http://', 'https://')):
                lines.append(self.url(line))
            elif ': ' in line and has_ar(line.split(': ', 1)[0]):
                a, b = line.split(': ', 1)
                ta, tb = self.text(a), self.text(b)
                lines.append(f'{ta if ta is not None else a}: {tb if tb is not None else b}')
            else:
                t = self.text(line)
                lines.append(t if t is not None else line)
        out = f'https://wa.me/{self.L["contact"]["wa"]}'
        if text:
            out += '?text=' + up.quote('\n'.join(lines), safe='')
        return out

    def json_value(self, v, html_keys=()):
        if isinstance(v, dict):
            return {k: (self.html_fragment(x) if k in html_keys and isinstance(x, str) else self.json_value(x, html_keys))
                    for k, x in v.items()}
        if isinstance(v, list):
            return [self.json_value(x, html_keys) for x in v]
        if isinstance(v, str):
            if v.startswith(SITE) or (v.startswith('/') and not v.startswith('//')):
                return self.url(v)
            if has_ar(v):
                if '<' in v and '>' in v:
                    return self.html_fragment(v)
                t = self.text(v)
                return v if t is None else t
        return v

    def html_fragment(self, h):
        if not has_ar(h):
            return h
        s = BeautifulSoup(f'<div id="__f">{h}</div>', 'html.parser')
        box = s.find(id='__f')
        self.attrs(box)
        self.walk(s, box)
        for a in box.find_all('a', href=True):
            a['href'] = self.url(a['href'])
        return box.decode_contents()

    def apply_override(self, soup, ov):
        title, desc = ov.get('title'), ov.get('description')
        if title and soup.title:
            soup.title.string = title
        for m in soup.head.find_all('meta'):
            n = m.get('name') or m.get('property') or ''
            if title and n in ('og:title', 'twitter:title'):
                m['content'] = title
            if desc and n in ('description', 'og:description', 'twitter:description'):
                m['content'] = desc
        for sc in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(sc.string or '')
            except ValueError:
                continue
            nodes = data.get('@graph', [data]) if isinstance(data, dict) else []
            for n in nodes:
                if isinstance(n, dict) and n.get('@type') in ('WebPage', 'CollectionPage', 'AboutPage', 'ContactPage'):
                    if title:
                        n['name'] = title
                    if desc:
                        n['description'] = desc
            sc.string = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')

    # ---- contacts: one sales rep per language
    PRIMARY = '905510059096'  # the general quote number on the Arabic site (Ms. Heba)
    CARD = ('mdk-box', 'mdk-contact')

    def contacts(self, soup):
        rep = self.L['contact']['wa']
        for a in soup.select('a[href*="wa.me/"]'):
            if a.decomposed if hasattr(a, 'decomposed') else False:
                continue
            m = re.search(r'wa\.me/(\d+)', a.get('href', ''))
            if not m or m.group(1) not in COMPANY_NUMBERS:
                continue
            num = m.group(1)
            card = a if set(a.get('class') or []) & set(self.CARD) else a.find_parent(class_=lambda c: c in self.CARD)
            if card is not None and not any(ph in card.get_text() for ph in COMPANY_PHONES):
                card = None  # a box that only holds a button, not a person
            if card is not None:
                if num != rep:
                    card.decompose()
            elif num != self.PRIMARY and num != rep:
                a.decompose()  # «Syria sales» and other second buttons

    # ---- whole page
    def page(self, html, ar_path, alternates):
        L, lang = self.L, self.lang
        soup = BeautifulSoup(html, 'lxml')
        root = soup.html
        root['lang'] = lang
        root['dir'] = L['dir']
        root['data-root'] = L['root']
        root['data-search'] = self.paths.lang_path('/search/', lang) or L['root']
        head, body = soup.head, soup.body

        for el in soup.select('[data-only]'):
            if el['data-only'] != 'intl':
                el.decompose()
            else:
                del el['data-only']
                if el.has_attr('hidden'):
                    del el['hidden']
        for el in soup.select('.m-logo img, .mnav-top img'):
            el['src'] = L['logo']
            el['alt'] = L['brand']
            el['width'], el['height'] = '168', '35'
        for el in soup.select('footer img[src*="wordmark-white"]'):
            el['src'] = L['logo_white']
            el['alt'] = L['brand']
            el['width'], el['height'] = '190', '40'
        self.contacts(soup)
        for el in soup.select('[data-contact-line]'):
            c = L['contact']
            el['href'] = f'https://wa.me/{c["wa"]}'
            for b in el.select('b'):
                b.string = c['label']
            for sm in el.select('small'):
                sm.string = c['person']
            for bd in el.select('bdi'):
                bd.string = c['phone']

        # head
        for m in head.find_all('meta'):
            n = m.get('name') or m.get('property') or ''
            if n == 'og:locale':
                m['content'] = L['locale']
            elif n in ('og:url', 'twitter:url'):
                m['content'] = self.url(m.get('content', ''))
            elif META_TEXT.match(n) and has_ar(m.get('content', '')):
                t = self.text(m['content'])
                if t is not None:
                    m['content'] = t
        for l in head.find_all('link'):
            rel = ' '.join(l.get('rel') or [])
            if rel in ('canonical', 'prev', 'next'):
                l['href'] = self.url(l['href'])
            elif rel == 'preload' and 'plex-arabic' in (l.get('href') or ''):
                l.decompose()
        for w in ('regular', 'semibold'):
            pl = soup.new_tag('link', attrs={'rel': 'preload', 'href': f'/assets/fonts/poppins-latin-{w}.woff2',
                                              'as': 'font', 'type': 'font/woff2', 'crossorigin': ''})
            head.insert(3, pl)
        for s in soup.find_all('script'):
            typ = s.get('type', '')
            if typ in ('application/ld+json', 'application/json'):
                try:
                    data = json.loads(s.string or '')
                except ValueError:
                    continue
                data = self.json_value(data, html_keys=('d',))
                if s.get('id') == 'pv' and isinstance(data, dict):
                    data['phone'] = L['contact']['wa']
                if typ == 'application/ld+json':
                    data = ld_lang(data, lang)
                s.string = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
            elif s.string and "location.replace('/search/'" in s.string:
                s.string = s.string.replace("location.replace('/search/'", f"location.replace('{root['data-search']}'")
        if soup.title and soup.title.string:
            t = self.text(soup.title.string)
            if t is not None:
                soup.title.string = t
        ov = self.over.get(up.unquote(ar_path))
        if ov:
            self.apply_override(soup, ov)

        self.attrs(soup)
        self.walk(soup, body)

        for a in soup.find_all(['a', 'link', 'area'], href=True):
            h = a['href']
            if 'wa.me/' in h or 'api.whatsapp.com' in h:
                a['href'] = self.wa(h)
            elif h.startswith('tel:'):
                a['href'] = 'tel:' + L['contact']['tel']
            elif a.name != 'link':
                a['href'] = self.url(h)
        for f in soup.find_all('form', action=True):
            f['action'] = self.url(f['action'])

        out = str(soup)
        for ph in COMPANY_PHONES:
            out = out.replace(ph, L['contact']['phone'])
        for num in COMPANY_NUMBERS:
            out = out.replace('+' + num, L['contact']['tel']).replace('wa.me/' + num, 'wa.me/' + L['contact']['wa'])
        return add_alternates(out, alternates)


GCC = ['United Arab Emirates', 'Saudi Arabia', 'Qatar', 'Kuwait', 'Bahrain', 'Oman', 'Iraq', 'Libya', 'Syria']


def ld_lang(data, lang):
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if k == 'inLanguage':
                out[k] = lang
            else:
                out[k] = ld_lang(v, lang)
        if lang == 'en' and out.get('@type') in ('Organization', 'LocalBusiness') and 'areaServed' not in out:
            out['areaServed'] = [{'@type': 'Country', 'name': c} for c in GCC]
        return out
    if isinstance(data, list):
        return [ld_lang(x, lang) for x in data]
    return data


def add_alternates(html, alternates):
    """alternates: {'ar': path, 'en': path, ...} -> hreflang links + the header language switch."""
    if not alternates:
        return html
    links = ''.join(f'<link rel="alternate" hreflang="{l}" href="{SITE}{p}">' for l, p in alternates.items())
    links += f'<link rel="alternate" hreflang="x-default" href="{SITE}{alternates["ar"]}">'
    html = re.sub(r'<link rel="alternate" hreflang="[^"]*" href="[^"]*"/?>', '', html)
    html = html.replace('</head>', links + '</head>', 1)
    m = re.search(r'<html[^>]*\blang="([a-z]+)"', html)
    cur = m.group(1) if m else 'ar'
    items = []
    for l in ('ar', 'en', 'tr'):
        if l == cur or l not in alternates:
            continue
        meta = AR_LANG if l == 'ar' else LANGS[l]
        items.append(f'<a href="{alternates[l]}" hreflang="{l}" lang="{l}" title="{meta["name"]}">{meta["short"] if l != "ar" else "عربي"}</a>')
    sw = ''.join(items)
    return re.sub(r'(<nav(?=[^>]*\bclass="m-lang[" ])[^>]*>)(.*?)(</nav>)', lambda m: m.group(1) + sw + m.group(3), html, flags=re.S)


# ---------------------------------------------------------------- URLs per language
class PathMap:
    """Arabic path -> translated path, per language. Slugs are kept in data/i18n/slugs.json
    once assigned, so a translated URL never changes when its wording is improved later."""

    def __init__(self, root):
        self.root = root
        self.file = os.path.join(root, 'data/i18n/slugs.json')
        self.saved = json.load(open(self.file, encoding='utf-8')) if os.path.exists(self.file) else {}
        self.map = {}       # lang -> {ar_path: lang_path}
        self.listing = {}   # lang -> {ar_base: lang_base}
        self.collect_all = os.environ.get('I18N_COLLECT') == '1'

    def save(self):
        if self.collect_all:
            return
        json.dump({l: dict(sorted(v.items())) for l, v in self.saved.items()}, open(self.file, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=0)

    def assign(self, lang, items, mems):
        """items: dicts {path, kind (home|page|shop|search|cat|product), name, parent, sku}, parents first."""
        L = LANGS[lang]
        saved = self.saved.setdefault(lang, {})
        mp = self.map.setdefault(lang, {})
        used = set(saved.values())
        mem = mems[lang]
        for it in items:
            p = it['path']
            if p in saved:
                mp[p] = saved[p]
                continue
            kind = it['kind']
            if kind == 'home':
                new = L['root']
            elif kind in ('shop', 'search'):
                new = L['root'] + L['seg'][kind] + '/'
            else:
                tname = mem.get(it['name'])
                if tname is None or has_ar(tname):
                    if not self.collect_all:
                        continue  # not translated yet: not published in this language
                    tname = it.get('sku') or key(it['name'])  # dry run: collect every text, save nothing
                last = up.unquote(p).strip('/').split('/')[-1]
                if kind == 'page' and lang == 'en' and re.fullmatch(r'[a-z0-9-]+', last):
                    slug = last
                else:
                    slug = slugify(tname, lang)
                if kind == 'product':
                    base = L['root'] + L['seg']['product'] + '/'
                elif kind == 'cat':
                    parent = it.get('parent')
                    base = (mp.get(parent) if parent else None) or (L['root'] + L['seg']['category'] + '/')
                    if parent and parent not in mp:
                        continue
                else:
                    parent = it.get('parent')
                    if parent and parent not in mp:
                        continue
                    base = mp[parent] if parent else L['root']
                new = base + slug + '/'
                if new in used:
                    extra = slugify(it.get('sku') or '', lang) if it.get('sku') else ''
                    new = base + slug + ('-' + extra if extra and extra != 'item' else '') + '/'
                    i = 2
                    while new in used:
                        new = base + f'{slug}-{i}/'
                        i += 1
            saved[p] = new
            used.add(new)
            mp[p] = new

    def lang_path(self, ar_path, lang):
        mp = self.map.get(lang, {})
        p = ar_path
        if p in mp:
            return mp[p]
        dec = up.unquote(p)
        for cand in (dec, up.quote(dec, safe='/'), up.quote(dec, safe='/').lower()):
            if cand in mp:
                return mp[cand]
        m = re.match(r'^(.*/)page/(\d+)/$', dec)
        if m:
            base = self.lang_path(m.group(1), lang)
            if base:
                return base + LANGS[lang]['seg']['page'] + f'/{m.group(2)}/'
        return None
