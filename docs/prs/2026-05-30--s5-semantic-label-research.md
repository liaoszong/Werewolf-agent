# S5 Semantic Label Research

## Decision

This PR prepares offline S5 research artifacts. It does not integrate semantic labels into scoring.

## Research Questions

1. Can saved semantic-label output follow the strict JSON contract?
2. Can every eval-set decision be covered exactly once?
3. Can semantic labels match the manual eval set at the required threshold?
4. Which label prompt is more stable on repeated saved-output runs?
5. Which invalid output shape should block scoring integration?

## Acceptance Thresholds

- Contract validity: 100%.
- Decision coverage: 100%.
- `quality_label` agreement: at least 80%.
- `evidence_alignment` agreement: at least 80%.
- `reasoning_consistency` agreement: at least 80%.
- Duplicate decisions, missing decisions, unknown labels, or out-of-range confidence values block integration.

## Required Validation Command

```bash
PYTHONPATH=. python scripts/research/evaluate_semantic_labels.py docs/gold-game/s5-semantic-label-eval-set.json docs/gold-game/s5-semantic-label-output.example.json
```

Expected output:

```text
s5_semantic_label_accuracy quality_label=1.000 evidence_alignment=1.000 reasoning_consistency=1.000 valid=true decisions=5
```
