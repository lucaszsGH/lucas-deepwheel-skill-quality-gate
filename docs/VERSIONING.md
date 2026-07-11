# Versioning / 版本管理

This repository is the single editable source. Draft and installed copies are snapshots and must not be edited as the source.

- `VERSION` is the single package-version source.
- Tags use the same value with a `v` prefix.
- `CHANGELOG.md` records user-visible changes and compatibility notes.
- Pull requests and automated validation must pass before a release.
- Installation remains a separate confirmed action.

Semantic versioning policy:

- patch: compatible fixes and documentation corrections;
- minor: backward-compatible capability additions;
- major: breaking CLI, report, or policy changes;
- pre-1.0 breaking changes must be explicit in release notes.

The report schema and product version may diverge later. A future report field should use a separate value such as `quality_gate_report_schema_version: 1` and include migration guidance.
