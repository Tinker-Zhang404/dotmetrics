# DotMetrics

DotMetrics is a desktop application for calibrated particle-size analysis of transmission electron microscopy (TEM) images. It combines YOLO-based particle localization with local image processing, interactive review, manual diameter measurements, and reproducible result export.

## Features

- Opens common TEM image formats, including PNG, JPEG, TIFF, and BMP.
- Preloads the detector in the background so the first analysis does not pause for model initialization.
- Calibrates image scale from a visible scale bar.
- Localizes candidate particles with the bundled DotMetrics YOLOv8n weights.
- Segments each detected region and reports equivalent circular diameter in nanometres.
- Lets the operator inspect contours, exclude false detections, restore excluded particles, and add manual diameter lines.
- Exports annotated images, per-particle measurements, size distributions, summary statistics, and an analysis log.

## Intended Scope

The bundled detector was developed for visually separable carbon-dot-like nanoparticles in TEM images. DotMetrics is an analysis aid, not an autonomous metrology authority. Scale calibration and human review remain required. See [MODEL_CARD.md](MODEL_CARD.md) for intended use and limitations.

## Quick Start

DotMetrics requires Python 3.11 or later. On Windows PowerShell:

```powershell
git clone https://github.com/Tinker-Zhang404/dotmetrics-tem.git
cd dotmetrics-tem
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
dotmetrics
```

For the exact dependency versions used in release verification, replace the editable-install command above with:

```powershell
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
python scripts/verify_checkout.py
dotmetrics
```

The application opens immediately while the detector loads in a background thread. `Run Analysis` becomes available when an image is loaded, scale calibration is complete, and the status reads `Detector: ready`.

## Basic Workflow

1. Select `Open TEM Image`.
2. Select `Calibrate Scale` and mark the two endpoints of the image scale bar.
3. Enter the scale-bar length in nanometres and confirm the calibration.
4. Keep the default confidence and IoU values or adjust them for the image.
5. Select `Run Analysis`.
6. Inspect the detected contours in `Analysis Results`.
7. Exclude false detections or add manual diameter lines where appropriate.
8. Select `Export Results` and choose an output directory.

Detailed instructions are in [USER_GUIDE.md](USER_GUIDE.md).

## Exported Results

Each export creates a `DotMetrics_<image-name>` directory containing:

- `result_<image-name>.png`: annotated image.
- `report_<image-name>.csv`: automated and manual measurements.
- `origin_distribution_<image-name>.csv`: 10-bin count and percentage distribution.
- `hist_<image-name>.png`: size-distribution plot.
- `stats_<image-name>.png`: summary-statistics table.
- `analysis_log_<image-name>.txt`: calibration, detector settings, and processing log.
- `filter_log_<image-name>.txt`: excluded-particle record.

## Model Integrity

Bundled file: `models/yolov8n-DotMetrics.pt`

SHA-256:

```text
DB994F722D05FBA38498894F30F3103F5E15A99684EA1549EF699D1DC23CE9C1
```

Verify it in PowerShell with:

```powershell
Get-FileHash .\models\yolov8n-DotMetrics.pt -Algorithm SHA256
```

An alternative compatible weight file can be selected by setting `DOTMETRICS_MODEL_PATH` to its absolute path before starting the application.

## Tests

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
```

## Windows Build

Install the development dependencies and run the build script:

```powershell
python -m pip install -e ".[dev]"
.\scripts\build_windows.ps1
```

The packaged application is written to `dist\DotMetrics`.

## Reproducible Environment

`requirements.txt` contains supported lower bounds. `requirements-lock.txt` records the versions used for the release verification environment.

## License

DotMetrics source code and the bundled DotMetrics model weights are distributed under `AGPL-3.0-only`. This strong copyleft license requires distributors of modified versions, including versions offered over a network, to provide the corresponding source under the same license. It does not prohibit commercial use. The software also uses third-party components with their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes and [SECURITY.md](SECURITY.md) for responsible vulnerability reporting.
