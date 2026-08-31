"""
File: blender_addons/acm_scene_composer/__init__.py
Purpose:
 - Register the ACM Scene Composer Blender extension.
 - Keep 2.5D relief and Meshy full-3D inputs as distinct, non-destructive modes.
"""

bl_info = {
    "name": "ACM Scene Composer",
    "author": "Arctic Crystal Memories",
    "version": (0, 2, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar > ACM Composer",
    "description": "Compose ACM 2.5D relief and Meshy full-3D assets",
    "category": "3D View",
}

from . import operators, panels, properties


MODULES = (properties, operators, panels)


def register() -> None:
    """Register property, operator and panel classes in dependency order."""
    for module in MODULES:
        module.register()


def unregister() -> None:
    """Unregister in reverse order so panels never reference missing properties."""
    for module in reversed(MODULES):
        module.unregister()


if __name__ == "__main__":
    register()
