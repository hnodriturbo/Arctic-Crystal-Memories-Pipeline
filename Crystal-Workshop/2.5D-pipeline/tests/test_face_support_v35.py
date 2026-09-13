"""
Purpose: Verify partial and hidden landmark handling before a final face edit is allowed.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'code/research'))
from face_support_v35 import face_support


def test_partial_face_does_not_require_468_points():
    points = [[20,20,0],[30,20,0],[40,20,0],[20,40,0],[30,40,1],[40,40,0],[80,30,0]]
    face = {'landmarks_3d': points, 'landmark_visibility': [1,1,1,1,1,1,0]}
    selected, mask, report = face_support(face, np.full((100,100),255), (100,100))
    assert len(selected) == 6
    assert not mask[:, 41:].any()
    assert report['visibility_source'] == 'explicit_per_point'


def test_bad_coordinates_and_masked_points_are_excluded():
    points = [[20,20,0],[30,20,0],[40,20,0],[20,40,0],[30,40,1],[40,40,0],[200,20,0],[10,10,float('nan')],[60,60,0]]
    alpha = np.full((100,100),255)
    alpha[60,60] = 0
    selected, _, report = face_support({'landmarks_3d': points}, alpha, (100,100))
    assert len(selected) == 6
    assert report['needs_occlusion_review']


def test_insufficient_support_never_invents_full_face():
    with pytest.raises(ValueError):
        face_support({'landmarks_3d': [[20,20,0],[30,30,1]]}, np.full((100,100),255), (100,100))
