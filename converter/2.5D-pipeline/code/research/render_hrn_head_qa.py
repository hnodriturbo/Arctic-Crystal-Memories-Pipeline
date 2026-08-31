"""
File: code/research/render_hrn_head_qa.py
Purpose:
 - Render native HRN Head OBJ output from front, oblique, and profile views.
 - Produce both texture and neutral-clay QA views without changing geometry.
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
    parser.add_argument("--resolution", type=int, default=1100)
    return parser.parse_args(values)


def look_at(camera: bpy.types.Object, target: Vector, up_axis: str = "Y") -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat(
        "-Z", up_axis
    ).to_euler()


def mesh_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    low = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    high = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    return low, high


def render_view(
    scene: bpy.types.Scene,
    camera: bpy.types.Object,
    location: tuple[float, float, float],
    ortho_scale: float,
    output: Path,
    color_type: str,
    up_axis: str = "Y",
) -> None:
    scene.display.shading.color_type = color_type
    camera.location = location
    camera.data.ortho_scale = ortho_scale
    look_at(camera, Vector((0.0, 0.0, 0.0)), up_axis)
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def add_area_light(
    scene: bpy.types.Scene,
    name: str,
    location: tuple[float, float, float],
    energy: float,
    size: float,
) -> None:
    light_data = bpy.data.lights.new(name=name, type="AREA")
    light_data.energy = energy
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light)
    light.location = location
    look_at(light, Vector((0.0, 0.0, 0.0)), "Y")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.obj_import(filepath=str(args.input.resolve()), use_split_objects=False)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{args.input} imported no mesh")

    low, high = mesh_bounds(meshes)
    center = (low + high) * 0.5
    for obj in meshes:
        obj.location -= center

    extent = high - low
    vertical_scale = max(float(extent.z), float(extent.x)) * 1.15
    camera_distance = max(float(extent.x), float(extent.y), float(extent.z)) * 2.4

    texture_path = args.input.with_suffix(".jpg")
    if not texture_path.is_file():
        raise FileNotFoundError(f"HRN texture not found: {texture_path}")
    texture_material = bpy.data.materials.new("HRN_NATIVE_TEXTURE")
    texture_material.use_nodes = True
    nodes = texture_material.node_tree.nodes
    links = texture_material.node_tree.links
    principled = nodes.get("Principled BSDF")
    texture_node = nodes.new("ShaderNodeTexImage")
    texture_node.image = bpy.data.images.load(str(texture_path.resolve()))
    links.new(texture_node.outputs["Color"], principled.inputs["Base Color"])
    principled.inputs["Roughness"].default_value = 0.72
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(texture_material)

    clay = bpy.data.materials.new("HRN_QA_CLAY")
    clay.diffuse_color = (0.62, 0.68, 0.75, 1.0)

    scene = bpy.context.scene
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.01, 0.014, 0.022)

    camera_data = bpy.data.cameras.new("HRN_QA_CAMERA")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("HRN_QA_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    add_area_light(
        scene,
        "HRN_KEY_LIGHT",
        (camera_distance * 0.7, -camera_distance, camera_distance * 0.7),
        750.0,
        camera_distance,
    )
    add_area_light(
        scene,
        "HRN_FILL_LIGHT",
        (-camera_distance * 0.8, -camera_distance * 0.4, camera_distance * 0.2),
        360.0,
        camera_distance * 0.8,
    )

    # ModelScope HRN exports X horizontal, Z vertical, and Y depth. Its face
    # points toward negative Y, so the negative-Y camera is the frontal view.
    scene.render.engine = "BLENDER_EEVEE"
    render_view(
        scene,
        camera,
        (0.0, -camera_distance, 0.0),
        vertical_scale,
        args.output_dir / "front-texture.png",
        "TEXTURE",
    )

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.curvature_ridge_factor = 1.8
    scene.display.shading.curvature_valley_factor = 1.4
    scene.display.shading.show_specular_highlight = True
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(clay)

    render_view(
        scene,
        camera,
        (0.0, -camera_distance, 0.0),
        vertical_scale,
        args.output_dir / "front-clay.png",
        "MATERIAL",
    )
    render_view(
        scene,
        camera,
        (camera_distance * 0.7, -camera_distance * 0.7, 0.0),
        vertical_scale,
        args.output_dir / "oblique-clay.png",
        "MATERIAL",
    )
    render_view(
        scene,
        camera,
        (camera_distance, 0.0, 0.0),
        vertical_scale,
        args.output_dir / "profile-clay.png",
        "MATERIAL",
    )
    print(f"HRN_HEAD_QA_OK {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
