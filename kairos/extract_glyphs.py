"""Cut the KAIRŌS wordmark out of the logo image into per-letter transparent PNGs."""
from PIL import Image
import numpy as np, json, sys

src = sys.argv[1] if len(sys.argv) > 1 else 'logo_src.jpg'
im = np.asarray(Image.open(src).convert('RGB')).astype(float)
L = im.mean(2)
bg = L[:200, :200].mean()
fg = np.percentile(L[L > 200], 90)
a = np.clip((L - bg - 6) / (fg - bg - 6), 0, 1)
FG = (250, 246, 241)

cols = (a > 0.5).any(0)
runs, s = [], None
for x, c in enumerate(cols):
    if c and s is None: s = x
    if not c and s is not None: runs.append((s, x)); s = None
names = ['K', 'A', 'I', 'R', 'O', 'S']
assert len(runs) == 6, runs
ys = np.where((a > 0.5).any(1))[0]
y0, y1 = ys.min() - 8, ys.max() + 8
meta = []

def save(n, x0, x1, ya, yb):
    rgba = np.zeros((yb - ya, x1 - x0, 4), np.uint8)
    rgba[..., :3] = FG
    rgba[..., 3] = (a[ya:yb, x0:x1] * 255).astype(np.uint8)
    Image.fromarray(rgba).save(f'glyphs/{n}.png')
    ink = np.argwhere(a[ya:yb, x0:x1] > 0.5)
    (iy0, ix0), (iy1, ix1) = ink.min(0), ink.max(0) + 1
    meta.append(dict(n=n, x=int(x0), y=int(ya), w=int(x1 - x0), h=int(yb - ya),
                     ink=[int(x0 + ix0), int(ya + iy0), int(x0 + ix1), int(ya + iy1)]))

for n, (s, e) in zip(names, runs):
    s, e = s - 6, e + 6
    if n == 'O':  # split macron from the O at the empty rows between them
        rows = (a[:, s:e] > 0.5).any(1)
        top = next(y for y in range(y0, y1) if rows[y])            # macron starts
        g0 = next(y for y in range(top, y1) if not rows[y])         # first empty row
        g1 = next(y for y in range(g0, y1) if rows[y])              # O starts
        split = (g0 + g1) // 2
        save('M', s, e, y0, split); save('O', s, e, split, y1)
    else:
        save(n, s, e, y0, y1)
json.dump(dict(bg='#%02x%02x%02x' % tuple(int(v) for v in im[:200, :200].reshape(-1, 3).mean(0)),
               baseline=int(ys.max()), glyphs=meta), open('glyphs/meta.json', 'w'), indent=1)
print(open('glyphs/meta.json').read())
