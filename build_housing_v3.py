"""
Croc Spin Charm - Housing V3
One-piece double-mushroom rivet design.

Cross-section (bottom to top):
  1. Bottom dome  — hemisphere, 8.1mm dia, locks under Croc
  2. Shaft        — cylinder, 7.5mm dia, 10mm tall, fits through Croc hole
  3. Middle flange— disc, 10mm dia, 2.5mm thick, sits on top of Croc surface
  4. Top dome     — hemisphere, 8.1mm dia, spinner snaps over this later

All dimensions in mm. Origin at bottom of bottom dome.
"""

import numpy as np
from stl import mesh

triangles = []

def add_tri(v0, v1, v2):
    triangles.append((v0, v1, v2))

def circle_pts(r, n, z):
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return [(r * np.cos(a), r * np.sin(a), z) for a in angles]

def tube_section(r_bot, z_bot, r_top, z_top, n=64):
    """Tapered cylinder wall, open top and bottom."""
    bot = circle_pts(r_bot, n, z_bot)
    top = circle_pts(r_top, n, z_top)
    for i in range(n):
        j = (i + 1) % n
        b0, b1 = bot[i], bot[j]
        t0, t1 = top[i], top[j]
        add_tri(b0, b1, t0)
        add_tri(b1, t1, t0)

def cap_circle(r, z, n=64, inward=False):
    """Solid filled disc."""
    pts = circle_pts(r, n, z)
    center = (0.0, 0.0, z)
    for i in range(n):
        j = (i + 1) % n
        if inward:
            add_tri(center, pts[j], pts[i])
        else:
            add_tri(center, pts[i], pts[j])

def ring_face(r_inner, r_outer, z, n=64, inward=False):
    """Annular (donut) face at height z."""
    inner = circle_pts(r_inner, n, z)
    outer = circle_pts(r_outer, n, z)
    for i in range(n):
        j = (i + 1) % n
        i0, i1 = inner[i], inner[j]
        o0, o1 = outer[i], outer[j]
        if inward:
            add_tri(o0, i0, i1)
            add_tri(o0, i1, o1)
        else:
            add_tri(o0, o1, i1)
            add_tri(o0, i1, i0)

def hemisphere(r, z_base, n=64, point_up=True):
    """
    Hemisphere of radius r.
    z_base = flat face z position.
    point_up=True  → dome rises above z_base (top dome).
    point_up=False → dome drops below z_base (bottom dome, normals flipped).
    """
    STEPS = 16
    for s in range(STEPS):
        t0 = s / STEPS
        t1 = (s + 1) / STEPS
        a0 = t0 * (np.pi / 2)
        a1 = t1 * (np.pi / 2)
        r0 = r * np.cos(a0)
        r1 = r * np.cos(a1)
        if point_up:
            z0 = z_base + r * np.sin(a0)
            z1 = z_base + r * np.sin(a1)
        else:
            z0 = z_base - r * np.sin(a0)
            z1 = z_base - r * np.sin(a1)

        if s == STEPS - 1:
            # Close at tip
            pts = circle_pts(r0, n, z0)
            tip = (0.0, 0.0, z_base + r if point_up else z_base - r)
            for i in range(n):
                j = (i + 1) % n
                if point_up:
                    add_tri(pts[i], pts[j], tip)
                else:
                    add_tri(pts[j], pts[i], tip)
        else:
            if point_up:
                tube_section(r0, z0, r1, z1, n)
            else:
                tube_section(r1, z1, r0, z0, n)

# ── Dimensions ───────────────────────────────────────────────
N           = 64

DOME_R      = 8.1 / 2     # 4.05mm radius — both domes same size
SHAFT_R     = 7.5 / 2     # 3.75mm radius — snug in Croc hole
SHAFT_H     = 10.0        # height of shaft between domes
FLANGE_R    = 10.0 / 2    # 5.0mm radius — sits on Croc surface
FLANGE_T    = 2.5         # flange thickness

# Z positions (building bottom to top)
# Bottom dome tip is at Z=0, flat face at Z=DOME_R
BOT_DOME_TIP  = 0.0
BOT_DOME_FLAT = DOME_R                    # 4.05

SHAFT_BOT     = BOT_DOME_FLAT             # 4.05
SHAFT_TOP     = SHAFT_BOT + SHAFT_H       # 14.05

FLANGE_BOT    = SHAFT_TOP                 # 14.05
FLANGE_TOP    = FLANGE_BOT + FLANGE_T     # 16.55

TOP_DOME_BASE = FLANGE_TOP                # 16.55
TOP_DOME_TIP  = TOP_DOME_BASE + DOME_R    # 20.60

# ── Geometry ─────────────────────────────────────────────────

# 1. Bottom dome (points downward, dome below SHAFT_BOT)
hemisphere(DOME_R, BOT_DOME_FLAT, N, point_up=False)

# Flat annular face at bottom dome/shaft junction
# Bottom dome flat face merges into shaft — no face needed (same radius, continuous)
# But dome_r (4.05) < shaft_r (3.75)? No: dome_r=4.05 > shaft_r=3.75
# So we need an annular ring face at the junction (inward=True, faces down into dome)
ring_face(SHAFT_R, DOME_R, BOT_DOME_FLAT, N, inward=True)

# 2. Shaft
tube_section(SHAFT_R, SHAFT_BOT, SHAFT_R, SHAFT_TOP, N)

# 3. Middle flange
# Bottom face of flange (annular — shaft passes through center)
ring_face(SHAFT_R, FLANGE_R, FLANGE_BOT, N, inward=True)
# Outer wall of flange
tube_section(FLANGE_R, FLANGE_BOT, FLANGE_R, FLANGE_TOP, N)
# Top face of flange (annular — shaft continues through center)
ring_face(SHAFT_R, FLANGE_R, FLANGE_TOP, N, inward=False)

# 4. Top dome (points upward from flange top)
# Dome_R (4.05) > shaft_r (3.75) so annular ring at base
ring_face(SHAFT_R, DOME_R, TOP_DOME_BASE, N, inward=True)
hemisphere(DOME_R, TOP_DOME_BASE, N, point_up=True)

# ── Write STL ─────────────────────────────────────────────────
n = len(triangles)
housing = mesh.Mesh(np.zeros(n, dtype=mesh.Mesh.dtype))
for i, (v0, v1, v2) in enumerate(triangles):
    housing.vectors[i] = [v0, v1, v2]

out = '/home/ubuntu/croc-spin-charm/croc_pin_housing_v3.stl'
housing.save(out)
print(f"Saved {n} triangles → {out}")

all_verts = np.array(triangles).reshape(-1, 3)
print(f"X: {all_verts[:,0].min():.2f} → {all_verts[:,0].max():.2f}  (dia: {all_verts[:,0].max()*2:.2f}mm)")
print(f"Y: {all_verts[:,1].min():.2f} → {all_verts[:,1].max():.2f}")
print(f"Z: {all_verts[:,2].min():.2f} → {all_verts[:,2].max():.2f}  (total height: {all_verts[:,2].max():.2f}mm)")
print()
print(f"Bottom dome dia:  {DOME_R*2:.1f}mm")
print(f"Shaft dia:        {SHAFT_R*2:.1f}mm  height: {SHAFT_H:.1f}mm")
print(f"Flange dia:       {FLANGE_R*2:.1f}mm  thick: {FLANGE_T:.1f}mm")
print(f"Top dome dia:     {DOME_R*2:.1f}mm")
print(f"Total height:     {TOP_DOME_TIP:.2f}mm")
