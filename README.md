# CAD Viewer

A simple Python utility for viewing 3D CAD models with multiple backends.
`cad_viewer.py` uses [Open3D](https://www.open3d.org/) and can optionally load
STEP/IGES files via the [OCP](https://github.com/CadQuery/OCP) library.  For a
lightweight viewer that can switch between rendering libraries, see
`multi_viewer.py`.

## Usage

```bash
python cad_viewer.py <path_to_model> --material iron
```

Alternatively, the pluggable viewer lets you pick a backend:

```bash
python multi_viewer.py <path_to_model> --backend pyassimp  # or open3d
```

You can also position a model in space for dataset generation:

```bash
python multi_viewer.py model.obj --translate 0 0 1 --rotate 0 45 0
```

See `requirements.txt` for required dependencies.

## Example: render Stanford Bunny

`render_bunny.py` downloads the classic Stanford Bunny model and saves a rendered
image using headless EGL-based rendering. You can choose a metal material preset:

```bash
python render_bunny.py --material aluminum  # outputs bunny.png
```

Specify translation and rotation to render from different poses:

```bash
python render_bunny.py --rotate 0 90 0 --translate 0 0.2 0
```
