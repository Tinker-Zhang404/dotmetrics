# Contributing to DotMetrics

Thank you for considering a contribution. DotMetrics is intended for reproducible TEM particle-size analysis, so changes must preserve traceability and operator review.

## Development Setup

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
python scripts/verify_checkout.py
```

## Pull Requests

- Keep changes focused and describe their effect on measurements or exports.
- Add tests for behavior changes and run the complete test suite.
- Do not commit TEM images, patient or participant data, unpublished manuscripts, reviewer material, credentials, build output, or local runtime files.
- Do not replace the bundled model without documenting its provenance, intended scope, evaluation, license, and SHA-256 digest.
- Preserve the distinction between automated measurements and operator-added manual measurements.

By submitting a contribution, you agree that it may be distributed under `AGPL-3.0-only`.
