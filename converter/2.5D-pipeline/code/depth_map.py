"""
File: converter/2.5D-pipeline/code/depth_map.py
Purpose:
 - Turn one photograph into a 16-bit depth map: the single stage that this
   whole pipeline exists to add, and the local stand-in for whatever
   Cockpit3D's AutoConvert-to-3D runs on their server.

Everything downstream is ordinary geometry. This is the only place a model is
involved, which is deliberate - it means the engine can be swapped without any
other file changing.

Output convention, fixed here so nothing downstream has to think about it:
16-bit grayscale PNG, BRIGHT = NEAR = raised toward the viewer. Depth Anything
predicts inverse depth and already reads that way; metric/true-depth engines
(MoGe-2, Depth Pro and Marigold) are flipped on the way out. --invert flips the
final result when a particular photo still comes out inside-out.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

from utils import (  # noqa: E402
    MODELS_DIR,
    base_parser,
    fail,
    prepare_output,
    report,
    torch_device,
    use_local_model_cache,
)

DEPTH_ANYTHING_MODELS = {
    "small": "depth-anything/Depth-Anything-V2-Small-hf",
    "base": "depth-anything/Depth-Anything-V2-Base-hf",
    "large": "depth-anything/Depth-Anything-V2-Large-hf",
}

MARIGOLD_MODEL = "prs-eth/marigold-depth-lcm-v1-0"

MOGE_MODELS = {
    "vitb": MODELS_DIR / "moge-2-vitb-normal" / "model.pt",
    "vitl": MODELS_DIR / "moge-2-vitl-normal" / "model.pt",
}

DEPTH_PRO_CHECKPOINT = MODELS_DIR / "depth-pro" / "checkpoints" / "depth_pro.pt"

# True when the engine's raw output is already "high value = near the camera".
ENGINE_NEAR_IS_HIGH = {
    "depth-anything": True,
    "depth-pro": False,
    "marigold": False,
    "moge-2": False,
}


def gaussian_blur(plane: np.ndarray, sigma: float) -> np.ndarray:
    """
    Separable Gaussian over a float plane, written out rather than pulled from
    SciPy so this venv stays a short install.

    Smoothing matters more than it looks: every model produces some per-pixel
    noise, and noise in a depth map becomes physical bumps on the relief
    surface, which the point sampler then faithfully turns into stray dots.
    """
    if sigma <= 0:
        return plane

    radius = max(1, int(round(sigma * 3)))
    offsets = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-(offsets**2) / (2 * sigma**2))
    kernel /= kernel.sum()

    padded = np.pad(plane, ((0, 0), (radius, radius)), mode="edge")
    blurred = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), 1, padded)

    padded = np.pad(blurred, ((radius, radius), (0, 0)), mode="edge")
    return np.apply_along_axis(lambda col: np.convolve(col, kernel, mode="valid"), 0, padded)


def apply_edge_profile(
    depth: np.ndarray, mask: np.ndarray, profile: str, feather: float
) -> np.ndarray:
    """
    Decide what the depth does at the subject's silhouette.

    The three profiles are carried over from pipeline-old/pipeline-01's
    DEPTH_PROFILES, which is where they were worked out against real cut-outs:

    - `standard`  — binary cut. Any transparent pixel goes to zero, opaque
      pixels keep their depth. Simplest correct behaviour, but it leaves a
      geometric cliff at the boundary that shows up in the mesh as a wall.
    - `soft`      — alpha used as a linear weight, so a half-transparent hair
      pixel gets half its depth. Fades the silhouette naturally, but only
      helps when the mask actually has soft edges.
    - `feathered` — blurs the alpha before weighting, which widens the
      transition zone. This is the one that works on a BINARY mask, where
      `soft` degenerates back into `standard`.
    """
    if profile == "standard":
        return depth * (mask > 0.5)
    if profile == "soft":
        return depth * np.clip(mask, 0.0, 1.0)

    # Auto: the ratio pipeline-old settled on, sigma 10 at a 3840px long edge.
    # A fixed pixel count is meaningless across resolutions - 3px of feather on
    # a 4000px portrait is not a transition zone, it is a rounding error.
    sigma = feather if feather > 0 else max(1.0, 0.0026 * max(mask.shape))
    report(f"[depth] feathering the silhouette, sigma {sigma:.1f}px")
    return depth * np.clip(gaussian_blur(mask, sigma), 0.0, 1.0)


def load_source(path: Path) -> tuple[Image.Image, np.ndarray | None]:
    """Open the photo as RGB, and keep its alpha separately if it is a cut-out."""
    try:
        image = Image.open(path)
    except Exception as error:  # noqa: BLE001 - any unreadable file is the same failure
        fail(f"Could not open {path}: {error}")

    image.load()
    alpha = None
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        alpha = np.asarray(image.convert("RGBA"))[:, :, 3].astype(np.float32) / 255.0

    return image.convert("RGB"), alpha


def run_depth_anything(image: Image.Image, size: str, device: str, resolution: int) -> np.ndarray:
    """
    Predict inverse depth with Depth Anything V2, resampled back to the photo's
    own size.

    IMPORTANT, and learned the hard way in pipeline-old/pipeline-02-zoedepth:
    enlarging the PIL image before handing it to the processor accomplishes
    nothing, because the processor immediately resizes to the checkpoint's own
    training size (~518px for Depth Anything V2). To actually run at a higher
    resolution the processor's `size` has to be overridden, which is what
    happens below. ViT interpolates its position embeddings, so this works -
    but it is off the training distribution, and measuring it says that is
    exactly what it feels like. On a 960px portrait (2026-08-29, Large, CPU):

        native ~518px   25s   Laplacian detail energy 3.12e-05
        override 1024px 66s   3.03e-05  -> 0.97x the detail for 2.6x the time

    So the flag is now honest but it is not a quality knob. Relief quality has
    to come from the engine or from facial enhancement, not from resolution.
    Hence the default of 0.
    """
    import torch
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation

    model_id = DEPTH_ANYTHING_MODELS[size]
    report(f"[depth] loading {model_id} on {device}")

    processor = AutoImageProcessor.from_pretrained(model_id)
    model = AutoModelForDepthEstimation.from_pretrained(model_id).to(device).eval()

    if resolution > 0:
        # Square, because the ViT patches a square grid; the aspect ratio is
        # restored by the interpolate back to the photo's own size below.
        inputs = processor(
            images=image,
            return_tensors="pt",
            size={"height": resolution, "width": resolution},
        ).to(device)
        report(f"[depth] inference at {resolution}x{resolution}px (processor default overridden)")
    else:
        inputs = processor(images=image, return_tensors="pt").to(device)
        report("[depth] inference at the checkpoint's own training size")

    with torch.no_grad():
        predicted = model(**inputs).predicted_depth

    if predicted.ndim == 3:
        predicted = predicted.unsqueeze(1)
    resampled = torch.nn.functional.interpolate(
        predicted, size=(image.height, image.width), mode="bicubic", align_corners=False
    )
    return resampled.squeeze().float().cpu().numpy()


def run_marigold(image: Image.Image, device: str, steps: int, ensemble: int) -> np.ndarray:
    """
    Predict affine-invariant depth with Marigold.

    Slower and a larger download than Depth Anything, but it resolves soft
    facial relief - the exact thing a portrait in glass lives or dies on -
    that Depth Anything can flatten into a mask-like slab.
    """
    import torch

    try:
        from diffusers import MarigoldDepthPipeline
    except ImportError:
        fail("The marigold engine needs diffusers. Run: pip install 'diffusers>=0.31'")

    report(f"[depth] loading {MARIGOLD_MODEL} on {device}")
    dtype = torch.float16 if device == "cuda" else torch.float32
    pipeline = MarigoldDepthPipeline.from_pretrained(MARIGOLD_MODEL, torch_dtype=dtype).to(device)

    report(f"[depth] {steps} steps, ensemble {ensemble}")
    result = pipeline(image, num_inference_steps=steps, ensemble_size=ensemble)

    prediction = np.asarray(result.prediction, dtype=np.float32)
    return np.squeeze(prediction)


def run_moge(
    image: Image.Image,
    model_size: str,
    device: str,
    resolution_level: int,
    apply_mask: bool,
    aux_output: Path | None,
) -> np.ndarray:
    """Run a pinned local MoGe-2 checkpoint and optionally retain normal/mask maps."""
    import torch

    try:
        from moge.model.v2 import MoGeModel
    except ImportError:
        fail(
            "MoGe-2 is installed in Models/runtimes/.venv-geometry. "
            "Run this script with that environment's python.exe."
        )

    checkpoint = MOGE_MODELS[model_size]
    if not checkpoint.is_file():
        fail(f"Missing MoGe-2 checkpoint: {checkpoint}. Run download_models.py --baseline")

    report(f"[depth] loading MoGe-2 {model_size} from {checkpoint} on {device}")
    model = MoGeModel.from_pretrained(checkpoint).to(device).eval()
    image_array = np.array(image, dtype=np.float32, copy=True) / 255.0
    image_tensor = torch.from_numpy(image_array).permute(2, 0, 1).to(device)

    report(
        f"[depth] MoGe-2 resolution level {resolution_level}/9, "
        f"fp16 autocast on CUDA, apply_mask={apply_mask}"
    )
    output = model.infer(
        image_tensor,
        resolution_level=resolution_level,
        apply_mask=apply_mask,
        use_fp16=device == "cuda",
    )

    if aux_output is not None:
        aux_output.mkdir(parents=True, exist_ok=True)
        normal = output.get("normal")
        if normal is not None:
            normal_rgb = ((normal.float().cpu().numpy() + 1.0) * 127.5).clip(0, 255).astype(np.uint8)
            Image.fromarray(normal_rgb, mode="RGB").save(aux_output / "normal.png")
            report(f"[depth] wrote {aux_output / 'normal.png'}")
        mask = output.get("mask")
        if mask is not None:
            mask_image = (mask.float().cpu().numpy().clip(0, 1) * 255).astype(np.uint8)
            Image.fromarray(mask_image, mode="L").save(aux_output / "mask.png")
            report(f"[depth] wrote {aux_output / 'mask.png'}")

    return output["depth"].float().cpu().numpy()


def run_depth_pro(image: Image.Image, device: str) -> np.ndarray:
    """Run Apple's pinned local Depth Pro checkpoint in metric-depth mode."""
    from dataclasses import replace

    import torch

    try:
        from depth_pro.depth_pro import (
            DEFAULT_MONODEPTH_CONFIG_DICT,
            create_model_and_transforms,
        )
    except ImportError:
        fail(
            "Depth Pro is installed in Models/runtimes/.venv-geometry. "
            "Run this script with that environment's python.exe."
        )

    if not DEPTH_PRO_CHECKPOINT.is_file():
        fail(f"Missing Depth Pro checkpoint: {DEPTH_PRO_CHECKPOINT}. Run download_models.py --baseline")

    precision = torch.float16 if device == "cuda" else torch.float32
    config = replace(
        DEFAULT_MONODEPTH_CONFIG_DICT,
        checkpoint_uri=str(DEPTH_PRO_CHECKPOINT),
    )
    report(f"[depth] loading Apple Depth Pro from {DEPTH_PRO_CHECKPOINT} on {device}")
    model, transform = create_model_and_transforms(
        config=config,
        device=torch.device(device),
        precision=precision,
    )
    model.eval()
    prediction = model.infer(transform(image))
    return prediction["depth"].float().cpu().numpy()


def normalise(depth: np.ndarray, clip_percent: float, mask: np.ndarray | None) -> np.ndarray:
    """
    Stretch to 0..1 against robust percentiles rather than raw min/max.

    One speck of predicted background at an extreme value would otherwise take
    the whole useful range with it and leave the face occupying the middle 5%.
    Percentiles are measured over the subject only when a cut-out mask exists.
    """
    finite = np.isfinite(depth)
    sample = depth[finite] if mask is None else depth[(mask > 0.5) & finite]
    if sample.size == 0:
        sample = depth[finite]
    if sample.size == 0:
        fail("The depth model returned no finite depth values.")

    low = float(np.percentile(sample, clip_percent))
    high = float(np.percentile(sample, 100 - clip_percent))
    if high - low < 1e-6:
        fail("The depth model returned a flat image - nothing to build a relief from.")

    report(f"[depth] range {low:.4f} .. {high:.4f} (clipped at {clip_percent:g}%)")
    clean = np.nan_to_num(depth, nan=high, posinf=high, neginf=low)
    return np.clip((clean - low) / (high - low), 0.0, 1.0)


def main() -> int:
    parser = base_parser("Predict a 16-bit depth map from one photograph.")
    parser.add_argument(
        "--engine",
        choices=sorted(ENGINE_NEAR_IS_HIGH),
        default="depth-anything",
        help=(
            "Select the depth engine. MoGe-2 also predicts normals/masks; Depth Pro "
            "focuses on sharp metric depth."
        ),
    )
    parser.add_argument(
        "--model",
        choices=sorted(DEPTH_ANYTHING_MODELS),
        default="large",
        help="Depth Anything checkpoint size. Large is the quality choice and the default.",
    )
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument(
        "--resolution",
        type=int,
        default=0,
        help=(
            "Override the processor's inference size. 0 uses the checkpoint's own "
            "training size, which is what you want. Measured 2026-08-29: 1024px cost "
            "2.6x the time for 0.97x the high-frequency detail - it changes the map "
            "without improving it. Kept for experiments, not for production."
        ),
    )
    parser.add_argument("--steps", type=int, default=4, help="Marigold denoising steps.")
    parser.add_argument("--ensemble", type=int, default=5, help="Marigold ensemble size.")
    parser.add_argument(
        "--moge-model",
        choices=sorted(MOGE_MODELS),
        default="vitb",
        help="MoGe-2 checkpoint. vitb is the 6 GB GPU baseline; vitl is the quality challenger.",
    )
    parser.add_argument(
        "--moge-resolution-level",
        type=int,
        choices=range(10),
        default=9,
        metavar="0..9",
        help=(
            "MoGe-2 token/detail level. 9 is the production/final-quality default; "
            "use 5 only for faster previews. Both fit the RTX 3060 6 GB."
        ),
    )
    parser.add_argument(
        "--moge-apply-mask",
        action="store_true",
        help=(
            "Replace MoGe-invalid/background depth with infinity before normalization. "
            "Leave off for AC3D-style full scenes; use for foreground-only experiments."
        ),
    )
    parser.add_argument(
        "--aux-output",
        type=Path,
        help="Optional folder for MoGe-2 normal.png and mask.png research outputs.",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        help=(
            "Optional float32 .npy output before percentile normalization. "
            "Use this for measured scene/person depth alignment research."
        ),
    )
    parser.add_argument(
        "--smooth",
        type=float,
        default=1.0,
        help="Gaussian sigma in pixels. Depth noise becomes physical bumps, so some is wanted.",
    )
    parser.add_argument("--clip-percent", type=float, default=1.0)
    parser.add_argument(
        "--mask-from-alpha",
        action="store_true",
        help="Flatten the background to zero using the cut-out's own alpha channel.",
    )
    parser.add_argument(
        "--edge-profile",
        choices=["feathered", "soft", "standard"],
        default="feathered",
        help="What the depth does at the silhouette. feathered works on binary masks too.",
    )
    parser.add_argument(
        "--feather",
        type=float,
        default=0.0,
        help=(
            "Blur sigma on the alpha weight, in pixels. 0 scales it to the image "
            "(0.26%% of the long edge). Only used by --edge-profile feathered."
        ),
    )
    parser.add_argument("--invert", action="store_true", help="Flip if the relief comes out inside-out.")
    args = parser.parse_args()

    use_local_model_cache()
    device = torch_device(args.device)

    image, alpha = load_source(args.input)
    report(f"[depth] source {args.input.name} {image.width}x{image.height}px")
    if args.mask_from_alpha and alpha is None:
        report("[depth] --mask-from-alpha asked for, but this image has no alpha channel; ignoring.")
    mask = alpha if (args.mask_from_alpha and alpha is not None) else None

    if args.engine == "depth-anything":
        raw = run_depth_anything(image, args.model, device, args.resolution)
    elif args.engine == "marigold":
        raw = run_marigold(image, device, args.steps, args.ensemble)
    elif args.engine == "moge-2":
        raw = run_moge(
            image,
            args.moge_model,
            device,
            args.moge_resolution_level,
            args.moge_apply_mask,
            args.aux_output,
        )
    else:
        raw = run_depth_pro(image, device)

    if raw.shape != (image.height, image.width):
        # Marigold returns at its own working size; match the photo so the mesh
        # stage can index depth and colour with the same coordinates.
        raw = np.asarray(
            Image.fromarray(raw.astype(np.float32), mode="F").resize(
                (image.width, image.height), Image.BICUBIC
            ),
            dtype=np.float32,
        )

    if args.raw_output is not None:
        prepare_output(args.raw_output)
        np.save(args.raw_output, raw.astype(np.float32, copy=False))
        report(f"[depth] wrote raw float32 depth {args.raw_output}")

    depth = normalise(raw, args.clip_percent, mask)

    # Flip to the fixed "bright = near" convention before anything else, so the
    # smoothing and masking below act on the final orientation.
    if not ENGINE_NEAR_IS_HIGH[args.engine]:
        depth = 1.0 - depth
    if args.invert:
        depth = 1.0 - depth

    if args.smooth > 0:
        report(f"[depth] smoothing sigma {args.smooth:g}px")
        depth = gaussian_blur(depth, args.smooth)

    if mask is not None:
        coverage = float((mask > 0.5).mean())
        report(f"[depth] subject covers {coverage * 100:.1f}% of the frame")
        if coverage > 0.95:
            report("[depth] nearly the whole frame is opaque - the cut-out probably found no subject.")

        # Applied after smoothing, so the blur cannot drag background values
        # inward across the silhouette before the profile decides its shape.
        depth = apply_edge_profile(depth, mask, args.edge_profile, args.feather)

    prepare_output(args.output)
    Image.fromarray((np.clip(depth, 0, 1) * 65535).astype(np.uint16)).save(args.output)
    report(f"[depth] wrote {args.output}")

    # A sidecar so the mesh stage and the job manifest can record what produced
    # this map without re-deriving it from the filename.
    sidecar = args.output.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "engine": args.engine,
                "model": (
                    MARIGOLD_MODEL
                    if args.engine == "marigold"
                    else str(MOGE_MODELS[args.moge_model])
                    if args.engine == "moge-2"
                    else str(DEPTH_PRO_CHECKPOINT)
                    if args.engine == "depth-pro"
                    else DEPTH_ANYTHING_MODELS[args.model]
                ),
                "device": device,
                "resolution": args.resolution,
                "moge_resolution_level": (
                    args.moge_resolution_level if args.engine == "moge-2" else None
                ),
                "moge_apply_mask": args.moge_apply_mask if args.engine == "moge-2" else None,
                "raw_output": str(args.raw_output) if args.raw_output is not None else None,
                "smooth": args.smooth,
                "masked": mask is not None,
                "inverted": bool(args.invert),
                "width": image.width,
                "height": image.height,
                "convention": "16-bit PNG, bright = near = raised",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    report(f"[depth] wrote {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
