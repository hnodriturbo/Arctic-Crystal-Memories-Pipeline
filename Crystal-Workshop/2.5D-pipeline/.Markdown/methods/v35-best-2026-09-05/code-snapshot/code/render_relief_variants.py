"""
File: converter/2.5D-pipeline/code/render_relief_variants.py
Purpose:
 - Render shallow, balanced and deep GLB relief variants side by side in
   Blender so physical Z-depth can be judged from one reproducible image.
 - Preserve embedded textures and use an oblique view that exposes profile
   depth without requiring manual viewport setup.

Run with Blender, not ordinary Python:
 blender --background --python code/render_relief_variants.py -- \
   --shallow shallow.glb --balanced balanced.glb --deep deep.glb --output compare.png
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--shallow", required=True, type=Path)
    parser.add_argument("--balanced", required=True, type=Path)
    parser.add_argument("--deep", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--angle", type=float, default=42.0, help="Oblique rotation in degrees.")
    parser.add_argument(
        "--appearance",
        choices=("crystal", "clay"),
        default="crystal",
        help="Show the embedded monochrome map or neutral geometry-only clay.",
    )
    parser.add_argument("--resolution-x", type=int, default=2400)
    parser.add_argument("--resolution-y", type=int, default=900)
    return parser.parse_args(values)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in tuple(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ Vector(corner) for obj in objects if hasattr(obj, "bound_box") for corner in obj.bound_box]
    low = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    high = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    return low, high


def make_textures_readable(objects: list[bpy.types.Object]) -> None:
    """Feed the embedded texture into emission so QA is independent of face winding."""
    materials = {
        slot.material
        for obj in objects
        if obj.type == "MESH"
        for slot in obj.material_slots
        if slot.material is not None
    }
    for material in materials:
        material.use_nodes = True
        tree = material.node_tree
        principled = next((node for node in tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
        if principled is None:
            continue
        base = principled.inputs.get("Base Color")
        emission = principled.inputs.get("Emission Color") or principled.inputs.get("Emission")
        strength = principled.inputs.get("Emission Strength")
        if base and emission and base.links:
            tree.links.new(base.links[0].from_socket, emission)
        if strength:
            strength.default_value = 0.85


def make_clay_readable(objects: list[bpy.types.Object]) -> None:
    """Replace imported photo materials with one neutral material for geometry QA."""
    material = bpy.data.materials.get("ACM_GEOMETRY_CLAY")
    if material is None:
        material = bpy.data.materials.new("ACM_GEOMETRY_CLAY")
        material.diffuse_color = (0.62, 0.66, 0.72, 1.0)
        material.use_nodes = True
        tree = material.node_tree
        principled = tree.nodes.get("Principled BSDF")
        layer_weight = tree.nodes.new("ShaderNodeLayerWeight")
        ramp = tree.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.58
        ramp.color_ramp.elements[0].color = (0.03, 0.04, 0.06, 1.0)
        ramp.color_ramp.elements[1].position = 0.86
        ramp.color_ramp.elements[1].color = (0.88, 0.92, 1.0, 1.0)
        tree.links.new(layer_weight.outputs["Facing"], ramp.inputs["Fac"])
        tree.links.new(ramp.outputs["Color"], principled.inputs["Base Color"])
        principled.inputs["Roughness"].default_value = 0.82
        emission = principled.inputs.get("Emission Color") or principled.inputs.get("Emission")
        strength = principled.inputs.get("Emission Strength")
        if emission:
            tree.links.new(ramp.outputs["Color"], emission)
        if strength:
            strength.default_value = 0.82
    for obj in objects:
        if obj.type != "MESH":
            continue
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        obj.select_set(False)
        obj.data.materials.clear()
        obj.data.materials.append(material)


def import_variant(path: Path, x_position: float, label: str, angle: float, appearance: str) -> None:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), import_pack_images=True)
    created = [obj for obj in bpy.data.objects if obj not in before]
    drawable = [obj for obj in created if obj.type == "MESH"]
    if appearance == "clay":
        make_clay_readable(drawable)
    else:
        make_textures_readable(drawable)
    low, high = bounds(drawable)
    center = (low + high) * 0.5

    root = bpy.data.objects.new(f"{label}_ROOT", None)
    bpy.context.scene.collection.objects.link(root)
    root.location = center
    created_set = set(created)
    top_level = [obj for obj in created if obj.parent not in created_set]
    for obj in top_level:
        matrix = obj.matrix_world.copy()
        obj.parent = root
        obj.matrix_world = matrix
    root.location = (x_position, 0.0, 0.0)
    # glTF imports into Blender's Z-up world: source Y(height) becomes Blender
    # Z and source Z(depth) becomes Blender Y. Rotate around vertical Z so the
    # camera sees both the face and the relief profile.
    root.rotation_euler[2] = math.radians(-angle)

    curve = bpy.data.curves.new(f"{label}_LABEL_CURVE", type="FONT")
    curve.body = label
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.size = 7.0
    text = bpy.data.objects.new(f"{label}_LABEL", curve)
    bpy.context.scene.collection.objects.link(text)
    text.location = (x_position, -18.0, -44.0)
    text.rotation_euler[0] = math.radians(90.0)

    material = bpy.data.materials.get("ACM_LABEL_MATERIAL")
    if material is None:
        material = bpy.data.materials.new("ACM_LABEL_MATERIAL")
        material.diffuse_color = (0.9, 0.94, 1.0, 1.0)
        material.use_nodes = True
        material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.94, 1.0, 1.0)
        material.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.7
        emission = material.node_tree.nodes["Principled BSDF"].inputs.get("Emission Color")
        if emission:
            emission.default_value = (0.9, 0.94, 1.0, 1.0)
        strength = material.node_tree.nodes["Principled BSDF"].inputs.get("Emission Strength")
        if strength:
            strength.default_value = 1.0
    curve.materials.append(material)


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    args = arguments()
    clear_scene()
    variants = (
        (args.shallow, -92.0, "SHALLOW · 8 mm"),
        (args.balanced, 0.0, "BALANCED · 16 mm"),
        (args.deep, 92.0, "DEEP · 24 mm"),
    )
    for path, x_position, label in variants:
        import_variant(path.resolve(), x_position, label, args.angle, args.appearance)

    camera_data = bpy.data.cameras.new("ACM_COMPARE_CAMERA")
    camera = bpy.data.objects.new("ACM_COMPARE_CAMERA", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (0.0, -390.0, 0.0)
    camera_data.lens = 56.0
    point_camera(camera, Vector((0.0, 0.0, 0.0)))
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("KEY", (-130.0, -240.0, 110.0), 1500.0, 130.0),
        ("FILL", (150.0, -170.0, -60.0), 900.0, 100.0),
    ):
        light_data = bpy.data.lights.new(f"ACM_{name}", type="AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(f"ACM_{name}", light_data)
        bpy.context.scene.collection.objects.link(light)
        light.location = location
        point_camera(light, Vector((0.0, 0.0, 0.0)))

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = args.resolution_x
    scene.render.resolution_y = args.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.003, 0.006, 0.012)
    scene.render.filepath = str(args.output.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print(f"RENDER_OK {args.output.resolve()}")


if __name__ == "__main__":
    main()
