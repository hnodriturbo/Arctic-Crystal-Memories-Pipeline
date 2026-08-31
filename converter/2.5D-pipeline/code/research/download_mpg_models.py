"""
File: code/research/download_mpg_models.py
Purpose:
 - Download the licensed inference archives referenced by ECON's official fetch_data.sh.
 - Keep credentials out of files while preserving hashes and source provenance.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ModelPackage:
    """Describe one official Max Planck model archive used for ECON inference."""

    name: str
    filename: str
    url: str


PACKAGES = (
    ModelPackage(
        "smpl",
        "SMPL_python_v.1.0.0.zip",
        "https://download.is.tue.mpg.de/download.php?domain=smpl&"
        "sfile=SMPL_python_v.1.0.0.zip&resume=1",
    ),
    ModelPackage(
        "smplify",
        "mpips_smplify_public_v2.zip",
        "https://download.is.tue.mpg.de/download.php?domain=smplify&"
        "sfile=mpips_smplify_public_v2.zip&resume=1",
    ),
    ModelPackage(
        "smplx",
        "models_smplx_v1_1.zip",
        "https://download.is.tue.mpg.de/download.php?domain=smplx&"
        "sfile=models_smplx_v1_1.zip&resume=1",
    ),
    ModelPackage(
        "econ",
        "econ_data.zip",
        "https://download.is.tue.mpg.de/download.php?domain=icon&"
        "sfile=econ_data.zip&resume=1",
    ),
    ModelPackage(
        "pixie",
        "pixie_data.zip",
        "https://download.is.tue.mpg.de/download.php?domain=icon&"
        "sfile=HPS/pixie_data.zip&resume=1",
    ),
    ModelPackage(
        "pymafx",
        "pymafx_data.zip",
        "https://download.is.tue.mpg.de/download.php?domain=icon&"
        "sfile=HPS/pymafx_data.zip&resume=1",
    ),
)


def parse_args() -> argparse.Namespace:
    """Parse destination, username, and optional package selection."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--package",
        action="append",
        choices=[package.name for package in PACKAGES],
        dest="packages",
        help="Download only this package; repeat to select multiple packages.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    """Calculate a streaming SHA-256 digest for a downloaded archive."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def download_package(
    package: ModelPackage,
    destination: Path,
    username: str,
    password: str,
) -> dict[str, object]:
    """Download one authenticated archive with safe partial-file handling."""

    output_path = destination / package.filename
    partial_path = output_path.with_suffix(output_path.suffix + ".part")

    if output_path.is_file() and zipfile.is_zipfile(output_path):
        print(f"[{package.name}] already verified: {output_path.name}", flush=True)
        return {
            "name": package.name,
            "filename": output_path.name,
            "bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
            "url": package.url,
            "status": "existing",
        }

    form_data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    partial_size = partial_path.stat().st_size if partial_path.exists() else 0
    headers = {"User-Agent": "ACM-ECON-research-downloader/1.0"}
    if partial_size:
        headers["Range"] = f"bytes={partial_size}-"

    print(f"[{package.name}] requesting {package.filename}", flush=True)

    # The current MPG download service requires a session cookie from the login
    # page before accepting credentials on the same download URL.
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    initial_request = urllib.request.Request(package.url, headers=headers, method="GET")
    with opener.open(initial_request, timeout=180) as initial_response:
        initial_response.read(256)

    request = urllib.request.Request(package.url, data=form_data, headers=headers, method="POST")

    try:
        response = opener.open(request, timeout=180)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} while downloading {package.name}") from error

    with response:
        status = getattr(response, "status", 200)
        content_type = response.headers.get("Content-Type", "")
        if "text/html" in content_type.lower():
            preview = response.read(256).decode("utf-8", errors="replace")
            raise RuntimeError(
                f"{package.name} returned HTML instead of an archive: {preview[:120]!r}"
            )

        append = partial_size > 0 and status == 206
        if not append:
            partial_size = 0

        response_bytes = int(response.headers.get("Content-Length", "0") or 0)
        expected_total = partial_size + response_bytes if response_bytes else 0
        written = partial_size
        next_report = ((written // (64 * 1024 * 1024)) + 1) * 64 * 1024 * 1024

        with partial_path.open("ab" if append else "wb") as output:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                written += len(chunk)
                if written >= next_report:
                    if expected_total:
                        percent = 100.0 * written / expected_total
                        print(
                            f"[{package.name}] {written / 1024**2:.0f} MiB / "
                            f"{expected_total / 1024**2:.0f} MiB ({percent:.1f}%)",
                            flush=True,
                        )
                    else:
                        print(f"[{package.name}] {written / 1024**2:.0f} MiB", flush=True)
                    next_report += 64 * 1024 * 1024

    if not zipfile.is_zipfile(partial_path):
        raise RuntimeError(f"Downloaded file is not a valid ZIP archive: {partial_path}")

    partial_path.replace(output_path)
    digest = sha256_file(output_path)
    print(
        f"[{package.name}] complete: {output_path.name} "
        f"({output_path.stat().st_size / 1024**2:.1f} MiB)",
        flush=True,
    )
    return {
        "name": package.name,
        "filename": output_path.name,
        "bytes": output_path.stat().st_size,
        "sha256": digest,
        "url": package.url,
        "status": "downloaded",
    }


def main() -> int:
    """Download selected official archives and write a credential-free manifest."""

    args = parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    password = getpass.getpass("Max Planck model password: ")
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        return 2

    selected_names = set(args.packages or [package.name for package in PACKAGES])
    selected = [package for package in PACKAGES if package.name in selected_names]
    records = []
    for package in selected:
        records.append(download_package(package, destination, args.username, password))

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Official ECON fetch_data.sh package list",
        "packages": records,
    }
    manifest_path = destination / "download-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
