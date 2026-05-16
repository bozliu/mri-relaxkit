# Public Release Checklist

Before pushing this repository to a public GitHub repo:

- Run `python -m mri_relaxkit.cli release-audit --root .`.
- Resolve every `fail` finding.
- Review every `warn` finding.
- Remove or replace local absolute machine paths and usernames.
- Remove or rewrite internal durable-memory files if they are not intended for publication.
- Confirm redistribution rights for original course PDFs, MATLAB Live Scripts, and `.mat` data files.
- Prefer synthetic or explicitly licensed demo data for public examples.
- Use `python -m mri_relaxkit.cli demo-data --out outputs/demo/demo_relaxometry.mat` to create synthetic demo data if original course files cannot be redistributed.
- Confirm the README states the non-clinical, non-regulated boundary.
- Confirm tests pass under the documented `dl` conda environment.
- Confirm generated outputs are ignored or intentionally published.
- Confirm no tokens, API keys, credentials, private emails, or private machine state are present.
