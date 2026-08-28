from __future__ import annotations

from dataclasses import dataclass, field
from typing import Collection, Iterable


DEFAULT_CONFIDENCE = 0.10
DEFAULT_IOU = 0.30
DEFAULT_MAX_DETECTIONS = 2000


@dataclass(slots=True)
class DetectionSettings:
    conf: float = DEFAULT_CONFIDENCE
    iou: float = DEFAULT_IOU
    max_det: int = DEFAULT_MAX_DETECTIONS

    def __post_init__(self) -> None:
        self.conf = float(self.conf)
        self.iou = float(self.iou)
        self.max_det = int(self.max_det)

    def clamped(self) -> "DetectionSettings":
        return DetectionSettings(
            conf=min(max(self.conf, 0.01), 0.99),
            iou=min(max(self.iou, 0.05), 0.95),
            max_det=max(self.max_det, 1),
        )

    def as_dict(self) -> dict[str, float | int]:
        return {
            "conf": self.conf,
            "iou": self.iou,
            "max_det": self.max_det,
        }


@dataclass(slots=True)
class Particle:
    id: int
    diameter_nm: float
    bbox: tuple[int, int, int, int]
    contour: object
    center: tuple[int, int]

    def contains(self, x: float, y: float) -> bool:
        x1, y1, x2, y2 = self.bbox
        return x1 <= x <= x2 and y1 <= y <= y2

    @property
    def area_hint(self) -> int:
        x1, y1, x2, y2 = self.bbox
        return max(0, x2 - x1) * max(0, y2 - y1)


@dataclass(slots=True)
class MeasurementLine:
    id: int
    start_px: tuple[float, float]
    end_px: tuple[float, float]
    diameter_nm: float


@dataclass(slots=True)
class AnalysisResult:
    particles: list[Particle] = field(default_factory=list)
    used_yolo: bool = False
    model_path: str | None = None
    settings: DetectionSettings = field(default_factory=DetectionSettings)

    def particle_measurements(
        self,
        filtered_particles: Collection[int] | None = None,
    ) -> list[float]:
        excluded = set(filtered_particles or [])
        return [particle.diameter_nm for particle in self.particles if particle.id not in excluded]

    def combined_measurements(
        self,
        filtered_particles: Collection[int] | None = None,
        measurement_lines: Iterable[MeasurementLine] | None = None,
    ) -> list[float]:
        values = self.particle_measurements(filtered_particles)
        if measurement_lines:
            values.extend(line.diameter_nm for line in measurement_lines)
        return values
