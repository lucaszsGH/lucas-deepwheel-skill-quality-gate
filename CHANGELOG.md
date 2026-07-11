# Changelog

All notable user-visible changes are recorded here.

## [0.1.0-rc.1] - 2026-07-11

### Added

- Independent Skill and optional publication-package audit.
- CLEAN, CONCERNS, and BLOCK verdicts with stable exit codes.
- Safe reporting that does not echo matched values or target absolute paths.
- Generic local-path and PII checks.
- Publication-package, safe installer, version, and CI validation.
- Positive and negative behavior tests.

### Fixed

- Removed the stray byte before the Python shebang.
- Made missing targets and critical findings return a blocking exit code.
- Removed the same-filename scanner bypass.
- Replaced the maintainer-specific home-path rule with generic path patterns.
- Made an explicitly requested but missing publication directory block.
