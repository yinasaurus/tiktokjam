param(
    [string]$Catalog = "data\catalog.jsonl",
    [string]$Dataset = "data\public_set.jsonl",
    [string]$Output = "results.json"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path -LiteralPath $Catalog)) {
    throw "Missing catalog at $Catalog. Run scripts\setup_local_data.ps1 first."
}
if (-not (Test-Path -LiteralPath $Dataset)) {
    throw "Missing public set at $Dataset. Run scripts\setup_local_data.ps1 first."
}

$Python = if (Test-Path ".venv\Scripts\python.exe") {
    Join-Path $Root ".venv\Scripts\python.exe"
} else {
    "python"
}

& $Python -m evaluator.local_evaluator --catalog $Catalog --dataset $Dataset --output $Output
Write-Host "Wrote $Output (gitignored)"
