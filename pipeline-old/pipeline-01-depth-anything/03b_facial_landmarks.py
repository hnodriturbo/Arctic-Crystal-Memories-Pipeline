# =============================================================
# 03b_facial_landmarks.py — Facial landmark detection (proof-of-concept)
# =============================================================
# PURPOSE:
#   Optional step, runs alongside step 03. Detects 478 3D facial
#   landmarks (MediaPipe Face Mesh) on the background-removed image.
#   These landmarks are anchor points for a future correction pass —
#   snapping the raw depth-map mesh to known facial geometry (nose
#   bridge, eye sockets, jawline) instead of relying on depth-model
#   guesswork alone, which is where portrait accuracy currently breaks.
#
# WHY THIS EXISTS:
#   Depth models (step 03) estimate depth per-pixel with no concept
#   of "this is a nose" or "this is an eye socket" — proportions drift
#   on faces specifically. Landmarks give step 04 (or a future 04b)
#   real reference points to deform the mesh against.
#
# STATUS: proof-of-concept.
#   Not wired into 04_mesh_generate.py yet — this step only detects
#   and saves landmarks. Using them to deform the mesh is a separate,
#   future change. See root README.md section 5 — do not treat this
#   as reviving local mesh generation as the main workflow; it's a
#   correction aid for the vendor (Cockpit3D) handoff path.
#
# INPUTS:
#   - Background-removed PNGs from output/bg_removed/{run}/
#
# OUTPUTS:
#   - JSON: output/landmarks/{run}/{stem}_landmarks.json
#     (478 points, each with pixel-space x, y and MediaPipe's
#     relative z — z is NOT metric depth, see get_landmarks() docstring)
#   - Preview PNG: output/landmarks/{run}/{stem}_landmarks_preview.png
#     (landmarks drawn over the source image for visual sanity check)
#
# USAGE:
#   python 03b_facial_landmarks.py
#   python 03b_facial_landmarks.py --file image_01_upscaled_nobg.png
#   python 03b_facial_landmarks.py --from-run try_03 --run try_01
#
# DEPENDENCIES: mediapipe, opencv-python, numpy, Pillow, python-dotenv, tqdm
#
# NOTES:
#   - No CUDA required — MediaPipe Face Mesh runs on CPU.
#   - Detects one face per image (static_image_mode). Group photos
#     with multiple people are not handled — flagged as failed instead
#     of silently picking one face.
#   - z values are relative to the face's own scale, not comparable
#     across images or to the step 03 depth map without calibration.
# =============================================================

from pathlib import Path
import argparse
import json
import sys
import time

import numpy as np

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))

from dotenv import load_dotenv
load_dotenv(PIPELINE_DIR / ".env")


# =============================================================
# DEPENDENCY CHECKS
# =============================================================

try:
    import cv2
except ImportError:
    print("ERROR: opencv-python is not installed. Run: pip install opencv-python")
    sys.exit(1)

try:
    import mediapipe as mp
except ImportError:
    print("ERROR: mediapipe is not installed. Run: pip install mediapipe")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: Pillow is not installed. Run: pip install Pillow")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: tqdm is not installed. Run: pip install tqdm")
    sys.exit(1)

from utils.file_utils import (
    build_output_path,
    get_output_dir,
    latest_run_name,
    resolve_run_name,
)


# =============================================================
# LANDMARK DETECTION
# =============================================================

def get_landmarks(image_path: Path) -> np.ndarray:
    """
    Run MediaPipe Face Mesh on one image and return landmark coordinates.

    x, y are pixel coordinates in the source image. z is MediaPipe's
    relative depth (roughly same scale as x, smaller = closer to camera)
    — it is NOT metric depth and is not on the same scale as the step 03
    depth map. Treat z as a rough ordering signal, not an absolute value,
    until it's been calibrated against the depth map in a future step.

    Args:
        image_path: Path to an RGB(A) image containing exactly one face

    Returns:
        float32 array, shape (478, 3) — columns are (x_px, y_px, z_rel)

    Raises:
        ValueError: No face detected, or more than one face detected
    """
    # static_image_mode=True re-runs full detection per call instead of
    # tracking between frames — correct mode for one-off portrait stills.
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=2,  # request 2 so we can tell "one face" from "group photo" apart
        refine_landmarks=True,
        min_detection_confidence=0.5,
    ) as face_mesh:
        # cv2 needed only for its RGB read here — mediapipe expects RGB, not BGR
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"Could not read image: {image_path}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]

        result = face_mesh.process(rgb)

    if not result.multi_face_landmarks:
        raise ValueError(f"No face detected in {image_path.name}")
    if len(result.multi_face_landmarks) > 1:
        raise ValueError(
            f"{len(result.multi_face_landmarks)} faces detected in {image_path.name} — "
            "this step expects single-portrait input. Crop to one face first."
        )

    face = result.multi_face_landmarks[0]
    # MediaPipe returns normalized [0,1] coords — scale x,y to pixel space
    # so landmarks line up directly with the source image and depth map.
    points = np.array(
        [(lm.x * w, lm.y * h, lm.z * w) for lm in face.landmark],
        dtype=np.float32,
    )
    return points


# =============================================================
# PREVIEW / SAVE
# =============================================================

def draw_landmarks_preview(image_path: Path, landmarks: np.ndarray) -> Image.Image:
    """
    Draw landmark points over the source image for a visual sanity check.

    Args:
        image_path: Path to the source image
        landmarks:  (478, 3) array from get_landmarks()

    Returns:
        RGB PIL Image with landmarks overlaid
    """
    base = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(base)
    r = max(1, base.width // 400)  # dot size scales with image resolution
    for x, y, _ in landmarks:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(0, 255, 0))
    return base


def save_landmark_outputs(
    landmarks: np.ndarray,
    image_path: Path,
    run: str,
) -> tuple[Path, Path]:
    """
    Save landmarks as JSON and a preview PNG into output/landmarks/{run}/.

    Args:
        landmarks:  (478, 3) array from get_landmarks()
        image_path: Source image path — used for the preview background and filename
        run:        Run subfolder name, e.g. 'try_01'

    Returns:
        Tuple of (json_path, preview_path)
    """
    stem = image_path.stem

    json_path = build_output_path(f"{stem}.json", "landmarks", "json", run=run)
    payload = {
        "source": image_path.name,
        "landmark_count": int(landmarks.shape[0]),
        "landmarks": landmarks.tolist(),  # [[x_px, y_px, z_rel], ...]
    }
    json_path.write_text(json.dumps(payload, indent=2))
    tqdm.write(f"  JSON:    {json_path.name}")

    preview = draw_landmarks_preview(image_path, landmarks)
    preview_path = build_output_path(f"{stem}_preview.png", "landmarks", "png", run=run)
    preview.save(str(preview_path), format="PNG")
    tqdm.write(f"  Preview: {preview_path.name}")

    return json_path, preview_path


# =============================================================
# INPUT SCANNER — bg_removed folder
# =============================================================

def list_nobg_images(run: str) -> list[Path]:
    """Return all _nobg.png files from output/bg_removed/{run}/, sorted alphabetically."""
    nobg_dir = get_output_dir("nobg", run)
    images = sorted(
        [p for p in nobg_dir.iterdir() if p.is_file() and p.name.endswith("_nobg.png")],
        key=lambda p: p.name.lower(),
    )
    print(f"Found {len(images)} background-removed image(s) in: {nobg_dir}")
    return images


# =============================================================
# CLI ARGUMENT PARSING
# =============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 03b — Detect facial landmarks (proof-of-concept, MediaPipe Face Mesh).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python 03b_facial_landmarks.py\n"
            "  python 03b_facial_landmarks.py --file image_01_upscaled_nobg.png\n"
            "  python 03b_facial_landmarks.py --from-run try_03 --run try_01\n"
        ),
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        metavar="FILENAME",
        help="Process a single file from the bg_removed run folder. Provide just the filename.",
    )
    parser.add_argument(
        "--from-run",
        type=str,
        default=None,
        metavar="NAME",
        help="Which bg_removed run to read from. Defaults to latest non-empty run.",
    )
    parser.add_argument(
        "--run",
        type=str,
        default=None,
        metavar="NAME",
        help="Output run subfolder name. Auto-increments to next available if omitted.",
    )
    return parser.parse_args()


# =============================================================
# MAIN ENTRY POINT
# =============================================================

def main() -> None:
    args = parse_args()

    print("=" * 60)
    print("K9 Crystal Pipeline  —  Step 03b: Facial Landmarks (proof-of-concept)")
    print("=" * 60)

    input_run = latest_run_name("nobg", args.from_run)
    tag = Path(args.file).stem if args.file else None
    output_run = resolve_run_name("landmarks", args.run, tag=tag)
    print(f"  Input:   output/bg_removed/{input_run}/")
    print(f"  Output:  output/landmarks/{output_run}/\n")

    if args.file:
        single_path = get_output_dir("nobg", input_run) / args.file
        if not single_path.exists():
            print(f"ERROR: File not found: {single_path}")
            sys.exit(1)
        images_to_process = [single_path]
    else:
        images_to_process = list_nobg_images(input_run)
        if not images_to_process:
            print("ERROR: No _nobg.png files found in bg_removed output.")
            print("       Run step 02 first:  python 02_remove_bg.py")
            sys.exit(1)

    print(f"Processing {len(images_to_process)} image(s).\n")

    total_start = time.perf_counter()
    success_count = 0
    failed: list[str] = []

    progress_bar = tqdm(images_to_process, desc="Landmark detection", unit="img", leave=True, dynamic_ncols=True)

    for image_path in progress_bar:
        progress_bar.set_description(f"Processing: {image_path.name}")
        try:
            t_start = time.perf_counter()
            landmarks = get_landmarks(image_path)
            elapsed = time.perf_counter() - t_start

            tqdm.write(f"  Input:   {image_path.name}")
            tqdm.write(f"  Points:  {landmarks.shape[0]}  |  {elapsed:.2f}s")

            save_landmark_outputs(landmarks, image_path, output_run)
            success_count += 1

        except Exception as exc:
            tqdm.write(f"\nERROR — '{image_path.name}': {exc}")
            tqdm.write("  Skipping this file and continuing.\n")
            failed.append(image_path.name)

    total_elapsed = time.perf_counter() - total_start

    print()
    print("=" * 60)
    print("Step 03b complete.")
    print(f"  Processed: {success_count} image(s)")
    if failed:
        print(f"  Failed:    {len(failed)} image(s)")
        for name in failed:
            print(f"    - {name}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Output:    output/landmarks/{output_run}/")
    print()
    print(
        "  Check the _landmarks_preview.png before using this data —\n"
        "  green dots should sit exactly on eyes/nose/jaw contours."
    )
    print()
    print("Next: use landmarks + depth map together in a future mesh-correction step.")
    print("=" * 60)


if __name__ == "__main__":
    main()
