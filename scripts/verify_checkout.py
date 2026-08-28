from __future__ import annotations

import hashlib
import importlib
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
MODEL = ROOT / "models" / "yolov8n-DotMetrics.pt"
EXPECTED_MODEL_SHA256 = "db994f722d05fba38498894f30f3103f5e15a99684ea1549ef699d1dc23ce9c1"
REQUIRED_IMPORTS = (
    "cv2",
    "matplotlib",
    "numpy",
    "PIL",
    "PySide6.QtCore",
    "scipy",
    "torch",
    "torchvision",
    "ultralytics",
)


def main() -> int:
    sys.path.insert(0, str(SOURCE))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    if not MODEL.is_file():
        raise FileNotFoundError(f"Bundled model is missing: {MODEL}")

    digest = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    if digest != EXPECTED_MODEL_SHA256:
        raise RuntimeError(f"Model checksum mismatch: {digest}")

    for module_name in REQUIRED_IMPORTS:
        importlib.import_module(module_name)

    with tempfile.TemporaryDirectory(prefix="dotmetrics_verify_") as temp_dir:
        os.environ["DOTMETRICS_DATA_DIR"] = temp_dir
        from dotmetrics import __version__
        from dotmetrics.app import main as application_main
        from dotmetrics.core.runtime_paths import resolve_model_path

        if __version__ != "1.0.0":
            raise RuntimeError(f"Unexpected package version: {__version__}")
        if not callable(application_main):
            raise RuntimeError("Application entry point is not callable")
        if resolve_model_path() != MODEL:
            raise RuntimeError("Runtime model resolution does not select the bundled model")

    print(f"DotMetrics checkout verified (model SHA-256: {digest}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
