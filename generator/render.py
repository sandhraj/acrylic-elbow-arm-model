# Motorised elbow model generator
# Author: Sandheep Rajendran  ·  License: MIT
import math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Ellipse
from matplotlib.path import Path
from shapely import affinity
from shapely.geometry import Point, LineString
from make_arm import *

def draw(ax, g, fc, ec="k", lw=0.6, alpha=1, z=1):
    gs = g.geoms if hasattr(g, "geoms") else [g]
    for p in gs:
        if p.geom_type != "Polygon": continue
        verts, codes = [], []
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords); verts += cs; codes += [Path.MOVETO] + [Path.LINETO] * (len(cs) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z))

# ---- sheet preview ----
fig, ax = plt.subplots(figsize=(13, 8.5))
ax.add_patch(plt.Rectangle((0, 0), SHEET_W, SHEET_H, fc="#eef6fb", ec="gray"))
for pp in placed:
    draw(ax, pp["cut"], "#d8ecf7", ec="red", lw=0.5)
    for f in pp["fill"]: draw(ax, f, "blue", ec="none")
    for l in pp["lines"]: ax.plot(*zip(*l.coords), color="blue", lw=0.6)
    if not pp["name"].startswith("ring"):
        mb = pp["cut"].bounds
        ax.text((mb[0] + mb[2]) / 2, mb[1] - 3.5, pp["name"], ha="center", fontsize=7, color="#333")
ax.set_xlim(-5, SHEET_W + 5); ax.set_ylim(-8, SHEET_H + 5); ax.set_aspect("equal"); ax.axis("off")
ax.set_title(f"Cut sheet {SHEET_W:.0f} x {SHEET_H:.0f} mm, 3 mm acrylic   (red = cut only)")
plt.savefig("out/cut_sheet_preview.png", dpi=110, bbox_inches="tight"); plt.close()

# ---- horn geometry (double horn ~37.5 mm long, hub ~7 mm) ----
HORN_LEN, HORN_W, HUB_R = 37.5, 5.5, 3.6
def horn(cx, cy, ang):
    g = unary_union([LineString([(-HORN_LEN / 2 + HORN_W / 2, 0), (HORN_LEN / 2 - HORN_W / 2, 0)]).buffer(HORN_W / 2), Point(0, 0).buffer(HUB_R + 1)])
    return affinity.translate(affinity.rotate(g, ang, origin=(0, 0)), cx, cy)

S = (0.0, SHOULDER_Y); E = (0.0, ELBOW_Y)
def tips(c, ang, r):
    a = math.radians(ang)
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a)), (c[0] - r * math.cos(a), c[1] - r * math.sin(a))

def pose(phi, r_s=R_HORN, r_e=R_HORN, horn_err=0.0):
    ang_s = HORN_REST + phi + horn_err          # servo horn angle (world)
    ang_e = HORN_AXIS + phi                     # elbow horn rotates with forearm
    sf, sb = tips(S, ang_s, r_s); ef, eb = tips(E, ang_e, r_e)
    return dict(ang_s=ang_s, ang_e=ang_e, bic=(sf, ef), tri=(sb, eb))

print("phi  servo_horn  biceps_len  triceps_len  min_clear_to_hubs")
worst = 99
for phi in range(0, 131, 10):
    d = pose(phi)
    bl = math.dist(*d["bic"]); tl = math.dist(*d["tri"])
    # clearance of each cord to both hubs (hub radius + 1 mm) and to elbow nut (r 3.5)
    cl = min(LineString(c).distance(Point(*p)) for c in (d["bic"], d["tri"]) for p in (S, E))
    worst = min(worst, cl)
    if phi % 30 == 0 or phi == 130: print(f"{phi:4d} {d['ang_s']:8.1f} {bl:11.2f} {tl:11.2f} {cl:12.1f}")
print("worst cord-to-hub-centre clearance:", round(worst, 1), "mm (hub radius ~3.6)")

def slack(**kw):
    L = [(math.dist(*pose(p, **kw)["bic"]), math.dist(*pose(p, **kw)["tri"])) for p in range(0, 131, 2)]
    b = [x[0] for x in L]; t = [x[1] for x in L]
    return round(max(b) - min(b), 2), round(max(t) - min(t), 2)
print("cord length variation (biceps, triceps) mm:")
print("  holes matched          ", slack())
print("  elbow hole 0.8 mm short", slack(r_e=R_HORN - 0.8))
print("  elbow hole 2.6 mm short", slack(r_e=R_HORN - 2.6))
print("  shoulder horn off 8 deg", slack(horn_err=8))

UA, FA, HAND = P["upper_arm"].cut, P["forearm"].cut, P["hand"].cut
fig, axs = plt.subplots(1, 3, figsize=(14, 5.6))
for ax, phi, lab in zip(axs, [0, 70, 130], ["Arm straight (triceps pulled)", "Biceps pulling", "Fully bent"]):
    d = pose(phi)
    ax.add_patch(plt.Rectangle((-80, -T), 195, T, fc="#ccc"))
    ax.add_patch(plt.Rectangle((-60, 0), 120, BB_H, fc="#f3f3f3", ec="#bbb"))
    draw(ax, affinity.translate(UA, 0, ELBOW_Y), "#f1e6c8", z=2)
    rot = lambda g: affinity.translate(affinity.rotate(g, phi, origin=(0, 0)), 0, ELBOW_Y)
    draw(ax, rot(FA), "#f1e6c8", z=3)
    draw(ax, rot(affinity.translate(HAND, 0, -L_FORE)), "#f6d7b8", z=4)
    draw(ax, horn(*S, d["ang_s"]), "#888", z=5)
    draw(ax, horn(*E, d["ang_e"]), "#555", z=5)
    for (p0, p1), col in ((d["bic"], "#c0392b"), (d["tri"], "#7b241c")):
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], col, lw=1.6, zorder=7)
    ax.plot(*S, "ko", ms=2.5, zorder=8); ax.plot(*E, "ko", ms=2.5, zorder=8)
    ax.set_title(f"{lab}\nelbow {phi:.0f}°  (servo turns the same {phi:.0f}°)", fontsize=10)
    ax.set_xlim(-110, 130); ax.set_ylim(-10, 215); ax.set_aspect("equal"); ax.axis("off")
axs[0].annotate("servo horn\n(shoulder)", S, (-108, 195), fontsize=8, arrowprops=dict(arrowstyle="-"))
axs[0].annotate("biceps (front)", (12, 140), (35, 175), fontsize=8, arrowprops=dict(arrowstyle="-"))
axs[0].annotate("triceps (back)", (-12, 140), (-108, 150), fontsize=8, arrowprops=dict(arrowstyle="-"))
axs[0].annotate("elbow horn\n(on forearm)", E, (-108, 85), fontsize=8, arrowprops=dict(arrowstyle="-"))
plt.suptitle("Side view (front of body to the right). The two horns stay parallel: cords form a parallelogram", fontsize=11)
plt.savefig("out/motion_preview.png", dpi=110, bbox_inches="tight"); plt.close()
