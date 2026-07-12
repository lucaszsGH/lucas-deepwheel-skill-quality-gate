# Quality Gate 优化待办（边跑边记，最后统一修）

> 用本闸审各家 Skill 时发现的、值得改进闸本身的点。逐条记录，Lucas 择时统一修改。
> 约定：已修的移到底部「已修」并注提交号;新发现追加到「待修」。

## 待修

### O5 · references「一层深」规则对大型域 Skill 太严（P2，判准）
- **现象**：`check_skill` 对 `references/` 下有子目录即报 WARNING「references are nested」。但完整规范型 Skill（如 lucas-deepwheel-brand-apply 内嵌手册 18 模块 + 图鉴 37 型 = 55 文件）必须按 `规范全集/`、`图形规格/型名/` 分层组织,拍平不可行。
- **改法建议**：允许一个「白名单子目录」层（如 references 下的分组目录不算违规），或从 risk-profile 读 `bundled_spec: true` 时豁免嵌套检查。
- **发现**：2026-07-13 审 lucas-deepwheel-brand-apply。

### O6 · 新检查(命名/skill_type/同义章节)缺自动测试（P1，工程质量）
- F2/F3/F4 三项新行为(见已修)当前靠手动验 + 24 原测试兜底,未加专门单测。
- **改法建议**：给 tests/ 补：①命名前缀设/未设两态 ②domain skill 工具类检查降 NOTE ③CORE_GROUPS 同义词识别。命名测试需给 `run_gate` 加 `env=` 参数支持。

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
