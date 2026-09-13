"""
File: code/local_workbench_server.py
Purpose:
 - Serve the local-only 2.5D workbench API on loopback.
 - Store uploaded photos and large generated artifacts under output/local-workbench.
 - Run bounded pipeline profiles and expose approved GLB references to the viewer.
"""

from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import uuid

from PIL import Image


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
WORKBENCH_ROOT = PIPELINE_ROOT / "local-workbench"
OUTPUT_ROOT = PIPELINE_ROOT / "output" / "local-workbench"
PREPROCESS_ROOT = OUTPUT_ROOT / "preprocess"
IMAGE_PIPELINE_ROOT = PIPELINE_ROOT.parent / "image-pipeline"
IMAGE_PIPELINE_CODE = IMAGE_PIPELINE_ROOT / "code"
IMAGE_PIPELINE_PYTHON = (
    IMAGE_PIPELINE_ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
)
GEOMETRY_PYTHON = (
    PIPELINE_ROOT / "Models" / "runtimes" / ".venv-geometry"
    / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
)
PROFILE_PATH = WORKBENCH_ROOT / "config" / "pipeline-profiles.json"
BLANKS_PATH = PIPELINE_ROOT / "blanks" / "blanks.json"
APPROVED_V3_ROOT = (
    PIPELINE_ROOT
    / "output"
    / "research"
    / "scene-fusion"
    / "pare-icon-econ-moge2-clearance0-depth-skirts-v3"
)
APPROVED_V3_GLB = APPROVED_V3_ROOT / "both_people_scene_with_depth_skirts-crystal-tone.glb"
WORKBENCH_GALLERY = (
    PIPELINE_ROOT
    / ".Markdown"
    / "runs"
    / "2026-09-02-amma-2-deep-and-approved-v3"
    / "artifacts"
    / "gallery"
    / "00-contact-sheet.jpg"
)
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")
FILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
ALLOWED_UI_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:4173",
}
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="acm-2.5d")
JOBS_LOCK = threading.Lock()
JOBS: dict[str, dict] = {}
PREPROCESS_MODELS = {
    "birefnet-portrait",
    "birefnet-general",
    "isnet-general-use",
    "u2net_human_seg",
    "u2net",
    "u2netp",
}


def utc_now() -> str:
    """Return a compact UTC timestamp for job metadata."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_profiles() -> list[dict]:
    """Read the tracked environment/profile catalogue."""
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))["profiles"]


def load_blanks() -> list[dict]:
    """Expose usable 2D Cockpit blanks without embedding licensed files in the site."""
    source = json.loads(BLANKS_PATH.read_text(encoding="utf-8"))
    blanks = [
        {
            "id": "none-fullsize",
            "name": "Ekkert form · Full-size",
            "width": 300.0,
            "height": 300.0,
            "depth": 60.0,
            "border": 0.0,
            "bevel": 0.0,
            "family": "none",
            "hasModel": False,
            "noCrystal": True,
            "fullSize": True,
        }
    ]
    for blank in source["blanks"]:
        if not blank["id"].startswith("2d-") or blank.get("type") == 8:
            continue
        blanks.append(
            {
                "id": blank["id"],
                "name": blank["name"],
                "width": blank["width"],
                "height": blank["height"],
                "depth": blank["depth"],
                "border": blank.get("border"),
                "bevel": blank.get("bevel"),
                "family": classify_blank(blank["name"]),
                "hasModel": bool(blank.get("model") and (PIPELINE_ROOT / "blanks" / blank["model"]).is_file()),
            }
        )
    return blanks


def classify_blank(name: str) -> str:
    """Map Cockpit names to the small set of workbench preview families."""
    lowered = name.lower()
    for family in ("heart", "prestige", "ornament", "diamond", "rectangle", "candle", "urn"):
        if family in lowered:
            return family
    return "special"


def write_job(job: dict) -> None:
    """Persist job state beside its artifacts so refreshes do not lose the run."""
    job_dir = OUTPUT_ROOT / job["id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    with JOBS_LOCK:
        JOBS[job["id"]] = job.copy()


def restore_jobs() -> None:
    """Load existing local job manifests at server startup."""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT_ROOT.glob("*/job.json"):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
            if JOB_ID_PATTERN.fullmatch(job.get("id", "")):
                JOBS[job["id"]] = job
        except (OSError, ValueError):
            continue


def run_command(job: dict, stage: str, command: list[str]) -> None:
    """Run one Python stage, stream it to run.log, and expose current progress."""
    job["stage"] = stage
    job["updatedAt"] = utc_now()
    write_job(job)
    log_path = OUTPUT_ROOT / job["id"] / "run.log"
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{utc_now()}] {stage}\n")
        log.flush()
        process = subprocess.Popen(
            command,
            cwd=PIPELINE_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
            marker = "[approved-v3] START "
            if line.startswith(marker):
                job["stage"] = line[len(marker):].strip()
                job["updatedAt"] = utc_now()
                write_job(job)
        return_code = process.wait()
    if return_code:
        raise RuntimeError(f"{stage} failed with exit code {return_code}")


def normalize_preprocess_options(payload: dict) -> dict:
    """Validate the small image-preparation surface exposed by the local UI."""
    options = payload.get("options") or {}
    model = str(options.get("removeBgModel", "isnet-general-use"))
    if model not in PREPROCESS_MODELS:
        raise ValueError("Unknown background-removal model")
    target = int(options.get("upscaleTarget", 2048))
    if target not in {2048, 4096}:
        raise ValueError("Upscale target must be 2048 or 4096 pixels")
    return {
        "enhance": bool(options.get("enhance", False)),
        "upscale": bool(options.get("upscale", True)),
        "removeBackground": bool(options.get("removeBackground", True)),
        "alphaMatting": bool(options.get("alphaMatting", False)),
        "removeBgModel": model,
        "upscaleTarget": target,
    }


def run_preprocess_command(run_dir: Path, stage: str, command: list[str]) -> None:
    """Run one existing image-pipeline script and keep its complete local log."""
    log_path = run_dir / "run.log"
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{utc_now()}] {stage}\n")
        completed = subprocess.run(
            command,
            cwd=IMAGE_PIPELINE_ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if completed.returncode:
        raise RuntimeError(f"{stage} failed with exit code {completed.returncode}")


def preprocess_image(run_id: str, source: Path, options: dict) -> dict:
    """Reuse the established image pipeline before any 2.5D model sees the source."""
    if not IMAGE_PIPELINE_PYTHON.is_file():
        raise RuntimeError("Local image-pipeline environment is missing")
    run_dir = PREPROCESS_ROOT / run_id
    current = source
    stages = []
    if options["enhance"]:
        enhanced = run_dir / "01-enhanced.png"
        run_preprocess_command(
            run_dir,
            "Gentle image enhancement",
            [
                str(IMAGE_PIPELINE_PYTHON), str(IMAGE_PIPELINE_CODE / "enhance.py"),
                "--input", str(current), "--output", str(enhanced), "--engine", "pillow",
                "--contrast", "1.05", "--sharpness", "1.12",
            ],
        )
        current = enhanced
        stages.append("enhance")
    if options["upscale"]:
        upscaled = run_dir / "02-upscaled.png"
        run_preprocess_command(
            run_dir,
            "Upscale",
            [
                str(IMAGE_PIPELINE_PYTHON), str(IMAGE_PIPELINE_CODE / "upscale.py"),
                "--input", str(current), "--output", str(upscaled), "--engine", "lanczos",
                "--target", str(options["upscaleTarget"]),
            ],
        )
        current = upscaled
        stages.append("upscale")
    mask = None
    if options["removeBackground"]:
        cutout = run_dir / "03-background-removed.png"
        mask = run_dir / "03-subject-mask.png"
        command = [
            str(IMAGE_PIPELINE_PYTHON), str(IMAGE_PIPELINE_CODE / "remove_bg.py"),
            "--input", str(current), "--output", str(cutout), "--mask", str(mask),
            "--model", options["removeBgModel"],
        ]
        if options["alphaMatting"]:
            command.append("--alpha-matting")
        run_preprocess_command(run_dir, "Background removal", command)
        current = cutout
        stages.append("remove_bg")
    if not stages:
        current = run_dir / "00-prepared.png"
        with Image.open(source) as image:
            image.save(current, format="PNG", optimize=True)
        stages.append("copy")

    with Image.open(current) as result:
        width, height = result.size
    manifest = {
        "id": run_id,
        "status": "complete",
        "createdAt": utc_now(),
        "options": options,
        "stages": stages,
        "resultFile": current.name,
        "resultUrl": f"http://127.0.0.1:8425/api/preprocess/{run_id}/files/{current.name}",
        "maskUrl": f"http://127.0.0.1:8425/api/preprocess/{run_id}/files/{mask.name}" if mask else None,
        "width": width,
        "height": height,
    }
    (run_dir / "preprocess.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def run_pipeline_job(job_id: str) -> None:
    """Execute a selected local profile and publish its monochrome GLB."""
    with JOBS_LOCK:
        job = JOBS[job_id].copy()
    job_dir = OUTPUT_ROOT / job_id
    source = job_dir / job["sourceFile"]
    profile = job["profileId"]
    blank = job["blank"]
    template = f"{blank['width']:g}x{blank['height']:g}x{blank['depth']:g}"
    python = str(GEOMETRY_PYTHON) if profile.startswith("cuda-") else sys.executable
    code = PIPELINE_ROOT / "code"
    depth = job_dir / "depth.png"
    refined_depth = job_dir / "refined-depth.png"
    final_depth = job_dir / "final-depth.png"
    tone = job_dir / "crystal-tone.png"
    geometry_dir = job_dir / "geometry"
    result_glb = job_dir / "relief-crystal.glb"
    result_obj = job_dir / "relief.obj"

    try:
        job.update({"status": "running", "stage": "Preparing", "updatedAt": utc_now()})
        write_job(job)
        if profile == "approved-v3-reference":
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if not powershell:
                raise RuntimeError("PowerShell is required for the approved v3 pipeline")
            run_command(
                job,
                "PARE → ICON → ECON → MoGe → depth-skirt v3",
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(code / "research" / "run_approved_v3_self_service.ps1"),
                    "-Source",
                    str(source),
                    "-OutputDir",
                    str(job_dir),
                ],
            )
            if not result_glb.is_file():
                raise RuntimeError("Approved v3 pipeline completed without relief-crystal.glb")
            job.update(
                {
                    "status": "complete",
                    "stage": "Ready in skref 4",
                    "updatedAt": utc_now(),
                    "resultUrl": f"http://127.0.0.1:8425/api/jobs/{job_id}/files/{result_glb.name}",
                    "recipe": "PARE + ICON + ECON + MoGe + depth-skirt v3",
                }
            )
            write_job(job)
            return
        if profile == "cpu-safe":
            depth_command = [
                python, str(code / "depth_map.py"), "--input", str(source), "--output", str(depth),
                "--engine", "depth-anything", "--model", "small", "--device", "cpu", "--mask-from-alpha",
            ]
            grid = "384"
            relief_depth = min(8.0, float(blank["depth"]) * 0.15)
        elif profile in {"cuda-preview", "cuda-quality", "cuda-quality-deep"}:
            model = "vitb" if profile == "cuda-preview" else "vitl"
            level = "5" if profile == "cuda-preview" else "9"
            depth_command = [
                python, str(code / "depth_map.py"), "--input", str(source), "--output", str(depth),
                "--engine", "moge-2", "--moge-model", model, "--moge-resolution-level", level,
                "--device", "cuda", "--aux-output", str(geometry_dir), "--raw-output", str(job_dir / "depth-raw.npy"),
                "--mask-from-alpha",
            ]
            grid = "512" if profile == "cuda-quality" else "384"
            if profile == "cuda-quality-deep":
                relief_depth = min(20.0, float(blank["depth"]) * 0.36)
            else:
                relief_depth = min(
                    8.0 if profile == "cuda-preview" else 10.0,
                    float(blank["depth"]) * (0.15 if profile == "cuda-preview" else 0.18),
                )
        else:
            raise ValueError(f"Profile {profile} is not runnable")

        run_command(job, "Global depth", depth_command)
        mesh_depth = depth
        if profile in {"cuda-quality", "cuda-quality-deep"}:
            run_command(
                job,
                "Face refinement",
                [
                    python, str(code / "face_refine.py"), "--input", str(source), "--depth", str(depth),
                    "--output", str(refined_depth), "--aux-output", str(job_dir / "face-refinement"),
                    "--device", "cuda", "--moge-model", "vitl", "--moge-resolution-level", "9",
                ],
            )
            run_command(
                job,
                "Surface detail",
                [
                    python, str(code / "detail_refine.py"), "--depth", str(refined_depth),
                    "--normal", str(geometry_dir / "normal.png"), "--mask", str(geometry_dir / "mask.png"),
                    "--output", str(final_depth), "--aux-output", str(job_dir / "detail-refinement"),
                ],
            )
            mesh_depth = final_depth

        run_command(
            job,
            "Crystal tone",
            [
                python, str(code / "appearance_refine.py"), "--input", str(source), "--output", str(tone),
                "--aux-output", str(job_dir / "appearance-refinement"), "--toning", "1.8",
            ],
        )
        run_command(
            job,
            "GLB export",
            [
                python, str(code / "depth_to_mesh.py"), "--depth", str(mesh_depth), "--photo", str(source),
                "--texture-image", str(tone), "--output", str(result_glb), "--obj", str(result_obj),
                "--template", template, "--relief-depth", f"{relief_depth:g}", "--grid", grid,
                "--vertex-color", "luma",
            ],
        )
        job.update(
            {
                "status": "complete",
                "stage": "Ready in skref 4",
                "updatedAt": utc_now(),
                "resultUrl": f"http://127.0.0.1:8425/api/jobs/{job_id}/files/{result_glb.name}",
                "toneUrl": f"http://127.0.0.1:8425/api/jobs/{job_id}/files/{tone.name}",
                "reliefDepthMm": relief_depth,
            }
        )
    except Exception as error:  # noqa: BLE001
        job.update({"status": "failed", "stage": "Failed", "error": str(error), "updatedAt": utc_now()})
    write_job(job)


class WorkbenchHandler(BaseHTTPRequestHandler):
    """Small loopback-only JSON and artifact server for the browser workbench."""

    server_version = "ACM2.5DWorkbench/1.0"

    def end_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin in ALLOWED_UI_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        """Write a UTF-8 JSON response."""
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path) -> None:
        """Stream one already-resolved local artifact."""
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        with path.open("rb") as source:
            while chunk := source.read(1024 * 1024):
                self.wfile.write(chunk)

    def do_GET(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route == "/api/catalog":
            self.send_json(
                {
                    "profiles": load_profiles(),
                    "blanks": load_blanks(),
                    "approvedV3Available": APPROVED_V3_GLB.is_file(),
                    "approvedV3Url": "http://127.0.0.1:8425/api/demo/v3.glb",
                    "imagePreprocess": {
                        "available": IMAGE_PIPELINE_PYTHON.is_file(),
                        "defaultModel": "isnet-general-use",
                        "models": sorted(PREPROCESS_MODELS),
                        "targets": [2048, 4096],
                    },
                }
            )
            return
        if route == "/api/jobs":
            with JOBS_LOCK:
                jobs = sorted(JOBS.values(), key=lambda item: item["createdAt"], reverse=True)
            self.send_json({"jobs": jobs})
            return
        if route == "/api/demo/v3.glb":
            self.send_file(APPROVED_V3_GLB)
            return
        if route == "/api/gallery/workbench.jpg":
            self.send_file(WORKBENCH_GALLERY)
            return
        preprocess_match = re.fullmatch(r"/api/preprocess/([a-f0-9]{12})/files/([^/]+)", route)
        if preprocess_match:
            run_id, file_name = preprocess_match.groups()
            if not FILE_NAME_PATTERN.fullmatch(file_name):
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            self.send_file(PREPROCESS_ROOT / run_id / file_name)
            return
        blank_match = re.fullmatch(r"/api/blanks/([^/]+)/model", route)
        if blank_match:
            blank_id = blank_match.group(1)
            source = json.loads(BLANKS_PATH.read_text(encoding="utf-8"))["blanks"]
            blank = next((item for item in source if item["id"] == blank_id), None)
            if not blank or not blank.get("model"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_file((PIPELINE_ROOT / "blanks" / blank["model"]).resolve())
            return
        job_match = re.fullmatch(r"/api/jobs/([a-f0-9]{12})(?:/files/([^/]+))?", route)
        if job_match:
            job_id, file_name = job_match.groups()
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if not job:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if not file_name:
                self.send_json(job)
                return
            if not FILE_NAME_PATTERN.fullmatch(file_name):
                self.send_error(HTTPStatus.BAD_REQUEST)
                return
            self.send_file(OUTPUT_ROOT / job_id / file_name)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route not in {"/api/jobs", "/api/preprocess"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_UPLOAD_BYTES * 1.5:
                raise ValueError("Upload body is empty or too large")
            payload = json.loads(self.rfile.read(length))
            if route == "/api/preprocess":
                options = normalize_preprocess_options(payload)
                file_name = Path(payload.get("fileName", "upload.png")).name
                suffix = Path(file_name).suffix.lower()
                if suffix not in ALLOWED_IMAGE_SUFFIXES:
                    raise ValueError("Only JPG, PNG and WebP images are accepted")
                encoded = payload.get("contentBase64", "")
                if "," in encoded:
                    encoded = encoded.split(",", 1)[1]
                raw = base64.b64decode(encoded, validate=True)
                if not raw or len(raw) > MAX_UPLOAD_BYTES:
                    raise ValueError("Image is empty or exceeds 40 MB")
                run_id = uuid.uuid4().hex[:12]
                run_dir = PREPROCESS_ROOT / run_id
                run_dir.mkdir(parents=True, exist_ok=False)
                source = run_dir / f"00-original{suffix}"
                source.write_bytes(raw)
                with Image.open(source) as image:
                    image.verify()
                self.send_json(preprocess_image(run_id, source, options), HTTPStatus.CREATED)
                return

            profile = next(
                item for item in load_profiles() if item["id"] == payload.get("profileId") and item["runnable"]
            )
            blank = next(item for item in load_blanks() if item["id"] == payload.get("blankId"))
            file_name = Path(payload.get("fileName", "upload.png")).name
            suffix = Path(file_name).suffix.lower()
            if suffix not in ALLOWED_IMAGE_SUFFIXES:
                raise ValueError("Only JPG, PNG and WebP images are accepted")

            job_id = uuid.uuid4().hex[:12]
            job_dir = OUTPUT_ROOT / job_id
            job_dir.mkdir(parents=True, exist_ok=False)
            preprocess_id = str(payload.get("preprocessId", ""))
            if preprocess_id:
                if not JOB_ID_PATTERN.fullmatch(preprocess_id):
                    raise ValueError("Invalid preprocess id")
                preprocess_manifest_path = PREPROCESS_ROOT / preprocess_id / "preprocess.json"
                preprocess_manifest = json.loads(preprocess_manifest_path.read_text(encoding="utf-8"))
                preprocess_file = PREPROCESS_ROOT / preprocess_id / preprocess_manifest["resultFile"]
                if not preprocess_file.is_file():
                    raise ValueError("Prepared image is missing")
                source_name = "source-prepared.png"
                source_path = job_dir / source_name
                shutil.copyfile(preprocess_file, source_path)
            else:
                encoded = payload.get("contentBase64", "")
                if "," in encoded:
                    encoded = encoded.split(",", 1)[1]
                raw = base64.b64decode(encoded, validate=True)
                if not raw or len(raw) > MAX_UPLOAD_BYTES:
                    raise ValueError("Image is empty or exceeds 40 MB")
                source_name = f"source{suffix}"
                source_path = job_dir / source_name
                source_path.write_bytes(raw)
            with Image.open(source_path) as image:
                image_width, image_height = image.size
                image.verify()
            if blank.get("fullSize"):
                blank = blank.copy()
                long_edge_mm = 300.0
                if image_width >= image_height:
                    blank["width"] = long_edge_mm
                    blank["height"] = round(long_edge_mm * image_height / image_width, 2)
                else:
                    blank["height"] = long_edge_mm
                    blank["width"] = round(long_edge_mm * image_width / image_height, 2)
            job = {
                "id": job_id,
                "status": "queued",
                "stage": "Waiting",
                "createdAt": utc_now(),
                "updatedAt": utc_now(),
                "profileId": profile["id"],
                "profileName": profile["name"],
                "blank": blank,
                "sourceFile": source_name,
                "originalFileName": file_name,
                "preprocessId": preprocess_id or None,
                "resultUrl": None,
                "toneUrl": None,
                "error": None,
            }
            write_job(job)
            EXECUTOR.submit(run_pipeline_job, job_id)
            self.send_json(job, HTTPStatus.ACCEPTED)
        except (ValueError, KeyError, StopIteration, json.JSONDecodeError, OSError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except RuntimeError as error:
            self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, message: str, *args: object) -> None:
        """Keep useful requests visible without the default host lookup noise."""
        print(f"[local-workbench] {self.address_string()} {message % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the ACM local 2.5D workbench API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8425)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("The local workbench may bind only to loopback")
    restore_jobs()
    server = ThreadingHTTPServer((args.host, args.port), WorkbenchHandler)
    print(f"[local-workbench] API http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        EXECUTOR.shutdown(wait=False, cancel_futures=True)
        server.server_close()


if __name__ == "__main__":
    main()
