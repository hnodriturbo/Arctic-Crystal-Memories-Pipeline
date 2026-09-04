"""
File: code/research/build_glb_from_cockpit.py
Purpose:
 - Extract one SolidEntity from a local `.cockpit` ZIP, decode its CIBF/CRUN
   `.ci` mesh with the installed Cockpit reader, and export a standard GLB.

Important context:
 - Inputs are read-only; every extracted or generated artifact is written to
   a separate output directory.
 - This is an interoperability research bridge, not a `.cockpit` writer.
 - The scene transform is applied in millimetres so the GLB matches Cockpit's
   scene placement and scale as closely as the documented XML permits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

import numpy as np
import trimesh
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_EXTRACTOR = SCRIPT_DIR / "extract_cockpit_ci_mesh.ps1"
DEFAULT_X86_POWERSHELL = Path("C:/Windows/SysWOW64/WindowsPowerShell/v1.0/powershell.exe")


def sha256(path: Path) -> str:
    """Return a stable lowercase SHA-256 for one artifact."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_member_name(name: str) -> str:
    """Reject absolute or traversal paths before extracting an archive member."""

    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts or not member.name or name.endswith("/"):
        raise ValueError(f"Unsafe archive member: {name}")
    return member.name


def required_attribute(element: ElementTree.Element, name: str) -> str:
    """Read one required XML attribute with a useful failure message."""

    value = element.get(name)
    if not value:
        raise ValueError(f"SolidEntity is missing required attribute: {name}")
    return value


def vector3(element: ElementTree.Element, prefix: str, default: float) -> np.ndarray:
    """Read an XYZ triplet such as ScaleX/ScaleY/ScaleZ."""

    return np.asarray(
        [float(element.get(f"{prefix}{axis}", str(default))) for axis in "XYZ"],
        dtype=np.float64,
    )


def xyz_euler_matrix(degrees: np.ndarray) -> np.ndarray:
    """Build an XYZ Euler rotation matrix from Cockpit's degree values."""

    x, y, z = np.radians(degrees)
    cx, sx = math.cos(x), math.sin(x)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(z), math.sin(z)
    rotation_x = np.asarray([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    rotation_y = np.asarray([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    rotation_z = np.asarray([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return rotation_z @ rotation_y @ rotation_x


def extract_scene_assets(cockpit_path: Path, output_dir: Path) -> dict:
    """Extract the scene XML and referenced geometry/texture/mask only."""

    source_dir = output_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(cockpit_path, "r") as archive:
        members = {member.filename: member for member in archive.infolist()}
        scene_member = members.get("CockpitScene.xml")
        if scene_member is None:
            raise ValueError("CockpitScene.xml is missing from the archive")

        scene_bytes = archive.read(scene_member)
        root = ElementTree.fromstring(scene_bytes)
        solid = root.find("./Entities/SolidEntity")
        if solid is None:
            raise ValueError("No SolidEntity was found in CockpitScene.xml")

        references = {
            "geometry": required_attribute(solid, "Geometry"),
            "texture": required_attribute(solid, "Texture"),
        }
        if solid.get("Mask"):
            references["mask"] = required_attribute(solid, "Mask")

        extracted = {}
        scene_path = source_dir / "CockpitScene.xml"
        scene_path.write_bytes(scene_bytes)
        extracted["scene"] = scene_path

        for label, archive_name in references.items():
            if archive_name not in members:
                raise ValueError(f"Referenced {label} is missing: {archive_name}")
            target = source_dir / safe_member_name(archive_name)
            with archive.open(members[archive_name], "r") as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            extracted[label] = target

    template = root.find("./Template")
    return {
        "paths": extracted,
        "solid": solid,
        "template": template,
    }


def decode_ci(ci_path: Path, output_dir: Path, force: bool) -> tuple[Path, dict]:
    """Run the 32-bit local decoder and return its raw buffer and metadata."""

    raw_path = output_dir / "decoded-ci-buffer.bin"
    metadata_path = output_dir / "decoded-ci-buffer.json"
    command = [
        str(DEFAULT_X86_POWERSHELL),
        "-NoProfile",
        "-STA",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(DEFAULT_EXTRACTOR),
        "-InputCi",
        str(ci_path),
        "-OutputRaw",
        str(raw_path),
        "-MetadataPath",
        str(metadata_path),
    ]
    if force:
        command.append("-Force")

    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "Cockpit CI decoding failed")

    return raw_path, json.loads(metadata_path.read_text(encoding="utf-8-sig"))


def load_decoded_mesh(raw_path: Path, metadata: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split the neutral raw buffer into position, UV, normal, and face arrays."""

    vertex_count = int(metadata["vertexCount"])
    floats_per_vertex = int(metadata["floatsPerVertex"])
    index_count = int(metadata["indexCount"])
    if floats_per_vertex != 8:
        raise ValueError(f"Unsupported CI vertex layout width: {floats_per_vertex}")

    vertex_float_count = vertex_count * floats_per_vertex
    expected_bytes = (vertex_float_count + index_count) * 4
    if raw_path.stat().st_size != expected_bytes:
        raise ValueError("Decoded buffer size does not match its metadata")

    data = np.memmap(raw_path, mode="r", dtype="<f4", shape=(vertex_float_count,))
    records = np.asarray(data).reshape(vertex_count, floats_per_vertex)
    positions = records[:, 0:3].astype(np.float64, copy=True)
    uv = records[:, 3:5].astype(np.float64, copy=True)
    normals = records[:, 5:8].astype(np.float64, copy=True)

    indices = np.memmap(
        raw_path,
        mode="r",
        dtype="<i4",
        offset=vertex_float_count * 4,
        shape=(index_count,),
    )
    faces = np.asarray(indices).reshape(-1, 3).astype(np.int64, copy=True)
    if faces.min() < 0 or faces.max() >= vertex_count:
        raise ValueError("Decoded triangle indices fall outside the vertex buffer")
    return positions, uv, normals, faces


def transform_to_scene_mm(positions: np.ndarray, normals: np.ndarray, solid: ElementTree.Element) -> tuple[np.ndarray, np.ndarray, dict]:
    """Apply Cockpit's internal centring followed by scene scale/rotation/position."""

    raw_min = positions.min(axis=0)
    raw_max = positions.max(axis=0)
    raw_center = (raw_min + raw_max) / 2.0
    scale = vector3(solid, "Scale", 1.0)
    eulers = vector3(solid, "Eulers", 0.0)
    position = vector3(solid, "Position", 0.0)
    rotation = xyz_euler_matrix(eulers)

    scene_positions = ((positions - raw_center) * scale) @ rotation.T + position
    normal_matrix = np.linalg.inv(rotation @ np.diag(scale)).T
    scene_normals = normals @ normal_matrix.T
    lengths = np.linalg.norm(scene_normals, axis=1)
    valid = lengths > 1e-12
    scene_normals[valid] /= lengths[valid, None]

    transform_report = {
        "rawBounds": {"min": raw_min.tolist(), "max": raw_max.tolist(), "center": raw_center.tolist()},
        "sceneTransform": {
            "scale": scale.tolist(),
            "eulersDegrees": eulers.tolist(),
            "positionMm": position.tolist(),
        },
        "sceneBoundsMm": {
            "min": scene_positions.min(axis=0).tolist(),
            "max": scene_positions.max(axis=0).tolist(),
            "size": np.ptp(scene_positions, axis=0).tolist(),
        },
    }
    return scene_positions, scene_normals, transform_report


def export_glb(
    positions: np.ndarray,
    uv: np.ndarray,
    normals: np.ndarray,
    faces: np.ndarray,
    texture_path: Path,
    output_path: Path,
) -> None:
    """Write a standard textured triangle GLB without topology processing."""

    texture = Image.open(texture_path).convert("RGB")
    material = trimesh.visual.material.PBRMaterial(
        name="Cockpit source texture",
        baseColorTexture=texture,
        metallicFactor=0.0,
        roughnessFactor=1.0,
    )
    visual = trimesh.visual.texture.TextureVisuals(uv=uv, material=material)
    mesh = trimesh.Trimesh(
        vertices=positions,
        faces=faces,
        vertex_normals=normals,
        visual=visual,
        process=False,
        validate=False,
    )
    mesh.metadata["units"] = "mm"
    scene = trimesh.Scene(mesh)
    output_path.write_bytes(scene.export(file_type="glb"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a standard GLB from one local Cockpit SolidEntity.")
    parser.add_argument("--cockpit", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    cockpit_path = args.cockpit.resolve()
    output_dir = args.output_dir.resolve()
    if not cockpit_path.is_file():
        parser.error(f"Cockpit file does not exist: {cockpit_path}")
    if output_dir.exists() and any(output_dir.iterdir()) and not args.force:
        parser.error(f"Output directory is not empty; pass --force to reuse it: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    scene = extract_scene_assets(cockpit_path, output_dir)
    raw_path, decoder_metadata = decode_ci(scene["paths"]["geometry"], output_dir, args.force)
    positions, uv, normals, faces = load_decoded_mesh(raw_path, decoder_metadata)
    positions, normals, transform_report = transform_to_scene_mm(positions, normals, scene["solid"])

    glb_path = output_dir / f"{cockpit_path.stem}-ci-scene-mm.glb"
    export_glb(positions, uv, normals, faces, scene["paths"]["texture"], glb_path)

    template = scene["template"]
    report = {
        "format": "acm-cockpit-interoperability-report",
        "version": 1,
        "source": {"path": str(cockpit_path), "sha256": sha256(cockpit_path)},
        "geometry": {
            "vertices": int(len(positions)),
            "triangles": int(len(faces)),
            "glb": glb_path.name,
            "glbSha256": sha256(glb_path),
            **transform_report,
        },
        "assets": {label: path.name for label, path in scene["paths"].items()},
        "template": dict(template.attrib) if template is not None else None,
        "notes": [
            "The GLB is reconstructed from the CI triangle mesh, not from the DXF point cloud.",
            "Cockpit scene centring, per-axis scale, Euler rotation, and position are applied in millimetres.",
            "The original cockpit archive and its embedded files are not modified.",
        ],
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"GLB: {glb_path}")
    print(f"Vertices: {len(positions):,}")
    print(f"Triangles: {len(faces):,}")
    print(f"Scene size (mm): {np.ptp(positions, axis=0).round(4).tolist()}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
