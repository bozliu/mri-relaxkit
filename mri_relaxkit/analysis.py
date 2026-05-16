from __future__ import annotations

import hashlib
import platform
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from . import __version__
from .data import load_relaxometry_mat
from .fitting import (
    LinearFitResult,
    fit_decay_nonlinear,
    fit_log_decay,
    fit_t1_recovery_linear,
    fit_t1_recovery_nonlinear,
)
from .reporting import write_json, write_reports

REFERENCE_SHA256 = "474d65deffba7f32fe7edb11d9e78ce93973e70ca732f683dfd711a50574064d"
REFERENCE_EXPECTED = {
    "simulated_t2_ms": (76.83, 0.75),
    "simulated_t1_ms": (1283.28, 2.0),
    "gm_t2star_ms": (58.68, 1.0),
    "max_contrast_te_ms": (90.0, 0.1),
}


def run_analysis(
    input_path: str | Path,
    out_dir: str | Path,
    gm_voxel: tuple[int, int] = (124, 43),
    wm_voxel: tuple[int, int] = (118, 145),
) -> dict[str, Any]:
    data = load_relaxometry_mat(input_path)
    out = Path(out_dir)
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    t2_linear = fit_log_decay(data.time2, data.data2, "simulated_t2")
    t2_nonlinear = fit_decay_nonlinear(data.time2, data.data2, "simulated_t2")
    t1_linear = fit_t1_recovery_linear(data.time1, data.data1, "simulated_t1", m0=1.0)
    t1_nonlinear = fit_t1_recovery_nonlinear(data.time1, data.data1, "simulated_t1")

    gm_signal = _voxel_signal(data.mGRE, gm_voxel)
    wm_signal = _voxel_signal(data.mGRE, wm_voxel)
    gm_t2star = fit_log_decay(data.TEs, gm_signal, "t2star_gm")
    wm_t2star = fit_log_decay(data.TEs, wm_signal, "t2star_wm")
    gm_nonlinear = fit_decay_nonlinear(data.TEs, gm_signal, "t2star_gm")
    wm_nonlinear = fit_decay_nonlinear(data.TEs, wm_signal, "t2star_wm")
    contrast = _contrast_metrics()

    _plot_signal_and_fit(figures / "simulated_t2_fit.png", data.time2, data.data2, t2_linear, "Simulated T2 Decay", "Echo time (ms)", "Signal")
    _plot_log_fit(figures / "simulated_t2_log_fit.png", t2_linear, "Simulated T2 Log-Linear Fit", "Echo time (ms)")
    _plot_signal_and_fit(figures / "simulated_t1_fit.png", data.time1, data.data1, t1_linear, "Simulated T1 Recovery", "Time (ms)", "Magnetization")
    _plot_log_fit(figures / "simulated_t1_log_fit.png", t1_linear, "Simulated T1 Log-Linear Fit", "Time (ms)")
    _plot_gre_echoes(figures / "gre_echoes.png", data.mGRE, data.TEs)
    _plot_signal_and_fit(figures / "gm_t2star_fit.png", data.TEs, gm_signal, gm_t2star, "GM Example T2* Decay", "TE (ms)", "Signal")
    _plot_signal_and_fit(figures / "wm_t2star_fit.png", data.TEs, wm_signal, wm_t2star, "WM/Reference T2* Decay", "TE (ms)", "Signal")
    _plot_contrast(figures / "gm_wm_contrast.png", contrast)

    input_sha = _sha256(data.path)
    artifacts = {
        "figures_dir": str(figures),
        "simulated_t2_fit": str(figures / "simulated_t2_fit.png"),
        "simulated_t1_fit": str(figures / "simulated_t1_fit.png"),
        "gre_echoes": str(figures / "gre_echoes.png"),
        "gm_t2star_fit": str(figures / "gm_t2star_fit.png"),
        "wm_t2star_fit": str(figures / "wm_t2star_fit.png"),
        "contrast": str(figures / "gm_wm_contrast.png"),
        "metrics": str(out / "metrics.json"),
        "qa": str(out / "qa.json"),
        "report_md": str(out / "report.md"),
        "report_html": str(out / "report.html"),
    }
    metrics: dict[str, Any] = {
        "tool": {"name": "mri-relaxkit", "version": __version__, "python": platform.python_version()},
        "input": {"path": str(data.path), "sha256": input_sha},
        "dataset": data.summary(),
        "fits": {
            "simulated_t2": {"linear": t2_linear.to_dict(), "nonlinear": t2_nonlinear},
            "simulated_t1": {"linear": t1_linear.to_dict(), "nonlinear": t1_nonlinear},
            "t2star_gm": {
                "voxel_matlab_1based": list(gm_voxel),
                "voxel_python_0based": list(_matlab_to_python_voxel(gm_voxel, data.mGRE.shape)),
                "linear": gm_t2star.to_dict(),
                "nonlinear": gm_nonlinear,
            },
            "t2star_wm": {
                "voxel_matlab_1based": list(wm_voxel),
                "voxel_python_0based": list(_matlab_to_python_voxel(wm_voxel, data.mGRE.shape)),
                "linear": wm_t2star.to_dict(),
                "nonlinear": wm_nonlinear,
            },
            "contrast": {
                "t2wm_ms": 74.0,
                "t2gm_ms": 110.0,
                "max_contrast_te_ms": contrast["max_contrast_te_ms"],
                "max_contrast": contrast["max_contrast"],
            },
            "inversion_recovery_extra": {"t1gm_ms": 1322.0, "gray_matter_null_ti_ms": float(1322.0 * np.log(2.0))},
        },
        "artifacts": artifacts,
    }
    qa = build_qa(metrics)

    write_json(out / "metrics.json", metrics)
    write_json(out / "qa.json", qa)
    write_reports(out, metrics, qa)
    return {"metrics": metrics, "qa": qa}


def build_qa(metrics: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "status": "pass" if passed else "fail", "detail": detail})

    fits = metrics["fits"]
    add("simulated_t2_plausible", 20.0 <= fits["simulated_t2"]["linear"]["tau_ms"] <= 200.0, "T2 should be within a teaching-data plausible range.")
    add("simulated_t1_plausible", 300.0 <= fits["simulated_t1"]["linear"]["tau_ms"] <= 3000.0, "T1 should be within a teaching-data plausible range.")
    add("gm_t2star_plausible", 5.0 <= fits["t2star_gm"]["linear"]["tau_ms"] <= 120.0, "GM example T2* should be plausible for 7T teaching data.")
    add("wm_t2star_plausible", 5.0 <= fits["t2star_wm"]["linear"]["tau_ms"] <= 120.0, "WM/reference T2* should be plausible for 7T teaching data.")
    add("contrast_te_grid", fits["contrast"]["max_contrast_te_ms"] == 90.0, "Default Wanaspura 3T example should peak at 90 ms on the 5 ms grid.")
    for key in ("simulated_t2", "simulated_t1", "t2star_gm", "t2star_wm"):
        linear = fits[key]["linear"]
        add(f"{key}_uses_enough_samples", linear["n_used"] >= 0.9 * linear["n_total"], "Fit uses at least 90% of available samples.")

    if metrics["input"]["sha256"] == REFERENCE_SHA256:
        add("reference_dataset_detected", True, "AA1_data.mat reference fixture recognized.")
        add("reference_t2_regression", _within(fits["simulated_t2"]["linear"]["tau_ms"], *REFERENCE_EXPECTED["simulated_t2_ms"]), "Reference T2 matches expected value.")
        add("reference_t1_regression", _within(fits["simulated_t1"]["linear"]["tau_ms"], *REFERENCE_EXPECTED["simulated_t1_ms"]), "Reference T1 matches corrected expected value.")
        add("reference_gm_t2star_regression", _within(fits["t2star_gm"]["linear"]["tau_ms"], *REFERENCE_EXPECTED["gm_t2star_ms"]), "Reference GM T2* matches expected voxel result.")
        add("reference_contrast_regression", _within(fits["contrast"]["max_contrast_te_ms"], *REFERENCE_EXPECTED["max_contrast_te_ms"]), "Reference contrast TE matches expected value.")

    passed = sum(1 for check in checks if check["status"] == "pass")
    return {
        "status": "pass" if passed == len(checks) else "fail",
        "passed_checks": passed,
        "total_checks": len(checks),
        "checks": checks,
    }


def review_run(run_dir: str | Path) -> dict[str, Any]:
    run = Path(run_dir)
    metrics_path = run / "metrics.json"
    qa_path = run / "qa.json"
    if not metrics_path.exists() or not qa_path.exists():
        missing = [str(path) for path in (metrics_path, qa_path) if not path.exists()]
        return {"status": "fail", "reason": f"Missing run artifacts: {', '.join(missing)}"}

    import json

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    missing_artifacts = [
        path for path in metrics.get("artifacts", {}).values() if isinstance(path, str) and not Path(path).exists()
    ]
    status = "pass" if qa.get("status") == "pass" and not missing_artifacts else "fail"
    return {
        "status": status,
        "qa_status": qa.get("status"),
        "passed_checks": qa.get("passed_checks"),
        "total_checks": qa.get("total_checks"),
        "missing_artifacts": missing_artifacts,
        "summary": {
            "simulated_t2_ms": metrics["fits"]["simulated_t2"]["linear"]["tau_ms"],
            "simulated_t1_ms": metrics["fits"]["simulated_t1"]["linear"]["tau_ms"],
            "gm_t2star_ms": metrics["fits"]["t2star_gm"]["linear"]["tau_ms"],
            "max_contrast_te_ms": metrics["fits"]["contrast"]["max_contrast_te_ms"],
        },
    }


def _matlab_to_python_voxel(voxel: tuple[int, int], shape: tuple[int, int, int]) -> tuple[int, int]:
    row, col = voxel
    if row < 1 or col < 1 or row > shape[0] or col > shape[1]:
        raise ValueError(f"MATLAB 1-based voxel {voxel} is outside image shape {shape[:2]}")
    return row - 1, col - 1


def _voxel_signal(mgre: np.ndarray, voxel: tuple[int, int]) -> np.ndarray:
    row, col = _matlab_to_python_voxel(voxel, mgre.shape)
    return np.asarray(mgre[row, col, :], dtype=float)


def _contrast_metrics() -> dict[str, Any]:
    t = np.arange(0.0, 300.0 + 5.0, 5.0)
    wm = np.exp(-t / 74.0)
    gm = np.exp(-t / 110.0)
    contrast = gm - wm
    index = int(np.argmax(contrast))
    return {
        "time_ms": t,
        "white_matter_signal": wm,
        "gray_matter_signal": gm,
        "contrast": contrast,
        "max_contrast_te_ms": float(t[index]),
        "max_contrast": float(contrast[index]),
    }


def _plot_signal_and_fit(path: Path, x: np.ndarray, y: np.ndarray, fit: LinearFitResult, title: str, xlabel: str, ylabel: str) -> None:
    plt.figure(figsize=(7, 4))
    plt.plot(x, y, "o", label="Observed", markersize=4)
    order = np.argsort(fit.x_used)
    plt.plot(fit.x_used[order], fit.signal_fit[order], "r-", label=f"Fit tau={fit.tau_ms:.2f} ms")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_log_fit(path: Path, fit: LinearFitResult, title: str, xlabel: str) -> None:
    plt.figure(figsize=(7, 4))
    plt.plot(fit.x_used, fit.y_log, "o", label="Linearized observed", markersize=4)
    order = np.argsort(fit.x_used)
    plt.plot(fit.x_used[order], fit.y_log_fit[order], "r-", label="Log-linear fit")
    plt.xlabel(xlabel)
    plt.ylabel("Log-transformed signal")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_gre_echoes(path: Path, mgre: np.ndarray, tes: np.ndarray) -> None:
    echo_indices = [4, 14, 24]
    plt.figure(figsize=(9, 3))
    for i, echo_index in enumerate(echo_indices, start=1):
        plt.subplot(1, 3, i)
        plt.imshow(mgre[:, :, echo_index], cmap="gray", origin="upper")
        plt.title(f"TE = {tes[echo_index]:.1f} ms")
        plt.axis("off")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_contrast(path: Path, contrast: dict[str, Any]) -> None:
    t = contrast["time_ms"]
    plt.figure(figsize=(7, 4))
    plt.plot(t, contrast["white_matter_signal"], label="White matter T2=74 ms")
    plt.plot(t, contrast["gray_matter_signal"], label="Gray matter T2=110 ms")
    plt.plot(t, contrast["contrast"], label="GM - WM contrast")
    plt.axvline(contrast["max_contrast_te_ms"], color="black", linestyle="--", label="Max contrast TE")
    plt.xlabel("Echo time (ms)")
    plt.ylabel("Normalized signal / contrast")
    plt.title("T2 Contrast Optimization")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _within(value: float, expected: float, tolerance: float) -> bool:
    return abs(float(value) - expected) <= tolerance
