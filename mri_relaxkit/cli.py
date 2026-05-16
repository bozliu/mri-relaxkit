from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .analysis import review_run, run_analysis
from .data import inspect_mat_file
from .demo import write_demo_mat
from .release_audit import audit_release


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mri-relax",
        description="MRI RelaxKit reproducible relaxometry SOP and CLI toolkit.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect required MAT variables.")
    inspect_parser.add_argument("mat_file", type=Path)
    inspect_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    analyze_parser = subparsers.add_parser("analyze", help="Run relaxometry analysis and SOP artifact generation.")
    analyze_parser.add_argument("--input", required=True, type=Path, help="Input MAT file.")
    analyze_parser.add_argument("--out", required=True, type=Path, help="Output directory.")
    analyze_parser.add_argument("--gm-voxel", default="124,43", help="MATLAB 1-based row,column voxel for GM example.")
    analyze_parser.add_argument("--wm-voxel", default="118,145", help="MATLAB 1-based row,column voxel for WM/reference example.")

    demo_parser = subparsers.add_parser("demo-data", help="Generate deterministic synthetic demo MAT data.")
    demo_parser.add_argument("--out", required=True, type=Path, help="Output MAT file path.")

    review_parser = subparsers.add_parser("review", help="Review a generated analysis run.")
    review_parser.add_argument("--run", required=True, type=Path, help="Run output directory.")
    review_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    audit_parser = subparsers.add_parser("release-audit", help="Scan a repo before public GitHub release.")
    audit_parser.add_argument("--root", default=Path("."), type=Path, help="Repository root to scan.")
    audit_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")

    args = parser.parse_args(argv)

    if args.command == "inspect":
        summary = inspect_mat_file(args.mat_file)
        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        else:
            print(f"MAT file: {summary['path']}")
            for name, info in summary["variables"].items():
                print(f"- {name}: shape={info['shape']} min={info['min']:.6g} max={info['max']:.6g}")
        return 0

    if args.command == "analyze":
        result = run_analysis(
            input_path=args.input,
            out_dir=args.out,
            gm_voxel=_parse_voxel(args.gm_voxel, "--gm-voxel"),
            wm_voxel=_parse_voxel(args.wm_voxel, "--wm-voxel"),
        )
        metrics = result["metrics"]
        qa = result["qa"]
        print(f"Wrote run: {args.out}")
        print(f"QA: {qa['status']} ({qa['passed_checks']}/{qa['total_checks']} checks)")
        print(f"T2={metrics['fits']['simulated_t2']['linear']['tau_ms']:.2f} ms")
        print(f"T1={metrics['fits']['simulated_t1']['linear']['tau_ms']:.2f} ms")
        print(f"GM T2*={metrics['fits']['t2star_gm']['linear']['tau_ms']:.2f} ms")
        print(f"Max contrast TE={metrics['fits']['contrast']['max_contrast_te_ms']:.1f} ms")
        return 0 if qa["status"] == "pass" else 2

    if args.command == "demo-data":
        out = write_demo_mat(args.out)
        print(f"Wrote synthetic demo data: {out}")
        return 0

    if args.command == "review":
        review = review_run(args.run)
        if args.json:
            print(json.dumps(review, indent=2, sort_keys=True))
        else:
            print(f"Run: {args.run}")
            print(f"Status: {review['status']}")
            if review["status"] == "pass":
                for name, value in review["summary"].items():
                    print(f"- {name}: {value:.4g}")
            else:
                print(review)
        return 0 if review["status"] == "pass" else 2

    if args.command == "release-audit":
        audit = audit_release(args.root)
        if args.json:
            print(json.dumps(audit, indent=2, sort_keys=True))
        else:
            print(f"Release audit: {audit['status']} ({audit['fail_count']} fails, {audit['warn_count']} warnings)")
            for finding in audit["findings"]:
                print(f"- [{finding['severity']}] {finding['file']}: {finding['detail']}")
        return 0 if audit["status"] == "pass" else 2

    parser.error(f"Unknown command: {args.command}")
    return 2


def _parse_voxel(value: str, flag: str) -> tuple[int, int]:
    try:
        row_text, col_text = value.split(",", maxsplit=1)
        row, col = int(row_text), int(col_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{flag} must be formatted as row,column") from exc
    if row < 1 or col < 1:
        raise argparse.ArgumentTypeError(f"{flag} must use MATLAB 1-based positive coordinates")
    return row, col


if __name__ == "__main__":
    raise SystemExit(main())
