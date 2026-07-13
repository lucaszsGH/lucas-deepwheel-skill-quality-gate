# 并行协作认领（避免撞车）

> 本仓库由 Claude（提交身份 `张帅`）与 Codex（提交身份 `lucaszsGH`）并行开发。
> 2026-07-13 已因「公开面一致性闸」撞过一次车（rebase 冲突 + 一次红版本）。
> **改动共享文件前，请先在本文件认领并声明范围。**

## 🚧 在办认领

### 2026-07-13 · Claude（张帅）· 门禁两能力增强（Lucas D1=A）
- **目标**：围绕门禁两大目标——① skills 傻瓜式引导式体验、快速上手；② skills 具备 gh 高星标准。
- **两个新能力**：
  1. **token 量级估算**：扫目标 skill 各层文件，估算入口/典型/全量 token 量级并报告（轻量，D2=A）。
  2. **介绍/引导硬核验**：核验目标 skill 是否有图文介绍、首次成功引导、token 消耗提示。
- **将改的文件**：
  - `scripts/skill_quality_gate.py`（新增函数 + 集成到 check_skill / 报告）
  - `references/token-and-budget-policy.md`、`references/interaction-and-onboarding-policy.md`
  - `SKILL.md`（标准流程 + 能力声明 + 输出标准）
  - `tests/test_skill_quality_gate.py`（补新检查测试，兼清 backlog O6）
  - `CHANGELOG.md`
- **⚠️ 交叉高发区**：上述改动使 skill 指纹变化 = **user_visible**，将按 Codex 的 public-surface 机制更新
  `docs/PUBLIC-SURFACE-REVIEW.json`（可能需同步 README / description / 双语介绍图）。
  **Codex 若并行改公开面闸（`check_public_surface_review` / `reconcile_release_state.py` / 该 manifest），请先与本认领同步。**
- **状态**：进行中。

## 约定
- 改共享文件前先在本文件登记认领 + 范围。
- `docs/PUBLIC-SURFACE-REVIEW.json` 与 public-surface 机制，由**当前改动方**负责同步更新指纹并复核。
- 撞车时以 Lucas 拍板为准。
