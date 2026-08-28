import sys
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.dotmetrics.core.exporter import ResultExporter
from src.dotmetrics.core.runtime_paths import project_root, resolve_model_path
from src.dotmetrics.domain.models import AnalysisResult, DetectionSettings, MeasurementLine, Particle


class DetectionSettingsTests(unittest.TestCase):
    def test_clamped_and_serialized(self):
        settings = DetectionSettings(conf=1.5, iou=0.0, max_det=-2).clamped()
        self.assertEqual(settings.conf, 0.99)
        self.assertEqual(settings.iou, 0.05)
        self.assertEqual(settings.max_det, 1)
        self.assertEqual(settings.as_dict(), {"conf": 0.99, "iou": 0.05, "max_det": 1})


class RuntimePathTests(unittest.TestCase):
    EXPECTED_MODEL_SHA256 = "db994f722d05fba38498894f30f3103f5e15a99684ea1549ef699d1dc23ce9c1"

    def test_source_mode_model_resolution_uses_project_model(self):
        path = resolve_model_path()
        self.assertIsNotNone(path)
        self.assertEqual(path, project_root() / "models" / "yolov8n-DotMetrics.pt")

    def test_bundled_model_checksum(self):
        model_path = project_root() / "models" / "yolov8n-DotMetrics.pt"
        digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
        self.assertEqual(digest, self.EXPECTED_MODEL_SHA256)

    def test_environment_override_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_model = Path(temp_dir) / "custom.pt"
            custom_model.write_bytes(b"model")
            with mock.patch.dict(os.environ, {"DOTMETRICS_MODEL_PATH": str(custom_model)}):
                resolved = resolve_model_path()
            self.assertEqual(resolved, custom_model)

    def test_frozen_mode_prefers_bundle_resource(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            model_dir = Path(temp_dir) / "models"
            model_dir.mkdir(parents=True)
            bundle_model = model_dir / "yolov8n-DotMetrics.pt"
            bundle_model.write_bytes(b"model")
            with mock.patch.object(sys, "_MEIPASS", temp_dir, create=True):
                resolved = resolve_model_path()
            self.assertEqual(resolved, bundle_model)


class MeasurementAggregationTests(unittest.TestCase):
    def test_combined_measurements_respect_filtered_particles_and_manual_lines(self):
        particle_a = Particle(1, 10.0, (0, 0, 10, 10), contour=self._dummy_contour(), center=(5, 5))
        particle_b = Particle(2, 20.0, (20, 20, 30, 30), contour=self._dummy_contour(), center=(25, 25))
        result = AnalysisResult(particles=[particle_a, particle_b])
        lines = [MeasurementLine(id=1, start_px=(0.0, 0.0), end_px=(10.0, 0.0), diameter_nm=12.5)]

        measurements = result.combined_measurements(filtered_particles={2}, measurement_lines=lines)
        self.assertEqual(measurements, [10.0, 12.5])

    @staticmethod
    def _dummy_contour():
        return [[[0, 0]], [[1, 0]], [[1, 1]], [[0, 1]]]


class OriginDistributionExportTests(unittest.TestCase):
    def test_build_distribution_rows_has_expected_shape(self):
        rows = ResultExporter._build_origin_distribution_rows([1.1, 1.5, 1.9, 2.3, 2.7, 3.1, 3.5, 3.9])

        self.assertEqual(len(rows), ResultExporter.HISTOGRAM_BINS)
        self.assertEqual(sum(row[0] for row in rows), 8)

        for count, percentage, lower, upper, midpoint in rows:
            self.assertGreaterEqual(count, 0)
            self.assertGreaterEqual(percentage, 0.0)
            self.assertLessEqual(percentage, 100.0)
            self.assertLess(lower, upper)
            self.assertGreater(midpoint, lower)
            self.assertLess(midpoint, upper)

    def test_write_origin_distribution_csv_outputs_expected_headers(self):
        exporter = ResultExporter()
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "origin_distribution.csv"
            exporter._write_origin_distribution_csv(output_path, [1.0, 1.2, 1.4, 1.6])
            content = output_path.read_text(encoding="utf-8-sig")

        self.assertIn("Count,Percentage,Diameter range (nm),Bin midpoint (nm)", content)

    def test_build_distribution_rows_returns_empty_for_no_data(self):
        self.assertEqual(ResultExporter._build_origin_distribution_rows([]), [])


if __name__ == "__main__":
    unittest.main()
