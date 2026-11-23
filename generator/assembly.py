# Motorised elbow model generator
# Author: Sandheep Rajendran  ·  License: MIT
"""Exploded assembly diagram + stack sections for the horn-version arm model."""
import math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle, FancyBboxPatch
from shapely import affinity
from shapely.geometry import Point, LineString
from make_arm import *

# oblique projection: +z (toward viewer) drawn down-left
KX, KY = -0.55 * math.cos(math.radians(32)), -0.55 * math.sin(math.radians(32))
def prj(x, y, z): return (x + KX * z, y + KY * z)

PAL = dict(frame="#dfeaf3", arm="#f1e6c8", hand="#f6d7b8", ring="#c9dbe8", horn="#7d7d7d", horn2="#4f4f4f", servo="#2b2b2b")

def plate_xy(ax, g, z, fc, t=T, ec="#333", lw=0.6, zo=None, alpha=1):
    """flat plate in an XY plane at depth z..z+t"""
    gs = g.geoms if hasattr(g, "geoms") else [g]
    for p in gs:
        for zz, f, a in ((z, fc, 0.55), (z + t, fc, 1.0)):
            ext = [prj(x, y, zz) for x, y in p.exterior.coords]
            ax.add_patch(MPoly(ext, closed=True, fc=f, ec=ec, lw=lw, alpha=alpha * (0.6 if zz == z else 1), zorder=zo))
            for r in p.interiors:
                ax.add_patch(MPoly([prj(x, y, zz) for x, y in r.coords], closed=True, fc="white", ec=ec, lw=lw * 0.8, zorder=zo))

def plate_generic(ax, pts3d_list, fc, ec="#333", lw=0.6, zo=None):
    for pts in pts3d_list:
        ax.add_patch(MPoly([prj(*p) for p in pts], closed=True, fc=fc, ec=ec, lw=lw, zorder=zo))

def box3d(ax, x0, x1, y0, y1, z0, z1, fc, zo):
    P = lambda x, y, z: prj(x, y, z)
    faces = [[P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)],   # front
             [P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)],   # top
             [P(x0, y0, z0), P(x0, y1, z0), P(x0, y1, z1), P(x0, y0, z1)]]   # left side
    for f, sh in zip(faces, (1.0, 0.75, 0.6)):
        ax.add_patch(MPoly(f, closed=True, fc=fc, ec="#111", lw=0.6, alpha=1, zorder=zo))

def axis_line(ax, x, y, z0, z1, zo=0):
    a, b = prj(x, y, z0), prj(x, y, z1)
    ax.plot([a[0], b[0]], [a[1], b[1]], ls=(0, (3, 2)), color="#1f5fbf", lw=0.8, zorder=zo)

def callout(ax, n, xy, txt_xy):
    ax.annotate("", xy=xy, xytext=txt_xy, arrowprops=dict(arrowstyle="-", color="#444", lw=0.7), zorder=200)
    ax.add_patch(plt.Circle(txt_xy, 5.2, fc="#c0392b", ec="white", lw=1, zorder=201))
    ax.text(*txt_xy, str(n), ha="center", va="center", color="white", fontsize=8, fontweight="bold", zorder=202)

def horn_shape(length=37.5, w=5.5, hub=4.6):
    return unary_union([LineString([(-length / 2 + w / 2, 0), (length / 2 - w / 2, 0)]).buffer(w / 2), Point(0, 0).buffer(hub)])

fig = plt.figure(figsize=(17, 12))
ax = fig.add_axes([0.0, 0.0, 0.62, 0.95])
z_order = 0


# ------------- exploded positions -------------
Z_SERVO_TAB = -75          # servo pulled out behind the backboard (tab plane)
Z_UA, Z_SH_HORN, Z_SPACER, Z_FA, Z_EL_HORN, Z_HAND = 45, 100, 95, 140, 190, 245
BBZ = -GAP_BACK - T        # backboard back face (= -3)
sv_top_w = SHOULDER_Y + SV_SHAFT_FROM_END; sv_bot_w = sv_top_w - SV_L

# servo behind backboard (drawn first; backboard is clear acrylic so it shows through)
box3d(ax, -SV_W / 2, SV_W / 2, sv_bot_w, sv_top_w, Z_SERVO_TAB - 18.4, Z_SERVO_TAB + 4.3, PAL["servo"], zo=1)
tab = box(-SV_W / 2, (sv_top_w + sv_bot_w) / 2 - 16.25, SV_W / 2, (sv_top_w + sv_bot_w) / 2 + 16.25)
plate_xy(ax, tab, Z_SERVO_TAB - 2.5, PAL["servo"], t=2.5, zo=2)
axis_line(ax, 0, SHOULDER_Y, Z_SERVO_TAB, Z_SH_HORN + 12, zo=3)
for yy in (SV_MID_W + SV_TAB_HOLES / 2, SV_MID_W - SV_TAB_HOLES / 2):
    axis_line(ax, 0, yy, Z_SERVO_TAB - 12, BBZ + T, zo=3)

# frame: base, gussets, backboard (semi-transparent)
for yy, a_ in ((-T, 0.6), (0, 1)):
    ax.add_patch(MPoly([prj(x, yy, z) for x, z in P["base"].cut.exterior.coords], fc=PAL["frame"], ec="#333", lw=0.6, alpha=a_, zorder=4))
    for r in P["base"].cut.interiors:
        ax.add_patch(MPoly([prj(x, yy, z) for x, z in r.coords], fc="white", ec="#333", lw=0.5, zorder=4))
G = P["gusset_1"].cut
for gx in (-GUSSET_X, GUSSET_X):
    for xx in (gx - T / 2, gx + T / 2):
        ax.add_patch(MPoly([prj(xx, v, BBZ - u) for u, v in G.exterior.coords], fc=PAL["frame"], ec="#333", lw=0.6, zorder=5))
plate_xy(ax, P["backboard"].cut, BBZ, PAL["frame"], zo=6, alpha=0.55)

# assembly axes in front of the backboard
for x, y in UA_STANDOFFS:
    axis_line(ax, x, y + ELBOW_Y, BBZ, Z_UA + 12, zo=7)
axis_line(ax, 0, ELBOW_Y, BBZ, Z_EL_HORN + 14, zo=7)
axis_line(ax, 0, ELBOW_Y - L_FORE, Z_FA - 6, Z_HAND + 12, zo=7)
axis_line(ax, 0, ELBOW_Y - L_FORE + 10, Z_FA - 6, Z_HAND + 12, zo=7)

ua_world = lambda g: affinity.translate(g, 0, ELBOW_Y)
plate_xy(ax, ua_world(P["upper_arm"].cut), Z_UA, PAL["arm"], zo=40)
for l in P["upper_arm"].lines:
    ax.plot(*zip(*[prj(x, y + ELBOW_Y, Z_UA + T) for x, y in l.coords]), color="blue", lw=0.8, zorder=41)
plate_xy(ax, affinity.translate(P["elbow_spacer"].cut, 0, ELBOW_Y), Z_SPACER, PAL["ring"], zo=50)
sh = affinity.translate(affinity.rotate(horn_shape(), HORN_REST, origin=(0, 0)), 0, SHOULDER_Y)
plate_xy(ax, sh, Z_SH_HORN, PAL["horn"], t=2, zo=60)
plate_xy(ax, ua_world(P["forearm"].cut), Z_FA, PAL["arm"], zo=70)
for l in P["forearm"].lines:
    ax.plot(*zip(*[prj(x, y + ELBOW_Y, Z_FA + T) for x, y in l.coords]), color="blue", lw=0.6, zorder=71)
eh = affinity.translate(affinity.rotate(horn_shape(38, 5.0, 4.4), HORN_AXIS, origin=(0, 0)), 0, ELBOW_Y)
plate_xy(ax, eh, Z_EL_HORN, PAL["horn2"], t=2, zo=80)
plate_xy(ax, affinity.translate(P["hand"].cut, 0, ELBOW_Y - L_FORE), Z_HAND, PAL["hand"], zo=90)

def add(n, pt3, off):
    p = prj(*pt3); callout(ax, n, p, (p[0] + off[0], p[1] + off[1]))
add(1, (105, 0, 30), (20, -20))
add(2, (25, 150, BBZ + T), (40, 20))
add(3, (GUSSET_X, 15, BBZ - 40), (40, 18))
add(4, (SV_W / 2, sv_top_w, Z_SERVO_TAB - 18.4), (40, 12))
add(5, (10, ELBOW_Y + 32, Z_UA + T), (55, -8))
add(6, (-14, SHOULDER_Y + 10, Z_SH_HORN + 2), (-40, 18))
add(7, (-5, ELBOW_Y, Z_SPACER + T), (-45, 22))
add(8, (16, ELBOW_Y - 10, Z_FA + T), (45, 8))
add(9, (-7, ELBOW_Y + 15, Z_EL_HORN + 2), (-45, 14))
add(10, (14, ELBOW_Y - L_FORE - 10, Z_HAND + T), (40, -6))

ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(-235, 190); ax.set_ylim(-130, 250)
ax.text(-230, 243, "Exploded view: parts slide together along the blue dashed lines", fontsize=12, fontweight="bold")
ax.text(-230, 234, "Servo goes in from BEHIND the backboard. Upper arm sits flat on the front. Arm shown straight (REST). Cords not shown.", fontsize=9.5, color="#444")

# ------------- legend -------------
lg = fig.add_axes([0.63, 0.53, 0.36, 0.43]); lg.axis("off")
items = [
    ("1", "Base", "pot + button holes, slots for 2 and 3"),
    ("2", "Backboard", "servo window near the top"),
    ("3", "Gussets x2", "brace the backboard from behind"),
    ("4", "MG90S servo", "from the BACK, tabs on the back face, its own 2 screws"),
    ("5", "Upper arm (humerus)", "flat on the backboard, 2 x M3 x 12 bolts"),
    ("6", "Shoulder horn (metal)", "on the spline, parallel to the elbow horn at REST"),
    ("7", "Elbow spacer", "the 'cartilage' between the bones"),
    ("8", "Forearm (radius & ulna)", "two slots set the elbow horn angle"),
    ("9", "Elbow horn (cross horn)", "short arms cut off, centre drilled 3 mm, 2 x M2 bolts"),
    ("10", "Hand", "2 x M3 x 10 at the wrist"),
]
lg.text(0, 1.0, "Parts", fontsize=12, fontweight="bold", va="top")
for i, (n, a_, b_) in enumerate(items):
    y = 0.91 - i * 0.09
    lg.add_patch(plt.Circle((0.025, y - 0.012), 0.022, fc="#c0392b", ec="none", transform=lg.transAxes))
    lg.text(0.025, y - 0.012, n, ha="center", va="center", color="white", fontsize=7.5, fontweight="bold", transform=lg.transAxes)
    lg.text(0.07, y, a_, fontsize=9.5, fontweight="bold", va="top")
    lg.text(0.07, y - 0.037, b_, fontsize=8.5, color="#444", va="top")

# ------------- section drawings (side view, z left->right = back->front) -------------
def rect(a, x, w, h, fc, y=0, z=2, ec="#333"):
    a.add_patch(Rectangle((x, y - h / 2), w, h, fc=fc, ec=ec, lw=0.7, zorder=z))
def lab(a, txt, xy, xyt):
    a.annotate(txt, xy=xy, xytext=xyt, fontsize=8, ha="center", va="center",
               arrowprops=dict(arrowstyle="-", color="#666", lw=0.6), zorder=9, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"))
def arrow(a, x0, x1, y):
    a.annotate("", xy=(x1, y), xytext=(x0, y), arrowprops=dict(arrowstyle="->", color="#1f5fbf"))
    a.text((x0 + x1) / 2, y + 1.6, "toward the viewer", ha="center", fontsize=7.5, color="#1f5fbf")

s1 = fig.add_axes([0.64, 0.27, 0.34, 0.25]); s1.axis("off"); s1.set_xlim(-30, 24); s1.set_ylim(-26, 26)
s1.text(-30, 25, "Shoulder: servo mounts straight onto the backboard", fontsize=11, fontweight="bold", va="top")
# servo body behind (z -21.4..0), body top passes through bb+ua to z 4.3
rect(s1, -18.4, 18.4 + 4.3, 12.2, PAL["servo"], y=-3, z=1)
rect(s1, -2.5, 2.5, 32, PAL["servo"], y=-3, z=3)           # tabs
rect(s1, 0, 3, 40, PAL["frame"], y=-3, z=2)                 # backboard (window shown by servo passing)
rect(s1, 3, 3, 30, PAL["arm"], y=-3, z=2)                   # upper arm
rect(s1, 4.3, 3.6, 2.6, "#999", y=-3, z=4)                  # shaft/spline
rect(s1, 8.6, 2, 30, PAL["horn"], y=-3, z=5)                # horn
s1.add_patch(Rectangle((-0.2, -3 - 6.1), 4.5, 12.2, fc=PAL["servo"], ec="none", zorder=3))  # body through the windows
for yy in (-3 + 13.9, -3 - 13.9):                          # tab screws from the back
    rect(s1, -4.0, 1.5, 3.6, "#8c8c8c", y=yy, z=6); rect(s1, -2.5, 8.0, 1.6, "#b0b0b0", y=yy, z=6)
lab(s1, "servo body (behind)", (-10, -3), (-19, -20))
lab(s1, "tab + its screw", (-3.2, -3 + 13.9), (-19, 19))
lab(s1, "backboard", (1.5, 15), (-1, 21))
lab(s1, "upper arm", (4.5, 11), (8, 18))
lab(s1, "horn", (9.6, -16), (12, -21))
arrow(s1, -28, 22, -25)

s2 = fig.add_axes([0.64, 0.02, 0.34, 0.25]); s2.axis("off"); s2.set_xlim(-14, 30); s2.set_ylim(-29, 26)
s2.text(-14, 25, "Elbow pivot", fontsize=11, fontweight="bold", va="top")
rect(s2, 0, 3, 18, PAL["frame"], y=12.5); rect(s2, 0, 3, 18, PAL["frame"], y=-12.5)     # backboard with 7 mm hole
rect(s2, 3, 3, 36, PAL["arm"]); rect(s2, 6, 3, 11, PAL["ring"]); rect(s2, 9, 3, 30, PAL["arm"])
rect(s2, 12, 2, 26, PAL["horn2"]); rect(s2, 14, 2.5, 9, PAL["horn2"]); rect(s2, 16.5, 0.7, 7, "#b0b0b0")
s2.add_patch(Rectangle((0.2, -2.75), 2.6, 5.5, fc="#8c8c8c", ec="#333", lw=0.6, zorder=6))        # head in the hole
s2.add_patch(Rectangle((2.8, -1.5), 18.0, 3, fc="#b0b0b0", ec="#333", lw=0.6, zorder=5))
s2.add_patch(Rectangle((17.2, -2.9), 4, 5.8, fc="#8c8c8c", ec="#333", lw=0.6, zorder=6))
lab(s2, "backboard\n(7 mm hole)", (1.5, 21), (-7, 19)); lab(s2, "bolt head sits\nin the hole", (1.5, 0), (-8, -9))
lab(s2, "upper arm", (4.5, -18), (-3, -21)); lab(s2, "spacer", (7.5, 5.5), (8, 15)); lab(s2, "forearm", (10.5, -15), (12, -21))
lab(s2, "elbow horn", (13, 13), (19, 19)); lab(s2, "washer", (16.85, -3.5), (22, -14)); lab(s2, "nylock", (19.2, 2.9), (26, 8))
s2.text(-14, -27.5, "M3 x 20. Tighten only until the forearm swings freely.", fontsize=8, color="#333")

fig.savefig("out/assembly_diagram.png", dpi=130, bbox_inches="tight")
fig.savefig("out/assembly_diagram.pdf", bbox_inches="tight")
print("ok")
