"""
Purpose:
 - Verify triangle GLB/STL equivalence, projection colors, and bounded sampling.
 - Ensure scene photo extraction never depends on the opaque CI member.
"""
import json
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

import numpy as np
from PIL import Image
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from utils.writers import reconstruct_mesh, write_glb, write_stl
from utils.photo_projection import vertex_colors
from utils.parsers import parse_dxf_points_fast
from utils.relief_surface import reconstruct_relief, repair_lower_depth


class ReconstructionTests(unittest.TestCase):
    def test_stronger_lower_repair_reaches_wider_ridges(self):
        grid = np.zeros((128, 128))
        grid[20:29, 25:100] = 15
        grid[85:90, 25:100] = 15
        valid = np.ones_like(grid, dtype=bool)
        normal = repair_lower_depth(grid, valid)
        stronger = repair_lower_depth(grid, valid, strength=2.5)
        self.assertLess(stronger[24, 60], normal[24, 60])
        np.testing.assert_array_equal(stronger[54:], grid[54:])
        self.assertGreaterEqual(stronger.min(), -1e-12)

    def test_lower_repair_preserves_upper_geometry_exactly(self):
        grid = np.zeros((128, 128))
        grid[20:24, 25:100] = 15
        grid[85:90, 25:100] = 15
        repaired = repair_lower_depth(grid, np.ones_like(grid, dtype=bool))
        np.testing.assert_array_equal(repaired[54:], grid[54:])
        self.assertLess(repaired[22, 60], 8)
        self.assertGreaterEqual(repaired.min(), -1e-12)

    def test_continuous_relief_removes_depth_layers(self):
        x, y = np.meshgrid(np.linspace(-2, 2, 65), np.linspace(-2, 2, 65))
        z = 2 - 0.2 * (x * x + y * y)
        points = np.concatenate([np.column_stack((x.ravel(), y.ravel(), z.ravel() - layer * 0.08)) for layer in range(8)])
        vertices, faces = reconstruct_relief(points, resolution=65, smoothing=1, gap=0, max_vertices=5000)
        expected = 2 - 0.2 * (vertices[:, 0] ** 2 + vertices[:, 1] ** 2)
        self.assertLess(np.sqrt(np.mean((vertices[:, 2] - expected) ** 2)), 0.10)
        self.assertLessEqual(len(vertices), 5000)
        self.assertGreater(len(faces), 7000)

    def test_continuous_relief_does_not_bridge_separate_subjects(self):
        points = [(x, y, 0.1 * y) for x in np.linspace(-3, 3, 97) for y in np.linspace(-1, 1, 33) if abs(x) > 1]
        vertices, faces = reconstruct_relief(points, resolution=97, gap=1, smoothing=1)
        spans = np.ptp(vertices[faces, 0], axis=1)
        self.assertLess(spans.max(), 0.1)

    def test_shared_mesh_exports_triangles_in_meters(self):
        points = [(x, y, 0.1 * x * y) for x in range(8) for y in range(8)]
        mesh = reconstruct_mesh(points, stl_limit=30)
        self.assertEqual(len(mesh[0]), 30)
        with TemporaryDirectory() as directory:
            glb, stl = Path(directory) / "mesh.glb", Path(directory) / "mesh.stl"
            write_glb(mesh, glb)
            write_stl(points, stl, mesh=mesh)
            raw = glb.read_bytes()
            length = struct.unpack_from("<I", raw, 12)[0]
            document = json.loads(raw[20:20 + length])
            self.assertEqual(document["meshes"][0]["primitives"][0].get("mode", 4), 4)
            loaded = trimesh.load(glb, force="mesh", process=False)
            comparison = trimesh.load(stl, force="mesh", process=False)
            self.assertEqual(len(loaded.faces), len(comparison.faces))
            np.testing.assert_allclose(loaded.bounds * 1000, comparison.bounds, atol=1e-5)

    def test_photo_corners_and_scene_without_ci(self):
        points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=float)
        with TemporaryDirectory() as directory:
            image = Path(directory) / "photo.png"
            Image.fromarray(np.array([[[255, 0, 0], [0, 255, 0]], [[0, 0, 255], [255, 255, 255]]], dtype=np.uint8)).save(image)
            scene = Path(directory) / "photo.cockpit"
            with ZipFile(scene, "w") as archive:
                archive.writestr("CockpitScene.xml", '<Scene><SolidEntity Texture="photo.png" Geometry="absent.ci"/><ProjectionSetting Direction="Z" Enabled="True"/></Scene>')
                archive.write(image, "photo.png")
            colors = vertex_colors(points, scene)
            np.testing.assert_array_equal(colors[0], [0, 0, 255, 255])
            np.testing.assert_array_equal(colors[2], [255, 0, 0, 255])
            np.testing.assert_array_equal(vertex_colors(points, image, flip_u=True)[0], colors[1])
            textured = Path(directory) / "textured.glb"
            write_glb(reconstruct_mesh(points), textured, image, "xy", color_mode="texture")
            raw = textured.read_bytes()
            length = struct.unpack_from("<I", raw, 12)[0]
            document = json.loads(raw[20:20 + length])
            self.assertIn("TEXCOORD_0", document["meshes"][0]["primitives"][0]["attributes"])
            self.assertEqual(len(document["images"]), 1)

    def test_stream_sample_spans_source(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "cloud.dxf"
            source.write_text("0\nSECTION\n2\nENTITIES\n" + "".join(f"0\nPOINT\n10\n{i}\n20\n{i}\n30\n0\n" for i in range(20)) + "0\nENDSEC\n0\nEOF\n")
            points = parse_dxf_points_fast(source, sample_rate=4)
            self.assertEqual([point[0] for point in points], [3, 7, 11, 15, 19])

    def test_empty_cloud_is_actionable(self):
        with self.assertRaisesRegex(ValueError, "three finite"):
            reconstruct_mesh([])


if __name__ == "__main__":
    unittest.main()
