"""
File: tests/test_build_glb_from_cockpit.py
Purpose:
 - Verify the neutral Cockpit CI-to-GLB interoperability helpers without
   requiring Cockpit 3D or an OpenGL context during the unit test run.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


SCRIPT_PATH = Path(__file__).parents[1] / "code" / "research" / "build_glb_from_cockpit.py"
SPEC = importlib.util.spec_from_file_location("build_glb_from_cockpit", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize("name", ["../mesh.ci", "/absolute/mesh.ci", "folder/../mesh.ci", "folder/"])
def test_safe_member_name_rejects_unsafe_archive_paths(name: str) -> None:
    with pytest.raises(ValueError, match="Unsafe archive member"):
        MODULE.safe_member_name(name)


def test_safe_member_name_flattens_a_safe_nested_member() -> None:
    assert MODULE.safe_member_name("assets/mesh.ci") == "mesh.ci"


def test_load_decoded_mesh_splits_cockpit_vertex_layout(tmp_path: Path) -> None:
    vertex_records = np.asarray(
        [
            [0, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 0, 1, 0, 0, 0, 1],
            [0, 1, 0, 0, 1, 0, 0, 1],
        ],
        dtype="<f4",
    )
    indices = np.asarray([0, 1, 2], dtype="<i4")
    raw_path = tmp_path / "decoded.bin"
    with raw_path.open("wb") as stream:
        stream.write(vertex_records.tobytes())
        stream.write(indices.tobytes())

    positions, uv, normals, faces = MODULE.load_decoded_mesh(
        raw_path,
        {"vertexCount": 3, "floatsPerVertex": 8, "indexCount": 3},
    )

    np.testing.assert_array_equal(positions, vertex_records[:, 0:3])
    np.testing.assert_array_equal(uv, vertex_records[:, 3:5])
    np.testing.assert_array_equal(normals, vertex_records[:, 5:8])
    np.testing.assert_array_equal(faces, [[0, 1, 2]])


def test_load_decoded_mesh_rejects_out_of_range_indices(tmp_path: Path) -> None:
    raw_path = tmp_path / "decoded.bin"
    raw_path.write_bytes(np.zeros((3, 8), dtype="<f4").tobytes() + np.asarray([0, 1, 3], dtype="<i4").tobytes())

    with pytest.raises(ValueError, match="outside the vertex buffer"):
        MODULE.load_decoded_mesh(
            raw_path,
            {"vertexCount": 3, "floatsPerVertex": 8, "indexCount": 3},
        )


def test_scene_transform_centres_and_scales_geometry() -> None:
    solid = MODULE.ElementTree.fromstring(
        '<SolidEntity ScaleX="2" ScaleY="3" ScaleZ="4" '
        'PositionX="10" PositionY="20" PositionZ="30" />'
    )
    positions = np.asarray([[-1.0, -1.0, -1.0], [1.0, 1.0, 1.0]])
    normals = np.asarray([[0.0, 0.0, 1.0], [0.0, 0.0, 1.0]])

    transformed, transformed_normals, report = MODULE.transform_to_scene_mm(positions, normals, solid)

    np.testing.assert_allclose(transformed, [[8, 17, 26], [12, 23, 34]])
    np.testing.assert_allclose(transformed_normals, normals)
    assert report["sceneBoundsMm"]["size"] == [4.0, 6.0, 8.0]

