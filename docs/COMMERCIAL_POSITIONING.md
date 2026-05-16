# Commercial Positioning

## Recommendation

Position MRI RelaxKit as B2B/B2Edu infrastructure for MRI training, research reproducibility, and imaging-core QA. Do not position it as a B2C app.

## Buyer

- MRI course leads and departments.
- Imaging research lab principal investigators and lab managers.
- Imaging core facility directors and staff scientists.
- Medtech/CRO imaging operations teams.

## User

- Graduate students and trainees learning relaxometry.
- Staff scientists teaching or reviewing protocol behavior.
- Research engineers converting old MATLAB analysis into reproducible Python.
- QA operators who need a transparent demo workflow for T1/T2/T2* fitting.

## Why They Buy Or Adopt

- Reduces MATLAB installation friction for teaching and onboarding.
- Makes old one-off scripts reproducible, inspectable, and testable.
- Creates an audit trail with data hashes, fit methods, coordinate conventions, metrics, QA checks, figures, and reports.
- Helps teams teach protocol tradeoffs such as T2 contrast selection, voxel choice, and fit residual inspection.
- Gives a public GitHub asset that can lead to paid customization, training, support, or internal SOP integration.

## What Practitioners Can Do

- Inspect a relaxometry MAT file and verify it has the expected schema.
- Run T1, T2, and T2* fitting without MATLAB.
- Generate figures and machine-readable metrics for review.
- Compare fitted values against teaching-data expectations.
- Run a release audit before publishing a repo or sharing an SOP.
- Extend the package to local datasets while preserving the same QA contract.

## Boundaries

- This is not a diagnostic tool.
- This is not automated tissue segmentation.
- This is not a substitute for regulatory validation.
- Public release requires review of third-party source data, course material permissions, private paths, emails, and durable-memory files.
