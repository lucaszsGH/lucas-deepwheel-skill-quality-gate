# Token / 额度高敏感策略

## 默认原则

```text
先低消耗，后高消耗
先保存，后理解
先文本，后 OCR
先转录，后总结
先抽样，后全量
高消耗前确认
```

## 建议字段

```text
token_sensitivity: low / normal / high
processing_budget: quick / standard / deep
```

## 高消耗动作

- 长 PDF 全文总结；
- 多图逐图 OCR；
- 复现级页面规格；
- 长视频转录后深度总结；
- 批量素材整理；
- HTML/PPT/PDF/image2 生产级输出。

## 降级路线

```text
只保存来源和摘要
只做前 1-3 页样张
只提取文本不 OCR
只转录不总结
分段处理
待用户确认后继续
```
