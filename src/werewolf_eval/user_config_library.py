"""User-saved match configuration library.

This module stores reusable match configs separately from built-in server
profiles.  It is pure filesystem/JSON logic: no HTTP and no Qt.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any

from werewolf_eval.profile_config import (
    ProfileValidationError,
    _reject_secret_like_keys,
    _reject_secret_like_values,
    validate_profile,
)

CONFIG_SCHEMA_VERSION = 1
CONFIG_KIND = "werewolf_agent.match_config"

_SAFE_CONFIG_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


class UserConfigError(ValueError):
    """Raised when a user config cannot be read, written, or validated."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slugify(value: str) -> str:
    pieces: list[str] = []
    last_dash = False
    for ch in value.lower():
        if ch.isascii() and (ch.isalnum() or ch in "_.-"):
            pieces.append(ch)
            last_dash = False
        elif not last_dash:
            pieces.append("-")
            last_dash = True
    slug = "".join(pieces).strip("-._")
    return (slug or "config")[:80]


def _safe_config_id(value: str) -> str:
    if not _SAFE_CONFIG_ID_RE.match(value):
        raise UserConfigError("config_not_found", "config not found")
    return value


def _config_path(configs_dir: Path, config_id: str) -> Path:
    safe_id = _safe_config_id(config_id)
    return Path(configs_dir) / f"{safe_id}.json"


def _scan_for_secrets(obj: Any) -> None:
    try:
        _reject_secret_like_keys(obj)
        _reject_secret_like_values(obj)
    except ProfileValidationError as exc:
        raise UserConfigError("secret_detected", str(exc)) from exc


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UserConfigError("invalid_config_file", f"invalid JSON in {path.name}: {exc}") from exc
    except OSError as exc:
        raise UserConfigError("config_not_found", "config not found") from exc
    if not isinstance(data, dict):
        raise UserConfigError("invalid_config_file", "config file must contain a JSON object")
    return data


def _validate_payload(payload: dict[str, Any], *, importing: bool) -> dict[str, Any]:
    if payload.get("schema_version") != CONFIG_SCHEMA_VERSION:
        raise UserConfigError("unsupported_config_version", "unsupported config schema version")
    if payload.get("kind") != CONFIG_KIND:
        raise UserConfigError("invalid_config_file", "invalid config kind")
    _scan_for_secrets(payload)
    display_name = payload.get("display_name")
    if not isinstance(display_name, str) or not display_name.strip():
        raise UserConfigError("config_name_required", "config display_name is required")
    profile = payload.get("profile")
    if not isinstance(profile, dict):
        raise UserConfigError("invalid_profile", "config profile must be a JSON object")
    try:
        validate_profile(profile)
    except ProfileValidationError as exc:
        code = "secret_detected" if "secret-like" in str(exc).lower() else "invalid_profile"
        raise UserConfigError(code, str(exc)) from exc
    if not importing:
        config_id = payload.get("id")
        if not isinstance(config_id, str) or not _SAFE_CONFIG_ID_RE.match(config_id):
            raise UserConfigError("invalid_config_file", "invalid config id")
    return payload


def _metadata_item(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": payload["id"],
        "display_name": payload["display_name"],
        "updated_at": payload["updated_at"],
        "script_id": payload.get("script_id"),
        "base_profile": payload.get("base_profile"),
    }


def _existing_payloads(configs_dir: Path) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    target_dir = Path(configs_dir)
    if not target_dir.is_dir():
        return payloads
    for path in sorted(target_dir.glob("*.json")):
        try:
            payload = _validate_payload(_read_payload(path), importing=False)
        except UserConfigError:
            continue
        payloads.append(payload)
    return payloads


def _unique_display_name(configs_dir: Path, requested: str) -> str:
    base = requested.strip()
    if not base:
        raise UserConfigError("config_name_required", "config display_name is required")
    existing = {str(p["display_name"]) for p in _existing_payloads(configs_dir)}
    if base not in existing:
        return base
    copy_base = f"{base} 副本"
    candidate = copy_base
    index = 2
    while candidate in existing:
        candidate = f"{copy_base} {index}"
        index += 1
    return candidate


def _unique_config_id(configs_dir: Path, display_name: str) -> str:
    base = _slugify(display_name)
    candidate = base
    index = 2
    while _config_path(configs_dir, candidate).exists():
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def _write_payload(configs_dir: Path, payload: dict[str, Any]) -> None:
    target_dir = Path(configs_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = _config_path(target_dir, str(payload["id"]))
    tmp = target.with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp.replace(target)
    except OSError as exc:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise UserConfigError("config_write_failed", "failed to write config") from exc


def save_user_config(
    configs_dir: Path,
    *,
    display_name: str,
    profile: dict[str, Any],
    script_id: str | None = None,
    base_profile: str | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """Validate and save a new user config, returning list metadata."""
    clean_profile = deepcopy(profile)
    try:
        validate_profile(clean_profile)
    except ProfileValidationError as exc:
        code = "secret_detected" if "secret-like" in str(exc).lower() else "invalid_profile"
        raise UserConfigError(code, str(exc)) from exc
    display = _unique_display_name(configs_dir, display_name)
    config_id = _unique_config_id(configs_dir, display)
    stamp = now or _utc_now()
    payload: dict[str, Any] = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "kind": CONFIG_KIND,
        "id": config_id,
        "display_name": display,
        "created_at": stamp,
        "updated_at": stamp,
        "script_id": script_id or clean_profile.get("template"),
        "base_profile": base_profile or clean_profile.get("name"),
        "profile": clean_profile,
    }
    _scan_for_secrets(payload)
    _write_payload(configs_dir, payload)
    return _metadata_item(payload)


def list_user_configs(configs_dir: Path) -> list[dict[str, Any]]:
    """Return valid user config metadata sorted by update time then id."""
    payloads = _existing_payloads(configs_dir)
    payloads.sort(key=lambda p: (str(p.get("updated_at", "")), str(p.get("id", ""))), reverse=True)
    return [_metadata_item(payload) for payload in payloads]


def load_user_config(configs_dir: Path, config_id: str) -> dict[str, Any]:
    path = _config_path(configs_dir, config_id)
    if not path.exists():
        raise UserConfigError("config_not_found", "config not found")
    return deepcopy(_validate_payload(_read_payload(path), importing=False))


def export_user_config(configs_dir: Path, config_id: str) -> dict[str, Any]:
    payload = load_user_config(configs_dir, config_id)
    _scan_for_secrets(payload)
    return payload


def import_user_config(
    configs_dir: Path,
    payload: dict[str, Any],
    *,
    now: str | None = None,
) -> dict[str, Any]:
    """Validate an exported config payload and save it as a new user config."""
    if not isinstance(payload, dict):
        raise UserConfigError("invalid_config_file", "config import body must be a JSON object")
    validated = _validate_payload(deepcopy(payload), importing=True)
    return save_user_config(
        configs_dir,
        display_name=str(validated["display_name"]),
        profile=deepcopy(validated["profile"]),
        script_id=validated.get("script_id"),
        base_profile=validated.get("base_profile"),
        now=now,
    )
