#!/usr/bin/env python3
"""One-off: turn the hard-coded colours in assets/css into role variables, so a night mode only has to
redefine the variables (Ammar 12 Nov 2026: «ضيف مود الليلي على الموقع»).

The light look does not change: every new variable is defined in base.css with the exact value it replaces.
The same colour gets a different variable per role, because navy text must turn light at night while a navy
band stays navy.

    python3 tools/tokenize_colors_2026_11_12.py [--dry]

Writes the CSS files in place, appends the light definitions to base.css and prints the night values to
paste into dark.css. Already run; kept for the record.
"""
import colorsys
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, 'assets/css')
FILES = ['base.css', 'legacy-theme.css', 'legacy-tidy.css', 'legacy-block.css', 'legacy-shop.css', 'm.css', 'i18n.css']

NAVY = {'#0d244c', 'var(--md-navy)', 'var(--sh-navy)', 'var(--navy)', 'var(--heading)', 'var(--gn)'}
BLUE_T = {'#3263db', 'var(--md-blue)', 'var(--sh-blue)', 'var(--action)', 'var(--gb)', 'var(--blue)'}
# navy backgrounds that are wide bands (stay navy at night); thin indicator lines follow the text colour;
# every other navy background is a button or a selected pill
BANDS = ('.md-table th', '.mdk-stats', '.mdk-markets', '.mdk-footer', '.footer-container', '.whb-top-bar', '.mdk-sh-hero', '.m-ftr', '.g-band', '.g-out', '.mdk-agb .agb')
LINES = ('.mdk-burger i', '.mdk-mnav-x:before', '.m-rail a:after', '.ptabs-nav button[aria-selected=true]:after')

LIT = re.compile(r'#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|var\(--[a-z0-9-]+\)|\bwhite\b')
light = {}   # token -> light value
dark = {}    # token -> night value


def rgb(h):
    h = h.lstrip('#')
    if len(h) in (3, 4):
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)), (int(h[6:8], 16) / 255 if len(h) == 8 else 1)


def hexs(r, g, b):
    return '#%02X%02X%02X' % (round(r), round(g), round(b))


def lum(h):
    (r, g, b), _ = rgb(h)
    return colorsys.rgb_to_hls(r / 255, g / 255, b / 255)[1]


def mix(a, b, t):
    (ra, ga, ba), _ = rgb(a)
    (rb, gb, bb), _ = rgb(b)
    return hexs(ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t)


D_BG, D_SURF2 = '#111A2C', '#0A111E'


def night_text(h):
    (r, g, b), _ = rgb(h)
    hh, ll, ss = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    ll2 = min(.9, max(.62, 1 - ll * .75))
    r, g, b = colorsys.hls_to_rgb(hh if ss > .03 else .61, ll2, min(ss, .22) if ss > .03 else .14)
    return hexs(r * 255, g * 255, b * 255)


def night_bg(h):
    t = min(1.3, (1 - lum(h)) / .09)
    return mix(D_BG, D_SURF2, t)


def define(tok, lv, dv):
    light.setdefault(tok, lv)
    dark.setdefault(tok, dv)
    return f'var({tok})'


def token(role, lit, sel, prop):
    v = lit.lower().replace(' ', '')
    ishex = v.startswith('#')
    if role == 'T':
        if v == '#fff' and prop == 'fill' and '.bg path' in sel:
            return 'var(--bg)'
        if v in NAVY:
            return 'var(--heading)' if v != 'var(--heading)' else None
        if v in ('var(--md-ink)', 'var(--sh-ink)', 'var(--gi)', '#3f4a5e'):
            return define('--t-ink', '#3F4A5E', '#B5BECE')
        if v == 'var(--sh-mute)' or v == '#7d8699':
            return define('--t-mute', '#7D8699', '#8792A6')
        if v in BLUE_T:
            return define('--t-blue', '#3263DB', '#8CABF8')
        if v == '#1e8e78':
            return define('--tx-1e8e78', '#1E8E78', '#3DBB9F')
        if v == '#b5523b':
            return define('--tx-b5523b', '#B5523B', '#E0806A')
        if v == '#b8becb':
            return define('--tx-b8becb', '#B8BECB', '#46526A')
        if ishex and len(v) in (4, 7) and lum(v) < .58:
            return define('--tx-' + v[1:], lit.upper(), night_text(v))
        return None
    if role == 'B':
        if v in ('#fff', '#ffffff', 'white'):
            return 'var(--bg)'
        if v in ('var(--md-cream)', 'var(--sh-cream)', 'var(--gc)', 'var(--cream)'):
            return 'var(--surface-2)'
        if v in NAVY:
            if any(b in sel for b in BANDS):
                return define('--b-navy', '#0D244C', '#0B1E42')
            if any(l in sel for l in LINES):
                return 'var(--heading)'
            return define('--btn-navy', '#0D244C', '#26499A')
        if v == '#13306a':
            return define('--btn-navy-h', '#13306A', '#2F58B4')
        m = re.fullmatch(r'rgba\(255,255,255,(\.9\d?)\)', v)
        if m:
            a = m.group(1)
            return define('--bg-a' + a[1:], f'rgba(255,255,255,{a})', f'rgba(17,26,44,{a})')
        if v == 'rgba(237,234,229,0)':
            return define('--bx-cream-0', v, 'rgba(10,17,30,0)')
        if v == 'rgba(247,246,242,0)':
            return define('--bx-wallhi-0', v, 'rgba(22,33,54,0)')
        if ishex and len(v) == 9 and v.startswith('#fbfaf7'):
            a = int(v[7:9], 16) / 255
            return define('--bx-' + v[1:], lit, 'rgba(17,26,44,%.2f)' % a)
        if ishex and len(v) in (4, 7) and lum(v) > .8:
            return define('--bx-' + v[1:], lit.upper(), night_bg(v))
        return None
    if role == 'L':
        if v in NAVY:
            return define('--l-navy', '#0D244C', '#6D8FE6')
        if v in ('var(--md-line)', 'var(--gl)'):
            return define('--lx-dcd8d1', '#DCD8D1', '#25324A')
        if v == 'var(--sh-line)':
            return define('--lx-e3dfd8', '#E3DFD8', '#25324A')
        m = re.fullmatch(r'rgba\(13,36,76,\.(\d+)\)', v)
        if m:
            a = float('.' + m.group(1))
            return define('--la-' + m.group(1), v, 'rgba(255,255,255,%.2f)' % (a + .03))
        if ishex and len(v) in (4, 7) and v not in ('#fff', '#ffffff') and lum(v) > .7:
            (r, g, b), _ = rgb(v)
            bluish = b - r > 12
            return define('--lx-' + v[1:], lit.upper(), '#2C3B59' if bluish else ('#1C273B' if lum(v) > .92 else '#25324A'))
        return None
    if role == 'S':
        if ishex and len(v) in (4, 7) and v not in ('#fff', '#ffffff') and lum(v) > .7:
            return define('--lx-' + v[1:], lit.upper(), '#25324A')
        if v == 'var(--md-cream)':
            return 'var(--surface-2)'
        if v in ('var(--heading)', 'var(--navy)'):
            return define('--l-navy', '#0D244C', '#6D8FE6')
    return None


def role_of(p):
    if p in ('color', '-webkit-text-fill-color', 'caret-color', 'fill', 'stroke', 'text-decoration-color'):
        return 'T'
    if p.startswith('background'):
        return 'B'
    if p.startswith('border') or p.startswith('outline') or p == 'column-rule':
        return 'L'
    if 'shadow' in p:
        return 'S'
    return None


def process(css):
    n = 0
    urls = []

    def stash(m):
        urls.append(m.group(0))
        return f'\x00{len(urls) - 1}\x00'

    css = re.sub(r'url\((?:"[^"]*"|\'[^\']*\'|[^)]*)\)', stash, css)

    def block(m):
        nonlocal n
        sel, body = m.group(1), m.group(2)
        if '.ms-' in sel or '.mdk-reel' in sel or '.rl-' in sel:   # the opening film keeps its day colours: its frames are pictures
            return m.group(0)
        out = []
        for d in body.split(';'):
            if ':' not in d or '/*' in d:
                out.append(d)
                continue
            p, v = d.split(':', 1)
            role = role_of(p.strip().lower())
            if not role:
                out.append(d)
                continue

            def rep(mm):
                nonlocal n
                t = token(role, mm.group(0), sel, p.strip().lower())
                if t:
                    n += 1
                    return t
                return mm.group(0)
            out.append(p + ':' + LIT.sub(rep, v))
        return sel + '{' + ';'.join(out) + '}'

    css = re.sub(r'([^{}]+)\{([^{}]*)\}', block, css)
    css = re.sub(r'\x00(\d+)\x00', lambda m: urls[int(m.group(1))], css)
    return css, n


def pages(dry):
    """The same pass over the <style> blocks that live inside the page content."""
    import json
    fp = os.path.join(ROOT, 'content/pages-raw.json')
    raw = open(fp, encoding='utf-8').read()
    data = json.loads(raw)
    total = 0

    def walk(x):
        nonlocal total
        if isinstance(x, str):
            def st(m):
                nonlocal total
                new, n = process(m.group(2))
                total += n
                return m.group(1) + new + m.group(3)
            return re.sub(r'(<style[^>]*>)(.*?)(</style>)', st, x, flags=re.S)
        if isinstance(x, list):
            return [walk(y) for y in x]
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        return x
    data = walk(data)
    have = open(os.path.join(CSS, 'base.css'), encoding='utf-8').read()
    new_l = {k: v for k, v in light.items() if (k + ':') not in have}
    print('pages', total, 'new tokens', len(new_l))
    print('LIGHT ' + ';'.join(f'{k}:{v}' for k, v in sorted(new_l.items())))
    print('NIGHT ' + ';'.join(f'{k}:{dark[k]}' for k in sorted(new_l)))
    if not dry:
        indent = 1 if raw.startswith('[\n') or raw.startswith('{\n') else None
        json.dump(data, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=indent)


def main():
    dry = '--dry' in sys.argv
    if '--pages' in sys.argv:
        return pages(dry)
    total = 0
    for f in FILES:
        fp = os.path.join(CSS, f)
        src = open(fp, encoding='utf-8').read()
        new, n = process(src)
        total += n
        print(f, n)
        if not dry:
            open(fp, 'w', encoding='utf-8').write(new)
    lt = ';'.join(f'{k}:{v}' for k, v in sorted(light.items()))
    dk = ';'.join(f'{k}:{v}' for k, v in sorted(dark.items()))
    print('total', total, 'tokens', len(light))
    print('\nLIGHT\n' + lt + '\n\nNIGHT\n' + dk)
    if not dry:
        fp = os.path.join(CSS, 'base.css')
        s = open(fp, encoding='utf-8').read()
        mark = '*,*::before,*::after{box-sizing:border-box}'
        assert mark in s
        s = s.replace(mark, '/* role colours: the same value per role in the day look; dark.css redefines them for the night look */\n:root{' + lt + '}\n' + mark, 1)
        open(fp, 'w', encoding='utf-8').write(s)


if __name__ == '__main__':
    main()
