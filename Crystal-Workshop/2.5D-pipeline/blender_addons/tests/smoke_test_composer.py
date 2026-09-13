"""
File: blender_addons/tests/smoke_test_composer.py
Purpose:
 - Run a headless Blender smoke test against the local Composer source.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import bpy


ADDONS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDONS_DIR))

import acm_scene_composer  # noqa: E402


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def main() -> None:
    acm_scene_composer.register()
    reset_scene()

    bpy.ops.mesh.primitive_cube_add(size=2.0)
    source = bpy.context.active_object
    source.name = "SMOKE_SOURCE"

    settings = bpy.context.scene.acm_composer
    settings.project_name = "Composer smoke test"
    settings.input_type = "ACM_RELIEF_2_5D"
    settings.face_count = 1

    result = bpy.ops.acm.adopt_selected()
    assert result == {"FINISHED"}
    root = bpy.context.active_object
    assert root.get("acm_asset_root") is True
    assert root.get("acm_input_type") == "ACM_RELIEF_2_5D"
    assert root.get("acm_geometry_policy") == "PRESERVE_SOURCE_GEOMETRY"
    assert source.data is not None

    settings.face_refinement_state = "COMPLETE"
    assert bpy.ops.acm.update_face_qa() == {"FINISHED"}
    assert bpy.ops.acm.add_text() == {"FINISHED"}
    assert bpy.ops.acm.add_frame() == {"FINISHED"}
    assert bpy.ops.acm.validate_asset() == {"FINISHED"}
    assert "READY" in settings.last_report

    output = Path(tempfile.gettempdir()) / "acm-composer-smoke.glb"
    settings.export_path = str(output)
    assert bpy.ops.acm.export_asset() == {"FINISHED"}
    assert output.is_file() and output.stat().st_size > 0

    print(f"ACM_COMPOSER_SMOKE_OK {output} {output.stat().st_size}")
    acm_scene_composer.unregister()


if __name__ == "__main__":
    main()
