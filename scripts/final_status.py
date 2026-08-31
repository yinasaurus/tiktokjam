"""Print current submission readiness from live repo state."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SCORE = "0.955300"
PULLS_URL = "https://github.com/yinasaurus/tiktokjam/pulls"
MAIN_POSTPLAN_URL = "https://mj4gkxs69b24.postplan.dev"
STATUS_POSTPLAN_URL = "https://pbexoc8bktvw.postplan.dev"


def run(args: list[str], timeout: float = 15.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout:g}s: {' '.join(args)}"
    return proc.returncode, proc.stdout.strip()


def latest_package() -> str:
    packages = sorted(
        (ROOT / "dist").glob("techjam-track4-submission-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not packages:
        return "missing; run scripts/package_submission.ps1"
    package = packages[0]
    checksum = package.with_suffix(package.suffix + ".sha256")
    checksum_note = "checksum present" if checksum.exists() else "checksum missing"
    return f"{package.relative_to(ROOT)} ({checksum_note})"


def latest_ci() -> str:
    code, out = run(
        [
            "gh",
            "run",
            "list",
            "--limit",
            "1",
            "--json",
            "status,conclusion,headSha,url,workflowName",
        ],
        timeout=10.0,
    )
    if code != 0:
        return "gh unavailable; check GitHub Actions manually"
    try:
        runs = json.loads(out)
    except json.JSONDecodeError:
        return "gh output unreadable; check GitHub Actions manually"
    if not runs:
        return "no GitHub Actions runs found"
    item = runs[0]
    conclusion = item.get("conclusion") or item.get("status") or "unknown"
    sha = str(item.get("headSha") or "")[:7]
    return f"{conclusion} for {sha}: {item.get('url')}"


def current_branch() -> str:
    code, out = run(["git", "branch", "--show-current"], timeout=5.0)
    return out.strip() if code == 0 else ""


def current_pr() -> str:
    branch = current_branch()
    if not branch:
        return f"check {PULLS_URL}"
    code, out = run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--state",
            "open",
            "--limit",
            "1",
            "--json",
            "number,url,state,isDraft,headRefName",
        ],
        timeout=10.0,
    )
    if code != 0:
        return f"check {PULLS_URL}"
    try:
        items = json.loads(out)
    except json.JSONDecodeError:
        return f"check {PULLS_URL}"
    if not items:
        return f"none for branch `{branch}`; check {PULLS_URL}"
    item = items[0]
    draft = "draft" if item.get("isDraft") else "non-draft"
    return f"#{item.get('number')} {item.get('url')} ({item.get('state')}, {draft})"


def yesno(value: bool) -> str:
    return "yes" if value else "no"


def main() -> None:
    _, head = run(["git", "log", "-1", "--oneline"], timeout=5.0)
    _, status = run(["git", "status", "--short"], timeout=5.0)
    hygiene_code, hygiene = run([sys.executable, "scripts/check_repo_hygiene.py"])
    data_ready = (ROOT / "data" / "catalog.jsonl").exists() and (ROOT / "data" / "public_set.jsonl").exists()

    print("# Final Submission Status")
    print()
    print(f"- HEAD: `{head}`")
    print(f"- Working tree clean: {yesno(not status)}")
    if status:
        print("  Run `git status --short` before packaging.")
    print(f"- Repository hygiene: {'passed' if hygiene_code == 0 else 'failed'}")
    if hygiene_code != 0:
        print(f"  {hygiene}")
    print(f"- Official data present locally: {yesno(data_ready)}")
    print(f"- Latest local package: `{latest_package()}`")
    print(f"- Latest GitHub Actions: {latest_ci()}")
    print(f"- Expected official-data TechnicalScore: `{EXPECTED_SCORE}`")
    print(f"- Current review PR: {current_pr()}")
    print(f"- Main PostPlan: {MAIN_POSTPLAN_URL}")
    print(f"- Status PostPlan: {STATUS_POSTPLAN_URL}")
    print()
    print("## Final Commands")
    print()
    print("```powershell")
    print("git switch main")
    print("git pull --ff-only origin main")
    print(".\\scripts\\verify_submission.ps1 -WithData")
    print(".\\scripts\\package_submission.ps1")
    print("```")
    print()
    print("## External Items")
    print()
    print(f"- Ask the team to review and merge any open final PR before final packaging: {PULLS_URL}")
    print("- Team name is `kpopy demon hunter`; fill individual names and contribution split in Devpost.")
    print("- Record/upload the public YouTube demo.")
    print("- Paste `docs/devpost_draft.md` into Devpost and submit before 2026-09-01 12:00 Singapore time.")


if __name__ == "__main__":
    main()
