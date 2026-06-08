"""
File: code/utils/parsers.py
Purpose:
 - Parse coordinate-like rows from Cockpit3D CAD files and transform point lists.
"""

import math
import re


NUMERIC_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def is_numeric_token(value):
    """Return True when a token can be safely treated as a number."""
    return bool(NUMERIC_PATTERN.match(value.strip()))


def is_numeric_row(parts):
    """Return True when all tokens in a split row are numeric."""
    return bool(parts) and all(is_numeric_token(part) for part in parts)


def classify_numeric_row(parts):
    """Classify numeric rows to help inspection reports describe likely structure."""
    if not is_numeric_row(parts):
        return "non_numeric"

    if len(parts) == 3:
        return "xyz_only"

    if len(parts) == 5:
        return "prefix_plus_xyz"

    if len(parts) >= 6:
        return "possible_rgb_or_extra_fields"

    return "numeric_but_not_xyz"


def extract_xyz_from_numeric_parts(parts):
    """Extract XYZ coordinates from supported numeric row shapes."""
    if len(parts) == 3:
        xyz_parts = parts[0:3]
    elif len(parts) >= 5:
        xyz_parts = parts[2:5]
    else:
        return None

    try:
        point = tuple(float(value) for value in xyz_parts)
    except ValueError:
        return None

    if any(not math.isfinite(value) for value in point):
        return None

    return point


def parse_cad_points(file_path, limit=None, sample_rate=1, scale=1.0):
    """Extract XYZ points from text-readable Cockpit3D CAD rows."""
    points = []
    total_lines = 0
    skipped_lines = 0
    candidate_rows = 0
    exported_candidates = 0
    row_shape_counts = {
        "xyz_only": 0,
        "prefix_plus_xyz": 0,
        "possible_rgb_or_extra_fields": 0,
        "numeric_but_not_xyz": 0,
    }

    with open(file_path, "r", encoding="utf-8", errors="replace") as source_file:
        for line in source_file:
            total_lines += 1
            parts = line.strip().split()

            if not is_numeric_row(parts):
                skipped_lines += 1
                continue

            row_shape = classify_numeric_row(parts)
            if row_shape in row_shape_counts:
                row_shape_counts[row_shape] += 1

            point = extract_xyz_from_numeric_parts(parts)
            if point is None:
                skipped_lines += 1
                continue

            candidate_rows += 1

            if sample_rate > 1 and candidate_rows % sample_rate != 0:
                continue

            exported_candidates += 1
            scaled_point = tuple(coordinate * scale for coordinate in point)
            points.append(scaled_point)

            if limit is not None and len(points) >= limit:
                break

    stats = {
        "total_lines": total_lines,
        "skipped_lines": skipped_lines,
        "candidate_rows": candidate_rows,
        "exported_candidates": exported_candidates,
        "row_shape_counts": row_shape_counts,
    }

    return points, stats


def dedupe_points(points):
    """Remove duplicate XYZ rows while preserving original point order."""
    seen_points = set()
    unique_points = []

    for point in points:
        if point in seen_points:
            continue
        seen_points.add(point)
        unique_points.append(point)

    return unique_points


def center_points(points):
    """Center a point cloud around the middle of its bounding box."""
    if not points:
        return points

    bounds = calculate_bounds(points)
    center_x = (bounds["min_x"] + bounds["max_x"]) / 2
    center_y = (bounds["min_y"] + bounds["max_y"]) / 2
    center_z = (bounds["min_z"] + bounds["max_z"]) / 2

    return [
        (x_coord - center_x, y_coord - center_y, z_coord - center_z)
        for x_coord, y_coord, z_coord in points
    ]


def calculate_bounds(points):
    """Calculate coordinate bounds for reports and conversion summaries."""
    if not points:
        return None

    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    z_values = [point[2] for point in points]

    return {
        "min_x": min(x_values),
        "max_x": max(x_values),
        "min_y": min(y_values),
        "max_y": max(y_values),
        "min_z": min(z_values),
        "max_z": max(z_values),
    }
