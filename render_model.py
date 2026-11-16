"""Generate directional PNG sprites from a locally supplied STL file.

Usage:
    pip install trimesh pillow numpy matplotlib
    python render_model.py
"""
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
STL = ROOT / "assets" / "labubu.stl"
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)
if not STL.exists():
    raise SystemExit("Missing assets/labubu.stl — add your original STL first.")
mesh = trimesh.load_mesh(STL)
vertices = np.asarray(mesh.vertices, dtype=float)
vertices -= (vertices.min(axis=0) + vertices.max(axis=0)) / 2
extent = np.ptp(vertices, axis=0)
vertices /= max(float(extent.max()), 1e-9)
faces = np.asarray(mesh.faces)
# Lightweight orthographic point projection; use a full renderer for shaded sprites.
for name, angle in (("front", 0), ("right", 90), ("back", 180), ("left", 270)):
    theta = np.deg2rad(angle)
    x = vertices[:, 0] * np.cos(theta) + vertices[:, 1] * np.sin(theta)
    y = vertices[:, 2]
    image = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    # Sparse vertex projection keeps generation manageable for large meshes.
    for xx, yy in zip(x[::4], y[::4]):
        px = int(256 + xx * 440)
        py = int(256 - yy * 440)
        if 0 <= px < 512 and 0 <= py < 512:
            draw.ellipse((px-1, py-1, px+1, py+1), fill=(215, 190, 150, 255))
    image.save(OUT / ("labubu_" + name + ".png"))
    print("Created", name)
