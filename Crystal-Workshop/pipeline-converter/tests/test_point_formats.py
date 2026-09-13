"""
File: tests/test_point_formats.py
Purpose:
 - Protect POINT-DXF parsing from mesh-entity false positives.
 - Verify that the existing point converter writes selected PLY output.
"""

import tempfile
import unittest
import sys
from pathlib import Path


CODE_DIR = Path(__file__).resolve().parents[1] / "code"
sys.path.insert(0, str(CODE_DIR))

from utils.parsers import parse_dxf_points_fast  # noqa: E402
from utils.writers import write_selected_formats  # noqa: E402


class PointFormatTest(unittest.TestCase):
    """Exercise lightweight point parsing and writing without Blender."""

    def test_dxf_parser_reads_points_but_ignores_3dface_coordinates(self):
        with tempfile.TemporaryDirectory(prefix="acm-point-parser-test-") as temporary:
            source = Path(temporary) / "mixed.dxf"
            source.write_text(
                "0\nSECTION\n2\nENTITIES\n"
                "0\nPOINT\n10\n1.25\n20\n2.5\n30\n3.75\n"
                "0\n3DFACE\n10\n100\n20\n200\n30\n300\n"
                "11\n101\n21\n201\n31\n301\n"
                "12\n102\n22\n202\n32\n302\n"
                "0\nENDSEC\n0\nEOF\n",
                encoding="utf-8",
            )

            self.assertEqual(parse_dxf_points_fast(source), [(1.25, 2.5, 3.75)])

    def test_selected_ply_output_is_written(self):
        with tempfile.TemporaryDirectory(prefix="acm-ply-writer-test-") as temporary:
            project_root = Path(temporary)
            outputs = write_selected_formats(
                [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)],
                "points",
                ["ply"],
                project_root,
            )

            ply_path = outputs["ply"]
            self.assertTrue(ply_path.is_file())
            self.assertIn("element vertex 2", ply_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
