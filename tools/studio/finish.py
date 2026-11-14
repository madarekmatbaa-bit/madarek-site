"""Studio shots for the site: the raw render (transparent PNG with the floor shadow) becomes the picture the pages use.

    python3 tools/studio/finish.py <raw.png> <name> [max_px]

The floor shadow is faded out towards the edges of the frame so the picture has no visible border on a tile, the empty margin is
cropped, and the file is written to media/wp-content/uploads/2026/11/mdk-studio-<name>.png. The build makes the WebP sizes from it.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def finish(raw, name, max_px=None):
    a = np.asarray(Image.open(raw).convert('RGBA')).astype(np.float32)
    h, w = a.shape[:2]
    floor = (a[:, :, :3].max(axis=2) < 14) & (a[:, :, 3] < 250)          # the shadow catcher is black with some alpha
    fx, fy = max(8.0, w * .10), max(8.0, h * .10)
    xs = np.minimum(np.arange(w), w - 1 - np.arange(w)) / fx
    ys = np.minimum(np.arange(h), h - 1 - np.arange(h)) / fy
    ramp = np.clip(np.minimum(xs[None, :], ys[:, None]), 0, 1)
    ramp = ramp * ramp * (3 - 2 * ramp)
    # the denoiser leaves the soft shadow a little cloudy: smooth it within the floor only (a normalised blur, so the
    # shadow keeps its strength right up to the pieces standing on it)
    rad = max(2.0, w * .006)
    blur = lambda x: np.asarray(Image.fromarray(x.round().astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(rad)), dtype=np.float32)
    fm = floor.astype(np.float32)
    smooth = blur(a[:, :, 3] * fm) / np.maximum(blur(fm * 255), 1.0) * 255
    a[:, :, 3] = np.where(floor, smooth * ramp, a[:, :, 3])
    im = Image.fromarray(a.round().astype(np.uint8), 'RGBA')
    box = Image.fromarray((a[:, :, 3] > 5).astype(np.uint8) * 255).getbbox()
    pad = round(w * .012)
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(w, box[2] + pad), min(h, box[3] + pad))
    im = im.crop(box)
    if max_px and max(im.size) > max_px:
        k = max_px / max(im.size)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    out = os.path.join(ROOT, 'media/wp-content/uploads/2026/11', f'mdk-studio-{name}.png')
    im.save(out, 'PNG', optimize=True)
    print(out, im.size, os.path.getsize(out) // 1024, 'KB')
    return out


if __name__ == '__main__':
    finish(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
