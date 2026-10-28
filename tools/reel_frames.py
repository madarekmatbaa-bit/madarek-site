"""Turn the hero video clips into scroll-scrubbed WebP frame sequences.

Usage:
  python3 tools/reel_frames.py OUT_DIR clip1.mp4 clip2.mp4 still3.png [--fps 12]

A still image counts as a one-frame clip (the page gives it a slow camera move).

Writes, for every clip i:
  OUT_DIR/d/c{i}_{n:03d}.webp   desktop, full 16:9 frame
  OUT_DIR/m/c{i}_{n:03d}.webp   mobile, cropped to where the objects sit
and OUT_DIR/manifest.json with the frame counts and sizes.
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image

D_W, D_Q = 1440, 72          # desktop frames
M_CROP, M_W, M_Q = (0.05, 0.04, 0.61, 1.0), 760, 70   # mobile: the part of the frame where the objects sit


def frames(mp4, fps, tmp):
    """Frames of a clip; a still image (.png/.jpg/.webp) counts as a one-frame clip."""
    if mp4.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        return [mp4]
    os.makedirs(tmp, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp4, '-vf', f'fps={fps}', os.path.join(tmp, 'f_%04d.png')],
                   check=True)
    return sorted(os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith('.png'))


def main():
    args = sys.argv[1:]
    fps = 12
    if '--fps' in args:
        i = args.index('--fps')
        fps = float(args[i + 1])
        del args[i:i + 2]
    out, clips = args[0], args[1:]
    for k in ('d', 'm'):
        os.makedirs(os.path.join(out, k), exist_ok=True)
    man = {'clips': [], 'fps': fps}
    total = {'d': 0, 'm': 0}
    for ci, mp4 in enumerate(clips):
        with tempfile.TemporaryDirectory() as tmp:
            pngs = frames(mp4, fps, tmp)
            for n, p in enumerate(pngs):
                im = Image.open(p).convert('RGB')
                w, h = im.size
                # every source becomes exactly 16:9 so stills and clips line up
                if abs(w / h - 16 / 9) > 0.002:
                    if w / h > 16 / 9:
                        nw = round(h * 16 / 9); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
                    else:
                        nh = round(w * 9 / 16); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
                    w, h = im.size
                d = im.resize((D_W, round(D_W * h / w)), Image.LANCZOS)
                dp = os.path.join(out, 'd', f'c{ci}_{n:03d}.webp')
                d.save(dp, 'WEBP', quality=D_Q, method=6)
                m = im.crop((round(w * M_CROP[0]), round(h * M_CROP[1]), round(w * M_CROP[2]), round(h * M_CROP[3])))
                m = m.resize((M_W, round(M_W * m.size[1] / m.size[0])), Image.LANCZOS)
                mp = os.path.join(out, 'm', f'c{ci}_{n:03d}.webp')
                m.save(mp, 'WEBP', quality=M_Q, method=6)
                total['d'] += os.path.getsize(dp)
                total['m'] += os.path.getsize(mp)
            man['clips'].append({'n': len(pngs), 'src': os.path.basename(mp4)})
            man['d'] = [D_W, d.size[1]]
            man['m'] = [M_W, m.size[1]]
            man['mcrop'] = list(M_CROP)
    man['bytes'] = total
    json.dump(man, open(os.path.join(out, 'manifest.json'), 'w'), indent=1)
    print(json.dumps(man))


if __name__ == '__main__':
    main()
