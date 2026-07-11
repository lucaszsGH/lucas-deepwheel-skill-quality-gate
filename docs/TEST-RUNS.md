# Test Runs

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
