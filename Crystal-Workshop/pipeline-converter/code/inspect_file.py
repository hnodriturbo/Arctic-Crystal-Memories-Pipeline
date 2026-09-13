"""
File: code/inspect_file.py
Purpose:
 - Inspect unknown CAD, DXF, or text-like point files before conversion.
"""

import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

from utils.parsers import classify_numeric_row, extract_xyz_from_numeric_parts, is_numeric_row


console = Console()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def detect_text_file(file_path, sample_size=65536):
    """Detect whether a file appears text-readable without loading the full file."""
    with open(file_path, "rb") as source_file:
        sample = source_file.read(sample_size)

    if b"\x00" in sample:
        return False, "Null bytes detected, likely binary."

    try:
        decoded_sample = sample.decode("utf-8")
    except UnicodeDecodeError:
        decoded_sample = sample.decode("utf-8", errors="replace")

    replacement_ratio = decoded_sample.count("\ufffd") / max(len(decoded_sample), 1)
    if replacement_ratio > 0.05:
        return False, "Many undecodable characters detected, likely binary or non-UTF text."

    return True, "File appears text-readable."


def inspect_text_file(file_path, sample_line_count):
    """Scan a text-readable file for sample lines and coordinate-like rows."""
    total_lines = 0
    candidate_rows = 0
    sample_lines = []
    row_shape_counts = {
        "xyz_only": 0,
        "prefix_plus_xyz": 0,
        "possible_rgb_or_extra_fields": 0,
        "numeric_but_not_xyz": 0,
        "non_numeric": 0,
    }

    with open(file_path, "r", encoding="utf-8", errors="replace") as source_file:
        for line in source_file:
            total_lines += 1
            clean_line = line.rstrip("\n\r")

            if len(sample_lines) < sample_line_count:
                sample_lines.append(clean_line)

            parts = clean_line.strip().split()
            row_shape = classify_numeric_row(parts)
            row_shape_counts[row_shape] = row_shape_counts.get(row_shape, 0) + 1

            if is_numeric_row(parts) and extract_xyz_from_numeric_parts(parts) is not None:
                candidate_rows += 1

    return {
        "total_lines": total_lines,
        "candidate_rows": candidate_rows,
        "sample_lines": sample_lines,
        "row_shape_counts": row_shape_counts,
    }


def write_inspection_report(file_path, file_size, text_detection, inspection):
    """Write a markdown report for later comparison and research notes."""
    reports_dir = PROJECT_ROOT / "output" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{file_path.stem}_inspection.md"

    lines = [
        f"# Inspection Report: {file_path.name}",
        "",
        "## File Summary",
        "",
        f"- Source file: `{file_path}`",
        f"- File size: `{file_size:,}` bytes",
        f"- Text detection: {text_detection}",
        "",
    ]

    if inspection:
        lines.extend(
            [
                "## Coordinate Row Summary",
                "",
                f"- Total text lines: `{inspection['total_lines']:,}`",
                f"- Candidate coordinate rows: `{inspection['candidate_rows']:,}`",
                "",
                "## Row Shape Counts",
                "",
            ]
        )

        for row_shape, count in inspection["row_shape_counts"].items():
            lines.append(f"- `{row_shape}`: `{count:,}`")

        lines.extend(["", "## First Safe Sample Lines", ""])
        for index, sample_line in enumerate(inspection["sample_lines"], start=1):
            lines.append(f"{index}. `{sample_line}`")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def print_summary(file_path, file_size, text_detection, inspection, report_path):
    """Print a clear terminal summary for quick inspection feedback."""
    console.print(f"[bold]Inspection complete:[/bold] {file_path}")
    console.print(f"File size: {file_size:,} bytes")
    console.print(f"Text detection: {text_detection}")

    if inspection:
        table = Table(title="Detected Row Shapes")
        table.add_column("Row shape")
        table.add_column("Count", justify="right")

        for row_shape, count in inspection["row_shape_counts"].items():
            table.add_row(row_shape, f"{count:,}")

        console.print(table)
        console.print(f"Candidate coordinate rows: {inspection['candidate_rows']:,}")

    console.print(f"Report written to: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Inspect CAD, DXF, or text-like point files.")
    parser.add_argument("--file", required=True, help="Path to the file to inspect.")
    parser.add_argument("--sample-lines", type=int, default=10, help="Number of safe sample lines to include.")
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    file_size = file_path.stat().st_size
    is_text, text_detection = detect_text_file(file_path)
    inspection = inspect_text_file(file_path, args.sample_lines) if is_text else None
    report_path = write_inspection_report(file_path, file_size, text_detection, inspection)
    print_summary(file_path, file_size, text_detection, inspection, report_path)


if __name__ == "__main__":
    main()
