# Bootstrap a scribe development environment on Windows.
# Creates .venv with Python 3.12 via uv and installs CUDA PyTorch plus all deps.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:UV_CACHE_DIR = Join-Path $root ".uv-cache"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "installing uv via winget ..."
    winget install --id astral-sh.uv --accept-source-agreements --accept-package-agreements
}

if (-not (Test-Path ".venv")) {
    uv venv --python 3.12 .venv
}

$py = ".venv\Scripts\python.exe"

Write-Host "installing PyTorch (CUDA 12.8 wheels) ..."
uv pip install --python $py torch torchaudio --index-url https://download.pytorch.org/whl/cu128

Write-Host "installing scribe ..."
uv pip install --python $py -e ".[dev]"

Write-Host ""
Write-Host "done. Start the server with:"
Write-Host "  .venv\Scripts\python.exe -m scribe.server"
