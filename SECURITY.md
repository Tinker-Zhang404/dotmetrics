# Security Policy

## Supported Version

Security fixes are applied to the latest release of DotMetrics.

## Reporting a Vulnerability

Please do not disclose an unpatched vulnerability in a public issue. Use GitHub's private vulnerability reporting feature for this repository. Include the affected version, operating system, reproduction steps, and expected impact.

DotMetrics processes local image files and model weights. Only open files and weights from trusted sources. Model files loaded by PyTorch may execute serialized Python content and must not be treated as untrusted data.
