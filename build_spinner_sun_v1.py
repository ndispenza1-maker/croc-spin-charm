"""
Croc Spin Charm - Sun Spinner Disc V1
50-cent piece diameter (30.61mm), 8 curved rays (counterclockwise sweep).

Geometry:
  - Central disc hub: solid circle, ~9mm dia, holds the snap hole
  - Center hole: 7.7mm dia — snaps over 8.1mm mushroom dome, rides on 7.5mm shaft
  - 8 curved rays: sweep counterclockwise from hub out to rim ring
  - Outer rim ring: thin ring at 30.61mm dia ties ray tips together
  - Thickness: 2.0mm uniform (rays same height as hub)

All units mm. Part is flat — print face-down, no supports.
"""

import numpy as np
from stl import mesh

triangles = []

def add_tri(v0, v1, v2):
    triangles.append((v0, v1, v2))

def add_quad(v0, v1, v2, v3):
    """Two triangles from a quad (v0,v1,v2,v3 in order)."""
    add_tri(v0, v1, v2)
    add_tri(v0, v2, v3)

def extrude_polygon(pts_2d, z_bot, z_top):
    """
    Extrude a 2D polygon (list of (x,y)) into a 3D solid.
    pts_2d should be ordered counterclockwise when viewed from above.
    Generates: bottom cap, top cap, side walls.
    """
    n = len(pts_2d)
    bot = [(x, y, z_bot) for x, y in pts_2d]
    top = [(x, y, z_top) for x, y in pts_2d]

    # Top cap (CCW from above = normal up)
    cx = sum(x for x, y in pts_2d) / n
    cy = sum(y for x, y in pts_2d) / n
    c_top = (cx, cy, z_top)
    c_bot = (cx, cy, z_bot)

    for i in range(n):
        j = (i + 1) % n
        # Top face
        add_tri(c_top, top[i], top[j])
        # Bottom face (normal down)
        add_tri(c_bot, bot[j], bot[i])
        # Side wall
        add_tri(bot[i], bot[j], top[j])
        add_tri(bot[i], top[j], top[i])

def ring_extrude(r_inner, r_outer, z_bot, z_top, n=64):
    """Hollow cylinder (annular ring extruded)."""
    inner_bot = [(r_inner*np.cos(a), r_inner*np.sin(a), z_bot)
                 for a in np.linspace(0, 2*np.pi, n, endpoint=False)]
    inner_top = [(r_inner*np.cos(a), r_inner*np.sin(a), z_top)
                 for a in np.linspace(0, 2*np.pi, n, endpoint=False)]
    outer_bot = [(r_outer*np.cos(a), r_outer*np.sin(a), z_bot)
                 for a in np.linspace(0, 2*np.pi, n, endpoint=False)]
    outer_top = [(r_outer*np.cos(a), r_outer*np.sin(a), z_top)
                 for a in np.linspace(0, 2*np.pi, n, endpoint=False)]

    for i in range(n):
        j = (i + 1) % n
        ib, it = inner_bot[i], inner_top[i]
        jb, jt = inner_bot[j], inner_top[j]
        ob, ot = outer_bot[i], outer_top[i]
        pb, pt = outer_bot[j], outer_top[j]

        # Top annular face (normal up)
        add_tri(it, pt, jt)  # wrong order — fix below
        add_tri(it, ot, pt)

        # Bottom annular face (normal down)
        add_tri(ib, jb, pb)
        add_tri(ib, pb, ob)

        # Outer wall
        add_tri(ob, pb, pt)
        add_tri(ob, pt, ot)

        # Inner wall (normal inward)
        add_tri(ib, it, jt)
        add_tri(ib, jt, jb)

# ── Dimensions ───────────────────────────────────────────────
DISC_R      = 30.61 / 2      # 15.305mm — 50-cent piece radius
HOLE_R      = 7.7  / 2       # 3.85mm  — snaps over 8.1mm dome
HUB_R       = 9.0  / 2       # 4.5mm   — solid hub around hole
RIM_W       = 1.5             # rim ring width at outer edge
RIM_R_INNER = DISC_R - RIM_W # inner edge of rim ring
THICKNESS   = 2.0             # overall disc thickness
Z_BOT       = 0.0
Z_TOP       = THICKNESS

N_RAYS      = 8
N_SEG       = 48              # segments per ray curve

# ── Ray geometry ─────────────────────────────────────────────
# Each ray is a curved blade sweeping counterclockwise.
# Base: starts at hub radius, angular width ~25 deg.
# Tip: ends at rim inner radius, swept ~40 deg counterclockwise from base center.
# Shape: built as a curved quadrilateral strip, slightly tapering.

RAY_BASE_HALF_ANG = np.radians(12)   # half-width at hub (deg each side)
RAY_TIP_HALF_ANG  = np.radians(5)    # half-width at tip (tapered)
RAY_SWEEP         = np.radians(38)   # how far CCW the tip sweeps from base center
RAY_STEPS         = 20               # segments along ray length

def curved_ray_polygon(center_angle_rad):
    """
    Returns a list of 2D points forming one curved ray polygon (CCW).
    The ray base is at HUB_R, tip at RIM_R_INNER.
    Sweeps counterclockwise by RAY_SWEEP over its length.
    """
    pts_leading = []   # leading edge (CCW side)
    pts_trailing = []  # trailing edge (CW side)

    for s in range(RAY_STEPS + 1):
        t = s / RAY_STEPS
        r = HUB_R + t * (RIM_R_INNER - HUB_R)
        # Angular sweep: at t=0 no extra sweep, at t=1 full sweep CCW
        sweep = t * RAY_SWEEP
        # Taper half-angle
        half_ang = RAY_BASE_HALF_ANG + t * (RAY_TIP_HALF_ANG - RAY_BASE_HALF_ANG)

        center_a = center_angle_rad + sweep
        lead_a   = center_a + half_ang    # leading (CCW) edge
        trail_a  = center_a - half_ang    # trailing (CW) edge

        pts_leading.append((r * np.cos(lead_a),  r * np.sin(lead_a)))
        pts_trailing.append((r * np.cos(trail_a), r * np.sin(trail_a)))

    # Polygon: leading edge forward, trailing edge backward
    return pts_leading + pts_trailing[::-1]

# ── Build geometry ───────────────────────────────────────────

# Hub (solid disc with hole) — annular ring
ring_extrude(HOLE_R, HUB_R, Z_BOT, Z_TOP, n=64)

# Outer rim ring
ring_extrude(RIM_R_INNER, DISC_R, Z_BOT, Z_TOP, n=128)

# 8 curved rays
for i in range(N_RAYS):
    center_a = i * (2 * np.pi / N_RAYS)
    poly = curved_ray_polygon(center_a)
    extrude_polygon(poly, Z_BOT, Z_TOP)

# ── Write STL ─────────────────────────────────────────────────
n = len(triangles)
spinner = mesh.Mesh(np.zeros(n, dtype=mesh.Mesh.dtype))
for i, (v0, v1, v2) in enumerate(triangles):
    spinner.vectors[i] = [v0, v1, v2]

out = '/home/ubuntu/croc-spin-charm/croc_spin_disc_sun_v1.stl'
spinner.save(out)
print(f"Saved {n} triangles → {out}")

all_verts = np.array(triangles).reshape(-1, 3)
print(f"X: {all_verts[:,0].min():.2f} → {all_verts[:,0].max():.2f}  (dia: {all_verts[:,0].max()*2:.2f}mm)")
print(f"Y: {all_verts[:,1].min():.2f} → {all_verts[:,1].max():.2f}")
print(f"Z: {all_verts[:,2].min():.2f} → {all_verts[:,2].max():.2f}  (thickness: {all_verts[:,2].max():.2f}mm)")
print(f"\nDisc dia:    {DISC_R*2:.2f}mm (50¢ = 30.61mm ✓)")
print(f"Center hole: {HOLE_R*2:.2f}mm")
print(f"Hub dia:     {HUB_R*2:.2f}mm")
print(f"Thickness:   {THICKNESS:.1f}mm")
print(f"Rays:        {N_RAYS} curved, CCW sweep {np.degrees(RAY_SWEEP):.0f}°")
