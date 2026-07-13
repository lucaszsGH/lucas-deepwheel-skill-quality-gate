# 审计视角与阶段策略（audience 视角 + stage 阶段）

本文件说明门禁的两条正交轴：`--audience`（视角/尺子）与 `--stage`（阶段），以及
`--report`（体检卡）。核心原则：**audience 是换视角、换审计关注点，不是同一把尺子调松紧。**

## 两把尺子（视角，不是松紧）

- **对外 public**：以「不认识作者的陌生第三方使用者」为尺子。审的是第三方门面/体验维度——
  介绍有没有讲清价值、陌生人能不能上手、双语与门面是否完整、GitHub 可用性齐不齐。
- **自用 private**：以「作者本人」为尺子。审结构清晰、功能满足作者用途、作者在意的正确性
  与安全。明确不审「吸引陌生人」这个维度——自己用不需要对外门面。
- **未声明 default（audience 未给）**：不启用任何视角逻辑，findings、判定、退出码与不带
  audience 时逐字一致；门面按类型自然严重度出现，既不提为主线、也不移出范围。只在
  `payload.audience` 加一个键、并追加一行中性视角页脚。default 已经审门面，页脚绝不说
  「不含门面」。

## 为什么是视角、不是松紧

1. **机制不对称**：public 把门面「纳入审计」并解除 facade 上的类型软化；private 把门面
   「移出审计」并追加一条汇总 NOTE。移出 ≠ 降级，二者不是镜像。private 从不把 warning
   变成 note。
2. **作用面只有门面（FACADE_SET 九项）**：`onboarding.first_success` 与八个 `pub.*`。
   通用/结构/安全/描述/critical 在三视角下逐字一致，audience 一律不碰。
3. **`large_no_progressive` / `heavy_file` / `entry_heavy` 归通用/结构轴**：它们是 token 经济
   与结构清晰，作者自用也在意自己的上下文预算，不是给陌生人看的门面，所以刻意不入
   FACADE_SET，只受 skill_type 影响、audience 不碰。
4. **public 的 note→warning 不是超基线加档**：它只对 `onboarding.first_success` 与
   `pub.usability_term` 两项（FACADE_LIFT_SET），是「解除按类型的私用软化、还原门面固有
   severity」——陌生第三方无论 skill_type 都要能上手，那条软化在对外视角不适用。绝不碰
   critical、绝不产生 info。

## private ≠ 放水（四重保证）

- 通用/安全/正确性/critical/描述在 private 下全强度照审，作者在意的一项不降。
- 门面维度不是降低标准，而是「移出范围并显式声明」：汇总 NOTE 白纸黑字列出未审项与如何
  开启，是透明的 out-of-scope。汇总 NOTE 区分「已移出范围」（上手路径）与「需
  `--publication-dir` 才审、本次未评估」（README 介绍/双语资产/安全安装入口/GitHub 可用性/
  门面指纹），不谎称关掉了九项检查。
- **发布态焊死放水口**：private 一旦带上 `--publication-dir`（正在发布 = 陌生人将看到），
  effective 折叠为 public（publishing=strict）：门面按对外审、不移出、生成星标加分 NOTE，
  另加一条 `audience.private_publishing_conflict` NOTE。
- 移出只在显式 `--audience private` 时发生，default 永不移出——没有任何存量 Skill 会被默默
  放行。

## effective_public 单一真源

`effective_public = (audience == public) 或 (audience == private 且给了 --publication-dir)`。
门禁在一处集中算一次，同时喂给 `check_publication`（门控星标加分 NOTE）与视角后处理
（门面 LIFT / 移出），避免「生成了星标却没抬档」这类两处各算各的偏差。

## stage：设计初期引导 vs 最终审计

- `--stage final`（默认）：今天的行为；CI 与发布前只认 final。
- `--stage start`：引导模式。恒退出码 0、判定 `DRAFTING`（绝不复用 CLEAN），打印「好 Skill
  要件全景」目标态清单，安全/高风险 critical 置顶强提示但不拦。start 绝不删除或改动任何
  finding，只在脚手架里重分组：默认（含 public）把对外发布门面列在主线；只有
  `--audience private` 才把它折叠进「以后开源再看」并仍然列出，不默认隐藏 GitHub 引导。
- 退出码 0 现同时含 CLEAN 与 DRAFTING；DRAFTING 只出现在 `--stage start`。硬防线是
  default = final。

## --report：体检卡

`--report` 输出 markdown 体检卡（与 `--json` 互斥）。按 `references/validation-report-template.md`
骨架分组，带 verdict→建议映射、L1–L4 等级段标「未完成·需人工」、以及目标 Skill 的
tree_sha256 指纹。体检卡带诚实声明：**本卡为静态机器扫描，按公开门面清单静态核验，非生产
质量认证，不含 7 角色人工评审与真实业务行为测试；唯有读者自己对当前 Skill 重跑门禁方可
采信。** `--report` 不是 CI 信号，CI 只认退出码。

## 诚实边界

所有输出（横幅、NOTE、体检卡、findings）只说「按公开门面清单静态核验」，绝不写「模拟陌生
用户首次上手」这类静态正则做不到的承诺；也绝不用「从严/放宽/更严/更松」这类松紧词，一律
用视角/尺子/审哪些/范围/移出/纳入来表达。
