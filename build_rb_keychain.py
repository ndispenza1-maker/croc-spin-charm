"""
Righteous Brothers BJJ — Shaka Keychain Pendant
50mm tip-to-tip (pinky to thumb)
~4mm thick
Small half-ring loop at top for keychain attachment
Standalone piece — not a spinner disc
"""

import subprocess, pathlib, re, math
import numpy as np
from PIL import Image
import trimesh
from trimesh import creation
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.affinity import translate as sh_translate, scale as sh_scale, rotate as sh_rotate
from svg.path import parse_path
from svg.path.path import Line, CubicBezier, QuadraticBezier, Arc, Close

# ── dimensions ───────────────────────────────────────────────────
TARGET_SPAN_MM = 50.0   # tip of pinky to tip of thumb
THICKNESS      = 4.0    # mm — solid, sturdy for keychain use
LOOP_OD        = 7.0    # outer diameter of keychain loop (mm)
LOOP_ID        = 4.5    # inner diameter (hole for ring)
LOOP_H         = 3.5    # how far the loop extends above the shaka

IMG_PATH = '/home/ubuntu/.openclaw/media/inbound/90b644b3-001a-4729-9841-aecd9bd943da.png'
OUT_STL  = '/home/ubuntu/croc-spin-charm/custom-orders/rb_shaka_keychain.stl'

# ── extract shaka silhouette ─────────────────────────────────────
def extract_shaka_shape(target_span_mm):
    img = Image.open(IMG_PATH).convert('L')
    w, h = img.size
    m = 0.22
    box = (int(w*m), int(h*m), int(w*(1-m)), int(h*(1-m)))
    cropped = img.crop(box)
    big = cropped.resize((cropped.width*4, cropped.height*4), Image.LANCZOS)
    arr = np.array(big)
    binary = Image.fromarray(((arr < 140) * 255).astype(np.uint8))

    pbm = '/tmp/shaka_key.pbm'
    svg_out = '/tmp/shaka_key.svg'
    binary.save(pbm)
    subprocess.run([
        '/home/linuxbrew/.linuxbrew/bin/potrace',
        '--svg', '--alphamax', '1.0', '--opttolerance', '0.3',
        '-o', svg_out, pbm
    ], capture_output=True)

    content = pathlib.Path(svg_out).read_text()
    vb_vals = [float(x) for x in re.search(r'viewBox="([^"]+)"', content).group(1).split()]
    vb_w, vb_h = vb_vals[2], vb_vals[3]
    tx, ty, sx, sy = 0.0, vb_h, 0.1, -0.1

    def tp(x, y): return tx + sx*x, ty + sy*y

    def d_to_poly(d, n=64):
        pts = []
        for seg in parse_path(d):
            if isinstance(seg, (Line, Close)):
                pts.append(tp(seg.end.real, seg.end.imag))
            elif isinstance(seg, (CubicBezier, QuadraticBezier, Arc)):
                for i in range(1, n+1):
                    t = i/n; p = seg.point(t)
                    pts.append(tp(p.real, p.imag))
        if len(pts) < 3: return None
        try:
            p = Polygon(pts)
            if not p.is_valid: p = p.buffer(0)
            return p if not p.is_empty else None
        except: return None

    raw = [p for d in re.findall(r'd="([^"]+)"', content)
           if (p := d_to_poly(d)) is not None]
    raw.sort(key=lambda p: p.area, reverse=True)

    # pick the hand polygons (central, not border noise)
    hand = [p for p in raw
            if (p.bounds[2]-p.bounds[0]) < vb_w*0.85
            and p.area >= 200
            and vb_w*0.15 < p.centroid.x < vb_w*0.85
            and vb_h*0.15 < p.centroid.y < vb_h*0.85]

    if not hand:
        raise RuntimeError("No hand polygons found")

    shape = unary_union(hand)

    # center on bounding box midpoint
    bnd = shape.bounds
    mid_x = (bnd[0]+bnd[2])/2
    mid_y = (bnd[1]+bnd[3])/2
    shape = sh_translate(shape, -mid_x, -mid_y)

    # scale so horizontal span = target_span_mm
    bnd = shape.bounds
    current_span = bnd[2] - bnd[0]   # x-span = pinky tip to thumb tip
    sf = target_span_mm / current_span
    shape = sh_scale(shape, sf, sf, origin=(0, 0))

    print(f"  Shaka bounds after scale: {[f'{x:.1f}' for x in shape.bounds]}")
    return shape

# ── extrude 2D polygon to 3D mesh ────────────────────────────────
def extrude_shape(shape, height):
    """Extrude a shapely polygon to a trimesh solid."""
    if isinstance(shape, MultiPolygon):
        parts = list(shape.geoms)
    else:
        parts = [shape]

    meshes = []
    for poly in parts:
        if poly.is_empty or poly.area < 0.01:
            continue
        try:
            m = trimesh.creation.extrude_polygon(poly, height)
            if m.is_volume:
                meshes.append(m)
        except Exception as e:
            print(f"  Warning: extrude failed for polygon: {e}")

    if not meshes:
        raise RuntimeError("No valid meshes extruded")
    return trimesh.boolean.union(meshes) if len(meshes) > 1 else meshes[0]

# ── build keychain loop ───────────────────────────────────────────
def make_loop(attach_y, attach_z_mid):
    """
    A half-ring (D-ring) that sits above the shaka.
    Modeled as a torus section — outer tube that forms a loop.
    attach_y: y position of top of shaka silhouette
    """
    # Ring center sits above the shaka top
    ring_r  = (LOOP_OD - (LOOP_OD - LOOP_ID)) / 2  # mid-radius of the ring
    tube_r  = (LOOP_OD - LOOP_ID) / 4               # tube cross-section radius

    ring_center_y = attach_y + ring_r + 1.0  # 1mm gap above shaka

    # Build a full torus, then clip to top half only
    torus = creation.torus(ring_r, tube_r, 64, 16)

    # Rotate so the ring is upright (in XY plane by default — we want it in XZ... 
    # actually we want the ring in the YZ plane so it sticks up above the shaka in Y)
    # torus is built in XY plane — rotate 90° around X so it stands up in Y
    rot = trimesh.transformations.rotation_matrix(math.pi/2, [1, 0, 0])
    torus.apply_transform(rot)

    # Translate to sit above shaka
    torus.apply_translation([0, ring_center_y, attach_z_mid])

    # Clip to upper half only (keep y > attach_y)
    # Use a box to boolean-intersect
    box_h = (LOOP_OD + 4) * 2
    clip_box = creation.box([LOOP_OD + 2, box_h, THICKNESS + 4])
    clip_box.apply_translation([0, attach_y + box_h/2, attach_z_mid])

    loop = trimesh.boolean.intersection([torus, clip_box])
    return loop

# ── MAIN ─────────────────────────────────────────────────────────
print("Extracting shaka silhouette...")
shaka_2d = extract_shaka_shape(TARGET_SPAN_MM)

print("Extruding shaka body...")
shaka_mesh = extrude_shape(shaka_2d, THICKNESS)

# Position: center XY, base at Z=0
shaka_mesh.apply_translation([0, 0, 0])

print("Building keychain loop...")
bnd = shaka_2d.bounds
top_y      = bnd[3]           # top of shaka silhouette
mid_z      = THICKNESS / 2    # mid-height for loop attachment

loop_mesh = make_loop(top_y, mid_z)

print("Combining...")
combined = trimesh.boolean.union([shaka_mesh, loop_mesh])

if not combined.is_watertight:
    combined.fill_holes()
    trimesh.repair.fix_normals(combined)

# export
pathlib.Path(OUT_STL).parent.mkdir(parents=True, exist_ok=True)
combined.export(OUT_STL)

dims = combined.bounding_box.extents
print(f"\nDone: {OUT_STL}")
print(f"  Watertight: {combined.is_watertight}")
print(f"  Faces:      {len(combined.faces)}")
print(f"  Dims:       {dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm  (X x Y x Z)")
print(f"  (X-span should be ~{TARGET_SPAN_MM}mm pinky-to-thumb)")
