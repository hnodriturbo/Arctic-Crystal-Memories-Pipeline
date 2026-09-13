"""
Purpose:
 - Derive face-edit support from however many valid, available landmarks a face has.
 - Honour supplied visibility and foreground masks without treating inferred points as observed.
"""

import cv2
import numpy as np
from scipy.ndimage import map_coordinates


def face_support(face, alpha, grid_shape):
    raw = face.get('landmarks_3d', face.get('dense_landmarks', face.get('dense_landmarks_468', [])))
    points = np.asarray(raw, dtype=float)
    if points.ndim != 2 or points.shape[1] < 3:
        raise ValueError('At least six supported XYZ face landmarks are required')
    h, w = alpha.shape
    valid = np.isfinite(points[:, :3]).all(axis=1)
    valid &= (points[:, 0] >= 0) & (points[:, 0] <= w-1) & (points[:, 1] >= 0) & (points[:, 1] <= h-1)
    safe = np.nan_to_num(points[:, :2])
    valid &= map_coordinates(alpha.astype(float), [safe[:, 1], safe[:, 0]], order=0, mode='constant', cval=0) >= 128
    visibility = face.get('landmark_visibility')
    if visibility is not None:
        visibility = np.asarray(visibility, float)
        if visibility.shape != (len(points),):
            raise ValueError('Visibility scores must match the supplied landmark count')
        valid &= np.isfinite(visibility) & (visibility >= .5)
    confidence = face.get('landmark_confidence')
    if confidence is not None:
        confidence = np.asarray(confidence, float)
        if confidence.shape != (len(points),):
            raise ValueError('Confidence scores must match the supplied landmark count')
        valid &= np.isfinite(confidence) & (confidence >= .5)
    selected = points[valid, :3]
    if len(selected) < 6 or np.linalg.matrix_rank(selected[:, :2]-selected[:, :2].mean(axis=0)) < 2:
        raise ValueError('Insufficient non-collinear face support; leave the baseline face unchanged')
    rows, cols = grid_shape
    projected = selected[:, :2] * [(cols-1)/(w-1), (rows-1)/(h-1)]
    mask = np.zeros(grid_shape, np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(np.rint(projected).astype(np.int32)), 1)
    width_grid = float(np.ptp(projected[:, 0]))
    # Scale blend widths with the face itself, not the image or a previous person's crop.
    boundary = float(np.clip(width_grid*.11, 3., 18.))
    smooth = float(np.clip(width_grid*.055, 1.2, 9.))
    feature_points = np.asarray(face.get('landmarks', []), float)
    pose_asymmetry = None
    if feature_points.shape == (5, 2):
        eye_axis = feature_points[1]-feature_points[0]
        eye_span = np.linalg.norm(eye_axis)
        if eye_span > 1:
            pose_asymmetry = float(abs(np.dot(feature_points[2]-(feature_points[0]+feature_points[1])/2, eye_axis)/(eye_span**2)))
    report = {'supplied_landmarks': len(points), 'usable_landmarks': len(selected),
              'visibility_source': 'explicit_per_point' if visibility is not None else 'not_available_inferred_landmarks_only',
              'hidden_landmarks_are_not_verified_observations': True,
              'boundary_width_grid_px': boundary, 'broad_smoothing_grid_px': smooth,
              'eye_nose_asymmetry_heuristic': pose_asymmetry,
              'needs_occlusion_review': visibility is None,
              'policy': 'No edit beyond available landmark hull; optional visibility mask can remove holes/occluders.'}
    return selected, mask.astype(bool), report
