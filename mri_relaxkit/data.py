from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import scipy.io as sio

REQUIRED_VARIABLES = ("TEs", "data1", "data2", "mGRE", "time1", "time2")


@dataclass(frozen=True)
class RelaxometryData:
    """Validated arrays from the legacy MATLAB relaxometry dataset."""

    path: Path
    TEs: np.ndarray
    data1: np.ndarray
    data2: np.ndarray
    mGRE: np.ndarray
    time1: np.ndarray
    time2: np.ndarray

    def summary(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "variables": {
                "TEs": _array_summary(self.TEs),
                "data1": _array_summary(self.data1),
                "data2": _array_summary(self.data2),
                "mGRE": _array_summary(self.mGRE),
                "time1": _array_summary(self.time1),
                "time2": _array_summary(self.time2),
            },
        }


def load_relaxometry_mat(path: str | Path) -> RelaxometryData:
    mat_path = Path(path)
    if not mat_path.exists():
        raise FileNotFoundError(f"MAT file not found: {mat_path}")

    raw = sio.loadmat(mat_path, squeeze_me=True, struct_as_record=False)
    missing = [name for name in REQUIRED_VARIABLES if name not in raw]
    if missing:
        raise ValueError(f"Missing required MAT variables: {', '.join(missing)}")

    data = RelaxometryData(
        path=mat_path,
        TEs=_as_1d_float(raw["TEs"], "TEs"),
        data1=_as_1d_float(raw["data1"], "data1"),
        data2=_as_1d_float(raw["data2"], "data2"),
        mGRE=_as_3d_float(raw["mGRE"], "mGRE"),
        time1=_as_1d_float(raw["time1"], "time1"),
        time2=_as_1d_float(raw["time2"], "time2"),
    )
    _validate_lengths(data)
    return data


def inspect_mat_file(path: str | Path) -> dict[str, Any]:
    data = load_relaxometry_mat(path)
    return data.summary()


def _as_1d_float(value: Any, name: str) -> np.ndarray:
    arr = np.asarray(value, dtype=float).squeeze()
    if arr.ndim != 1:
        raise ValueError(f"{name} must be a vector after squeezing; got shape {arr.shape}")
    if arr.size < 3:
        raise ValueError(f"{name} must contain at least 3 samples; got {arr.size}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


def _as_3d_float(value: Any, name: str) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if arr.ndim != 3:
        raise ValueError(f"{name} must be a 3D array; got shape {arr.shape}")
    if min(arr.shape) < 2:
        raise ValueError(f"{name} has an invalid image/echo shape: {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


def _validate_lengths(data: RelaxometryData) -> None:
    if data.time1.size != data.data1.size:
        raise ValueError("time1 and data1 must have the same length")
    if data.time2.size != data.data2.size:
        raise ValueError("time2 and data2 must have the same length")
    if data.TEs.size != data.mGRE.shape[2]:
        raise ValueError("TEs length must match the third dimension of mGRE")


def _array_summary(arr: np.ndarray) -> dict[str, Any]:
    return {
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "min": float(np.nanmin(arr)),
        "max": float(np.nanmax(arr)),
        "mean": float(np.nanmean(arr)),
    }
