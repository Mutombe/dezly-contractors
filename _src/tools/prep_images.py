"""Converts source photos into optimised WebP assets for the site."""
import os, sys
import pillow_avif  # noqa: F401
from PIL import Image, ImageFilter
import numpy as np
D = 'C:/Users/PC/Downloads/dezly/'
W = 'C:/Users/PC/AppData/Local/Temp/claude/b12d6594ad52f926/e1224ad6-9c2a-44aa-9567-d861f6c7a097/scratchpad/dl/'
OUT = 'assets/img/'
MAP = {  # out name: (source, max width)
 'hero-excavator':    (D+'AdobeStock_240944542 (1).webp', 1600),
 'hero-earthworks':   (D+'DJI_0904-1-scaled.webp', 2200),
 'hero-housing':      (D+'iStock-1304168109.jpg', 1400),
 'concrete-pour':     (D+'360_F_1659898677_Cl3XpPSK3OiAc0Dd9jCdMhWgQPJRoUaz.jpg', 900),
 'estate-aerial':     (D+'EV-CON-Aerial-Views-of-Property-Blog-Feature.webp', 1200),
 'suburb-aerial':     (D+'SNAP_NEW_LANDING_PAGE_BANNER_MAR2018.jpg', 1920),
 'interchange':       (D+'06-12-2017-0089-uai-1244x933.jpg', 1244),
 'dam':               (D+'aerial-view-of-the-hoover-dam.jpg', 2000),
 'irrigation':        (D+'WesternEnvironmentalLiner-341497-Irrigation-Canals-Agriculture-blogbanner1.jpg', 964),
 'earthworks':        (D+'a-practical-guide-to-bulk-earthworks-featured.webp', 1536),
 'quarry':            (D+'bwc-contracting-bulk-earthworks.jpg', 1500),
 'steel-frame':       (D+'iStock-1028568006-min (1).webp', 1024),
 'timber-frame':      (D+'6a5ab63d619cea6270943999_Property Developer Finance jpg.jpg', 1800),
 'estate-render':     (D+'images.jpg', 790),
 'harare':            (D+'a690ab84-4d48-41d8-84ca-a9675dda0f43.jpg', 2200),
 'hilltop-home':      (D+'-1x-1.webp', 1800),
 'villa':             (D+'000_par8321605-scaled.jpg', 1800),
 'stone-house':       (D+'2017-03-JBPM-4a.avif', 1631),
 'family-home':       (D+'23aca937e3bf8c380609088cbda6913bdd4fdb84.webp', 1600),
 'aerial-home':       (D+'BGKY7HX.jpeg', 1600),
 'treehouse-home':    (D+'vTgfLwZ.jpeg', 1800),
 'road-paving':       (D+'konstruksi-jalan___converted_1280_720.jpg', 1280),
 'asphalt-crew':      (D+'shutterstock_92209726.jpg', 1000),
 'industrial-park':   (D+'types-of-industrial-properties-savills-1.webp', 1000),
 'site-team':         (W+'c23.jpg', 1024),
 'hardhat-hand':      (W+'c24.jpg', 1024),
 'tower-cranes':      (W+'c33.jpg', 960),
 'viaduct-plate':     (W+'c19.jpg', 1024),
}
os.makedirs(OUT, exist_ok=True)
for name, (src, mw) in MAP.items():
    im = Image.open(src).convert('RGB')
    if im.width > mw:
        im = im.resize((mw, round(im.height * mw / im.width)), Image.LANCZOS)
    im.save(OUT + name + '.webp', 'WEBP', quality=80, method=6)
    print(name, im.size, os.path.getsize(OUT + name + '.webp') // 1024, 'KB')

# ---- logo: key from the black JPG, upscale 3x, build white + ink variants
lg = Image.open(D + '447307204_122144486258162337_188788513119425290_n.jpg').convert('RGB')
lg = lg.resize((lg.width * 3, lg.height * 3), Image.LANCZOS)
a = np.asarray(lg).astype(float)
bg = np.array([3, 1, 22.])
dist = np.abs(a - bg).max(-1)
alpha = np.clip((dist - 28) / 90, 0, 1)
rgb = np.clip((a - bg * (1 - alpha[..., None])) / np.maximum(alpha[..., None], 1e-3), 0, 255)
out = np.dstack([rgb, alpha * 255]).astype(np.uint8)
im = Image.fromarray(out, 'RGBA')
im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox())
im.save(OUT + 'logo-full-light.png', optimize=True)          # white + blue, for dark backgrounds
# mark-only (house + DC), top portion above wordmark
arr = np.asarray(im)
rows = (arr[..., 3] > 40).sum(1)
# find gap between mark and wordmark
gaps = [i for i in range(int(len(rows) * .55), int(len(rows) * .8)) if rows[i] == 0]
cut = gaps[0] if gaps else int(len(rows) * .72)
mark = im.crop((0, 0, im.width, cut)); mark = mark.crop(mark.getchannel('A').getbbox())
mark.save(OUT + 'logo-mark-light.png', optimize=True)
# ink variant: white -> ink, blue stays
def ink(img):
    p = np.asarray(img).astype(float)
    white = (p[..., 0] > 150) & (p[..., 1] > 150)
    p[white, 0:3] = [7, 8, 15]
    return Image.fromarray(p.astype(np.uint8), 'RGBA')
ink(im).save(OUT + 'logo-full-dark.png', optimize=True)
ink(mark).save(OUT + 'logo-mark-dark.png', optimize=True)
print('logo', im.size, 'mark', mark.size, 'cut', cut)
