# Quality Gate 优化待办（边跑边记，最后统一修）

> 用本闸审各家 Skill 时发现的、值得改进闸本身的点。逐条记录，Lucas 择时统一修改。
> 约定：已修的移到底部「已修」并注提交号;新发现追加到「待修」。

## 待修

### O1 · 章节检测太关键词化，误伤合规域 Skill（P1，影响判准）
- **现象**：`check_core_sections` 找精确标题「标准流程 / 完成前验收 / 什么时候不要使用」等;域 Skill 合理地叫「生成流程 / 交付前自检 / 什么时候不用」就被报 WARNING。审 `deepwheel-brand`(自包含、合规)时误报多条。
- **改法建议**：章节检测认**语义等价集**（如 标准流程≈生成流程≈工作流程；完成前验收≈交付前自检≈自检清单；什么时候不用≈什么时候不要使用≈不适用）;或从关键词匹配升级为"是否存在‘流程类/自检类/边界类’段落"的意图判断。
- **发现**：2026-07-12 审 deepwheel-brand。

### O2 · 不区分「工具 Skill」与「域 Skill」，强套工具类检查（P1，影响判准）
- **现象**：对自包含品牌应用 Skill 也检查 OCR/音频/安装体检、token 分段策略、companion Skill 路由——这些对不涉文件处理/无外部工具依赖的域 Skill 本就 N/A,却报 WARNING。
- **改法建议**：读目标 Skill 的 `agents/risk-profile.json` 的 `domains` / 新增一个 `skill_type`(tool / domain / meta) 字段判类型;**工具类才查 OCR/token/companion，域类跳过或降为 NOTE**。缺 risk-profile 时保守按现状全查。
- **发现**：2026-07-12 审 deepwheel-brand（9 条 WARNING 里约 5 条属此类）。

### O3 · description 长度/边界检查可再宽容折叠换行（P2，观察）
- 折叠解析已修（见已修 F1）。后续可留意：超长折叠描述折叠成单行后可能逼近 1024 上限的边界情形，必要时给出更精确的"折叠后长度"提示。

## 已修

### F1 · description 只认双引号单行 → 折叠/字面/单引号/无引号误判 BLOCK（已修 b210906，2026-07-12）
- `parse_frontmatter` 原正则 `^description:\s*"(.*)"` 只认双引号单行;折叠 `description: >`(skill-creator 示例常用)被读成空 → "description length is invalid" 假 BLOCK。
- 改：加 `_extract_scalar` 兼容 双/单引号、折叠(>)、字面(|)、无引号;顶层键检查忽略缩进续行。24 测试全过、闸自审仍 CLEAN。
