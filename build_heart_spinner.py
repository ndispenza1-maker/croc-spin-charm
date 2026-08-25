"""Build the first Spinnlitz heart spinner.

One-piece heart silhouette with the locked 7.7 mm center snap hole.
All dimensions are millimeters. Print flat, face-down, without supports.
"""
from pathlib import Path
import math

import numpy as np
import trimesh
from shapely.geometry import Polygon, Point

MAX_SIZE = 30.61
HOLE_DIAMETER = 7.7
THICKNESS = 2.0
SAMPLES = 256


def heart_points():
    raw = []
    for i in range(SAMPLES):
        t = 2 * math.pi * i / SAMPLES
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        raw.append((x, y))
    width = max(x for x, _ in raw) - min(x for x, _ in raw)
    height = max(y for _, y in raw) - min(y for _, y in raw)
    scale = MAX_SIZE / max(width, height)
    return [(x * scale, y * scale) for x, y in raw]


def main():
    outline = Polygon(heart_points()).buffer(0)
    hole = Point(0, 0).buffer(HOLE_DIAMETER / 2, resolution=96)
    heart = outline.difference(hole).buffer(0)
    if heart.is_empty or heart.geom_type != "Polygon":
        raise RuntimeError(f"Expected one polygon, got {heart.geom_type}")
    if not heart.contains(Point(HOLE_DIAMETER / 2 + 0.01, 0)):
        raise RuntimeError("Center hole does not fit inside the heart silhouette")

    mesh = trimesh.creation.extrude_polygon(heart, height=THICKNESS)
    mesh.process(validate=True)

    out = Path(__file__).resolve().parent / "assets" / "heart_spinner.stl"
    out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(out)

    extents = mesh.bounds[1] - mesh.bounds[0]
    print(f"Saved {out}")
    print(f"size: {extents[0]:.2f} x {extents[1]:.2f} x {extents[2]:.2f} mm")
    print(f"watertight: {mesh.is_watertight}")
    print(f"components: {len(mesh.split(only_watertight=False))}")
    print(f"volume: {mesh.volume:.2f} mm^3")


if __name__ == "__main__":
    main()
