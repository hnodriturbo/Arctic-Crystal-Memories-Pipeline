# =============================================================
# 04b_texture_bake.py — UV unwrap + photo texture projection
# =============================================================
# PURPOSE:
#   Phase 4 Path B. Takes the geometry mesh from step 03 and
#   produces an SSLE-ready textured mesh by:
#     1. UV unwrapping with xatlas (default) or RizomUV / MoF
#     2. Projecting the source photo texture onto the UV-mapped mesh
#     3. Exporting OBJ+MTL+atlas PNG and GLB (binary GLTF)
#
# WHY TEXTURE MATTERS FOR CRYSTAL QUALITY:
#   Without texture, Cockpit3D assigns laser power from geometry
#   alone. With a photo-textured mesh, every surface point carries
#   its actual photo color. Cockpit3D samples that color to assign
#   precise power values — encoding portrait shading directly into
#   the crystal. Texture is not decoration, it is accuracy.
#
# OUTPUT PATHS:
#   output/meshes/{run}/textured/{stem}_textured.obj
#   output/meshes/{run}/textured/{stem}_textured.mtl
#   output/meshes/{run}/textured/{stem}_atlas.png
#   output/meshes/{run}/textured/{stem}_textured.glb
#
# USAGE:
#   python 04b_texture_bake.py
#   python 04b_texture_bake.py --uv-tool xatlas
#   python 04b_texture_bake.py --atlas-size 8192
#   python 04b_texture_bake.py --no-glb
#   python 04b_texture_bake.py --from-run try_01 --from-bg-run try_01 --run bake_01
#
# DEPENDENCIES: open3d, trimesh, xatlas, pymeshlab, Pillow, numpy, tqdm
# =============================================================

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from PIL import Image

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))
load_dotenv(PIPELINE_DIR / ".env")

from utils.file_utils import get_output_dir, latest_run_name, resolve_run_name
from utils.image_utils import composite_rgba_on_grey

try:
    import open3d as o3d
except ImportError:
    print("ERROR: open3d not installed. Run: pip install open3d")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm not installed. Run: pip install tqdm")
    sys.exit(1)


# ----------------------------------------------------------------
# DEFAULTS
# ----------------------------------------------------------------
DEFAULT_UV_TOOL = os.getenv("UV_TOOL", "xatlas")
DEFAULT_ATLAS_SIZE = int(os.getenv("TEXTURE_ATLAS_SIZE", "4096"))


# ----------------------------------------------------------------
# UV TOOLS
# ----------------------------------------------------------------


def uv_with_xatlas(
    vertices: np.ndarray, faces: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate UV coordinates using xatlas.

    Returns (uvs, vmapping, indices) where:
        uvs:      (N, 2) float32 UV coordinates for the new vertex set
        vmapping: (N,) original vertex indices
        indices:  (F, 3) face indices into the new vertex set
    """
    try:
        import xatlas
    except ImportError:
        raise ImportError("xatlas not installed. Run: pip install xatlas")

    atlas = xatlas.Atlas()
    atlas.add_mesh(vertices.astype(np.float32), faces.astype(np.uint32))
    atlas.generate(xatlas.ChartOptions(), xatlas.PackOptions())
    vmapping, indices, uvs = atlas[0]
    return uvs, vmapping, indices


def uv_with_rizomuv(
    vertices: np.ndarray, faces: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Stub: RizomUV subprocess call. Requires RizomUV CLI installation."""
    raise NotImplementedError(
        "RizomUV UV tool is not yet implemented. "
        "Install RizomUV and implement the subprocess call. Use xatlas for now."
    )


def uv_with_mof(
    vertices: np.ndarray, faces: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Stub: Ministry of Flat subprocess call. Requires mof.exe in tools/."""
    raise NotImplementedError(
        "Ministry of Flat UV tool is not yet implemented. "
        "Place mof.exe in tools/ and implement the subprocess call. Use xatlas for now."
    )


UV_TOOLS = {
    "xatlas": uv_with_xatlas,
    "rizomuv": uv_with_rizomuv,
    "mof": uv_with_mof,
}


# ----------------------------------------------------------------
# PHOTO TEXTURE PROJECTION
# ----------------------------------------------------------------


def project_photo_to_atlas(
    vertices: np.ndarray,
    uvs: np.ndarray,
    vmapping: np.ndarray,
    faces_uv: np.ndarray,
    photo_rgb: np.ndarray,
    atlas_size: int,
) -> np.ndarray:
    """
    Project photo colors onto a UV atlas by rasterizing UV triangles.

    For each UV triangle, samples the corresponding pixel region
    from the source photo using barycentric coordinates.

    Args:
        vertices:   (V, 3) float32 original vertices
        uvs:        (N, 2) float32 UV coordinates
        vmapping:   (N,) original vertex indices
        faces_uv:   (F, 3) face indices into the UV vertex set
        photo_rgb:  (H, W, 3) uint8 source photo in RGB
        atlas_size: Output atlas resolution in pixels

    Returns:
        (atlas_size, atlas_size, 3) uint8 RGB atlas image
    """
    # Map UV vertices back to 3D positions
    uv_vertices_3d = vertices[vmapping]  # (N, 3)

    H, W = photo_rgb.shape[:2]
    atlas = np.zeros((atlas_size, atlas_size, 3), dtype=np.uint8)

    # Precompute UV pixel coords
    uv_px = (uvs * (atlas_size - 1)).astype(np.float32)

    for face in faces_uv:
        i0, i1, i2 = face
        # 3D positions (for photo sampling)
        p0, p1, p2 = uv_vertices_3d[i0], uv_vertices_3d[i1], uv_vertices_3d[i2]
        # UV positions in atlas space
        u0, u1, u2 = uv_px[i0], uv_px[i1], uv_px[i2]

        # Bounding box in atlas
        min_u = int(np.floor(min(u0[0], u1[0], u2[0])))
        max_u = int(np.ceil(max(u0[0], u1[0], u2[0])))
        min_v = int(np.floor(min(u0[1], u1[1], u2[1])))
        max_v = int(np.ceil(max(u0[1], u1[1], u2[1])))

        min_u = max(0, min_u)
        max_u = min(atlas_size - 1, max_u)
        min_v = max(0, min_v)
        max_v = min(atlas_size - 1, max_v)

        # Sample pixels inside the bounding box
        for ay in range(min_v, max_v + 1):
            for ax in range(min_u, max_u + 1):
                p = np.array([ax, ay], dtype=np.float32)

                # Barycentric coordinates in UV space
                v0 = u1 - u0
                v1 = u2 - u0
                v2 = p - u0
                d00 = np.dot(v0, v0)
                d01 = np.dot(v0, v1)
                d11 = np.dot(v1, v1)
                d20 = np.dot(v2, v0)
                d21 = np.dot(v2, v1)
                denom = d00 * d11 - d01 * d01
                if abs(denom) < 1e-10:
                    continue
                bv = (d11 * d20 - d01 * d21) / denom
                bw = (d00 * d21 - d01 * d20) / denom
                bu = 1.0 - bv - bw

                if bu < 0 or bv < 0 or bw < 0:
                    continue

                # Interpolate 3D position
                pos = bu * p0 + bv * p1 + bw * p2

                # Map 3D position to photo pixel (X,Y map to W,H; Z ignored)
                px = int(np.clip((pos[0] + 1.0) / 2.0 * (W - 1), 0, W - 1))
                py = int(np.clip((-pos[1] + 1.0) / 2.0 * (H - 1), 0, H - 1))

                atlas[ay, ax] = photo_rgb[py, px]

    return atlas


# ----------------------------------------------------------------
# EXPORT HELPERS
# ----------------------------------------------------------------


def save_obj_with_texture(
    vertices: np.ndarray,
    uvs: np.ndarray,
    vmapping: np.ndarray,
    faces_uv: np.ndarray,
    atlas_path: Path,
    obj_path: Path,
) -> None:
    """Write OBJ + MTL files with the texture atlas reference."""
    mtl_path = obj_path.with_suffix(".mtl")
    mtl_name = mtl_path.name

    with open(str(mtl_path), "w") as f:
        f.write(f"newmtl material0\n")
        f.write(f"map_Kd {atlas_path.name}\n")

    uv_vertices_3d = vertices[vmapping]

    with open(str(obj_path), "w") as f:
        f.write(f"mtllib {mtl_name}\n")
        f.write("usemtl material0\n")
        for v in uv_vertices_3d:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
        for uv in uvs:
            f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")
        for face in faces_uv:
            i0, i1, i2 = face + 1  # OBJ is 1-indexed
            f.write(f"f {i0}/{i0} {i1}/{i1} {i2}/{i2}\n")


def save_glb(obj_path: Path, atlas_path: Path, glb_path: Path) -> None:
    """Export the textured mesh as binary GLTF (.glb) via trimesh."""
    try:
        import trimesh
    except ImportError:
        print(
            "  WARNING: trimesh not installed — skipping GLB export. Run: pip install trimesh - requirement already satisfied says the pip output"
        )
        return

    try:
        mesh = trimesh.load(str(obj_path), process=False)
        if isinstance(mesh, trimesh.Scene):
            mesh = list(mesh.geometry.values())[0]

        from trimesh.visual.material import PBRMaterial, SimpleMaterial  # type: ignore[import]
        from trimesh.visual.texture import TextureVisuals  # type: ignore[import]

        texture_img = Image.open(atlas_path)
        try:
            material = PBRMaterial(baseColorTexture=texture_img)
        except TypeError:
            material = SimpleMaterial(image=texture_img)
        existing = getattr(mesh, "visual", None)
        uv_coords = getattr(existing, "uv", None)
        mesh.visual = TextureVisuals(uv=uv_coords, material=material)  # type: ignore[assignment]
        mesh.export(str(glb_path))
        print(
            f"  GLB:    {glb_path.name}  ({glb_path.stat().st_size / 1024 / 1024:.1f} MB)"
        )
    except Exception as e:
        print(f"  WARNING: GLB export failed: {e}")


# ----------------------------------------------------------------
# MAIN BAKE LOGIC
# ----------------------------------------------------------------


def bake_mesh(
    mesh_path: Path,
    prepared_path: Path | None,
    out_dir: Path,
    uv_tool: str,
    atlas_size: int,
    export_glb: bool,
) -> None:
    """Run the full UV unwrap + texture projection + export pipeline for one mesh."""
    stem = mesh_path.stem.replace("_mesh", "")

    print(f"\nBaking: {mesh_path.name}")

    # Load geometry mesh
    mesh_o3d = o3d.io.read_triangle_mesh(str(mesh_path))
    mesh_o3d.compute_vertex_normals()

    vertices = np.asarray(mesh_o3d.vertices, dtype=np.float32)
    faces = np.asarray(mesh_o3d.triangles, dtype=np.int32)

    if len(vertices) == 0 or len(faces) == 0:
        print(f"  ERROR: empty mesh — skipping")
        return

    print(f"  Mesh:   {len(vertices):,} vertices  {len(faces):,} triangles")

    # UV unwrap
    t_uv = time.time()
    print(f"  UV:     running {uv_tool}...")
    uv_fn = UV_TOOLS[uv_tool]
    uvs, vmapping, faces_uv = uv_fn(vertices, faces)
    print(f"  UV:     {len(uvs):,} UV verts  |  {time.time() - t_uv:.1f}s")

    # Load and composite source photo
    if prepared_path is not None and prepared_path.exists():
        rgba_arr = np.array(Image.open(prepared_path).convert("RGBA"))
        photo_rgb = composite_rgba_on_grey(rgba_arr, grey=128)
        print(
            f"  Photo:  {prepared_path.name}  ({photo_rgb.shape[1]}x{photo_rgb.shape[0]})"
        )
    else:
        print("  WARNING: no prepared image found — using flat grey texture")
        photo_rgb = np.full((512, 512, 3), 128, dtype=np.uint8)

    # Project photo to atlas
    t_proj = time.time()
    print(f"  Atlas:  projecting photo to {atlas_size}x{atlas_size} UV atlas...")
    atlas = project_photo_to_atlas(
        np.asarray(mesh_o3d.vertices, dtype=np.float32),
        uvs,
        vmapping,
        faces_uv,
        photo_rgb,
        atlas_size,
    )
    print(f"  Atlas:  done  |  {time.time() - t_proj:.1f}s")

    # Save atlas PNG
    atlas_path = out_dir / f"{stem}_atlas.png"
    Image.fromarray(atlas).save(str(atlas_path))
    print(f"  Saved:  {atlas_path.name}")

    # Save OBJ + MTL
    uv_verts_3d = np.asarray(mesh_o3d.vertices, dtype=np.float32)[vmapping]
    obj_path = out_dir / f"{stem}_textured.obj"
    save_obj_with_texture(
        np.asarray(mesh_o3d.vertices, dtype=np.float32),
        uvs,
        vmapping,
        faces_uv,
        atlas_path,
        obj_path,
    )
    print(f"  OBJ:    {obj_path.name}")

    # Save GLB
    if export_glb:
        glb_path = out_dir / f"{stem}_textured.glb"
        save_glb(obj_path, atlas_path, glb_path)


# ----------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------


def list_geometry_meshes(run: str) -> list[Path]:
    """Find all _mesh.obj or _mesh.ply files in output/meshes/{run}/geometry/."""
    mesh_base = get_output_dir("mesh", run)
    geo_dir = mesh_base / "geometry"
    if not geo_dir.exists():
        return []
    files = sorted(
        [
            p
            for p in geo_dir.iterdir()
            if p.suffix in (".obj", ".ply") and "_mesh" in p.name
        ],
        key=lambda p: p.name.lower(),
    )
    print(f"Found {len(files)} geometry mesh(es) in: {geo_dir}")
    return files


def find_prepared_for_mesh(mesh_path: Path, prepared_run: str) -> Path | None:
    """Locate the _prepared.png corresponding to a mesh file by stripping depth/mesh suffixes."""
    prepared_dir = get_output_dir("prepared", prepared_run)
    name = mesh_path.stem  # e.g. photo_prepared_depth_anything_v2_standard_depth_mesh
    # Strip known suffixes backwards
    for token in [
        "_mesh",
        "_depth_anything_v2",
        "_midas",
        "_depth_pro",
        "_marigold",
        "_standard",
        "_soft_edges_v1",
        "_soft_edges_feathered",
        "_depth",
    ]:
        if name.endswith(token):
            name = name[: -len(token)]
    candidate = prepared_dir / f"{name}.png"
    if candidate.exists():
        return candidate
    # Fallback: pick first _prepared.png in the run
    candidates = list(prepared_dir.glob("*_prepared.png"))
    return candidates[0] if candidates else None


# ----------------------------------------------------------------
# CLI
# ----------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 04b — UV unwrap + photo texture projection"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Process a single mesh file (name only, inside geometry/)",
    )
    parser.add_argument(
        "--uv-tool",
        type=str,
        default=DEFAULT_UV_TOOL,
        choices=list(UV_TOOLS.keys()),
        help=f"UV unwrap tool (default: {DEFAULT_UV_TOOL})",
    )
    parser.add_argument(
        "--atlas-size",
        type=int,
        default=DEFAULT_ATLAS_SIZE,
        help=f"Texture atlas resolution in pixels (default: {DEFAULT_ATLAS_SIZE})",
    )
    parser.add_argument("--no-glb", action="store_true", help="Skip GLB export")
    parser.add_argument(
        "--from-run",
        type=str,
        default=None,
        help="Read geometry meshes from this mesh run (default: latest)",
    )
    parser.add_argument(
        "--from-prepared-run",
        type=str,
        default=None,
        help="Read prepared images from this prepared run (default: latest)",
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        help="Write textured output to this mesh run (default: same as --from-run)",
    )
    return parser.parse_args()


# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------


def main() -> None:
    args = parse_args()

    mesh_run = latest_run_name("mesh", args.from_run)
    prepared_run = latest_run_name("prepared", args.from_prepared_run)
    # Default: write textured into the same mesh run
    output_mesh_run = args.run if args.run else mesh_run

    print("=" * 60)
    print("K9 Crystal Pipeline 03 Pro  —  Step 04b: Texture Bake")
    print(f"  Mesh run:     {mesh_run}  (geometry/ subfolder)")
    print(f"  Prepared run: {prepared_run}")
    print(f"  Output run:   {output_mesh_run}  (textured/ subfolder)")
    print(f"  UV tool:      {args.uv_tool}")
    print(f"  Atlas size:   {args.atlas_size}x{args.atlas_size}")
    print(f"  GLB export:   {'disabled' if args.no_glb else 'enabled'}")
    print("=" * 60)

    mesh_files = list_geometry_meshes(mesh_run)
    if not mesh_files:
        print(
            "ERROR: No geometry meshes found. Run step 03 first: python 03_mesh_generate.py"
        )
        sys.exit(1)

    if args.file:
        mesh_base = get_output_dir("mesh", mesh_run)
        targets = [mesh_base / "geometry" / args.file]
        if not targets[0].exists():
            print(f"ERROR: {args.file} not found in {mesh_base / 'geometry'}")
            sys.exit(1)
    else:
        targets = mesh_files

    # Textured output subfolder
    out_mesh_base = get_output_dir("mesh", output_mesh_run)
    textured_dir = out_mesh_base / "textured"
    textured_dir.mkdir(parents=True, exist_ok=True)

    total_start = time.time()
    success_count = 0

    for mesh_path in tqdm(targets, desc="Texture baking", unit="mesh"):
        prepared_path = find_prepared_for_mesh(mesh_path, prepared_run)
        try:
            bake_mesh(
                mesh_path,
                prepared_path,
                textured_dir,
                uv_tool=args.uv_tool,
                atlas_size=args.atlas_size,
                export_glb=not args.no_glb,
            )
            success_count += 1
        except Exception as e:
            print(f"\nERROR baking {mesh_path.name}: {e}")
            import traceback

            traceback.print_exc()

    total_elapsed = time.time() - total_start

    print()
    print("=" * 60)
    print("Step 04b complete.")
    print(f"  Baked:      {success_count} mesh(es)")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Output:     output/meshes/{output_mesh_run}/textured/")
    print()
    print("  QUALITY CHECK:")
    print("    - Open the OBJ in Blender, switch to Material Preview (Z key)")
    print("    - Face texture must be visible and correctly projected")
    print("    - No black fringing at hair boundaries")
    print("    - Skin tone gradients from photo must appear on the surface")
    print()
    print("Next step: python 05_export.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
