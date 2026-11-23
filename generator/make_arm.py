# Motorised elbow model generator
# Author: Sandheep Rajendran  ·  License: MIT
"""Parametric acrylic elbow model (biceps/triceps antagonistic pair) for an MG90S/SG90 servo.
Outputs: SVG + DXF cut sheet (red = cut, blue = engrave), previews.
All units mm. Viewer looks at the arm from its side; +X = front of the body, +Y = up.
"""
import math, json
from shapely.geometry import Polygon, Point, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

T = 3.0                       # sheet thickness
M3 = 3.3                      # M3 clearance hole
SLOT_W = 3.2                  # slot width for 3 mm tabs
# --- servo (MG90S / SG90 share this footprint) ---
SV_L, SV_W = 22.8, 12.2       # body
SV_CLR = 0.4                  # total clearance
SV_SHAFT_FROM_END = 6.0       # shaft centre to near end of body
SV_TAB_HOLES = 27.8           # tab hole spacing
SV_TAB_HOLE_D = 2.2
# --- mechanism ---
L_UPPER = 70.0                # shoulder (servo shaft) to elbow pivot
L_FORE = 54.0                 # elbow pivot to wrist pivot
# Horn-lever version: shoulder horn (on servo) and elbow horn (on forearm) use holes at the
# same radius, so horns + cords form a parallelogram: elbow angle = servo angle, cords never slack.
R_HORN = 16.8                 # cord hole radius used on BOTH horns (outer hole, measured from photo)
SERVO_RANGE = 130.0           # servo travel = elbow travel (1:1)
ELBOW_RANGE = SERVO_RANGE
HORN_REST = -SERVO_RANGE / 2  # horn angle at rest, deg from front-horizontal (front tip points down-front)
SHOULDER_Y = 174.0            # shoulder height above base top
ELBOW_Y = SHOULDER_Y - L_UPPER
HAND_SX, HAND_SY = 0.75, 0.56 # hand scale vs the original drawing
GAP_BACK = 0.0                # upper arm sits flat on the backboard front face
SV_PILOT_D = 1.6              # pilot hole for the servo's self-tapping screws (backboard)
SV_SCREW_CLR = 2.6            # clearance in upper arm for the screw tips

def circ(x, y, r, n=96):
    return Point(x, y).buffer(r, resolution=n)

def hole(x, y, d):
    return circ(x, y, d / 2, 48)

def polar(r, deg):
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)

def radial_slot(r_in, r_out, deg, w):
    x0, y0 = polar(r_in, deg); x1, y1 = polar(r_out + 2, deg)
    return LineString([(x0, y0), (x1, y1)]).buffer(w / 2, cap_style=2)

def smooth(g, r=3):
    return g.buffer(r, resolution=32).buffer(-2 * r, resolution=32).buffer(r, resolution=32)

def text_polys(s, x, y, h, angle=0, anchor="c"):
    fp = FontProperties(family="DejaVu Sans", weight="bold")
    tp = TextPath((0, 0), s, size=h, prop=fp)
    polys = [Polygon(p) for p in tp.to_polygons() if len(p) >= 3]
    # even-odd combine (letters with holes)
    g = None
    for p in polys:
        if not p.is_valid: p = p.buffer(0)
        g = p if g is None else g.symmetric_difference(p)
    minx, miny, maxx, maxy = g.bounds
    g = affinity.translate(g, -(minx + maxx) / 2, -(miny + maxy) / 2)
    g = affinity.rotate(g, angle, origin=(0, 0))
    return affinity.translate(g, x, y)

class Part:
    def __init__(self, name, outline, holes=(), engrave_fill=(), engrave_lines=(), qty=1, note=""):
        self.name, self.qty, self.note = name, qty, note
        g = outline
        for h in holes: g = g.difference(h)
        self.cut = g
        self.fill = list(engrave_fill)
        self.lines = list(engrave_lines)

parts = []

# ---------------- UPPER ARM (humerus) ----------------
ua = unary_union([
    circ(0, L_UPPER, 24),
    Polygon([(-13, L_UPPER - 15), (13, L_UPPER - 15), (12, 30), (17, 8), (-17, 8), (-12, 30)]),
    circ(0, 0, 17),
])
ua = smooth(ua, 7)
sv_top = L_UPPER + SV_SHAFT_FROM_END
sv_bot = sv_top - SV_L
sv_mid = (sv_top + sv_bot) / 2
UA_STANDOFFS = [(0, 22), (0, 44)]   # M3 bolts: upper arm -> backboard
ua_holes = [box(-(SV_W + SV_CLR) / 2, sv_bot - SV_CLR / 2, (SV_W + SV_CLR) / 2, sv_top + SV_CLR / 2),
            hole(0, sv_mid + SV_TAB_HOLES / 2, SV_SCREW_CLR), hole(0, sv_mid - SV_TAB_HOLES / 2, SV_SCREW_CLR),
            hole(0, 0, M3)] + [hole(x, y, M3) for x, y in UA_STANDOFFS]
parts.append(Part("upper_arm", ua, ua_holes,
                  engrave_fill=[text_polys("HUMERUS", 0, 33, 2.3, angle=90)],
                  engrave_lines=[LineString([(lambda a: (r * math.cos(a), L_UPPER + r * math.sin(a)))(math.radians(ang)) for r in (19.5, 23)])
                                 for ang in (HORN_REST, HORN_REST + 180)],
                  note="Humerus. Servo goes in from the BACK, tabs against back face."))

# elbow spacers
parts.append(Part("elbow_spacer", circ(0, 0, 5.5), [hole(0, 0, M3)]))

# ---------------- FOREARM (radius & ulna) ----------------
fa = unary_union([circ(0, 0, 17),
                  Polygon([(-13, 0), (13, 0), (11, -L_FORE), (-11, -L_FORE)]),
                  circ(0, -L_FORE, 12)])
fa = smooth(fa, 3)
# elbow horn lies along HORN_REST+... in the forearm frame (forearm points -Y = 270 deg at rest)
HORN_AXIS = HORN_REST          # front tip direction at rest, same as shoulder horn -> parallelogram
horn_slots = [LineString([polar(8.0, a), polar(14.2, a)]).buffer(1.15, resolution=12) for a in (HORN_AXIS, HORN_AXIS + 180)]
fa_holes = [hole(0, 0, M3), hole(0, -L_FORE, M3), hole(0, -L_FORE + 10, M3)] + horn_slots
ulna = unary_union([LineString([(-7, -22), (-6, -L_FORE + 4)]).buffer(2.6, resolution=16), circ(-8, -22, 3.8)])
radius = unary_union([LineString([(6.5, -25), (6, -L_FORE + 8)]).buffer(2.4, resolution=16), circ(6, -L_FORE + 6, 3.4)])
parts.append(Part("forearm", fa, fa_holes,
                  engrave_fill=[text_polys("ULNA", -6.5, -(22 + L_FORE) / 2 - 2, 2.8, angle=90),
                                text_polys("RADIUS", 6.3, -(25 + L_FORE) / 2 + 1, 2.4, angle=90)],
                  engrave_lines=[ulna.exterior, radius.exterior],
                  note="Ulna drawn at back (olecranon side), radius at front."))

# ---------------- HAND ----------------
palm = box(-16, -34, 16, 24).buffer(0)
palm = smooth(palm, 5)
fingers = []
for x, L in [(-11.5, 26), (-4, 33), (3.5, 31), (11, 24)]:
    fingers.append(LineString([(x, -30), (x, -30 - L)]).buffer(3.3, resolution=24))
thumb = LineString([(12, -8), (24, -34)]).buffer(4, resolution=24)
hand = smooth(unary_union([palm] + fingers + [thumb]), 1.2)
hand = affinity.scale(hand, HAND_SX, HAND_SY, origin=(0, 0))
sc = lambda g: affinity.scale(g, HAND_SX, HAND_SY, origin=(0, 0))
parts.append(Part("hand", hand, [hole(0, 0, M3), hole(0, 10, M3)],
                  engrave_lines=[sc(LineString([(-9, -12), (8, -16)])), sc(LineString([(-11, -22), (6, -26)]))],
                  note="Wrist: remove top bolt to show the wrist as a 2nd hinge."))

# ---------------- BACKBOARD (torso) ----------------
BB_W, BB_H = 70.0, 200.0
bb = smooth(box(-BB_W / 2, 0, BB_W / 2, BB_H), 8)
BB_TABS = ((-24.0, -8.0), (8.0, 24.0))
tabs = [box(a, -T, b, 1) for a, b in BB_TABS]
bb = unary_union([bb] + tabs)
GUSSET_X = 28.0
G_TAB_V = (25.0, 55.0)
SV_TOP_W, SV_BOT_W = SHOULDER_Y + SV_SHAFT_FROM_END, SHOULDER_Y + SV_SHAFT_FROM_END - SV_L
SV_MID_W = (SV_TOP_W + SV_BOT_W) / 2
bb_holes = [hole(x, y + ELBOW_Y, M3) for x, y in UA_STANDOFFS] + \
           [box(-(SV_W + SV_CLR) / 2, SV_BOT_W - SV_CLR / 2, (SV_W + SV_CLR) / 2, SV_TOP_W + SV_CLR / 2),   # servo window
            hole(0, SV_MID_W + SV_TAB_HOLES / 2, SV_PILOT_D), hole(0, SV_MID_W - SV_TAB_HOLES / 2, SV_PILOT_D),
            hole(0, ELBOW_Y, 7.0)] + \
           [box(sx - SLOT_W / 2, G_TAB_V[0] - 0.1, sx + SLOT_W / 2, G_TAB_V[1] + 0.1) for sx in (-GUSSET_X, GUSSET_X)]
parts.append(Part("backboard", bb, bb_holes,
                  engrave_fill=[text_polys("SERVO", 0, SV_BOT_W - 18, 3.0)],
                  note="Engraved side faces BACK (Arduino + servo side)."))

# ---------------- GUSSETS ----------------
g = Polygon([(0, 0), (40, 0), (0, 75)])
g = unary_union([g, box(-T, G_TAB_V[0], 0.5, G_TAB_V[1]), box(8, -T, 30, 0.5)])
for i in range(2):
    parts.append(Part(f"gusset_{i+1}", g))

# ---------------- BASE ----------------
# base frame: X = world X, second axis = world Z (toward viewer)
BB_Z0 = -GAP_BACK - T       # backboard back face
base = smooth(box(-45, -50, 100, 40), 6)
base_holes = [box(a - 0.1, BB_Z0 - 0.1, b + 0.1, BB_Z0 + SLOT_W - 0.1) for a, b in BB_TABS]
base_holes += [box(sx - SLOT_W / 2, BB_Z0 - 30.1, sx + SLOT_W / 2, BB_Z0 - 7.9) for sx in (-GUSSET_X, GUSSET_X)]
base_holes += [hole(86, 24, 7.2), hole(86, 2, 7.2)]
parts.append(Part("base", base, base_holes,
                  engrave_fill=[text_polys("MOVE", 86, 15, 3.0), text_polys("DEMO", 86, -7, 3.0),
                                text_polys("BICEPS contracts = elbow BENDS (flexion)", 16, 33, 3.0),
                                text_polys("TRICEPS contracts = elbow STRAIGHTENS (extension)", 16, 26, 3.0)],
                  note="Knob = pot, button = demo mode."))

# No engraving: cut-only file
ENGRAVE = False
if not ENGRAVE:
    for p in parts: p.fill, p.lines = [], []

# ======================= LAYOUT (from nest.py) =======================
import os
NEST = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out/nest_best.json")))
SHEET_W, SHEET_H = math.ceil(NEST["L"]), math.ceil(NEST["H"])
P = {p.name: p for p in parts}
placed = []
for pl in NEST["placed"]:
    p = P[pl["name"]]
    tf = lambda g, pl=pl: affinity.translate(affinity.rotate(g, pl["rot"], origin=(0, 0)), pl["x"], pl["y"])
    placed.append(dict(name=p.name, cut=tf(p.cut), fill=[tf(f) for f in p.fill], lines=[tf(l) for l in p.lines]))

# sanity: overlaps / sheet bounds
allc = [pp["cut"] for pp in placed]
for i in range(len(allc)):
    mb = allc[i].bounds
    assert mb[0] >= 0 and mb[1] >= 0 and mb[2] <= SHEET_W and mb[3] <= SHEET_H, (placed[i]["name"], mb)
    for j in range(i + 1, len(allc)):
        assert allc[i].distance(allc[j]) > 1.9, (placed[i]["name"], placed[j]["name"])
used = unary_union(allc).bounds
print("sheet used:", [round(v, 1) for v in used])

# ======================= EXPORT =======================
def rings_of(geom):
    gs = geom.geoms if hasattr(geom, "geoms") else [geom]
    for g in gs:
        if g.geom_type == "Polygon":
            yield list(g.exterior.coords)
            for r in g.interiors: yield list(r.coords)
        elif g.geom_type in ("LineString", "LinearRing"):
            yield list(g.coords)

def path_d(coords, close=True):
    # flip Y for SVG
    s = "M" + " L".join(f"{x:.3f},{SHEET_H - y:.3f}" for x, y in coords)
    return s + (" Z" if close else "")

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W}mm" height="{SHEET_H}mm" viewBox="0 0 {SHEET_W} {SHEET_H}">',
       '<!-- RED = cut through (3 mm acrylic). BLUE fill = raster engrave, BLUE line = vector score. Units mm, 1:1. -->']
svg.append('<g id="ENGRAVE_FILL" fill="#0000FF" stroke="none">')
for pp in placed:
    for f in pp["fill"]:
        d = " ".join(path_d(c) for c in rings_of(f))
        svg.append(f'<path fill-rule="evenodd" d="{d}"/>')
svg.append('</g><g id="SCORE" fill="none" stroke="#0000FF" stroke-width="0.1">')
for pp in placed:
    for l in pp["lines"]:
        cs = list(l.coords); closed = cs[0] == cs[-1]
        svg.append(f'<path d="{path_d(cs, closed)}"/>')
svg.append('</g><g id="CUT" fill="none" stroke="#FF0000" stroke-width="0.1">')
for pp in placed:
    for c in rings_of(pp["cut"]):
        svg.append(f'<path d="{path_d(c)}"/>')
svg.append('</g></svg>')
svg_txt = "\n".join(svg)
if not ENGRAVE:
    svg_txt = svg_txt.replace('<g id="ENGRAVE_FILL" fill="#0000FF" stroke="none">\n</g><g id="SCORE" fill="none" stroke="#0000FF" stroke-width="0.1">\n</g>', "")
    svg_txt = svg_txt.replace("RED = cut through (3 mm acrylic). BLUE fill = raster engrave, BLUE line = vector score.", "RED = cut through (3 mm acrylic). Cut only, no engraving. Design: Sandheep Rajendran (CC BY 4.0).")
open("out/arm_model_cut_3mm_acrylic.svg", "w").write(svg_txt)

import ezdxf
doc = ezdxf.new("R2010"); doc.units = ezdxf.units.MM
doc.layers.add("CUT", color=1); doc.layers.add("ENGRAVE", color=5); doc.layers.add("SCORE", color=5)
msp = doc.modelspace()
for pp in placed:
    for c in rings_of(pp["cut"]):
        msp.add_lwpolyline(c, close=True, dxfattribs={"layer": "CUT"})
    for f in pp["fill"]:
        for c in rings_of(f):
            msp.add_lwpolyline(c, close=True, dxfattribs={"layer": "ENGRAVE"})
    for l in pp["lines"]:
        cs = list(l.coords)
        msp.add_lwpolyline(cs, close=cs[0] == cs[-1], dxfattribs={"layer": "SCORE"})
doc.saveas("out/arm_model_cut_3mm_acrylic.dxf")

json.dump(dict(ELBOW_RANGE=ELBOW_RANGE, used=used), open("out/params.json", "w"))
import pickle; pickle.dump(dict(parts={p.name: p for p in parts}, placed=placed), open("out/parts.pkl", "wb"))
print("elbow range", ELBOW_RANGE, "elbow Y", ELBOW_Y)
