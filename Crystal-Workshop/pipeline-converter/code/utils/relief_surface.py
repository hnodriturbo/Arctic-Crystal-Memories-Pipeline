"""
Purpose:
 - Estimate a continuous relief from layered laser points on a bounded XY grid.
 - Collapse depth layers, fill small sampling gaps, and avoid convex-hull bridges.
 - This estimates a surface; it cannot recover the original private CI mesh.
"""
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, median_filter, binary_closing, binary_fill_holes, convolve, grey_opening


def repair_lower_depth(grid, valid, fraction=0.42, strength=1.0):
    """Suppress narrow forward ridges only in the selected lower part of a relief.

    The upper rows are copied exactly. This conservative experimental opening
    removes local forward protrusions rather than flattening the entire model.
    """
    if not 0 < fraction <= 0.5:
        raise ValueError("Lower repair must stay within the bottom half.")
    if not 1 <= strength <= 3:
        raise ValueError("Lower repair strength must be between 1 and 3.")
    _, nearest = distance_transform_edt(~valid, return_indices=True)
    extended = grid[tuple(nearest)]
    size = max(5, int(max(grid.shape) * 0.045 * strength) | 1)
    underlying = grey_opening(extended, size=(size, size), mode="nearest")
    # Preserve the first millimetre of local relief; only taller narrow peaks
    # are pulled toward the surrounding surface. Feather below the boundary.
    correction = np.maximum(extended - underlying - 1.0 / strength, 0)
    correction = np.minimum(gaussian_filter(correction, 1.2 * strength), correction)
    y_fraction = np.linspace(0, 1, grid.shape[0])[:, None]
    blend = np.clip((fraction - y_fraction) / 0.06, 0, 1)
    result = grid.copy()
    selected = valid & (y_fraction < fraction)
    result[selected] = (grid - correction * blend)[selected]
    return result


def reconstruct_relief(points, resolution=512, smoothing=1.2, gap=2.0,
                       percentile=85.0, front="positive", max_vertices=300000, lower_repair=False,
                       lower_repair_strength=1.0):
    """Robust front envelope with a local support mask and shared grid triangles."""
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 3 or len(pts) < 3 or not np.isfinite(pts).all():
        raise ValueError("A relief needs at least three finite XYZ points.")
    if resolution < 16 or smoothing < 0 or gap < 0 or not 0 <= percentile <= 100:
        raise ValueError("Invalid relief grid settings.")
    lower = pts.min(axis=0)
    extent = np.ptp(pts, axis=0)
    if np.any(extent[:2] <= 0):
        raise ValueError("A relief requires nonzero XY width and height.")
    shape = np.maximum(2, np.rint(extent[:2] / extent[:2].max() * (resolution - 1)).astype(int) + 1)
    if np.prod(shape) > max_vertices:
        shape = np.maximum(2, np.floor(shape * np.sqrt(max_vertices / np.prod(shape))).astype(int))
    width, height = shape
    cell_xy = np.rint((pts[:, :2] - lower[:2]) / extent[:2] * (shape - 1)).astype(int)
    keys = cell_xy[:, 1] * width + cell_xy[:, 0]
    depths = pts[:, 2] * (-1 if front == "negative" else 1)

    # Sort within each projected cell. A high quantile ignores isolated extreme
    # points while selecting the front of the laser's stack rather than mixing layers.
    order = np.lexsort((depths, keys))
    ordered_keys = keys[order]
    unique, starts, counts = np.unique(ordered_keys, return_index=True, return_counts=True)
    offsets = np.rint((counts - 1) * percentile / 100).astype(int)
    grid = np.zeros((height, width), dtype=np.float64)
    grid.flat[unique] = depths[order[starts + offsets]]
    support = np.zeros_like(grid, dtype=bool)
    support.flat[unique] = True

    # Distance is in grid cells. Only nearby holes may become geometry: empty
    # background and spaces between subjects must not become huge triangles.
    _, nearest = distance_transform_edt(~support, return_indices=True)
    radius = int(np.ceil(gap))
    if radius:
        # Laser density follows brightness: dark clothing is missing data, not
        # a physical hole. Close small contour breaks, then fill enclosed holes.
        padded = np.pad(support, radius + 1)
        closed = binary_closing(padded, iterations=radius)
        valid = binary_fill_holes(closed)[radius + 1:-(radius + 1), radius + 1:-(radius + 1)] | support
    else:
        valid = support.copy()
    filled = grid[tuple(nearest)]
    missing = valid & ~support
    if missing.any():
        # Harmonic interpolation estimates only unmeasured interior depth.
        # Measured depth stays fixed during this pass, preserving facial anchors.
        kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float)
        weights = np.maximum(convolve(valid.astype(float), kernel, mode="nearest"), 1)
        for _ in range(200):
            average = convolve(np.where(valid, filled, 0), kernel, mode="nearest") / weights
            filled[missing] = average[missing]
    if smoothing:
        filtered = median_filter(filled, size=3, mode="nearest")
        weights = gaussian_filter(valid.astype(float), smoothing)
        grid = gaussian_filter(np.where(valid, filtered, 0), smoothing) / np.maximum(weights, 1e-12)
    else:
        grid = filled
    if lower_repair:
        grid = repair_lower_depth(grid, valid, strength=lower_repair_strength)
    grid *= -1 if front == "negative" else 1

    xx, yy = np.meshgrid(np.linspace(lower[0], lower[0] + extent[0], width),
                         np.linspace(lower[1], lower[1] + extent[1], height))
    vertices = np.column_stack((xx.ravel(), yy.ravel(), grid.ravel())).astype(np.float32)
    indices = np.arange(width * height).reshape(height, width)
    a, b, c, d = indices[:-1, :-1], indices[:-1, 1:], indices[1:, :-1], indices[1:, 1:]
    triangles = np.concatenate((np.stack((a, b, c), axis=-1).reshape(-1, 3),
                                np.stack((b, d, c), axis=-1).reshape(-1, 3)))
    triangles = triangles[valid.ravel()[triangles].all(axis=1)]
    if not len(triangles):
        raise ValueError("No connected surface. Lower the grid resolution or sampling interval.")
    used, inverse = np.unique(triangles, return_inverse=True)
    return vertices[used], inverse.reshape(-1, 3).astype(np.int32)
