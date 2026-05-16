# MRI RelaxKit SOP

## Purpose

This SOP describes how to run MRI RelaxKit as a reusable relaxometry workflow for education, research training, imaging-core QA demos, and non-clinical protocol review.

## Inputs

The current CLI expects a MATLAB `.mat` file with:

- `time1`: T1 recovery time points in ms
- `data1`: T1 recovery signal
- `time2`: T2 echo time points in ms
- `data2`: T2 decay signal
- `TEs`: GRE echo times in ms
- `mGRE`: multi-echo GRE image stack with shape `row, column, echo`

## Procedure

1. Activate the `dl` conda environment.
2. Inspect the input with `python -m mri_relaxkit.cli inspect <input.mat>`.
3. Choose MATLAB-style 1-based row,column voxels for representative GM and WM/reference examples.
4. Run `python -m mri_relaxkit.cli analyze --input <input.mat> --out outputs/<run> --gm-voxel row,col --wm-voxel row,col`.
5. Run `python -m mri_relaxkit.cli review --run outputs/<run>`.
6. Review `metrics.json`, `qa.json`, `report.md`, `report.html`, and `figures/`.
7. Before GitHub publication, run `python -m mri_relaxkit.cli release-audit --root .` and resolve all failures plus any warnings relevant to public release.

For a public-safe demo that does not redistribute original course files:

```bash
python -m mri_relaxkit.cli demo-data --out outputs/demo/demo_relaxometry.mat
python -m mri_relaxkit.cli analyze --input outputs/demo/demo_relaxometry.mat --out outputs/demo/run
python -m mri_relaxkit.cli review --run outputs/demo/run
```

## Fit Models

- T2 and T2*: `S = S0 * exp(-TE / tau)`, fit by transparent log-linear least squares.
- Simulated T2 also receives a nonlinear curve-fit cross-check.
- T1: `Mz = M0 * (1 - exp(-t / T1))`, fit with corrected `log(1 - signal/M0)` linearization plus nonlinear recovery cross-check.
- GM/WM contrast: normalized exponential curves with `T2wm = 74 ms`, `T2gm = 110 ms`, sampled on a `0:5:300 ms` grid.

## QA Gates

The generated `qa.json` checks:

- Required variables and array dimensions.
- Positive/plausible fitted relaxation constants.
- Sample usage after log-domain filtering.
- Expected values for the known local reference fixture.
- Generated run review and artifact presence.

## Operator Notes

- Voxel coordinates are MATLAB-style 1-based row,column coordinates.
- Default voxels come from the legacy assignment material and are not automated tissue segmentation.
- Linearized fits are chosen for transparency and teaching value; nonlinear checks help identify obvious drift.
- Public release should replace or explicitly license third-party course artifacts before publishing.
