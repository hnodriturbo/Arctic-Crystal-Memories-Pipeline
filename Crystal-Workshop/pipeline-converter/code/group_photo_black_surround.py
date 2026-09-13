"""
Purpose: Create a preview-only black surround joined to the approved relief boundary.
Context: The original textured geometry is preserved; the surround is not SSLE data.
"""
from pathlib import Path
from datetime import datetime, timezone
import json
import numpy as np
import trimesh
from scipy.ndimage import convolve


def main():
    """Fill missing grid faces rather than place an opaque plane behind the model."""
    folder = Path(__file__).resolve().parents[1] / 'output/cockpit-reconstruct'
    source = folder / '20260913-123218-1613fba3.glb'
    model = trimesh.load(source, force='mesh', process=False)
    xs, ys = np.unique(model.vertices[:, 0]), np.unique(model.vertices[:, 1])
    width, height = len(xs), len(ys)
    ix = np.searchsorted(xs, model.vertices[:, 0])
    iy = np.searchsorted(ys, model.vertices[:, 1])
    ids = iy * width + ix
    measured = np.zeros((height, width), dtype=bool)
    measured[iy, ix] = True
    depth = np.zeros((height, width))
    depth[iy, ix] = model.vertices[:, 2]
    kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]]) / 4
    # Interpolate the black area toward the central plane while anchoring its seam.
    for _ in range(300):
        average = convolve(depth, kernel, mode='constant', cval=0)
        depth[~measured] = average[~measured]
    xx, yy = np.meshgrid(xs, ys)
    vertices = np.column_stack((xx.ravel(), yy.ravel(), depth.ravel()))
    grid = np.arange(width * height).reshape(height, width)
    a, b, c, d = grid[:-1, :-1], grid[:-1, 1:], grid[1:, :-1], grid[1:, 1:]
    faces = np.concatenate((np.stack((a, b, c), -1).reshape(-1, 3),
                            np.stack((b, d, c), -1).reshape(-1, 3)))
    # Compare canonical triangle IDs so no black face covers an existing photo face.
    keys = lambda f: np.sort(f, axis=1).astype(np.int64) @ np.array([width * height, 1, (width * height) ** 2], dtype=np.int64)
    faces = faces[~np.isin(keys(faces), keys(ids[model.faces]))]
    used, inverse = np.unique(faces, return_inverse=True)
    surround = trimesh.Trimesh(vertices[used], inverse.reshape(-1, 3), process=False)
    surround.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
        name='Preview only black surround', baseColorFactor=[0, 0, 0, 255],
        metallicFactor=0, roughnessFactor=1, doubleSided=True))
    scene = trimesh.Scene()
    scene.add_geometry(model, geom_name='Group_Photo', node_name='Group_Photo')
    scene.add_geometry(surround, geom_name='Preview_Only_Surround', node_name='Preview_Only_Surround')
    name = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '-group-photo-connected-surround'
    path = folder / (name + '.glb')
    scene.export(path, file_type='glb')
    check = trimesh.load(path, force='scene', process=False).geometry['Group_Photo']
    assert np.array_equal(check.vertices, model.vertices)
    assert np.array_equal(check.faces, model.faces)
    assert np.array_equal(np.asarray(check.visual.material.baseColorTexture), np.asarray(model.visual.material.baseColorTexture))
    report = {'jobId': name, 'sourceGlb': source.name, 'previewOnly': True,
              'geometryAndTextureUnchanged': True, 'surroundTriangles': len(faces),
              'method': 'Missing XY grid triangles, boundary-anchored depth fading to Z=0; visual approximation',
              'files': {'glb': 'cockpit-reconstruct/' + path.name}}
    (folder / (name + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
