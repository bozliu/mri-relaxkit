"""MRI RelaxKit: reproducible MRI relaxometry SOP and CLI toolkit."""

__version__ = "0.1.0"

from .analysis import run_analysis
from .data import RelaxometryData, inspect_mat_file, load_relaxometry_mat

__all__ = [
    "RelaxometryData",
    "inspect_mat_file",
    "load_relaxometry_mat",
    "run_analysis",
]
