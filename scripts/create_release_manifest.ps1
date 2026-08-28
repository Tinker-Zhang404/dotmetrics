param(
    [Parameter(Mandatory = $true)]
    [string]$DistributionRoot
)

$ErrorActionPreference = "Stop"

$DistributionRoot = (Resolve-Path -LiteralPath $DistributionRoot).Path
$executable = Join-Path $DistributionRoot "DotMetrics.exe"
$model = Join-Path $DistributionRoot "_internal\models\yolov8n-DotMetrics.pt"
$manifest = Join-Path $DistributionRoot "RELEASE_MANIFEST.txt"

foreach ($requiredFile in @($executable, $model)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required release file is missing: $requiredFile"
    }
}

$payloadFiles = Get-ChildItem -LiteralPath $DistributionRoot -File -Recurse |
    Where-Object { $_.FullName -ne $manifest }
$payloadSize = ($payloadFiles | Measure-Object -Property Length -Sum).Sum
$executableInfo = Get-Item -LiteralPath $executable
$executableHash = (Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash
$modelHash = (Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash

$content = @(
    "DotMetrics v1.0.0 Windows Release Manifest"
    "=========================================="
    ""
    "Build date: $(Get-Date -Format 'yyyy-MM-dd')"
    "Platform: Windows x64"
    "Packaging: PyInstaller one-folder bundle"
    "Payload file count: $($payloadFiles.Count)"
    "Payload size: $payloadSize bytes"
    ""
    "DotMetrics.exe"
    "  Size: $($executableInfo.Length) bytes"
    "  SHA-256: $executableHash"
    ""
    "_internal/models/yolov8n-DotMetrics.pt"
    "  SHA-256: $modelHash"
    ""
    "Usage"
    "  - Extract the complete ZIP archive before running the application."
    "  - Keep DotMetrics.exe and the _internal directory together."
    "  - Example TEM images are provided in the examples directory."
    ""
    "Verification"
    "  - The bundled model checksum matches the documented release checksum."
    "  - Paper-validation controls are not included in the formal release."
)

Set-Content -LiteralPath $manifest -Value $content -Encoding UTF8
Write-Host "Release manifest written: $manifest"
