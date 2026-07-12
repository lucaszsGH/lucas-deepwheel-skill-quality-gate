# Changelog

## [0.1.0-rc.6] - 2026-07-12

- Ignore the installer's `.installed-version` metadata when comparing source and installed Skill bodies.
- Add a regression test proving an otherwise identical installation remains `MATCH` when the version marker is present.
- Allow an internal-only public-surface review to record `NO_CHANGE_REQUIRED` without claiming that bilingual images changed.
- **Naming-convention check**: set `SKILL_QUALITY_GATE_NAME_PREFIX` (e.g. `lucas-deepwheel-`) to verify a target Skill's `name` starts with it (WARNING if not); when unset, a NOTE reminds to establish one unified naming rule. "Verify my own rule when I run it; remind others to set a unified rule."
- **Skill-type awareness**: read `skill_type` (`tool` / `domain` / `meta`) from the target's `agents/risk-profile.json`; for `domain` Skills the tool-only policy checks (new-user OCR/audio preflight, token budget, companion routing, independent entry) are downgraded from WARNING to NOTE, so self-contained domain Skills aren't dragged to CONCERNS by inapplicable checks.
- **Semantic section detection**: `CORE_GROUPS` now accepts synonyms (标准流程≈生成流程, 完成前验收≈交付前自检, 什么时候不用≈什么时候不要使用, + English aliases), so compliant Skills that phrase sections differently no longer trigger false "missing core section" warnings.

## [0.1.0-rc.5] - 2026-07-12

- Accept double-quoted, single-quoted, folded, literal and unquoted YAML description scalars without false frontmatter failures.
- Ignore indented block-scalar continuation lines when validating top-level frontmatter keys.
- Add read-only reconciliation across the unique source, local branch, GitHub main/PR, Actions, VERSION/Tag/Release and installed Skill.
- Report MATCH, DRIFT, NOT PUSHED, PR OPEN, ACTIONS PENDING/FAILED and INSTALL OUTDATED without mutating Git or GitHub state.
- Bind the exact packaged-Skill fingerprint to reviewed README, bilingual editable/rendered introduction assets, examples, installation guidance and Changelog.
- Return `VISUAL ASSET STALE` when public-surface review evidence is missing, malformed or stale.
- Keep repair responsibility outside the gate: AI may update public assets only after Lucas confirms, then the gate revalidates the new exact state.
- Refresh the bilingual Hero and Workflow SVG/PNG introduction assets to explain synchronization and public-surface freshness.
- Treat existing publication packages without a public-surface review manifest as `VISUAL ASSET STALE` until they complete a one-time evidence backfill.

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
