# S5 Semantic Label Contract

## Saved-output JSON shape

```json
{
  "label_log_id": "s5_g001_example",
  "game_id": "g001",
  "source_label": "[semantic research output]",
  "prompt_candidate": "candidate_a_minimal_json",
  "labels": [
    {
      "decision_id": "g001_d001",
      "quality_label": "supported_neutral",
      "evidence_alignment": "aligned",
      "reasoning_consistency": "consistent",
      "confidence": 0.8,
      "short_rationale": "The decision cites visible evidence and has a plausible target."
    }
  ]
}
```

## Field constraints

`confidence` must be a number from `0.0` to `1.0`. `short_rationale` must be non-empty and at most 180 characters.

## Allowed `quality_label` values

- `supported_good`
- `supported_neutral`
- `unsupported`
- `contradicted`
- `random_or_default`

## Allowed `evidence_alignment` values

- `aligned`
- `weak`
- `missing`
- `contradicted`

## Allowed `reasoning_consistency` values

- `consistent`
- `thin`
- `inconsistent`
