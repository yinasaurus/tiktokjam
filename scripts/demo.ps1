param(
    [switch]$Install,
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment"
    python -m venv .venv
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if ($Install) {
    & $Python -m pip install -r requirements.txt
}

if (Test-Path "data\catalog.jsonl") {
    Write-Host "Using official catalog at data\catalog.jsonl"
} else {
    Write-Warning "data\catalog.jsonl is missing; UI will fall back only if the app code can discover fixture data."
    Write-Host "Run scripts\setup_local_data.ps1 after downloading the participant data."
}

Write-Host "Running unit tests"
& $Python -m pytest tests -q

Write-Host "Starting demo UI at http://127.0.0.1:$Port/"
& $Python -m ui --port $Port
