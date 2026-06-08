from __future__ import annotations

VALID_SOURCE_LABELS = {
    "[人工 gold sample]",
    "[AI 生成]",
    "[scripted deterministic output]",
    "[deterministic mock agent output]",
    "[deterministic fake provider output]",
    "[DeepSeek API output]",
    "[OpenAI API output]",
    "[Anthropic API output]",
    "[OpenAI-compatible API output]",
}
