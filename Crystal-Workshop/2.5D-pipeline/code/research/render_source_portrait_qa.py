"""
File: code/research/render_source_portrait_qa.py
Purpose:
 - Render auto-fitted neutral QA views of a standard Y-up portrait relief GLB.
 - Expose front, oblique, and profile geometry without appearance bias.
 - Optionally preserve the source texture to verify UV and mask appearance.
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
    parser.add_argument("--label", default="portrait")
    parser.add_argument("--appearance", choices=("clay", "source"), default="clay")
    return parser.parse_args(values)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(scene, camera, location, output: Path) -> None:
    camera.location = location
    look_at(camera, Vector((0.0, 0.0, 0.0)))
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(input_path), import_pack_images=True)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    high = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    center = (low + high) * 0.5
    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            obj.location -= center

    if args.appearance == "clay":
        material = bpy.data.materials.new("SOURCE_PORTRAIT_QA_CLAY")
        material.diffuse_color = (0.58, 0.64, 0.72, 1.0)
        for obj in meshes:
            obj.data.materials.clear()
            obj.data.materials.append(material)

    width = float(high.x - low.x)
    depth = float(high.y - low.y)
    height = float(high.z - low.z)
    distance = max(width, height, depth) * 2.4

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE" if args.appearance == "source" else "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.8
    scene.display.shading.curvature_valley_factor = 1.35
    scene.display.shading.show_specular_highlight = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.008, 0.011, 0.018)

    camera_data = bpy.data.cameras.new("SOURCE_PORTRAIT_QA_CAMERA")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = height * 1.08
    camera = bpy.data.objects.new("SOURCE_PORTRAIT_QA_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    render(scene, camera, (0.0, -distance, 0.0), output_dir / f"{args.label}_front.png")
    render(
        scene,
        camera,
        (distance * 0.57, -distance, 0.0),
        output_dir / f"{args.label}_30deg.png",
    )
    render(
        scene,
        camera,
        (distance, -0.02, 0.0),
        output_dir / f"{args.label}_profile.png",
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / f"{args.label}_qa.blend"))
    print(f"SOURCE_PORTRAIT_QA_OK {output_dir}")


if __name__ == "__main__":
    main()
