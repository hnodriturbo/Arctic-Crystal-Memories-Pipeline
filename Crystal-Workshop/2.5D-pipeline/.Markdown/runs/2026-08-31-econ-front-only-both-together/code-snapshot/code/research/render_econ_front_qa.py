"""
File: code/research/render_econ_front_qa.py
Purpose:
 - Build a monochrome Blender QA scene from two ECON front-only OBJ surfaces.
 - Render source-facing and 45-degree views and export a combined GLB.
"""

import argparse
import math
from pathlib import Path

import bpy
from mathutils import Vector


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--person-left", required=True)
    parser.add_argument("--person-right", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(__import__("sys").argv[__import__("sys").argv.index("--") + 1 :])


def look_at(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def import_obj(path, name):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="NEGATIVE_Z", up_axis="Y")
    imported = list(set(bpy.data.objects) - before)
    if not imported:
        raise RuntimeError(f"Blender did not import an object from {path}")

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
    return light


def render_view(scene, camera, location, target, output_path):
    camera.location = location
    look_at(camera, target)
    scene.render.filepath = str(output_path)
    bpy.ops.render.render(write_still=True)


def main():
    args = parse_arguments()
    left_path = Path(args.person_left).resolve()
    right_path = Path(args.person_right).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Reset Blender and import the unmodified ECON surfaces.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    left = import_obj(left_path, "ECON_Front_Left_Man")
    right = import_obj(right_path, "ECON_Front_Right_Woman")

    # ECON normalizes each detected person around the crop origin. Recreate the
    # visible left/right ordering for QA while preserving all vertex geometry.
    left.location.x = -0.48
    right.location.x = 0.48
    right.location.z = 0.01

    material = bpy.data.materials.new("Crystal_White_Matte")
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.28, 0.30, 0.34, 1.0)
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = 0.68
    left.data.materials.append(material)
    right.data.materials.append(material)

    # Dark studio lighting exposes the same silhouette and fine relief changes
    # that matter in the crystal conversion QA view.
    world = bpy.data.worlds.new("QA_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.003, 0.004, 0.006, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.08

    scene = bpy.context.scene
    scene.world = world
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"

    target = (0.0, 0.0, 0.25)
    add_area_light("Key", (2.6, -4.2, 2.4), 480.0, 3.0, target)
    add_area_light("Fill", (-3.2, -2.6, 0.5), 135.0, 3.8, target)
    add_area_light("Rim", (0.4, 2.4, 2.8), 320.0, 2.6, target)

    camera_data = bpy.data.cameras.new("QA_Camera")
    camera = bpy.data.objects.new("QA_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.55

    render_view(
        scene,
        camera,
        (0.0, -5.0, 0.25),
        target,
        output_dir / "both_together_econ_front.png",
    )
    render_view(
        scene,
        camera,
        (3.6, -3.6, 0.25),
        target,
        output_dir / "both_together_econ_45deg.png",
    )

    # Store the QA scene and a compact interchange copy for MeshLab/web viewers.
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "both_together_econ_front_qa.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    left.select_set(True)
    right.select_set(True)
    bpy.context.view_layer.objects.active = left
    bpy.ops.export_scene.gltf(
        filepath=str(output_dir / "both_together_econ_front.glb"),
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
    )


if __name__ == "__main__":
    main()
