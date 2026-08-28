# DotMetrics

DotMetrics is a desktop application for calibrated particle-size analysis of transmission electron microscopy (TEM) images. It combines YOLO-based particle localization with local image processing, interactive review, manual diameter measurements, and reproducible result export.

The software is designed for a transparent operator-in-the-loop workflow. The detector proposes particle locations, local image processing produces the measurement contours, and the operator verifies the calibration and result before export. DotMetrics does not infer material composition from image appearance.

## Release Status

- Current version: `1.0.0`
- Primary platform: Windows 10/11 x64
- Supported Python: 3.11 or later
- Bundled detector: DotMetrics YOLOv8n weights
- License: `AGPL-3.0-only`

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

The release is not presented as a reliable method for separating heavily overlapping or visually unresolvable aggregates. Performance on substantially different materials, microscopes, contrast conditions, or acquisition protocols must be validated independently.

## How Measurements Are Produced

1. The operator calibrates the image from its visible scale bar.
2. YOLOv8n localizes candidate particle regions.
3. Each candidate region is converted to grayscale and processed with median filtering, Gaussian blur, and Otsu thresholding.
4. A valid local contour is selected and its equivalent circular diameter is calculated from contour area.
5. Pixel measurements are converted to nanometres with the image-specific calibration.
6. The operator reviews contours, excludes inappropriate detections, and may add clearly identified manual diameter lines.
7. DotMetrics exports measurements, figures, settings, and audit information together.

## Quick Start

DotMetrics requires Git and Python 3.11 or later. The release has been verified on Windows. In PowerShell:

```powershell
git clone https://github.com/Tinker-Zhang404/dotmetrics.git
cd dotmetrics
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
dotmetrics
```

The first launch initializes the local runtime directory and preloads the detector. Wait until the status reads `Detector: ready` before analysis.

### Reproducible Installation

For the exact dependency versions used in release verification, use:

```powershell
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
python scripts/verify_checkout.py
dotmetrics
```

The verification script checks required imports, the application entry point, runtime model resolution, and the bundled model SHA-256 digest.

`Run Analysis` becomes available when an image is loaded, scale calibration is complete, and the detector is ready.

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

Manual lines and automated contour measurements remain distinguishable in the exported report. Excluding a detection does not alter the original TEM image.

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

Only load model files from trusted sources. PyTorch model files can contain serialized Python objects. See [SECURITY.md](SECURITY.md).

## Repository Layout

```text
dotmetrics.py                 Source-checkout launcher
models/                       Bundled detector weights
scripts/                      Verification and Windows build scripts
src/dotmetrics/core/          Detection, segmentation, export, and paths
src/dotmetrics/domain/        Measurement data models
src/dotmetrics/ui/            PySide6 desktop interface
tests/                        Unit and offscreen UI tests
```

## Tests

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
python scripts/verify_checkout.py
```

The GitHub Actions workflow performs installation and the same checks on Windows with Python 3.11.

## Windows Build

Install the development dependencies and run the build script:

```powershell
python -m pip install -e ".[dev]"
.\scripts\build_windows.ps1
```

The packaged application is written to `dist\DotMetrics`.

The Windows build is a one-folder package. `DotMetrics.exe` depends on the adjacent `_internal` directory and must not be distributed by itself.

## Reproducible Environment

`requirements.txt` contains supported lower bounds. `requirements-lock.txt` records the versions used for the release verification environment.

Analysis exports record calibration, detector settings, processing information, and excluded particles so the operator can retain an audit trail. Source TEM images are read but are not modified by DotMetrics.

## Privacy and Network Use

Image analysis is performed locally. DotMetrics does not implement image upload, user accounts, cloud processing, or application telemetry. Dependency installation and retrieval of alternative model files may require network access, but routine analysis uses the local image and local model.

## Getting Help

For reproducible problems, open a GitHub issue and include the DotMetrics version, operating system, Python version, steps to reproduce, and the relevant application log. Do not attach confidential TEM images or unpublished research data to a public issue.

## License

DotMetrics source code and the bundled DotMetrics model weights are distributed under `AGPL-3.0-only`. This strong copyleft license requires distributors of modified versions, including versions offered over a network, to provide the corresponding source under the same license. It does not prohibit commercial use. The software also uses third-party components with their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes and [SECURITY.md](SECURITY.md) for responsible vulnerability reporting.
