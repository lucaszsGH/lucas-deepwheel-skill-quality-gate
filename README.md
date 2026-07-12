# Lucas-DeepWheel Skill Quality Gate

**English** | [简体中文](README.zh-CN.md)

Status: public release candidate; current version 0.1.0-rc.5.

![DeepWheel Skill Quality Gate: gate with evidence and release with confidence](assets/intro/quality-gate-hero-en.png)

## What it does

Skill Quality Gate audits an Agent Skill and, optionally, its publication package before installation or release.

The default publication-file baseline is designed for Lucas-DeepWheel family repositories. Third-party Skills may need a tailored baseline instead of treating family-specific file omissions as release blockers.

It checks:

- structure and frontmatter;
- capability claims and adjacent-task boundaries;
- independent product entry and companion-Skill routing;
- new-user capability preflight;
- token and interaction policies;
- common credential shapes, local paths, PII, and raw residue;
- GitHub publication readiness;
- read-only reconciliation across local source, GitHub main/PR, Actions, VERSION/Tag/Release, and the installed Skill;
- whether README, bilingual editable/rendered introduction assets, examples, and installation guidance still match the current capability;
- whether machine findings can correctly block CI.

It does not execute the target Skill's business actions and does not replace real behavior tests or human review.

![Skill Quality Gate workflow from a Skill package to an evidence-backed verdict](assets/intro/quality-gate-workflow-en.png)

## Quick Start

Audit a Skill folder:

```bash
python3 skills/lucas-deepwheel-skill-quality-gate/scripts/skill_quality_gate.py /path/to/target-skill
```

Audit both the Skill and its publication package:

```bash
python3 skills/lucas-deepwheel-skill-quality-gate/scripts/skill_quality_gate.py /path/to/target-skill --publication-dir /path/to/publication-package
```

Reconcile the repository, live GitHub state, Actions, release metadata, and installed snapshot without changing them:

```bash
python3 skills/lucas-deepwheel-skill-quality-gate/scripts/reconcile_release_state.py /path/to/repository --json
```

For a high-risk professional sign-off, print the deterministic packaged-Skill fingerprint and record it beside `Status: APPROVED`:

```bash
python3 skills/lucas-deepwheel-skill-quality-gate/scripts/skill_quality_gate.py /path/to/target-skill --print-skill-sha256
```

Exit codes are stable for automation:

- `0`: CLEAN;
- `1`: CONCERNS;
- `2`: BLOCK or invalid requested path.

The report names the risk category and relative file only. It does not echo matched credentials or machine-specific absolute paths.

## Capability boundary

### Supported

- Static Skill and publication-package audit.
- Read-only post-change GitHub and installed-copy reconciliation.
- Capability-fingerprint binding for README, bilingual SVG/PNG introductions, examples, installation guidance, and Changelog.
- `VISUAL ASSET STALE` when public explanations were not reviewed after the Skill changed.
- Safe JSON or human-readable output.
- CI-blocking exit semantics.
- Seven-role review guidance and P0/P1/P2 repair planning.

### Requires tools or human review

- Real behavior smoke tests.
- HTML, PPT, PDF, OCR, video, audio, or image-generation tests.
- Copyright, customer privacy, supply-chain, and release decisions.
- Cross-platform installation and rollback tests.

### Not promised

- Complete secret or PII detection.
- Proof that all business capabilities work.
- Automatic repair, README/image generation, installation, publishing, push, Tag, or Release.
- Replacement for a security review.

## Installation

Preview the safe local installation from the repository root:

```bash
python3 scripts/install-local.py
```

The default invocation is a dry run. It does not create or replace files. Read [docs/INSTALLATION.md](docs/INSTALLATION.md) before any `--apply` action.

## Validation

```bash
python3 scripts/validate-version.py
python3 scripts/validate-lucas-deepwheel-skill.py skills/lucas-deepwheel-skill-quality-gate .
python3 scripts/validate-lucas-deepwheel-quality-gate.py skills/lucas-deepwheel-skill-quality-gate .
python3 -m unittest discover -s tests -p 'test_skill_quality_gate.py' -v
```

## Security

See [SECURITY.md](SECURITY.md). Never place credentials, private customer material, complete sensitive logs, or real protected assets in examples, tests, issues, or reports.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes to scanner behavior must include positive and negative tests.

## License

MIT License. See [LICENSE](LICENSE).

## High-risk domain gate

A Skill whose entrypoint covers health, medical, genetic, nutrition, legal or financial decisions must provide agents/risk-profile.json. Missing or under-classified consent, human-review, provenance or refusal controls returns BLOCK.

The machine gate verifies declared fields and the presence of entrypoint controls; it does not prove that domain logic is correct. High-risk Skills still require expert and behavioral review.

Every high-risk package must also declare an executable behavioral safety contract and a publication test file covering consent, data-subject confirmation, minimum input, safety preflight, stop routing, blocked-output suppression and source provenance. The gate checks this evidence statically and leaves test execution to the target repository's CI.

For a high-risk publication that enables personalized numeric guidance, a missing, pending or stale professional sign-off returns BLOCK. An explicitly education-only candidate with personalized numeric guidance disabled remains CONCERNS until sign-off. A disclaimer does not unlock numeric guidance.
