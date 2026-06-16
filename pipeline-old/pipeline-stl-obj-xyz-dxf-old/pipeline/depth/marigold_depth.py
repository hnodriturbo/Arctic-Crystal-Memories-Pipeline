# pipeline/depth/marigold_depth.py
# 🌊 Marigold Depth Estimator
# - Loads MarigoldDepthPipeline from HuggingFace
# - Infers normalized depth map in [0,1]
# - Supports CPU and CUDA (fp16 on CUDA)

import torch  # 🧠 Tensor engine
from PIL import Image  # 🖼️ Image wrapper
import torchvision.transforms as T  # 🔧 (kept for future use)


class MarigoldDepth:
    def __init__(self, device="cuda"):
        # 🚀 Delayed heavy imports so CLI starts fast
        from diffusers import MarigoldDepthPipeline
        import os

        print("[depth] Loading Marigold model (may take a bit on first run)...")
        print(
            "[depth] If model download hangs, try deleting cache: "
            '"$HOME/.cache/huggingface/hub/models--prs-eth--marigold-depth-v1-1"'
        )

        # 🚫 Disable progress bars to avoid stuck downloads in some terminals
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

        # ⚙️ Configure dtype & variant based on device
        torch_dtype = torch.float16 if device == "cuda" else torch.float32
        variant = "fp16" if device == "cuda" else None

        # 📥 Load pipeline from HuggingFace Hub
        self.pipe = MarigoldDepthPipeline.from_pretrained(
            "prs-eth/marigold-depth-v1-1",
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,  # 🧠 Reduce memory spikes
            variant=variant,  # 🧊 fp16 weights on CUDA
            local_files_only=False,  # ☁️ Allow re-download
            resume_download=True,  # 🔁 Resume partial downloads
        ).to(device)

        print("[depth] Marigold model loaded successfully")
        self.device = device  # 💻 Store device choice

    def predict(self, image_bgr, invert=False):
        import numpy as np  # 🧮 Local import for light init

        # 🔄 Convert BGR numpy image to RGB PIL image
        image_rgb = Image.fromarray(image_bgr[:, :, ::-1])

        # 🌊 Run depth estimation
        result = self.pipe(image_rgb)  # 🧠 Inference call
        depth = result.prediction  # 🔢 Marigold v1-1 returns numpy array or tensor

        # 🔁 Convert torch tensor → numpy if needed
        if hasattr(depth, "cpu"):
            depth_np = depth.squeeze().cpu().numpy()
        else:
            depth_np = np.array(depth).squeeze()

        # 📊 Normalize to [0,1]
        d_min = depth_np.min()
        d_max = depth_np.max()
        depth_norm = (depth_np - d_min) / (d_max - d_min + 1e-8)

        # 🔄 Optional inversion
        if invert:
            depth_norm = 1.0 - depth_norm

        return depth_norm  # 📤 Float32 depth map in [0,1]
