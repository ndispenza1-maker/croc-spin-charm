"""
Righteous Brothers BJJ — Shaka Keychain Pendant
50mm tip-to-tip (pinky to thumb), 4mm thick, one solid piece
Shaka drawn from geometric primitives — guaranteed single connected body
Keychain loop attached at top of curled fingers
"""

import pathlib, math
import numpy as np
import trimesh
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from shapely.affinity import translate as sh_translate, scale as sh_scale, rotate as sh_rotate

TARGET_SPAN_MM = 50.0   # pinky tip to thumb tip, mm
THICKNESS      = 4.0    # mm — solid
LOOP_R_INNER   = 2.5    # keyring hole radius, mm
LOOP_WALL      = 2.2    # ring wall thickness, mm
LOOP_NECK_W    = 6.0    # neck width connecting loop to body, mm

OUT_STL = '/home/ubuntu/croc-spin-charm/custom-orders/rb_shaka_keychain.stl'

# ── geometry helpers ─────────────────────────────────────────────
def circle(cx, cy, r, n=64):
    return Polygon([(cx + r*math.cos(2*math.pi*i/n),
                     cy + r*math.sin(2*math.pi*i/n)) for i in range(n)])

def rounded_rect(cx, cy, w, h, r, n=12):
    pts = []
    corners = [
        ( w/2-r,  h/2-r, 0),
        (-w/2+r,  h/2-r, math.pi/2),
        (-w/2+r, -h/2+r, math.pi),
        ( w/2-r, -h/2+r, 3*math.pi/2),
    ]
    for (ox, oy, start) in corners:
        for i in range(n+1):
            t = start + (math.pi/2)*i/n
            pts.append((cx + ox + r*math.cos(t), cy + oy + r*math.sin(t)))
    return Polygon(pts)

# ── build shaka from geometric primitives ────────────────────────
def build_shaka():
    """
    Hang-loose shaka: thumb extended upper-right, pinky extended lower-left,
    middle three fingers curled into palm. All parts overlapping = one solid piece.
    """
    parts = []

    # Palm — fat rounded rectangle, center of the hand
    palm = rounded_rect(0, 0, 18, 22, 4)
    parts.append(palm)

    # Thumb — capsule angled upper-right, rooted at right side of palm
    thumb_angle = math.radians(35)
    thumb_len, thumb_w = 20, 7
    # place center of thumb capsule along the angle from palm root
    tx = 9 + thumb_len/2 * math.cos(thumb_angle)
    ty = 8 + thumb_len/2 * math.sin(thumb_angle)
    thumb = rounded_rect(tx, ty, thumb_len, thumb_w, thumb_w/2 - 0.5)
    thumb = sh_rotate(thumb, math.degrees(thumb_angle), origin=(9, 8))
    parts.append(thumb)

    # Pinky — capsule angled lower-left, rooted at left side of palm
    pinky_angle = math.radians(200)
    pinky_len, pinky_w = 18, 6
    px = -9 + pinky_len/2 * math.cos(pinky_angle)
    py = -8 + pinky_len/2 * math.sin(pinky_angle)
    pinky = rounded_rect(px, py, pinky_len, pinky_w, pinky_w/2 - 0.5)
    pinky = sh_rotate(pinky, math.degrees(pinky_angle), origin=(-9, -8))
    parts.append(pinky)

    # Curled fingers — three rounded bumps along the top of the palm,
    # overlapping into the palm so they merge into one piece
    for (fx, fy, fw, fh) in [
        (-5,  10, 5.5, 10),   # index
        ( 0,  11, 5.0,  9),   # middle
        ( 5,  10, 5.0,  9),   # ring
    ]:
        parts.append(rounded_rect(fx, fy, fw, fh, 2.2))

    shape = unary_union(parts)
    if shape.geom_type != 'Polygon':
        # buffer merge any tiny gaps
        shape = shape.buffer(0.3).buffer(-0.2)
    return shape

# ── scale and center ─────────────────────────────────────────────
print("Building shaka geometry...")
shaka = build_shaka()
print(f"  Shaka type: {shaka.geom_type}")

bnd = shaka.bounds
sf = TARGET_SPAN_MM / (bnd[2] - bnd[0])
shaka = sh_scale(shaka, sf, sf, origin=(0, 0))
bnd = shaka.bounds
shaka = sh_translate(shaka, -(bnd[0]+bnd[2])/2, -(bnd[1]+bnd[3])/2)
bnd = shaka.bounds
print(f"  Span: {bnd[2]-bnd[0]:.1f}mm x {bnd[3]-bnd[1]:.1f}mm")

# ── find loop attachment point ───────────────────────────────────
# Attach at the topmost solid point near the centroid X
# (the curled fingers — the natural top of the hanging pendant)
print("Finding loop attachment point...")
cx_shaka = shaka.centroid.x
attach_x = cx_shaka
attach_y = bnd[1]  # fallback

for y in np.arange(bnd[3], bnd[1], -0.2):
    if shaka.contains(Point(attach_x, y)):
        attach_y = y
        break

# if nothing at centroid x, scan nearby
if attach_y == bnd[1]:
    for dx in np.arange(0, 10, 0.5):
        for sx in [1, -1]:
            xtest = cx_shaka + sx*dx
            for y in np.arange(bnd[3], bnd[1], -0.2):
                if shaka.contains(Point(xtest, y)):
                    attach_x = xtest
                    attach_y = y
                    break
            if attach_y != bnd[1]:
                break
        if attach_y != bnd[1]:
            break

print(f"  Attachment point: x={attach_x:.1f}, y={attach_y:.1f}")

# ── build loop and neck ──────────────────────────────────────────
print("Building keychain loop...")
loop_r_outer = LOOP_R_INNER + LOOP_WALL
loop_cy = attach_y + loop_r_outer + 1.0  # loop center sits above attachment

outer_ring = circle(attach_x, loop_cy, loop_r_outer)
inner_hole = circle(attach_x, loop_cy, LOOP_R_INNER)
ring = outer_ring.difference(inner_hole)

# Neck: solid rectangle overlapping 5mm into the shaka body
neck = Polygon([
    (attach_x - LOOP_NECK_W/2, attach_y - 5.0),
    (attach_x + LOOP_NECK_W/2, attach_y - 5.0),
    (attach_x + LOOP_NECK_W/2, loop_cy + loop_r_outer),
    (attach_x - LOOP_NECK_W/2, loop_cy + loop_r_outer),
])

loop_shape = ring.union(neck)

# ── merge shaka + loop into one 2D shape ────────────────────────
print("Merging into one 2D shape...")
full_2d = shaka.union(loop_shape)
print(f"  Result type: {full_2d.geom_type}")

if full_2d.geom_type != 'Polygon':
    # Force merge with a slightly larger buffer
    full_2d = full_2d.buffer(0.4).buffer(-0.3)
    print(f"  After bridge: {full_2d.geom_type}")

# ── extrude to 3D ────────────────────────────────────────────────
print("Extruding to 3D...")
if full_2d.geom_type == 'MultiPolygon':
    # take the largest part — should include body+loop
    parts_list = sorted(full_2d.geoms, key=lambda g: g.area, reverse=True)
    full_2d = parts_list[0]
    print(f"  Using largest part (area={full_2d.area:.0f})")

mesh = trimesh.creation.extrude_polygon(full_2d, THICKNESS)

if not mesh.is_watertight:
    mesh.fill_holes()
    trimesh.repair.fix_normals(mesh)

pathlib.Path(OUT_STL).parent.mkdir(parents=True, exist_ok=True)
mesh.export(OUT_STL)

dims = mesh.bounding_box.extents
print(f"\nDone: {OUT_STL}")
print(f"  Watertight: {mesh.is_watertight}")
print(f"  Faces:      {len(mesh.faces)}")
print(f"  Dims:       {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm")
