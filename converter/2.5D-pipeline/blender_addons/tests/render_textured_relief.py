"""
File: blender_addons/tests/render_textured_relief.py
Purpose:
 - Render one UV-textured relief from the front and an oblique inspection angle.
 - Verify that the embedded GLB base-colour texture and relief geometry agree.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def argument(name: str) -> Path:
    values = sys.argv[sys.argv.index("--") + 1 :]
    try:
        index = values.index(name)
    except ValueError as error:
        raise SystemExit(f"Missing {name}") from error
    return Path(values[index + 1]).resolve()


def look_at(obj: bpy.types.Object, point: Vector) -> None:
    obj.rotation_euler = (point - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_sun(name: str, location: tuple[float, float, float], energy: float, angle: float) -> None:
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = energy
    data.angle = math.radians(angle)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, Vector((0.0, 0.0, 0.0)))


def render(scene: bpy.types.Scene, camera: bpy.types.Object, location, output: Path) -> None:
    camera.location = location
    look_at(camera, Vector((0.0, 0.0, 0.0)))
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    input_glb = argument("--input")
    output_dir = argument("--output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(input_glb), import_pack_images=True)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{input_glb} imported no mesh")

    minimum = Vector((float("inf"),) * 3)
    maximum = Vector((float("-inf"),) * 3)
    for obj in meshes:
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            minimum = Vector(tuple(min(minimum[index], point[index]) for index in range(3)))
            maximum = Vector(tuple(max(maximum[index], point[index]) for index in range(3)))
    center = (minimum + maximum) / 2.0
    for obj in bpy.context.scene.objects:
        if obj.parent is None:
            obj.location -= center

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 1.35

    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.008, 0.012, 0.02, 1.0)
    background.inputs["Strength"].default_value = 0.65

    camera_data = bpy.data.cameras.new("ACM_TEXTURE_QA_CAMERA")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 68.0
    camera = bpy.data.objects.new("ACM_TEXTURE_QA_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    add_sun("KEY", (-55.0, -100.0, 85.0), 3.2, 22.0)
    add_sun("FILL", (70.0, -85.0, 15.0), 1.35, 28.0)
    add_sun("RIM", (0.0, 50.0, 70.0), 0.9, 18.0)

    render(scene, camera, (0.0, -180.0, 0.0), output_dir / "textured-relief-front.png")
    camera_data.ortho_scale = 78.0
    render(scene, camera, (62.0, -190.0, 48.0), output_dir / "textured-relief-angle.png")
    print(f"ACM_TEXTURED_RELIEF_RENDER_OK {output_dir}")


if __name__ == "__main__":
    main()
