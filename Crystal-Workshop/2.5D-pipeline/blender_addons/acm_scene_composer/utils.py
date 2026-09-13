"""
File: blender_addons/acm_scene_composer/utils.py
Purpose:
 - Provide non-destructive asset grouping, import metadata and geometry helpers.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import bpy
from mathutils import Vector


MASTER_COLLECTION = "ACM_SCENE_COMPOSER"


def safe_name(value: str) -> str:
    """Return a compact Blender-safe display name without changing the source file."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("_")
    return cleaned or "asset"


def ensure_scene_units(scene: bpy.types.Scene) -> None:
    """Display one Blender unit as one millimetre, matching the native relief pipeline."""
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001


def ensure_master_collection(scene: bpy.types.Scene) -> bpy.types.Collection:
    collection = bpy.data.collections.get(MASTER_COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(MASTER_COLLECTION)
        scene.collection.children.link(collection)
    elif collection.name not in {child.name for child in scene.collection.children}:
        scene.collection.children.link(collection)
    return collection


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    """Move an object into one ACM collection without altering its world transform."""
    if collection.objects.get(obj.name) is None:
        collection.objects.link(obj)
    for owner in tuple(obj.users_collection):
        if owner != collection:
            owner.objects.unlink(obj)


def imported_objects(filepath: Path) -> list[bpy.types.Object]:
    """Import a supported local model and return only objects created by that call."""
    before = set(bpy.data.objects)
    suffix = filepath.suffix.lower()

    if suffix in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(
            filepath=str(filepath),
            import_pack_images=True,
            import_scene_extras=True,
            import_scene_as_collection=False,
        )
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(filepath))
    elif suffix == ".stl":
        bpy.ops.wm.stl_import(filepath=str(filepath))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(filepath))
    else:
        raise ValueError(f"Unsupported input extension: {suffix or '(none)'}")

    created = [obj for obj in bpy.data.objects if obj not in before]
    if not created:
        raise RuntimeError("The importer completed but created no Blender objects")
    return created


def create_asset_root(
    context: bpy.types.Context,
    objects: list[bpy.types.Object],
    input_type: str,
    source_path: str,
    project_name: str,
    face_count: int,
    face_state: str,
) -> bpy.types.Object:
    """Group an input under a metadata root while preserving every mesh transform."""
    master = ensure_master_collection(context.scene)
    asset_id = uuid.uuid4().hex
    label = safe_name(Path(source_path).stem if source_path else project_name)
    mode_label = "RELIEF" if input_type == "ACM_RELIEF_2_5D" else "FULL3D"
    collection = bpy.data.collections.new(f"ACM_{mode_label}_{label}")
    master.children.link(collection)

    object_set = set(objects)
    world_matrices = {obj: obj.matrix_world.copy() for obj in objects}
    for obj in objects:
        move_to_collection(obj, collection)

    root = bpy.data.objects.new(f"ACM_{mode_label}_{label}_ROOT", None)
    root.empty_display_type = "ARROWS"
    root.empty_display_size = 5.0
    collection.objects.link(root)

    for obj in objects:
        if obj.parent not in object_set:
            obj.parent = root
            obj.matrix_world = world_matrices[obj]

    root["acm_asset_root"] = True
    root["acm_asset_id"] = asset_id
    root["acm_input_type"] = input_type
    root["acm_geometry_policy"] = "PRESERVE_SOURCE_GEOMETRY"
    root["acm_source_path"] = source_path
    root["acm_project_name"] = project_name
    root["acm_face_count"] = int(face_count)
    root["acm_face_refinement_state"] = face_state
    root["acm_composer_version"] = "0.2.0"

    context.scene.acm_composer.active_asset_id = asset_id
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    context.view_layer.objects.active = root
    return root


def find_asset_root(context: bpy.types.Context) -> bpy.types.Object | None:
    """Resolve the selected asset first, then the scene's remembered asset id."""
    active = context.view_layer.objects.active
    cursor = active
    while cursor is not None:
        if cursor.get("acm_asset_root"):
            return cursor
        cursor = cursor.parent

    asset_id = context.scene.acm_composer.active_asset_id
    for obj in bpy.data.objects:
        if obj.get("acm_asset_root") and obj.get("acm_asset_id") == asset_id:
            return obj
    return None


def descendants(root: bpy.types.Object) -> list[bpy.types.Object]:
    result: list[bpy.types.Object] = []
    pending = list(root.children)
    while pending:
        obj = pending.pop()
        result.append(obj)
        pending.extend(obj.children)
    return result


def world_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector] | None:
    """World-space bounds for mesh, curve, surface and font objects."""
    points: list[Vector] = []
    for obj in objects:
        if obj.type not in {"MESH", "CURVE", "SURFACE", "FONT", "META"}:
            continue
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        return None
    minimum = Vector(tuple(min(point[index] for point in points) for index in range(3)))
    maximum = Vector(tuple(max(point[index] for point in points) for index in range(3)))
    return minimum, maximum


def asset_collection(root: bpy.types.Object) -> bpy.types.Collection:
    if not root.users_collection:
        raise RuntimeError("The active ACM root is not linked to a collection")
    return root.users_collection[0]


def create_box(
    name: str,
    dimensions: tuple[float, float, float],
    location: tuple[float, float, float],
    collection: bpy.types.Collection,
    parent: bpy.types.Object,
) -> bpy.types.Object:
    """Create one exact rectangular prism without relying on viewport context."""
    half_x, half_y, half_z = (value / 2.0 for value in dimensions)
    vertices = [
        (-half_x, -half_y, -half_z),
        (half_x, -half_y, -half_z),
        (half_x, half_y, -half_z),
        (-half_x, half_y, -half_z),
        (-half_x, -half_y, half_z),
        (half_x, -half_y, half_z),
        (half_x, half_y, half_z),
        (-half_x, half_y, half_z),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    ]
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    obj["acm_component_type"] = "FRAME"
    return obj
