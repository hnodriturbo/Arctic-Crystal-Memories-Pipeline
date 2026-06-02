# =============================================================
# 03_mesh_generate.py — Point cloud and mesh generation
# =============================================================
# PURPOSE:
#   Third step. Converts the depth map into a 3D point cloud,
#   then generates a mesh from that point cloud. This is
#   the step that produces the actual 3D geometry that will be
#   exported to SSLE production software (Cockpit3D).
#
# TWO-STAGE PROCESS:
#   Stage A — Depth map → Point cloud
#     Each pixel in the depth map becomes an XYZ point.
#     X = pixel column, Y = pixel row, Z = depth value * Z_SCALE
#     Points where alpha=0 (background) are excluded.
#
#   Stage B — Point cloud → Mesh (Poisson Reconstruction)
#     Open3D's Poisson surface reconstruction builds a watertight
#     mesh from the point cloud. Higher MESH_POISSON_DEPTH = more
#     detail but slower and larger file.
#
# Z_SCALE IS CRITICAL:
#   Z_SCALE (from .env) controls how "deep" the engraving appears.
#   Too low = flat, boring engraving. Too high = crashes inside
#   crystal (points too close together cause cracks). Start at 0.3.
#   Adjust per crystal size when you know your machine limits.
#
# INPUTS:
#   - 16-bit depth PNGs from OUTPUT_DIR/depth_maps/
#   - Alpha masks from OUTPUT_DIR/bg_removed/ (for point masking)
#   - MESH_Z_SCALE, MESH_POISSON_DEPTH, MESH_EXPORT_FORMAT from .env
#
# OUTPUTS:
#   - Point cloud PLY: OUTPUT_DIR/point_clouds/{run}/{stem}_pointcloud.ply
#   - Mesh OBJ:        OUTPUT_DIR/meshes/{run}/{stem}_mesh.obj
#   - Mesh STL:        OUTPUT_DIR/meshes/{run}/{stem}_mesh.stl
#   - Mesh PLY:        OUTPUT_DIR/meshes/{run}/{stem}_mesh.ply
#
# USAGE:
#   python 03_mesh_generate.py
#   python 03_mesh_generate.py --file image_01_upscaled_nobg_depth_anything_v2_depth.png
#   python 03_mesh_generate.py --z-scale 0.5 --poisson-depth 10
#   python 03_mesh_generate.py --from-run try_02 --run try_01
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

# Resolve project root so imports work regardless of working directory
PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))
load_dotenv(PIPELINE_DIR / ".env")

from utils.file_utils import (
    get_output_dir,
    latest_run_name,
    resolve_run_name,
    STAGE_OUTPUT_DIRS,
)

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
# DEFAULTS from .env
# ----------------------------------------------------------------
DEFAULT_Z_SCALE      = float(os.getenv("MESH_Z_SCALE", "0.3"))
DEFAULT_POISSON      = int(os.getenv("MESH_POISSON_DEPTH", "9"))
DEFAULT_EXPORT_FMT   = os.getenv("MESH_EXPORT_FORMAT", "all").lower()

# Voxel size for downsampling before Poisson reconstruction.
# 0.002 keeps ~300K-500K points from a 3840x3840 map — enough detail
# without blowing up memory or mesh generation time.
VOXEL_DOWNSAMPLE_SIZE = float(os.getenv("MESH_VOXEL_SIZE", "0.002"))

# Density quantile threshold for trimming low-density boundary triangles.
# 0.01 removes the bottom 1% — just the rough fringe, not real geometry.
DENSITY_TRIM_QUANTILE = 0.01


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


def find_nobg_image(depth_path: Path, nobg_run: str) -> Path | None:
    """
    Locate the bg_removed RGBA PNG that corresponds to this depth map.

    Depth filenames follow the convention:
      {nobg_stem}_{model}_{profile}[_fSIGMA]_depth.png
    e.g. image_01_upscaled_nobg_depth_anything_v2_soft_edges_feathered_f100_depth.png
         → image_01_upscaled_nobg.png

    Strategy: split on the first known model suffix token to recover the nobg stem.
    """
    nobg_dir = get_output_dir("nobg", nobg_run)
    name = depth_path.stem  # e.g. image_01_upscaled_nobg_depth_anything_v2_standard_depth
    for model_suffix in ["_depth_anything_v2", "_midas", "_zoedepth", "_depth_pro", "_marigold", "_patchfusion"]:
        if model_suffix in name:
            nobg_stem = name.split(model_suffix)[0]
            candidate = nobg_dir / f"{nobg_stem}.png"
            if candidate.exists():
                return candidate
    return None


# ----------------------------------------------------------------
# DEPTH → POINT CLOUD
# ----------------------------------------------------------------

def depth_to_pointcloud(
    depth_path: Path,
    nobg_path: Path | None,
    z_scale: float,
) -> tuple[o3d.geometry.PointCloud, int]:
    """
    Convert a 16-bit depth PNG into an Open3D PointCloud.

    Returns (point_cloud, raw_point_count_before_downsample).
    """
    # Load 16-bit depth — keep full 16-bit range
    depth_img = Image.open(depth_path)
    depth_arr = np.array(depth_img, dtype=np.float32)  # 0..65535

    H, W = depth_arr.shape

    # Normalize to 0.0..1.0 (1.0 = closest to camera = highest Z in the model)
    depth_norm = depth_arr / 65535.0

    # Build alpha mask — background pixels are excluded from the point cloud
    if nobg_path is not None:
        try:
            mask_img = Image.open(nobg_path).convert("RGBA")
            mask_arr = np.array(mask_img)[:, :, 3]  # alpha channel
            fg_mask = mask_arr >= 128
        except Exception as e:
            print(f"  Warning: could not read mask from {nobg_path.name}: {e}")
            fg_mask = np.ones((H, W), dtype=bool)
    else:
        fg_mask = depth_norm > 0.0

    # Build XY grid — normalized to [-1, 1] so the mesh is unit-scale
    col_idx = np.arange(W, dtype=np.float32)
    row_idx = np.arange(H, dtype=np.float32)
    col_grid, row_grid = np.meshgrid(col_idx, row_idx)

    x = (col_grid / (W - 1)) * 2.0 - 1.0   # -1 (left) .. +1 (right)
    y = (row_grid / (H - 1)) * 2.0 - 1.0   # -1 (top)  .. +1 (bottom)
    y = -y                                  # flip so +Y is up (standard 3D convention)
    z = depth_norm * z_scale

    # Flatten and mask
    x_flat = x[fg_mask]
    y_flat = y[fg_mask]
    z_flat = z[fg_mask]
    raw_count = int(fg_mask.sum())

    xyz = np.stack([x_flat, y_flat, z_flat], axis=1).astype(np.float64)

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)

    # Downsample before normal estimation — reduces memory and speeds Poisson
    if VOXEL_DOWNSAMPLE_SIZE > 0:
        pcd = pcd.voxel_down_sample(voxel_size=VOXEL_DOWNSAMPLE_SIZE)

    # Estimate normals — required for Poisson reconstruction
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamKNN(knn=30)
    )
    # Orient normals consistently: all pointing away from a camera at (0, 0, 2)
    # This prevents Poisson from building an inside-out surface.
    pcd.orient_normals_towards_camera_location(camera_location=[0.0, 0.0, 2.0])

    return pcd, raw_count


# ----------------------------------------------------------------
# POINT CLOUD → MESH
# ----------------------------------------------------------------

def pointcloud_to_mesh(
    pcd: o3d.geometry.PointCloud,
    poisson_depth: int,
) -> o3d.geometry.TriangleMesh:
    """
    Run Poisson surface reconstruction and clean up the result.
    """
    print(f"  Running Poisson reconstruction (depth={poisson_depth})...")
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=poisson_depth, width=0, scale=1.1, linear_fit=False
    )

    # Trim the low-density fringe triangles Poisson adds at convex hull boundaries.
    # These appear as thin skirts around the mesh and are not real geometry.
    densities_np = np.asarray(densities)
    threshold = np.quantile(densities_np, DENSITY_TRIM_QUANTILE)
    verts_to_remove = densities_np < threshold
    mesh.remove_vertices_by_mask(verts_to_remove)

    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_non_manifold_edges()

    # Light smoothing — reduces Poisson surface noise without erasing features
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
    pointcloud_run: str,
    mesh_run: str,
) -> None:
    """Save point cloud PLY and mesh in all requested formats."""
    # Point cloud always saved as PLY regardless of MESH_EXPORT_FORMAT
    pcd_dir = get_output_dir("pointcloud", pointcloud_run)
    pcd_path = pcd_dir / f"{source_stem}_pointcloud.ply"
    try:
        o3d.io.write_point_cloud(str(pcd_path), pcd)
        print(f"  Point cloud → {pcd_path.name}  ({len(pcd.points):,} points)")
    except Exception as e:
        print(f"  ERROR saving point cloud: {e}")

    # Mesh formats
    mesh_dir = get_output_dir("mesh", mesh_run)

    formats: list[tuple[str, str]] = []
    if export_fmt == "all":
        formats = [("obj", ".obj"), ("stl", ".stl"), ("ply", ".ply")]
    elif export_fmt == "obj":
        formats = [("obj", ".obj")]
    elif export_fmt == "stl":
        formats = [("stl", ".stl")]
    elif export_fmt == "ply":
        formats = [("ply", ".ply")]
    else:
        # Comma-separated list: "obj,stl"
        for fmt in [f.strip() for f in export_fmt.split(",")]:
            if fmt in ("obj", "stl", "ply"):
                formats.append((fmt, f".{fmt}"))

    tri_count = len(np.asarray(mesh.triangles))
    for fmt_name, ext in formats:
        out_path = mesh_dir / f"{source_stem}_mesh{ext}"
        try:
            o3d.io.write_triangle_mesh(str(out_path), mesh)
            print(f"  Mesh ({fmt_name.upper()}) → {out_path.name}  ({tri_count:,} triangles)")
        except Exception as e:
            print(f"  ERROR saving {fmt_name} mesh: {e}")


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 04 — Generate 3D point cloud and mesh from depth map"
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Process a single depth map file (name only, not full path)"
    )
    parser.add_argument(
        "--z-scale", type=float, default=DEFAULT_Z_SCALE,
        help=f"Depth exaggeration factor (default: {DEFAULT_Z_SCALE})"
    )
    parser.add_argument(
        "--poisson-depth", type=int, default=DEFAULT_POISSON,
        help=f"Poisson reconstruction depth (default: {DEFAULT_POISSON})"
    )
    parser.add_argument(
        "--export-format", type=str, default=DEFAULT_EXPORT_FMT,
        choices=["obj", "stl", "ply", "all"],
        help=f"Mesh export format (default: {DEFAULT_EXPORT_FMT})"
    )
    parser.add_argument(
        "--from-run", type=str, default=None,
        help="Read depth maps from this run subfolder (default: latest)"
    )
    parser.add_argument(
        "--nobg-run", type=str, default=None,
        help="Read bg_removed masks from this run subfolder (default: latest)"
    )
    parser.add_argument(
        "--run", type=str, default=None,
        help="Write outputs to this run subfolder (default: auto-increment)"
    )
    return parser.parse_args()


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------

def main() -> None:
    args = parse_args()

    depth_run  = latest_run_name("depth", args.from_run)
    nobg_run   = latest_run_name("nobg",  args.nobg_run)
    tag = Path(args.file).stem if args.file else None
    output_run = resolve_run_name("mesh", args.run, tag=tag)

    print("=" * 60)
    print("Stage 04 — Mesh Generation")
    print(f"  Depth run:    {depth_run}")
    print(f"  Mask run:     {nobg_run}")
    print(f"  Output run:   {output_run}")
    print(f"  Z-scale:      {args.z_scale}")
    print(f"  Poisson depth:{args.poisson_depth}")
    print(f"  Export format:{args.export_format}")
    print("=" * 60)

    all_depth_maps = list_depth_maps(depth_run)
    if not all_depth_maps:
        print("No depth maps found. Run 03_depth_estimate.py first.")
        sys.exit(1)

    if args.file:
        targets = [p for p in all_depth_maps if p.name == args.file]
        if not targets:
            print(f"ERROR: {args.file} not found in run {depth_run}")
            sys.exit(1)
    else:
        targets = all_depth_maps

    for depth_path in tqdm(targets, desc="Generating meshes"):
        t0 = time.time()
        print(f"\nProcessing: {depth_path.name}")

        nobg_path = find_nobg_image(depth_path, nobg_run)
        if nobg_path:
            print(f"  Mask: {nobg_path.name}")
        else:
            print(f"  Warning: no matching nobg image found — using depth threshold as mask")

        try:
            pcd, raw_count = depth_to_pointcloud(depth_path, nobg_path, args.z_scale)
            print(f"  Points: {raw_count:,} raw → {len(pcd.points):,} after voxel downsample")

            mesh = pointcloud_to_mesh(pcd, args.poisson_depth)

            # Use depth map stem as output name prefix
            stem = depth_path.stem  # e.g. image_01_upscaled_nobg_depth_anything_v2_depth
            save_mesh_outputs(pcd, mesh, stem, args.export_format, output_run, output_run)

            elapsed = time.time() - t0
            print(f"  Done in {elapsed:.1f}s")

        except Exception as e:
            print(f"  ERROR processing {depth_path.name}: {e}")
            import traceback
            traceback.print_exc()

    print("\nStage 04 complete.")


if __name__ == "__main__":
    main()
