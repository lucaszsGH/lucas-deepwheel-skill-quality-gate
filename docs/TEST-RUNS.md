# Test Runs

## 2026-07-12 · rc.4 high-risk behavior regression candidate

- Version target: 0.1.0-rc.4; no Tag or Release created.
- High-risk behavior contract declaration: covered by positive and negative tests.
- Publication test-file existence and declared case markers: covered by negative tests.
- Untrusted target code execution: intentionally disabled; target CI remains responsible.
- Gene Nutrition rc.4 cross-check: expected to retain only the pending professional sign-off and incomplete publication-checklist CONCERNS.

## 2026-07-11 pre-fix baseline

- Draft and installed copies: MATCH, 11 files.
- Direct executable entrypoint: failed because a stray byte appeared before the shebang.
- Missing target: displayed BLOCK but returned exit code 0.
- Same-named scanner file: excluded from scanning.
- Local-path rule: maintainer-specific.
- Explicitly requested missing publication directory: not blocking.
- Behavior tests: absent.

## 2026-07-11 local source candidate

Result: PASS.

- Version validation: PASS for 0.1.0-rc.1.
- Generic publication-package validation: PASS.
- Quality Gate-specific validation: PASS.
- Product self-audit with publication package: CLEAN.
- Behavior tests: 9 / 9 PASS.
- Direct executable and Python entrypoints: PASS.
- Exit semantics:
  - CLEAN returned 0;
  - CONCERNS returned 1;
  - BLOCK returned 2.
- Missing Skill and missing requested publication package: BLOCK with exit 2.
- Same-filename scanner bypass regression: PASS; the synthetic finding was detected.
- Generic local-home-path detection: PASS without echoing the value.
- Human-readable and JSON output redaction: PASS.
- Safe installer:
  - default invocation stayed a dry run;
  - existing installation was refused without the confirmation-specific option;
  - temporary fresh install completed and matched the repository Skill body.
- Original draft and installed copies: unchanged.
- Installed copy replacement, GitHub repository, remote, push, Tag, and Release: not performed.

## 2026-07-12 · high-risk domain gate

- Version metadata: PASS for 0.1.0-rc.2
- Generic and product-specific validators: PASS
- Behavior tests: 20 PASS
- Self-audit: CLEAN
- High-risk Skill without risk profile: BLOCK
- High-risk Skill missing entrypoint boundary: BLOCK
- High-risk signal located only in references: BLOCK
- English substring false-positive cases: CLEAN
- Gene Nutrition structural and high-risk controls: PASS; publication readiness remains CONCERNS until its final human sign-off is recorded
- Clean local branch clone: PASS
- Missing bilingual introduction image: CONCERNS
- Numeric high-risk guidance without a machine contract: BLOCK
- Non-executable numeric safety contract: BLOCK
- Incomplete publication checklist: CONCERNS
- Missing or pending high-risk professional sign-off: CONCERNS; explicit APPROVED sign-off: CLEAN
- Approved sign-off with a stale or mismatched Skill fingerprint: CONCERNS

## 2026-07-12 · unreviewed numeric-publication hard gate

- Version metadata: PASS for 0.1.0-rc.3
- Generic and product-specific validators: PASS
- Behavior tests: 20 PASS
- Self-audit with publication package: CLEAN
- High-risk personalized numeric publication with missing or pending sign-off: BLOCK
- High-risk personalized numeric publication with stale approved fingerprint: BLOCK
- Explicitly education-only, personalized-numeric-disabled high-risk candidate with pending sign-off: CONCERNS
- Gene Nutrition 0.1.0-rc.2 local candidate: CONCERNS with exactly two expected open items and no critical findings
- Gene Nutrition numeric draft fixture: refused while unreviewed
- Current Quality Gate changes: local source only; not committed or pushed
