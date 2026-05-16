from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.io import savemat

from mri_relaxkit.analysis import run_analysis
from mri_relaxkit.data import inspect_mat_file, load_relaxometry_mat
from mri_relaxkit.demo import write_demo_mat
from mri_relaxkit.release_audit import audit_release

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "AA1_data.mat"


pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


requires_legacy_fixture = pytest.mark.skipif(
    not SAMPLE.exists(), reason="legacy AA1_data.mat fixture is not distributed in public release"
)


@requires_legacy_fixture
def test_inspect_sample_dataset() -> None:
    summary = inspect_mat_file(SAMPLE)
    assert summary["variables"]["mGRE"]["shape"] == [224, 224, 30]
    assert summary["variables"]["TEs"]["shape"] == [30]
    assert summary["variables"]["data1"]["shape"] == [50]
    assert summary["variables"]["data2"]["shape"] == [60]


@requires_legacy_fixture
def test_legacy_fixture_golden_values(tmp_path: Path) -> None:
    run = tmp_path / "sample"
    result = run_analysis(SAMPLE, run)
    metrics = result["metrics"]
    qa = result["qa"]

    assert qa["status"] == "pass"
    assert metrics["fits"]["simulated_t2"]["linear"]["tau_ms"] == pytest.approx(76.8313, abs=0.01)
    assert metrics["fits"]["simulated_t1"]["linear"]["tau_ms"] == pytest.approx(1283.2766, abs=0.05)
    assert metrics["fits"]["t2star_gm"]["linear"]["tau_ms"] == pytest.approx(58.68, abs=0.05)
    assert metrics["fits"]["t2star_wm"]["linear"]["tau_ms"] == pytest.approx(49.47, abs=0.05)
    assert metrics["fits"]["contrast"]["max_contrast_te_ms"] == 90.0
    assert (run / "metrics.json").exists()
    assert (run / "qa.json").exists()
    assert (run / "report.md").exists()
    assert (run / "report.html").exists()
    assert (run / "figures" / "simulated_t2_fit.png").exists()


def test_missing_variables_are_rejected(tmp_path: Path) -> None:
    broken = tmp_path / "broken.mat"
    savemat(broken, {"time1": np.array([1, 2, 3]), "data1": np.array([0.1, 0.2, 0.3])})
    with pytest.raises(ValueError, match="Missing required MAT variables"):
        load_relaxometry_mat(broken)


def test_bad_voxel_is_rejected(tmp_path: Path) -> None:
    dataset = SAMPLE if SAMPLE.exists() else write_demo_mat(tmp_path / "demo-for-bad-voxel.mat")
    with pytest.raises(ValueError, match="outside image shape"):
        run_analysis(dataset, tmp_path / "bad", gm_voxel=(999, 1))


def test_cli_smoke_with_public_demo_data(tmp_path: Path) -> None:
    demo = tmp_path / "demo.mat"
    run = tmp_path / "cli"
    demo_cmd = subprocess.run(
        [sys.executable, "-m", "mri_relaxkit.cli", "demo-data", "--out", str(demo)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Wrote synthetic demo data" in demo_cmd.stdout

    inspect = subprocess.run(
        [sys.executable, "-m", "mri_relaxkit.cli", "inspect", str(demo), "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(inspect.stdout)["variables"]["mGRE"]["shape"] == [224, 224, 30]

    analyze = subprocess.run(
        [sys.executable, "-m", "mri_relaxkit.cli", "analyze", "--input", str(demo), "--out", str(run)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "QA: pass" in analyze.stdout

    review = subprocess.run(
        [sys.executable, "-m", "mri_relaxkit.cli", "review", "--run", str(run)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Status: pass" in review.stdout


def test_public_safe_demo_data_path(tmp_path: Path) -> None:
    demo = write_demo_mat(tmp_path / "demo.mat")
    summary = inspect_mat_file(demo)
    assert summary["variables"]["mGRE"]["shape"] == [224, 224, 30]
    run = run_analysis(demo, tmp_path / "demo-run")
    assert run["qa"]["status"] == "pass"


def test_release_audit_detects_secret_like_text(tmp_path: Path) -> None:
    key_name = "api" + "_key"
    fake_value = "1234567890abcdef" * 2
    (tmp_path / "note.txt").write_text(f"{key_name} = '{fake_value}'\n", encoding="utf-8")
    audit = audit_release(tmp_path)
    assert audit["status"] == "fail"
    assert audit["fail_count"] == 1
