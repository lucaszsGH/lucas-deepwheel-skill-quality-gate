# Quality Gate 优化待办（边跑边记，最后统一修）

> 用本闸审各家 Skill 时发现的、值得改进闸本身的点。逐条记录，Lucas 择时统一修改。
> 约定：已修的移到底部「已修」并注提交号;新发现追加到「待修」。

## 待修

### ✅ O5 已修（2026-07-13,rc.8）· 自动测试并入 O6
- references-nested 与 interaction-and-onboarding 关键词策略对 `skill_type=domain` 降 WARNING→NOTE(tool/meta/未声明仍 WARNING);skill_type 读取提前到 references 检查前。brand-apply 实证转 **CLEAN**、72 测试无回归。**自动测试待补**(domain 降 NOTE / tool 保持 WARNING 两态),并入 O6。

### ✅ O6 已修（2026-07-13,1.0.0）· 12 个自动测试
- 补 12 测：命名前缀设/未设两态 · skill_type=domain 工具类 5 项(含 interaction onboarding)降 NOTE · O5 references-nested / onboarding 对 domain 降 NOTE、tool 保持 WARNING · CORE_GROUPS 同义词零误报。给 `run_gate` 加 `env=` 参数。O5 的自动测试也含在内。

### ✅ O7 已修（2026-07-13,1.0.0）· description/README 补命名检查
- SKILL.md frontmatter `description` 加 naming-convention / 命名规则;README.md + README.zh-CN.md 各补一行命名规则检查(对照 `SKILL_QUALITY_GATE_NAME_PREFIX`)。manifest 按 `internal_only/NO_CHANGE_REQUIRED` 签(公开面文字补充、介绍图不改)。

### ✅ O8 已理（2026-07-13,1.0.0）· CHANGELOG 版本归属
- 判定：命名/skill_type/同义 3 条随 rc.6 批次(a0782da)同批推送,CHANGELOG 归 rc.6 成立、不强移;1.0.0 为首个正式版,收敛 rc.1–rc.8 全部能力,历史段保持。

## 已修

### F1 · description 只认双引号单行 → 折叠/字面/单引号/无引号误判 BLOCK（已修 b210906，2026-07-12）
- 加 `_extract_scalar` 兼容五种 YAML 标量;顶层键检查忽略缩进续行。24 测试全过。

### F2 · O1 章节检测太关键词化,误伤合规域 Skill（已修，2026-07-13）
- `CORE_GROUPS` 每组补语义同义词:标准流程≈生成流程/工作流程/how it works;完成前验收≈交付前自检/自检清单/pre-flight;什么时候不用≈什么时候不要使用;+英文别名。合规域 Skill 用不同措辞不再误报。

### F3 · O2 不区分工具/域 Skill,强套工具类检查（已修，2026-07-13）
- 新增 `TOOL_ONLY_POLICY`(OCR体检/token/companion/独立入口)+ 读 risk-profile 的 `skill_type`;`skill_type=domain` 时这四项由 WARNING 降为 NOTE。自包含域 Skill 不再被工具类检查拖成 CONCERNS。

### F4 · ③ 新增命名规则检查（已修，2026-07-13）
- 环境变量 `SKILL_QUALITY_GATE_NAME_PREFIX`:配了→核验目标 Skill name 是否遵此前缀(不遵=WARNING);没配→提醒「建立统一命名规则」(NOTE)。即「我用核验我的规则(设 lucas-deepwheel-)、别人用提醒建统一规则」。
- 手动验:设 `lucas-deepwheel-` 审 lucas-deepwheel-brand-apply=过、审自己=CLEAN;未设=出提醒 NOTE。
