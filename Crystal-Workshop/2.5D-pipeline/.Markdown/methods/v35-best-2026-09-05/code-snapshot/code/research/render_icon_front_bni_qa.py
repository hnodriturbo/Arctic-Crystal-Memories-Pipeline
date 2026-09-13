"""
File: code/research/render_icon_front_bni_qa.py
Purpose:
 - Render neutral front and angled QA views of ICON-normal d-BiNI front surfaces.
 - Keep individual posture inspection separate from diagnostic side-by-side placement.
"""

import argparse
from pathlib import Path

import bpy
from mathutils import Vector


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--man", required=True)
    parser.add_argument("--woman", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(__import__("sys").argv[__import__("sys").argv.index("--") + 1 :])


def look_at(item, target):
    direction = Vector(target) - item.location
    item.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def import_front(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="NEGATIVE_Z", up_axis="Y")
    imported = list(set(bpy.data.objects) - before)
    if not imported:
        raise RuntimeError(f"No mesh imported from {path}")
    obj = imported[0]
    obj.name = name
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def add_area_light(name, location, energy, size, target):
    light_data = bpy.data.lights.new(name=name, type="AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name=name, object_data=light_data)
    bpy.context.collection.objects.link(light)
    light.location = location
    look_at(light, target)


def render(scene, camera, objects, location, target, ortho_scale, output_path):
    for obj, visible in objects:
        obj.hide_render = not visible
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    look_at(camera, target)
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def main():
    args = parse_arguments()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    man = import_front(Path(args.man).resolve(), "ICON_Front_BNI_Man")
    woman = import_front(Path(args.woman).resolve(), "ICON_Front_BNI_Woman")

    material = bpy.data.materials.new("Neutral_Geometry_QA")
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.32, 0.35, 0.40, 1.0)
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = 0.70
    man.data.materials.append(material)
    woman.data.materials.append(material)

    world = bpy.data.worlds.new("ICON_Front_QA_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.003, 0.004, 0.006, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.06

    scene = bpy.context.scene
    scene.world = world
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"

    target = (0.0, 0.0, 0.12)
    add_area_light("Key", (2.5, -4.0, 2.6), 520.0, 3.0, target)
    add_area_light("Fill", (-3.0, -2.4, 0.6), 150.0, 3.5, target)
    add_area_light("Rim", (0.5, 2.2, 2.8), 300.0, 2.6, target)

    camera_data = bpy.data.cameras.new("ICON_Front_QA_Camera")
    camera = bpy.data.objects.new("ICON_Front_QA_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"

    # Inspect each surface at its native origin before any side-by-side layout.
    man.location.x = 0.0
    woman.location.x = 0.0
    render(scene, camera, [(man, True), (woman, False)], (0.0, -5.0, 0.12), target, 2.15, output_dir / "man_icon_front_bni_front.png")
    render(scene, camera, [(man, True), (woman, False)], (2.7, -4.7, 0.12), target, 2.15, output_dir / "man_icon_front_bni_30deg.png")
    render(scene, camera, [(man, False), (woman, True)], (0.0, -5.0, 0.12), target, 2.15, output_dir / "woman_icon_front_bni_front.png")
    render(scene, camera, [(man, False), (woman, True)], (2.7, -4.7, 0.12), target, 2.15, output_dir / "woman_icon_front_bni_30deg.png")

    # The pair view is explicitly diagnostic placement, not source-camera fusion.
    man.location.x = -0.50
    woman.location.x = 0.50
    render(scene, camera, [(man, True), (woman, True)], (0.0, -5.0, 0.12), target, 2.55, output_dir / "both_icon_front_bni_diagnostic.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "icon_front_bni_qa.blend"))

    bpy.ops.object.select_all(action="DESELECT")
    man.select_set(True)
    woman.select_set(True)
    bpy.context.view_layer.objects.active = man
    bpy.ops.export_scene.gltf(
        filepath=str(output_dir / "both_icon_front_bni_diagnostic.glb"),
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
    )


if __name__ == "__main__":
    main()
