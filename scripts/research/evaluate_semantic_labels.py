from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VALID_QUALITY_LABELS = {"supported_good", "supported_neutral", "unsupported", "contradicted", "random_or_default"}
VALID_EVIDENCE_ALIGNMENTS = {"aligned", "weak", "missing", "contradicted"}
VALID_REASONING_CONSISTENCIES = {"consistent", "thin", "inconsistent"}
ACCEPTANCE_THRESHOLD = 0.8
MAX_RATIONALE_CHARS = 180

LABEL_REQUIRED_FIELDS = {
    "decision_id",
    "quality_label",
    "evidence_alignment",
    "reasoning_consistency",
    "confidence",
    "short_rationale",
}


def _validate_label(label: dict[str, Any]) -> None:
    missing = LABEL_REQUIRED_FIELDS - set(label)
    if missing:
        raise ValueError(f"label missing fields: {sorted(missing)}")

    did = label["decision_id"]

    if label["quality_label"] not in VALID_QUALITY_LABELS:
        raise ValueError(f"unknown quality_label for {did}: {label['quality_label']!r}")
    if label["evidence_alignment"] not in VALID_EVIDENCE_ALIGNMENTS:
        raise ValueError(f"unknown evidence_alignment for {did}: {label['evidence_alignment']!r}")
    if label["reasoning_consistency"] not in VALID_REASONING_CONSISTENCIES:
        raise ValueError(f"unknown reasoning_consistency for {did}: {label['reasoning_consistency']!r}")

    confidence = label["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise ValueError(f"confidence must be a number for {did}: {confidence!r}")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError(f"confidence out of range for {did}: {confidence}")

    rationale = label["short_rationale"]
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError(f"short_rationale must be non-empty for {did}")
    if len(rationale) > MAX_RATIONALE_CHARS:
        raise ValueError(f"short_rationale exceeds {MAX_RATIONALE_CHARS} chars for {did}: {len(rationale)}")


def evaluate_files(eval_set_path: Path, output_path: Path) -> dict[str, Any]:
    eval_set = json.loads(eval_set_path.read_text(encoding="utf-8"))
    output = json.loads(output_path.read_text(encoding="utf-8"))

    if eval_set["game_id"] != output["game_id"]:
        raise ValueError(
            f"game_id mismatch: eval set {eval_set['game_id']!r} != output {output['game_id']!r}"
        )

    label_ids = [label.get("decision_id") for label in output["labels"]]
    seen: set[str] = set()
    for did in label_ids:
        if did in seen:
            raise ValueError(f"duplicate decision_id in output labels: {did!r}")
        seen.add(did)

    for label in output["labels"]:
        _validate_label(label)

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
    quality_acc = quality_correct / total
    evidence_acc = evidence_correct / total
    reasoning_acc = reasoning_correct / total
    valid = quality_acc >= ACCEPTANCE_THRESHOLD and evidence_acc >= ACCEPTANCE_THRESHOLD and reasoning_acc >= ACCEPTANCE_THRESHOLD

    return {
        "valid": valid,
        "decision_count": total,
        "quality_label_accuracy": quality_acc,
        "evidence_alignment_accuracy": evidence_acc,
        "reasoning_consistency_accuracy": reasoning_acc,
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
