"""
File: blender_addons/acm_scene_composer/properties.py
Purpose:
 - Define persistent project, input, composition and quality-control settings.
"""

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup


INPUT_TYPES = (
    (
        "ACM_RELIEF_2_5D",
        "ACM 2.5D Relief",
        "A completed textured relief from the native MoGe and face-refinement pipeline",
    ),
    (
        "MESHY_FULL_3D",
        "Meshy Full 3D",
        "A complete full-3D Meshy asset; geometry remains full 3D",
    ),
)

APPEARANCE_VARIANTS = (
    ("CRYSTAL_TONE", "Crystal tone", "Monochrome AC3D-style appearance GLB"),
    ("RGB", "RGB", "Full-colour identity inspection GLB"),
    ("GEOMETRY_ONLY", "Geometry only", "No photographic appearance is expected"),
)

FACE_STATES = (
    ("NOT_APPLICABLE", "Not applicable", "The asset contains no human faces"),
    ("PENDING", "FaceBuilder pending", "At least one face still requires FaceBuilder and review"),
    ("COMPLETE", "FaceBuilder complete", "Every detected face has completed FaceBuilder review"),
)

RELIEF_DEPTH_PROFILES = (
    ("SHALLOW", "Shallow", "Up to 8 mm or 20% of usable crystal depth"),
    ("BALANCED", "Balanced", "Up to 16 mm or 40% of usable crystal depth"),
    ("DEEP", "Deep", "Up to 24 mm or 60% of usable crystal depth"),
    ("CUSTOM", "Custom", "Use the exact custom millimetre depth"),
)


class ACMSceneComposerSettings(PropertyGroup):
    """One scene-level control surface for the active ACM composition."""

    project_name: StringProperty(
        name="Project",
        default="ACM Composition",
        description="Human-readable name stored with imported assets",
    )
    input_type: EnumProperty(name="Input type", items=INPUT_TYPES, default="ACM_RELIEF_2_5D")
    appearance_variant: EnumProperty(
        name="Appearance",
        items=APPEARANCE_VARIANTS,
        default="CRYSTAL_TONE",
        description="Which visual version of the unchanged relief geometry is being imported",
    )
    input_path: StringProperty(
        name="Input file",
        subtype="FILE_PATH",
        description="Textured GLB/GLTF or supported interchange file",
    )
    source_image_path: StringProperty(
        name="Source image",
        subtype="FILE_PATH",
        description="Optional original photograph retained as provenance",
    )
    active_asset_id: StringProperty(name="Active ACM asset", options={"HIDDEN"})

    face_count: IntProperty(
        name="Human faces",
        default=0,
        min=0,
        description="Number of human faces that require individual FaceBuilder review",
    )
    face_refinement_state: EnumProperty(
        name="Face refinement",
        items=FACE_STATES,
        default="NOT_APPLICABLE",
    )
    enforce_face_refinement: BoolProperty(
        name="Block final export until complete",
        default=True,
        description="Prevent final GLB export while a required FaceBuilder review is pending",
    )

    target_height_mm: FloatProperty(
        name="Target height",
        default=100.0,
        min=0.1,
        unit="LENGTH",
        description="Uniformly scale the active asset to this height in ACM millimetres",
    )
    crystal_depth_mm: FloatProperty(
        name="Crystal depth",
        default=40.0,
        min=1.0,
        unit="LENGTH",
        description="Physical front-to-back depth of the selected crystal template",
    )
    crystal_margin_mm: FloatProperty(
        name="Depth margin per side",
        default=1.0,
        min=0.0,
        unit="LENGTH",
    )
    relief_depth_profile: EnumProperty(
        name="Relief depth profile",
        items=RELIEF_DEPTH_PROFILES,
        default="BALANCED",
    )
    custom_relief_depth_mm: FloatProperty(
        name="Custom relief depth",
        default=16.0,
        min=0.1,
        unit="LENGTH",
    )
    placement: FloatVectorProperty(
        name="Position",
        size=3,
        subtype="TRANSLATION",
        default=(0.0, 0.0, 0.0),
        description="Asset-root position using ACM X/Y/Z coordinates",
    )
    rotation: FloatVectorProperty(
        name="Rotation",
        size=3,
        subtype="EULER",
        default=(0.0, 0.0, 0.0),
        description="Non-destructive rotation applied only to the asset root",
    )

    text_body: StringProperty(name="Text", default="Arctic Crystal Memories")
    text_size_mm: FloatProperty(name="Text size", default=8.0, min=0.1, unit="LENGTH")
    text_depth_mm: FloatProperty(name="Text depth", default=1.0, min=0.0, unit="LENGTH")
    text_position: FloatVectorProperty(
        name="Text position",
        size=3,
        subtype="TRANSLATION",
        default=(0.0, -45.0, 0.0),
    )

    frame_width_mm: FloatProperty(name="Frame width", default=80.0, min=1.0, unit="LENGTH")
    frame_height_mm: FloatProperty(name="Frame height", default=110.0, min=1.0, unit="LENGTH")
    frame_depth_mm: FloatProperty(name="Frame depth", default=2.0, min=0.01, unit="LENGTH")
    frame_bar_mm: FloatProperty(name="Frame bar", default=3.0, min=0.1, unit="LENGTH")
    frame_bevel_mm: FloatProperty(name="Frame bevel", default=0.5, min=0.0, unit="LENGTH")

    export_path: StringProperty(name="Final GLB", subtype="FILE_PATH")
    last_report: StringProperty(name="Last validation", default="No asset validated yet")


CLASSES = (ACMSceneComposerSettings,)


def register() -> None:
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.acm_composer = PointerProperty(type=ACMSceneComposerSettings)


def unregister() -> None:
    del bpy.types.Scene.acm_composer
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
