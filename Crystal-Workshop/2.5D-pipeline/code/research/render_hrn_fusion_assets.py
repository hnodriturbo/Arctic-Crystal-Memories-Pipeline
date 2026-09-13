"""
File: code/research/render_hrn_fusion_assets.py
Purpose:
 - Render a native HRN head into deterministic front texture, depth, and mask images.
 - Provide source-camera fusion inputs without changing the HRN geometry.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--resolution", type=int, default=1024)
    return parser.parse_args(values)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.wm.obj_import(filepath=str(input_path), use_split_objects=False)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{input_path} imported no mesh")

    corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    low = Vector(tuple(min(point[index] for point in corners) for index in range(3)))
    high = Vector(tuple(max(point[index] for point in corners) for index in range(3)))
    center = (low + high) * 0.5
    for obj in meshes:
        obj.location -= center
    extent = high - low

    texture_path = input_path.with_suffix(".jpg")
    if not texture_path.is_file():
        raise FileNotFoundError(f"HRN texture not found: {texture_path}")
    material = bpy.data.materials.new("HRN_FUSION_TEXTURE")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = nodes.get("Principled BSDF")
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = bpy.data.images.load(str(texture_path))
    links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    principled.inputs["Roughness"].default_value = 1.0
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(material)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True

    camera_distance = max(float(extent.x), float(extent.y), float(extent.z)) * 2.4
    ortho_scale = max(float(extent.z), float(extent.x)) * 1.15
    camera_data = bpy.data.cameras.new("HRN_FUSION_CAMERA")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = ortho_scale
    camera_data.clip_start = max(0.001, camera_distance * 0.05)
    camera_data.clip_end = camera_distance * 4.0
    camera = bpy.data.objects.new("HRN_FUSION_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -camera_distance, 0.0)
    look_at(camera, Vector((0.0, 0.0, 0.0)))
    scene.camera = camera

    light_data = bpy.data.lights.new(name="HRN_FUSION_LIGHT", type="AREA")
    light_data.energy = 900.0
    light_data.shape = "DISK"
    light_data.size = camera_distance
    light = bpy.data.objects.new("HRN_FUSION_LIGHT", light_data)
    scene.collection.objects.link(light)
    light.location = (camera_distance * 0.5, -camera_distance, camera_distance * 0.6)
    look_at(light, Vector((0.0, 0.0, 0.0)))

    near_y = float(low.y - center.y)
    far_y = float(high.y - center.y)
    scene.render.filepath = str(output_dir / "hrn-front-texture.png")
    bpy.ops.render.render(write_still=True)

    # Encode native object-space depth directly as a grayscale emission. This
    # avoids compositor/API differences while retaining a 16-bit alpha mask.
    depth_material = bpy.data.materials.new("HRN_NATIVE_FRONT_DEPTH")
    depth_material.use_nodes = True
    depth_nodes = depth_material.node_tree.nodes
    depth_links = depth_material.node_tree.links
    for node in list(depth_nodes):
        depth_nodes.remove(node)
    output = depth_nodes.new("ShaderNodeOutputMaterial")
    emission = depth_nodes.new("ShaderNodeEmission")
    geometry = depth_nodes.new("ShaderNodeNewGeometry")
    separate = depth_nodes.new("ShaderNodeSeparateXYZ")
    map_range = depth_nodes.new("ShaderNodeMapRange")
    map_range.inputs["From Min"].default_value = near_y
    map_range.inputs["From Max"].default_value = far_y
    map_range.inputs["To Min"].default_value = 1.0
    map_range.inputs["To Max"].default_value = 0.0
    map_range.clamp = True
    depth_links.new(geometry.outputs["Position"], separate.inputs["Vector"])
    depth_links.new(separate.outputs["Y"], map_range.inputs["Value"])
    depth_links.new(map_range.outputs["Result"], emission.inputs["Color"])
    depth_links.new(emission.outputs["Emission"], output.inputs["Surface"])
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(depth_material)

    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "16"
    scene.render.filepath = str(output_dir / "hrn-front-depth.png")
    bpy.ops.render.render(write_still=True)

    metadata = {
        "input": str(input_path),
        "texture": str(texture_path),
        "resolution": args.resolution,
        "camera": {
            "location": list(camera.location),
            "ortho_scale": ortho_scale,
            "near_object_y": near_y,
            "far_object_y": far_y,
        },
        "center_removed": list(center),
        "original_bounds": [list(low), list(high)],
        "model_stack": "Official ModelScope HRN Head (BFM+FLAME), native geometry",
    }
    (output_dir / "hrn-front-assets.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(f"HRN_FUSION_ASSETS_OK {output_dir}")


if __name__ == "__main__":
    main()
