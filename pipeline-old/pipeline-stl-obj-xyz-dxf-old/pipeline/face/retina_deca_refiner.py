# pipeline/face/retina_deca_refiner.py
# 🙂 Face depth refiner
# - Uses InsightFace RetinaFace detector for multi-face detection
# - Uses DECA to generate detailed depth for each face
# - Blends refined face depth back into the global depth map with feathered edges

import cv2  # 📸 For cropping and resizing
import numpy as np  # 🧮 Masking and blending


class FaceRefiner:
    def __init__(self, device="cuda"):
        # 😊 Load face detector (InsightFace)
        from insightface.app import FaceAnalysis

        # 🧠 Use CPU provider to avoid CUDA ONNX issues
        self.detector = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        self.detector.prepare(ctx_id=-1)  # 🧠 -1 = CPU

        # 🎭 Load DECA (or fail if not installed)
        from decalib.deca import DECA

        self.deca = DECA(device=device)  # 😎 DECA depth extractor
        self.device = device  # 💻 Store device

    def refine(self, image_bgr, depth_map):
        # 🧮 Resize depth map to match image resolution
        h, w = image_bgr.shape[:2]
        depth = cv2.resize(depth_map, (w, h))

        # 🔍 Detect faces on original image (BGR)
        faces = self.detector.get(image_bgr)

        if len(faces) == 0:
            return depth  # ↩️ No faces → return original depth

        result = depth.copy()  # 🧊 Start from base depth

        for face in faces:
            x1, y1, x2, y2 = map(int, face.bbox)  # 📦 Face bounding box
            face_crop = image_bgr[y1:y2, x1:x2]  # ✂️ Crop face region

            if face_crop.shape[0] < 64 or face_crop.shape[1] < 64:
                # ⚠️ Skip tiny faces (too small for DECA)
                continue

            # 🌊 Get DECA depth patch for this face
            depth_patch = self._run_deca_depth(face_crop)
            resized_patch = cv2.resize(depth_patch, (x2 - x1, y2 - y1))

            # 🎨 Create feathered alpha mask for smooth blending
            face_h, face_w = y2 - y1, x2 - x1
            feather_x = max(int(face_w * 0.15), 10)  # ↔️ Feather width
            feather_y = max(int(face_h * 0.15), 10)  # ↕️ Feather height

            mask = np.ones((face_h, face_w), dtype=np.float32)  # 🧊 Base mask

            # 🌫️ Gaussian blur for soft edges
            mask = cv2.GaussianBlur(
                mask,
                (0, 0),
                sigmaX=feather_x / 2,
                sigmaY=feather_y / 2,
            )

            # 🧱 Extra falloff near edges via linear ramps
            for i in range(feather_y):
                alpha = i / feather_y
                mask[i, :] *= alpha  # 🔻 Top edge
                mask[-(i + 1), :] *= alpha  # 🔺 Bottom edge

            for i in range(feather_x):
                alpha = i / feather_x
                mask[:, i] *= alpha  # ◀️ Left edge
                mask[:, -(i + 1)] *= alpha  # ▶️ Right edge

            mask = np.clip(mask, 0, 1)  # 📊 Clamp mask to [0,1]

            # 🎚️ Alpha blend DECA depth into original depth
            original_region = depth[y1:y2, x1:x2]  # 🧊 Base depth slice
            blended = resized_patch * mask + original_region * (1 - mask)  # 🧮 Blend

            result[y1:y2, x1:x2] = blended  # 🧱 Write blended region back

        return result  # 📤 Refined depth map

    def _run_deca_depth(self, face_bgr):
        # 🔄 Convert BGR → RGB and resize for DECA
        import torch
        from PIL import Image

        face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)  # 🔄 Colorspace
        pil_img = Image.fromarray(face_rgb).resize((224, 224))  # 🖼️ Normalize size

        depth_map = self.deca.extract_depth(pil_img)  # 🌊 DECA depth inference
        return depth_map  # 📤 Depth patch as numpy or tensor
