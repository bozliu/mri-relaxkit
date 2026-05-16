from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from scipy.optimize import curve_fit


@dataclass
class LinearFitResult:
    label: str
    method: str
    intercept: float
    slope: float
    tau_ms: float
    tau_se_ms: float | None
    rmse_log: float
    r2_log: float
    n_total: int
    n_used: int
    n_excluded: int
    x_used: np.ndarray
    y_log: np.ndarray
    y_log_fit: np.ndarray
    signal_used: np.ndarray
    signal_fit: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "method": self.method,
            "intercept": self.intercept,
            "slope": self.slope,
            "tau_ms": self.tau_ms,
            "tau_se_ms": self.tau_se_ms,
            "rmse_log": self.rmse_log,
            "r2_log": self.r2_log,
            "n_total": self.n_total,
            "n_used": self.n_used,
            "n_excluded": self.n_excluded,
        }


def fit_log_decay(x: np.ndarray, signal: np.ndarray, label: str) -> LinearFitResult:
    """Fit S = S0 * exp(-x / tau) through log-linear least squares."""

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(signal, dtype=float)
    mask = y_arr > 0
    if mask.sum() < 3:
        raise ValueError(f"{label}: at least 3 positive signal samples are required")

    x_used = x_arr[mask]
    signal_used = y_arr[mask]
    y_log = np.log(signal_used)
    return _linear_fit(
        x_used=x_used,
        y_log=y_log,
        signal_used=signal_used,
        label=label,
        method="log_linear_decay",
        tau_sign=-1.0,
        n_total=y_arr.size,
    )


def fit_t1_recovery_linear(
    x: np.ndarray, signal: np.ndarray, label: str, m0: float = 1.0
) -> LinearFitResult:
    """Fit Mz = M0 * (1 - exp(-x / T1)) through log(1 - M/M0)."""

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(signal, dtype=float)
    transformed = 1.0 - (y_arr / m0)
    mask = transformed > 0
    if mask.sum() < 3:
        raise ValueError(f"{label}: at least 3 samples with 1 - signal/m0 > 0 are required")

    x_used = x_arr[mask]
    y_log = np.log(transformed[mask])
    signal_used = y_arr[mask]
    result = _linear_fit(
        x_used=x_used,
        y_log=y_log,
        signal_used=signal_used,
        label=label,
        method="log_linear_t1_recovery",
        tau_sign=-1.0,
        n_total=y_arr.size,
    )
    result.signal_fit = m0 * (1.0 - np.exp(result.y_log_fit))
    return result


def fit_decay_nonlinear(x: np.ndarray, signal: np.ndarray, label: str) -> dict[str, Any]:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(signal, dtype=float)
    mask = y_arr > 0
    x_used = x_arr[mask]
    y_used = y_arr[mask]
    if x_used.size < 3:
        return {"label": label, "method": "nonlinear_decay", "status": "fail", "reason": "too_few_positive_samples"}

    def model(t: np.ndarray, s0: float, tau: float) -> np.ndarray:
        return s0 * np.exp(-t / tau)

    return _curve_fit_to_dict(
        x_used,
        y_used,
        model,
        p0=(max(float(y_used.max()), 1e-6), max(float(np.median(x_used)), 1.0)),
        label=label,
        method="nonlinear_decay",
        tau_index=1,
        param_names=("s0", "tau_ms"),
    )


def fit_t1_recovery_nonlinear(x: np.ndarray, signal: np.ndarray, label: str) -> dict[str, Any]:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(signal, dtype=float)

    def model(t: np.ndarray, m0: float, tau: float, offset: float) -> np.ndarray:
        return offset + m0 * (1.0 - np.exp(-t / tau))

    return _curve_fit_to_dict(
        x_arr,
        y_arr,
        model,
        p0=(1.0, max(float(np.median(x_arr)), 1.0), min(float(y_arr.min()), 0.0)),
        label=label,
        method="nonlinear_t1_recovery",
        tau_index=1,
        param_names=("m0", "tau_ms", "offset"),
    )


def _linear_fit(
    *,
    x_used: np.ndarray,
    y_log: np.ndarray,
    signal_used: np.ndarray,
    label: str,
    method: str,
    tau_sign: float,
    n_total: int,
) -> LinearFitResult:
    X = np.column_stack([np.ones_like(x_used), x_used])
    beta, *_ = np.linalg.lstsq(X, y_log, rcond=None)
    y_fit = X @ beta
    residuals = y_log - y_fit
    rmse = float(np.sqrt(np.mean(residuals**2)))
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y_log - np.mean(y_log)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    slope = float(beta[1])
    tau = float(tau_sign / slope)
    tau_se = _tau_standard_error(X, residuals, slope, tau_sign)
    signal_fit = np.exp(y_fit)

    return LinearFitResult(
        label=label,
        method=method,
        intercept=float(beta[0]),
        slope=slope,
        tau_ms=tau,
        tau_se_ms=tau_se,
        rmse_log=rmse,
        r2_log=float(r2),
        n_total=int(n_total),
        n_used=int(x_used.size),
        n_excluded=int(n_total - x_used.size),
        x_used=x_used,
        y_log=y_log,
        y_log_fit=y_fit,
        signal_used=signal_used,
        signal_fit=signal_fit,
    )


def _tau_standard_error(
    X: np.ndarray, residuals: np.ndarray, slope: float, tau_sign: float
) -> float | None:
    dof = X.shape[0] - X.shape[1]
    if dof <= 0:
        return None
    try:
        sigma2 = float(np.sum(residuals**2) / dof)
        cov = sigma2 * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return None
    slope_se = float(np.sqrt(max(cov[1, 1], 0.0)))
    return float(abs(tau_sign / (slope**2)) * slope_se)


def _curve_fit_to_dict(
    x: np.ndarray,
    y: np.ndarray,
    model: Callable[..., np.ndarray],
    p0: tuple[float, ...],
    label: str,
    method: str,
    tau_index: int,
    param_names: tuple[str, ...],
) -> dict[str, Any]:
    try:
        popt, pcov = curve_fit(model, x, y, p0=p0, maxfev=20000)
        y_fit = model(x, *popt)
        residuals = y - y_fit
        rmse = float(np.sqrt(np.mean(residuals**2)))
        ss_res = float(np.sum(residuals**2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        tau_se = None
        if pcov.shape[0] > tau_index and np.isfinite(pcov[tau_index, tau_index]):
            tau_se = float(np.sqrt(max(float(pcov[tau_index, tau_index]), 0.0)))
        params = {name: float(value) for name, value in zip(param_names, popt)}
        return {
            "label": label,
            "method": method,
            "status": "pass",
            "parameters": params,
            "tau_ms": float(popt[tau_index]),
            "tau_se_ms": tau_se,
            "rmse_signal": rmse,
            "r2_signal": float(r2),
            "n_used": int(x.size),
        }
    except Exception as exc:  # pragma: no cover - defensive status path
        return {"label": label, "method": method, "status": "fail", "reason": str(exc)}
