# Motorised elbow model generator
# Author: Sandheep Rajendran  ·  License: MIT
"""Kid-friendly illustrations for the build guide (7th grade)."""
import math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, FancyArrowPatch, Circle, FancyBboxPatch, Polygon as MPoly, Wedge
from matplotlib.path import Path
from shapely import affinity
from shapely.geometry import Point, LineString
from make_arm import *

plt.rcParams.update({"font.family": "DejaVu Sans"})
BONE, HAND, BG = "#fff3d6", "#ffd9b8", "#f4f9ff"
RED, DARK, BLUE, GREEN, PURPLE = "#e63946", "#7b241c", "#1d6fb8", "#2a9d8f", "#6a4c93"

def draw(ax, g, fc, ec="#333", lw=1.2, z=1, alpha=1):
    gs = g.geoms if hasattr(g, "geoms") else [g]
    for p in gs:
        if p.geom_type != "Polygon": continue
        verts, codes = [], []
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords); verts += cs; codes += [Path.MOVETO] + [Path.LINETO] * (len(cs) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))

def horn(c, ang, L=37.5, w=5.5):
    g = unary_union([LineString([(-L / 2 + w / 2, 0), (L / 2 - w / 2, 0)]).buffer(w / 2), Point(0, 0).buffer(4.4)])
    return affinity.translate(affinity.rotate(g, ang, origin=(0, 0)), *c)

S, E = (0.0, SHOULDER_Y), (0.0, ELBOW_Y)
def tip(c, ang, r=R_HORN): return (c[0] + r * math.cos(math.radians(ang)), c[1] + r * math.sin(math.radians(ang)))

def arm(ax, phi, bic_w=2, tri_w=2, bic_c=RED, tri_c=DARK, board=True):
    if board: ax.add_patch(FancyBboxPatch((-35, 0), 70, BB_H, boxstyle="round,pad=0,rounding_size=8", fc="#e8eef5", ec="#b8c4d0", lw=1, zorder=0))
    ax.add_patch(plt.Rectangle((-45, -4), 145, 4, fc="#cfd8e3", ec="none", zorder=0))
    draw(ax, affinity.translate(P["upper_arm"].cut, 0, ELBOW_Y), BONE, z=2)
    rot = lambda g: affinity.translate(affinity.rotate(g, phi, origin=(0, 0)), 0, ELBOW_Y)
    draw(ax, rot(P["forearm"].cut), BONE, z=3)
    draw(ax, rot(affinity.translate(P["hand"].cut, 0, -L_FORE)), HAND, z=4)
    a_s, a_e = HORN_REST + phi, HORN_AXIS + phi
    draw(ax, horn(S, a_s), "#9a9a9a", z=5); draw(ax, horn(E, a_e, 38, 5), "#666", z=5)
    for sgn, col, w in ((0, bic_c, bic_w), (180, tri_c, tri_w)):
        p0, p1 = tip(S, a_s + sgn), tip(E, a_e + sgn)
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=col, lw=w, solid_capstyle="round", zorder=7)
    return a_s, a_e

def big_arrow(ax, p0, p1, col, lw=3, rad=0.0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=22, color=col, lw=lw, connectionstyle=f"arc3,rad={rad}", zorder=9))

def finish(ax, xlim, ylim):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect("equal"); ax.axis("off")

# ------------------------------------------------------------ 1. muscles work in pairs
fig, axs = plt.subplots(1, 2, figsize=(11, 6.2), facecolor="white")
for ax, phi, title, sub, hot in ((axs[0], 0, "Triceps pulls", "→ the arm goes STRAIGHT", "tri"),
                                 (axs[1], 110, "Biceps pulls", "→ the arm BENDS", "bic")):
    a_s, a_e = arm(ax, phi, bic_w=5 if hot == "bic" else 1.5, tri_w=5 if hot == "tri" else 1.5,
                   bic_c=RED if hot == "bic" else "#f4a3a8", tri_c=DARK if hot == "tri" else "#c9a39d")
    ax.text(0, 232, title, ha="center", fontsize=20, fontweight="bold", color=RED if hot == "bic" else DARK)
    ax.text(0, 218, sub, ha="center", fontsize=14, color="#333")
    if hot == "tri":
        p = tip(S, a_s + 180); big_arrow(ax, (p[0] - 22, p[1] - 40), (p[0] - 22, p[1] + 5), DARK)
        ax.text(p[0] - 22, p[1] + 10, "pull!", ha="center", fontsize=13, color=DARK, fontweight="bold")
        ax.text(48, 140, "Biceps is\nrelaxed", fontsize=12, color="#b5838d", ha="left")
    else:
        p = tip(S, a_s); big_arrow(ax, (p[0] + 24, p[1] - 45), (p[0] + 24, p[1] + 5), RED)
        ax.text(p[0] + 24, p[1] + 10, "pull!", ha="center", fontsize=13, color=RED, fontweight="bold")
        big_arrow(ax, (95, 60), (70, 140), "#999", lw=2, rad=0.35)
        ax.text(-95, 140, "Triceps is\nrelaxed", fontsize=12, color="#b5838d", ha="left")
    finish(ax, (-110, 130), (-10, 245))
fig.text(0.5, 0.03, "Muscles can only PULL, never push. So every joint needs a pair: one to bend it, one to straighten it.",
         ha="center", fontsize=13, color="#222")
fig.savefig("out/ill_muscle_pair.png", dpi=130, bbox_inches="tight"); plt.close(fig)

# ------------------------------------------------------------ 2. lever
fig, ax = plt.subplots(figsize=(11, 5.2))
ax.add_patch(MPoly([(-8, -14), (8, -14), (0, 0)], closed=True, fc=GREEN, ec="#1b6b62", lw=1.5, zorder=3))
ax.add_patch(FancyBboxPatch((-6, -4), 116, 8, boxstyle="round,pad=0,rounding_size=4", fc=BONE, ec="#333", lw=1.5, zorder=2))
ax.add_patch(Circle((102, 14), 10, fc="#ff8c42", ec="#c45f1c", lw=1.5, zorder=4))
for a in (0, 60, 120): ax.plot([102 + 10 * math.cos(math.radians(a)), 102 - 10 * math.cos(math.radians(a))], [14 + 10 * math.sin(math.radians(a)), 14 - 10 * math.sin(math.radians(a))], color="#c45f1c", lw=0.8, zorder=5)
big_arrow(ax, (12, 4), (12, 45), RED, lw=4); ax.text(12, 50, "EFFORT\n(biceps pulls here)", ha="center", fontsize=13, color=RED, fontweight="bold")
big_arrow(ax, (102, 2), (102, -30), "#c45f1c", lw=3); ax.text(102, -40, "LOAD\n(ball in your hand)", ha="center", fontsize=13, color="#c45f1c", fontweight="bold", va="top")
ax.text(0, -22, "FULCRUM\n(elbow)", ha="center", fontsize=13, color="#1b6b62", fontweight="bold", va="top")
ax.annotate("", xy=(0, 26), xytext=(12, 26), arrowprops=dict(arrowstyle="<->", color="#555"))
ax.text(-4, 30, "short", ha="center", fontsize=11, color="#555")
ax.annotate("", xy=(0, -58), xytext=(102, -58), arrowprops=dict(arrowstyle="<->", color="#555"))
ax.text(51, -64, "long", ha="center", fontsize=11, color="#555", va="top")
ax.text(150, 30, "A small pull close to the\nelbow makes the hand\nmove a LONG way, FAST.", fontsize=14, va="center")
ax.text(150, -20, "The catch: the muscle has\nto pull much HARDER than\nthe weight in your hand.", fontsize=14, va="center", color="#555")
ax.text(-20, 80, "Your forearm is a lever", fontsize=20, fontweight="bold")
finish(ax, (-25, 265), (-80, 90))
fig.savefig("out/ill_lever.png", dpi=130, bbox_inches="tight"); plt.close(fig)

# ------------------------------------------------------------ 3. parallelogram trick
fig, axs = plt.subplots(1, 3, figsize=(12, 5))
for ax, ang in zip(axs, (-60, 0, 55)):
    s, e = (0, 70), (0, 0)
    for c, col in ((s, "#9a9a9a"), (e, "#666")):
        ax.add_patch(FancyBboxPatch((c[0] - 18, c[1] - 2.5), 36, 5, boxstyle="round,pad=0,rounding_size=2.5", fc=col, ec="#333", lw=1,
                                    transform=matplotlib.transforms.Affine2D().rotate_deg_around(c[0], c[1], ang) + ax.transData, zorder=3))
        ax.add_patch(Circle(c, 3.5, fc="#444", zorder=4))
    for sg, col in ((0, RED), (180, DARK)):
        p0, p1 = tip(s, ang + sg, 16.8), tip(e, ang + sg, 16.8)
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=col, lw=4, zorder=2, solid_capstyle="round")
    ax.plot([0, 0], [0, 70], color="#bbb", lw=1.5, ls="--", zorder=1)
    ax.text(0, -26, f"servo turned {ang + 60:.0f}°", ha="center", fontsize=12)
    finish(ax, (-35, 35), (-32, 100))
axs[0].text(-30, 92, "shoulder horn (on servo)", fontsize=10, color="#555")
axs[0].text(-30, -18, "elbow horn", fontsize=10, color="#555")
fig.suptitle("The trick: both horns always stay parallel, so the red cords never go slack", fontsize=15, fontweight="bold", y=1.0)
fig.text(0.5, 0.0, "Same-length sides + parallel horns = a parallelogram. The elbow turns exactly as much as the servo.", ha="center", fontsize=12, color="#333")
fig.savefig("out/ill_parallelogram.png", dpi=130, bbox_inches="tight"); plt.close(fig)

# ------------------------------------------------------------ 4. build strip
steps = ["1. Build the stand", "2. Servo in from behind", "3. Build the arm,\nbolt it on", "4. Shoulder horn on", "5. Tie the strings"]
fig, axs = plt.subplots(1, 5, figsize=(15, 5.4))
NEW = "#ffe066"
for k, (ax, t) in enumerate(zip(axs, steps)):
    ax.add_patch(FancyBboxPatch((-35, 0), 70, BB_H, boxstyle="round,pad=0,rounding_size=8", fc=NEW if k == 0 else "#e8eef5", ec="#b8c4d0", lw=1, zorder=0))
    ax.add_patch(plt.Rectangle((-45, -4), 145, 4, fc=NEW if k == 0 else "#cfd8e3", ec="none", zorder=0))
    if k >= 1:
        ax.add_patch(plt.Rectangle((-SV_W / 2, SHOULDER_Y - 17), SV_W, 23, fc="#333", ec=NEW if k == 1 else "#333", lw=4 if k == 1 else 1, zorder=1))
    if k >= 2:
        hi = (k == 2)
        draw(ax, affinity.translate(P["upper_arm"].cut, 0, ELBOW_Y), NEW if hi else BONE, z=2)
        draw(ax, affinity.translate(P["forearm"].cut, 0, ELBOW_Y), NEW if hi else BONE, z=3)
        draw(ax, affinity.translate(P["hand"].cut, 0, ELBOW_Y - L_FORE), NEW if hi else HAND, z=4)
        draw(ax, horn(E, HORN_AXIS, 38, 5), "#666", z=5)
    if k >= 3: draw(ax, horn(S, HORN_REST), NEW if k == 3 else "#9a9a9a", z=5)
    if k >= 4:
        for sg, col in ((0, RED), (180, DARK)):
            p0, p1 = tip(S, HORN_REST + sg), tip(E, HORN_AXIS + sg)
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=col, lw=4, zorder=7)
    ax.set_title(t, fontsize=14, fontweight="bold")
    finish(ax, (-50, 60), (-8, 210))
fig.text(0.5, 0.02, "Yellow = the part you add in that step", ha="center", fontsize=13, color="#555")
fig.savefig("out/ill_build_steps.png", dpi=120, bbox_inches="tight"); plt.close(fig)
print("ok")
