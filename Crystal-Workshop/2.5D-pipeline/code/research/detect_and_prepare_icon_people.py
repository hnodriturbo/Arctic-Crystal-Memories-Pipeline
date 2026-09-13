"""
File: code/research/detect_and_prepare_icon_people.py
Purpose:
 - Detect each person in a preprocessed source image for self-service ICON runs.
 - Preserve source pixels on deterministic transparent square canvases.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def expand_box(box: tuple[float, float, float, float], size: tuple[int, int], margin: int) -> tuple[int, int, int, int]:
    """Expand and clamp a floating-point detector box."""

    width, height = size
    x1, y1, x2, y2 = box
    return (
        max(0, int(x1) - margin),
        max(0, int(y1) - margin),
        min(width, int(x2 + 0.9999) + margin),
        min(height, int(y2 + 0.9999) + margin),
    )


def square_canvas(crop: Image.Image) -> Image.Image:
    """Place a crop at native resolution in the centre of a transparent square."""

    side = max(crop.width, crop.height)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(crop, ((side - crop.width) // 2, (side - crop.height) // 2))
    return canvas


def alpha_fallback_box(source: Image.Image) -> tuple[int, int, int, int]:
    """Use visible alpha bounds when the person detector finds no safe candidate."""

    alpha = source.getchannel("A")
    return alpha.getbbox() or (0, 0, source.width, source.height)


def detect_people(source: Image.Image, threshold: float, maximum: int, device_name: str) -> list[dict]:
    """Run the same torchvision Mask R-CNN family used by ICON."""

    import torch
    from torchvision.models import detection
    from torchvision.transforms.functional import to_tensor

    device = torch.device(device_name if device_name != "auto" else ("cuda:0" if torch.cuda.is_available() else "cpu"))
    composite = Image.new("RGB", source.size, (127, 127, 127))
    composite.paste(source.convert("RGB"), mask=source.getchannel("A"))
    scale = min(1.0, 1400.0 / max(source.size))
    detector_image = composite.resize(
        (round(source.width * scale), round(source.height * scale)), Image.Resampling.LANCZOS
    )
    model = detection.maskrcnn_resnet50_fpn(pretrained=True).to(device).eval()
    with torch.no_grad():
        prediction = model([to_tensor(detector_image).to(device)])[0]

    candidates = []
    for box, label, score in zip(prediction["boxes"], prediction["labels"], prediction["scores"]):
        confidence = float(score.detach().cpu())
        if int(label.detach().cpu()) != 1 or confidence < threshold:
            continue
        original_box = tuple(float(value) / scale for value in box.detach().cpu().tolist())
        candidates.append({"box": original_box, "score": confidence, "method": "maskrcnn"})
    candidates.sort(key=lambda item: item["box"][0])
    return candidates[:maximum]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=0.80)
    parser.add_argument("--maximum-subjects", type=int, default=4)
    parser.add_argument("--margin", type=int, default=64)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    source = Image.open(args.source).convert("RGBA")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    detections = detect_people(source, args.threshold, args.maximum_subjects, args.device)
    if not detections:
        detections = [{"box": alpha_fallback_box(source), "score": None, "method": "alpha-fallback"}]

    subjects = []
    for index, detection in enumerate(detections, start=1):
        name = f"person_{index:02d}"
        crop_box = expand_box(tuple(detection["box"]), source.size, args.margin)
        canvas = square_canvas(source.crop(crop_box))
        output_path = args.output_dir / f"{name}.png"
        canvas.save(output_path, optimize=True)
        subjects.append(
            {
                "name": name,
                "score": detection["score"],
                "method": detection["method"],
                "detector_box": [round(value, 3) for value in detection["box"]],
                "crop_box": list(crop_box),
                "canvas_size": list(canvas.size),
                "file": output_path.name,
            }
        )
        print(f"[people] {name}: {detection['method']} {crop_box} -> {canvas.size}")

    manifest = {
        "source": str(args.source.resolve()),
        "source_size": list(source.size),
        "threshold": args.threshold,
        "subjects": subjects,
    }
    (args.output_dir / "people.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[people] prepared {len(subjects)} subject(s)")


if __name__ == "__main__":
    main()

