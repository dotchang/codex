import argparse
import numpy as np
from trimesh.transformations import euler_matrix


class BaseRenderer:
    def __init__(self) -> None:
        self.transform = np.eye(4)

    def load(self, path: str) -> None:
        raise NotImplementedError

    def render(self) -> None:
        raise NotImplementedError

    def set_transform(self, matrix: np.ndarray) -> None:
        self.transform = matrix


class Open3DRenderer(BaseRenderer):
    def __init__(self) -> None:
        super().__init__()
        import open3d as o3d

        self.o3d = o3d
        self.mesh = None

    def load(self, path: str) -> None:
        self.mesh = self.o3d.io.read_triangle_mesh(path)
        if self.mesh is None or self.mesh.is_empty():
            raise RuntimeError(f"Failed to load mesh: {path}")
        self.mesh.compute_vertex_normals()

    def render(self) -> None:
        if self.mesh is not None:
            self.mesh.transform(self.transform)
        self.o3d.visualization.draw_geometries([self.mesh])


class PyAssimpRenderer(BaseRenderer):
    def __init__(self) -> None:
        super().__init__()
        import pyassimp
        import trimesh
        import pyrender

        self.pyassimp = pyassimp
        self.trimesh = trimesh
        self.pyrender = pyrender
        self.meshes = []

    def load(self, path: str) -> None:
        scene = self.pyassimp.load(path)
        for m in scene.meshes:
            tm = self.trimesh.Trimesh(vertices=m.vertices, faces=m.faces)
            self.meshes.append(tm)
        self.pyassimp.release(scene)

    def render(self) -> None:
        scene = self.pyrender.Scene()
        for mesh in self.meshes:
            scene.add(
                self.pyrender.Mesh.from_trimesh(mesh), pose=self.transform
            )
        self.pyrender.Viewer(scene)


RENDERERS = {
    "open3d": Open3DRenderer,
    "pyassimp": PyAssimpRenderer,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple pluggable 3D viewer")
    parser.add_argument("path", help="Path to a 3D model file")
    parser.add_argument(
        "--backend",
        choices=RENDERERS.keys(),
        default="open3d",
        help="Rendering backend to use",
    )
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

    renderer = RENDERERS[args.backend]()
    renderer.load(args.path)
    transform = np.eye(4)
    transform[:3, 3] = np.array(args.translate)
    rot = euler_matrix(
        np.deg2rad(args.rotate[0]),
        np.deg2rad(args.rotate[1]),
        np.deg2rad(args.rotate[2]),
    )
    transform[:3, :3] = rot[:3, :3]
    renderer.set_transform(transform)
    renderer.render()


if __name__ == "__main__":
    main()
