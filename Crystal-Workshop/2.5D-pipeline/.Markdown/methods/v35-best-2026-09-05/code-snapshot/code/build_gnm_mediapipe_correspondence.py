"""
File: converter/2.5D-pipeline/code/build_gnm_mediapipe_correspondence.py
Purpose:
 - Reproducibly embed MediaPipe's official 468-point canonical face mesh onto
   the Apache-2.0 Google GNM Head v3 surface.
 - Preserve anatomical separation around eyelids and lips by limiting nearest
   surface searches to suitable GNM vertex groups.
 - Write three vertex-index/weight pairs per MediaPipe landmark for use by the
   automatic parametric-head fitting stage.

The input models are the official Google MediaPipe canonical face OBJ and the
official Google GNM Head v3 model. Both are Apache-2.0 licensed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


# MediaPipe indices corresponding to the conventional iBUG 68 ordering.
MEDIAPIPE_TO_IBUG_68 = (
    162, 234, 93, 58, 172, 136, 149, 148, 152, 377, 378, 365, 397, 288, 323, 454, 389,
    70, 63, 105, 66, 107, 336, 296, 334, 293, 300, 168, 197, 5, 4, 75, 97, 2, 326, 305,
    33, 160, 158, 133, 153, 144, 362, 385, 387, 263, 373, 380, 61, 39, 37, 0, 267,
    269, 291, 405, 314, 17, 84, 181, 78, 82, 13, 312, 308, 317, 14, 87,
)

UPPER_LIP = {0, 13, 37, 39, 40, 61, 78, 80, 81, 82, 185, 191, 267, 269, 270, 291, 308, 310, 311, 312, 409, 415}
LOWER_LIP = {14, 17, 61, 78, 84, 87, 88, 91, 95, 146, 178, 181, 291, 308, 314, 317, 318, 321, 324, 375, 402, 405}
LIP_CORNERS = {61, 78, 291, 308}
LID_UPPER = {157, 158, 159, 160, 161, 246, 384, 385, 386, 387, 388, 466}
LID_LOWER = {7, 144, 145, 153, 154, 163, 249, 373, 374, 380, 381, 390}
RIGHT_EYE = {7, 33, 133, 144, 145, 153, 154, 155, 157, 158, 159, 160, 161, 163, 173, 246}
LEFT_EYE = {249, 263, 362, 373, 374, 380, 381, 382, 384, 385, 386, 387, 388, 390, 398, 466}
RIGHT_BROW = {46, 52, 53, 55, 63, 65, 66, 70, 105, 107}
LEFT_BROW = {276, 282, 283, 285, 293, 295, 296, 300, 334, 336}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", required=True, type=Path)
    parser.add_argument("--gnm-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def similarity_fit(source: np.ndarray, target: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, float]:
    """Fit a similarity transform from source points to target points."""
    source_mean = source.mean(axis=0)
    target_mean = target.mean(axis=0)
    source_centered = source - source_mean
    target_centered = target - target_mean
    covariance = target_centered.T @ source_centered / len(source)
    left, singular_values, right_transposed = np.linalg.svd(covariance)
    reflection_guard = np.eye(3)
    if np.linalg.det(left) * np.linalg.det(right_transposed) < 0:
        reflection_guard[2, 2] = -1
    rotation = left @ reflection_guard @ right_transposed
    scale = np.trace(np.diag(singular_values) @ reflection_guard) / np.mean(
        np.sum(source_centered**2, axis=1)
    )
    translation = target_mean - scale * rotation @ source_mean
    transformed = scale * source @ rotation.T + translation
    rms = float(np.sqrt(np.mean(np.sum((transformed - target) ** 2, axis=1))))
    return scale, rotation, translation, rms


def closest_barycentric(point: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    """Return clamped barycentric coordinates of the closest triangle point."""
    a, b, c = triangle
    ab, ac, ap = b - a, c - a, point - a
    d1, d2 = ab @ ap, ac @ ap
    if d1 <= 0 and d2 <= 0:
        return np.array([1.0, 0.0, 0.0])
    bp = point - b
    d3, d4 = ab @ bp, ac @ bp
    if d3 >= 0 and d4 <= d3:
        return np.array([0.0, 1.0, 0.0])
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        value = d1 / (d1 - d3)
        return np.array([1.0 - value, value, 0.0])
    cp = point - c
    d5, d6 = ab @ cp, ac @ cp
    if d6 >= 0 and d5 <= d6:
        return np.array([0.0, 0.0, 1.0])
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        value = d2 / (d2 - d6)
        return np.array([1.0 - value, 0.0, value])
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        value = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return np.array([0.0, 1.0 - value, value])
    denominator = 1.0 / (va + vb + vc)
    value_b = vb * denominator
    value_c = vc * denominator
    return np.array([1.0 - value_b - value_c, value_b, value_c])


def mirror_ibug_indices(indices: tuple[int, ...]) -> tuple[int, ...]:
    order = list(range(68))
    order[0:17] = range(16, -1, -1)
    order[17:22], order[22:27] = range(26, 21, -1), range(21, 16, -1)
    order[31:36] = range(35, 30, -1)
    order[36:42] = (45, 44, 43, 42, 47, 46)
    order[42:48] = (39, 38, 37, 36, 41, 40)
    order[48:55] = (54, 53, 52, 51, 50, 49, 48)
    order[55:60] = (59, 58, 57, 56, 55)
    order[60:65] = (64, 63, 62, 61, 60)
    order[65:68] = (67, 66, 65)
    return tuple(indices[index] for index in order)


def main() -> int:
    args = parse_args()
    sys.path.insert(0, str(args.gnm_root.resolve()))
    from gnm.shape import gnm_landmarks, gnm_numpy

    model = gnm_numpy.GNM.from_local(
        version=gnm_numpy.GNMMajorVersion.V3,
        variant=gnm_numpy.GNMVariant.HEAD,
    )
    neutral = np.asarray(model())
    canonical = np.asarray(
        [
            [float(value) for value in line.split()[1:4]]
            for line in args.canonical.read_text(encoding="utf-8").splitlines()
            if line.startswith("v ")
        ],
        dtype=np.float64,
    )
    if canonical.shape != (468, 3):
        raise ValueError(f"Expected 468 canonical vertices, got {canonical.shape}.")

    sparse = gnm_landmarks.load_landmarks(gnm_landmarks.GNMLandmarksType.HEAD_SPARSE_68)
    gnm_68 = (neutral[sparse.indices] * sparse.weights[..., None]).sum(axis=1)
    candidates = {
        "normal": similarity_fit(canonical[list(MEDIAPIPE_TO_IBUG_68)], gnm_68),
        "mirrored": similarity_fit(canonical[list(mirror_ibug_indices(MEDIAPIPE_TO_IBUG_68))], gnm_68),
    }
    orientation = min(candidates, key=lambda name: candidates[name][3])
    scale, rotation, translation, _ = candidates[orientation]
    canonical_aligned = scale * canonical @ rotation.T + translation

    def group(name: str) -> set[int]:
        if name not in model.vertex_group_names:
            return set()
        return set(np.asarray(model.vertex_group_indices(name)).tolist())

    skin = group("skin_exterior") or group("skin")
    generic = skin - (group("eyes") | group("teeth") | group("gums") | group("tongue") | group("mouth_sock"))
    upper_lip = group("upper_lip") | group("upper_lip_region")
    lower_lip = group("lower_lip") | group("lower_lip_region")
    orbital_left, orbital_right = group("left_orbital_region"), group("right_orbital_region")
    brow_left, brow_right = group("left_brow_region"), group("right_brow_region")

    socket = np.asarray(sorted(group("eye_sockets")), dtype=np.int64)
    lid_upper: set[int] = set()
    lid_lower: set[int] = set()
    for side in (socket[neutral[socket, 0] >= 0], socket[neutral[socket, 0] < 0]):
        if side.size:
            middle_y = neutral[side, 1].mean()
            lid_upper |= set(side[neutral[side, 1] >= middle_y].tolist())
            lid_lower |= set(side[neutral[side, 1] < middle_y].tolist())

    regions = {
        "corners": upper_lip | lower_lip,
        "upper_lip": upper_lip,
        "lower_lip": lower_lip,
        "lid_upper": lid_upper or generic,
        "lid_lower": lid_lower or generic,
        "left_eye": orbital_left or generic,
        "right_eye": orbital_right or generic,
        "left_brow": brow_left | orbital_left,
        "right_brow": brow_right | orbital_right,
        "generic": generic,
    }

    def region_name(index: int) -> str:
        if index in LIP_CORNERS:
            return "corners"
        if index in LID_UPPER:
            return "lid_upper"
        if index in LID_LOWER:
            return "lid_lower"
        if index in UPPER_LIP:
            return "upper_lip"
        if index in LOWER_LIP:
            return "lower_lip"
        if index in LEFT_EYE:
            return "left_eye"
        if index in RIGHT_EYE:
            return "right_eye"
        if index in LEFT_BROW:
            return "left_brow"
        if index in RIGHT_BROW:
            return "right_brow"
        return "generic"

    triangles = np.asarray(model.triangles_group("~eye_exteriors"), dtype=np.int64)
    cache: dict[str, tuple[np.ndarray, cKDTree]] = {}
    rows: list[tuple[np.ndarray, np.ndarray]] = []
    distances: list[float] = []
    for index, point in enumerate(canonical_aligned):
        region = region_name(index)
        if region not in cache:
            eligible = triangles[np.isin(triangles, list(regions[region])).any(axis=1)]
            cache[region] = eligible, cKDTree(neutral[eligible].mean(axis=1))
        eligible, tree = cache[region]
        _distance, candidate_indices = tree.query(point, k=min(24, len(eligible)))
        best_distance = float("inf")
        best_row: tuple[np.ndarray, np.ndarray] | None = None
        for candidate_index in np.atleast_1d(candidate_indices):
            triangle_indices = eligible[candidate_index]
            weights = closest_barycentric(point, neutral[triangle_indices])
            projected = (neutral[triangle_indices] * weights[:, None]).sum(axis=0)
            distance = float(np.linalg.norm(point - projected))
            if distance < best_distance:
                best_distance = distance
                best_row = triangle_indices, weights
        if best_row is None:
            raise RuntimeError(f"No GNM surface candidate for landmark {index}.")
        rows.append(best_row)
        distances.append(best_distance)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        for triangle_indices, weights in rows:
            output.write(
                f"{triangle_indices[0]} {weights[0]:.6f} "
                f"{triangle_indices[1]} {weights[1]:.6f} "
                f"{triangle_indices[2]} {weights[2]:.6f}\n"
            )

    embedded = np.asarray(
        [(neutral[indices] * weights[:, None]).sum(axis=0) for indices, weights in rows]
    )
    aperture_right = float(np.linalg.norm(embedded[159] - embedded[145]) * 1000.0)
    aperture_left = float(np.linalg.norm(embedded[386] - embedded[374]) * 1000.0)
    errors_mm = np.asarray(distances) * 1000.0
    if min(aperture_right, aperture_left) <= 3.0:
        raise RuntimeError("Generated correspondence collapsed an eyelid aperture.")
    print(
        f"GNM_MEDIAPIPE_OK orientation={orientation} "
        f"rms68={candidates[orientation][3] * 1000.0:.2f}mm "
        f"mean={errors_mm.mean():.2f}mm p95={np.percentile(errors_mm, 95):.2f}mm "
        f"eyelids={aperture_right:.2f}/{aperture_left:.2f}mm"
    )
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
