# main.py
# 🧊 Crystal 2.5D pipeline entrypoint
# - Loads image and (optionally) removes background
# - Runs Marigold depth estimation (+ optional DECA face refinement)
# - Builds a clean 2.5D mesh using zmax only (no crystal box constraints)
# - Exports STL / OBJ / XYZ / DXF for engraving or preview

import argparse  # 🧩 CLI argument parsing
import os  # 📁 Filesystem helpers

from pipeline.depth.marigold_depth import MarigoldDepth  # 🌊 Depth model
from pipeline.mesh.mesh_generator import MeshGenerator  # 🧱 2.5D mesh builder
from pipeline.export.exporter import Exporter  # 📤 File exporters
from pipeline.utils.image import load_image, remove_background  # 🖼️ Image helpers

# 🙂 Optional face refinement (RetinaFace + DECA)
try:
    from pipeline.face.retina_deca_refiner import FaceRefiner  # 😎 Face depth booster

    FACE_REFINER_AVAILABLE = True  # ✅ Face refinement ready
except ImportError:
    FACE_REFINER_AVAILABLE = False  # ⚠️ Fallback to plain depth only
    print("[warning] Face refiner (DECA) not available - skipping face refinement")


def main():
    # 🎛️ CLI configuration
    parser = argparse.ArgumentParser(
        description="Generate crystal-ready 2.5D mesh from a 2D image"
    )
    parser.add_argument(
        "--image", required=True, help="Path to input image"
    )  # 🖼️ Input photo
    parser.add_argument(
        "--outdir", required=True, help="Output directory"
    )  # 📁 Output folder

    parser.add_argument(
        "--zmax",
        type=float,
        default=40.0,
        help="Max depth relief in mm (0 → zmax) (default: 40)",
    )  # 📏 Maximum depth range in mm

    parser.add_argument(
        "--target-points",
        type=int,
        default=750000,
        help="Target number of XYZ points (default: 750000)",
    )  # 🧮 Grid resolution via point count

    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="Inference device (cuda or cpu, default: cuda)",
    )  # 💻 Where Marigold runs

    parser.add_argument(
        "--keep-bg",
        action="store_true",
        help="Keep original background (skip AI background removal)",
    )  # 🌄 Optional background

    parser.add_argument(
        "--depth-gain",
        type=float,
        default=1.5,
        help="Depth contrast multiplier for foreground vs background (default: 1.5)",
    )  # 🎛️ Extra pop for faces

    parser.add_argument(
        "--width-mm",
        type=float,
        default=100.0,
        help="Physical width of the mesh in mm (default: 100mm)",
    )  # 📏 X-span in mm (for engraving scale)

    parser.add_argument(
        "--height-mm",
        type=float,
        default=None,
        help="Physical height of the mesh in mm (default: auto from aspect)",
    )  # 📏 Y-span in mm (auto if None)

    parser.add_argument(
        "--invert-depth",
        action="store_true",
        help="Force invert depth (use if subject looks carved in instead of out)",
    )  # 🔄 Manual front/back flip

    parser.add_argument(
        "--no-auto-orient-depth",
        action="store_true",
        help="Disable auto orientation (center vs border depth check)",
    )  # 🧪 Optional auto orientation

    parser.add_argument(
        "--edge-falloff",
        type=float,
        default=0.3,
        help="Edge falloff strength [0–1]; 0 = no fade, 0.3 = gentle fade to zero depth near borders",
    )  # 🌊 Fade depth near image edges to avoid stretched walls

    args = parser.parse_args()  # 📥 Parse CLI args

    # 📁 Ensure output directory exists
    os.makedirs(args.outdir, exist_ok=True)

    print("[load] Image")
    image = load_image(args.image)  # 🖼️ Load input image (BGR)

    # 🧮 Aspect ratio + physical dimensions
    h, w = image.shape[:2]
    aspect = w / h  # 📐 width / height

    if args.height_mm is None:
        # 🧱 Auto height from width and aspect (keeps proportions in mm)
        height_mm = args.width_mm / aspect
    else:
        height_mm = args.height_mm

    width_mm = args.width_mm

    print(
        f"[dimensions] Mesh physical size: {width_mm:.1f}×{height_mm:.1f} mm (W×H), aspect={aspect:.2f}"
    )

    # ✂️ Background removal
    if not args.keep_bg:
        print("[bg] Removing background (AI rembg if available)")
        print("[bg] TIP: Use --keep-bg to preserve logos/text or full scene depth")
        image = remove_background(image, keep_bg=False)
    else:
        print("[bg] Keeping full background (--keep-bg specified)")

    # 🌊 Depth estimation (Marigold)
    print("[depth] Marigold estimation")
    depth_model = MarigoldDepth(device=args.device)  # 🚀 Load depth model
    depth_map = depth_model.predict(image, invert=False)  # 🔢 Normalized [0,1] depth

    # 🙂 Face refinement (optional)
    if FACE_REFINER_AVAILABLE:
        try:
            print("[face] Detect & refine with RetinaFace + DECA")
            face_refiner = FaceRefiner(device=args.device)  # 😎 Face depth enhancer
            refined_depth = face_refiner.refine(image, depth_map)  # 🎯 Sharper faces
        except (ImportError, ModuleNotFoundError) as e:
            print(f"[face] Skipping face refinement (DECA issue: {e})")
            refined_depth = depth_map
    else:
        print("[face] Skipping face refinement (DECA not installed)")
        refined_depth = depth_map

    # 🔄 Manual depth inversion (if user wants explicit control)
    if args.invert_depth:
        refined_depth = 1.0 - refined_depth  # 🔁 Flip near/far
        print("[depth] Manual inversion applied (--invert-depth)")

    # 🧭 Automatic orientation: ensure center is nearer than borders
    if not args.no_auto_orient_depth:
        import numpy as np  # 🧮 Local import to keep startup fast

        h_d, w_d = refined_depth.shape
        cy1, cy2 = int(h_d * 0.3), int(h_d * 0.7)  # 🎯 Center crop bounds (Y)
        cx1, cx2 = int(w_d * 0.3), int(w_d * 0.7)  # 🎯 Center crop bounds (X)

        center_region = refined_depth[cy1:cy2, cx1:cx2]  # 🎯 Main subject area

        border_top = refined_depth[:cy1, :]  # 🧱 Top border
        border_bottom = refined_depth[cy2:, :]  # 🧱 Bottom border
        border_left = refined_depth[cy1:cy2, :cx1]  # 🧱 Left border
        border_right = refined_depth[cy1:cy2, cx2:]  # 🧱 Right border

        border_region = np.concatenate(
            [
                border_top.reshape(-1),
                border_bottom.reshape(-1),
                border_left.reshape(-1),
                border_right.reshape(-1),
            ]
        )  # 🧱 All borders flattened

        center_mean = float(center_region.mean())
        border_mean = (
            float(border_region.mean()) if border_region.size > 0 else center_mean
        )

        if center_mean > border_mean:
            # 🧭 If center looks farther than background → flip
            refined_depth = 1.0 - refined_depth
            print(
                f"[depth] Auto-orient: center_mean={center_mean:.3f} > border_mean={border_mean:.3f} → depth inverted"
            )
        else:
            print(
                f"[depth] Auto-orient: center_mean={center_mean:.3f} <= border_mean={border_mean:.3f} → keep orientation"
            )
    else:
        print("[depth] Auto orientation disabled (--no-auto-orient-depth)")

    # 🧱 Build 2.5D mesh with simple zmax mapping (0 → zmax)
    print("[mesh] Generate 2.5D surface")
    mesh_generator = MeshGenerator(
        zmax_mm=args.zmax,
        depth_gain=args.depth_gain,
        width_mm=width_mm,
        height_mm=height_mm,
        edge_falloff_strength=args.edge_falloff,
    )  # 🧱 Use edge falloff so borders fade instead of forming deep walls

    mesh, point_cloud = mesh_generator.build(
        image_bgr=image,
        depth_map=refined_depth,
        target_points=args.target_points,
    )  # 🧮 Build mesh and XYZ points

    # 📤 Export everything
    print("[export] Writing outputs")
    exporter = Exporter()  # 📦 Export helper
    exporter.write_all(
        mesh, point_cloud, args.outdir, write_obj=True
    )  # 💾 STL/OBJ/XYZ/DXF

    print("[done] All exports complete")


if __name__ == "__main__":
    main()  # ▶️ Run CLI
