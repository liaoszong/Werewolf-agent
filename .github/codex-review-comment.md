# Codex 审查评论模板

## 默认模板

```text
@codex review
```

> 仅完整的发送上述内容
> 如果有前一轮的行内审查,并且你已经完成了修复,逐个给上一轮的行内 review comment 发送 reply。

## 使用规则

- 满足模板要求时可直接发送，无需先展示给用户并取得批准。
- 审查评论不能带有```text --- IGNORE ---```标签。
- 已修复上一轮行内审查意见时，必须回复对应 inline PR review comment。
- 不要用普通 PR 顶层评论代替行内审查回复。

## Review Packet Gate v1

For Implementation PRs, start with `.logs/review/latest/review-packet.md` when available.

A档 review output must use one verdict:

- `PASS`
- `BLOCK`
- `NEED_DEEP_REVIEW`

A档 should not perform repository-wide context discovery by default. If evidence is insufficient, output `Minimal Next Reads` with explicit file paths and line ranges.
