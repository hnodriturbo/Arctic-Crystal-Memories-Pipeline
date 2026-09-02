"""
File: code/blender_model_io.py
Purpose:
 - Run inside Blender to import, inspect, size, slice, and export common 3D meshes.
 - Keep Blender-specific APIs isolated from the lightweight converter environment.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


UNIT_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}


def parse_arguments():
    """Read arguments after Blender's `--` separator."""
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Blender-backed ACM model conversion worker.")
    parser.add_argument("--file", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--output-stem")
    parser.add_argument("--formats", nargs="+", required=True)
    parser.add_argument("--input-unit", choices=sorted(UNIT_TO_MM), default="mm")
    parser.add_argument("--fit-width", type=float, default=0.0)
    parser.add_argument("--fit-height", type=float, default=0.0)
    parser.add_argument("--fit-depth", type=float, default=0.0)
    parser.add_argument("--placement", choices=["keep", "center", "ground"], default="center")
    parser.add_argument("--slice-axis", choices=["none", "x", "y", "z"], default="none")
    parser.add_argument("--slice-min", type=float)
    parser.add_argument("--slice-max", type=float)
    parser.add_argument("--fill-cuts", action="store_true")
    parser.add_argument("--stage-obj")
    parser.add_argument("--manifest", required=True)
    return parser.parse_args(arguments)


def clear_scene():
    """Remove factory objects before importing a non-BLEND source."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_model(source):
    """Import one supported model without executing embedded Python."""
    extension = source.suffix.lower()
    if extension == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
        return

    clear_scene()
    if extension == ".obj":
        bpy.ops.wm.obj_import(filepath=str(source))
    elif extension == ".stl":
        bpy.ops.wm.stl_import(filepath=str(source))
    elif extension == ".ply":
        bpy.ops.wm.ply_import(filepath=str(source))
    elif extension in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(source))
    elif extension == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(source))
    elif extension == ".dae":
        bpy.ops.wm.collada_import(filepath=str(source))
    elif extension in {".usd", ".usda", ".usdc", ".usdz"}:
        bpy.ops.wm.usd_import(filepath=str(source))
    else:
        raise ValueError(f"Unsupported Blender input format: {extension}")


def join_meshes():
    """Apply evaluated geometry and join every imported mesh into one editable object."""
    mesh_objects = [item for item in bpy.context.scene.objects if item.type == "MESH"]
    if not mesh_objects:
        raise ValueError("The file contains no mesh objects.")

    bpy.ops.object.select_all(action="DESELECT")
    for item in mesh_objects:
        item.hide_set(False)
        item.hide_viewport = False
        item.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.convert(target="MESH")
    if len([item for item in bpy.context.selected_objects if item.type == "MESH"]) > 1:
        bpy.ops.object.join()
    model = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return model


def bounds(model):
    """Return world-space bounds and dimensions in the current millimetre coordinate system."""
    corners = [model.matrix_world @ Vector(corner) for corner in model.bound_box]
    minimum = [min(point[index] for point in corners) for index in range(3)]
    maximum = [max(point[index] for point in corners) for index in range(3)]
    dimensions = [maximum[index] - minimum[index] for index in range(3)]
    return minimum, maximum, dimensions


def apply_units_and_fit(model, args):
    """Convert the declared source units to mm and uniformly fit requested dimensions."""
    unit_scale = UNIT_TO_MM[args.input_unit]
    model.scale = (unit_scale, unit_scale, unit_scale)
    bpy.context.view_layer.objects.active = model
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    _, _, dimensions = bounds(model)
    targets = [args.fit_width, args.fit_height, args.fit_depth]
    ratios = [target / size for target, size in zip(targets, dimensions) if target > 0 and size > 0]
    fit_scale = min(ratios) if ratios else 1.0
    if not math.isclose(fit_scale, 1.0):
        model.scale = (fit_scale, fit_scale, fit_scale)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return unit_scale, fit_scale


def place_model(model, placement):
    """Place the converted geometry predictably without changing its dimensions."""
    minimum, maximum, _ = bounds(model)
    if placement == "center":
        offset = [-(minimum[index] + maximum[index]) / 2.0 for index in range(3)]
    elif placement == "ground":
        offset = [-(minimum[0] + maximum[0]) / 2.0, -(minimum[1] + maximum[1]) / 2.0, -minimum[2]]
    else:
        return
    model.location = Vector(offset)
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


def bisect_model(model, axis, boundary, keep_above, fill):
    """Bisect at one absolute millimetre coordinate and discard one side."""
    index = {"x": 0, "y": 1, "z": 2}[axis]
    plane_co = [0.0, 0.0, 0.0]
    plane_no = [0.0, 0.0, 0.0]
    plane_co[index] = boundary
    plane_no[index] = 1.0

    bpy.context.view_layer.objects.active = model
    model.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(
        plane_co=plane_co,
        plane_no=plane_no,
        clear_inner=keep_above,
        clear_outer=not keep_above,
        use_fill=fill,
    )
    bpy.ops.object.mode_set(mode="OBJECT")


def export_model(model, output_dir, stem, formats):
    """Export the selected processed mesh and return paths created by each format."""
    bpy.ops.object.select_all(action="DESELECT")
    model.select_set(True)
    bpy.context.view_layer.objects.active = model
    written = []

    for format_name in formats:
        target = output_dir / f"{stem}.{format_name}"
        if format_name == "obj":
            bpy.ops.wm.obj_export(filepath=str(target), export_selected_objects=True, path_mode="COPY")
        elif format_name == "stl":
            bpy.ops.wm.stl_export(filepath=str(target), export_selected_objects=True)
        elif format_name == "ply":
            bpy.ops.wm.ply_export(filepath=str(target), export_selected_objects=True)
        elif format_name == "glb":
            bpy.ops.export_scene.gltf(filepath=str(target), export_format="GLB", use_selection=True)
        elif format_name == "gltf":
            bpy.ops.export_scene.gltf(filepath=str(target), export_format="GLTF_SEPARATE", use_selection=True)
        elif format_name == "fbx":
            bpy.ops.export_scene.fbx(filepath=str(target), use_selection=True, bake_anim=False)
        elif format_name in {"usd", "usdz"}:
            bpy.ops.wm.usd_export(filepath=str(target), selected_objects_only=True)
        else:
            raise ValueError(f"Unsupported Blender output format: {format_name}")
        written.append(str(target))
    return written


def model_statistics(model, coordinate_space="mm"):
    """Collect simple geometry facts and label the coordinate space honestly."""
    minimum, maximum, dimensions = bounds(model)
    mesh = model.data
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "triangles": sum(max(len(polygon.vertices) - 2, 0) for polygon in mesh.polygons),
        f"bounds_{coordinate_space}": {"min": minimum, "max": maximum},
        f"dimensions_{coordinate_space}": {
            "width": dimensions[0],
            "height": dimensions[1],
            "depth": dimensions[2],
        },
    }


def main():
    args = parse_arguments()
    source = Path(args.file).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    import_model(source)
    model = join_meshes()
    imported = model_statistics(model, coordinate_space="source_units")
    unit_scale, fit_scale = apply_units_and_fit(model, args)
    place_model(model, args.placement)

    if args.slice_axis != "none":
        if args.slice_min is not None:
            bisect_model(model, args.slice_axis, args.slice_min, keep_above=True, fill=args.fill_cuts)
        if args.slice_max is not None:
            bisect_model(model, args.slice_axis, args.slice_max, keep_above=False, fill=args.fill_cuts)

    processed = model_statistics(model)
    if processed["vertices"] == 0 or processed["polygons"] == 0:
        raise ValueError("The requested slice removed all mesh geometry.")

    standard_formats = [item for item in args.formats if item != "dxf"]
    export_model(model, output_dir, args.output_stem or source.stem, standard_formats)
    if args.stage_obj:
        bpy.ops.wm.obj_export(filepath=str(Path(args.stage_obj).resolve()), export_selected_objects=True)

    manifest = {
        "source": str(source),
        "input_format": source.suffix.lower().lstrip("."),
        "input_unit": args.input_unit,
        "unit_scale_to_mm": unit_scale,
        "uniform_fit_scale": fit_scale,
        "placement": args.placement,
        "slice": {"axis": args.slice_axis, "min_mm": args.slice_min, "max_mm": args.slice_max},
        "imported_source": imported,
        "processed": processed,
        "blender_version": bpy.app.version_string,
    }
    Path(args.manifest).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("ACM_BLENDER_MANIFEST=" + json.dumps(manifest, separators=(",", ":")))


if __name__ == "__main__":
    main()
