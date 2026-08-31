param(
    [string]$OutDir = "dist"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git is required to build the submission package."
}

$dirty = git status --short
if ($dirty) {
    throw "Working tree is not clean. Commit or stash changes before packaging."
}

$sha = (git rev-parse --short HEAD).Trim()
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$zip = Join-Path $OutDir "techjam-track4-submission-$sha.zip"

if (Test-Path $zip) {
    Remove-Item -LiteralPath $zip
}

git archive --format=zip --output=$zip HEAD
$hash = Get-FileHash -Algorithm SHA256 -LiteralPath $zip
$checksum = "$zip.sha256"
"{0}  {1}" -f $hash.Hash.ToLowerInvariant(), (Split-Path -Leaf $zip) |
    Set-Content -Path $checksum -Encoding ascii

Write-Host "Wrote $zip"
Write-Host "Wrote $checksum"
Write-Host "SHA256 $($hash.Hash.ToLowerInvariant())"
Write-Host "Built from commit $sha"
Write-Host "Archive is generated from tracked files only; ignored catalog/data/cache/results are excluded."
