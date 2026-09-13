"""
File: code/research/render_v35_comparison.py
Purpose:
 - Render relief candidates and references with shared orthographic QA cameras.
 - Normalize each imported subject to 80 mm tall for a stated shape comparison.
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mesh', action='append', required=True, help='label=path')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for entry in args.mesh:
        label, path = entry.split('=', 1)
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.import_scene.gltf(filepath=str(Path(path).resolve()))
        meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
        points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
        low = Vector([min(p[i] for p in points) for i in range(3)])
        high = Vector([max(p[i] for p in points) for i in range(3)])
        center = (low + high) * .5
        factor = .08 / (high.z - low.z)
        # Bake imported object transforms so legacy mm and standard m files agree.
        for obj in meshes:
            world = obj.matrix_world.copy()
            for vertex in obj.data.vertices:
                vertex.co = (world @ vertex.co - center) * factor
            obj.parent = None
            obj.matrix_world.identity()
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
        scene = bpy.context.scene
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.render.resolution_x = 600
        scene.render.resolution_y = 800
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.world.color = (.025, .03, .04)
        shading = scene.display.shading
        shading.light = 'STUDIO'
        shading.color_type = 'SINGLE'
        shading.single_color = (.64, .67, .70)
        shading.show_shadows = True
        shading.show_cavity = True
        shading.cavity_type = 'BOTH'
        shading.curvature_ridge_factor = 1.25
        shading.curvature_valley_factor = 1.0
        camera_data = bpy.data.cameras.new('Shared QA camera')
        camera_data.type = 'ORTHO'
        camera_data.ortho_scale = .096
        camera_data.clip_start = .001
        camera_data.clip_end = 10
        camera = bpy.data.objects.new('Shared QA camera', camera_data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        for angle in (0, 30, -30, 45, 90, -90):
            radians = math.radians(angle)
            camera.location = (.25 * math.sin(radians), -.25 * math.cos(radians), 0)
            camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
            scene.render.filepath = str((args.output_dir / f'{label}-{angle:+04d}.png').resolve())
            bpy.ops.render.render(write_still=True)
        shading.color_type = 'TEXTURE'
        camera.location = (0, -.25, 0)
        camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str((args.output_dir / f'{label}-texture.png').resolve())
        bpy.ops.render.render(write_still=True)
        manifest.append({'label': label, 'path': str(Path(path).resolve()), 'import_to_80mm_scale': factor})
    (args.output_dir / 'cameras.json').write_text(json.dumps({'height_m': .08, 'orthographic_scale': .096,
        'angles_degrees': [0, 30, -30, 45, 90, -90], 'elevation': 0, 'meshes': manifest}, indent=2))


if __name__ == '__main__':
    main()
