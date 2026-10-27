"""Image variants for the static site.

Originals stay at their WordPress paths (/wp-content/uploads/...), so old image URLs keep working.
Variants are WebP files written next to them:  name-430x430.webp (cropped), name-700w.webp (fit width).
Sized JPEG/PNG names that old page content links to (name-768x768.jpg ...) are recreated the WordPress way.
Generated files are cached in cache/img and reused between builds.
"""
import os
import re
import shutil
import urllib.parse as up
from concurrent.futures import ProcessPoolExecutor

from PIL import Image, ImageOps

MEDIA = CACHE = None
_jobs = {}      # url -> (kind, src_file, w, h)
_dims = {}


def setup(media, cache):
    global MEDIA, CACHE
    MEDIA, CACHE = media, os.path.join(cache, 'img')
    os.makedirs(CACHE, exist_ok=True)


def local_url(src):
    p = up.urlsplit(src).path if src.startswith('http') else src
    return p


def _file(url):
    return os.path.join(MEDIA, up.unquote(url).lstrip('/'))


def _size(path):
    if path not in _dims:
        with Image.open(path) as im:
            _dims[path] = ImageOps.exif_transpose(im).size if im.getexif().get(0x0112) else im.size
    return _dims[path]


def _stem(url):
    base, ext = os.path.splitext(url)
    return base, ext


def variant(src, w, h):
    """Cropped square-ish thumbnail (WooCommerce thumbnail style)."""
    url = local_url(src)
    f = _file(url)
    if not os.path.exists(f):
        return url
    base, _ = _stem(url)
    out = f'{base}-{w}x{h}.webp'
    _jobs[out] = ('crop', f, w, h)
    return out


def fit(src, w):
    url = local_url(src)
    f = _file(url)
    if not os.path.exists(f):
        return {'url': url, 'w': w, 'h': w}
    ow, oh = _size(f)
    if ow <= w:
        tw, th = ow, oh
    else:
        tw, th = w, round(oh * w / ow)
    base, _ = _stem(url)
    out = f'{base}-{w}w.webp'
    _jobs[out] = ('fit', f, tw, th)
    return {'url': out, 'w': tw, 'h': th}


def _make(job):
    out_url, (kind, src, w, h), cache = job
    dst = os.path.join(cache, up.unquote(out_url).lstrip('/'))
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return out_url
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        has_alpha = im.mode in ('RGBA', 'LA', 'P') and 'transparency' in im.info or im.mode in ('RGBA', 'LA')
        im = im.convert('RGBA' if has_alpha else 'RGB')
        if kind == 'crop' or kind == 'wpcrop':
            im = ImageOps.fit(im, (w, h), Image.LANCZOS, centering=(0.5, 0.5))
        else:
            im = im.resize((w, h), Image.LANCZOS) if (w, h) != im.size else im
        ext = os.path.splitext(dst)[1].lower()
        if ext == '.webp':
            im.save(dst, 'WEBP', quality=82, method=5)
        elif ext in ('.jpg', '.jpeg'):
            im.convert('RGB').save(dst, 'JPEG', quality=84, optimize=True, progressive=True)
        elif ext == '.png':
            im.save(dst, 'PNG', optimize=True)
        else:
            im.save(dst)
    return out_url


SIZED = re.compile(r'(/wp-content/uploads/[^"\'\s)<>,]+?)-(\d+)x(\d+)(\.(?:jpe?g|png|webp|gif))', re.I)


def scan_sized(out_dir):
    """Find WordPress-sized image names linked from the built HTML that don't exist yet."""
    found = 0
    for root, _, files in os.walk(out_dir):
        if os.path.join(out_dir, 'wp-content') in root:
            continue
        for fn in files:
            if not fn.endswith(('.html', '.css', '.js')):
                continue
            t = open(os.path.join(root, fn), encoding='utf-8', errors='ignore').read()
            for m in SIZED.finditer(t):
                url = m.group(0)
                if url in _jobs or os.path.exists(_file(url)):
                    continue
                orig = m.group(1) + m.group(4)
                f = _file(orig)
                if not os.path.exists(f):
                    # WordPress "-scaled" originals
                    alt = _file(m.group(1) + '-scaled' + m.group(4))
                    if not os.path.exists(alt):
                        continue
                    f = alt
                _jobs[url] = ('wpcrop', f, int(m.group(2)), int(m.group(3)))
                found += 1
    return found


def export(out_dir, copy_media=True):
    scan_sized(out_dir)
    jobs = [(u, j, CACHE) for u, j in _jobs.items()]
    with ProcessPoolExecutor() as ex:
        list(ex.map(_make, jobs, chunksize=16))
    if copy_media:
        src = os.path.join(MEDIA, 'wp-content')
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(out_dir, 'wp-content'), dirs_exist_ok=True)
    gen = os.path.join(CACHE, 'wp-content')
    if os.path.isdir(gen):
        shutil.copytree(gen, os.path.join(out_dir, 'wp-content'), dirs_exist_ok=True)
    return len(jobs)
