# DotMetrics Example Images

These images are provided as inputs for learning the DotMetrics calibration, analysis, review, and export workflow.

| File | Scale-bar value |
| --- | ---: |
| `TEM_Example_01.jpg` | 5 nm |
| `TEM_Example_02.tif` | 20 nm |
| `TEM_Example_03.tif` | 20 nm |

## Suggested Workflow

1. Open an example image in DotMetrics.
2. Select `Calibrate Scale`.
3. Mark the two endpoints of the horizontal scale-bar line.
4. Enter the corresponding value from the table above.
5. Wait for `Detector: ready`, then select `Run Analysis`.
6. Review the contours and exclude any object that does not meet the study-specific inclusion criteria.
7. Export the result to a new directory.

Automated results can depend on detector settings, image quality, and operator inclusion criteria. No fixed particle count or expected diameter distribution is asserted for these demonstration files.

## Demonstration Outputs

The Windows release archive includes `examples/reference_outputs`. These outputs were generated with DotMetrics v1.0.0 using confidence `0.10`, IoU `0.30`, image-specific scale calibration, and operator review.

| Example | Automated candidates | Excluded | Manual lines | Final measurements | Mean diameter |
| --- | ---: | ---: | ---: | ---: | ---: |
| `TEM_Example_01` | 11 | 3 | 2 | 10 | 2.47 nm |
| `TEM_Example_02` | 69 | 10 | 0 | 59 | 6.14 nm |
| `TEM_Example_03` | 83 | 0 | 0 | 83 | 2.96 nm |

These values demonstrate the software workflow and export structure. They are operator-reviewed software outputs, not independent manual ground truth, benchmark targets, or claims of universal performance. Raw analysis logs are intentionally excluded because they contain local filesystem paths and cumulative session history.

The example images are distributed with this repository under `AGPL-3.0-only` unless otherwise indicated. Do not use them as a substitute for independent method validation.
