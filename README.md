# MRI RelaxKit

MRI RelaxKit is a reusable MRI relaxometry SOP and CLI toolkit for research, education, and QA workflows. It converts a brittle MATLAB Live Script style assignment into a reproducible Python command-line workflow with auditable metrics, figures, reports, and release checks.

## Commercial Positioning

MRI RelaxKit is a B2B/B2Edu tool, not a consumer app.

Primary buyers and users:

- MRI course instructors who need a reliable teaching workflow without a heavy MATLAB dependency.
- Imaging research labs that want repeatable onboarding examples for T1, T2, and T2* fitting.
- Imaging core facilities that need lightweight protocol QA demos and training artifacts.
- Medtech and CRO imaging teams that need transparent, non-clinical SOP examples for internal education.

Why they would use it:

- It turns legacy MATLAB materials into a reproducible CLI and SOP.
- It records fit methods, voxel coordinate conventions, QA checks, and source-data fingerprints.
- It generates reusable artifacts that a team can review, archive, and regenerate.
- It is explicit about the non-clinical boundary, which makes it safer for public release and commercial discovery.

## Not Medical Advice

MRI RelaxKit is for research, education, QA, and protocol-training workflows. It is not a clinical diagnostic product and is not validated as a regulated medical device.

## Quick Start

Activate the `dl` conda environment:

```bash
conda activate dl
```

Generate public-safe synthetic demo data:

```bash
python -m mri_relaxkit.cli demo-data --out outputs/demo/demo_relaxometry.mat
```

Inspect the synthetic demo data:

```bash
python -m mri_relaxkit.cli inspect outputs/demo/demo_relaxometry.mat
```

Run and review the synthetic public-demo analysis:

```bash
python -m mri_relaxkit.cli analyze --input outputs/demo/demo_relaxometry.mat --out outputs/demo/run
python -m mri_relaxkit.cli review --run outputs/demo/run
```

If you have the local legacy assignment fixture, you can also run:

```bash
python -m mri_relaxkit.cli inspect AA1_data.mat
python -m mri_relaxkit.cli analyze --input AA1_data.mat --out outputs/sample
python -m mri_relaxkit.cli review --run outputs/sample
```

Review the generated run:

```bash
python -m mri_relaxkit.cli review --run outputs/sample
```

Run a public-release audit:

```bash
python -m mri_relaxkit.cli release-audit --root .
```

## Expected Sample Results

For the local `AA1_data.mat` fixture:

- Simulated T2: about `76.83 ms`
- Corrected simulated T1: about `1283.28 ms`
- Default GM example T2*: about `58.68 ms`
- Default WM/reference T2*: about `49.47 ms`
- Max GM/WM contrast TE: `90 ms`

Generated run artifacts are written under the output directory:

- `metrics.json`
- `qa.json`
- `report.md`
- `report.html`
- `figures/`

## Validation

```bash
conda activate dl
python -m mri_relaxkit.cli demo-data --out outputs/demo/demo_relaxometry.mat
python -m mri_relaxkit.cli analyze --input outputs/demo/demo_relaxometry.mat --out outputs/demo/run
python -m mri_relaxkit.cli review --run outputs/demo/run
python -m pytest
python -m mri_relaxkit.cli release-audit --root .
```

The release audit can pass while still reporting warnings. Warnings are intended to force human review before a public GitHub push, especially for original course materials, durable-memory files, private paths, or email addresses.
