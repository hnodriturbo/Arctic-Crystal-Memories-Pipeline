"""
File: converter/2.5D-pipeline/code/render_head_prior_comparison.py
Purpose:
 - Render the same 2.5D relief before and after Google GNM Head refinement.
 - Use a strong oblique/profile angle so missing skull, cheek, nose, chin, and
   neck depth cannot be hidden by the front-facing texture.

Run with Blender, not ordinary Python:
 blender --background --python code/render_head_prior_comparison.py -- \
   --before relief-deep.glb --after relief-gnm.glb --output compare.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_relief_variants import clear_scene, import_variant, point_camera  # noqa: E402


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--before-label", default="BEFORE · FLAT DEPTH")
    parser.add_argument("--after-label", default="GNM 468 · HEAD PRIOR")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--angle", type=float, default=68.0)
    parser.add_argument("--appearance", choices=("crystal", "clay"), default="clay")
    parser.add_argument("--resolution-x", type=int, default=2100)
    parser.add_argument("--resolution-y", type=int, default=1000)
    return parser.parse_args(values)


def main() -> None:
    args = arguments()
    clear_scene()
    import_variant(args.before.resolve(), -53.0, args.before_label, args.angle, args.appearance)
    import_variant(args.after.resolve(), 53.0, args.after_label, args.angle, args.appearance)

    camera_data = bpy.data.cameras.new("ACM_HEAD_COMPARE_CAMERA")
    camera = bpy.data.objects.new("ACM_HEAD_COMPARE_CAMERA", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (0.0, -295.0, 2.0)
    camera_data.lens = 55.0
    point_camera(camera, Vector((0.0, 0.0, 0.0)))
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("KEY", (-125.0, -190.0, 120.0), 1500.0, 120.0),
        ("FILL", (135.0, -150.0, -45.0), 780.0, 95.0),
    ):
        light_data = bpy.data.lights.new(f"ACM_{name}", type="AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"ACM_{name}", light_data)
        bpy.context.scene.collection.objects.link(light)
        light.location = location
        point_camera(light, Vector((0.0, 0.0, 0.0)))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = args.resolution_x
    scene.render.resolution_y = args.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.003, 0.006, 0.012)
    scene.render.filepath = str(args.output.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(f"RENDER_OK {args.output.resolve()}")


if __name__ == "__main__":
    main()
