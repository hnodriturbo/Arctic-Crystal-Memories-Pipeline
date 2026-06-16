# =============================================================
# 04_export.py — Final export and Cockpit3D prep
# =============================================================
# PURPOSE:
#   Fourth and final step. Takes the finished (and optionally
#   manually edited) mesh and prepares it for SSLE production.
#   Validates dimensions, scales to crystal size, and exports
#   in formats compatible with Cockpit3D and other SSLE software.
#
# WHAT THIS STEP DOES NOT DO:
#   It does NOT generate the laser point cloud — that is done
#   inside Cockpit3D. This step only prepares and validates
#   the mesh geometry before handing off to Cockpit3D.
#
# KEY OPERATIONS:
#   1. Validate mesh (check for holes, inverted normals, crashes)
#   2. Scale mesh to match physical crystal dimensions (mm)
#   3. Center mesh within crystal bounding box
#   4. Final smoothing pass if requested
#   5. Export as OBJ (primary) for Cockpit3D import
#   6. Generate a simple render preview (top-down view) as PNG
#
# CRYSTAL SIZE PRESETS (common K9 crystal blank sizes in mm):
#   small_cube     : 60 x 60 x 40
#   medium_cube    : 80 x 80 x 50
#   large_cube     : 100 x 100 x 60
#   rectangle_s    : 80 x 60 x 40
#   rectangle_m    : 100 x 80 x 50
#   keychain       : 40 x 30 x 20
#
# INPUTS:
#   - Edited OBJ mesh from OUTPUT_DIR/meshes/
#   - Crystal size preset or custom dimensions
#
# OUTPUTS:
#   - Final OBJ: OUTPUT_DIR/exports/{stem}_final.obj
#   - Validation report: OUTPUT_DIR/exports/{stem}_report.txt
#   - Preview PNG: OUTPUT_DIR/exports/{stem}_preview.png
#
# USAGE:
#   python 04_export.py
#   python 04_export.py --file photo_mesh.obj
#   python 04_export.py --crystal medium_cube
#   python 04_export.py --crystal-size 100 80 50   # custom WxHxD in mm
#
# DEPENDENCIES: open3d, numpy, Pillow, python-dotenv
#
# NOTES:
#   - After this step, import the final OBJ into Cockpit3D.
#   - Cockpit3D will generate the actual point cloud for the laser.
#   - Always check the validation report before importing.
#   - If mesh has holes, go back to Blender/Meshmixer and fix them.
# =============================================================

# TODO (Claude Code): Implement this script with the following structure:
#
# 1. IMPORTS AND CONFIG
#    - Load .env
#    - Parse CLI args: --file, --crystal, --crystal-size
#    - Define CRYSTAL_PRESETS dict with size tuples (W, H, D) in mm
#
# 2. VALIDATE MESH — validate_mesh(mesh: o3d.TriangleMesh) -> dict
#    - Check: is_watertight, is_orientable, is_self_intersecting
#    - Get stats: vertex count, triangle count, bounding box
#    - Return validation report dict
#    - Print pass/fail for each check
#
# 3. SCALE TO CRYSTAL — scale_to_crystal(mesh, crystal_dims: tuple) -> o3d.TriangleMesh
#    - Get current mesh bounding box
#    - Calculate scale factor to fit within crystal dims with 10% margin
#    - Apply uniform scale
#    - Center mesh at origin
#    - Translate so bottom of subject sits at Z=0 (flat base)
#    - Return scaled mesh
#
# 4. SAVE EXPORT — save_export(mesh, stem: str, report: dict)
#    - Save final OBJ to exports/ folder
#    - Write report as plain text file (human readable)
#    - Generate and save top-down preview using Open3D offscreen renderer
#
# 5. MAIN
#    - Process single file or all meshes
#    - Print clear summary: ready for Cockpit3D / needs fixing
#
# COMMENTING STANDARD: same as 01_upscale.py
