from __future__ import annotations

import traceback
from threading import Lock
from pathlib import Path

import cv2
import numpy as np

from ..domain.models import AnalysisResult, DetectionSettings, Particle
from .logging_utils import logger
from .runtime_paths import resolve_model_path


_YOLO_CLASS = None
_YOLO_IMPORT_ATTEMPTED = False


MIN_PARTICLE_AREA = 10


def _get_yolo_class():
    global _YOLO_CLASS
    global _YOLO_IMPORT_ATTEMPTED

    if _YOLO_IMPORT_ATTEMPTED:
        return _YOLO_CLASS

    _YOLO_IMPORT_ATTEMPTED = True
    try:
        from ultralytics import YOLO as yolo_class

        _YOLO_CLASS = yolo_class
    except Exception as exc:
        logger.info("Ultralytics unavailable, YOLO disabled: %s", exc)
        _YOLO_CLASS = None

    return _YOLO_CLASS


class ParticleAnalyzer:
    def __init__(self, model_path: str | Path | None = None, prefer_yolo: bool = True):
        self.model_path = resolve_model_path(override=model_path) if model_path else resolve_model_path()
        self.prefer_yolo = prefer_yolo
        self.model = None
        self.use_yolo = False
        self._model_init_attempted = False
        self._model_init_lock = Lock()

    def initialize_model(self) -> bool:
        """Load the detector once and return whether it is ready for inference."""
        with self._model_init_lock:
            if self._model_init_attempted:
                return self.use_yolo and self.model is not None

            self._model_init_attempted = True
            if not self.prefer_yolo or self.model_path is None:
                return False

            yolo_class = _get_yolo_class()
            if yolo_class is None:
                return False

            try:
                logger.info("Loading YOLO model from %s", self.model_path)
                self.model = yolo_class(str(self.model_path))
                logger.info("Warming up the YOLO inference backend")
                self.model.predict(
                    np.zeros((640, 640, 3), dtype=np.uint8),
                    imgsz=640,
                    conf=0.99,
                    max_det=1,
                    verbose=False,
                )
                self.use_yolo = True
            except Exception as exc:
                logger.error("Unable to load YOLO model: %s", exc)
                self.model = None
                self.use_yolo = False

            return self.use_yolo and self.model is not None

    def analyze(
        self,
        img_bgr: np.ndarray,
        calibration_factor: float,
        settings: DetectionSettings,
    ) -> AnalysisResult:
        settings = settings.clamped()
        result = AnalysisResult(used_yolo=False, model_path=str(self.model_path) if self.model_path else None, settings=settings)

        try:
            if img_bgr is None:
                raise ValueError("Input image is empty")

            logger.info(
                "Starting analysis: shape=%s calibration_factor=%.6f conf=%.2f iou=%.2f max_det=%s",
                img_bgr.shape,
                calibration_factor,
                settings.conf,
                settings.iou,
                settings.max_det,
            )

            if self.prefer_yolo and not self._model_init_attempted:
                self.initialize_model()

            image_for_analysis = img_bgr.copy()
            particles: list[Particle] = []
            boxes: list[np.ndarray] = []

            if self.use_yolo and self.model is not None:
                try:
                    model_results = self.model.predict(
                        image_for_analysis,
                        conf=settings.conf,
                        iou=settings.iou,
                        max_det=settings.max_det,
                        verbose=False,
                    )
                    if model_results and getattr(model_results[0], "boxes", None) is not None:
                        boxes = model_results[0].boxes.xyxy.cpu().numpy().tolist()
                        result.used_yolo = True
                    logger.info("YOLO detected %s regions", len(boxes))
                except Exception as exc:
                    logger.warning("YOLO inference failed, falling back to OTSU: %s", exc)
                    boxes = []
                    result.used_yolo = False

            if boxes:
                for box in boxes:
                    particle = self._analyze_roi_with_yolo(image_for_analysis, np.array(box), calibration_factor, len(particles) + 1)
                    if particle is not None:
                        particles.append(particle)
            else:
                particles = self._analyze_with_otsu(image_for_analysis, calibration_factor)

            result.particles = particles
            logger.info("Analysis complete: %s particles", len(particles))
            return result
        except Exception as exc:
            logger.error("Analysis failed: %s", exc)
            traceback.print_exc()
            raise

    def _analyze_roi_with_yolo(
        self,
        img_bgr: np.ndarray,
        box: np.ndarray,
        calibration_factor: float,
        particle_id: int,
    ) -> Particle | None:
        try:
            x1, y1, x2, y2 = map(int, box)
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(img_bgr.shape[1] - 1, x2)
            y2 = min(img_bgr.shape[0] - 1, y2)
            if x2 - x1 < 4 or y2 - y1 < 4:
                return None

            roi = img_bgr[y1:y2, x1:x2]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.medianBlur(gray, 3)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None

            contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(contour)
            if area < MIN_PARTICLE_AREA:
                return None

            diameter_px = 2 * np.sqrt(area / np.pi)
            diameter_nm = float(diameter_px * calibration_factor)
            contour_offset = contour + np.array([[x1, y1]])
            bbox = (x1, y1, x2, y2)
            center = (int(x1 + (x2 - x1) / 2), int(y1 + (y2 - y1) / 2))
            return Particle(particle_id, diameter_nm, bbox, contour_offset, center)
        except Exception as exc:
            logger.error("ROI analysis failed: %s", exc)
            return None

    def _analyze_with_otsu(self, img_bgr: np.ndarray, calibration_factor: float) -> list[Particle]:
        try:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            logger.info("OTSU found %s contours", len(contours))

            particles: list[Particle] = []
            particle_id = 1
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < MIN_PARTICLE_AREA:
                    continue
                diameter_px = 2 * np.sqrt(area / np.pi)
                diameter_nm = float(diameter_px * calibration_factor)
                x, y, w, h = cv2.boundingRect(contour)
                bbox = (x, y, x + w, y + h)
                center = (int(x + w / 2), int(y + h / 2))
                particles.append(Particle(particle_id, diameter_nm, bbox, contour, center))
                particle_id += 1
            return particles
        except Exception as exc:
            logger.error("OTSU analysis failed: %s", exc)
            return []
