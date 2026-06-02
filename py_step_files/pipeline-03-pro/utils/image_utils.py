# =============================================================
# image_utils.py — Image loading, saving, and conversion helpers
# =============================================================
# Shared image operations used across all pipeline-03-pro steps.
# Handles format conversions between PIL, numpy, and cv2.
#
# New in pipeline-03-pro vs pipeline-02:
#   - composite_rgba_on_grey() for color projection before texturing
#   - load_depth_map() for loading 16-bit depth back to float32
#   - save_preview_depth() extracted as a standalone function
# =============================================================

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


# -------------------------------------------------------------
# LOADING
# -------------------------------------------------------------

def load_image(path: Path) -> Image.Image:
    """Load an image from disk and return it as a plain RGB PIL Image."""
    try:
        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception as exc:
        raise RuntimeError(f"Failed to load image from '{path}': {exc}") from exc


def load_rgba(path: Path) -> Image.Image:
    """Load an image from disk and return it as RGBA PIL Image."""
    try:
        img = Image.open(path).convert("RGBA")
        return img
    except Exception as exc:
        raise RuntimeError(f"Failed to load RGBA image from '{path}': {exc}") from exc


def load_image_bgr(path: Path) -> np.ndarray:
    """Load an image from disk as a BGR uint8 numpy array (OpenCV format)."""
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(
            f"cv2.imread returned None for '{path}'. "
            "The file may be corrupt, missing, or an unsupported format."
        )
    return img


def load_depth_map(path: Path) -> np.ndarray:
    """
    Load a 16-bit PNG depth map and return a float32 array normalized to 0.0-1.0.
    1.0 = closest to camera, 0.0 = furthest.
    """
    depth_img = Image.open(path)
    depth_arr = np.array(depth_img, dtype=np.float32)
    d_max = depth_arr.max()
    if d_max > 0:
        return depth_arr / d_max
    return depth_arr


# -------------------------------------------------------------
# SAVING
# -------------------------------------------------------------

def save_image(image: Image.Image, path: Path, quality: int = 95) -> None:
    """Save a PIL Image to disk. PNG files are always lossless."""
    try:
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            image.save(path, format="JPEG", quality=quality, optimize=True)
        else:
            image.save(path, format="PNG", compress_level=1)
    except Exception as exc:
        raise RuntimeError(f"Failed to save image to '{path}': {exc}") from exc


def save_depth_map(depth_array: np.ndarray, path: Path) -> None:
    """
    Normalize a float depth array and save as a 16-bit grayscale PNG.
    16-bit gives 65536 depth levels — critical for mesh precision.
    """
    try:
        d_min = float(depth_array.min())
        d_max = float(depth_array.max())

        if d_max == d_min:
            normalized = np.zeros_like(depth_array, dtype=np.uint16)
        else:
            span = d_max - d_min
            normalized = ((depth_array - d_min) / span * 65535.0).astype(np.uint16)

        success = cv2.imwrite(str(path), normalized)
        if not success:
            raise RuntimeError(
                "cv2.imwrite returned False — check the output path and write permissions"
            )

    except Exception as exc:
        raise RuntimeError(f"Failed to save depth map to '{path}': {exc}") from exc


def save_preview_depth(depth: np.ndarray, path: Path) -> None:
    """Save an 8-bit inferno colormap preview of a normalized 0.0-1.0 depth array."""
    depth_uint8 = (depth * 255).clip(0, 255).astype(np.uint8)
    preview_pil = _apply_inferno_colormap(depth_uint8)
    preview_pil.save(str(path), format="PNG")


def _apply_inferno_colormap(gray: np.ndarray) -> Image.Image:
    """Apply matplotlib inferno colormap to a uint8 grayscale array."""
    import matplotlib
    colormap = matplotlib.colormaps["inferno"]
    rgba = colormap(gray.astype(np.float32) / 255.0)
    rgb = (rgba[:, :, :3] * 255).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


# -------------------------------------------------------------
# COLOR COMPOSITING
# -------------------------------------------------------------

def composite_rgba_on_grey(rgba: np.ndarray, grey: int = 128) -> np.ndarray:
    """
    Composite an RGBA image onto a flat grey background.

    Returns uint8 RGB array (H, W, 3). Used before color projection
    to avoid black-fringing at alpha boundaries in hair regions.

    Args:
        rgba: uint8 numpy array (H, W, 4) in RGBA order
        grey: background grey value 0-255 (default 128)

    Returns:
        uint8 numpy array (H, W, 3)
    """
    bg = np.full((*rgba.shape[:2], 3), grey, dtype=np.uint8)
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    rgb_composited = (rgba[:, :, :3].astype(np.float32) * alpha +
                      bg.astype(np.float32) * (1.0 - alpha))
    return rgb_composited.clip(0, 255).astype(np.uint8)


# -------------------------------------------------------------
# ASPECT-RATIO-SAFE SIZING AND RESIZING
# -------------------------------------------------------------

def compute_target_size(orig_w: int, orig_h: int, target_long_edge: int) -> tuple[int, int]:
    """
    Calculate new (width, height) that fits target_long_edge on the longer side
    while preserving the exact input aspect ratio.

    This is the single source of truth for all resize operations.
    Never compute target sizes inline.
    """
    if orig_h >= orig_w:
        new_h = target_long_edge
        new_w = round(orig_w * target_long_edge / orig_h)
    else:
        new_w = target_long_edge
        new_h = round(orig_h * target_long_edge / orig_w)
    new_w = max(1, new_w)
    new_h = max(1, new_h)
    return new_w, new_h


def resize_image(image: Image.Image, new_w: int, new_h: int) -> Image.Image:
    """Resize a PIL Image to exactly (new_w, new_h) using Lanczos resampling."""
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)


def extract_alpha_mask(rgba_image: Image.Image) -> Image.Image:
    """
    Extract the alpha channel from an RGBA image as a grayscale image.
    White = subject kept, black = background removed.
    """
    if rgba_image.mode != "RGBA":
        raise ValueError(f"Expected RGBA image, got mode '{rgba_image.mode}'")
    _, _, _, alpha = rgba_image.split()
    return alpha


# -------------------------------------------------------------
# FORMAT CONVERSIONS
# -------------------------------------------------------------

def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert a PIL Image to a uint8 numpy array (H, W, C)."""
    return np.array(image, dtype=np.uint8)


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """Convert a uint8 numpy array to a PIL Image."""
    clipped = np.clip(array, 0, 255).astype(np.uint8)
    return Image.fromarray(clipped)


def bgr_to_rgb(img_bgr: np.ndarray) -> np.ndarray:
    """Swap BGR (OpenCV) to RGB (PIL/model standard)."""
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def rgb_to_bgr(img_rgb: np.ndarray) -> np.ndarray:
    """Swap RGB to BGR."""
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


# -------------------------------------------------------------
# METADATA
# -------------------------------------------------------------

def get_image_info(path: Path) -> dict:
    """
    Return basic metadata for an image file without fully decoding pixels.

    Returns dict with: width, height, mode, channels, file_size_mb
    """
    try:
        img = Image.open(path)
        width, height = img.size
        mode = img.mode
        channels = len(img.getbands())
        file_size_mb = round(path.stat().st_size / (1024 * 1024), 2)

        return {
            "width": width,
            "height": height,
            "mode": mode,
            "channels": channels,
            "file_size_mb": file_size_mb,
        }

    except Exception as exc:
        raise RuntimeError(f"Failed to read image info from '{path}': {exc}") from exc
