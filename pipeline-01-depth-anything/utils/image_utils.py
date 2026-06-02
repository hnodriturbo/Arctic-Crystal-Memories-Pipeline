# =============================================================
# image_utils.py — Image loading, saving, and conversion helpers
# =============================================================
# PURPOSE:
#   Shared image operations used across all pipeline steps.
#   Handles loading, saving, and the conversions between PIL,
#   numpy, and OpenCV formats, since each major dependency
#   (Real-ESRGAN, REMBG, Depth Anything, Open3D) prefers a
#   different internal format.
#
# RESPONSIBILITIES:
#   - Load images from disk into PIL or numpy format
#   - Save images with appropriate compression settings
#   - Convert between PIL Image, float32 numpy array, and cv2 BGR
#   - Save depth maps as 16-bit PNG to preserve full precision
#   - Report image metadata for logging at the start of each step
#
# INPUTS:  Image file paths, PIL Images, numpy arrays
# OUTPUTS: Converted images, saved files
#
# DEPENDENCIES: Pillow, numpy, opencv-python
# =============================================================

from pathlib import Path

import cv2
import numpy as np
from PIL import Image


# -------------------------------------------------------------
# LOADING
# -------------------------------------------------------------

def load_image(path: Path) -> Image.Image:
    """
    Load an image from disk and return it as a plain RGB PIL Image.

    Alpha channels are dropped at this stage — the pixel data is composited
    against white. If the alpha channel must be preserved (e.g. the RGBA output
    of step 02 background removal), use PIL.Image.open() directly instead.

    This function is appropriate for loading source photos before step 01
    and for any step that consumes a plain RGB image.

    Args:
        path: Path to the image file

    Returns:
        PIL Image in RGB mode
    """
    try:
        img = Image.open(path)

        # Converting to RGB collapses any colour mode (CMYK, L, P, RGBA)
        # into the standard 3-channel format that most downstream models expect.
        # Real-ESRGAN, depth models, and most PyTorch transforms all assume RGB.
        if img.mode != "RGB":
            img = img.convert("RGB")

        return img

    except Exception as exc:
        raise RuntimeError(f"Failed to load image from '{path}': {exc}") from exc


def load_image_bgr(path: Path) -> np.ndarray:
    """
    Load an image from disk as a BGR uint8 numpy array (OpenCV format).

    Some models — notably Real-ESRGAN — expect BGR input because they use
    OpenCV internally. Call this instead of load_image() when passing the
    image directly to a cv2-based model.

    Args:
        path: Path to the image file

    Returns:
        uint8 numpy array, shape (H, W, 3), channels in BGR order
    """
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise RuntimeError(
            f"cv2.imread returned None for '{path}'. "
            "The file may be corrupt, missing, or an unsupported format."
        )
    return img


# -------------------------------------------------------------
# SAVING
# -------------------------------------------------------------

def save_image(image: Image.Image, path: Path, quality: int = 95) -> None:
    """
    Save a PIL Image to disk.

    PNG files are always written losslessly — the quality parameter is
    only used for JPEG output. PNG is the preferred format for all
    intermediate pipeline stages to prevent quality loss between steps.

    Args:
        image:   PIL Image to save
        path:    Destination path (the extension determines the output format)
        quality: JPEG quality 1–95. Ignored for PNG and other lossless formats.
    """
    try:
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            image.save(path, format="JPEG", quality=quality, optimize=True)
        else:
            # compress_level=1 gives light compression with very fast write speed.
            # Level 9 (maximum) saves roughly 10% extra on photo data at 5–10x
            # the write time — not worth it for intermediate pipeline files.
            image.save(path, format="PNG", compress_level=1)
    except Exception as exc:
        raise RuntimeError(f"Failed to save image to '{path}': {exc}") from exc


def save_depth_map(depth_array: np.ndarray, path: Path) -> None:
    """
    Normalize a floating-point depth array and save it as a 16-bit grayscale PNG.

    16-bit gives 65,536 depth levels versus only 256 for 8-bit. In the laser
    engraving pipeline this precision matters: depth values map directly to
    Z-axis laser positioning inside the crystal. Losing precision at this step
    introduces staircase artifacts in the final engraving.

    The depth array is min-max normalised across its full range before writing,
    so the output always uses the full 0–65535 scale regardless of what unit
    or range the depth model produced.

    Args:
        depth_array: 2D float32 or float64 array from a depth model
        path:        Destination path — must have a .png extension

    Notes:
        Uses cv2.imwrite with a uint16 array. OpenCV handles the 16-bit PNG
        encoding automatically from the dtype.
    """
    try:
        d_min = float(depth_array.min())
        d_max = float(depth_array.max())

        if d_max == d_min:
            # Completely flat depth map — store as all zeros rather than
            # dividing by zero. This shouldn't happen in normal use but
            # is a safety net for test images or degenerate model output.
            normalized = np.zeros_like(depth_array, dtype=np.uint16)
        else:
            span = d_max - d_min
            normalized = ((depth_array - d_min) / span * 65535.0).astype(np.uint16)

        # cv2.imwrite selects 16-bit PNG encoding automatically when the array dtype is uint16
        success = cv2.imwrite(str(path), normalized)
        if not success:
            raise RuntimeError(
                "cv2.imwrite returned False — check the output path and write permissions"
            )

    except Exception as exc:
        raise RuntimeError(f"Failed to save depth map to '{path}': {exc}") from exc


# -------------------------------------------------------------
# FORMAT CONVERSIONS
# -------------------------------------------------------------

def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """
    Convert a PIL Image to a float32 numpy array normalized to [0.0, 1.0].

    Most neural network models and OpenCV operations expect float32 input in
    the 0.0–1.0 range rather than the uint8 0–255 range used for display and
    storage. Call this before feeding an image into a depth or segmentation model.

    Args:
        image: PIL Image — any mode, but typically RGB or RGBA

    Returns:
        float32 numpy array, shape (H, W, C), values in [0.0, 1.0]
    """
    arr = np.array(image, dtype=np.float32)
    return arr / 255.0


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """
    Convert a float32 numpy array (0.0–1.0) back to a uint8 PIL Image.

    Values are clipped to [0.0, 1.0] before scaling to catch the small
    out-of-range values that model outputs sometimes contain.

    Args:
        array: float32 numpy array, shape (H, W, C), values nominally in [0.0, 1.0]

    Returns:
        PIL Image in mode RGB (3 channels) or RGBA (4 channels)
    """
    clipped = np.clip(array, 0.0, 1.0)
    uint8_array = (clipped * 255.0).astype(np.uint8)
    return Image.fromarray(uint8_array)


def bgr_to_rgb(img_bgr: np.ndarray) -> np.ndarray:
    """
    Swap the channel order from BGR (OpenCV) to RGB (PIL / model standard).

    Real-ESRGAN and other OpenCV-based tools return BGR arrays. Most depth
    models and PIL-based code expect RGB. Call this at the boundary between
    the two worlds rather than scattering cv2.cvtColor calls through step files.

    Args:
        img_bgr: uint8 or float32 numpy array with channels in BGR order

    Returns:
        Array with the same dtype and shape, channels in RGB order
    """
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def rgb_to_bgr(img_rgb: np.ndarray) -> np.ndarray:
    """
    Swap the channel order from RGB to BGR.

    Use this when handing an RGB array to an OpenCV-based model or when
    writing an RGB image with cv2.imwrite (which expects BGR).

    Args:
        img_rgb: uint8 or float32 numpy array with channels in RGB order

    Returns:
        Array with the same dtype and shape, channels in BGR order
    """
    return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


# -------------------------------------------------------------
# METADATA
# -------------------------------------------------------------

def get_image_info(path: Path) -> dict:
    """
    Return basic metadata for an image file without fully decoding its pixels.

    PIL defers full pixel decoding until pixel data is accessed. The size, mode,
    and band information are read from the file header immediately, making this
    cheap even for large files. Used for logging at the start of each step so
    the operator can confirm the input resolution before a slow inference run.

    Args:
        path: Path to the image file

    Returns:
        Dict with keys:
            width        (int)   — pixel width
            height       (int)   — pixel height
            mode         (str)   — PIL mode string, e.g. 'RGB', 'RGBA', 'L'
            channels     (int)   — number of colour channels
            file_size_mb (float) — file size in megabytes, rounded to 2 decimals
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
