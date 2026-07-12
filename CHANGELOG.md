# Changelog

## [0.1.0-rc.4] - 2026-07-12

- Require every high-risk Skill to declare an executable behavioral safety contract.
- Require publication packages to expose a static behavior-test path and seven baseline negative-case identifiers.
- Block missing or incomplete consent, data-subject, minimum-input, safety-preflight, stop-routing, blocked-output and source-provenance regression evidence.
- Keep target-code execution in the target repository CI rather than running untrusted code inside Quality Gate.

## [0.1.0-rc.3] - 2026-07-12

- Block public release of high-risk personalized numeric guidance when professional sign-off is missing, pending or stale.
- Allow an explicitly education-only, numeric-disabled high-risk candidate to remain CONCERNS while awaiting professional review.

## [0.1.0-rc.2] - 2026-07-12

- Add machine-readable risk profiles.
- Block under-classified health, genetics, nutrition, legal and financial Skills.
- Require consent, human review, source provenance and refusal controls for high-risk Skills.
- Add positive and negative high-risk behavior tests.
- Require bilingual GitHub hero and workflow assets for CLEAN publication readiness.
- Require a publication roadmap in the DeepWheel family baseline.
- Require a machine contract for numeric high-risk guidance.
- Prevent CLEAN when the publication checklist still contains incomplete items.
- Require a recorded review document in the DeepWheel publication baseline.
- Require explicit approved professional sign-off before a high-risk package can return CLEAN publication readiness.
- Bind high-risk professional approval to a deterministic SHA-256 fingerprint of the reviewed Skill body.

All notable user-visible changes are recorded here.

## [Unreleased]

### Fixed

- Made the Lucas-DeepWheel family publication audit independent of Quality Gate-specific CLI, validator, release-template, and test filenames; documented that third-party Skills may need a tailored baseline.

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
