# pipeline/export/exporter.py
# 📤 Export utilities
# - Writes STL and optional OBJ from mesh
# - Writes XYZ point cloud as text
# - Writes DXF with all points (for engraving workflows)

import os  # 📁 Path handling
import trimesh  # 🔺 Mesh export
import numpy as np  # 🧮 Point export
import ezdxf  # 📐 DXF writer


class Exporter:
    def write_all(self, mesh, xyz_points, outdir, write_obj=False):
        # 📁 Build output file paths
        stl_path = os.path.join(outdir, "model.stl")  # 🧊 Main 3D mesh
        obj_path = os.path.join(outdir, "model.obj")  # 🧊 Optional OBJ mesh
        xyz_path = os.path.join(outdir, "points.xyz")  # 🧊 XYZ point cloud
        dxf_path = os.path.join(outdir, "points.dxf")  # 🧊 DXF point list

        # 💾 Export STL
        mesh.export(stl_path)

        # 💾 Optional OBJ export
        if write_obj:
            mesh.export(obj_path)

        # 💾 Export XYZ points
        np.savetxt(xyz_path, xyz_points, fmt="%.3f")

        # 💾 Export DXF of points
        self._write_dxf(dxf_path, xyz_points)

    def _write_dxf(self, path, points):
        # 🧾 Create new DXF document in mm units
        doc = ezdxf.new()
        doc.header["$INSUNITS"] = 4  # 📏 4 = millimeters

        msp = doc.modelspace()  # 🧱 Model space handle
        for pt in points:
            msp.add_point(pt)  # 🔹 Add each point

        doc.saveas(path)  # 💾 Save DXF to disk
