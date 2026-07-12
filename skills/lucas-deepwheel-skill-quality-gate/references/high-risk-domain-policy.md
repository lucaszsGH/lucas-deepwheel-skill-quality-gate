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
- refusal_rules_required true.

The Skill entrypoint must also expose safety boundary, consent, source provenance, stop conditions and review routing. A disclaimer alone is insufficient.

## Gate behavior

A high-risk entrypoint without the profile is BLOCK. An under-classified or disabled control is BLOCK. Product-specific validators remain responsible for domain logic such as dose tiers, medication boundaries or legal-jurisdiction rules.

The machine gate proves declaration and entrypoint control presence, not clinical, legal or financial correctness. Expert and behavioral review remains mandatory.

## Numeric intervention contract

If a high-risk Skill promises dose, supplement amount, intake amount or upper-limit comparison, its risk profile must enable numeric_safety_contract_required and point numeric_contract_path to a real, non-symlink file inside the Skill. Missing declarations or files return BLOCK. The product-specific validator must still prove unit normalization, source metadata, upper-limit comparison and negative behavior.

## Public-release sign-off

A high-risk publication package must include `docs/PROFESSIONAL-SIGNOFF.md`. Only an explicit `Status: APPROVED` may satisfy this gate. Missing or pending sign-off returns CONCERNS; structural checks and machine tests cannot self-approve a high-risk public release.
