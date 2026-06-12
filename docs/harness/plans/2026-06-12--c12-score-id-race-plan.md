# C12-05: 消除 scoring score_id 模块级全局态竞态

**审计来源**: `docs/health-check/2026-06-12-system-view-audit.md` C12-05  
**分支**: `codex/c12-score-id-race`  
**日期**: 2026-06-12

## 问题

`scoring_records.py:533` 模块级全局 `_current_score_id_prefix` 在 ThreadingHTTPServer
并发场景下，A 局 `score_game()` 的 score_id 可能被 B 局前缀污染，且污染结果被
`settlement_bundle.py:385-390` 缓存固化。

## 范围

- **修改**: `src/werewolf_eval/scoring_records.py`（核心：删全局，改参数传递）
- **连带**: `src/werewolf_eval/scoring.py`（facade 重导出更新）
- **测试**: `tests/test_scoring.py`（新增并发隔离回归测试）
- **不碰**: engine/provider/ablation/其他任何 src 文件

## 验收

1. 全量 unittest 绿（`PYTHONPATH=src python -m pytest tests/ -q`）
2. 分值数值不变（字节/分数恒等，对既有 fixture 无变化）
3. 并发隔离：两个不同 game_id 的 score_game 并发调用，score_id 前缀不互污染
4. `git diff --stat` 确认只有上述三个文件
5. `_current_score_id_prefix` 模块级变量已删除

## 变更设计

### scoring_records.py

1. `_record()`: 加 `score_id_prefix: str` 参数 → 直接使用，不再读全局
2. `_score_werewolf_kill/check/save/poison/vote()`: 加 `score_id_prefix: str` 参数 → 透传给 `_record()`
3. `score_game()`: 本地计算 `score_id_prefix = _score_id_prefix(game)` → 逐调用透传
4. 删除 `_current_score_id_prefix` 模块级变量和 `global` 声明

### scoring.py (facade)

- `_record` 签名变了（加了参数），但对外无调用者，保持重导出不变
- 无需额外变更

### 测试

- 新增 `test_score_game_prefix_isolation_concurrent`：两线程并发 `score_game`，断言 score_id 前缀不互污染
