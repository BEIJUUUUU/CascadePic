# Build a distributable Waterfall Media Viewer folder with PyInstaller.
#
# Usage:
#   .\build.ps1
#   .\build.ps1 -VlcDir "C:\Program Files\VideoLAN\VLC" -Ffmpeg "E:\tools\ffmpeg.exe" -Ffprobe "E:\tools\ffprobe.exe"
#
# The output lands in dist\WaterfallMediaViewer\ and contains the viewer
# executable, libVLC runtime (when available) and ffmpeg/ffprobe (when found).

param(
    [string]$VlcDir = "",
    [string]$Ffmpeg = "",
    [string]$Ffprobe = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "Virtual environment not found at $py. Run: py -3.12 -m venv .venv"
    exit 1
}

Write-Host "== Installing build tooling =="
& $py -m pip install --quiet pyinstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Running PyInstaller =="
& $py -m PyInstaller --noconfirm --clean packaging\waterfall_viewer.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$dist = Join-Path $root "dist\WaterfallMediaViewer"
if (-not (Test-Path $dist)) {
    Write-Error "Expected output directory $dist was not created."
    exit 1
}

# --- libVLC runtime -----------------------------------------------------
if (-not $VlcDir) {
    $candidates = @(
        "$env:ProgramFiles\VideoLAN\VLC",
        "${env:ProgramFiles(x86)}\VideoLAN\VLC",
        "$env:LOCALAPPDATA\Programs\VideoLAN\VLC"
    )
    $VlcDir = $candidates | Where-Object { Test-Path (Join-Path $_ "libvlc.dll") } | Select-Object -First 1
}
if ($VlcDir -and (Test-Path (Join-Path $VlcDir "libvlc.dll"))) {
    Write-Host "== Bundling libVLC from $VlcDir =="
    Copy-Item (Join-Path $VlcDir "libvlc.dll") $dist -Force
    Copy-Item (Join-Path $VlcDir "libvlccore.dll") $dist -Force
    if (Test-Path (Join-Path $VlcDir "plugins")) {
        Copy-Item (Join-Path $VlcDir "plugins") $dist -Recurse -Force
    }
} else {
    Write-Warning "VLC was not found. Video playback will be disabled in this build."
}

# --- ffmpeg / ffprobe ---------------------------------------------------
if (-not $Ffmpeg) { $Ffmpeg = (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue).Source }
if (-not $Ffprobe) { $Ffprobe = (Get-Command ffprobe.exe -ErrorAction SilentlyContinue).Source }
if (-not $Ffmpeg -and (Test-Path "E:\各种录播\ffmpeg.exe")) { $Ffmpeg = "E:\各种录播\ffmpeg.exe" }
if (-not $Ffprobe -and (Test-Path "E:\各种录播\ffprobe.exe")) { $Ffprobe = "E:\各种录播\ffprobe.exe" }

if ($Ffmpeg -and (Test-Path $Ffmpeg)) {
    Write-Host "== Bundling ffmpeg =="
    Copy-Item $Ffmpeg (Join-Path $dist "ffmpeg.exe") -Force
} else {
    Write-Warning "ffmpeg was not found. Video thumbnails will be disabled in this build."
}
if ($Ffprobe -and (Test-Path $Ffprobe)) {
    Write-Host "== Bundling ffprobe =="
    Copy-Item $Ffprobe (Join-Path $dist "ffprobe.exe") -Force
} else {
    Write-Warning "ffprobe was not found. Video metadata will be disabled in this build."
}

$size = (Get-ChildItem $dist -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host ""
Write-Host "Build complete: $dist" -ForegroundColor Green
Write-Host ("Total size: {0:N0} MB" -f $size)
