---
name: lucas-deepwheel-skill-quality-gate
description: "Use when evaluating, testing, red-teaming, preparing, or publishing an Agent Skill. Checks structure, safety, capability claims, independent product entry, companion-Skill routing, new-user readiness, optional tool setup, token cost, interaction quality, GitHub publishability, and reuse potential. Use for Skills 质量门禁, GitHub 发布前检查, 独立产品入口检查, 关联 Skill 主动提醒, 新用户能力体检, Token 成本评估, 交互体验评估, 红蓝对抗, 安全审计. Do not use to execute the target Skill's risky actions or replace real behavior tests."
---

# Lucas-DeepWheel Skill Quality Gate｜Skills 质量门禁

定位：独立检查一个 Agent Skill 是否达到“本地可用、用户可懂、安全可信、低消耗、可安装、GitHub 可发布、具备持续复用价值”。

## 目标

对目标 Skill 或发布包进行：

```text
结构检查
能力声明检查
新用户能力体检检查
独立产品入口检查
关联 Skill 主动提醒检查
Token / 额度消耗检查
交互与失败恢复检查
安全隐私检查
GitHub 发布准备检查
多角色红蓝对抗
修复包建议
```

## 什么时候使用

- 准备创建、升级或安装一个 Skill；
- 准备进入 GitHub 私有联调或公开发布前；
- Skill 功能变重、边界不清、用户看不懂时；
- 需要检查独立入口、关联 Skill 路由或新用户能力体检时；
- 需要做红蓝对抗、安全审计或多角色评审时；
- 需要检查是否过度承诺、缺安装引导或消耗过高时。

用户可以直接提供 Skill 文件夹或发布包路径，不需要先使用其他 Skill。

## 什么时候不要使用

- 不用于直接执行目标 Skill 的业务动作；
- 不替代真实任务 smoke test、截图 QA、导出 QA 或目标客户端复核；
- 不自动安装、删除、覆盖、发送、公开发布、commit、push、Tag 或 Release；
- 不读取、保存或输出敏感凭证、匹配到的敏感原文和完整敏感日志；
- 不把“一次机器扫描通过”当作已经具备生产质量。

## 能力声明

### 已支持

- 检查 Skill 入口、frontmatter、references、agent metadata 和核心章节；
- 检查能力声明、新用户能力体检、Token 策略、独立入口、关联 Skill 路由与交互恢复；
- 检查发布包常用文件、安装入口、CI 和示例；
- 检测凭证形状、本机绝对路径、常见个人信息和原始调试残留；
- 输出 CLEAN / CONCERNS / BLOCK，并用退出码支持 CI。

### 需要工具或人工复核

- 真实业务行为测试；
- HTML、PPT、PDF、OCR、视频、音频和 image2 能力实测；
- GitHub Actions、安装、升级、回滚和跨平台验证；
- 版权、客户隐私、供应链和对外发布判断；
- 固定 7 角色红蓝对抗的人工结论。

### 暂不承诺

- 不证明目标 Skill 的所有业务能力真实可用；
- 不保证扫描覆盖所有凭证、个人信息或供应链风险；
- 不自动修复目标 Skill；
- 不自动安装关联 Skill 或任何可选工具；
- 不代替 Lucas 或发布负责人的最终判断。

## 标准流程

1. 识别目标等级：本地草稿 / 安装候选 / GitHub 发布候选 / 高星目标版。
2. 读取 `references/quality-gate-framework.md`。
3. 检查目标 Skill 本体：`SKILL.md`、`references/`、`scripts/`、`agents/openai.yaml`。
4. 如提供发布包，检查 README、安装、测试、贡献、安全、CI 和示例。
5. 读取 `references/new-user-capability-preflight.md`，检查文件、OCR、PDF、视频、音频、安装、权限和降级路径。
6. 检查目标 Skill 是否有独立产品入口，不把关联 Skill 当成唯一前提。
7. 检查关联 Skill 能补齐什么、不安装如何降级、风险动作是否先确认。
8. 读取 `references/token-and-budget-policy.md`，默认低消耗、先抽样、分段处理。
9. 读取 `references/interaction-and-onboarding-policy.md`，检查首次成功、渐进披露、下一步和失败恢复。
10. 读取 `references/reviewer-role-matrix.md`，完成 7 角色红蓝对抗。
11. 如需要机器辅助，运行 `scripts/skill_quality_gate.py`。
12. 输出 P0 / P1 / P2 修复建议；未获确认不修改目标 Skill。
13. 发布包存在未勾选发布清单时，必须返回 CONCERNS；不得用结构检查或自动化测试替代尚未完成的人工签核。

## 机器门禁

当前发布包文件基线面向 Lucas-DeepWheel 家族仓库。审计第三方 Skill 时，应先确认或定制发布基线，不把 `README.zh-CN.md` 等家族文件缺失直接当作安全阻断。

从 Quality Gate Skill 目录运行：

```bash
python3 scripts/skill_quality_gate.py /path/to/target-skill
```

同时检查发布包：

```bash
python3 scripts/skill_quality_gate.py /path/to/target-skill --publication-dir /path/to/publication-package
```

退出码：

- `0`：CLEAN；
- `1`：CONCERNS；
- `2`：BLOCK 或目标路径无效。

扫描结果只报告类别和相对文件名，不输出匹配到的敏感值或目标机器的绝对路径。

## 输出标准

输出必须包含：

```text
总体结论
适用等级
已核实通过项
🔴 严重问题
🟡 警告问题
🔵 建议项
7 角色评审摘要
是否建议定稿 / 安装 / 发布
下一步最小修复包
```

每项都要区分：已核实 / 推断 / 待确认。

## 安全边界

不得读取、输出、保存或扩散 API Key、Token、Cookie、sessionKey、密码、私钥、验证码、一次性登录凭证、匹配到的敏感原文或完整敏感日志。

不得因为报告问题而输出客户文件正文、个人资料或可复用登录信息。删除、覆盖、安装、发送、公开发布、commit、push、Tag、Release 前必须确认。

如果发现敏感值，只报告风险类别、相对文件名和修复方向，不回显原值。

## 完成前验收

- 是否现场读取目标文件；
- 是否区分 Skill 本体、发布包和真实行为测试；
- 是否区分已核实、推断和待确认；
- 是否给出明确严重程度和可靠退出码；
- 是否包含新用户能力体检、独立入口、关联 Skill、Token 和交互恢复视角；
- 是否完成 7 角色人工评审，或明确说明尚未完成；
- 是否没有把机器 CLEAN 当作生产能力证明；
- 是否没有擅自修改、安装或发布目标 Skill；
- 是否没有泄露敏感值、绝对路径或完整敏感日志。

高风险领域规则见 `references/high-risk-domain-policy.md`。
