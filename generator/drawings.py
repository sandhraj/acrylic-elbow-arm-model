# Motorised elbow model generator
# Author: Sandheep Rajendran  ·  License: MIT
"""Engineering drawing sheets for the motorised elbow model (A4 landscape PNG + one multi-page PDF)."""
import math
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle, Arc, FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages
from shapely import affinity
from shapely.geometry import Point, LineString, Polygon
from make_arm import *

AUTHOR = "Sandheep Rajendran"
DATE = "2026-11-23"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
LINE = "#111"; DIM = "#1f4e9c"; CENTER = "#999"

# ---------------------------------------------------------------- helpers
def outline(ax, g, lw=0.9, fc="none", ec=LINE, z=2, holes=True):
    gs = g.geoms if hasattr(g, "geoms") else [g]
    for p in gs:
        ax.add_patch(MPoly(list(p.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw, zorder=z))
        if holes:
            for r in p.interiors:
                ax.add_patch(MPoly(list(r.coords), closed=True, fc="white", ec=ec, lw=lw * 0.8, zorder=z + 1))

def dim_h(ax, x1, x2, y, text, off=0, ext_from=None, fs=7):
    yy = y + off
    if ext_from is not None:
        for x, y0 in ((x1, ext_from[0]), (x2, ext_from[1])):
            ax.plot([x, x], [y0, yy + (1.5 if off > 0 else -1.5)], color=DIM, lw=0.4)
    ax.annotate("", xy=(x1, yy), xytext=(x2, yy), arrowprops=dict(arrowstyle="<->", color=DIM, lw=0.6, shrinkA=0, shrinkB=0))
    ax.text((x1 + x2) / 2, yy + (1.0 if off >= 0 else -1.0), text, ha="center", va="bottom" if off >= 0 else "top", color=DIM, fontsize=fs,
            bbox=dict(fc="white", ec="none", pad=0.3))

def dim_v(ax, y1, y2, x, text, off=0, ext_from=None, fs=7):
    xx = x + off
    if ext_from is not None:
        for y, x0 in ((y1, ext_from[0]), (y2, ext_from[1])):
            ax.plot([x0, xx + (1.5 if off > 0 else -1.5)], [y, y], color=DIM, lw=0.4)
    ax.annotate("", xy=(xx, y1), xytext=(xx, y2), arrowprops=dict(arrowstyle="<->", color=DIM, lw=0.6, shrinkA=0, shrinkB=0))
    ax.text(xx + (1.0 if off >= 0 else -1.0), (y1 + y2) / 2, text, ha="left" if off >= 0 else "right", va="center", rotation=90, color=DIM, fontsize=fs,
            bbox=dict(fc="white", ec="none", pad=0.3))

def centermark(ax, x, y, s=3):
    ax.plot([x - s, x + s], [y, y], color=CENTER, lw=0.4, zorder=1); ax.plot([x, x], [y - s, y + s], color=CENTER, lw=0.4, zorder=1)

def classify_holes(g, origin=(0, 0)):
    """return list of dicts describing each interior ring relative to origin"""
    out = []
    for r in g.interiors:
        poly = Polygon(r); c = poly.centroid; cs = np.array(r.coords)
        rr = np.hypot(cs[:, 0] - c.x, cs[:, 1] - c.y)
        x, y = c.x - origin[0], c.y - origin[1]
        if len(cs) > 16 and rr.std() < 0.05 * rr.mean():
            out.append(dict(kind="hole", x=x, y=y, size=f"Ø{2 * rr.mean():.1f}", cx=c.x, cy=c.y))
            continue
        mrr = poly.minimum_rotated_rectangle; mc = np.array(mrr.exterior.coords)[:4]
        e1, e2 = np.linalg.norm(mc[1] - mc[0]), np.linalg.norm(mc[2] - mc[1])
        L, W = max(e1, e2), min(e1, e2)
        v = (mc[1] - mc[0]) if e1 >= e2 else (mc[2] - mc[1]); ang = math.degrees(math.atan2(v[1], v[0])) % 180
        if abs(poly.area - L * W) < 0.02 * L * W:
            if min(ang % 90, 90 - ang % 90) < 1:
                bx = poly.bounds; out.append(dict(kind="rect", x=x, y=y, size=f"{bx[2] - bx[0]:.1f} × {bx[3] - bx[1]:.1f}", cx=c.x, cy=c.y))
            else:
                out.append(dict(kind="rect", x=x, y=y, size=f"{L:.1f} × {W:.1f} @ {ang:.0f}°", cx=c.x, cy=c.y))
        else:
            out.append(dict(kind="slot", x=x, y=y, size=f"slot {W:.1f} wide × {L:.1f} long @ {ang:.0f}°", cx=c.x, cy=c.y))
    # merge identical holes into one row each but keep labels
    return out

def describe(part, hs):
    for h in hs:
        x, y, sz = h["x"], h["y"], h["size"]; k = h["kind"]
        w = ""
        if part == "upper_arm":
            w = {"rect": "servo window"}.get(k) or ("servo screw clear." if sz == "Ø2.6" else "elbow pivot" if abs(y) < .1 else
                 "bolt to backboard" if sz == "Ø3.3" else "?")
        elif part == "forearm":
            w = "elbow horn slot (M2)" if k == "slot" else "elbow pivot" if abs(y) < .1 else "wrist pivot" if y < -50 else "wrist lock"
        elif part == "hand":
            w = "wrist pivot" if abs(y) < .1 else "wrist lock"
        elif part == "backboard":
            w = ("servo window" if k == "rect" and "12.6" in sz else "gusset slot" if k == "rect" else
                 "servo screw pilot" if sz == "Ø1.6" else "elbow bolt head" if sz == "Ø7.0" else "upper arm bolt")
        elif part == "base":
            w = ("backboard tab slot" if k == "rect" and abs(y) < 5 else "gusset tab slot" if k == "rect" else
                 "knob (pot)" if y > 10 else "button")
        h["what"] = w
        if k == "slot": h["size"] = sz.replace("slot ", "").replace(" wide × ", "×").replace(" long", "")
    return hs

def hole_table(ax, x0, y0, rows, title="HOLE TABLE", w=None):
    f = lambda v: f"{(0.0 if abs(v) < 0.05 else v):.1f}"
    lines = [("ID", "X", "Y", "SIZE")] + [(r["id"], f(r['x']), f(r['y']), r["size"] + (f"  {r['what']}" if r.get('what') else "")) for r in rows]
    colx = [0, 7, 19, 31]
    ax.text(x0, y0, title, fontsize=7, fontweight="bold", va="top")
    for i, ln in enumerate(lines):
        yy = y0 - 4.2 - i * 3.6
        for cx_, t in zip(colx, ln):
            ax.text(x0 + cx_, yy, t, fontsize=6.4, va="top", fontweight="bold" if i == 0 else "normal", family="DejaVu Sans Mono")

def label_holes(ax, holes, letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ", dx=2.2, dy=2.2):
    for h, L in zip(holes, letters):
        h["id"] = L
        ax.text(h["cx"] + dx, h["cy"] + dy, L, fontsize=6.2, color="#b03a2e", fontweight="bold", zorder=9)

def sheet(title, dwg, scale="1:1 (print at 100%)", note=None):
    fig = plt.figure(figsize=(11.69, 8.27))
    ax = fig.add_axes([0.02, 0.02, 0.96, 0.96]); ax.set_xlim(0, 287); ax.set_ylim(0, 200); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 287, 200, fc="none", ec=LINE, lw=1.2))
    # title block
    tb = [(0, 0, 287, 14)]
    ax.add_patch(Rectangle((0, 0), 287, 14, fc="#f4f6f8", ec=LINE, lw=1.0))
    for xv in (110, 170, 215, 250):
        ax.plot([xv, xv], [0, 14], color=LINE, lw=0.6)
    ax.text(3, 9.5, title, fontsize=10, fontweight="bold", va="center")
    ax.text(3, 4, "Motorised elbow model (muscles & joints)  ·  3 mm acrylic  ·  units mm", fontsize=7, va="center", color="#333")
    for x, k, v in ((112, "DESIGNED BY", AUTHOR), (172, "DATE", DATE), (217, "SCALE", scale), (252, "DRAWING", dwg)):
        ax.text(x, 10.5, k, fontsize=5.8, color="#555", va="center"); ax.text(x, 4.5, v, fontsize=7.5, va="center", fontweight="bold")
    if note: ax.text(3, 17, note, fontsize=6.6, color="#444", va="bottom")
    return fig, ax

def sub(fig, rect, xlim, ylim):
    a = fig.add_axes(rect); a.set_xlim(*xlim); a.set_ylim(*ylim); a.set_aspect("equal"); a.axis("off"); return a

figs = []

# ================================================================ DWG-01 General arrangement
fig, ax = sheet("General arrangement", "DWG-01", scale="1:2 (approx.)",
                note="Arm shown at REST (straight). Horns parallel; cords tie at matching holes R16.8 on both horns. Elbow travel 0–130°, 1:1 with servo.")
a = sub(fig, [0.03, 0.12, 0.5, 0.84], (-120, 150), (-30, 225))
a.text(-118, 220, "FRONT ELEVATION (side of the arm)", fontsize=8, fontweight="bold")
outline(a, P["backboard"].cut, fc="#eef4f9")
a.add_patch(Rectangle((-45, -T), 145, T, fc="#dfe8ef", ec=LINE, lw=0.9))
outline(a, affinity.translate(P["upper_arm"].cut, 0, ELBOW_Y), fc="#f6efdc")
outline(a, affinity.translate(P["forearm"].cut, 0, ELBOW_Y), fc="#f6efdc")
outline(a, affinity.translate(P["hand"].cut, 0, ELBOW_Y - L_FORE), fc="#f9e3cf")
def horn(cx, cy, ang, L=37.5, w=5.5):
    g = unary_union([LineString([(-L / 2 + w / 2, 0), (L / 2 - w / 2, 0)]).buffer(w / 2), Point(0, 0).buffer(4.4)])
    return affinity.translate(affinity.rotate(g, ang, origin=(0, 0)), cx, cy)
outline(a, horn(0, SHOULDER_Y, HORN_REST), fc="#9a9a9a", z=5); outline(a, horn(0, ELBOW_Y, HORN_AXIS, 38, 5), fc="#666", z=5)
tip = lambda c, ang, r: (c[0] + r * math.cos(math.radians(ang)), c[1] + r * math.sin(math.radians(ang)))
S, E = (0, SHOULDER_Y), (0, ELBOW_Y)
for sgn, col in ((0, "#c0392b"), (180, "#7b241c")):
    p0, p1 = tip(S, HORN_REST + sgn, R_HORN), tip(E, HORN_AXIS + sgn, R_HORN)
    a.plot([p0[0], p1[0]], [p0[1], p1[1]], color=col, lw=1.4, zorder=8)
for c in (S, E): centermark(a, *c, 6)
dim_v(a, 0, BB_H, -35, "200", off=-18, ext_from=(-45, -35))
dim_v(a, 0, ELBOW_Y, -35, "104 (elbow)", off=-32, ext_from=(-45, -6))
dim_v(a, 0, SHOULDER_Y, -35, "174 (shoulder)", off=-46, ext_from=(-45, -6))
dim_v(a, ELBOW_Y, SHOULDER_Y, 30, "70", off=22, ext_from=(5, 5))
dim_v(a, ELBOW_Y - L_FORE, ELBOW_Y, 20, "54", off=14, ext_from=(5, 5))
dim_h(a, -35, 35, BB_H, "70", off=8, ext_from=(BB_H, BB_H))
dim_h(a, -45, 100, -T, "145", off=-12, ext_from=(-T, -T))
hp = tip(S, HORN_REST, R_HORN)
a.annotate("R16.8 (cord hole,\nboth horns)", xy=hp, xytext=(62, 186), fontsize=6.8, color=DIM, arrowprops=dict(arrowstyle="-", color=DIM, lw=0.5))
a.add_patch(Arc(S, 44, 44, theta1=HORN_REST, theta2=270, color=DIM, lw=0.6))
a.text(14, SHOULDER_Y - 26, "25°", color=DIM, fontsize=7)
a.annotate("biceps cord", xy=(9, 130), xytext=(62, 128), fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5))
a.annotate("triceps cord", xy=(-9, 150), xytext=(-110, 150), fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5))
a.annotate("MG90S behind backboard", xy=(0, SHOULDER_Y + 6), xytext=(62, 212), fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5))
a.annotate("elbow pivot M3×20", xy=E, xytext=(62, 92), fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5))
a.annotate("wrist 2× M3×10", xy=(0, ELBOW_Y - L_FORE), xytext=(62, 40), fontsize=7, arrowprops=dict(arrowstyle="-", lw=0.5))
# plan view
b = sub(fig, [0.55, 0.47, 0.43, 0.48], (-60, 115), (-60, 52))
b.text(-58, 49, "PLAN VIEW (from above)", fontsize=8, fontweight="bold")
outline(b, P["base"].cut, fc="#eef4f9")
b.add_patch(Rectangle((-BB_W / 2, BB_Z0), BB_W, T, fc="#c9d9e6", ec=LINE, lw=0.8, zorder=5))
for gx in (-GUSSET_X, GUSSET_X):
    b.add_patch(Rectangle((gx - T / 2, BB_Z0 - 40), T, 40, fc="#c9d9e6", ec=LINE, lw=0.8, zorder=5))
b.add_patch(Rectangle((-24, 0), 48, T, fc="#f6efdc", ec=LINE, lw=0.8, zorder=6))          # upper arm footprint
b.add_patch(Rectangle((-SV_W / 2, BB_Z0 - 18.4), SV_W, 18.4, fc="#333", ec=LINE, lw=0.6, zorder=6))
b.text(0, BB_Z0 - 9, "servo", color="white", ha="center", va="center", fontsize=6, zorder=7)
b.text(-GUSSET_X - 3, BB_Z0 - 20, "gusset", rotation=90, ha="right", va="center", fontsize=6.5)
b.text(40, BB_Z0 + 1.5, "backboard", va="center", fontsize=6.5)
b.text(30, 6, "upper arm", fontsize=6.5)
b.text(86, 30, "knob", ha="center", fontsize=6.5); b.text(86, -11, "button", ha="center", fontsize=6.5)
dim_h(b, -45, 100, -50, "145", off=-5, ext_from=(-50, -50))
dim_v(b, -50, 40, 100, "90", off=6, ext_from=(100, 100))
b.text(28, 45, "↑ FRONT (viewer side)", fontsize=6.5, ha="center")
# notes
c = fig.add_axes([0.56, 0.1, 0.42, 0.33]); c.axis("off")
notes = ["NOTES",
         "1. All parts laser cut from 3 mm acrylic, cut lines only. Kerf not compensated;",
         "    holes for M3 are Ø3.3 clearance, slots for 3 mm tabs are 3.2 wide.",
         "2. Layer stack, back to front: servo (behind) | backboard | upper arm |",
         "    elbow spacer | forearm | elbow horn | washer + nylock.",
         "3. Shoulder horn and elbow horn must stay parallel; set REST_DEG in code.",
         "4. Cords: braided line, tied at R16.8 on both horns; length = pivot",
         "    distance (70 mm). Glue each knot.",
         "5. Cross horn (elbow): cut off the short arms; open the centre to Ø3.",
         "6. Hand clears the base by about 13 mm when the arm hangs straight."]
for i, n in enumerate(notes):
    c.text(0, 1 - i * 0.1, n, fontsize=7.6 if i else 8.5, fontweight="bold" if i == 0 else "normal", va="top", transform=c.transAxes)
figs.append(("DWG-01_general_arrangement", fig))

# ================================================================ DWG-02 Arm parts
fig, ax = sheet("Arm parts: upper arm, forearm, hand, elbow spacer", "DWG-02", scale="1:1 on A4",
                note="Datum (0,0) = main pivot hole of each part. Outlines are exact in the DXF; use the DXF for cutting, this sheet for checking.")
MM = 1 / 287 * 0.96   # 1 mm in figure fraction (x); y fraction per mm = 0.96/200
def part_axes(x_mm, y_mm, w_mm, h_mm, xlim, ylim):
    return sub(fig, [0.02 + x_mm * 0.96 / 287, 0.02 + y_mm * 0.96 / 200, w_mm * 0.96 / 287, h_mm * 0.96 / 200], xlim, ylim)
# upper arm
ua = P["upper_arm"].cut; b_ = ua.bounds
a = part_axes(8, 30, 70, 160, (b_[0] - 11, b_[2] + 11), (b_[1] - 25, b_[1] - 25 + 160))
a.text(b_[0] - 10, b_[1] - 25 + 155, "A4  UPPER ARM ×1", fontsize=8, fontweight="bold")
outline(a, ua); centermark(a, 0, 0); centermark(a, 0, L_UPPER)
hs = describe('upper_arm', classify_holes(ua)); label_holes(a, hs)
dim_h(a, b_[0], b_[2], b_[1], f"{b_[2] - b_[0]:.0f}", off=-8, ext_from=(b_[1] + 15, b_[1] + 15))
dim_v(a, b_[1], b_[3], b_[0], f"{b_[3] - b_[1]:.0f}", off=-6, ext_from=(b_[0] + 15, b_[0] + 15))
dim_v(a, 0, L_UPPER, b_[2], f"{L_UPPER:.0f}", off=6, ext_from=(3, 3))
ua_rows = hs
# forearm
fa = P["forearm"].cut; bf = fa.bounds
a = part_axes(84, 60, 52, 130, (bf[0] - 11, bf[2] + 7), (bf[1] - 22, bf[1] - 22 + 130))
a.text(bf[0] - 10, bf[1] - 22 + 125, "A5  FOREARM ×1", fontsize=8, fontweight="bold")
outline(a, fa); centermark(a, 0, 0)
hf = describe('forearm', classify_holes(fa)); label_holes(a, hf)
dim_h(a, bf[0], bf[2], bf[1], f"{bf[2] - bf[0]:.0f}", off=-8, ext_from=(bf[1] + 12, bf[1] + 12))
dim_v(a, bf[1], bf[3], bf[0], f"{bf[3] - bf[1]:.0f}", off=-6, ext_from=(bf[0] + 10, bf[0] + 10))
dim_v(a, -L_FORE, 0, bf[2], f"{L_FORE:.0f}", off=3, ext_from=(3, 3))
for ang in (HORN_AXIS, HORN_AXIS + 180):
    x1, y1 = polar(16, ang); a.plot([0, x1], [0, y1], color=CENTER, lw=0.4, ls="--")
a.text(9, -15, "65°", color=DIM, fontsize=6.5)
a.add_patch(Arc((0, 0), 20, 20, theta1=HORN_AXIS, theta2=0, color=DIM, lw=0.5))
# hand
hd = P["hand"].cut; bh = hd.bounds
a = part_axes(140, 120, 50, 70, (bh[0] - 8, bh[2] + 8), (bh[1] - 12, bh[1] - 12 + 70))
a.text(bh[0] - 7, bh[1] - 12 + 66, "A6  HAND ×1", fontsize=8, fontweight="bold")
outline(a, hd); centermark(a, 0, 0)
hh = describe('hand', classify_holes(hd)); label_holes(a, hh)
dim_h(a, bh[0], bh[2], bh[1], f"{bh[2] - bh[0]:.0f}", off=-6, ext_from=(bh[1] + 8, bh[1] + 8))
dim_v(a, bh[1], bh[3], bh[2], f"{bh[3] - bh[1]:.0f}", off=4, ext_from=(bh[2] - 8, bh[2] - 8))
# spacer
sp = P["elbow_spacer"].cut
a = part_axes(140, 82, 30, 30, (-15, 15), (-15, 15))
a.text(-14, 12, "A7  ELBOW SPACER ×1", fontsize=8, fontweight="bold")
outline(a, sp); centermark(a, 0, 0, 7)
a.text(0, -10.5, "Ø11 outer, Ø3.3 hole", ha="center", fontsize=6.8, color=DIM)
# tables
t = fig.add_axes([0.66, 0.12, 0.33, 0.84]); t.set_xlim(0, 95); t.set_ylim(0, 200); t.axis("off")
hole_table(t, 0, 196, ua_rows, "A4 UPPER ARM  (datum: elbow hole)")
hole_table(t, 0, 196 - 6 - 3.6 * (len(ua_rows) + 1) - 6, hf, "A5 FOREARM  (datum: elbow hole)")
y_h = 196 - 12 - 3.6 * (len(ua_rows) + len(hf) + 2) - 6
hole_table(t, 0, y_h, hh, "A6 HAND  (datum: wrist hole)")
t.text(0, y_h - 3.6 * (len(hh) + 1) - 10,
       "Servo window (A4) = MG90S body 22.8 × 12.2 + 0.4 clearance.\nShaft centre is 6 mm below the window's top edge\n(i.e. at 0, 70).\nForearm slots: elbow horn lies along them,\n65° below the forearm's front, through the pivot.\nM2 bolts go through any horn holes over the slots.",
       fontsize=6.6, va="top", color="#333")
sb = part_axes(8, 20, 70, 8, (0, 70), (0, 8))
sb.add_patch(Rectangle((0, 3), 50, 1.6, fc=LINE)); [sb.add_patch(Rectangle((x, 3), 10, 1.6, fc="white", ec=LINE, lw=0.5)) for x in (10, 30)]
sb.text(0, 6, "SCALE CHECK: this bar must measure 50 mm when printed", fontsize=6.5)
figs.append(("DWG-02_arm_parts", fig))

# ================================================================ DWG-03 Frame parts
fig, ax = sheet("Frame parts: backboard, base, gussets", "DWG-03", scale="1:1.25 (approx.)",
                note="Datum (0,0): backboard = bottom-centre (top of base); base = arm plane / centre line; gusset = inner corner. Tabs and slots are 3 mm stock + 0.2.")
bb = P["backboard"].cut; bbb = bb.bounds
a = sub(fig, [0.02, 0.1, 0.3, 0.86], (bbb[0] - 22, bbb[2] + 20), (bbb[1] - 18, bbb[3] + 10))
a.text(bbb[0] - 20, bbb[3] + 6, "A2  BACKBOARD ×1", fontsize=8, fontweight="bold")
outline(a, bb); hb = describe('backboard', classify_holes(bb)); label_holes(a, hb, dx=3, dy=1.5)
dim_h(a, bbb[0], bbb[2], bbb[3], f"{bbb[2] - bbb[0]:.0f}", off=5, ext_from=(bbb[3] - 5, bbb[3] - 5))
dim_v(a, 0, BB_H, bbb[0], f"{BB_H:.0f}", off=-8, ext_from=(bbb[0] + 5, bbb[0] + 5))
dim_v(a, -T, 0, bbb[2], "3 (tabs)", off=5, ext_from=(24, 24))
dim_h(a, 8, 24, -T, "16", off=-7, ext_from=(-T, -T)); dim_h(a, -8, 8, -T, "16", off=-7, ext_from=(-T, -T))
base = P["base"].cut; bs = base.bounds
a2 = sub(fig, [0.30, 0.47, 0.40, 0.49], (bs[0] - 12, bs[2] + 12), (bs[1] - 14, bs[3] + 10))
a2.text(bs[0] - 10, bs[3] + 6, "A1  BASE ×1   (front edge = top of this view)", fontsize=8, fontweight="bold")
outline(a2, base); hbs = describe('base', classify_holes(base)); label_holes(a2, hbs, dx=2, dy=2.5)
centermark(a2, 0, 0, 5)
dim_h(a2, bs[0], bs[2], bs[1], f"{bs[2] - bs[0]:.0f}", off=-8, ext_from=(bs[1] + 4, bs[1] + 4))
dim_v(a2, bs[1], bs[3], bs[2], f"{bs[3] - bs[1]:.0f}", off=6, ext_from=(bs[2] - 4, bs[2] - 4))
gs = P["gusset_1"].cut; gb = gs.bounds
a3 = sub(fig, [0.30, 0.12, 0.2, 0.34], (gb[0] - 14, gb[2] + 12), (gb[1] - 16, gb[3] + 8))
a3.text(gb[0] - 9, gb[3] + 4, "A3  GUSSET ×2", fontsize=8, fontweight="bold")
outline(a3, gs)
dim_h(a3, 0, 40, gb[1], "40", off=-9, ext_from=(-T, -T)); dim_v(a3, 0, 75, gb[0], "75", off=-9, ext_from=(-T, -T))
dim_v(a3, G_TAB_V[0], G_TAB_V[1], -T, "tab 30", off=-1.5, fs=6)
dim_h(a3, 8, 30, -T, "tab 22", off=-3.5, fs=6)
t = fig.add_axes([0.70, 0.1, 0.29, 0.86]); t.set_xlim(0, 85); t.set_ylim(0, 200); t.axis("off")
hole_table(t, 0, 196, hb, "A2 BACKBOARD")
hole_table(t, 0, 196 - 10 - 3.6 * (len(hb) + 1), hbs, "A1 BASE")
t.text(0, 196 - 22 - 3.6 * (len(hb) + len(hbs) + 2),
       "Rectangles: SIZE = width × height.\nServo goes into the backboard\nwindow from the BACK; its two\nself-tapping screws go into the\nØ1.6 pilots.",
       fontsize=6.6, va="top", color="#333")
figs.append(("DWG-03_frame_parts", fig))

# ================================================================ DWG-04 Wiring
fig, ax = sheet("Wiring diagram (ESP8266)", "DWG-04", scale="NTS",
                note="Power the board from a USB power bank. The servo takes 5 V from VIN; the knob must use 3V3 (NodeMCU A0 accepts 0–3.3 V). No servo driver needed for one servo.")
w = sub(fig, [0.04, 0.12, 0.92, 0.84], (0, 280), (0, 170))
def box_(x, y, wd, ht, label, fc):
    w.add_patch(FancyBboxPatch((x, y), wd, ht, boxstyle="round,pad=1", fc=fc, ec=LINE, lw=1)); w.text(x + wd / 2, y + ht + 4, label, ha="center", fontsize=9, fontweight="bold")
box_(100, 40, 60, 100, "ESP8266 (NodeMCU / Wemos D1 mini)", "#e8f1f8")
pins = {"VIN": 130, "GND": 105, "D5": 95, "3V3": 80, "A0": 70, "D6": 60}
for n, y in pins.items():
    w.plot([160, 166], [y, y], color=LINE, lw=1); w.text(157, y, n, ha="right", va="center", fontsize=8.5, family="DejaVu Sans Mono")
w.text(130, 47, "USB ← power bank", ha="center", fontsize=8)
box_(215, 105, 45, 35, "MG90S servo", "#f2f2f2")
box_(215, 55, 45, 30, "10 kΩ pot (MOVE)", "#f7f2e6")
box_(215, 12, 45, 25, "Push button (DEMO)", "#f7f2e6")
def wire(pts, col, lw=1.6):
    xs, ys = zip(*pts); w.plot(xs, ys, color=col, lw=lw, solid_capstyle="round", zorder=3)
RED, BRN, ORG, BLU, GRN, PNK = "#d62728", "#6b3e26", "#f39c12", "#2e86c1", "#27ae60", "#c2185b"
wire([(166, 130), (215, 130)], RED); w.text(217, 130, "red  +5V (VIN)", va="center", fontsize=7.5)
wire([(166, 105), (182, 105), (182, 122), (215, 122)], BRN); w.text(217, 122, "brown  GND", va="center", fontsize=7.5)
wire([(166, 95), (198, 95), (198, 114), (215, 114)], ORG); w.text(217, 114, "orange  signal (D5)", va="center", fontsize=7.5)
w.plot([174, 174], [130, 119.5], color=LINE, lw=1); w.plot([170, 178], [119.5, 119.5], color=LINE, lw=1.6); w.plot([170, 178], [116.5, 116.5], color=LINE, lw=1.6)
w.plot([174, 174], [116.5, 105], color=LINE, lw=1); w.text(169, 118, "470 µF\n+ to VIN", ha="right", va="center", fontsize=6.8)
w.plot(174, 130, "o", color=LINE, ms=3); w.plot(174, 105, "o", color=LINE, ms=3)
wire([(166, 80), (204, 80), (204, 78), (215, 78)], PNK, 1.2); w.text(217, 78, "outer leg  3V3", va="center", fontsize=7.5)
wire([(166, 70), (215, 70)], BLU, 1.2); w.text(217, 70, "middle (wiper)  A0", va="center", fontsize=7.5)
wire([(182, 105), (182, 62), (215, 62)], BRN, 1.2); w.plot(182, 105, "o", color=LINE, ms=3); w.text(217, 62, "outer leg  GND", va="center", fontsize=7.5)
wire([(166, 60), (172, 60), (172, 28), (215, 28)], GRN, 1.2); w.text(217, 28, "leg 1  D6", va="center", fontsize=7.5)
wire([(182, 62), (182, 20), (215, 20)], BRN, 1.2); w.plot(182, 62, "o", color=LINE, ms=3); w.text(217, 20, "leg 2  GND", va="center", fontsize=7.5)
w.text(5, 160, "Pin summary", fontsize=9, fontweight="bold")
for i, t_ in enumerate(["Servo: signal → D5 (GPIO14), + → VIN (5 V), − → GND",
                        "Pot: wiper → A0, outer legs → 3V3 and GND (not 5 V)",
                        "Button: D6 (GPIO12) and GND, internal pull-up",
                        "Avoid D3, D4, D8: they affect booting",
                        "Dots = connections; crossing wires without",
                        "    a dot are not connected",
                        "Sketch: firmware/elbow_arm_esp8266/elbow_arm_esp8266.ino",
                        "Optional phone control: Wi-Fi \"ElbowArm\" → 192.168.4.1"]):
    w.text(5, 152 - i * 7, ("• " if not t_.startswith("    ") else "  ") + t_.strip(), fontsize=8)
figs.append(("DWG-04_wiring", fig))

with PdfPages("out/engineering_drawings.pdf") as pdf:
    for name, f in figs:
        f.savefig(f"out/{name}.png", dpi=150); pdf.savefig(f)
print("ok", [n for n, _ in figs])
