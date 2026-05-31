from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from werewolf_eval.decision_log import DecisionLog

VALID_QUALITY_LABELS = {"supported_good", "supported_neutral", "unsupported", "contradicted", "random_or_default"}
VALID_EVIDENCE_ALIGNMENTS = {"aligned", "weak", "missing", "contradicted"}
VALID_REASONING_CONSISTENCIES = {"consistent", "thin", "inconsistent"}
VALID_SOURCE_LABELS = {"[semantic research output]"}
VALID_PROMPT_CANDIDATES = {"candidate_a_minimal_json", "candidate_b_evidence_first_json"}
MAX_RATIONALE_CHARS = 180

REQUIRED_TOP_KEYS = {"label_log_id", "game_id", "source_label", "prompt_candidate", "labels"}
REQUIRED_LABEL_KEYS = {"decision_id", "quality_label", "evidence_alignment", "reasoning_consistency", "confidence", "short_rationale"}


@dataclass(frozen=True)
class SemanticLabel:
    decision_id: str
    quality_label: str
    evidence_alignment: str
    reasoning_consistency: str
    confidence: float
    short_rationale: str


@dataclass(frozen=True)
class SemanticLabelLog:
    label_log_id: str
    game_id: str
    source_label: str
    prompt_candidate: str
    labels: list[SemanticLabel]

    @property
    def label_by_decision_id(self) -> dict[str, SemanticLabel]:
        return {label.decision_id: label for label in self.labels}


class SemanticLabelValidationError(ValueError):
    """Raised when a Semantic Label Log cannot be accepted as saved S5 input."""


def _validate_enum(value: str, allowed: set[str], field: str) -> None:
    if value not in allowed:
        raise SemanticLabelValidationError(
            f"invalid {field} '{value}'; allowed: {sorted(allowed)}"
        )


def parse_semantic_label_log(raw: dict[str, Any], decision_log: DecisionLog) -> SemanticLabelLog:
    if not isinstance(raw, dict):
        raise SemanticLabelValidationError("root must be an object")

    missing = REQUIRED_TOP_KEYS - raw.keys()
    extra = raw.keys() - REQUIRED_TOP_KEYS
    if missing or extra:
        raise SemanticLabelValidationError(
            f"top-level keys must be exactly {sorted(REQUIRED_TOP_KEYS)}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )

    if raw["game_id"] != decision_log.game_id:
        raise SemanticLabelValidationError(
            f"game_id '{raw['game_id']}' does not match decision_log.game_id '{decision_log.game_id}'"
        )

    _validate_enum(raw["source_label"], VALID_SOURCE_LABELS, "source_label")
    _validate_enum(raw["prompt_candidate"], VALID_PROMPT_CANDIDATES, "prompt_candidate")

    if not isinstance(raw["labels"], list):
        raise SemanticLabelValidationError("labels must be a list")

    seen_ids: set[str] = set()
    labels: list[SemanticLabel] = []

    for i, item in enumerate(raw["labels"]):
        if not isinstance(item, dict):
            raise SemanticLabelValidationError(f"labels[{i}] must be an object")

        missing_keys = REQUIRED_LABEL_KEYS - item.keys()
        extra_keys = item.keys() - REQUIRED_LABEL_KEYS
        if missing_keys or extra_keys:
            raise SemanticLabelValidationError(
                f"labels[{i}] keys must be exactly {sorted(REQUIRED_LABEL_KEYS)}; "
                f"missing={sorted(missing_keys)}, extra={sorted(extra_keys)}"
            )

        decision_id = item["decision_id"]
        if decision_id in seen_ids:
            raise SemanticLabelValidationError(f"duplicate decision_id '{decision_id}'")
        seen_ids.add(decision_id)

        if decision_id not in decision_log.decision_ids:
            raise SemanticLabelValidationError(f"unknown decision_id '{decision_id}'")

        _validate_enum(item["quality_label"], VALID_QUALITY_LABELS, f"labels[{i}].quality_label")
        _validate_enum(item["evidence_alignment"], VALID_EVIDENCE_ALIGNMENTS, f"labels[{i}].evidence_alignment")
        _validate_enum(item["reasoning_consistency"], VALID_REASONING_CONSISTENCIES, f"labels[{i}].reasoning_consistency")

        confidence = item["confidence"]
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise SemanticLabelValidationError(
                f"labels[{i}].confidence must be a number, got {type(confidence).__name__}"
            )
        if confidence < 0.0 or confidence > 1.0:
            raise SemanticLabelValidationError(
                f"labels[{i}].confidence {confidence} is not in [0.0, 1.0]"
            )

        short_rationale = item["short_rationale"]
        if not isinstance(short_rationale, str) or short_rationale == "":
            raise SemanticLabelValidationError(f"labels[{i}].short_rationale must be non-empty string")
        if len(short_rationale) > MAX_RATIONALE_CHARS:
            raise SemanticLabelValidationError(
                f"labels[{i}].short_rationale length {len(short_rationale)} exceeds {MAX_RATIONALE_CHARS}"
            )

        labels.append(SemanticLabel(
            decision_id=decision_id,
            quality_label=item["quality_label"],
            evidence_alignment=item["evidence_alignment"],
            reasoning_consistency=item["reasoning_consistency"],
            confidence=float(confidence),
            short_rationale=short_rationale,
        ))

    return SemanticLabelLog(
        label_log_id=raw["label_log_id"],
        game_id=raw["game_id"],
        source_label=raw["source_label"],
        prompt_candidate=raw["prompt_candidate"],
        labels=labels,
    )


def load_semantic_label_log(path: str | Path, decision_log: DecisionLog) -> SemanticLabelLog:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_semantic_label_log(raw, decision_log)
