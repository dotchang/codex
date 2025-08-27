# CAD Viewer

A simple Python script for viewing 3D CAD models with [Open3D](https://www.open3d.org/).
It loads various mesh formats via Trimesh and optionally supports STEP/IGES through the
[OCP](https://github.com/CadQuery/OCP) library.

## Usage

```bash
python cad_viewer.py <path_to_model> --material iron
```
See `requirements.txt` for required dependencies.

## Example: render Stanford Bunny

`render_bunny.py` downloads the classic Stanford Bunny model and saves a rendered
image using headless EGL-based rendering. You can choose a metal material preset:

```bash
python render_bunny.py --material aluminum  # outputs bunny.png
```
