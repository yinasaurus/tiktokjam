"""Fail if tracked files include forbidden data artifacts or likely secrets."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_PATHS = (
    "data/catalog.jsonl",
    "data/public_set.jsonl",
    "cache/",
    "runs/",
    "eval_output/",
    "dist/",
    "results.json",
    "catalog.jsonl.gz",
    "techjam-participant-kit.zip",
    ".env",
    "credentials.json",
)

SECRET_PATTERNS = (
    re.compile(r"\b(?:sk|xoxb|ghp|github_pat)_[A-Za-z0-9_=-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]{8,}['\"]"),
)

ALLOW_SECRET_WORD_FILES = {
    ".gitignore",
    "docs/submission_rules.md",
    "docs/submission_checklist.md",
    "docs/devpost_draft.md",
    "docs/final_submission_handoff.md",
    "README.md",
    "DISCLOSURE.md",
    "DATA_ATTRIBUTION.md",
    "PRD-v2.0-conversational-shopping-agent.md",
    "TDD-v2.0-conversational-shopping-agent.md",
    "plan.html",
    "scripts/check_repo_hygiene.py",
}


def tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]


def has_forbidden_path(path: str) -> bool:
    return any(path == forbidden or path.startswith(forbidden) for forbidden in FORBIDDEN_PATHS)


def scan_file(path: str) -> list[str]:
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        return [f"{path}: cannot read tracked file: {exc}"]
    if b"\0" in raw:
        return []
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return []
    findings = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"{path}: possible secret pattern {pattern.pattern}")
    if path not in ALLOW_SECRET_WORD_FILES:
        if re.search(r"(?i)\b(api[_-]?key|secret|password)\b", text):
            findings.append(f"{path}: contains secret-like keyword")
    return findings


def main() -> None:
    files = tracked_files()
    findings = [f"{path}: forbidden tracked artifact" for path in files if has_forbidden_path(path)]
    for path in files:
        findings.extend(scan_file(path))
    if findings:
        print("Repository hygiene check failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Repository hygiene check passed for {len(files)} tracked files.")


if __name__ == "__main__":
    main()
