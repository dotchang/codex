import os
import argparse
import urllib.request
import numpy as np
import trimesh
import pyrender
import imageio.v2 as iio
from trimesh.transformations import euler_matrix

# Use OSMesa for headless rendering
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

BUNNY_URL = "https://github.com/isl-org/open3d_downloads/releases/download/20220201-data/BunnyMesh.ply"
BUNNY_FILE = "bunny.ply"

# Simple PBR material presets for metals
MATERIALS = {
    "iron": {
        "baseColorFactor": [0.56, 0.57, 0.58, 1.0],
        "metallicFactor": 1.0,
        "roughnessFactor": 0.5,
    },
    "aluminum": {
        "baseColorFactor": [0.91, 0.92, 0.93, 1.0],
        "metallicFactor": 1.0,
        "roughnessFactor": 0.2,
    },
    "nickel": {
        "baseColorFactor": [0.66, 0.61, 0.53, 1.0],
        "metallicFactor": 1.0,
        "roughnessFactor": 0.3,
    },
}


def download_bunny() -> str:
    if not os.path.exists(BUNNY_FILE):
        urllib.request.urlretrieve(BUNNY_URL, BUNNY_FILE)
    return BUNNY_FILE


def render_and_save(
    mesh_path: str,
    out_path: str,
    material: str,
    translate: np.ndarray,
    rotate: np.ndarray,
) -> None:
    mesh = trimesh.load(mesh_path, force="mesh")
    scene = pyrender.Scene()
    mat_cfg = MATERIALS.get(material, MATERIALS["iron"])
    mat = pyrender.MetallicRoughnessMaterial(**mat_cfg)

    transform = np.eye(4)
    transform[:3, 3] = translate
    rot = euler_matrix(
        np.deg2rad(rotate[0]),
        np.deg2rad(rotate[1]),
        np.deg2rad(rotate[2]),
    )
    transform[:3, :3] = rot[:3, :3]

    scene.add(
        pyrender.Mesh.from_trimesh(mesh, smooth=True, material=mat),
        pose=transform,
    )
    light = pyrender.DirectionalLight(color=np.ones(3), intensity=3.0)
    scene.add(light, pose=np.eye(4))
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0)
    scene.add(
        camera,
        pose=np.array([[1, 0, 0, 0], [0, 1, 0, -1], [0, 0, 1, 1.5], [0, 0, 0, 1]]),
    )
    renderer = pyrender.OffscreenRenderer(800, 600)
    color, _ = renderer.render(scene)
    iio.imwrite(out_path, color)
    renderer.delete()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render the Stanford Bunny with a metal material")
    parser.add_argument(
        "--material",
        choices=MATERIALS.keys(),
        default="iron",
        help="Material preset",
    )
    parser.add_argument("--out", default="bunny.png", help="Output image path")
    parser.add_argument(
        "--translate",
        nargs=3,
        type=float,
        default=(0.0, 0.0, 0.0),
        metavar=("X", "Y", "Z"),
        help="Translation of the mesh",
    )
    parser.add_argument(
        "--rotate",
        nargs=3,
        type=float,
        default=(0.0, 0.0, 0.0),
        metavar=("RX", "RY", "RZ"),
        help="Rotation in degrees around X, Y, Z axes",
    )
    args = parser.parse_args()

    path = download_bunny()
    render_and_save(path, args.out, args.material, np.array(args.translate), np.array(args.rotate))
    print(
        f"Saved {args.out} with {args.material} material at translate={args.translate} rotate={args.rotate}"
    )
