import sys
import os
import numpy as np

# 依存関係
try:
    import open3d as o3d
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "open3d is required for visualization. Install it with 'pip install open3d'."
    ) from exc

try:
    import trimesh
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "trimesh is required for mesh processing. Install it with 'pip install trimesh'."
    ) from exc

# OCP (pythonocc) は任意
try:
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IGESControl import IGESControl_Reader
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.ShapeFix import ShapeFix_Shape
    from OCP.TopoDS import topods_Face
    from OCP.Poly import Poly_Triangulation
    OCP_AVAILABLE = True
except Exception:
    OCP_AVAILABLE = False


def to_o3d_from_trimesh(tmesh: trimesh.Trimesh) -> o3d.geometry.TriangleMesh:
    # 頂点・面の配列をOpen3Dへ
    g = o3d.geometry.TriangleMesh()
    g.vertices = o3d.utility.Vector3dVector(np.asarray(tmesh.vertices, dtype=np.float64))
    g.triangles = o3d.utility.Vector3iVector(np.asarray(tmesh.faces, dtype=np.int32))

    # 頂点色（あれば）
    if tmesh.visual.kind == 'vertex' and tmesh.visual.vertex_colors is not None:
        vc = np.asarray(tmesh.visual.vertex_colors)[:, :3] / 255.0
        g.vertex_colors = o3d.utility.Vector3dVector(vc)

    # 法線
    g.compute_vertex_normals()
    return g


def load_mesh_generic(path: str) -> o3d.geometry.TriangleMesh:
    """
    多形式ローダー：拡張子に応じて最適な読み込み経路を選択し、
    Open3D TriangleMesh を返す
    """
    ext = os.path.splitext(path)[1].lower()

    # Open3Dが直接読める（obj, ply, stl, gltf/glb, off, 3mf など）
    o3d_loadable = {".obj", ".ply", ".stl", ".gltf", ".glb", ".off", ".3mf"}
    if ext in o3d_loadable:
        mesh = o3d.io.read_triangle_mesh(path, enable_post_processing=True)
        if mesh is None or mesh.is_empty():
            raise RuntimeError(f"Open3D failed to load: {path}")
        mesh.compute_vertex_normals()
        return mesh

    # Trimeshで広く読む（obj, ply, stl, gltf/glb, 3mf, off, 3ds など）
    # ※FBXはTrimesh非対応。FBXはglTFへ事前変換推奨（Blender/Assimp）。
    if ext in {".obj", ".ply", ".stl", ".gltf", ".glb", ".3mf", ".off", ".3ds"}:
        tmesh = trimesh.load(path, force='mesh')
        if tmesh is None or tmesh.is_empty:
            raise RuntimeError(f"trimesh failed to load: {path}")
        return to_o3d_from_trimesh(tmesh)

    # STEP/IGES → OCPでB-Repを三角形化（任意）
    if ext in {".step", ".stp", ".iges", ".igs"}:
        if not OCP_AVAILABLE:
            raise RuntimeError(
                "STEP/IGES を読むには `pip install OCP` が必要です。"
            )
        return load_step_iges_to_o3d(path)

    raise RuntimeError(f"Unsupported extension: {ext}")


def _shape_to_o3d_mesh(shape) -> o3d.geometry.TriangleMesh:
    """
    OCP Shape（B-Rep）→ 三角形メッシュ化 → Open3D TriangleMesh
    """
    # 形状の修正（面の向きやトポロジ補修）
    fixer = ShapeFix_Shape(shape)
    fixer.Perform()
    fixed = fixer.Shape()

    # 三角形化（メッシュ化の細かさは環境に応じて調整）
    BRepMesh_IncrementalMesh(fixed, 0.5, True, 0.5, True)  # (deflection, isRelative, angle, parallel)

    explorer = TopExp_Explorer(fixed, TopAbs_FACE)
    vertices = []
    faces = []
    vmap = {}

    def add_vertex(p):
        key = (p.X(), p.Y(), p.Z())
        idx = vmap.get(key)
        if idx is None:
            idx = len(vertices)
            vertices.append([p.X(), p.Y(), p.Z()])
            vmap[key] = idx
        return idx

    while explorer.More():
        face = topods_Face(explorer.Current())
        loc = face.Location()
        triangulation = BRep_Tool.Triangulation(face, loc)
        if triangulation is None:
            explorer.Next()
            continue

        # 頂点座標
        nodes = triangulation.Nodes()
        tri: Poly_Triangulation = triangulation
        for t in range(1, tri.NbTriangles() + 1):
            tr = tri.Triangle(t)
            # OCCは1始まり
            ids = [tr.Value(1), tr.Value(2), tr.Value(3)]
            idxs = []
            for nid in ids:
                pnt = nodes.Value(nid)
                idxs.append(add_vertex(pnt))
            faces.append(idxs)
        explorer.Next()

    if len(vertices) == 0 or len(faces) == 0:
        raise RuntimeError("Triangulation failed or empty model.")

    g = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(np.array(vertices, dtype=np.float64)),
        o3d.utility.Vector3iVector(np.array(faces, dtype=np.int32)),
    )
    g.remove_duplicated_vertices()
    g.remove_degenerate_triangles()
    g.remove_duplicated_triangles()
    g.remove_non_manifold_edges()
    g.compute_vertex_normals()
    return g


def load_step_iges_to_o3d(path: str) -> o3d.geometry.TriangleMesh:
    ext = os.path.splitext(path)[1].lower()
    if ext in {".step", ".stp"}:
        reader = STEPControl_Reader()
        status = reader.ReadFile(path)
        if status != 0:
            raise RuntimeError(f"STEP read error: {status}")
        reader.TransferRoots()
        shape = reader.OneShape()
        return _shape_to_o3d_mesh(shape)
    else:
        reader = IGESControl_Reader()
        status = reader.ReadFile(path)
        if status != 0:
            raise RuntimeError(f"IGES read error: {status}")
        reader.TransferRoots()
        shape = reader.OneShape()
        return _shape_to_o3d_mesh(shape)


def setup_pbr_scene(mesh: o3d.geometry.TriangleMesh):
    # マテリアル設定：既存テクスチャ/カラーがあれば利用
    material = o3d.visualization.rendering.MaterialRecord()
    # PBR（メタリック/ラフネス）
    material.shader = "defaultLit"

    # 頂点カラーがある場合は自動適用。なければ灰色
    if not mesh.has_vertex_colors() and not mesh.has_textures():
        mesh.paint_uniform_color([0.7, 0.7, 0.72])

    return material


def visualize(mesh: o3d.geometry.TriangleMesh, title="CAD Viewer"):
    mesh.compute_vertex_normals()

    # ハイレベルGUI（O3DVisualizer）
    app = o3d.visualization.gui.Application.instance
    app.initialize()

    w = o3d.visualization.O3DVisualizer(title, 1280, 800)
    w.show_settings = True

    mat = setup_pbr_scene(mesh)
    w.add_geometry("model", mesh, mat)

    # 背景とライティング
    w.set_background((0.02, 0.02, 0.025, 1.0))
    w.scene.set_sun_light(
        direction=[-1.0, -1.0, -1.0],  # 適度な斜め光
        intensity=65000,               # 多少強め
        color=[1.0, 1.0, 1.0]
    )
    w.scene.enable_sun_light(True)

    # IBL (環境マップ) は任意。HDR (.hdr/.exr) を用意できるなら設定可能
    # 例: w.scene.scene.set_indirect_light("path/to/hdr.exr")

    # トーンマッピング/SSAO/シャドウ
    w.scene.set_shadow_intensity(0.4)
    w.scene.enable_screen_space_reflections(True)
    w.scene.enable_indirect_light(True)

    app.add_window(w)
    app.run()


def main():
    if len(sys.argv) < 2:
        print("Usage: python cad_viewer.py <path_to_model>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    mesh = load_mesh_generic(path)
    visualize(mesh, f"CAD Viewer - {os.path.basename(path)}")


if __name__ == "__main__":
    main()
