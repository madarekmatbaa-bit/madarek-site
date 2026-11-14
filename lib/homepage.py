"""Home page: less writing on screen, with every word still in the page (Ammar 14 Nov 2026: «قلل الكتابة بدون ما تاثر على ال seo»).

Long text and the details under each point go into <details>: the heading stays visible and the paragraph opens on a tap.
Nothing is removed from the HTML, so search engines read the same text as before. Google's spam policies name accordions
and tabs as fine: https://developers.google.com/search/docs/essentials/spam-policies#hidden-text-and-links

The «why» points and the steps are written open (`open data-wide`): site.js closes them on phones and keeps them open on
wide screens, so a browser without scripts shows all the text.
"""
import re

# the studio shot of the product family (tools/studio); the build turns it into WebP sizes with a srcset
FAMILY = ('/wp-content/uploads/2026/11/mdk-studio-family.png', 'منتجات مطبوعة بشعار مدارك: ملف، دفتر، ترمس، علبة هدايا، علم مكتبي، قبعة، مقلمة ودرع تكريم')


def _must(n, what):
    if not n:
        raise SystemExit(f'home: {what} changed, so its folded form has no place')


def fold_seo(html):
    """The long text at the end of the page: three headings, each opens its text."""
    html, n = re.subn(r'<div class="mdk-seo-col"><h3>(.*?)</h3><p>(.*?)</p></div>',
                      r'<details class="mdk-seo-col"><summary><h3>\1</h3></summary><p>\2</p></details>', html, flags=re.S)
    _must(n == 3, 'the long text section')
    html, n = re.subn(r'<div class="mdk-seo-more">.*?</div>', '', html, count=1, flags=re.S)
    _must(n, 'the «read more» button')
    html, n = re.subn(r'(<section class="mdk mdk-sec mdk-seo) is-folded"', r'\1"', html, count=1)
    _must(n, 'the long text section tag')
    return html


def fold_why(html):
    """«أكثر من مطبعة»: the studio shot of the product family beside the heading, and each point opens its line."""
    html, n = re.subn(r'<li><h3>(.*?)</h3><p>(.*?)</p></li>', r'<li><details open data-wide><summary><h3>\1</h3></summary><p>\2</p></details></li>', html, flags=re.S)
    _must(n == 4, 'the «why» list')
    src, alt = FAMILY
    shot = f'<div class="mdk-why2-shot"><img alt="{alt}" data-sizes="(max-width: 860px) 92vw, 560px" decoding="async" loading="lazy" src="{src}"/></div>'
    html, n = re.subn(r'<div class="mdk-why2-grid"><div>(.*?)</div>(<ul class="mdk-why2-list">)',
                      lambda m: f'<div class="mdk-why2-grid"><div class="mdk-why2-hd">{m.group(1)}</div>{shot}{m.group(2)}', html, count=1, flags=re.S)
    _must(n, 'the «why» section')
    return html


def fold_steps(html):
    """The five steps: number and name stay, the line under each opens on a tap."""
    html, n = re.subn(r'<div class="mdk-step">(<span aria-hidden="true" class="n"></span><h3>.*?</h3>)<p>(.*?)</p></div>',
                      r'<details class="mdk-step" open data-wide><summary>\1</summary><p>\2</p></details>', html, flags=re.S)
    _must(n == 5, 'the steps')
    return html
