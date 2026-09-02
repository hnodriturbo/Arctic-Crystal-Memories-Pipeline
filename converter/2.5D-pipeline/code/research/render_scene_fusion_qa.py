"""
File: code/research/render_scene_fusion_qa.py
Purpose:
 - Render source-camera and angled neutral QA for human plus MoGe scene-layer fusion.
 - Use separate materials so layer ownership and gaps remain visible during review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fusion-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def look_at(item, target) -> None:
    item.rotation_euler = (Vector(target) - item.location).to_track_quat("-Z", "Y").to_euler()


def material(name, color, roughness):
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color, 1.0)
    result.use_nodes = True
    principled = result.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    return result


def import_obj(path: Path, name: str, surface_material):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="NEGATIVE_Z", up_axis="Y")
    objects = [item for item in set(bpy.data.objects) - before if item.type == "MESH"]
    if len(objects) != 1:
        raise RuntimeError(f"Expected one mesh in {path}, found {len(objects)}")
    result = objects[0]
    result.name = name
    result.data.materials.clear()
    result.data.materials.append(surface_material)
    for polygon in result.data.polygons:
        polygon.use_smooth = True
    return result


def add_light(name, location, energy, size, target) -> None:
    data = bpy.data.lights.new(name=name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(name=name, object_data=data)
    bpy.context.collection.objects.link(light)
    light.location = location
    look_at(light, target)


def render(scene, camera, location, target, path) -> None:
    camera.location = location
    look_at(camera, target)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = arguments()
    fusion_dir = args.fusion_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_stats_path = fusion_dir / "scene_fusion_stats.json"
    skirt_stats_path = fusion_dir / "silhouette_depth_skirt_stats.json"
    stats = json.loads(
        (scene_stats_path if scene_stats_path.exists() else skirt_stats_path).read_text(encoding="utf-8")
    )

    bpy.ops.wm.read_factory_settings(use_empty=True)
    human_material = material("Accepted_Human_Geometry", (0.56, 0.62, 0.70), 0.68)
    scene_material = material("MoGe_Scene_Depth", (0.17, 0.25, 0.34), 0.82)
    skirt_material = material("Silhouette_Depth_Skirt", (0.30, 0.40, 0.50), 0.76)
    import_obj(fusion_dir / "scene_depth_layer.obj", "MoGe_Rest_Of_Image", scene_material)
    import_obj(fusion_dir / "man_source_camera_scene_anchored.obj", "PARE_Man", human_material)
    import_obj(fusion_dir / "woman_source_camera_scene_anchored.obj", "PARE_Woman", human_material)
    for skirt_path in sorted(fusion_dir.glob("*_silhouette_depth_skirt.obj")):
        import_obj(skirt_path, skirt_path.stem, skirt_material)

    world = bpy.data.worlds.new("Scene_Fusion_QA_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.003, 0.005, 0.009, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.07
    scene = bpy.context.scene
    scene.world = world
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_y = 1177
    scene.render.resolution_x = round(1177 * stats["source_size"][0] / stats["source_size"][1])
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"

    target = (0.0, 0.05, 0.0)
    add_light("Key", (2.7, -4.2, 2.9), 590.0, 3.2, target)
    add_light("Fill", (-3.2, -2.6, 0.9), 180.0, 3.8, target)
    add_light("Rim", (0.4, 2.6, 3.0), 330.0, 2.8, target)
    camera_data = bpy.data.cameras.new("Scene_Fusion_QA_Camera")
    camera = bpy.data.objects.new("Scene_Fusion_QA_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.04

    render(scene, camera, (0.0, -5.0, 0.0), target, output_dir / "scene_fusion_front.png")
    render(scene, camera, (2.65, -4.60, 0.0), target, output_dir / "scene_fusion_30deg.png")
    render(scene, camera, (3.75, -3.75, 0.0), target, output_dir / "scene_fusion_45deg.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "scene_fusion_qa.blend"))


if __name__ == "__main__":
    main()
