#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DATA_DIR="$ROOT/data"
RELEASE_BASE="https://github.com/TechJam2026/techjam-conversational-search/releases/download/participant-kit"
DOWNLOAD_OFFICIAL=0

for arg in "$@"; do
  case "$arg" in
    --download-official|-DownloadOfficial) DOWNLOAD_OFFICIAL=1 ;;
  esac
done

mkdir -p "$DATA_DIR"

download_if_missing() {
  name="$1"
  dest="$ROOT/$name"
  if [ -f "$dest" ]; then
    echo "$name already present: $dest"
    return
  fi
  echo "Downloading $RELEASE_BASE/$name"
  if command -v curl >/dev/null 2>&1; then
    curl -L -o "$dest" "$RELEASE_BASE/$name"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$dest" "$RELEASE_BASE/$name"
  else
    echo "Need curl or wget to download official assets." >&2
    exit 1
  fi
}

if [ "$DOWNLOAD_OFFICIAL" -eq 1 ]; then
  download_if_missing catalog.jsonl.gz
  download_if_missing techjam-participant-kit.zip
  download_if_missing SHA256SUMS
  if command -v sha256sum >/dev/null 2>&1; then
    (cd "$ROOT" && sha256sum -c SHA256SUMS --ignore-missing)
  else
    echo "sha256sum unavailable; skipping checksum verification"
  fi
fi

if [ ! -f "$DATA_DIR/catalog.jsonl" ]; then
  archive="$ROOT/catalog.jsonl.gz"
  [ -f "$archive" ] || archive="$DATA_DIR/catalog.jsonl.gz"
  if [ ! -f "$archive" ]; then
    echo "Missing catalog.jsonl.gz. Use --download-official or place it at repo root/data." >&2
    exit 1
  fi
  echo "Decompressing $archive"
  gzip -dc "$archive" > "$DATA_DIR/catalog.jsonl"
else
  echo "Catalog already present: $DATA_DIR/catalog.jsonl"
fi

if [ ! -f "$DATA_DIR/public_set.jsonl" ]; then
  kit="$ROOT/techjam-participant-kit.zip"
  if [ ! -f "$kit" ]; then
    echo "Missing public_set.jsonl and participant kit; copy public_set.jsonl into data/." >&2
  elif command -v unzip >/dev/null 2>&1; then
    tmp="${TMPDIR:-/tmp}/techjam-kit-$$"
    mkdir -p "$tmp"
    unzip -q "$kit" -d "$tmp"
    found="$(find "$tmp" -name public_set.jsonl -print -quit)"
    if [ -n "$found" ]; then
      cp "$found" "$DATA_DIR/public_set.jsonl"
      echo "Copied public set to $DATA_DIR/public_set.jsonl"
    else
      echo "participant kit did not contain public_set.jsonl" >&2
      rm -rf "$tmp"
      exit 1
    fi
    rm -rf "$tmp"
  else
    echo "Need unzip to extract public_set.jsonl." >&2
    exit 1
  fi
else
  echo "Public set already present: $DATA_DIR/public_set.jsonl"
fi

[ -f "$DATA_DIR/catalog.jsonl" ] && wc -l "$DATA_DIR/catalog.jsonl"
[ -f "$DATA_DIR/public_set.jsonl" ] && wc -l "$DATA_DIR/public_set.jsonl"
git -C "$ROOT" status --short -- data
