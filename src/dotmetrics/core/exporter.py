from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from ..domain.models import AnalysisResult, DetectionSettings, MeasurementLine
from .logging_utils import logger
from .visualization import Visualizer


class ResultExporter:
    HISTOGRAM_BINS = 10

    def export(
        self,
        destination_dir: str | Path,
        source_image_path: str | Path | None,
        source_image_bgr: np.ndarray,
        calibration_factor: float,
        is_calibrated: bool,
        analysis_result: AnalysisResult,
        filtered_particles: set[int],
        measurement_lines: list[MeasurementLine],
        settings: DetectionSettings,
        ui_log_text: str,
    ) -> Path:
        base_name = Path(source_image_path).stem if source_image_path else "analysis"
        output_dir = Path(destination_dir) / f"DotMetrics_{base_name}"
        output_dir.mkdir(parents=True, exist_ok=True)

        annotated_path = output_dir / f"result_{base_name}.png"
        histogram_path = output_dir / f"hist_{base_name}.png"
        stats_path = output_dir / f"stats_{base_name}.png"
        csv_path = output_dir / f"report_{base_name}.csv"
        origin_distribution_path = output_dir / f"origin_distribution_{base_name}.csv"
        log_path = output_dir / f"analysis_log_{base_name}.txt"
        filter_log_path = output_dir / f"filter_log_{base_name}.txt"

        annotated = source_image_bgr.copy()
        for particle in analysis_result.particles:
            contour = particle.contour.astype(np.int32)
            x1, y1, _x2, _y2 = particle.bbox
            if particle.id in filtered_particles:
                color = (128, 128, 128)
                label = f"X {particle.diameter_nm:.1f}nm"
            else:
                color = (0, 255, 0)
                label = f"{particle.diameter_nm:.1f}nm"
            cv2.drawContours(annotated, [contour], -1, color, 1)
            cv2.putText(annotated, label, (x1, max(y1 - 6, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 2)

        for line in measurement_lines:
            start = tuple(int(round(value)) for value in line.start_px)
            end = tuple(int(round(value)) for value in line.end_px)
            cv2.line(annotated, start, end, (0, 0, 255), 2)
            mid_x = int((start[0] + end[0]) / 2)
            mid_y = int((start[1] + end[1]) / 2)
            cv2.putText(annotated, f"{line.diameter_nm:.1f}nm", (mid_x, max(mid_y - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        cv2.imwrite(str(annotated_path), annotated)

        measurements = analysis_result.combined_measurements(filtered_particles, measurement_lines)
        Visualizer.create_histogram(measurements, histogram_path)
        Visualizer.create_stats_table(measurements, stats_path)

        with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Type", "ID", "Diameter(nm)", "X1", "Y1", "X2", "Y2", "Status"])
            for particle in analysis_result.particles:
                x1, y1, x2, y2 = particle.bbox
                writer.writerow([
                    "particle",
                    particle.id,
                    f"{particle.diameter_nm:.3f}",
                    x1,
                    y1,
                    x2,
                    y2,
                    "filtered" if particle.id in filtered_particles else "kept",
                ])
            for line in measurement_lines:
                writer.writerow([
                    "manual_line",
                    line.id,
                    f"{line.diameter_nm:.3f}",
                    f"{line.start_px[0]:.2f}",
                    f"{line.start_px[1]:.2f}",
                    f"{line.end_px[0]:.2f}",
                    f"{line.end_px[1]:.2f}",
                    "manual_measurement",
                ])

        self._write_origin_distribution_csv(origin_distribution_path, measurements)

        with log_path.open("w", encoding="utf-8") as handle:
            handle.write(f"DotMetrics Analysis Report - {datetime.now()}\n")
            handle.write("=" * 60 + "\n")
            handle.write(f"Image file: {source_image_path}\n")
            handle.write(f"Calibration factor: {calibration_factor:.6f} nm/px\n")
            handle.write(f"Calibration enabled: {is_calibrated}\n")
            handle.write(f"YOLO used: {analysis_result.used_yolo}\n")
            handle.write(f"YOLO model path: {analysis_result.model_path}\n")
            handle.write(f"Confidence: {settings.conf:.2f}\n")
            handle.write(f"IoU: {settings.iou:.2f}\n")
            handle.write(f"Max detections: {settings.max_det}\n")
            handle.write(f"Origin distribution csv: {origin_distribution_path.name}\n\n")

            handle.write("Particle stats:\n")
            kept_measurements = analysis_result.particle_measurements(filtered_particles)
            handle.write(f"  Total particles: {len(analysis_result.particles)}\n")
            handle.write(f"  Kept particles: {len(kept_measurements)}\n")
            handle.write(f"  Filtered particles: {len(filtered_particles)}\n")
            handle.write(f"  Manual lines: {len(measurement_lines)}\n")
            if measurements:
                handle.write(f"  Mean size: {np.mean(measurements):.2f} nm\n")
                handle.write(f"  Std dev: {np.std(measurements):.2f} nm\n")
                handle.write(f"  Median size: {np.median(measurements):.2f} nm\n")
                handle.write(f"  Min size: {np.min(measurements):.2f} nm\n")
                handle.write(f"  Max size: {np.max(measurements):.2f} nm\n")
            handle.write("\nUI log:\n")
            handle.write(ui_log_text.strip())
            handle.write("\n")

        with filter_log_path.open("w", encoding="utf-8") as handle:
            handle.write(f"Filtered particles - {datetime.now()}\n")
            handle.write("=" * 60 + "\n")
            for particle_id in sorted(filtered_particles):
                particle = next((item for item in analysis_result.particles if item.id == particle_id), None)
                if particle is not None:
                    handle.write(f"Particle {particle.id}: {particle.diameter_nm:.2f} nm\n")

        logger.info("Export completed at %s", output_dir)
        return output_dir

    def _write_origin_distribution_csv(self, output_path: Path, measurements: list[float]) -> None:
        rows = self._build_origin_distribution_rows(measurements)
        with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Count", "Percentage", "Diameter range (nm)", "Bin midpoint (nm)"])
            for count, percentage, lower, upper, midpoint in rows:
                if count <= 0:
                    continue
                writer.writerow([
                    count,
                    f"{percentage:.2f}",
                    f"{lower:.2f}-{upper:.2f}",
                    f"{midpoint:.2f}",
                ])

    @classmethod
    def _build_origin_distribution_rows(cls, measurements: list[float]) -> list[tuple[int, float, float, float, float]]:
        if not measurements:
            return []

        values = np.asarray(measurements, dtype=float)
        if values.size == 0:
            return []

        counts, edges = np.histogram(values, bins=cls.HISTOGRAM_BINS)
        total = float(values.size)
        rows: list[tuple[int, float, float, float, float]] = []

        for index, count in enumerate(counts):
            lower = float(edges[index])
            upper = float(edges[index + 1])
            midpoint = (lower + upper) / 2
            percentage = float(count) / total * 100.0
            rows.append((int(count), percentage, lower, upper, midpoint))

        return rows
