#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"
OUT_DIR="${OUT_DIR:-dist}"

command -v git >/dev/null 2>&1 || {
  echo "git is required to build the submission package." >&2
  exit 1
}

if [ -n "$(git status --short)" ]; then
  echo "Working tree is not clean. Commit or stash changes before packaging." >&2
  exit 1
fi

SHA="$(git rev-parse --short HEAD)"
mkdir -p "$OUT_DIR"
ZIP="$OUT_DIR/techjam-track4-submission-$SHA.zip"
rm -f "$ZIP"
git archive --format=zip --output="$ZIP" HEAD
if command -v sha256sum >/dev/null 2>&1; then
  HASH="$(sha256sum "$ZIP" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  HASH="$(shasum -a 256 "$ZIP" | awk '{print $1}')"
else
  HASH=""
fi
if [ -n "$HASH" ]; then
  CHECKSUM="$ZIP.sha256"
  printf '%s  %s\n' "$HASH" "$(basename "$ZIP")" > "$CHECKSUM"
  echo "Wrote $CHECKSUM"
  echo "SHA256 $HASH"
else
  echo "Warning: sha256sum/shasum unavailable; checksum file not written." >&2
fi

echo "Wrote $ZIP"
echo "Built from commit $SHA"
echo "Archive is generated from tracked files only; ignored catalog/data/cache/results are excluded."
