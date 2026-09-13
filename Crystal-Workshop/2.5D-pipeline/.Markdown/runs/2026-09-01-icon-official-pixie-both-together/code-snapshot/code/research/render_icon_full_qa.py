"""
File: code/research/render_icon_full_qa.py
Purpose:
 - Build a neutral Blender QA scene from two unmodified official ICON recon meshes.
 - Render front, 45-degree, and profile views and export a combined GLB.
"""

import argparse
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

    # Import raw marching-cubes reconstructions. Only scene placement and smooth
    # shading are applied; no topology or vertex positions inside either mesh change.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    left = import_obj(left_path, "ICON_Official_PIXIE_Man_Raw_Recon")
    right = import_obj(right_path, "ICON_Official_PIXIE_Woman_Raw_Recon")
    left.location.x = -0.47
    right.location.x = 0.47

    material = bpy.data.materials.new("ICON_Raw_Recon_Neutral")
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.34, 0.37, 0.43, 1.0)
    principled.inputs["Metallic"].default_value = 0.0
    principled.inputs["Roughness"].default_value = 0.62
    left.data.materials.append(material)
    right.data.materials.append(material)

    world = bpy.data.worlds.new("ICON_QA_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.005, 0.008, 1.0)
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

    target = (0.0, 0.0, -0.05)
    add_area_light("Key", (2.8, -4.4, 2.8), 520.0, 3.2, target)
    add_area_light("Fill", (-3.0, -2.8, 0.6), 155.0, 3.8, target)
    add_area_light("Rim", (0.2, 2.8, 2.7), 350.0, 2.8, target)

    camera_data = bpy.data.cameras.new("ICON_QA_Camera")
    camera = bpy.data.objects.new("ICON_QA_Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.35

    render_view(
        scene,
        camera,
        (0.0, -5.2, -0.05),
        target,
        output_dir / "both_together_icon_official_pixie_front.png",
    )
    render_view(
        scene,
        camera,
        (3.8, -3.8, -0.05),
        target,
        output_dir / "both_together_icon_official_pixie_45deg.png",
    )
    render_view(
        scene,
        camera,
        (5.2, 0.0, -0.05),
        target,
        output_dir / "both_together_icon_official_pixie_profile.png",
    )

    bpy.ops.wm.save_as_mainfile(
        filepath=str(output_dir / "both_together_icon_official_pixie_raw_recon_qa.blend")
    )
    bpy.ops.object.select_all(action="DESELECT")
    left.select_set(True)
    right.select_set(True)
    bpy.context.view_layer.objects.active = left
    bpy.ops.export_scene.gltf(
        filepath=str(output_dir / "both_together_icon_official_pixie_raw_recon.glb"),
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
    )


if __name__ == "__main__":
    main()
