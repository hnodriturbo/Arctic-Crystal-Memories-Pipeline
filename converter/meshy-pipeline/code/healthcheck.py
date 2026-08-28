"""
File: converter/meshy-pipeline/code/healthcheck.py
Purpose:
 - Verify the Meshy pipeline's Python 3.11 support environment and workspace.
 - Report only non-secret runtime facts for deployment health checks.
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import requests


def main() -> int:
    """Print a machine-readable health report and fail on an invalid runtime."""

    pipeline_root = Path(__file__).resolve().parents[1]
    expected_directories = ("input", "work", "output")
    directories = {
        name: (pipeline_root / name).is_dir() for name in expected_directories
    }
    correct_python = sys.version_info[:2] == (3, 11)

    report = {
        "ok": correct_python and all(directories.values()),
        "python": platform.python_version(),
        "cpu_only": True,
        "requests": requests.__version__,
        "directories": directories,
    }
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
