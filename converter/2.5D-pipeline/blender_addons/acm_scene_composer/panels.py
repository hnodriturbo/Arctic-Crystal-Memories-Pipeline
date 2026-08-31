"""
File: blender_addons/acm_scene_composer/panels.py
Purpose:
 - Present the ACM Scene Composer workflow in Blender's 3D View sidebar.
"""

import bpy
from bpy.types import Panel

from . import utils


class ACM_PT_composer(Panel):
    bl_idname = "ACM_PT_composer"
    bl_label = "ACM Scene Composer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ACM Composer"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.acm_composer
        layout.prop(settings, "project_name")
        layout.label(text="X width / Y height / Z front depth", icon="ORIENTATION_GLOBAL")


class ACM_PT_input(Panel):
    bl_idname = "ACM_PT_input"
    bl_label = "1. Input"
    bl_parent_id = "ACM_PT_composer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.acm_composer
        layout.prop(settings, "input_type", expand=True)
        if settings.input_type == "ACM_RELIEF_2_5D":
            layout.prop(settings, "appearance_variant", expand=True)
        layout.prop(settings, "input_path")
        layout.prop(settings, "source_image_path")
        row = layout.row(align=True)
        row.operator("acm.import_asset", icon="IMPORT")
        row.operator("acm.adopt_selected", icon="OUTLINER_OB_EMPTY")

        box = layout.box()
        if settings.input_type == "ACM_RELIEF_2_5D":
            box.label(text="Accepts completed ACM relief geometry", icon="MESH_GRID")
            box.label(text="No depth generation occurs inside Composer")
        else:
            box.label(text="Preserves the complete Meshy model", icon="MESH_MONKEY")
            box.label(text="No cutting or relief compression")


class ACM_PT_face_qa(Panel):
    bl_idname = "ACM_PT_face_qa"
    bl_label = "2. FaceBuilder QA"
    bl_parent_id = "ACM_PT_composer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.acm_composer
        layout.prop(settings, "face_count")
        layout.prop(settings, "face_refinement_state")
        layout.prop(settings, "enforce_face_refinement")
        layout.operator("acm.update_face_qa", icon="CHECKMARK")
        if settings.face_count > 0 and settings.face_refinement_state != "COMPLETE":
            layout.label(text="Final export is blocked", icon="ERROR")


class ACM_PT_layout(Panel):
    bl_idname = "ACM_PT_layout"
    bl_label = "3. Asset Layout"
    bl_parent_id = "ACM_PT_composer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.acm_composer
        root = utils.find_asset_root(context)
        layout.label(text=root.name if root else "No active ACM asset", icon="EMPTY_ARROWS")
        layout.prop(settings, "target_height_mm")
        if settings.input_type == "ACM_RELIEF_2_5D":
            depth_box = layout.box()
            depth_box.label(text="Crystal-bounded relief depth", icon="MOD_DISPLACE")
            depth_box.prop(settings, "crystal_depth_mm")
            depth_box.prop(settings, "crystal_margin_mm")
            depth_box.prop(settings, "relief_depth_profile")
            if settings.relief_depth_profile == "CUSTOM":
                depth_box.prop(settings, "custom_relief_depth_mm")
        layout.prop(settings, "placement")
        layout.prop(settings, "rotation")
        layout.operator("acm.apply_layout", icon="OBJECT_ORIGIN")


class ACM_PT_components(Panel):
    bl_idname = "ACM_PT_components"
    bl_label = "4. Text and Frame"
    bl_parent_id = "ACM_PT_composer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.acm_composer

        text_box = layout.box()
        text_box.label(text="Editable text", icon="FONT_DATA")
        text_box.prop(settings, "text_body")
        text_box.prop(settings, "text_size_mm")
        text_box.prop(settings, "text_depth_mm")
        text_box.prop(settings, "text_position")
        text_box.operator("acm.add_text", icon="ADD")

        frame_box = layout.box()
        frame_box.label(text="Rectangular frame", icon="MESH_CUBE")
        frame_box.prop(settings, "frame_width_mm")
        frame_box.prop(settings, "frame_height_mm")
        frame_box.prop(settings, "frame_depth_mm")
        frame_box.prop(settings, "frame_bar_mm")
        frame_box.prop(settings, "frame_bevel_mm")
        frame_box.operator("acm.add_frame", icon="ADD")


class ACM_PT_export(Panel):
    bl_idname = "ACM_PT_export"
    bl_label = "5. Validate and Export"
    bl_parent_id = "ACM_PT_composer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.acm_composer
        layout.operator("acm.validate_asset", icon="VIEWZOOM")
        box = layout.box()
        box.label(text=settings.last_report, icon="INFO")
        layout.prop(settings, "export_path")
        layout.operator("acm.export_asset", icon="EXPORT")


CLASSES = (
    ACM_PT_composer,
    ACM_PT_input,
    ACM_PT_face_qa,
    ACM_PT_layout,
    ACM_PT_components,
    ACM_PT_export,
)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
