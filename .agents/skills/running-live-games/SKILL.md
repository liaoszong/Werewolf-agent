---
name: running-live-games
description: Use when launching live DeepSeek games or ablation arms, when aggregate metrics look implausible, when most turns fall back to RNG, or when estimating cost/time before a live batch.
---

# 跑 live 对局与消融批次

## 先过用户门

live 批次花真钱。跑前向用户报预算再执行:45 局 × 80 请求上限 = 3600 上限,实测一批 ~1000 请求 / ~780k completion tokens / ~40 分钟(deepseek-v4-flash)。

## 命令

```bash
export DEEPSEEK_API_KEY=$(tr -d '\r\n' < .tmp/deepseek.key)   # key 也记录在 docs/secrets/api-keys.md(均 gitignored)
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation run <arm_label> \
    --prompt-version <ver> --n 45 --seed-base 1000
# 产物 .runs/ablation/<arm_label>/{<label>_NNN/, _index.jsonl, _metrics.json}
NO_PROXY='*' PYTHONPATH=src python -m werewolf_eval.ablation compare <armA_dir> <armB_dir>
```

`seed_base` 跨臂保持同值(默认 1000)= 同 index 同布局,配对可比。注意 `compare` 是**聚合 delta**,`_metrics.json` 不含 per-game 明细。臂没有注册表:label 自由取名,臂配置(model/base_url/seed 规则)= `src/werewolf_eval/ablation/arms.py` 的 `Arm` dataclass。

## 数据有效性三铁律(违反会得出全错结论)

1. **provider 每局新建**(harness 已内建):provider 带 per-game 请求预算,跨局复用耗光后整局退化为兜底 RNG。
2. **按 live 率过滤**:`metrics.aggregate` 剔除 `live_success` 占比 < 0.7 的局(计入 `n_invalid_lowlive`)。任何手工分析同样必须过滤——曾有 44 局只有 6 局真 live,差点全错。
3. **n_valid 核验**:< 40/45 要补跑并排查;抽 2-3 局 `provider-trace.json` 确认请求内容是预期版本(不是假空对比)。

## 已知行为

- 兜底是本地 RNG 不打 API,不花钱;`budget_exhausted`/exception 看 `_index.jsonl` 计数。
- seed 只锁布局,API 非确定 → 对局不逐字复现。
- Windows Defender 偶发 PermissionError(原子 rename 瞬时锁),harness 内建重试。
- 单局 e2e(非批次)走 `run_emergent_deepseek_game`;launcher 起的 server 须 `--allow-live-api`,重启 server 用 taskkill by port(见 testing-and-process-control)。

## 基线对照

prompt_v1 45 局基线快照:`historical harness review 2026-06-11-baseline-prompt-v1-metrics.json`(n_valid=45,狼胜 ~0.778)。原始 .runs 不在仓库,compare 只需把快照复制为 `<dir>/_metrics.json`。

