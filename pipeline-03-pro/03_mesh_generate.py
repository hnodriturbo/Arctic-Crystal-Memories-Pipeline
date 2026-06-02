# =============================================================
# 03_mesh_generate.py — Point cloud + mesh + vertex color projection
# =============================================================
# PURPOSE:
#   Third step. Converts the depth map into a 3D point cloud,
#   projects RGB color onto each point, runs Poisson surface
#   reconstruction, and saves a vertex-colored mesh for the
#   artist review path (Path A — geometry only).
#
#   This is a pro-pipeline upgrade from pipeline-02: every point
#   in the cloud carries (X, Y, Z, R, G, B) from the source photo.
#   The result is a colored mesh that can be inspected in MeshLab
#   or Blender before texture baking in step 04b.
#
# TWO-STAGE PROCESS:
#   Stage A — Depth map -> Point cloud with vertex colors
#     Each pixel -> XYZ point. Background pixels (alpha=0) excluded.
#     RGB is sampled from the source RGBA image composited on grey
#     (avoids black fringing at hair boundaries).
#
#   Stage B — Point cloud -> Mesh (Poisson Reconstruction)
#     Open3D Poisson builds a watertight mesh. Higher poisson_depth
#     = more detail but slower and more memory use.
#
# WHY 1800px — NOT A QUALITY LIMIT:
#   Depth Anything V2 (and every other depth model) resizes its input
#   internally to ~384-518px before inference. Feeding a 4x-upscaled
#   10K image gives IDENTICAL depth quality to a 1800px image — the
#   extra pixels are invisible to the model. Upscaling only adds
#   interpolated pixels that were never in the depth estimate, so the
#   resulting point cloud has 157M vertices all carrying the same
#   limited depth information — a guaranteed OOM crash on 16GB RAM
#   with zero quality gain.
#
#   1800px is not a quality compromise. It is the highest-information
#   resolution the depth model can use. Full production mesh quality
#   comes from Poisson depth and voxel size settings, not from source
#   image pixel count past what the depth model can consume.
#
# TRIANGLE COUNT AND QUALITY:
#   Use POISSON_DEPTH and MESH_VOXEL_SIZE to control output quality:
#     POISSON_DEPTH=9    — fast draft, ~100K-300K triangles
#     POISSON_DEPTH=10   — standard, ~300K-800K triangles
#     POISSON_DEPTH=11   — production quality, ~1M-3M triangles (default)
#     POISSON_DEPTH=12   — maximum, ~3M-8M triangles, slow, ~12GB RAM
#   Smaller MESH_VOXEL_SIZE keeps more points -> denser mesh at any depth.
#   MESH_VOXEL_SIZE=0.0 disables downsampling entirely (all source pixels).
#
# PHASE 3 HUMAN RECONSTRUCTION:
#   Stubbed. Passes through without modification. To activate:
#   pass --reconstruction mediapipe or --reconstruction face_align.
#   The stubs are wired but the landmark logic is not implemented
#   yet — they will raise NotImplementedError when called.
#
# OUTPUTS:
#   output/point_clouds/{run}/{stem}_pointcloud.ply       — vertex-colored PLY
#   output/meshes/{run}/geometry/{stem}_mesh.obj          — vertex-colored mesh OBJ
#   output/meshes/{run}/geometry/{stem}_mesh.ply          — vertex-colored mesh PLY
#
# USAGE:
#   python 03_mesh_generate.py
#   python 03_mesh_generate.py --z-scale 0.3 --poisson-depth 10
#   python 03_mesh_generate.py --no-color
#   python 03_mesh_generate.py --from-run try_01 --run try_01
#   python 03_mesh_generate.py --export-format obj
#
# DEPENDENCIES: open3d, numpy, Pillow, python-dotenv, tqdm
# =============================================================

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from dotenv import load_dotenv

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))
load_dotenv(PIPELINE_DIR / ".env")

from utils.file_utils import (
    get_output_dir,
    latest_run_name,
    resolve_run_name,
    STAGE_OUTPUT_DIRS,
)
from utils.image_utils import composite_rgba_on_grey

try:
    import open3d as o3d
except ImportError:
    print("ERROR: open3d not installed. Run: pip install open3d")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm is not installed. Run: pip install tqdm")
    sys.exit(1)


# ----------------------------------------------------------------
# DEFAULTS
# ----------------------------------------------------------------
DEFAULT_Z_SCALE    = float(os.getenv("Z_SCALE", "0.3"))
DEFAULT_POISSON    = int(os.getenv("POISSON_DEPTH", "11"))    # 11 = production; 12 = maximum
DEFAULT_EXPORT_FMT = os.getenv("MESH_EXPORT_FORMAT", "all").lower()
VOXEL_DOWNSAMPLE_SIZE = float(os.getenv("MESH_VOXEL_SIZE", "0.001"))  # smaller = denser mesh
DENSITY_TRIM_QUANTILE = 0.01


# ----------------------------------------------------------------
# RECONSTRUCTION REGISTRY (Phase 3 — all stubbed)
# ----------------------------------------------------------------

def run_reconstruction_stub(rgba_image, depth_map):
    """Phase 3 is stubbed — geometry comes from depth only."""
    print("  Phase 3 (Human Reconstruction): STUBBED — using depth geometry only")
    return None


def run_reconstruction_mediapipe(rgba_image, depth_map):
    raise NotImplementedError(
        "MediaPipe reconstruction not yet implemented. "
        "Install mediapipe and implement landmark projection to activate."
    )


def run_reconstruction_face_align(rgba_image, depth_map):
    raise NotImplementedError(
        "face-alignment reconstruction not yet implemented. "
        "Install face-alignment and implement 3D landmark projection to activate."
    )


RECONSTRUCTION_REGISTRY = {
    "none":         run_reconstruction_stub,
    "mediapipe":    run_reconstruction_mediapipe,
    "face_align":   run_reconstruction_face_align,
}


# ----------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------

def list_depth_maps(run: str) -> list[Path]:
    """Return all 16-bit depth PNG files in the given depth_maps run folder."""
    depth_dir = get_output_dir("depth", run)
    files = sorted(
        [p for p in depth_dir.iterdir() if p.name.endswith("_depth.png")],
        key=lambda p: p.name.lower(),
    )
    print(f"Found {len(files)} depth map(s) in: {depth_dir}")
    return files


def find_prepared_image(depth_path: Path, prepared_run: str) -> Path | None:
    """
    Locate the _prepared.png that corresponds to this depth map.

    Depth filenames: {prepared_stem}_{model}_{profile}_depth.png
    Strategy: strip known model tokens to recover the prepared stem.
    """
    prepared_dir = get_output_dir("prepared", prepared_run)
    name = depth_path.stem  # e.g. photo_prepared_depth_anything_v2_standard_depth
    for model_token in ["_depth_anything_v2", "_midas", "_depth_pro", "_marigold"]:
        if model_token in name:
            prepared_stem = name.split(model_token)[0]
            candidate = prepared_dir / f"{prepared_stem}.png"
            if candidate.exists():
                return candidate
    return None


# ----------------------------------------------------------------
# DEPTH -> POINT CLOUD WITH VERTEX COLORS
# ----------------------------------------------------------------

def depth_to_pointcloud(
    depth_path: Path,
    prepared_path: Path | None,
    z_scale: float,
    use_color: bool = True,
) -> tuple[o3d.geometry.PointCloud, int]:
    """
    Convert a 16-bit depth PNG into an Open3D PointCloud with vertex colors.

    Each pixel becomes an XYZ point. Background pixels (alpha=0) are excluded.
    RGB is sampled from the prepared RGBA image composited onto neutral grey
    to avoid dark fringing at semi-transparent hair boundaries.

    Returns (point_cloud, raw_point_count_before_downsample).
    """
    depth_img = Image.open(depth_path)
    depth_arr = np.array(depth_img, dtype=np.float32)
    H, W = depth_arr.shape
    depth_norm = depth_arr / 65535.0

    # Build alpha mask and color from prepared RGBA
    if prepared_path is not None:
        try:
            rgba_img = Image.open(prepared_path).convert("RGBA")
            rgba_arr = np.array(rgba_img)
            alpha_arr = rgba_arr[:, :, 3]
            fg_mask = alpha_arr >= 128

            if use_color:
                # Composite onto grey to avoid black fringing at hair edges
                rgb_arr = composite_rgba_on_grey(rgba_arr, grey=128)
            else:
                rgb_arr = None
        except Exception as e:
            print(f"  Warning: could not read prepared image {prepared_path.name}: {e}")
            fg_mask = depth_norm > 0.0
            rgb_arr = None
    else:
        fg_mask = depth_norm > 0.0
        rgb_arr = None

    # Build unit-scale XY grid
    col_idx = np.arange(W, dtype=np.float32)
    row_idx = np.arange(H, dtype=np.float32)
    col_grid, row_grid = np.meshgrid(col_idx, row_idx)

    x = (col_grid / (W - 1)) * 2.0 - 1.0
    y = -((row_grid / (H - 1)) * 2.0 - 1.0)  # flip: +Y is up
    z = depth_norm * z_scale

    x_flat = x[fg_mask]
    y_flat = y[fg_mask]
    z_flat = z[fg_mask]
    raw_count = int(fg_mask.sum())

    xyz = np.stack([x_flat, y_flat, z_flat], axis=1).astype(np.float64)

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)

    if rgb_arr is not None:
        colors_flat = rgb_arr[fg_mask].astype(np.float64) / 255.0
        pcd.colors = o3d.utility.Vector3dVector(colors_flat)

    if VOXEL_DOWNSAMPLE_SIZE > 0:
        pcd = pcd.voxel_down_sample(voxel_size=VOXEL_DOWNSAMPLE_SIZE)

    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamKNN(knn=30))
    pcd.orient_normals_towards_camera_location(camera_location=[0.0, 0.0, 2.0])

    return pcd, raw_count


# ----------------------------------------------------------------
# POINT CLOUD -> MESH
# ----------------------------------------------------------------

def pointcloud_to_mesh(
    pcd: o3d.geometry.PointCloud,
    poisson_depth: int,
) -> o3d.geometry.TriangleMesh:
    """Run Poisson surface reconstruction and clean up the result."""
    print(f"  Running Poisson reconstruction (depth={poisson_depth})...")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=poisson_depth, width=0, scale=1.1, linear_fit=False
    )

    densities_np = np.asarray(densities)
    threshold = np.quantile(densities_np, DENSITY_TRIM_QUANTILE)
    verts_to_remove = densities_np < threshold
    mesh.remove_vertices_by_mask(verts_to_remove)

    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()

    mesh = mesh.filter_smooth_laplacian(number_of_iterations=2)
    mesh.compute_vertex_normals()

    return mesh


# ----------------------------------------------------------------
# SAVE OUTPUTS
# ----------------------------------------------------------------

def save_mesh_outputs(
    pcd: o3d.geometry.PointCloud,
    mesh: o3d.geometry.TriangleMesh,
    source_stem: str,
    export_fmt: str,
    run: str,
) -> None:
    """Save point cloud PLY and vertex-colored mesh to geometry subfolder."""
    pcd_dir = get_output_dir("pointcloud", run)
    pcd_path = pcd_dir / f"{source_stem}_pointcloud.ply"
    try:
        o3d.io.write_point_cloud(str(pcd_path), pcd)
        print(f"  Point cloud -> {pcd_path.name}  ({len(pcd.points):,} points)")
    except Exception as e:
        print(f"  ERROR saving point cloud: {e}")

    # Geometry subfolder inside meshes/{run}/
    mesh_base = get_output_dir("mesh", run)
    geometry_dir = mesh_base / "geometry"
    geometry_dir.mkdir(parents=True, exist_ok=True)

    formats: list[tuple[str, str]] = []
    if export_fmt == "all":
        formats = [("obj", ".obj"), ("ply", ".ply")]
    elif export_fmt == "obj":
        formats = [("obj", ".obj")]
    elif export_fmt == "ply":
        formats = [("ply", ".ply")]
    elif export_fmt == "stl":
        formats = [("stl", ".stl")]
    else:
        for fmt in [f.strip() for f in export_fmt.split(",")]:
            if fmt in ("obj", "ply", "stl"):
                formats.append((fmt, f".{fmt}"))

    tri_count = len(np.asarray(mesh.triangles))
    for fmt_name, ext in formats:
        out_path = geometry_dir / f"{source_stem}_mesh{ext}"
        try:
            o3d.io.write_triangle_mesh(str(out_path), mesh)
            print(f"  Mesh ({fmt_name.upper()}) -> {out_path.relative_to(PIPELINE_DIR)}  ({tri_count:,} triangles)")
        except Exception as e:
            print(f"  ERROR saving {fmt_name} mesh: {e}")


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 03 — Generate vertex-colored 3D point cloud and mesh from depth map"
    )
    parser.add_argument("--file", type=str, default=None,
                        help="Process a single depth map file (name only)")
    parser.add_argument("--z-scale", type=float, default=DEFAULT_Z_SCALE,
                        help=f"Depth exaggeration factor (default: {DEFAULT_Z_SCALE})")
    parser.add_argument("--poisson-depth", type=int, default=DEFAULT_POISSON,
                        help=f"Poisson reconstruction depth (default: {DEFAULT_POISSON})")
    parser.add_argument("--export-format", type=str, default=DEFAULT_EXPORT_FMT,
                        choices=["obj", "ply", "stl", "all"],
                        help=f"Mesh export format (default: {DEFAULT_EXPORT_FMT})")
    parser.add_argument("--no-color", action="store_true",
                        help="Skip color projection — geometry-only output")
    parser.add_argument("--reconstruction", type=str, default="none",
                        choices=list(RECONSTRUCTION_REGISTRY.keys()),
                        help="Phase 3 reconstruction mode (default: none = stubbed)")
    parser.add_argument("--from-run", type=str, default=None,
                        help="Read depth maps from this run subfolder (default: latest)")
    parser.add_argument("--prepared-run", type=str, default=None,
                        help="Read prepared images from this run subfolder (default: latest)")
    parser.add_argument("--run", type=str, default=None,
                        help="Write outputs to this run subfolder (default: auto-increment)")
    return parser.parse_args()


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------

def main() -> None:
    args = parse_args()

    depth_run    = latest_run_name("depth",    args.from_run)
    prepared_run = latest_run_name("prepared", args.prepared_run)
    tag = Path(args.file).stem if args.file else None
    output_run = resolve_run_name("mesh", args.run, tag=tag)

    print("=" * 60)
    print("K9 Crystal Pipeline 03 Pro  —  Step 03: Mesh Generation")
    print(f"  Depth run:    {depth_run}")
    print(f"  Prepared run: {prepared_run}")
    print(f"  Output run:   {output_run}")
    print(f"  Z-scale:      {args.z_scale}")
    print(f"  Poisson depth:{args.poisson_depth}")
    print(f"  Export format:{args.export_format}")
    print(f"  Color:        {'disabled' if args.no_color else 'enabled (composite-on-grey)'}")
    print(f"  Phase 3:      {args.reconstruction}")
    print("=" * 60)

    all_depth_maps = list_depth_maps(depth_run)
    if not all_depth_maps:
        print("No depth maps found. Run step 02 first: python 02_depth_estimate.py")
        sys.exit(1)

    if args.file:
        targets = [p for p in all_depth_maps if p.name == args.file]
        if not targets:
            print(f"ERROR: {args.file} not found in run {depth_run}")
            sys.exit(1)
    else:
        targets = all_depth_maps

    reconstruction_fn = RECONSTRUCTION_REGISTRY[args.reconstruction]

    for depth_path in tqdm(targets, desc="Generating meshes"):
        t0 = time.time()
        print(f"\nProcessing: {depth_path.name}")

        prepared_path = find_prepared_image(depth_path, prepared_run)
        if prepared_path:
            print(f"  Source:   {prepared_path.name}")
        else:
            print("  Warning: no matching prepared image found — using depth threshold as mask")

        try:
            # Phase 3 reconstruction (stubbed unless activated)
            if prepared_path:
                rgba_img = np.array(Image.open(prepared_path).convert("RGBA"))
                depth_arr = np.array(Image.open(depth_path), dtype=np.float32) / 65535.0
                reconstruction_fn(rgba_img, depth_arr)

            pcd, raw_count = depth_to_pointcloud(
                depth_path,
                prepared_path,
                args.z_scale,
                use_color=not args.no_color,
            )
            has_color = pcd.has_colors()
            print(f"  Points:   {raw_count:,} raw -> {len(pcd.points):,} after voxel downsample  |  colors={has_color}")

            mesh = pointcloud_to_mesh(pcd, args.poisson_depth)

            stem = depth_path.stem
            save_mesh_outputs(pcd, mesh, stem, args.export_format, output_run)

            elapsed = time.time() - t0
            print(f"  Done in {elapsed:.1f}s")

        except Exception as e:
            print(f"  ERROR processing {depth_path.name}: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print("Step 03 complete.")
    print(f"  Output: output/meshes/{output_run}/geometry/")
    print()
    print("  QUALITY CHECK: Open the PLY in MeshLab.")
    print("    - Face should be visible from the front (normals correct)")
    print("    - Vertex colors should show skin tones (not uniform grey)")
    print("    - Nose tip should protrude — Z relief should be visible")
    print()
    print("Next step: python 04b_texture_bake.py  (UV unwrap + photo texture)")
    print("       or: python 05_export.py          (skip texture, export geometry only)")
    print("=" * 60)


if __name__ == "__main__":
    main()
