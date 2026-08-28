# DotMetrics Model Card

## Model Details

- Model file: `yolov8n-DotMetrics.pt`
- Architecture family: YOLOv8n object detector
- Task in DotMetrics: candidate nanoparticle localization in TEM images
- Output use: bounding boxes define regions for subsequent local segmentation and equivalent-diameter calculation
- License: `AGPL-3.0-only`
- SHA-256: `DB994F722D05FBA38498894F30F3103F5E15A99684EA1549EF699D1DC23CE9C1`

## Intended Use

The model is intended to assist analysis of carbon-dot-like nanoparticles that are visually separable in TEM images. It is designed for use inside DotMetrics with image-specific scale calibration, local segmentation, and operator review.

## Out-of-Scope Use

- Autonomous measurement without checking scale calibration and contours.
- Reliable separation of heavily overlapping or unresolvable aggregates.
- Images whose contrast, particle morphology, specimen type, or acquisition conditions differ substantially from the development data without additional validation.
- Clinical, safety-critical, regulatory, or production quality-control decisions without independent method validation.
- Inferring chemical identity or material composition from image appearance.

## Processing Pipeline

1. YOLOv8n localizes candidate regions.
2. Each region is converted to grayscale and filtered.
3. Otsu thresholding produces a binary particle mask.
4. The largest valid contour in the region is retained.
5. Equivalent circular diameter is calculated from contour area and converted with the calibrated `nm/px` factor.

The default interface settings are confidence `0.10`, IoU `0.30`, and a maximum of 2,000 detections. Operators should document any parameter changes.

## Limitations and Risks

Performance can degrade for low contrast, blur, edge-truncated particles, strong background texture, touching particles, and dense aggregation. Bounding-box localization does not itself provide a pixel-accurate diameter; the downstream contour step supplies the segmentation used for measurement. The software can also fall back to image-wide Otsu segmentation if detector inference fails, so the exported analysis log must be checked.

False positives and false negatives are possible. Human review, consistent inclusion criteria, and retention of exported audit information are required.

## Integrity Verification

```powershell
Get-FileHash .\models\yolov8n-DotMetrics.pt -Algorithm SHA256
```

The result must match the checksum above before the weights are used for reproducibility comparisons.
