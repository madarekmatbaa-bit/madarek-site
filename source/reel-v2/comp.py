"""Place a big-framed studio shot smaller into a wider seamless backdrop (same transform for every shot)."""
import sys
from PIL import Image, ImageFilter, ImageDraw
import numpy as np
SCALE, OX, OY = .55, .102, .2935
def comp(src_path, out_path, box=(.06, .02, .70, .995)):
    src = Image.open(src_path).convert('RGB'); W, H = src.size
    a = np.array(src).astype(np.float32)
    def samp(x, y, r=60): return a[max(0, y-r):y+r, max(0, x-r):x+r].reshape(-1, 3).mean(0)
    # backdrop gradient taken from the reference shot k0 so every composite shares it
    ref = np.array(Image.open('../ai/k0_ai_v1.png').convert('RGB').resize((W, H))).astype(np.float32)
    def rs(x, y, r=60): return ref[max(0, y-r):y+r, max(0, x-r):x+r].reshape(-1, 3).mean(0)
    tl = rs(200, 150); tr = rs(W-200, 150); br = rs(W-200, H-150); bl = rs(int(W*.05), H-120)
    yy, xx = np.mgrid[0:H, 0:W]; u = xx / W; v = yy / H
    grad = (tl*((1-u)*(1-v))[..., None] + tr*(u*(1-v))[..., None] + bl*((1-u)*v)[..., None] + br*(u*v)[..., None])
    canvas = Image.fromarray(grad.clip(0, 255).astype(np.uint8))
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    d.rounded_rectangle((int(box[0]*W), int(box[1]*H), int(box[2]*W), int(box[3]*H)), radius=220, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(90))
    sw, sh = int(W*SCALE), int(H*SCALE)
    canvas.paste(src.resize((sw, sh), Image.LANCZOS), (int(OX*W), int(OY*H)), m.resize((sw, sh), Image.LANCZOS))
    canvas.save(out_path)
if __name__ == '__main__':
    comp(sys.argv[1], sys.argv[2])
