"""
File: tests/test_convert_model.py
Purpose:
 - Exercise common-format export, centimetre-to-mm sizing, slicing, printer DXF,
   and multi-output ZIP creation through the real headless Blender backend.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONVERTER = PROJECT_ROOT / "code" / "convert_model.py"


def write_cube_fixture(path):
    """Write a deterministic 2 x 2 x 2 triangulated OBJ test mesh."""
    path.write_text(
        "# ACM converter integration fixture\n"
        "o ACM_Test_Cube\n"
        "v -1 -1 -1\nv 1 -1 -1\nv 1 1 -1\nv -1 1 -1\n"
        "v -1 -1 1\nv 1 -1 1\nv 1 1 1\nv -1 1 1\n"
        "f 1 3 2\nf 1 4 3\nf 5 6 7\nf 5 7 8\n"
        "f 1 2 6\nf 1 6 5\nf 2 3 7\nf 2 7 6\n"
        "f 3 4 8\nf 3 8 7\nf 4 1 5\nf 4 5 8\n",
        encoding="utf-8",
    )


def blender_available():
    """Match the converter's ordinary PATH and local Windows discovery cases."""
    configured = os.environ.get("BLENDER_EXE")
    return bool(
        (configured and Path(configured).is_file())
        or shutil.which("blender")
        or Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe").is_file()
    )


@unittest.skipUnless(blender_available(), "Blender 4.3+ is required for integration conversion")
class ConvertModelIntegrationTest(unittest.TestCase):
    """Validate the complete conversion contract used by the Next.js route."""

    def test_multi_format_resize_slice_and_zip(self):
        with tempfile.TemporaryDirectory(prefix="acm-converter-test-") as temporary:
            fixture = Path(temporary) / "cube.obj"
            write_cube_fixture(fixture)
            command = [
                sys.executable,
                str(CONVERTER),
                "--file",
                str(fixture),
                "--out",
                temporary,
                "--formats",
                "glb",
                "gltf",
                "stl",
                "obj",
                "ply",
                "fbx",
                "usd",
                "usdz",
                "dxf",
                "--input-unit",
                "cm",
                "--fit-width",
                "20",
                "--fit-height",
                "30",
                "--fit-depth",
                "30",
                "--slice-axis",
                "x",
                "--slice-min",
                "-5",
                "--slice-max",
                "5",
                "--fill-cuts",
                "--spacing",
                "2",
                "--min-distance",
                "2",
                "--layer-spacing",
                "2",
                "--max-points",
                "5000",
                "--seed",
                "0",
            ]
            completed = subprocess.run(command, check=True, capture_output=True, text=True)
            sentinel = next(
                line for line in completed.stdout.splitlines() if line.startswith("ACM_CONVERTER_JOB=")
            )
            result = json.loads(sentinel.split("=", 1)[1])
            job_dir = Path(result["directory"])
            manifest = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))
            dimensions = manifest["processed"]["dimensions_mm"]

            self.assertAlmostEqual(dimensions["width"], 10.0, places=4)
            self.assertAlmostEqual(dimensions["height"], 20.0, places=4)
            self.assertAlmostEqual(dimensions["depth"], 20.0, places=4)
            self.assertEqual(manifest["input_unit"], "cm")
            self.assertIn("dimensions_source_units", manifest["imported_source"])

            extensions = {item["extension"] for item in result["files"]}
            self.assertTrue(
                {".glb", ".gltf", ".stl", ".obj", ".ply", ".fbx", ".usd", ".usdz", ".dxf", ".zip"}
                .issubset(extensions)
            )
            archive_path = next(job_dir / item["path"] for item in result["files"] if item["extension"] == ".zip")
            with zipfile.ZipFile(archive_path) as archive:
                self.assertTrue(any(name.endswith(".dxf") for name in archive.namelist()))

    def test_3dface_dxf_input_uses_original_output_name(self):
        with tempfile.TemporaryDirectory(prefix="acm-converter-dxf-test-") as temporary:
            source = Path(temporary) / "triangle-source.dxf"
            source.write_text(
                "0\nSECTION\n2\nENTITIES\n0\n3DFACE\n"
                "10\n0\n20\n0\n30\n0\n"
                "11\n10\n21\n0\n31\n0\n"
                "12\n0\n22\n10\n32\n0\n"
                "13\n0\n23\n10\n33\n0\n"
                "0\nENDSEC\n0\nEOF\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(CONVERTER),
                    "--file",
                    str(source),
                    "--out",
                    temporary,
                    "--formats",
                    "glb",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            sentinel = next(
                line for line in completed.stdout.splitlines() if line.startswith("ACM_CONVERTER_JOB=")
            )
            result = json.loads(sentinel.split("=", 1)[1])
            job_dir = Path(result["directory"])
            manifest = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["input_format"], "dxf")
            self.assertEqual(Path(manifest["source"]), source.resolve())
            self.assertTrue((job_dir / "triangle-source.glb").is_file())
            self.assertFalse((job_dir / ".acm-dxf-source.obj").exists())


if __name__ == "__main__":
    unittest.main()
