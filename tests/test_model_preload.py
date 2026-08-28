import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.dotmetrics.core.analyzer import ParticleAnalyzer


class FakeYolo:
    load_count = 0
    predict_count = 0

    def __init__(self, _model_path):
        type(self).load_count += 1

    def predict(self, *_args, **_kwargs):
        type(self).predict_count += 1
        return []


class ModelPreloadTests(unittest.TestCase):
    def test_initialize_model_loads_detector_only_once(self):
        FakeYolo.load_count = 0
        FakeYolo.predict_count = 0
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model.pt"
            model_path.write_bytes(b"model")
            analyzer = ParticleAnalyzer(model_path=model_path)
            with mock.patch("src.dotmetrics.core.analyzer._get_yolo_class", return_value=FakeYolo):
                self.assertTrue(analyzer.initialize_model())
                self.assertTrue(analyzer.initialize_model())

        self.assertEqual(FakeYolo.load_count, 1)
        self.assertEqual(FakeYolo.predict_count, 1)


if __name__ == "__main__":
    unittest.main()
