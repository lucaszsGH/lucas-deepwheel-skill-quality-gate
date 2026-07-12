# GitHub 发布能力检查

## 必备

```text
README.md
README.zh-CN.md
LICENSE
SECURITY.md
CONTRIBUTING.md
CHANGELOG.md
docs/INSTALLATION.md
docs/TEST-RUNS.md
docs/REVIEW-RECORD.md
examples/example-prompts.md
.github/workflows/validate.yml
Issue / PR 模板
```

## 高星加分

```text
一句话价值
Quick Start
示例输出
能力矩阵
Optional tools
Troubleshooting
Roadmap
视觉介绍图或截图
```

## Bilingual GitHub introduction

Lucas-DeepWheel publication packages require editable and rendered English and Chinese hero and workflow assets under assets/intro. English and Chinese READMEs must route to their matching PNG pair. Missing language assets return CONCERNS and prevent CLEAN publication readiness.

File presence is not semantic freshness. After the packaged Skill changes, `docs/PUBLIC-SURFACE-REVIEW.json` must bind the current Skill fingerprint to the reviewed README, bilingual SVG/PNG assets, examples, installation guidance and Changelog. A missing or stale decision returns `VISUAL ASSET STALE`.

User-visible changes require updated English and Chinese editable/rendered assets. Internal-only changes may record `NO_CHANGE_REQUIRED` with a concrete reason. Quality Gate does not perform the repair; AI may edit the public surfaces only after Lucas confirms.

## Post-change state reconciliation

Before saying an updated Skill is usable or published, run the read-only release-state reconciler. Confirm the unique source, local branch, GitHub main or PR, Actions for the exact HEAD, VERSION/Tag/Release and installed snapshot. `NOT PUSHED`, `PR OPEN`, `ACTIONS FAILED`, `INSTALL OUTDATED` or other DRIFT states must remain visible until separately repaired and rechecked.

## Completion evidence

The publication checklist is an executable release boundary, not decorative documentation. Any unchecked `- [ ]` item returns CONCERNS and prevents CLEAN. Applicable specialist, privacy, accessibility and visual sign-off must be recorded in `docs/REVIEW-RECORD.md`; a machine gate must not silently substitute for qualified human review.
