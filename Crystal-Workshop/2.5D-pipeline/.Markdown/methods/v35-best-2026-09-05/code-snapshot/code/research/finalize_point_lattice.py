"""
Purpose: Convert an existing dense review cloud to an exact, unique XYZ point lattice.
Context: Original review and GLB remain unchanged; first contributing sample supplies colour.
"""
import argparse
import base64
import json
import shutil
from pathlib import Path

import numpy as np
import trimesh

from export_v35_point_review import encoded
from sample_relief_surface import quantize_point_lattice


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--id', required=True)
    p.add_argument('--label', required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    data = json.loads((args.input/'geometry.json').read_text())
    points = np.frombuffer(base64.b64decode(data['pointPositions']), dtype='<f4').reshape(-1,3).astype(float)
    colors = np.frombuffer(base64.b64decode(data['pointColors']), dtype='u1').reshape(-1,3)
    result, retained, stats = quantize_point_lattice(points, .00008, .00009)
    colors = colors[retained]
    gray = np.repeat(np.round(colors @ np.array([.2126,.7152,.0722])).astype('uint8')[:,None],3,axis=1)
    for name, color in [('points-color-mm.ply',colors),('points-gray-mm.ply',gray)]:
        trimesh.points.PointCloud(result*1000, colors=color).export(args.output/name)
        loaded = trimesh.load(args.output/name, process=False)
        assert np.allclose(loaded.vertices,result*1000,atol=5e-6)
        assert np.array_equal(loaded.colors[:,:3],color)
    data['pointPositions'],data['pointColors'] = encoded(result,'<f4'),encoded(colors,'u1')
    (args.output/'geometry.json').write_text(json.dumps(data),encoding='utf-8')
    shutil.copy2(args.input/'relief.glb',args.output/'relief.glb')
    report = json.loads((args.input/'manifest.json').read_text())
    report.update({'id':args.id,'label':args.label,'point_count':len(result),'pre_lattice_sample_count':len(points)})
    report['sampling'].update(stats)
    report['sampling']['points_after_layer_deduplication'] = len(result)
    report['sampling']['lattice_note'] = 'Exact 0.08 mm X/Y and 0.09 mm Z cells; one point per occupied cell; unchanged source GLB.'
    report['sampling']['max_axis_error_vs_original_surface_bound_mm'] = [.04,.04,.045]
    (args.output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'id':args.id,'points':len(result),'spacing':stats},indent=2))


if __name__=='__main__':
    main()
