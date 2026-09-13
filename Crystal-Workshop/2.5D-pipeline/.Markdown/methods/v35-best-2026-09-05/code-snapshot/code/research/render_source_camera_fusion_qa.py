"""
File: code/research/render_source_camera_fusion_qa.py
Purpose:
 - Render neutral-material source-camera and angled QA for registered 2.5D people.
 - Preserve source aspect ratio and expose local-depth/seam behavior without texture camouflage.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def look_at(item, target) -> None:
    direction = Vector(target) - item.location
    item.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def import_surface(path: Path, name: str):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="NEGATIVE_Z", up_axis="Y")
    imported = [item for item in set(bpy.data.objects) - before if item.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError(f"Expected one mesh in {path}, found {len(imported)}")
    surface = imported[0]
    surface.name = name
    for polygon in surface.data.polygons:
        polygon.use_smooth = True
    return surface


def add_area_light(name, location, energy, size, target) -> None:
    light_data = bpy.data.lights.new(name=name, type="AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name=name, object_data=light_data)
    bpy.context.collection.objects.link(light)
    light.location = location
    look_at(light, target)


def render(scene, camera, location, target, output_path) -> None:
    camera.location = location
    look_at(camera, target)
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_arguments()
    stats_path = args.stats.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    source_width, source_height = stats["source_size"]
    geometry_dir = stats_path.parent

    bpy.ops.wm.read_factory_settings(use_empty=True)
    surfaces = []
    for subject, subject_stats in stats["subjects"].items():
        surfaces.append(
            import_surface(geometry_dir / subject_stats["output_obj"], f"SourceCamera_{subject}")
        )

    material = bpy.data.materials.new("Neutral_Source_Camera_QA")
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.34, 0.38, 0.44, 1.0)
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = 0.68
    for surface in surfaces:
        surface.data.materials.clear()
        surface.data.materials.append(material)

    world = bpy.data.worlds.new("Source_Camera_QA_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.006, 0.010, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.08

    scene = bpy.context.scene
    scene.world = world
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_y = 1177
    scene.render.resolution_x = round(scene.render.resolution_y * source_width / source_height)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"

    bounds = stats["combined"]["bounds"]
    depth_center = (bounds[0][2] + bounds[1][2]) * 0.5
    target = (0.0, depth_center, 0.0)
    add_area_light("Key", (2.7, -4.2, 2.9), 560.0, 3.2, target)
    add_area_light("Fill", (-3.2, -2.6, 0.9), 170.0, 3.8, target)
    add_area_light("Rim", (0.4, 2.6, 3.0), 320.0, 2.8, target)

    camera_data = bpy.data.cameras.new("Source_Camera_QA_Camera")
    camera = bpy.data.objects.new("Source_Camera_QA_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.04

    render(scene, camera, (0.0, -5.0, 0.0), target, output_dir / "both_source_camera_front.png")
    render(scene, camera, (2.65, -4.60, 0.0), target, output_dir / "both_source_camera_30deg.png")
    render(scene, camera, (3.75, -3.75, 0.0), target, output_dir / "both_source_camera_45deg.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "source_camera_fusion_qa.blend"))


if __name__ == "__main__":
    main()
