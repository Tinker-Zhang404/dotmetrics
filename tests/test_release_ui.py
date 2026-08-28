import os
import unittest
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QPushButton, QScrollArea

from src.dotmetrics.ui.main_window import MainWindow


class ReleaseUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow(preload_model=False)

    def tearDown(self):
        self.window.close()

    def test_release_has_no_paper_validation_controls(self):
        self.assertEqual(self.window.windowTitle(), "DotMetrics v1.0.0")
        self.assertFalse(hasattr(self.window, "validation_mode_checkbox"))
        self.assertFalse(hasattr(self.window, "expert_id_edit"))

    def test_control_panel_scrolls_and_buttons_keep_readable_height(self):
        self.assertIsInstance(self.window.left_scroll, QScrollArea)
        buttons = self.window.left_scroll.findChildren(QPushButton)
        self.assertTrue(buttons)
        self.assertTrue(all(button.minimumHeight() >= 36 for button in buttons))
        self.assertFalse(hasattr(self.window, "lock_manual_button"))

    def test_analysis_requires_image_calibration_and_ready_model(self):
        self.assertFalse(self.window.analyze_button.isEnabled())
        self.window.current_image_bgr = np.zeros((32, 32, 3), dtype=np.uint8)
        self.window.is_calibrated = True
        self.window.model_ready = True
        self.window._update_action_states()
        self.assertTrue(self.window.analyze_button.isEnabled())

    def test_python_sources_contain_no_chinese_ui_text(self):
        source_root = Path(__file__).resolve().parents[1] / "src"
        for path in source_root.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            self.assertFalse(
                any("\u4e00" <= character <= "\u9fff" for character in content),
                f"Chinese text remains in {path}",
            )


if __name__ == "__main__":
    unittest.main()
