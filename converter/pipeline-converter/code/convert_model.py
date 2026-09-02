"""
File: code/convert_model.py
Purpose:
 - Orchestrate common 3D format conversion through headless Blender.
 - Reuse ACM's existing mesh sampler for SSLE-compatible POINT DXF output.
 - Package multi-format results into one downloadable ZIP archive.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = PROJECT_ROOT / "output" / "conversions"
BLENDER_INPUTS = {".blend", ".obj", ".stl", ".ply", ".glb", ".gltf", ".fbx", ".dae", ".dxf", ".usd", ".usda", ".usdc", ".usdz"}
OUTPUT_FORMATS = {"dxf", "obj", "stl", "ply", "glb", "gltf", "fbx", "usd", "usdz"}


def find_blender():
    """Resolve an explicit, PATH, local Windows, or shared VPS Blender binary."""
    configured = os.environ.get("BLENDER_EXE")
    candidates = [
        Path(configured) if configured else None,
        Path(shutil.which("blender")) if shutil.which("blender") else None,
        Path(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        Path(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"),
        Path("/home/hreidar/apps/acm-pipeline/shared/tools/blender/blender"),
        Path("/usr/bin/blender"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "Blender was not found. Set BLENDER_EXE to a Blender 4.3+ executable."
    )


def stream_command(command, label):
    """Run one child process while forwarding readable progress to the web console."""
    print(f"{label}: {' '.join(str(part) for part in command)}", flush=True)
    process = subprocess.Popen(
        [str(part) for part in command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        clean = line.rstrip()
        if clean:
            print(clean, flush=True)
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"{label} failed with exit code {return_code}.")


def add_if_positive(command, flag, value):
    """Append a numeric CLI option only when it has a positive value."""
    if value is not None and value > 0:
        command.extend([flag, str(value)])


def prepare_dxf_mesh(source, target):
    """Convert a 3DFACE DXF to Blender's simple OBJ interchange format."""
    from mesh_to_pointcloud import load_dxf_mesh

    vertices, faces, _, _ = load_dxf_mesh(source)
    if len(faces) == 0:
        raise ValueError(
            "The DXF contains no 3DFACE mesh geometry. POINT-cloud DXF files "
            "are printer output and cannot be reconstructed into a surface model."
        )

    with target.open("w", encoding="utf-8", newline="\n") as output:
        output.write("# ACM temporary 3DFACE DXF mesh\n")
        for x_value, y_value, z_value in vertices:
            output.write(f"v {x_value:.12g} {y_value:.12g} {z_value:.12g}\n")
        for corner_a, corner_b, corner_c in faces:
            output.write(f"f {corner_a + 1} {corner_b + 1} {corner_c + 1}\n")


def run_blender(source, output_stem, job_dir, manifest_path, stage_obj, args):
    """Invoke the isolated Blender worker for geometry processing and standard exports."""
    standard_formats = [item for item in args.formats if item != "dxf"]
    command = [
        find_blender(),
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        "--python",
        CODE_DIR / "blender_model_io.py",
        "--",
        "--file",
        source,
        "--output-dir",
        job_dir,
        "--output-stem",
        output_stem,
        "--formats",
        *(standard_formats or ["obj"]),
        "--input-unit",
        args.input_unit,
        "--placement",
        args.placement,
        "--slice-axis",
        args.slice_axis,
        "--manifest",
        manifest_path,
    ]
    add_if_positive(command, "--fit-width", args.fit_width)
    add_if_positive(command, "--fit-height", args.fit_height)
    add_if_positive(command, "--fit-depth", args.fit_depth)
    if args.slice_min is not None:
        command.extend(["--slice-min", str(args.slice_min)])
    if args.slice_max is not None:
        command.extend(["--slice-max", str(args.slice_max)])
    if args.fill_cuts:
        command.append("--fill-cuts")
    if "dxf" in args.formats:
        command.extend(["--stage-obj", stage_obj])
    stream_command(command, "Blender conversion")

    # A DXF-only job used OBJ as an internal transport, not a requested result.
    if not standard_formats:
        internal_obj = job_dir / f"{output_stem}.obj"
        internal_mtl = internal_obj.with_suffix(".mtl")
        internal_obj.unlink(missing_ok=True)
        internal_mtl.unlink(missing_ok=True)


def run_printer_dxf(stage_obj, job_dir, source_stem, args):
    """Reuse the tested ACM surface sampler for the selected processed mesh."""
    command = [
        sys.executable,
        CODE_DIR / "mesh_to_pointcloud.py",
        "--file",
        stage_obj,
        "--out",
        job_dir,
        "--template",
        args.template,
        "--spacing",
        str(args.spacing),
        "--min-distance",
        str(args.min_distance),
        "--layer-spacing",
        str(args.layer_spacing),
        "--stagger",
        str(args.stagger),
        "--max-points",
        str(args.max_points),
        "--seed",
        str(args.seed),
    ]
    add_if_positive(command, "--width", args.width)
    add_if_positive(command, "--height", args.height)
    add_if_positive(command, "--depth", args.depth)
    add_if_positive(command, "--border", args.border)
    add_if_positive(command, "--points", args.points)
    add_if_positive(command, "--z-distance", args.z_distance)
    add_if_positive(command, "--layers", args.layers)
    stream_command(command, "Printer DXF")

    staged_outputs = sorted(job_dir.glob(f"{stage_obj.stem}-*.dxf"))
    if not staged_outputs:
        raise RuntimeError("Printer DXF completed without producing a DXF file.")
    for staged_output in staged_outputs:
        suffix = staged_output.name[len(stage_obj.stem) :]
        staged_output.rename(job_dir / f"{source_stem}-printer{suffix}")


def result_files(job_dir):
    """List durable job artifacts while excluding the internal OBJ transport."""
    records = []
    for path in sorted(item for item in job_dir.rglob("*") if item.is_file()):
        if path.name.startswith(".acm-stage") or path.suffix.lower() == ".zip":
            continue
        relative = path.relative_to(job_dir).as_posix()
        records.append(
            {
                "path": relative,
                "name": path.name,
                "extension": path.suffix.lower(),
                "bytes": path.stat().st_size,
            }
        )
    return records


def write_report(source, job_dir, args, manifest):
    """Write a concise human-readable inspection and conversion report."""
    processed = manifest["processed"]
    dimensions = processed["dimensions_mm"]
    report_path = job_dir / "conversion-report.md"
    lines = [
        "<!--",
        "File: conversion-report.md",
        "Purpose:",
        " - Record source inspection, millimetre transforms, slicing, and outputs.",
        "-->",
        "",
        f"# Model conversion: {source.name}",
        "",
        f"- Input format: `{manifest['input_format']}`",
        f"- Declared input unit: `{manifest['input_unit']}`",
        f"- Blender: `{manifest['blender_version']}`",
        f"- Output formats: `{', '.join(args.formats)}`",
        f"- Processed vertices: `{processed['vertices']:,}`",
        f"- Processed triangles: `{processed['triangles']:,}`",
        f"- Dimensions: `{dimensions['width']:.4f} × {dimensions['height']:.4f} × {dimensions['depth']:.4f} mm`",
        f"- Placement: `{manifest['placement']}`",
        f"- Slice: `{manifest['slice']}`",
        "- Source modified: `No`",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def write_archive(job_dir, archive_name):
    """Create one ZIP containing every requested artifact and its report."""
    archive_path = job_dir / archive_name
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for record in result_files(job_dir):
            archive.write(job_dir / record["path"], record["path"])
    return archive_path


def build_parser():
    """Describe the web-backed universal conversion options."""
    parser = argparse.ArgumentParser(description="Inspect, size, slice, and convert common 3D models.")
    parser.add_argument("--file", required=True)
    parser.add_argument("--out", help="Optional output root; defaults to output/conversions.")
    parser.add_argument("--formats", nargs="+", required=True, choices=sorted(OUTPUT_FORMATS))
    parser.add_argument("--input-unit", choices=["mm", "cm", "m", "in"], default="mm")
    parser.add_argument("--fit-width", type=float, default=0.0)
    parser.add_argument("--fit-height", type=float, default=0.0)
    parser.add_argument("--fit-depth", type=float, default=0.0)
    parser.add_argument("--placement", choices=["keep", "center", "ground"], default="center")
    parser.add_argument("--slice-axis", choices=["none", "x", "y", "z"], default="none")
    parser.add_argument("--slice-min", type=float)
    parser.add_argument("--slice-max", type=float)
    parser.add_argument("--fill-cuts", action="store_true")

    parser.add_argument("--template", default="60x80x40")
    parser.add_argument("--width", type=float, default=0.0)
    parser.add_argument("--height", type=float, default=0.0)
    parser.add_argument("--depth", type=float, default=0.0)
    parser.add_argument("--border", type=float, default=1.0)
    parser.add_argument("--points", type=int, default=0)
    parser.add_argument("--spacing", type=float, default=0.08)
    parser.add_argument("--min-distance", type=float, default=0.08)
    parser.add_argument("--z-distance", type=float, default=0.0)
    parser.add_argument("--max-points", type=int, default=500000)
    parser.add_argument("--layers", type=int, default=0)
    parser.add_argument("--layer-spacing", type=float, default=0.08)
    parser.add_argument("--stagger", type=int, default=1)
    parser.add_argument("--seed", type=int, default=7)
    return parser


def main():
    args = build_parser().parse_args()
    source = Path(args.file).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input file not found: {source}")
    if source.suffix.lower() not in BLENDER_INPUTS:
        raise ValueError(f"Unsupported model input: {source.suffix}")
    if args.slice_min is not None and args.slice_max is not None and args.slice_min >= args.slice_max:
        raise ValueError("Slice minimum must be smaller than slice maximum.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    job_id = f"{source.stem}-{stamp}-{uuid.uuid4().hex[:8]}"
    output_root = Path(args.out).resolve() if args.out else OUTPUT_ROOT
    output_root.mkdir(parents=True, exist_ok=True)
    job_dir = output_root / job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    manifest_path = job_dir / "job.json"
    stage_obj = job_dir / ".acm-stage.obj"

    blender_source = source
    prepared_dxf_obj = None
    if source.suffix.lower() == ".dxf":
        prepared_dxf_obj = job_dir / ".acm-dxf-source.obj"
        prepare_dxf_mesh(source, prepared_dxf_obj)
        blender_source = prepared_dxf_obj

    print(f"Source: {source.name}", flush=True)
    print(f"Job: {job_id}", flush=True)
    try:
        run_blender(blender_source, source.stem, job_dir, manifest_path, stage_obj, args)
        if "dxf" in args.formats:
            run_printer_dxf(stage_obj, job_dir, source.stem, args)
    finally:
        stage_obj.unlink(missing_ok=True)
        stage_obj.with_suffix(".mtl").unlink(missing_ok=True)
        if prepared_dxf_obj:
            prepared_dxf_obj.unlink(missing_ok=True)
            prepared_dxf_obj.with_suffix(".mtl").unlink(missing_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source.suffix.lower() == ".dxf":
        manifest["source"] = str(source)
        manifest["input_format"] = "dxf"
    report_path = write_report(source, job_dir, args, manifest)
    manifest.update(
        {
            "job_id": job_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "requested_formats": args.formats,
            "report": report_path.name,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if len(args.formats) > 1 or "gltf" in args.formats:
        archive = write_archive(job_dir, f"{source.stem}-converted.zip")
        print(f"ZIP: {archive}", flush=True)

    files = result_files(job_dir)
    zip_path = next((path for path in job_dir.glob("*.zip")), None)
    if zip_path:
        files.append(
            {
                "path": zip_path.name,
                "name": zip_path.name,
                "extension": ".zip",
                "bytes": zip_path.stat().st_size,
            }
        )
    for record in files:
        print(f"Output: {record['path']} ({record['bytes']:,} bytes)", flush=True)
    print(
        "ACM_CONVERTER_JOB="
        + json.dumps({"jobId": job_id, "directory": str(job_dir), "files": files}, separators=(",", ":")),
        flush=True,
    )


if __name__ == "__main__":
    main()
