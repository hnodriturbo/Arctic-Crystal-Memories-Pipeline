"""
File: converter/2.5D-pipeline/code/render_people_reliefs.py
Purpose:
 - Render the current one-person and two-person deep-relief GLBs together.
 - Produce reproducible front-oblique and profile QA images that expose both
   crystal appearance detail and actual physical head/face depth.

Run with Blender, not ordinary Python:
 blender --background --python code/render_people_reliefs.py -- \
   --single amma-single/relief-deep.glb --pair amma-afi-pair/relief-deep.glb \
   --output people.png --angle 28 --appearance crystal
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
    parser.add_argument("--single", required=True, type=Path)
    parser.add_argument("--pair", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--angle", type=float, default=28.0)
    parser.add_argument("--appearance", choices=("crystal", "clay"), default="crystal")
    parser.add_argument("--resolution-x", type=int, default=2100)
    parser.add_argument("--resolution-y", type=int, default=950)
    return parser.parse_args(values)


def main() -> None:
    args = arguments()
    clear_scene()
    import_variant(args.single.resolve(), -53.0, "ONE PERSON · 24 mm", args.angle, args.appearance)
    import_variant(args.pair.resolve(), 53.0, "TWO PEOPLE · 24 mm", args.angle, args.appearance)

    camera_data = bpy.data.cameras.new("ACM_PEOPLE_CAMERA")
    camera = bpy.data.objects.new("ACM_PEOPLE_CAMERA", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (0.0, -285.0, 2.0)
    camera_data.lens = 54.0
    point_camera(camera, Vector((0.0, 0.0, 0.0)))
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("KEY", (-110.0, -180.0, 115.0), 1300.0, 115.0),
        ("FILL", (130.0, -145.0, -45.0), 720.0, 95.0),
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
