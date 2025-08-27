import os
import urllib.request
import numpy as np
import trimesh
import pyrender
import imageio.v2 as iio

# Use OSMesa for headless rendering
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

BUNNY_URL = "https://github.com/isl-org/open3d_downloads/releases/download/20220201-data/BunnyMesh.ply"
BUNNY_FILE = "bunny.ply"


def download_bunny() -> str:
    if not os.path.exists(BUNNY_FILE):
        urllib.request.urlretrieve(BUNNY_URL, BUNNY_FILE)
    return BUNNY_FILE


def render_and_save(mesh_path: str, out_path: str) -> None:
    mesh = trimesh.load(mesh_path, force='mesh')
    scene = pyrender.Scene()
    scene.add(pyrender.Mesh.from_trimesh(mesh, smooth=True))
    light = pyrender.DirectionalLight(color=np.ones(3), intensity=3.0)
    scene.add(light, pose=np.eye(4))
    camera = pyrender.PerspectiveCamera(yfov=np.pi / 3.0)
    scene.add(camera, pose=np.array([[1,0,0,0],[0,1,0,-1],[0,0,1,1.5],[0,0,0,1]]))
    renderer = pyrender.OffscreenRenderer(800, 600)
    color, _ = renderer.render(scene)
    iio.imwrite(out_path, color)
    renderer.delete()


if __name__ == "__main__":
    path = download_bunny()
    render_and_save(path, "bunny.png")
    print("Saved bunny.png")
