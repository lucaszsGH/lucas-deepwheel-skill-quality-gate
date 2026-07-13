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
- **状态**：✅ 已完成并上线（2026-07-13,`db913f7`,VERSION `0.1.0-rc.7`）。见下方完成记录。

## ✅ 完成记录

### 2026-07-13 · Claude（张帅）· 门禁 rc.7 已上线（此认领结清）
认领的门禁增强全部完成并推送,实际交付比原认领更多:
- token 量级估算 + 上手/引导硬核验（4 检查 + `payload.token_layers` 量级表,表绝不走 finding）
- **角色感知 `--audience public|private`**：切换审计**视角**（对外第三方 vs 作者自用），**非松紧**（Lucas 明确"对外/自用只是审计视角,不是严格宽松"）;public 对 `FACADE_LIFT_SET` 做 note→warning（LIFT=A Lucas 拍）、private 把 facade 整组 SUPPRESS+汇总 NOTE、private+publication=publishing strict
- **全程助手 `--stage start|final`**：start=脚手架清单（exit 0,verdict DRAFTING）,final=严格审计（默认）
- **价值增项 `--report`**：markdown 体检卡（含诚实声明+指纹）+ `payload.remediation_plan` 修复优先级
- 双语 Hero/Workflow 介绍图从「Skill 作者收益」视角重做并重渲（8 个 SVG+PNG）
- `docs/PUBLIC-SURFACE-REVIEW.json` 已按 **user_visible / UPDATED** 签、列 8 张双语图、两个指纹重算
- **74 测试全绿**,自审（含 `--publication-dir`）CLEAN
**与 Codex 的 public-surface 闸无残留冲突**（manifest 已正确签 UPDATED）。

### 2026-07-13 · Claude（张帅）· rc.8（O5 修复,追加）
references-nested / interaction-and-onboarding 关键词策略对 `skill_type=domain` 降 WARNING→NOTE(tool/meta/未声明仍 WARNING),让大型自包含域 Skill(如 brand-apply)不被结构规则拖成 CONCERNS(brand-apply 已转 CLEAN)。manifest 按 `internal_only/NO_CHANGE_REQUIRED` 签(O5 是内部检查精化、介绍图无需改)。门禁现处 **rc.8**。Codex 后续改动照常在本文件登记范围。

## 约定
- 改共享文件前先在本文件登记认领 + 范围。
- `docs/PUBLIC-SURFACE-REVIEW.json` 与 public-surface 机制，由**当前改动方**负责同步更新指纹并复核。
- 撞车时以 Lucas 拍板为准。
