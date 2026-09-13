"""
File: converter/2.5D-pipeline/code/crystal_mask.py
Purpose:
 - Convert print-empty black padding connected to selected image borders into
   an explicit geometry/point-cloud mask.
 - Preserve equally dark clothing, hair, furniture and shadows when they are
   enclosed inside the photographed subject rather than connected to a chosen
   empty border.
 - Produce QA previews before the mask is used to omit relief triangles.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


VALID_EDGES = ("top", "bottom", "left", "right")


def border_connected_dark(
    tone: np.ndarray,
    threshold: int,
    edges: tuple[str, ...] = ("top",),
) -> np.ndarray:
    """Return dark pixels connected to any selected image border."""
    if tone.ndim != 2:
        raise ValueError("tone must be a single-channel image")
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")
    invalid = sorted(set(edges) - set(VALID_EDGES))
    if invalid:
        raise ValueError(f"unsupported edges: {', '.join(invalid)}")

    dark = (tone <= threshold).astype(np.uint8)
    component_count, labels = cv2.connectedComponents(dark, connectivity=8)
    selected_labels: set[int] = set()
    if "top" in edges:
        selected_labels.update(int(value) for value in np.unique(labels[0, :]))
    if "bottom" in edges:
        selected_labels.update(int(value) for value in np.unique(labels[-1, :]))
    if "left" in edges:
        selected_labels.update(int(value) for value in np.unique(labels[:, 0]))
    if "right" in edges:
        selected_labels.update(int(value) for value in np.unique(labels[:, -1]))
    selected_labels.discard(0)
    if component_count <= 1 or not selected_labels:
        return np.zeros_like(dark, dtype=bool)
    return np.isin(labels, np.fromiter(selected_labels, dtype=np.int32))


def build_crystal_mask(
    tone: np.ndarray,
    source_alpha: np.ndarray,
    threshold: int,
    edges: tuple[str, ...] = ("top",),
    feather_px: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return an 8-bit keep mask and the removed border-connected region."""
    removed = border_connected_dark(tone, threshold, edges)
    keep = (~removed).astype(np.float32)
    keep *= np.clip(source_alpha.astype(np.float32) / 255.0, 0.0, 1.0)
    if feather_px > 0:
        inside_distance = cv2.distanceTransform((keep > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
        keep *= np.clip(inside_distance / feather_px, 0.0, 1.0)
    return np.rint(np.clip(keep, 0.0, 1.0) * 255.0).astype(np.uint8), removed


def save_qa(
    tone: np.ndarray,
    mask: np.ndarray,
    removed: np.ndarray,
    output: Path,
) -> None:
    """Save tone, mask and a red removed-region overlay in one panel."""
    base = np.repeat(tone[:, :, None], 3, axis=2)
    overlay = base.copy()
    overlay[removed] = np.array([255, 45, 45], dtype=np.uint8)
    mask_rgb = np.repeat(mask[:, :, None], 3, axis=2)
    panel = np.concatenate([base, mask_rgb, overlay], axis=1)
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(panel, mode="RGB").save(output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mask print-empty dark padding connected to selected image borders."
    )
    parser.add_argument("--input", required=True, type=Path, help="Crystal-tone or embedded texture image.")
    parser.add_argument("--output", required=True, type=Path, help="8-bit white-is-geometry mask PNG.")
    parser.add_argument("--qa-output", type=Path, help="Optional tone/mask/removed comparison PNG.")
    parser.add_argument("--black-threshold", type=int, default=12)
    parser.add_argument(
        "--edge",
        action="append",
        choices=VALID_EDGES,
        help="Border that seeds empty black removal. Repeat for more edges; default is top only.",
    )
    parser.add_argument("--feather-px", type=float, default=0.0)
    args = parser.parse_args()

    with Image.open(args.input) as source:
        source.load()
        rgba = np.asarray(source.convert("RGBA"), dtype=np.uint8)
    tone = np.asarray(Image.fromarray(rgba, mode="RGBA").convert("L"), dtype=np.uint8)
    edges = tuple(args.edge or ("top",))
    mask, removed = build_crystal_mask(
        tone,
        rgba[:, :, 3],
        threshold=args.black_threshold,
        edges=edges,
        feather_px=max(0.0, args.feather_px),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask, mode="L").save(args.output)
    qa_output = args.qa_output or args.output.with_name(f"{args.output.stem}-qa.png")
    save_qa(tone, mask, removed, qa_output)

    payload = {
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "convention": "8-bit white = geometry/points; black = transparent/omitted",
        "black_threshold": args.black_threshold,
        "seed_edges": list(edges),
        "feather_px": max(0.0, args.feather_px),
        "removed_fraction": float(np.mean(removed)),
        "kept_fraction": float(np.mean(mask >= 128)),
        "rule": "remove only threshold-dark connected components touching selected borders",
    }
    args.output.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"CRYSTAL_MASK_OK removed={payload['removed_fraction'] * 100:.2f}% "
        f"kept={payload['kept_fraction'] * 100:.2f}%"
    )
    print(args.output)
    print(qa_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
