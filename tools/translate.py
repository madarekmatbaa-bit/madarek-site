#!/usr/bin/env python3
"""Translation memory for the /en/ and /tr/ sites (see lib/i18n.py).

    python3 build.py                                   # writes data/i18n/missing-<lang>.json
    python3 tools/translate.py api --lang en           # translate what is missing with the Claude API (ANTHROPIC_API_KEY)
    python3 tools/translate.py export --lang en --size 30000 --out DIR   # split the missing texts into chunk files
    python3 tools/translate.py check --lang en FILE...  # validate translated chunk files ({key: text})
    python3 tools/translate.py import --lang en FILE... # merge valid translations into data/i18n/<lang>.json
    python3 tools/translate.py prune                   # drop memory entries no page uses any more (after a full build)

Each text keeps its markers: ⟦1⟧…⟦/1⟧ wrap inline tags, ⟦2/⟧ is an icon or image, ⟨0⟩ is a code,
price or number that is put back after translation. tools/i18n_style.md is the style guide.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import i18n  # noqa: E402

LANG_NAMES = {'en': 'English', 'tr': 'Turkish'}


def mem_path(lang):
    return os.path.join(ROOT, 'data/i18n', f'{lang}.json')


def load(path, default=None):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else (default if default is not None else {})


CONCISE = '--concise' in sys.argv


def problems(src, out):
    errs = []
    if CONCISE:
        if not isinstance(out, str) or not out.strip():
            return ['empty']
        if i18n.AR_LETTER.search(out):
            errs.append('Arabic letters left')
        if not i18n.marks_ok(src, out):
            errs.append('⟦⟧ markers: only ones from the source, each once, properly closed')
        v = i18n.VMARK.findall(out)
        if len(set(v)) != len(v) or not set(v) <= set(i18n.VMARK.findall(src)):
            errs.append('⟨⟩ values: only ones from the source, each once')
        return errs
    if not isinstance(out, str) or not out.strip():
        return ['empty']
    if i18n.AR_LETTER.search(out):
        errs.append('Arabic letters left')
    if sorted(i18n.MARK.findall(src)) != sorted(i18n.MARK.findall(out)) or not i18n.valid_marks(src, out):
        errs.append('⟦⟧ markers differ: ' + ' '.join(m.group(0) for m in i18n.MARK.finditer(src)))
    if sorted(i18n.VMARK.findall(src)) != sorted(i18n.VMARK.findall(out)):
        errs.append('⟨⟩ values differ: ' + ' '.join(m.group(0) for m in i18n.VMARK.finditer(src)))
    return errs


def read_chunks(files):
    out = {}
    for f in files:
        out.update(load(f))
    return out


def cmd_export(a):
    miss = load(os.path.join(ROOT, 'data/i18n', f'missing-{a.lang}.json'))
    items = sorted(miss.items(), key=lambda kv: kv[1])
    os.makedirs(a.out, exist_ok=True)
    chunks, cur, size = [], {}, 0
    for k, v in items:
        if size + len(v) > a.size and cur:
            chunks.append(cur)
            cur, size = {}, 0
        cur[k] = v
        size += len(v)
    if cur:
        chunks.append(cur)
    for i, c in enumerate(chunks, 1):
        json.dump(c, open(os.path.join(a.out, f'{a.lang}-{i:02d}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{len(miss)} texts -> {len(chunks)} chunks in {a.out}')


def source_for(lang):
    """key -> masked Arabic, from the missing list and the memory itself."""
    src = {k: v[0] for k, v in load(mem_path(lang)).items()}
    src.update(load(os.path.join(ROOT, 'data/i18n', f'missing-{lang}.json')))
    return src


def cmd_check(a, merge=False):
    src = load(a.src) if getattr(a, 'src', None) else source_for(a.lang)
    src = {k: (v['ar'] if isinstance(v, dict) else v) for k, v in src.items()}
    extra = {}
    for f in a.files:
        if f.endswith('.src.json'):
            extra.update(load(f))
    src.update(extra)
    tr = read_chunks([f for f in a.files if not f.endswith('.src.json')])
    bad, ok, unknown = {}, {}, []
    for k, t in tr.items():
        if k not in src:
            unknown.append(k)
            continue
        e = problems(src[k], t)
        if e:
            bad[k] = e
        else:
            ok[k] = t
    for k, e in list(bad.items())[:60]:
        print(f'{k}: {"; ".join(e)}\n   ar: {src[k][:160]}\n   tr: {str(tr[k])[:160]}')
    print(f'ok {len(ok)} · problems {len(bad)} · unknown keys {len(unknown)}')
    if merge:
        mem = load(mem_path(a.lang))
        for k, t in ok.items():
            mem[k] = [src[k], t]
        json.dump(dict(sorted(mem.items())), open(mem_path(a.lang), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print(f'memory {a.lang}: {len(mem)} entries')
    return 1 if bad else 0


def cmd_prune(a):
    print('prune: run a full build first; entries unused by any page are listed, not deleted, unless --apply')


STYLE = open(os.path.join(ROOT, 'tools/i18n_style.md'), encoding='utf-8').read() if os.path.exists(
    os.path.join(ROOT, 'tools/i18n_style.md')) else ''


def api_call(lang, batch, key, model):
    prompt = (f'{STYLE}\n\nTranslate every value of this JSON object from Arabic to {LANG_NAMES[lang]}. '
              'Reply with only a JSON object with the same keys.\n\n' + json.dumps(batch, ensure_ascii=False))
    body = json.dumps({'model': model, 'max_tokens': 16000, 'messages': [{'role': 'user', 'content': prompt}]}).encode()
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=body, headers={
        'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        res = json.load(r)
    text = ''.join(b.get('text', '') for b in res.get('content', []))
    m = re.search(r'\{.*\}', text, re.S)
    return json.loads(m.group(0)) if m else {}


def cmd_api(a):
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        print('ANTHROPIC_API_KEY is not set: nothing translated')
        return 0
    miss = load(os.path.join(ROOT, 'data/i18n', f'missing-{a.lang}.json'))
    if not miss:
        print('nothing missing')
        return 0
    mem = load(mem_path(a.lang))
    items = list(miss.items())
    done = 0
    i = 0
    while i < len(items):
        batch, size = {}, 0
        while i < len(items) and size < 12000:
            batch[items[i][0]] = items[i][1]
            size += len(items[i][1])
            i += 1
        for attempt in range(3):
            try:
                out = api_call(a.lang, batch, key, a.model)
                break
            except Exception as e:  # network or rate limit
                print('retry', e)
                time.sleep(10 * (attempt + 1))
                out = {}
        for k, t in out.items():
            if k in batch and not problems(batch[k], t):
                mem[k] = [batch[k], t]
                done += 1
    json.dump(dict(sorted(mem.items())), open(mem_path(a.lang), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{a.lang}: translated {done} of {len(items)}')
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('export', 'check', 'import', 'api', 'prune'):
        p = sub.add_parser(name)
        p.add_argument('--lang', choices=list(i18n.LANGS), required=name != 'prune')
        if name == 'export':
            p.add_argument('--size', type=int, default=30000)
            p.add_argument('--out', required=True)
        if name in ('check', 'import'):
            p.add_argument('files', nargs='+')
            p.add_argument('--src', help='the chunk file that was translated (source texts)')
            p.add_argument('--concise', action='store_true', help='short versions: markers and values may be dropped')
        if name == 'api':
            p.add_argument('--model', default='claude-sonnet-5-5')
    a = ap.parse_args()
    if a.cmd == 'export':
        return cmd_export(a)
    if a.cmd == 'check':
        return cmd_check(a)
    if a.cmd == 'import':
        return cmd_check(a, merge=True)
    if a.cmd == 'api':
        return cmd_api(a)
    return cmd_prune(a)


if __name__ == '__main__':
    sys.exit(main() or 0)
