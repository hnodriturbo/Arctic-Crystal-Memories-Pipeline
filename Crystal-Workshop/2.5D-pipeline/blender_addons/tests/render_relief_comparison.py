"""
File: blender_addons/tests/render_relief_comparison.py
Purpose:
 - Render the same native relief before and after face-depth refinement.
 - Produce repeatable front and angled QA images with identical lighting.
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


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for material in tuple(bpy.data.materials):
        bpy.data.materials.remove(material)


def import_glb(path: Path, label: str, x_offset: float) -> list[bpy.types.Object]:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path), import_pack_images=True)
    objects = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [obj for obj in objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{path} imported no mesh objects")

    minimum = Vector((float("inf"),) * 3)
    maximum = Vector((float("-inf"),) * 3)
    for obj in meshes:
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            minimum = Vector(tuple(min(minimum[index], point[index]) for index in range(3)))
            maximum = Vector(tuple(max(maximum[index], point[index]) for index in range(3)))
    center = (minimum + maximum) / 2.0
    for obj in objects:
        if obj.parent is None:
            obj.location += Vector((x_offset - center.x, -center.y, -center.z))

    add_label(label, (x_offset, -10.0, 36.0))
    return meshes


def add_label(body: str, location: tuple[float, float, float]) -> None:
    curve = bpy.data.curves.new(f"{body}_CURVE", type="FONT")
    curve.body = body
    curve.align_x = "CENTER"
    curve.size = 4.0
    curve.extrude = 0.08
    obj = bpy.data.objects.new(body, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    # glTF imports the relief into Blender's XZ plane, facing a camera on -Y.
    obj.rotation_euler.x = math.radians(90.0)


def look_at(obj: bpy.types.Object, point: Vector) -> None:
    obj.rotation_euler = (point - obj.location).to_track_quat("-Z", "Y").to_euler()


def create_clay_material() -> bpy.types.Material:
    material = bpy.data.materials.new("ACM_QA_CLAY")
    material.diffuse_color = (0.62, 0.66, 0.72, 1.0)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.42, 0.48, 0.58, 1.0)
    shader.inputs["Roughness"].default_value = 0.72
    shader.inputs["Metallic"].default_value = 0.0
    return material


def add_area_light(name: str, location: tuple[float, float, float], energy: float, size: float) -> None:
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    look_at(obj, Vector((0.0, 0.0, 0.0)))


def add_sun_light(name: str, location: tuple[float, float, float], energy: float) -> None:
    """Add scale-independent studio illumination for millimetre-sized geometry."""
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = energy
    data.angle = math.radians(18.0)
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
    base = argument("--base")
    refined = argument("--refined")
    detail = argument("--detail")
    output_dir = argument("--output-dir")
    output_dir.mkdir(parents=True, exist_ok=True)

    reset_scene()
    base_meshes = import_glb(base, "MOGE 9/9", -66.0)
    refined_meshes = import_glb(refined, "FACE REFINED", 0.0)
    detail_meshes = import_glb(detail, "FACE + MICRO DETAIL", 66.0)
    clay = create_clay_material()
    for obj in [*base_meshes, *refined_meshes, *detail_meshes]:
        obj.data.materials.clear()
        obj.data.materials.append(clay)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.035, 0.045, 0.065, 1.0)
    background.inputs["Strength"].default_value = 0.32
    scene.view_settings.look = "AgX - Medium High Contrast"

    camera_data = bpy.data.cameras.new("ACM_QA_CAMERA")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 150.0
    camera = bpy.data.objects.new("ACM_QA_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    add_sun_light("KEY", (-65.0, -110.0, 95.0), 3.2)
    add_sun_light("FILL", (85.0, -95.0, 25.0), 1.35)
    add_sun_light("RIM", (0.0, 55.0, 75.0), 1.8)

    render(scene, camera, (0.0, -220.0, 0.0), output_dir / "relief-comparison-front.png")
    camera_data.ortho_scale = 175.0
    render(scene, camera, (90.0, -240.0, 75.0), output_dir / "relief-comparison-angle.png")
    print(f"ACM_RELIEF_COMPARISON_OK {output_dir}")


if __name__ == "__main__":
    main()
