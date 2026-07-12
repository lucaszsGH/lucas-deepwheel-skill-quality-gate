# High-risk domain policy

## Purpose

Public Skills that influence health, genetics, nutrition, legal, financial, investment or tax decisions require a machine-readable risk declaration.

## File

Place agents/risk-profile.json inside the Skill bundle.

Required fields for risk_level high:

- schema_version equal to 1;
- non-empty domains;
- declared sensitive_data classes;
- consent_required true;
- human_review_required true;
- source_provenance_required true;
- refusal_rules_required true;
- behavioral_safety_contract_required true;
- a safe, executable behavioral_safety_contract_path inside the Skill;
- a publication-relative behavioral_test_path;
- behavioral_case_ids covering consent missing, data-subject uncertainty, minimum-input failure, incomplete safety preflight, stop conditions, blocked-output suppression and invalid source provenance.

If the Skill contains personalized numeric guidance, declare `personalized_numeric_guidance_enabled` explicitly. An unreviewed education-only candidate sets it to false and declares a non-empty `unreviewed_output_policy`; missing the flag is treated conservatively as potentially enabled when numeric capability signals are present.

The Skill entrypoint must also expose safety boundary, consent, source provenance, stop conditions and review routing. A disclaimer alone is insufficient.

## Gate behavior

A high-risk entrypoint without the profile is BLOCK. An under-classified or disabled control is BLOCK. Product-specific validators remain responsible for domain logic such as dose tiers, medication boundaries or legal-jurisdiction rules.

The machine gate proves declaration, entrypoint control presence and the existence of named negative behavior regressions; it does not prove clinical, legal or financial correctness. It never executes untrusted target code. Product CI and expert review remain mandatory.

## Behavioral intervention contract

Every high-risk Skill must declare an executable behavioral safety contract inside the Skill bundle. When a publication package is supplied, the gate also requires the declared behavior-test file and verifies that each declared case identifier appears in that file.

The mandatory baseline identifiers are:

- `consent_missing`;
- `data_subject_unconfirmed`;
- `minimum_input_missing`;
- `safety_preflight_incomplete`;
- `stop_condition`;
- `blocked_output_suppression`;
- `source_provenance_invalid`.

These identifiers are coverage evidence, not self-certification. The target repository's CI must execute the tests; Quality Gate intentionally performs static inspection rather than running code from an untrusted package.

## Numeric intervention contract

If a high-risk Skill promises dose, supplement amount, intake amount or upper-limit comparison, its risk profile must enable numeric_safety_contract_required and point numeric_contract_path to a real, non-symlink file inside the Skill. Missing declarations or files return BLOCK. The product-specific validator must still prove unit normalization, source metadata, upper-limit comparison and negative behavior.

## Public-release sign-off

A high-risk publication package must include `docs/PROFESSIONAL-SIGNOFF.md`. Only an explicit `Status: APPROVED` plus a `Target Skill SHA256` matching the current packaged Skill may satisfy this gate. Compute the deterministic fingerprint with `--print-skill-sha256`.

For a high-risk package with personalized numeric guidance enabled—or with numeric capability signals but no explicit false enablement flag—missing, pending, malformed or stale sign-off returns BLOCK. A clearly declared education-only candidate with personalized numeric guidance disabled remains CONCERNS until professional sign-off. A disclaimer alone never unlocks numeric publication; structural checks and machine tests cannot self-approve a high-risk public release.
