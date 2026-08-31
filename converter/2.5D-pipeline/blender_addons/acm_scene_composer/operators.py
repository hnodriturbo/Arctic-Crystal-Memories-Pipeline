"""
File: blender_addons/acm_scene_composer/operators.py
Purpose:
 - Import, adopt, arrange, validate and export ACM composition assets.
 - Add simple frame and text components without modifying source mesh data.
"""

from __future__ import annotations

from pathlib import Path

import bpy
from bpy.types import Operator

from . import utils


SUPPORTED_EXTENSIONS = {".glb", ".gltf", ".obj", ".stl", ".fbx"}


def face_state(settings) -> str:
    return "PENDING" if settings.face_count > 0 else "NOT_APPLICABLE"


def sync_face_metadata(root: bpy.types.Object, settings) -> None:
    root["acm_face_count"] = int(settings.face_count)
    root["acm_face_refinement_state"] = settings.face_refinement_state


def resolved_relief_depth(settings) -> float:
    """Resolve a Composer depth preset without exceeding usable crystal depth."""
    usable = max(0.1, settings.crystal_depth_mm - 2.0 * settings.crystal_margin_mm)
    if settings.relief_depth_profile == "CUSTOM":
        return min(float(settings.custom_relief_depth_mm), usable)
    profiles = {
        "SHALLOW": min(8.0, usable * 0.20),
        "BALANCED": min(16.0, usable * 0.40),
        "DEEP": min(24.0, usable * 0.60),
    }
    return profiles.get(settings.relief_depth_profile, profiles["BALANCED"])


class ACM_OT_import_asset(Operator):
    bl_idname = "acm.import_asset"
    bl_label = "Import ACM Input"
    bl_description = "Import and tag a relief or full-3D asset without changing its mesh geometry"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.acm_composer
        filepath = Path(bpy.path.abspath(settings.input_path)).resolve()
        if not filepath.is_file():
            self.report({"ERROR"}, f"Input file does not exist: {filepath}")
            return {"CANCELLED"}
        if filepath.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self.report({"ERROR"}, f"Unsupported input type: {filepath.suffix}")
            return {"CANCELLED"}

        try:
            objects = utils.imported_objects(filepath)
            settings.face_refinement_state = face_state(settings)
            root = utils.create_asset_root(
                context,
                objects,
                settings.input_type,
                str(filepath),
                settings.project_name,
                settings.face_count,
                settings.face_refinement_state,
            )
            root["acm_appearance_variant"] = settings.appearance_variant
            utils.ensure_scene_units(context.scene)
        except Exception as error:  # noqa: BLE001 - Blender must surface importer failures in the UI
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Imported {len(objects)} object(s) under {root.name}")
        return {"FINISHED"}


class ACM_OT_adopt_selected(Operator):
    bl_idname = "acm.adopt_selected"
    bl_label = "Adopt Selected as Input"
    bl_description = "Tag existing selected objects as one ACM input without re-importing them"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.acm_composer
        objects = [obj for obj in context.selected_objects if not obj.get("acm_asset_root")]
        if not objects:
            self.report({"ERROR"}, "Select one or more source objects first")
            return {"CANCELLED"}

        settings.face_refinement_state = face_state(settings)
        root = utils.create_asset_root(
            context,
            objects,
            settings.input_type,
            settings.input_path,
            settings.project_name,
            settings.face_count,
            settings.face_refinement_state,
        )
        root["acm_appearance_variant"] = settings.appearance_variant
        utils.ensure_scene_units(context.scene)
        self.report({"INFO"}, f"Adopted {len(objects)} object(s) under {root.name}")
        return {"FINISHED"}


class ACM_OT_apply_layout(Operator):
    bl_idname = "acm.apply_layout"
    bl_label = "Apply Asset Layout"
    bl_description = "Apply root-only position, rotation and uniform target-height scaling"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.acm_composer
        root = utils.find_asset_root(context)
        if root is None:
            self.report({"ERROR"}, "No active ACM asset")
            return {"CANCELLED"}

        root.location = settings.placement
        root.rotation_euler = settings.rotation
        bounds = utils.world_bounds(utils.descendants(root))
        if bounds is None:
            self.report({"ERROR"}, "The active asset has no drawable geometry")
            return {"CANCELLED"}

        current_height = bounds[1].y - bounds[0].y
        if current_height <= 1e-9:
            self.report({"ERROR"}, "The asset has zero Y height")
            return {"CANCELLED"}
        factor = settings.target_height_mm / current_height
        root.scale = tuple(value * factor for value in root.scale)
        context.view_layer.update()

        if settings.input_type == "ACM_RELIEF_2_5D":
            scaled_bounds = utils.world_bounds(utils.descendants(root))
            current_depth = scaled_bounds[1].z - scaled_bounds[0].z if scaled_bounds else 0.0
            if current_depth <= 1e-9:
                self.report({"ERROR"}, "The relief has zero Z depth")
                return {"CANCELLED"}
            target_depth = resolved_relief_depth(settings)
            root.scale.z *= target_depth / current_depth
            root["acm_relief_depth_profile"] = settings.relief_depth_profile
            root["acm_relief_depth_mm"] = target_depth
            root["acm_crystal_depth_mm"] = float(settings.crystal_depth_mm)
            root["acm_crystal_margin_mm"] = float(settings.crystal_margin_mm)
        root["acm_target_height_mm"] = float(settings.target_height_mm)
        suffix = (
            f", relief depth {root.get('acm_relief_depth_mm', 0):g} mm"
            if settings.input_type == "ACM_RELIEF_2_5D"
            else ""
        )
        self.report({"INFO"}, f"Asset height set to {settings.target_height_mm:g} mm{suffix}")
        return {"FINISHED"}


class ACM_OT_update_face_qa(Operator):
    bl_idname = "acm.update_face_qa"
    bl_label = "Update FaceBuilder Status"
    bl_description = "Store the per-asset face count and FaceBuilder completion state"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.acm_composer
        root = utils.find_asset_root(context)
        if root is None:
            self.report({"ERROR"}, "No active ACM asset")
            return {"CANCELLED"}
        if settings.face_count == 0:
            settings.face_refinement_state = "NOT_APPLICABLE"
        elif settings.face_refinement_state == "NOT_APPLICABLE":
            settings.face_refinement_state = "PENDING"
        sync_face_metadata(root, settings)
        self.report({"INFO"}, "FaceBuilder QA state stored on the active asset")
        return {"FINISHED"}


class ACM_OT_add_text(Operator):
    bl_idname = "acm.add_text"
    bl_label = "Add Composition Text"
    bl_description = "Add editable text in the ACM XY composition plane"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.acm_composer
        root = utils.find_asset_root(context)
        if root is None:
            self.report({"ERROR"}, "No active ACM asset")
            return {"CANCELLED"}
        if not settings.text_body.strip():
            self.report({"ERROR"}, "Text cannot be empty")
            return {"CANCELLED"}

        curve = bpy.data.curves.new("ACM_TEXT_CURVE", type="FONT")
        curve.body = settings.text_body
        curve.align_x = "CENTER"
        curve.align_y = "CENTER"
        curve.size = settings.text_size_mm
        curve.extrude = settings.text_depth_mm / 2.0
        curve.offset = 0.01
        obj = bpy.data.objects.new("ACM_TEXT", curve)
        utils.asset_collection(root).objects.link(obj)
        obj.parent = root
        obj.location = settings.text_position
        obj["acm_component_type"] = "TEXT"
        self.report({"INFO"}, "Added editable ACM text")
        return {"FINISHED"}


class ACM_OT_add_frame(Operator):
    bl_idname = "acm.add_frame"
    bl_label = "Add Rectangular Frame"
    bl_description = "Add a four-piece frame in the ACM XY composition plane"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.acm_composer
        root = utils.find_asset_root(context)
        if root is None:
            self.report({"ERROR"}, "No active ACM asset")
            return {"CANCELLED"}
        if settings.frame_bar_mm * 2 >= min(settings.frame_width_mm, settings.frame_height_mm):
            self.report({"ERROR"}, "Frame bars are too wide for the frame")
            return {"CANCELLED"}

        collection = utils.asset_collection(root)
        width = settings.frame_width_mm
        height = settings.frame_height_mm
        depth = settings.frame_depth_mm
        bar = settings.frame_bar_mm
        pieces = (
            ("ACM_FRAME_TOP", (width, bar, depth), (0.0, (height - bar) / 2.0, 0.0)),
            ("ACM_FRAME_BOTTOM", (width, bar, depth), (0.0, -(height - bar) / 2.0, 0.0)),
            ("ACM_FRAME_LEFT", (bar, height - 2 * bar, depth), (-(width - bar) / 2.0, 0.0, 0.0)),
            ("ACM_FRAME_RIGHT", (bar, height - 2 * bar, depth), ((width - bar) / 2.0, 0.0, 0.0)),
        )
        for name, dimensions, location in pieces:
            obj = utils.create_box(name, dimensions, location, collection, root)
            if settings.frame_bevel_mm > 0:
                modifier = obj.modifiers.new("ACM_FRAME_BEVEL", "BEVEL")
                modifier.width = settings.frame_bevel_mm
                modifier.segments = 3
        self.report({"INFO"}, "Added four-piece ACM frame")
        return {"FINISHED"}


def validation_summary(root: bpy.types.Object) -> tuple[str, list[str]]:
    objects = utils.descendants(root)
    meshes = [obj for obj in objects if obj.type == "MESH"]
    errors: list[str] = []
    if not meshes:
        errors.append("no mesh objects")
    polygons = sum(len(obj.data.polygons) for obj in meshes)
    vertices = sum(len(obj.data.vertices) for obj in meshes)
    materials = sum(len(obj.material_slots) for obj in meshes)
    bounds = utils.world_bounds(objects)
    dimensions = "n/a"
    if bounds is not None:
        size = bounds[1] - bounds[0]
        dimensions = f"{size.x:.2f} x {size.y:.2f} x {size.z:.2f} mm"

    faces = int(root.get("acm_face_count", 0))
    face_state_value = root.get("acm_face_refinement_state", "NOT_APPLICABLE")
    if faces > 0 and face_state_value != "COMPLETE":
        errors.append(f"FaceBuilder pending for {faces} face(s)")

    summary = (
        f"{root.get('acm_input_type', 'UNKNOWN')}: {len(meshes)} mesh(es), "
        f"{vertices:,} vertices, {polygons:,} polygons, {materials} material slot(s), {dimensions}"
    )
    return summary, errors


class ACM_OT_validate_asset(Operator):
    bl_idname = "acm.validate_asset"
    bl_label = "Validate Active Asset"
    bl_description = "Inspect geometry, materials, dimensions and required FaceBuilder state"

    def execute(self, context):
        settings = context.scene.acm_composer
        root = utils.find_asset_root(context)
        if root is None:
            self.report({"ERROR"}, "No active ACM asset")
            return {"CANCELLED"}
        summary, errors = validation_summary(root)
        settings.last_report = summary + (" | BLOCKED: " + "; ".join(errors) if errors else " | READY")
        self.report({"WARNING"} if errors else {"INFO"}, settings.last_report)
        return {"FINISHED"}


class ACM_OT_export_asset(Operator):
    bl_idname = "acm.export_asset"
    bl_label = "Export Final Textured GLB"
    bl_description = "Export the active composition while preserving its 2.5D or full-3D mode"

    def execute(self, context):
        settings = context.scene.acm_composer
        root = utils.find_asset_root(context)
        if root is None:
            self.report({"ERROR"}, "No active ACM asset")
            return {"CANCELLED"}

        summary, errors = validation_summary(root)
        if settings.enforce_face_refinement:
            face_errors = [error for error in errors if error.startswith("FaceBuilder")]
            if face_errors:
                self.report({"ERROR"}, "; ".join(face_errors))
                return {"CANCELLED"}
        if any(error == "no mesh objects" for error in errors):
            self.report({"ERROR"}, "The active asset has no mesh objects")
            return {"CANCELLED"}

        output = Path(bpy.path.abspath(settings.export_path)).resolve()
        if output.suffix.lower() != ".glb":
            output = output.with_suffix(".glb")
            settings.export_path = str(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        previous_selection = list(context.selected_objects)
        previous_active = context.view_layer.objects.active
        bpy.ops.object.select_all(action="DESELECT")
        export_objects = [root, *utils.descendants(root)]
        for obj in export_objects:
            obj.select_set(True)
        context.view_layer.objects.active = root

        try:
            bpy.ops.export_scene.gltf(
                filepath=str(output),
                export_format="GLB",
                use_selection=True,
                export_materials="EXPORT",
                export_texcoords=True,
                export_normals=True,
                export_cameras=False,
                export_lights=False,
                export_animations=False,
                export_extras=True,
                export_apply=False,
                gltf_export_id="ACM_SCENE_COMPOSER",
            )
        finally:
            bpy.ops.object.select_all(action="DESELECT")
            for obj in previous_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if previous_active and previous_active.name in bpy.data.objects:
                context.view_layer.objects.active = previous_active

        settings.last_report = f"{summary} | EXPORTED {output}"
        self.report({"INFO"}, f"Exported {output.name}")
        return {"FINISHED"}


CLASSES = (
    ACM_OT_import_asset,
    ACM_OT_adopt_selected,
    ACM_OT_apply_layout,
    ACM_OT_update_face_qa,
    ACM_OT_add_text,
    ACM_OT_add_frame,
    ACM_OT_validate_asset,
    ACM_OT_export_asset,
)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
