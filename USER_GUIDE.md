# DotMetrics User Guide

## 1. Open an Image

Select `Open TEM Image` and choose a PNG, JPEG, TIFF, or BMP file. The source image appears in the `Original Image` tab. Use the mouse wheel or the view buttons to inspect it.

## 2. Calibrate the Scale

Select `Calibrate Scale`. In the calibration window:

1. Click one endpoint of the visible scale bar.
2. Click the other endpoint.
3. Enter the printed scale-bar length in nanometres.
4. Confirm the calibration.

The main window reports the resulting `nm/px` factor. Recalibrate whenever a different image or magnification is loaded.

## 3. Run Automated Analysis

Wait until the detector status reads `Detector: ready`. The default settings are:

- Confidence: `0.10`
- IoU: `0.30`

Select `Run Analysis`. DotMetrics localizes candidate particles, segments each region, and calculates equivalent circular diameter from the segmented area. Results appear in the `Analysis Results`, `Size Distribution`, and `Summary Statistics` tabs.

## 4. Review the Result

Inspect every image before export.

- Click a particle overlay to select it.
- Use `Select All` or `Clear Selection` for bulk selection.
- Use `Exclude Selected` to remove false detections from the reported distribution.
- Use `Restore Excluded` to undo exclusions.

Excluded objects remain visible for traceability but are omitted from the combined measurement distribution.

## 5. Add Manual Measurements

After automated analysis, enable `Draw Manual Diameter Lines`. Drag across the intended particle diameter in the `Analysis Results` view. The line length is converted to nanometres with the active calibration factor and included in the exported measurement table and distribution.

Use manual lines only when the particle boundary and measurement direction can be judged reliably. `Clear Manual Lines` removes all manual measurements from the current image.

## 6. Export Results

Select `Export Results` and choose a parent folder. DotMetrics creates a new image-specific result directory without modifying the source image.

The analysis log records the scale factor, calibration state, detector settings, model path, count summary, and visible application log. Keep this folder together with the original image for reproducibility.

## Quality-Control Checklist

- Confirm that the scale bar belongs to the image and that its unit was entered correctly.
- Confirm the detector status is ready and the analysis log reports `YOLO used: True` when YOLO output is expected.
- Inspect boundaries near image edges, low-contrast objects, touching particles, and non-particle structures.
- Exclude false detections consistently.
- Do not interpret a segmented aggregate as multiple particles unless the boundaries are visually resolvable.
- Preserve the original image and exported log with the numerical results.

## Troubleshooting

### Run Analysis is disabled

Load an image, complete scale calibration, and wait for `Detector: ready`.

### Detector is unavailable

Confirm that `models/yolov8n-DotMetrics.pt` exists and matches the checksum in `README.md`. Review the application log for the loading error.

### The result contains false detections

Review the confidence setting, exclude inappropriate objects, and document the review in the exported files. Parameter changes should be applied consistently within a comparison set.

### A scale bar cannot be calibrated reliably

Do not report measurements from that image until a trustworthy pixel-to-nanometre scale is available.
