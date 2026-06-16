# pipeline/utils/image.py
# 🧩 Image utilities
# - Load image from disk safely
# - Simple scene classification (portrait/landscape/square)
# - Optional crystal dimension helper (kept for future use)
# - Optional AI background removal with rembg

import os  # 📁 Environment + path

os.environ["ONNXRUNTIME_EXECUTION_PROVIDERS"] = (
    "CPUExecutionProvider"  # 🧠 Force CPU for ONNX
)

import cv2  # 📸 OpenCV for image handling
import numpy as np  # 🧮 Array math


def load_image(path):
    # 📥 Load BGR image from disk and validate existence
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Image file not found: {path}"
        )  # ⚠️ Clear error for missing file

    image = cv2.imread(path)  # 📸 Read image (BGR)
    if image is None:
        raise ValueError(
            f"Failed to load image (possibly corrupted or unsupported format): {path}"
        )  # ⚠️ Guard against invalid image

    return image  # 📤 Return BGR image as numpy array


def classify_image_type(image):
    # 🧮 Classify image as portrait/landscape/square by aspect ratio
    h, w = image.shape[:2]
    aspect = w / h

    if aspect > 1.4:
        return "landscape"  # 🌄 Wide image
    elif aspect < 0.8:
        return "portrait"  # 📱 Tall image
    else:
        return "square"  # ⏹️ Square image


def calculate_crystal_dimensions(image, crystal_depth=60.0, auto_size=True):
    """
    📐 Legacy helper for crystal dimensions (kept for future use)

    - Not used in the simplified pipeline.
    - Returns width/height/depth in mm based on aspect ratio.
    """
    h, w = image.shape[:2]
    aspect = w / h

    if not auto_size:
        # ↔️ Simple default if auto-sizing is disabled
        return 80.0, 60.0, crystal_depth

    scene_type = classify_image_type(image)

    if scene_type == "portrait":
        width = 60.0  # 📏 Narrower width
        height = width / aspect  # 📏 Taller height
    elif scene_type == "landscape":
        width = 120.0  # 📏 Wider width
        height = width / aspect  # 📏 Shorter height
    else:
        width = 80.0  # 📏 Square
        height = 80.0

    width = round(width / 5) * 5  # 🔢 Round to nearest 5mm
    height = round(height / 5) * 5  # 🔢 Round to nearest 5mm

    return width, height, crystal_depth


def remove_background(image, keep_bg=False):
    """
    ✂️ Remove background from image using rembg if available.

    Args:
        image: Input image (BGR numpy array)
        keep_bg: If True, return original image unchanged

    Returns:
        Image with background removed (or original if keep_bg=True)
    """
    if keep_bg:
        return image  # 🔁 Return original image untouched

    try:
        # 🧠 Prefer rembg (better quality foreground extraction)
        os.environ["ONNXRUNTIME_EXECUTION_PROVIDERS"] = (
            "CPUExecutionProvider"  # 🧠 Force CPU
        )

        from rembg import remove  # ✂️ AI background remover
        from PIL import Image  # 🖼️ PIL wrapper

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # 🔄 Convert BGR → RGB
        pil_img = Image.fromarray(image_rgb)  # 🖼️ Wrap as PIL image

        result = remove(pil_img)  # ✂️ Remove background

        result_rgb = np.array(result)  # 🔢 Back to numpy
        if result_rgb.shape[2] == 4:
            # 🧊 If alpha channel exists, composite over white
            bg = np.ones_like(image_rgb) * 255  # ⚪ White background
            alpha = result_rgb[:, :, 3:4] / 255.0  # 🔍 Normalize alpha
            result_rgb = (result_rgb[:, :, :3] * alpha + bg * (1 - alpha)).astype(
                np.uint8
            )  # 🧮 Blend foreground and background

        return cv2.cvtColor(result_rgb, cv2.COLOR_RGB2BGR)  # 🔁 Back to BGR

    except ImportError:
        print("[warning] rembg not installed - skipping background removal")
        print("[warning] Install with: pip install rembg")
        return image  # 🔁 Fallback to original image
