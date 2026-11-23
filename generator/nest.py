# Motorised elbow model generator
# Author: Sandheep Rajendran  ·  License: MIT
"""Raster nesting: bottom-left-fill on a strip, trying many strip heights, rotations and part orders.
Minimises the bounding rectangle (sheet) area. Parts keep >= GAP between them and MARGIN to the sheet edge."""
import math, random, json, time, hashlib
import numpy as np
from PIL import Image, ImageDraw
from scipy.signal import fftconvolve
from scipy.ndimage import binary_dilation
from shapely import affinity

GAP, MARGIN = 2.5, 3.0

def raster(geom, res):
    """filled outline (holes ignored) -> bool mask, plus the geometry's min corner"""
    minx, miny, maxx, maxy = geom.bounds
    w = int(math.ceil((maxx - minx) / res)) + 2; h = int(math.ceil((maxy - miny) / res)) + 2
    im = Image.new("1", (w, h), 0); d = ImageDraw.Draw(im)
    gs = geom.geoms if hasattr(geom, "geoms") else [geom]
    for g in gs:
        d.polygon([((x - minx) / res + 1, (y - miny) / res + 1) for x, y in g.exterior.coords], fill=1, outline=1)
    return np.array(im, dtype=bool), (minx - res, miny - res)

def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]; return x * x + y * y <= r * r

class Shape:
    def __init__(self, name, geom, rots, res):
        self.name, self.variants = name, []
        for a in rots:
            g = affinity.rotate(geom, a, origin=(0, 0))
            m, org = raster(g, res)
            self.variants.append((a, m, org))

def nest_strip(shapes, order, H, res, Lmax):
    gpx, mpx = int(math.ceil(GAP / res)), int(math.ceil(MARGIN / res))
    Hp, Lp = int(H / res), int(Lmax / res)
    occ = np.zeros((Hp, Lp), dtype=np.float32)
    occ[:mpx, :] = 1; occ[-mpx:, :] = 1; occ[:, :mpx] = 1
    k = disk(gpx); placed = []; right = 0
    for idx in order:
        sh = shapes[idx]; best = None
        for a, m, org in sh.variants:
            h, w = m.shape
            if h > Hp - 2 * mpx: continue
            coll = fftconvolve(occ, m[::-1, ::-1].astype(np.float32), mode="valid") > 0.5
            if coll.all(): continue
            ii, jj = np.nonzero(~coll)
            score = (jj + w) * 100000 + ii           # leftmost right-edge first, then lowest
            t = np.argmin(score); i, j = ii[t], jj[t]
            cand = (j + w, i, a, m, org, i, j)
            if best is None or cand[:2] < best[:2]: best = cand
        if best is None: return None
        _, _, a, m, org, i, j = best
        dm = binary_dilation(np.pad(m, gpx), structure=k)
        i0, j0 = i - gpx, j - gpx
        si, sj = max(0, -i0), max(0, -j0)
        sub = dm[si:, sj:]; ei, ej = min(Hp, i0 + dm.shape[0]), min(Lp, j0 + dm.shape[1])
        occ[i0 + si:ei, j0 + sj:ej] = np.maximum(occ[i0 + si:ei, j0 + sj:ej], sub[:ei - i0 - si, :ej - j0 - sj])
        right = max(right, j + m.shape[1])
        placed.append(dict(name=sh.name, rot=a, x=j * res - org[0], y=i * res - org[1]))
    L = right * res + MARGIN
    return L, placed

def nest(parts, small_rots=range(0, 360, 15), big_rots=(0, 90, 180, 270), big=("backboard", "base"),
         H_range=(150, 330, 10), tries=8, res=1.0, Lmax=520, seed=1):
    random.seed(seed)
    shapes = [Shape(p.name, p.cut, big_rots if p.name in big else small_rots, res) for p in parts]
    areas = [p.cut.area for p in parts]
    base_order = sorted(range(len(parts)), key=lambda i: -areas[i])
    best = None; t0 = time.time()
    for H in range(*H_range):
        for t in range(tries):
            order = base_order[:] if t == 0 else base_order[:2] + random.sample(base_order[2:], len(base_order) - 2)
            if t > 0 and random.random() < 0.3: order[0], order[1] = order[1], order[0]
            r = nest_strip(shapes, order, H, res, Lmax)
            if r is None: continue
            L, placed = r
            # tighten H to what is actually used
            Hused = max_y(placed, parts) + MARGIN
            area = L * Hused
            if best is None or area < best[0]:
                best = (area, L, Hused, H, order, placed)
    print(f"nesting search {time.time() - t0:.0f}s; best sheet {best[1]:.0f} x {best[2]:.0f} mm (strip H {best[3]})")
    return best

def max_y(placed, parts):
    P = {p.name: p for p in parts}; m = 0
    for pl in placed:
        g = affinity.translate(affinity.rotate(P[pl["name"]].cut, pl["rot"], origin=(0, 0)), pl["x"], pl["y"])
        m = max(m, g.bounds[3])
    return m


if __name__ == "__main__":
    # Re-nest all parts and save the layout used by make_arm.py (takes a few minutes).
    import os, json
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, "make_arm.py")).read()
    exec(src[:src.index("# No engraving")])
    best = nest(parts, small_rots=range(0, 360, 10), H_range=(205, 300, 5), tries=10, res=1.0)
    area, L, Hu, H, order, placed = best
    json.dump(dict(L=L, H=Hu, placed=placed), open(os.path.join(here, "out/nest_best.json"), "w"))
    print(f"saved out/nest_best.json  ({L:.0f} x {Hu:.0f} mm)")
