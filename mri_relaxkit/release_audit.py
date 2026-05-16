from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

IGNORED_DIRS = {".git", ".omx", "__pycache__", ".pytest_cache", "outputs", "dist", "build"}
INTERNAL_FILES = {"Prompt.md", "Plan.md", "Implement.md", "Documentation.md"}
THIRD_PARTY_REVIEW_FILES = {"BME 495_HW.pdf", "BME495_AnalysisAssignment1.mlx", "AA1_data.mat"}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}"),
]
PRIVATE_PATTERNS = [
    re.compile(r"/Users/[A-Za-z0-9._-]+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]


@dataclass(frozen=True)
class Finding:
    severity: str
    file: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "file": self.file, "detail": self.detail}


def audit_release(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    findings: list[Finding] = []
    for path in _iter_files(root_path):
        rel = str(path.relative_to(root_path))
        if path.name in INTERNAL_FILES:
            findings.append(Finding("warn", rel, "Project durable-memory file; review before public GitHub release."))
        if path.name in THIRD_PARTY_REVIEW_FILES:
            findings.append(Finding("warn", rel, "Original course/source artifact; confirm redistribution rights or replace with synthetic demo data."))
        text = _read_text(path)
        if text is None:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(Finding("fail", rel, "Potential secret-like token or private key pattern."))
        for pattern in PRIVATE_PATTERNS:
            if pattern.search(text):
                findings.append(Finding("warn", rel, "Potential private path or email address."))

    fail_count = sum(1 for finding in findings if finding.severity == "fail")
    warn_count = sum(1 for finding in findings if finding.severity == "warn")
    return {
        "status": "fail" if fail_count else "pass",
        "fail_count": fail_count,
        "warn_count": warn_count,
        "findings": [finding.to_dict() for finding in findings],
    }


def _iter_files(root: Path) -> Iterable[Path]:
    git_files = _git_release_files(root)
    if git_files is not None:
        for rel in git_files:
            path = root / rel
            if path.is_file():
                yield path
        return

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _git_release_files(root: Path) -> list[Path] | None:
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def _read_text(path: Path) -> str | None:
    if path.stat().st_size > 2_000_000:
        return None
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
