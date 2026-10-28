"""Hide AI-garbled logos on objects while they move: inpaint the marks for a frame range,
fading the clean version in and out so nothing pops.

python3 logo_clean.py in.mp4 out.mp4 MODE a b ramp x0 y0 x1 y1
  MODE  white   : white marks on navy objects (box, folder)
        navy    : navy marks on white objects (paper bag)
  a b   : seconds where the cleaned look is fully on; ramp = seconds of fade before/after
  x0..y1: region as fractions of the frame
"""
import subprocess
import sys

import cv2
import numpy as np

src, dst, mode = sys.argv[1], sys.argv[2], sys.argv[3]
a, b, ramp = map(float, sys.argv[4:7])
x0, y0, x1, y1 = map(float, sys.argv[7:11])

cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS)
W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
                         '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', dst],
                        stdin=subprocess.PIPE)
region = np.zeros((H, W), np.uint8)
region[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = 1


def clean(fr):
    hsv = cv2.cvtColor(fr, cv2.COLOR_BGR2HSV)
    b_, g_, r_ = [fr[..., i].astype(int) for i in range(3)]
    navy = ((b_ - r_ > 30) & (r_ < 110) & (hsv[..., 2] < 170)).astype(np.uint8)
    if mode == 'white':
        body = cv2.morphologyEx(navy, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
        marks = (hsv[..., 2] > 120) & (hsv[..., 1] < 110) & (body > 0) & (navy == 0)
    else:
        white = ((hsv[..., 2] > 170) & (hsv[..., 1] < 40)).astype(np.uint8)
        body = cv2.morphologyEx(white, cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(navy)
        small = np.zeros_like(navy)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < 0.004 * W * H:   # logo strokes, not the box itself
                small[lab == i] = 1
        blueish = ((b_ - r_ > 18) & (hsv[..., 2] < 235)).astype(np.uint8)   # light-blue lines
        marks = ((small > 0) | (blueish > 0)) & (body > 0)
    m = (marks & (region > 0)).astype(np.uint8) * 255
    m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=2)
    return cv2.inpaint(fr, m, 5, cv2.INPAINT_TELEA)


i = 0
while True:
    ok, fr = cap.read()
    if not ok:
        break
    t = i / fps
    w = 0.0
    if a - ramp <= t <= b + ramp:
        w = 1.0 if a <= t <= b else (1 - (a - t) / ramp if t < a else 1 - (t - b) / ramp)
    if w > 0:
        c = clean(fr)
        fr = cv2.addWeighted(c, w, fr, 1 - w, 0)
    proc.stdin.write(fr.tobytes())
    i += 1
proc.stdin.close()
proc.wait()
print(dst, i, 'frames', fps, 'fps')
