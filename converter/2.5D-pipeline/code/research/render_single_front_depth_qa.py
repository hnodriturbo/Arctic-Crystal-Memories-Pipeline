"""
File: code/research/render_single_front_depth_qa.py
Purpose:
 - Render consistent neutral front, angled, and both profile QA views for one source-facing 2.5D surface.
 - Compare depth-integration variants without texture or viewer-material bias.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--label", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def look_at(item, target) -> None:
    item.rotation_euler = (Vector(target) - item.location).to_track_quat("-Z", "Y").to_euler()


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
    args = arguments()
    mesh_path = args.mesh.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(mesh_path), forward_axis="NEGATIVE_Z", up_axis="Y")
    surface = next(item for item in bpy.context.selected_objects if item.type == "MESH")
    surface.name = args.label
    for polygon in surface.data.polygons:
        polygon.use_smooth = True

    material = bpy.data.materials.new("Neutral_2_5D_Depth_QA")
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.34, 0.37, 0.42, 1.0)
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = 0.72
    surface.data.materials.clear()
    surface.data.materials.append(material)

    world = bpy.data.worlds.new("Single_2_5D_QA_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.003, 0.004, 0.006, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.06

    scene = bpy.context.scene
    scene.world = world
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1400
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"

    bounds = [Vector(corner) for corner in surface.bound_box]
    center = sum(bounds, Vector()) / 8.0
    height = max(corner.z for corner in bounds) - min(corner.z for corner in bounds)
    target = tuple(center)
    distance = max(4.5, height * 2.8)
    add_area_light("Key", (2.7, -4.2, 2.8), 560.0, 3.2, target)
    add_area_light("Fill", (-3.2, -2.5, 0.7), 170.0, 3.6, target)
    add_area_light("Rim", (0.7, 2.5, 3.0), 310.0, 2.8, target)

    camera_data = bpy.data.cameras.new("Single_2_5D_QA_Camera")
    camera = bpy.data.objects.new("Single_2_5D_QA_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(2.15, height * 1.14)

    render(scene, camera, (center.x, -distance, center.z), target, output_dir / f"{args.label}_front.png")
    render(
        scene,
        camera,
        (center.x + distance * 0.57, -distance, center.z),
        target,
        output_dir / f"{args.label}_30deg.png",
    )
    render(
        scene,
        camera,
        (center.x + distance, -0.05, center.z),
        target,
        output_dir / f"{args.label}_left-profile.png",
    )
    render(
        scene,
        camera,
        (center.x - distance, -0.05, center.z),
        target,
        output_dir / f"{args.label}_right-profile.png",
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / f"{args.label}_qa.blend"))


if __name__ == "__main__":
    main()
