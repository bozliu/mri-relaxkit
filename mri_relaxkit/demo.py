from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io import savemat


def write_demo_mat(path: str | Path) -> Path:
    """Write deterministic synthetic relaxometry demo data."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    time2 = np.arange(1, 297, 5, dtype=float)
    data2 = np.exp(-time2 / 78.0) + rng.normal(0.0, 0.012, size=time2.shape)
    data2 = np.clip(data2, 0.005, None)

    time1 = np.arange(1, 4902, 100, dtype=float)
    data1 = 1.0 - np.exp(-time1 / 1320.0) + rng.normal(0.0, 0.012, size=time1.shape)
    data1 = np.clip(data1, -0.01, 0.995)

    tes = 4.3 + 2.8 * np.arange(30, dtype=float)
    rows, cols = 224, 224
    yy, xx = np.mgrid[0:rows, 0:cols]
    gm_blob = np.exp(-(((yy - 122) ** 2) / (2 * 42**2) + ((xx - 42) ** 2) / (2 * 24**2)))
    wm_blob = np.exp(-(((yy - 116) ** 2) / (2 * 34**2) + ((xx - 144) ** 2) / (2 * 30**2)))
    anatomy = 3000.0 + 19000.0 * gm_blob + 22000.0 * wm_blob
    t2star_map = 35.0 + 25.0 * gm_blob + 15.0 * wm_blob
    mgre = np.empty((rows, cols, tes.size), dtype=np.float32)
    for index, te in enumerate(tes):
        echo = anatomy * np.exp(-te / t2star_map)
        echo += rng.normal(0.0, 35.0, size=echo.shape)
        mgre[:, :, index] = np.clip(echo, 0.0, None).astype(np.float32)

    savemat(
        out,
        {
            "TEs": tes.reshape(1, -1),
            "data1": data1.reshape(1, -1),
            "data2": data2.reshape(1, -1),
            "mGRE": mgre,
            "time1": time1.reshape(1, -1),
            "time2": time2.reshape(1, -1),
        },
    )
    return out
