"""Print current submission readiness from live repo state."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SCORE = "0.852704"


def run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc.returncode, proc.stdout.strip()


def latest_package() -> str:
    packages = sorted(
        (ROOT / "dist").glob("techjam-track4-submission-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return str(packages[0].relative_to(ROOT)) if packages else "missing; run scripts/package_submission.ps1"


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
        ]
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


def yesno(value: bool) -> str:
    return "yes" if value else "no"


def main() -> None:
    _, head = run(["git", "log", "-1", "--oneline"])
    _, status = run(["git", "status", "--short"])
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
    print()
    print("## Final Commands")
    print()
    print("```powershell")
    print("git pull origin main")
    print(".\\scripts\\verify_submission.ps1 -WithData")
    print(".\\scripts\\package_submission.ps1")
    print("```")
    print()
    print("## External Items")
    print()
    print("- Team name is `kpopy demon hunter`; fill individual names and contribution split in Devpost.")
    print("- Record/upload the public YouTube demo.")
    print("- Paste `docs/devpost_draft.md` into Devpost and submit before 2026-09-01 12:00 Singapore time.")


if __name__ == "__main__":
    main()
