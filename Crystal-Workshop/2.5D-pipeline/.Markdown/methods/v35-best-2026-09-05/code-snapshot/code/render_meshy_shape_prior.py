"""
File: converter/2.5D-pipeline/code/render_meshy_shape_prior.py
Purpose:
 - Render Meshy full-3D geometry as neutral clay from front and oblique views.
 - Exclude helper cubes and textures so only the reusable head/body shape prior
   is judged before it is fused into the ACM 2.5D pipeline.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--height-mm", type=float, default=78.0)
    parser.add_argument("--resolution-x", type=int, default=1800)
    parser.add_argument("--resolution-y", type=int, default=900)
    return parser.parse_args(values)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def world_bounds(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    low = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    high = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    return low, high


def clay_material() -> bpy.types.Material:
    material = bpy.data.materials.new("ACM_MESHY_SHAPE_CLAY")
    material.diffuse_color = (0.58, 0.64, 0.72, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (0.58, 0.64, 0.72, 1.0)
    principled.inputs["Roughness"].default_value = 0.78
    return material


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_label(text_value: str, location: tuple[float, float, float]) -> None:
    curve = bpy.data.curves.new(f"{text_value}_CURVE", type="FONT")
    curve.body = text_value
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = 5.5
    text = bpy.data.objects.new(text_value, curve)
    bpy.context.scene.collection.objects.link(text)
    text.location = location
    text.rotation_euler[0] = math.radians(90.0)

    material = bpy.data.materials.get("ACM_LABEL") or bpy.data.materials.new("ACM_LABEL")
    material.diffuse_color = (0.92, 0.95, 1.0, 1.0)
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        0.92,
        0.95,
        1.0,
        1.0,
    )
    curve.materials.append(material)


def main() -> None:
    args = arguments()
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()), import_pack_images=True)

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    source = max(meshes, key=lambda obj: len(obj.data.vertices))
    low, high = world_bounds(source)
    center = (low + high) * 0.5
    height = max(high.z - low.z, 1e-6)
    scale = args.height_mm / height
    source_matrix = source.matrix_world.copy()
    material = clay_material()

    # Share the dense Meshy mesh datablock between both QA views. Each root is
    # independently rotated around the normalized model centre.
    for x_position, angle, label in (
        (-47.0, 0.0, "MESHY SHAPE · FRONT"),
        (47.0, -52.0, "MESHY SHAPE · OBLIQUE"),
    ):
        duplicate = bpy.data.objects.new(f"{label}_MESH", source.data)
        bpy.context.scene.collection.objects.link(duplicate)
        duplicate.matrix_world = Matrix.Translation(-center) @ source_matrix
        duplicate.data.materials.clear()
        duplicate.data.materials.append(material)

        root = bpy.data.objects.new(f"{label}_ROOT", None)
        bpy.context.scene.collection.objects.link(root)
        duplicate.parent = root
        root.scale = (scale, scale, scale)
        root.rotation_euler[2] = math.radians(angle)
        root.location = (x_position, 0.0, 3.0)
        add_label(label, (x_position, -18.0, -43.0))

    for obj in list(bpy.context.scene.objects):
        if obj not in {source} and obj.name.endswith(("_MESH", "_ROOT")):
            continue
        if obj == source or obj.type == "MESH" and not obj.name.endswith("_MESH"):
            bpy.data.objects.remove(obj, do_unlink=True)

    camera_data = bpy.data.cameras.new("ACM_MESHY_PRIOR_CAMERA")
    camera = bpy.data.objects.new("ACM_MESHY_PRIOR_CAMERA", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (0.0, -360.0, 3.0)
    camera_data.lens = 52.0
    point_at(camera, Vector((0.0, 0.0, 2.0)))
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("KEY", (-100.0, -150.0, 120.0), 1400.0, 105.0),
        ("FILL", (120.0, -120.0, -30.0), 720.0, 90.0),
    ):
        light_data = bpy.data.lights.new(f"ACM_{name}", type="AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"ACM_{name}", light_data)
        bpy.context.scene.collection.objects.link(light)
        light.location = location
        point_at(light, Vector((0.0, 0.0, 2.0)))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.show_specular_highlight = True
    scene.render.resolution_x = args.resolution_x
    scene.render.resolution_y = args.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.015, 0.02, 0.03)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.output.resolve())
    bpy.ops.render.render(write_still=True)
    print(f"MESHY_SHAPE_RENDER_OK {args.output.resolve()}")


if __name__ == "__main__":
    main()
