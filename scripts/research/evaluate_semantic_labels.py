from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VALID_QUALITY_LABELS = {"supported_good", "supported_neutral", "unsupported", "contradicted", "random_or_default"}
VALID_EVIDENCE_ALIGNMENTS = {"aligned", "weak", "missing", "contradicted"}
VALID_REASONING_CONSISTENCIES = {"consistent", "thin", "inconsistent"}


def evaluate_files(eval_set_path: Path, output_path: Path) -> dict[str, Any]:
    eval_set = json.loads(eval_set_path.read_text(encoding="utf-8"))
    output = json.loads(output_path.read_text(encoding="utf-8"))

    if eval_set["game_id"] != output["game_id"]:
        raise ValueError(
            f"game_id mismatch: eval set {eval_set['game_id']!r} != output {output['game_id']!r}"
        )

    eval_items = {item["decision_id"]: item for item in eval_set["items"]}
    output_labels = {label["decision_id"]: label for label in output["labels"]}

    if set(output_labels) != set(eval_items):
        missing = set(eval_items) - set(output_labels)
        extra = set(output_labels) - set(eval_items)
        parts = []
        if missing:
            parts.append(f"missing from output: {sorted(missing)}")
        if extra:
            parts.append(f"extra in output: {sorted(extra)}")
        raise ValueError("; ".join(parts))

    for label in output["labels"]:
        if label["quality_label"] not in VALID_QUALITY_LABELS:
            raise ValueError(f"unknown quality_label: {label['quality_label']!r}")
        if label["evidence_alignment"] not in VALID_EVIDENCE_ALIGNMENTS:
            raise ValueError(f"unknown evidence_alignment: {label['evidence_alignment']!r}")
        if label["reasoning_consistency"] not in VALID_REASONING_CONSISTENCIES:
            raise ValueError(f"unknown reasoning_consistency: {label['reasoning_consistency']!r}")
        confidence = label.get("confidence")
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            raise ValueError(f"confidence out of range for {label['decision_id']}: {confidence}")

    quality_correct = sum(
        1 for did, item in eval_items.items()
        if output_labels[did]["quality_label"] == item["expected_quality_label"]
    )
    evidence_correct = sum(
        1 for did, item in eval_items.items()
        if output_labels[did]["evidence_alignment"] == item["expected_evidence_alignment"]
    )
    reasoning_correct = sum(
        1 for did, item in eval_items.items()
        if output_labels[did]["reasoning_consistency"] == item["expected_reasoning_consistency"]
    )
    total = len(eval_items)
    valid = quality_correct == total and evidence_correct == total and reasoning_correct == total

    return {
        "valid": valid,
        "decision_count": total,
        "quality_label_accuracy": quality_correct / total,
        "evidence_alignment_accuracy": evidence_correct / total,
        "reasoning_consistency_accuracy": reasoning_correct / total,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate S5 semantic label output against a manual eval set.")
    parser.add_argument("eval_set_path", type=Path)
    parser.add_argument("output_path", type=Path)
    args = parser.parse_args()

    try:
        result = evaluate_files(args.eval_set_path, args.output_path)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"s5_semantic_label_accuracy error={exc}")
        return 1

    print(
        f"s5_semantic_label_accuracy "
        f"quality_label={result['quality_label_accuracy']:.3f} "
        f"evidence_alignment={result['evidence_alignment_accuracy']:.3f} "
        f"reasoning_consistency={result['reasoning_consistency_accuracy']:.3f} "
        f"valid={'true' if result['valid'] else 'false'} "
        f"decisions={result['decision_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
