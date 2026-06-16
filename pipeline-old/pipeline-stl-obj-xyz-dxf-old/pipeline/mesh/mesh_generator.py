# pipeline/mesh/mesh_generator.py
# 🧱 Mesh generator
# - Converts normalized depth map into a 2.5D relief
# - Uses simple physical scaling in X/Y and zmax in Z
# - No crystal box / safety margins: pure depth → 0..zmax mapping

import numpy as np  # 🧮 Numeric operations
import trimesh  # 🔺 Mesh construction + export
import cv2  # 📸 Resizing depth maps


class MeshGenerator:
    def __init__(
        self,
        zmax_mm=40.0,
        depth_gain=1.15,
        width_mm=80.0,
        height_mm=60.0,
        edge_falloff_strength=0.3,
    ):
        # 📏 Maximum relief depth (0 → zmax_mm)
        self.zmax = zmax_mm

        # 🎛️ Foreground / background contrast control
        self.gain = depth_gain

        # 📐 Physical dimensions in mm
        self.width_mm = width_mm
        self.height_mm = height_mm

        # 🌊 Edge falloff factor (0 = off, 0.2–0.4 = nice smooth fade)
        self.edge_falloff_strength = max(0.0, min(float(edge_falloff_strength), 1.0))

    def _apply_edge_falloff(self, depth_norm):
        # 🌊 Create a smooth fade-to-zero near image borders to avoid vertical walls
        if self.edge_falloff_strength <= 0.0:
            return depth_norm  # 🔁 No falloff requested

        h, w = depth_norm.shape  # 📐 Depth map size

        # 🧭 Create normalized coordinate grids ([0..1])
        y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]  # ↕️ Vertical axis
        x = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]  # ↔️ Horizontal axis

        # 📏 Distances to each edge (all shape h×w)
        dist_top = y             # 🔝 Distance from top
        dist_bottom = 1.0 - y    # 🔚 Distance from bottom
        dist_left = x            # ⬅️ Distance from left
        dist_right = 1.0 - x     # ➡️ Distance from right

        # 🧮 Closest-edge distance (0 at border → max at center)
        #    Using chained minimum to avoid NumPy "inhomogeneous shape" errors
        dist_edge = np.minimum(
            np.minimum(dist_top, dist_bottom),
            np.minimum(dist_left, dist_right),
        )

        # 🔁 Normalize to 0..1 (edges → 0, interior → 1)
        edge_fraction = 0.15  # 🎚️ Width of soft fading band (15%)
        mask = dist_edge / max(edge_fraction, 1e-6)
        mask = np.clip(mask, 0.0, 1.0)

        # 🎨 Shape falloff curve (quadratic = soft in center, strong near edges)
        falloff = mask ** 2

        # 🎛️ Blend based on user falloff strength
        falloff *= self.edge_falloff_strength

        # 🌊 Pull depths toward 0.5 near edges to avoid stretched walls
        depth_centered = depth_norm - 0.5
        depth_shaped = depth_centered * falloff
        depth_out = 0.5 + depth_shaped

        return np.clip(depth_out, 0.0, 1.0)  # 🔒 Stay in 0..1


    def build(self, image_bgr, depth_map, target_points=750000):
        # 🧮 Compute grid resolution to hit target_points approximately
        h_orig, w_orig = depth_map.shape
        aspect = w_orig / h_orig  # 📐 width / height

        grid_h = int(np.sqrt(target_points / aspect))  # 🔢 Grid rows
        grid_w = int(grid_h * aspect)                  # 🔢 Grid cols

        # 🔁 Resize depth + RGB image to the same grid
        depth_resized = cv2.resize(depth_map, (grid_w, grid_h))
        image_resized = cv2.resize(image_bgr, (grid_w, grid_h))
        h, w = depth_resized.shape

        print(f"[mesh] Image aspect ratio: {aspect:.2f} (width/height)")
        print(f"[mesh] Grid resolution: {w}×{h} samples")

        # 🎭 SUBJECT MASK – remove background geometry completely
        # Assumes "no-bg" image: subject darker/colored, background near white.
        gray = cv2.cvtColor(image_resized, cv2.COLOR_BGR2GRAY)  # 🎚️ Grayscale
        subject_mask = gray < 245                               # 🎭 True = subject pixel

        # 🧼 Clean up mask (close tiny holes / gaps on the contour)
        subject_mask = cv2.morphologyEx(
            subject_mask.astype(np.uint8),
            cv2.MORPH_CLOSE,
            np.ones((3, 3), np.uint8),
        ).astype(bool)

        # 📊 Normalize depth to [0, 1] (global range)
        d_min = float(depth_resized.min())
        d_max = float(depth_resized.max())
        if d_max - d_min < 1e-6:
            # 🧊 Flat depth map: place surface at mid-depth
            depth_norm = np.full_like(depth_resized, 0.5, dtype=np.float32)
        else:
            depth_norm = (depth_resized - d_min) / (d_max - d_min)
            depth_norm = depth_norm.astype(np.float32)

        # 🧠 LOCAL RELIEF – stop slabs, keep only "bumps" (people, clothes)
        # 1) Blur → large-scale background
        depth_blur = cv2.GaussianBlur(
            depth_norm,
            ksize=(0, 0),
            sigmaX=12.0,
            sigmaY=12.0,
        )  # 🌫️ Smooth global background / tilt

        # 2) Subtract → local deviation
        depth_rel = depth_norm - depth_blur          # 🔍 Local detail (edges, bodies)

        # 3) Clamp negative deviations → no "inward" walls at silhouette
        depth_rel = np.maximum(depth_rel, 0.0)       # 🚫 Only outward relief

        # 4) Re-normalize local relief to [0,1]
        d_max_rel = float(depth_rel.max())
        if d_max_rel < 1e-6:
            depth_norm = np.full_like(depth_rel, 0.5, dtype=np.float32)  # 🧊 Fallback
        else:
            depth_norm = (depth_rel / d_max_rel).astype(np.float32)
            depth_norm = np.clip(depth_norm, 0.0, 1.0)  # 🔒 Clamp 0..1

        # 🎛️ Optional global gain – keep direction, just change contrast
        if abs(self.gain - 1.0) > 1e-3:
            gamma = max(0.2, min(5.0, 1.0 / self.gain))  # 🎚️ Map gain → gamma
            depth_norm = np.power(depth_norm, gamma).astype(np.float32)

        # 🌊 Edge falloff – soften borders, avoid vertical walls
        depth_norm = self._apply_edge_falloff(depth_norm)

        # 🚪 HARD REMOVE BACKGROUND – no depth where mask = False
        depth_norm[~subject_mask] = 0.0  # ❌ Background → Z=0 plane only

        # 📏 Map normalized depth to physical Z coordinates
        zz = depth_norm * self.zmax  # 🧱 0..zmax mm, auto-using full range per image

        # 📐 Generate X/Y coordinates from physical width/height (centered)
        yy, xx = np.meshgrid(
            np.linspace(self.height_mm / 2.0, -self.height_mm / 2.0, h),  # ↕️ Y axis
            np.linspace(-self.width_mm / 2.0, self.width_mm / 2.0, w),    # ↔️ X axis
            indexing="ij",
        )

        # 🧱 Stack into vertices
        vertices = np.stack([xx, yy, zz], axis=-1).reshape(-1, 3)

        # 🔺 Build triangle faces (2 triangles per cell), skipping pure background
        faces = []
        for y in range(h - 1):
            for x in range(w - 1):
                # Vertex indices for this quad
                i00 = y * w + x
                i10 = y * w + (x + 1)
                i01 = (y + 1) * w + x
                i11 = (y + 1) * w + (x + 1)

                # 🎭 Subject coverage
                m00 = subject_mask[y, x]
                m10 = subject_mask[y, x + 1]
                m01 = subject_mask[y + 1, x]
                m11 = subject_mask[y + 1, x + 1]

                # If all four vertices are background, skip this quad completely
                if not (m00 or m10 or m01 or m11):
                    continue  # 🧱 No geometry here

                # 🔺 Triangle 1 (only if at least one corner is subject)
                if m00 or m10 or m01:
                    faces.append([i00, i01, i10])

                # 🔺 Triangle 2
                if m11 or m10 or m01:
                    faces.append([i10, i01, i11])

        faces = np.array(faces, dtype=np.int64)

        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            process=True,
        )  # 🧱 Build Trimesh object

        # 🧼 Ensure normals face towards viewer
        if hasattr(mesh, "fix_normals"):
            mesh.fix_normals()

        xyz = vertices.copy()  # 📤 Dense XYZ point cloud

        # 🧾 Debug info
        z_min, z_max = zz.min(), zz.max()
        x_range = (xx.min(), xx.max())
        y_range = (yy.min(), yy.max())
        depth_range = z_max - z_min

        print(f"[mesh] Generated {len(vertices)} vertices, {len(faces)} faces")
        print(
            f"[mesh] Physical span X={x_range[0]:.1f}..{x_range[1]:.1f} mm "
            f"(~{self.width_mm:.1f} mm)"
        )
        print(
            f"[mesh] Physical span Y={y_range[0]:.1f}..{y_range[1]:.1f} mm "
            f"(~{self.height_mm:.1f} mm)"
        )
        print(
            f"[mesh] Relief Z range: {z_min:.1f}..{z_max:.1f} mm (zmax={self.zmax:.1f} mm)"
        )
        print(f"[mesh] Effective relief depth: {depth_range:.1f} mm")

        return mesh, xyz  # 📤 Trimesh mesh + XYZ numpy array