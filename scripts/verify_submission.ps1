param(
    [switch]$WithData,
    [switch]$WithLtr,
    [switch]$WithResearch
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = if (Test-Path ".venv\Scripts\python.exe") {
    Join-Path $Root ".venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host "Running unit tests"
& $Python -m pytest tests -q

Write-Host "Compiling Python modules"
& $Python -m compileall agent scripts tools starter tests evaluator ui -q

Write-Host "Checking repository hygiene"
& $Python scripts/check_repo_hygiene.py

Write-Host "Running fixture smoke session"
& $Python scripts/smoke_session.py

Write-Host "Running synthetic fixture customer gate"
& $Python scripts/synthetic_customer_gate.py --threshold 0.80 --trials 100

if ($WithData) {
    if (-not (Test-Path "data\catalog.jsonl") -or -not (Test-Path "data\public_set.jsonl")) {
        throw "WithData requested but data\catalog.jsonl or data\public_set.jsonl is missing."
    }
    Write-Host "Running official-data acceptance gate"
    & $Python scripts/check_acceptance.py --threshold 0.80

    if ($WithResearch) {
        Write-Host "Running optional ablations"
        & $Python scripts/run_ablations.py
        Write-Host "Benchmarking heuristic reranker"
        & $Python scripts/bench_reranker.py --mode heuristic
    }

    if ($WithLtr) {
        if (-not (Test-Path "models\ltr.txt")) {
            throw "WithLtr requested but models\ltr.txt is missing."
        }
        Write-Host "Benchmarking LTR reranker"
        & $Python scripts/bench_reranker.py --mode ltr
    }
}

Write-Host ""
Write-Host "Git status:"
git status --short
