from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_reports(out_dir: Path, metrics: dict[str, Any], qa: dict[str, Any]) -> None:
    markdown = _markdown_report(metrics, qa)
    (out_dir / "report.md").write_text(markdown, encoding="utf-8")
    (out_dir / "report.html").write_text(_html_report(markdown), encoding="utf-8")


def _markdown_report(metrics: dict[str, Any], qa: dict[str, Any]) -> str:
    fits = metrics["fits"]
    artifacts = metrics["artifacts"]
    qa_status = "PASS" if qa["status"] == "pass" else "FAIL"
    return f"""# MRI RelaxKit SOP Run Report

## Commercial Use Case

MRI RelaxKit is a reusable B2B/B2Edu SOP and CLI toolkit for MRI courses, imaging research labs, imaging core facilities, and medtech/CRO teams. It turns legacy MATLAB relaxometry exercises into reproducible Python analysis with auditable metrics, QA checks, and reviewable figures.

This output is for research, education, QA, and protocol-training workflows. It is not a clinical diagnosis tool or a regulated medical-device workflow.

## Dataset

- Input: `{metrics['input']['path']}`
- SHA256: `{metrics['input']['sha256']}`
- TEs: {metrics['dataset']['variables']['TEs']['shape']}
- mGRE: {metrics['dataset']['variables']['mGRE']['shape']}

## Key Results

- Simulated T2 log-linear fit: {fits['simulated_t2']['linear']['tau_ms']:.2f} ms
- Simulated T1 corrected log-linear fit: {fits['simulated_t1']['linear']['tau_ms']:.2f} ms
- GM example T2* fit at MATLAB voxel {fits['t2star_gm']['voxel_matlab_1based']}: {fits['t2star_gm']['linear']['tau_ms']:.2f} ms
- WM/reference T2* fit at MATLAB voxel {fits['t2star_wm']['voxel_matlab_1based']}: {fits['t2star_wm']['linear']['tau_ms']:.2f} ms
- Max GM/WM T2 contrast TE: {fits['contrast']['max_contrast_te_ms']:.1f} ms
- Optional inversion-recovery GM null TI: {fits['inversion_recovery_extra']['gray_matter_null_ti_ms']:.1f} ms

## QA Status

- Overall: {qa_status}
- Passed checks: {qa['passed_checks']} / {qa['total_checks']}

## SOP Artifacts

"""
    for name, path in artifacts.items():
        if isinstance(path, str):
            markdown += f"- {name}: `{path}`\n"
    markdown += "\n## Operator Review\n\n"
    markdown += "1. Confirm input SHA256 matches the intended dataset.\n"
    markdown += "2. Review fit residual figures before using values in teaching or QA decisions.\n"
    markdown += "3. Confirm voxel coordinates are interpreted as MATLAB 1-based `(row, column)` coordinates.\n"
    markdown += "4. If using a new dataset, update SOP acceptance thresholds before public release claims.\n"
    return markdown


def _html_report(markdown: str) -> str:
    body = []
    for line in markdown.splitlines():
        escaped = html.escape(line)
        if line.startswith("# "):
            body.append(f"<h1>{escaped[2:]}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{escaped[3:]}</h2>")
        elif line.startswith("- "):
            body.append(f"<p>{escaped}</p>")
        elif line.startswith("1. ") or line.startswith("2. ") or line.startswith("3. ") or line.startswith("4. "):
            body.append(f"<p>{escaped}</p>")
        elif not line.strip():
            body.append("")
        else:
            body.append(f"<p>{escaped}</p>")
    return "<!doctype html><html><head><meta charset=\"utf-8\"><title>MRI RelaxKit Report</title></head><body>\n" + "\n".join(body) + "\n</body></html>\n"
