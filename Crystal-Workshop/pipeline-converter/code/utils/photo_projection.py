"""
Purpose:
 - Project a paired photo onto reconstructed vertices without reading CI data.
 - Ambiguous scene projections require an explicit operator choice.
"""

from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageOps


def load_photo(source):
    """Read only the scene XML and the SolidEntity's named texture member."""
    source = Path(source)
    direction = None
    if source.suffix.lower() != ".cockpit":
        with Image.open(source) as image:
            return ImageOps.exif_transpose(image).convert("RGB"), direction
    with ZipFile(source) as archive:
        xml_info = archive.getinfo("CockpitScene.xml")
        if xml_info.file_size > 4 * 1024 * 1024:
            raise ValueError("Scene XML exceeds 4 MB.")
        scene = ET.fromstring(archive.read(xml_info))
        entities = [node for node in scene.iter() if node.tag.split("}")[-1] == "SolidEntity" and node.get("Texture")]
        if len(entities) != 1:
            raise ValueError("Choose a photo directly: scene must contain exactly one textured SolidEntity.")
        texture = entities[0].get("Texture")
        if Path(texture).suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("Scene texture must be a JPEG or PNG.")
        info = archive.getinfo(texture)
        if info.file_size > 64 * 1024 * 1024:
            raise ValueError("Scene photo exceeds 64 MB.")
        settings = [node for node in scene.iter() if node.tag.split("}")[-1] == "ProjectionSetting" and node.get("Enabled", "True").lower() == "true"]
        directions = {node.get("Direction") for node in settings if node.get("Direction")}
        if len(directions) == 1:
            direction = directions.pop()
        with Image.open(BytesIO(archive.read(info))) as image:
            return ImageOps.exif_transpose(image).convert("RGB"), direction


def photo_uv(vertices, source, plane="auto", flip_u=False, flip_v=False):
    """Bounds-based alignment is adjustable; no inferred scene pairing is hidden."""
    photo, direction = load_photo(source)
    if plane == "auto":
        if Path(source).suffix.lower() == ".cockpit":
            # Recognize explicit axis names only; undocumented enum values are not guessed.
            plane = {"X": "yz", "Y": "xz", "Z": "xy", "-X": "yz", "-Y": "xz", "-Z": "xy"}.get(str(direction).upper())
            if plane is None:
                raise ValueError(f"Unrecognized projection direction {direction!r}; select XY, XZ or YZ explicitly.")
        else:
            plane = "xy"
    axes = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}[plane]
    coordinates = vertices[:, axes]
    extent = np.ptp(coordinates, axis=0)
    if np.any(extent <= 0):
        raise ValueError("Photo projection plane has zero width or height.")
    uv = (coordinates - coordinates.min(axis=0)) / extent
    if flip_u:
        uv[:, 0] = 1 - uv[:, 0]
    if flip_v:
        uv[:, 1] = 1 - uv[:, 1]
    return photo, uv


def vertex_colors(vertices, source, plane="auto", flip_u=False, flip_v=False):
    """Sample RGB at projected vertex coordinates."""
    photo, uv = photo_uv(vertices, source, plane, flip_u, flip_v)
    pixels = np.asarray(photo)
    x = np.rint(uv[:, 0] * (photo.width - 1)).astype(int)
    y = np.rint((1 - uv[:, 1]) * (photo.height - 1)).astype(int)
    return np.column_stack((pixels[y, x], np.full(len(vertices), 255, dtype=np.uint8)))
