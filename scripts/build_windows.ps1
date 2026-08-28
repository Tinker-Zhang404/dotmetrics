$ErrorActionPreference = "Stop"

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repositoryRoot
$pythonExecutable = (Get-Command python).Source
$basePrefix = (& $pythonExecutable -c "import sys; print(sys.base_prefix)").Trim()
$configRoot = Join-Path $repositoryRoot ".ultralytics"
New-Item -ItemType Directory -Force -Path (Join-Path $configRoot "Ultralytics") | Out-Null
$env:YOLO_CONFIG_DIR = $configRoot

# Keep unrelated desktop-tool DLLs out of PyInstaller's dependency search.
$env:Path = @(
    (Split-Path -Parent $pythonExecutable),
    $basePrefix,
    (Join-Path $basePrefix "Library\bin"),
    (Join-Path $basePrefix "Scripts"),
    (Join-Path $env:SystemRoot "System32"),
    $env:SystemRoot,
    (Join-Path $env:SystemRoot "System32\Wbem")
) -join ";"

& $pythonExecutable -m PyInstaller --noconfirm --clean dotmetrics.spec

$distributionRoot = Join-Path $repositoryRoot "dist\DotMetrics"
foreach ($document in @(
    "WINDOWS_README.txt",
    "README.md",
    "USER_GUIDE.md",
    "MODEL_CARD.md",
    "LICENSE",
    "THIRD_PARTY_NOTICES.md"
)) {
    Copy-Item -LiteralPath (Join-Path $repositoryRoot $document) -Destination $distributionRoot -Force
}

Write-Host "DotMetrics build completed: $repositoryRoot\dist\DotMetrics"
