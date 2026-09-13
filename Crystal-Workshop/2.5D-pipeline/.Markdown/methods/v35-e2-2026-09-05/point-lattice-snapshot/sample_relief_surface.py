"""
Purpose:
 - Add deterministic rows of points to stretched triangles using 3D surface distances.
 - Interpolate positions and UVs on existing triangles; never create new body geometry.
"""

import numpy as np


def quantize_point_lattice(points, point_spacing, layer_spacing):
    """Return one point per exact XYZ lattice cell, plus source indices for colours."""
    step = np.array([point_spacing, point_spacing, layer_spacing], dtype=float)
    if not np.isfinite(step).all() or (step <= 0).any():
        raise ValueError('Point and layer spacing must be positive and finite')
    cells = np.rint(points/step).astype(np.int64)
    _, retained = np.unique(cells, axis=0, return_index=True)
    retained.sort()
    quantized = cells[retained]*step
    error = np.max(abs(quantized-points[retained]), axis=0)
    assert (error <= step*.5+1e-12).all()
    return quantized, retained, {'point_spacing_xy_mm': point_spacing*1000,
                                'layer_spacing_mm': layer_spacing*1000,
                                'unique_lattice_points': len(quantized),
                                'max_axis_quantization_mm': (error*1000).tolist()}


def sample_surface(vertices, faces, uv, spacing, max_points=3000000):
    if not np.isfinite(spacing) or spacing <= 0:
        raise ValueError('Surface spacing must be positive and finite')
    triangles = vertices[faces]
    lengths = np.stack([np.linalg.norm(triangles[:, (i+1)%3] - triangles[:, i], axis=1) for i in range(3)], axis=1)
    chosen = np.flatnonzero(lengths.max(axis=1) > spacing)
    positions, coordinates = [vertices], [uv]
    total = len(vertices)

    def append(points, texcoords):
        nonlocal total
        total += len(points)
        if total > max_points:
            raise ValueError(f'Sampling exceeds {max_points} points; increase surface spacing')
        positions.append(points)
        coordinates.append(texcoords)

    # Shared triangle edges are sampled once, retaining every original vertex exactly.
    edges = np.unique(np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1), axis=0)
    edge_lengths = np.linalg.norm(vertices[edges[:, 1]] - vertices[edges[:, 0]], axis=1)
    for edge_index in np.flatnonzero(edge_lengths > spacing):
        a, b = edges[edge_index]
        segments = int(np.ceil(edge_lengths[edge_index] / spacing))
        t = (np.arange(1, segments) / segments)[:, None]
        append(vertices[a]*(1-t)+vertices[b]*t, uv[a]*(1-t)+uv[b]*t)

    # Rows span the longest edge; spacing across and along rows is measured in 3D.
    # This avoids quadratic oversampling of very long, narrow stretch triangles.
    for face_index in chosen:
        longest = int(np.argmax(lengths[face_index]))
        order = [longest, (longest+1)%3, (longest+2)%3]
        ids = faces[face_index, order]
        a, b, c = vertices[ids]
        ta, tb, tc = uv[ids]
        width = np.linalg.norm(b-a)
        height = np.linalg.norm(np.cross(b-a, c-a)) / max(width, 1e-15)
        rows = max(1, int(np.ceil(height / spacing)))
        for row in range(rows):
            t = (row+.5)/rows
            columns = max(1, int(np.ceil(width*(1-t)/spacing)))
            u = ((np.arange(columns)+.5)/columns)[:, None]
            append((a*(1-u)+b*u)*(1-t)+c*t, (ta*(1-u)+tb*u)*(1-t)+tc*t)
    result = np.concatenate(positions)
    result_uv = np.concatenate(coordinates)
    assert np.array_equal(result[:len(vertices)], vertices)
    return result, result_uv, {'spacing_mm': float(spacing*1000), 'original_points': len(vertices),
                              'points': len(result), 'added_points': len(result)-len(vertices),
                              'stretched_triangles_sampled': len(chosen),
                              'original_max_edge_mm': float(edge_lengths.max()*1000),
                              'sampling': 'original vertices + shared edge subdivisions + interior barycentric rows'}
