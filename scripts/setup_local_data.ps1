param(
    [string]$CatalogArchive = "",
    [string]$ParticipantKit = "techjam-participant-kit.zip",
    [switch]$DownloadOfficial
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DataDir = Join-Path $Root "data"
$CatalogPath = Join-Path $DataDir "catalog.jsonl"
$PublicSetPath = Join-Path $DataDir "public_set.jsonl"
$ReleaseBase = "https://github.com/TechJam2026/techjam-conversational-search/releases/download/participant-kit"

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

function Download-IfMissing {
    param(
        [string]$Name,
        [string]$Destination
    )
    if (Test-Path -LiteralPath $Destination) {
        Write-Host "$Name already present: $Destination"
        return
    }
    $Uri = "$ReleaseBase/$Name"
    Write-Host "Downloading $Uri"
    Invoke-WebRequest -Uri $Uri -OutFile $Destination
}

function Confirm-Sha256 {
    param([string]$ChecksumFile)
    if (-not (Test-Path -LiteralPath $ChecksumFile)) {
        Write-Warning "No SHA256SUMS file found; skipping checksum verification."
        return
    }
    $Expected = @{}
    foreach ($Line in Get-Content -LiteralPath $ChecksumFile) {
        if ($Line -match "^\s*([a-fA-F0-9]{64})\s+\*?(.+?)\s*$") {
            $Expected[$Matches[2]] = $Matches[1].ToLowerInvariant()
        }
    }
    foreach ($Name in @("catalog.jsonl.gz", "techjam-participant-kit.zip")) {
        $Path = Join-Path $Root $Name
        if ((Test-Path -LiteralPath $Path) -and $Expected.ContainsKey($Name)) {
            $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
            if ($Actual -ne $Expected[$Name]) {
                throw "SHA256 mismatch for $Name. Expected $($Expected[$Name]), got $Actual."
            }
            Write-Host "SHA256 ok: $Name"
        }
    }
}

if ($DownloadOfficial) {
    Download-IfMissing "catalog.jsonl.gz" (Join-Path $Root "catalog.jsonl.gz")
    Download-IfMissing "techjam-participant-kit.zip" (Join-Path $Root "techjam-participant-kit.zip")
    Download-IfMissing "SHA256SUMS" (Join-Path $Root "SHA256SUMS")
    Confirm-Sha256 (Join-Path $Root "SHA256SUMS")
}

function Resolve-FirstExisting {
    param([string[]]$Candidates)
    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path -LiteralPath $Candidate)) {
            return (Resolve-Path -LiteralPath $Candidate).Path
        }
    }
    return $null
}

if (-not (Test-Path -LiteralPath $CatalogPath)) {
    $Archive = Resolve-FirstExisting @(
        $CatalogArchive,
        (Join-Path $Root "catalog.jsonl.gz"),
        (Join-Path $DataDir "catalog.jsonl.gz")
    )
    if (-not $Archive) {
        throw "Missing catalog. Put catalog.jsonl.gz at repo root or data/, or pass -CatalogArchive <path>."
    }
    Write-Host "Decompressing catalog from $Archive"
    $In = [System.IO.Compression.GzipStream]::new(
        [System.IO.File]::OpenRead($Archive),
        [System.IO.Compression.CompressionMode]::Decompress
    )
    try {
        $Out = [System.IO.File]::Create($CatalogPath)
        try {
            $In.CopyTo($Out)
        } finally {
            $Out.Dispose()
        }
    } finally {
        $In.Dispose()
    }
} else {
    Write-Host "Catalog already present: $CatalogPath"
}

if (-not (Test-Path -LiteralPath $PublicSetPath)) {
    $Kit = Resolve-FirstExisting @(
        $ParticipantKit,
        (Join-Path $Root "techjam-participant-kit.zip")
    )
    if (-not $Kit) {
        Write-Warning "Missing public_set.jsonl and participant kit. Copy public_set.jsonl into data/ when available."
    } else {
        $TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("techjam-kit-" + [guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
        try {
            Expand-Archive -LiteralPath $Kit -DestinationPath $TempDir -Force
            $PublicSet = Get-ChildItem -LiteralPath $TempDir -Recurse -Filter "public_set.jsonl" | Select-Object -First 1
            if (-not $PublicSet) {
                throw "participant kit did not contain public_set.jsonl"
            }
            Copy-Item -LiteralPath $PublicSet.FullName -Destination $PublicSetPath
            Write-Host "Copied public set to $PublicSetPath"
        } finally {
            Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "Public set already present: $PublicSetPath"
}

if (Test-Path -LiteralPath $CatalogPath) {
    $Rows = (Get-Content -LiteralPath $CatalogPath -ReadCount 1000 | ForEach-Object { $_.Count } | Measure-Object -Sum).Sum
    Write-Host "catalog rows: $Rows"
}
if (Test-Path -LiteralPath $PublicSetPath) {
    $Rows = (Get-Content -LiteralPath $PublicSetPath -ReadCount 1000 | ForEach-Object { $_.Count } | Measure-Object -Sum).Sum
    Write-Host "public-set rows: $Rows"
}

Write-Host ""
Write-Host "Local data files are gitignored. Confirm before committing:"
git -C $Root status --short -- data
