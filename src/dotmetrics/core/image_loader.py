from __future__ import annotations

import traceback
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .logging_utils import logger


class ImageLoader:
    """Loads microscopy images while handling large TIFF sources safely."""

    @staticmethod
    def load_image(
        file_path: str | Path,
        max_dimension: int = 10000,
    ) -> tuple[np.ndarray | None, float]:
        path = Path(file_path)
        try:
            logger.info("Loading image: %s", path)
            if not path.exists():
                logger.error("Image does not exist: %s", path)
                return None, 1.0

            pil_image: Image.Image | None
            scale_factor = 1.0

            if path.suffix.lower() in {".tif", ".tiff"}:
                pil_image = ImageLoader._load_tiff_safe(path, max_dimension)
            else:
                try:
                    pil_image = Image.open(path)
                    if hasattr(pil_image, "n_frames") and pil_image.n_frames > 1:
                        pil_image.seek(0)
                except Exception as exc:
                    logger.warning("PIL failed for %s, falling back to OpenCV: %s", path, exc)
                    return ImageLoader._load_with_opencv(path, max_dimension)

            if pil_image is None:
                logger.error("All image loading strategies failed for %s", path)
                return None, 1.0

            if pil_image.mode in {"RGBA", "LA"}:
                background = Image.new("RGB", pil_image.size, (255, 255, 255))
                background.paste(pil_image, mask=pil_image.split()[-1])
                pil_image = background
            elif pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")

            array = np.array(pil_image)
            if len(array.shape) == 3 and array.shape[2] == 3:
                array = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)

            logger.info("Loaded image shape: %s", array.shape)
            return array, scale_factor
        except Exception as exc:
            logger.error("Image loading failed: %s", exc)
            traceback.print_exc()
            return None, 1.0

    @staticmethod
    def _load_tiff_safe(file_path: Path, max_dimension: int) -> Image.Image | None:
        try:
            pil_image = Image.open(file_path)
            width, height = pil_image.size
            logger.info("TIFF dimensions: %sx%s", width, height)

            if width > max_dimension or height > max_dimension:
                scale = min(max_dimension / width, max_dimension / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info("Downsampled TIFF to %sx%s", new_width, new_height)

            return pil_image
        except (OSError, IOError, Image.UnidentifiedImageError) as exc:
            logger.error("TIFF load failed via PIL: %s", exc)
            try:
                array = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
                if array is None:
                    return None
                if len(array.shape) == 2:
                    return Image.fromarray(array)
                return Image.fromarray(cv2.cvtColor(array, cv2.COLOR_BGR2RGB))
            except Exception as cv_exc:
                logger.error("TIFF load failed via OpenCV too: %s", cv_exc)
                return None

    @staticmethod
    def _load_with_opencv(file_path: Path, max_dimension: int) -> tuple[np.ndarray | None, float]:
        try:
            array = cv2.imread(str(file_path))
            if array is None:
                logger.error("OpenCV could not load image: %s", file_path)
                return None, 1.0

            height, width = array.shape[:2]
            scale_factor = 1.0
            if width > max_dimension or height > max_dimension:
                scale = min(max_dimension / width, max_dimension / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                array = cv2.resize(array, (new_width, new_height))
                scale_factor = scale
                logger.info("OpenCV downsampled image to %sx%s", new_width, new_height)
            return array, scale_factor
        except Exception as exc:
            logger.error("OpenCV image loading failed: %s", exc)
            return None, 1.0
