"""
File: converter/2.5D-pipeline/code/render_single_relief_qa.py
Purpose:
 - Render one relief as neutral clay from front, oblique, and side views.
 - Expose real head, face, edge, and micro-detail geometry without allowing
   the source photograph or point-cloud brightness to hide flat surfaces.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--resolution", type=int, default=1400)
    return parser.parse_args(values)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def scene_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    low = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    high = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    return low, high


def apply_clay(objects: list[bpy.types.Object]) -> None:
    material = bpy.data.materials.new("ACM_DETAIL100_QA_CLAY")
    material.diffuse_color = (0.58, 0.64, 0.72, 1.0)
    for obj in objects:
        obj.data.materials.clear()
        obj.data.materials.append(material)


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    location: tuple[float, float, float],
    ortho_scale: float,
    output: Path,
) -> None:
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    look_at(camera, Vector((0.0, 0.0, 0.0)))
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()), import_pack_images=True)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{args.input} imported no mesh")

    low, high = scene_bounds(meshes)
    center = (low + high) * 0.5
    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            obj.location -= center
    apply_clay(meshes)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.8
    scene.display.shading.curvature_valley_factor = 1.35
    scene.display.shading.show_specular_highlight = True
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.012, 0.016, 0.025)

    camera_data = bpy.data.cameras.new("ACM_RELIEF_QA_CAMERA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("ACM_RELIEF_QA_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    # glTF imports source Y-up as Blender Z-up and source relief Z as Blender Y.
    # These three cameras therefore reveal the image plane, 3D depth, and exact
    # relief profile independently.
    render_view(scene, camera, (0.0, -220.0, 0.0), 90.0, args.output_dir / "detail100-front.png")
    render_view(scene, camera, (135.0, -190.0, 24.0), 94.0, args.output_dir / "detail100-oblique.png")
    render_view(scene, camera, (220.0, -8.0, 0.0), 90.0, args.output_dir / "detail100-profile.png")
    render_view(scene, camera, (92.0, -175.0, 18.0), 62.0, args.output_dir / "detail100-face-closeup.png")
    print(f"ACM_SINGLE_RELIEF_QA_OK {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
