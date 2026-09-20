"""Fail closed on likely credentials without printing their values."""

from __future__ import annotations

import re
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path

PATTERNS = (
    re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{20,}"),
    re.compile(
        r"(?i)(consumer_secret|access_token_secret|private_key)\s*[:=]\s*['\"]?[^\s'\"]{24,}"
    ),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[A-Za-z0-9._-]{24,}"),
)
SKIP_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
}
SKIP_NAMES = {".env.example", "uv.lock", "package-lock.json"}


def current_files(root: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return [path for path in root.rglob("*") if path.is_file()]
    names = [name for name in result.stdout.splitlines() if name]
    if not names:
        return [path for path in root.rglob("*") if path.is_file()]
    return [root / name for name in names]


def history_files(root: Path) -> list[tuple[str, Path, str]]:
    commits = subprocess.run(
        ["git", "rev-list", "--all"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    result: list[tuple[str, Path, str]] = []
    for commit in commits:
        names = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", commit],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        for name in names:
            if name in SKIP_NAMES or name == "scripts/secret_scan.py":
                continue
            try:
                content = subprocess.run(
                    ["git", "show", f"{commit}:{name}"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            except (OSError, subprocess.CalledProcessError):
                continue
            result.append((commit, root / name, content))
    return result


def scan_lines(filename: str, lines: list[str], findings: list[tuple[str, int, int]]) -> None:
    for line_number, line in enumerate(lines, start=1):
        for pattern_index, pattern in enumerate(PATTERNS):
            if pattern.search(line):
                findings.append((filename, line_number, pattern_index))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = ArgumentParser()
    parser.add_argument(
        "--history", action="store_true", help="also scan all reachable Git commits"
    )
    args = parser.parse_args()
    findings: list[tuple[str, int, int]] = []
    for path in current_files(root):
        if not path.is_file() or path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(root).parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        scan_lines(str(path.relative_to(root)), lines, findings)
    if args.history:
        for commit, path, content in history_files(root):
            history_findings: list[tuple[str, int, int]] = []
            scan_lines(str(path.relative_to(root)), content.splitlines(), history_findings)
            findings.extend(
                (f"{commit[:12]}:{filename}", line, pattern)
                for filename, line, pattern in history_findings
            )
    if findings:
        print("Potential secret pattern(s) detected; values are intentionally suppressed:")
        for filename, line_number, pattern_index in findings:
            print(f"- {filename}:{line_number} (pattern {pattern_index})")
        return 1
    print("Secret scan passed: no likely credential values detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
