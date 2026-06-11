---
name: guarding-prompt-bytes
description: Use when changing any model-visible prompt text (system prompts, observation renderers, witch/hunter augmentations), when tests/test_prompt_versioning.py fails, or when deciding between bumping PROMPT_VERSION and adding a coexisting prompt version.
---

# Prompt 字节锁(改模型可见字节前必读)

## 核心规则

`src/werewolf_eval/prompt_version.py` docstring 是权威:baseline 渲染链(`build_action_system_prompt` / `build_speech_system_prompt` / `compose_system` / `render_observation_text`、含 `augment_witch_observation` 与 `HUNTER_SHOT_OBSERVATION_SUFFIX`)的**任何**模型可见字节变化都要走版本化流程,**无 cosmetic 豁免**。`tests/test_prompt_versioning.py` 三条规则全 FAIL 不警告:

- RULE 1:字节漂移但没 bump → fail
- RULE 2:缺 golden 目录 / ledger 条目 / hash 过期 → fail
- RULE 3:新版本与 base 字节相同 → fail(无意义 bump)

## 先做判断:bump 还是新增共存版本?

- **改既有版本的字节**(修字、调措辞)→ bump `PROMPT_VERSION` + regen + ledger。
- **新增一条渲染路径、运行时按 arm/局选择**(如 prompt_v2 共存)→ 不翻 `PROMPT_VERSION`,新增版本进 `KNOWN_PROMPT_VERSIONS`,自带 golden 目录 + ledger 条目;v1 golden 必须零变化(`git diff --exit-code tests/golden_prompts/prompt_v1` 验证)。默认版本翻转是消融出结果后的独立用户决策。

## 流程(bump 或新增,同一套机械步骤)

```bash
# 1. 改 prompt_version.py(bump 常量,或扩 KNOWN_PROMPT_VERSIONS)
# 2. 重生成 golden(UTF-8+LF,.gitattributes 钉死)
NO_PROXY='*' PYTHONPATH=src python tools/generate_golden_prompts.py
# 3. ledger 条目:docs/generated-games/prompt-version-ledger.json
#    必填:base_version / reason / expected_change / golden_prompt_hashes{before,after}
#         / behavior_evidence{status, reason_if_not_run} / blessed_by / blessed_at
#    hash 勿手填:第 2 步的生成器会打印 {version: {name: sha256}} map,直接粘贴进 after
# 4. 守卫 + 全量
NO_PROXY='*' PYTHONPATH=src python -m pytest tests/test_prompt_versioning.py tests/ -q
```

## 容易漏的点

- golden 样本集单源在 `src/werewolf_eval/prompt_goldens.py`,加可见字节(如新角色后缀)要同步加样本,否则锁不住。
- 消融 harness(`ablation/harness.py`)对 prompt_version 有硬门,版本集合变化要联动。
- provider trace 经 asdict 存 `observation_text` 渲染串——比对 trace 类工件时注意。
- ledger root 是 JSON 数组;每个版本恰好一条。
