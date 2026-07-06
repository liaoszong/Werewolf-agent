"""G2d profile configuration helpers.

Pure profile schema, validation, resolution, and resolved-profile artifact
helpers for the prompt-configuration MVP.  No networking, no Qt; standard
library plus one in-package import of pure rules data (action_runtime.ruleset,
the role->team single source per ADR 2026-06-11).
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any

from werewolf_eval.action_runtime.ruleset import known_role_teams

PROFILE_SCHEMA_VERSION = "g2d.profile.v1"

ALLOWED_TEMPLATES: frozenset[str] = frozenset({"default_6p_fake"})
# P2-B-3: every live provider in provider_registry.PROVIDER_REGISTRY plus the
# deterministic fake. Kept as a literal so this module stays pure (stdlib only,
# no provider-runtime import); a consistency test enforces it stays a superset of
# the registry.
ALLOWED_PROVIDERS: frozenset[str] = frozenset(
    {
        "fake_deterministic", "deepseek", "openai", "anthropic", "openai_compatible",
        # P2-B preset vendors (OpenAI-compatible). Kept as a literal so this module
        # stays registry-free; test_allowed_providers_superset_of_registry guards it.
        "zhipu", "moonshot", "qwen", "minimax", "siliconflow",
        "xai", "gemini", "modelscope", "openrouter",
        # Provider migration slice: cc-switch e606adf Codex presets that are
        # explicitly openai_chat-compatible. Responses/Anthropic/Gemini-native
        # presets stay out until matching adapters exist in this backend.
        "volcengine_ark", "byteplus_ark", "zhipu_coding",
        "zhipu_global_coding", "qianfan_coding", "moonshot_cn",
        "kimi_coding", "stepfun", "stepfun_global", "bailing",
        "siliconflow_global", "novita", "nvidia_nim",
        "opencode_go", "atlascloud",
        # P3-C-1b: local participant controller, not a model gateway provider.
        "human",
    }
)
ALLOWED_MODELS: dict[str, frozenset[str]] = {
    "fake_deterministic": frozenset({"none"}),
    "human": frozenset({"none"}),
    "deepseek": frozenset({"deepseek-chat", "deepseek-reasoner"}),
}
# P2-B-1 r2: providers whose model is validated against ALLOWED_MODELS. Live
# providers are deliberately absent (they trust the live model list); only the
# deterministic fake provider keeps a strict model allowlist.
_MODEL_ALLOWLIST_PROVIDERS: frozenset[str] = frozenset({"fake_deterministic", "human"})

# P2-B-3: optional per-seat sampling knobs (numeric, unlike the string config keys).
TEMPERATURE_MIN: float = 0.0
TEMPERATURE_MAX: float = 2.0
MAX_TOKENS_MIN: int = 1
MAX_TOKENS_MAX: int = 8192
_NUMERIC_CONFIG_KEYS: frozenset[str] = frozenset({"temperature", "max_tokens"})

ALLOWED_STRATEGIES: frozenset[str] = frozenset({"default", "aggressive", "cautious"})
ALLOWED_ROLES: frozenset[str] = frozenset({"werewolf", "seer", "witch", "villager", "guard"})
CANONICAL_DEFAULT_6P_ROLES: dict[str, int] = {
    "werewolf": 2,
    "seer": 1,
    "witch": 1,
    "villager": 2,
}
# Derived projection of the single source (ADR 2026-06-11), restricted to the
# product gate. Iteration follows ruleset declaration order, which keeps the
# capabilities payload (":480") stable: werewolf, seer, witch, villager, guard (L4).
ROLE_TEAMS: dict[str, str] = {
    role: team for role, team in known_role_teams().items() if role in ALLOWED_ROLES
}
DEFAULT_6P_SEAT_ROLES: dict[str, str] = {
    "p1": "werewolf",
    "p2": "werewolf",
    "p3": "seer",
    "p4": "witch",
    "p5": "villager",
    "p6": "villager",
}
DEFAULT_SEAT_IDS: tuple[str, ...] = tuple(DEFAULT_6P_SEAT_ROLES)
PROMPT_MAX_LEN = 8000

# Live/default-profile diversity policy (NOT a prompt/rendering policy). Explicit per-seat
# temperature always wins; a null seat temperature is filled with this at build_seat_agents
# time. Single source of truth so build_resolved_profile_artifact can record effective_temperature.
DEFAULT_LIVE_TEMPERATURE = 0.8

# Editable starter personas per role. These are PREPENDED to the machine contract
# as the per-seat persona (llm_providers.compose_system) — they flavor behavior but
# never replace the JSON contract. Seeded into the default profile so the per-seat
# prompt box is never blank; users tweak from here (e.g. make the wolf aggressive).
DEFAULT_ROLE_PROMPTS: dict[str, str] = {
    "werewolf": (
        "你是狼人阵营的一员。夜晚与狼队友配合选择击杀目标;白天伪装成好人,"
        "用合理的逻辑误导其他玩家、把怀疑引向好人,并优先保护狼队友。"
        "发言冷静自然,不要暴露身份。"
    ),
    "seer": (
        "你是预言家(好人阵营)。每晚可以查验一名玩家的真实身份;白天用查验到的信息"
        "引导好人投票放逐狼人,同时提防被狼人冒充。发言条理清晰,让队友信任你。"
    ),
    "witch": (
        "你是女巫(好人阵营)。你有一瓶解药和一瓶毒药,各只能用一次。谨慎判断何时救人、"
        "何时毒人,把药用在最关键的时刻,帮助好人阵营获胜。"
    ),
    "villager": (
        "你是村民(好人阵营),没有特殊能力。通过观察发言、投票和逻辑找出狼人;"
        "积极参与讨论、提出你的推理,带领好人阵营走向胜利。"
    ),
}

# Per-seat ROLE-AGNOSTIC personalities seeded into the default profile so same-role seats
# (e.g. the two wolves) are not clones out of the box. Tone/style ONLY — never role ability
# or team strategy (that lives in the role contract / role_defaults). Users edit per-seat from here.
DEFAULT_SEAT_PERSONAS: dict[str, str] = {
    "p1": "你说话沉稳,偏好用证据和逻辑链推理,不轻易下结论。",
    "p2": "你性格直率、爱挑头表态,常率先抛出怀疑对象并解释理由。",
    "p3": "你谨慎克制,先听后说,擅长复盘别人发言里的前后矛盾。",
    "p4": "你偏感性,善用语气和共情拉拢人心,容易被情绪带动。",
    "p5": "你话不多但一针见血,倾向用一句简短结论收尾。",
    "p6": "你表面松弛爱开玩笑,实则暗中观察并记住每个人的反应。",
}

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,255}$")
_CONFIG_KEYS = frozenset({"provider", "model", "prompt", "strategy", "temperature", "max_tokens"})
_SECRET_KEY_FRAGMENTS = (
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "secret",
    "token",
    "bearer",
    "password",
    "credential",
    "access_key",
)
# Value markers are intentionally NARROWER than key fragments: they target
# high-confidence credential shapes so free-text prompts (e.g. "keep your role
# secret") are NOT rejected, while real credentials (api keys, bearer tokens)
# are.  No bare "secret"/"token"/"password" here.
_VALUE_SECRET_MARKERS = (
    "sk-",
    "bearer ",
    "api_key",
    "api-key",
    "apikey",
    "authorization",
    "access_key",
    "deepseek_api_key",
)


class ProfileValidationError(ValueError):
    """Raised when a profile cannot be validated safely."""


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _reject_secret_like_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            # Known config keys are exempt from the fragment scan (e.g. "max_tokens"
            # contains "token"); recursion into the value still catches nested
            # secret-like keys.
            if str(key).lower() not in _CONFIG_KEYS and any(
                frag in str(key).lower() for frag in _SECRET_KEY_FRAGMENTS
            ):
                raise ProfileValidationError(
                    f"secret-like key not allowed: {path}{key}"
                )
            _reject_secret_like_keys(value, f"{path}{key}.")
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _reject_secret_like_keys(item, f"{path}{index}.")


def _reject_secret_like_values(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            _reject_secret_like_values(value, f"{path}{key}.")
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _reject_secret_like_values(item, f"{path}{index}.")
    elif isinstance(obj, str):
        lowered = obj.lower()
        if any(marker in lowered for marker in _VALUE_SECRET_MARKERS):
            raise ProfileValidationError(
                f"secret-like value not allowed at {path.rstrip('.')}"
            )


def _template_seat_roles(template: str) -> dict[str, str]:
    if template == "default_6p_fake":
        return dict(DEFAULT_6P_SEAT_ROLES)
    raise ProfileValidationError(f"unknown template: {template!r}")


def _check_numeric_field(field_name: str, value: object, where: str) -> None:
    """Validate a per-seat numeric knob. ``bool`` is rejected explicitly (it is an
    ``int`` subclass and must not pass as a number)."""
    if field_name == "temperature":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ProfileValidationError(f"{where}.temperature must be a number")
        if not (TEMPERATURE_MIN <= float(value) <= TEMPERATURE_MAX):
            raise ProfileValidationError(
                f"{where}.temperature must be in [{TEMPERATURE_MIN}, {TEMPERATURE_MAX}]"
            )
    elif field_name == "max_tokens":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ProfileValidationError(f"{where}.max_tokens must be an integer")
        if not (MAX_TOKENS_MIN <= value <= MAX_TOKENS_MAX):
            raise ProfileValidationError(
                f"{where}.max_tokens must be in [{MAX_TOKENS_MIN}, {MAX_TOKENS_MAX}]"
            )


def _check_fragment(fragment: object, *, where: str, required: bool) -> None:
    if not isinstance(fragment, dict):
        raise ProfileValidationError(f"{where} must be an object")
    if "role" in fragment:
        raise ProfileValidationError(f"{where} may not set 'role'")
    extra = set(fragment) - _CONFIG_KEYS
    if extra:
        raise ProfileValidationError(f"{where} has unexpected keys: {sorted(extra)}")
    if required:
        for field_name in ("provider", "model", "strategy"):
            if field_name not in fragment:
                raise ProfileValidationError(f"{where} missing {field_name!r}")
    for field_name, value in fragment.items():
        if field_name in _NUMERIC_CONFIG_KEYS:
            _check_numeric_field(field_name, value, where)
            continue
        if not isinstance(value, str):
            raise ProfileValidationError(f"{where}.{field_name} must be a string")
    if where.startswith("role_defaults.") and fragment.get("provider") == "human":
        raise ProfileValidationError(
            f"{where}.provider may not be 'human'; human control is seat-level only"
        )
    prompt = fragment.get("prompt")
    if isinstance(prompt, str) and len(prompt) > PROMPT_MAX_LEN:
        raise ProfileValidationError(f"{where}.prompt exceeds {PROMPT_MAX_LEN} chars")


def _resolve_seat(profile: dict, seat: str, role: str) -> dict[str, Any]:
    base = dict(profile["role_defaults"][role])
    override = dict(profile.get("seat_overrides", {}).get(seat, {}))
    merged = {**base, **override}
    # persona = role strategy (tracks the role; role_defaults.prompt, overridable per-seat)
    # + per-seat personality (tracks the seat; role-agnostic seat_personas[seat]). Both are
    # profile config inputs; composed here in the config layer and handed to the unchanged
    # compose_system. No seat_personas -> prompt == role_strategy (byte-identical to before).
    role_strategy = merged.get("prompt", "")
    personality = profile.get("seat_personas", {}).get(seat, "")
    if not personality:
        prompt = role_strategy
    elif not role_strategy:
        prompt = personality
    else:
        prompt = f"{role_strategy}\n\n{personality}"
    return {
        "player_id": seat,
        "role": role,
        "team": ROLE_TEAMS[role],
        "provider": merged.get("provider"),
        "model": merged.get("model"),
        "prompt": prompt,
        "strategy": merged.get("strategy"),
        "temperature": merged.get("temperature"),
        "max_tokens": merged.get("max_tokens"),
    }


def _check_resolved_seat(seat_cfg: dict, seat: str) -> None:
    provider = seat_cfg["provider"]
    model = seat_cfg["model"]
    strategy = seat_cfg["strategy"]
    prompt = seat_cfg["prompt"]
    if provider not in ALLOWED_PROVIDERS:
        raise ProfileValidationError(f"{seat}: provider {provider!r} not allowed")
    # P2-B-1 r2: only the fake provider keeps a strict model allowlist. Live
    # providers (deepseek, and the multi-providers added in P2-B-3) trust the
    # live model list fetched from the provider, so they format-check only — a
    # non-empty string. This also fixes the latent bug where the current default
    # model (deepseek-v4-flash) was rejected by a stale allowlist. (ALLOWED_MODELS
    # still backs build_profile_schema's offline fallback dropdown.)
    if provider in _MODEL_ALLOWLIST_PROVIDERS:
        if model not in ALLOWED_MODELS.get(provider, frozenset()):
            raise ProfileValidationError(
                f"{seat}: model {model!r} not valid for provider {provider!r}"
            )
    elif not isinstance(model, str) or not model:
        raise ProfileValidationError(
            f"{seat}: model must be a non-empty string for provider {provider!r}"
        )
    if strategy not in ALLOWED_STRATEGIES:
        raise ProfileValidationError(f"{seat}: strategy {strategy!r} not allowed")
    if not isinstance(prompt, str) or len(prompt) > PROMPT_MAX_LEN:
        raise ProfileValidationError(f"{seat}: prompt invalid or too long")


def validate_profile(profile: object) -> None:
    """Raise ``ProfileValidationError`` on the first failed rule; else return."""
    if not isinstance(profile, dict):
        raise ProfileValidationError("profile must be a JSON object")
    # Secret-like keys and values first, so the failure reason is explicit.
    _reject_secret_like_keys(profile)
    _reject_secret_like_values(profile)
    allowed_top = {"schema_version", "name", "template", "role_defaults", "seat_overrides", "seat_personas", "role_shuffle"}
    extra = set(profile) - allowed_top
    if extra:
        raise ProfileValidationError(f"unexpected top-level keys: {sorted(extra)}")
    if profile.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise ProfileValidationError(
            f"schema_version must be {PROFILE_SCHEMA_VERSION!r}"
        )
    name = profile.get("name")
    if not isinstance(name, str) or not _SAFE_NAME_RE.match(name):
        raise ProfileValidationError(f"invalid profile name: {name!r}")
    template = profile.get("template")
    if template not in ALLOWED_TEMPLATES:
        raise ProfileValidationError(f"unknown template: {template!r}")
    seat_roles = _template_seat_roles(template)
    needed_roles = set(seat_roles.values())
    role_defaults = profile.get("role_defaults")
    if not isinstance(role_defaults, dict) or set(role_defaults) != needed_roles:
        raise ProfileValidationError(
            f"role_defaults must cover exactly {sorted(needed_roles)}"
        )
    for role, fragment in role_defaults.items():
        _check_fragment(fragment, where=f"role_defaults.{role}", required=True)
    seat_overrides = profile.get("seat_overrides", {})
    if not isinstance(seat_overrides, dict):
        raise ProfileValidationError("seat_overrides must be an object")
    for seat, fragment in seat_overrides.items():
        if seat not in DEFAULT_SEAT_IDS:
            raise ProfileValidationError(f"unknown seat id: {seat!r}")
        _check_fragment(fragment, where=f"seat_overrides.{seat}", required=False)
    # seat_personas: per-seat ROLE-AGNOSTIC personality (tone/style only). MUST NOT encode
    # role abilities or team strategy (e.g. "你是狼/夜晚击杀/查验") — those belong to the role
    # contract; a role-coded persona would clash with the seat's actual role once role-shuffle
    # lands. Semantics are doc-enforced (not machine-checkable) here + in the field docstring.
    seat_personas = profile.get("seat_personas", {})
    if not isinstance(seat_personas, dict):
        raise ProfileValidationError("seat_personas must be an object")
    for sp_seat, persona in seat_personas.items():
        if sp_seat not in DEFAULT_SEAT_IDS:
            raise ProfileValidationError(f"unknown seat id in seat_personas: {sp_seat!r}")
        if not isinstance(persona, str):
            raise ProfileValidationError(
                f"seat_personas.{sp_seat} must be a role-agnostic personality string "
                f"(tone/style only; no role ability or team strategy), got {type(persona).__name__}"
            )
        if len(persona) > PROMPT_MAX_LEN:
            raise ProfileValidationError(
                f"seat_personas.{sp_seat} exceeds {PROMPT_MAX_LEN} chars "
                f"(role-agnostic personality; tone/style only)"
            )
    role_shuffle = profile.get("role_shuffle", {})
    if not isinstance(role_shuffle, dict):
        raise ProfileValidationError("role_shuffle must be an object")
    if "enabled" in role_shuffle and not isinstance(role_shuffle["enabled"], bool):
        raise ProfileValidationError("role_shuffle.enabled must be a boolean")
    counts: dict[str, int] = {}
    for role in seat_roles.values():
        counts[role] = counts.get(role, 0) + 1
    if counts != CANONICAL_DEFAULT_6P_ROLES:
        raise ProfileValidationError("role multiset must match canonical default_6p")
    human_seats: list[str] = []
    for seat in DEFAULT_SEAT_IDS:
        resolved_seat = _resolve_seat(profile, seat, seat_roles[seat])
        _check_resolved_seat(resolved_seat, seat)
        if resolved_seat.get("provider") == "human":
            human_seats.append(seat)
    if len(human_seats) > 1:
        raise ProfileValidationError(
            f"only one human-controlled seat is supported, got {human_seats}"
        )


def resolve_profile(profile: dict) -> list[dict]:
    """Return resolved per-seat configs in template seat order.  Assumes a
    validated profile."""
    seat_roles = _template_seat_roles(profile["template"])
    return [
        _resolve_seat(profile, seat, seat_roles[seat])
        for seat in DEFAULT_SEAT_IDS
    ]


def compute_role_shuffle(profile: dict, *, run_id: str | None, shuffle_seed: int | None) -> dict:
    """Single source of the per-run role shuffle. Returns
    {enabled, seed, seed_source, seat_roles}. seat_roles preserves the template's canonical
    multiset; explicit shuffle_seed beats run_id; off -> default (template) layout."""
    base = _template_seat_roles(profile["template"])  # single source per template
    enabled = bool(profile.get("role_shuffle", {}).get("enabled", False))
    if not enabled:
        return {"enabled": False, "seed": None, "seed_source": None, "seat_roles": dict(base)}
    if shuffle_seed is not None:
        seed, seed_source = int(shuffle_seed), "explicit"
    elif run_id is not None:
        seed = int.from_bytes(hashlib.sha256(run_id.encode("utf-8")).digest()[:8], "big")
        seed_source = "run_id"
    else:
        seed, seed_source = None, None
    seat_order = list(base.keys())
    roles = [base[s] for s in seat_order]
    if seed is not None:
        random.Random(seed).shuffle(roles)
    return {"enabled": True, "seed": seed, "seed_source": seed_source,
            "seat_roles": dict(zip(seat_order, roles))}


def resolve_profile_for_run(profile: dict, *, run_id: str | None = None,
                            shuffle_seed: int | None = None) -> list[dict]:
    """Resolve seats for an ACTUAL run, applying role_shuffle. When role_shuffle is
    enabled a seed (explicit or run_id-derived) is REQUIRED — no silent fallback to the
    default layout. Off -> identical to resolve_profile (byte-parity)."""
    info = compute_role_shuffle(profile, run_id=run_id, shuffle_seed=shuffle_seed)
    if info["enabled"] and info["seed"] is None:
        raise ProfileValidationError(
            "role_shuffle enabled but neither shuffle_seed nor run_id provided"
        )
    seat_roles = info["seat_roles"]
    resolved = [_resolve_seat(profile, seat, seat_roles[seat]) for seat in DEFAULT_SEAT_IDS]
    if info["enabled"]:
        # shuffle produces NEW (seat,role) combos validate_profile never checked (it only
        # validated the default mapping). Re-check each — catches e.g. the composed
        # "new-role strategy + seat personality" exceeding PROMPT_MAX_LEN. No silent pass.
        for seat_cfg, seat in zip(resolved, DEFAULT_SEAT_IDS):
            _check_resolved_seat(seat_cfg, seat)
    return resolved


def build_resolved_profile_artifact(
    profile: dict,
    run_id: str,
    *,
    execution_mode: str = "fake",
    live_api: str = "not_used",
) -> dict:
    """Build the ``resolved-profile.json`` content: declared per-seat config
    with hashed prompts and explicit execution markers.

    ``execution_mode``/``live_api`` default to the fake markers for back-compat;
    the server live ``_profile_launcher`` wrapper passes ``"live"``/``"used"``.
    The per-seat ``model`` is the resolved real model — this artifact is the
    authoritative model record (A3)."""
    info = compute_role_shuffle(profile, run_id=run_id, shuffle_seed=None)
    seats: list[dict[str, Any]] = []
    for seat_cfg in resolve_profile_for_run(profile, run_id=run_id):
        prompt = seat_cfg.get("prompt") or ""
        seats.append(
            {
                "player_id": seat_cfg["player_id"],
                "role": seat_cfg["role"],
                "team": seat_cfg["team"],
                "provider": seat_cfg["provider"],
                "model": seat_cfg["model"],
                "strategy": seat_cfg["strategy"],
                # temperature = EXPLICIT configured value (null = unset; filled at build_seat_agents).
                "temperature": seat_cfg.get("temperature"),
                # effective_temperature = additive: what the live run actually samples at
                # (explicit value, else the DEFAULT_LIVE_TEMPERATURE policy). Single-sourced so
                # old(API default) vs new(0.8) live runs are distinguishable in the artifact.
                "effective_temperature": (
                    None if seat_cfg["provider"] == "human"
                    else (
                        seat_cfg["temperature"] if seat_cfg.get("temperature") is not None
                        else DEFAULT_LIVE_TEMPERATURE
                    )
                ),
                "max_tokens": seat_cfg.get("max_tokens"),
                "prompt_hash": "" if seat_cfg["provider"] == "human" else (_hash_text(prompt) if prompt else ""),
            }
        )
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_name": profile["name"],
        "template": profile["template"],
        "execution_mode": execution_mode,
        "live_api": live_api,
        "secrets_redacted": True,
        "role_shuffle": {
            "enabled": info["enabled"], "seed": info["seed"], "seed_source": info["seed_source"],
        },
        "seats": seats,
    }


def build_profile_schema() -> dict:
    """Return read-only UI metadata (dropdown options + seat layout) derived
    from the validation constants.  No profile-name list (that comes from
    GET /api/profiles), no secrets, no paths."""
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "providers": sorted(ALLOWED_PROVIDERS),
        "models": {p: sorted(ALLOWED_MODELS[p]) for p in sorted(ALLOWED_MODELS)},
        "strategies": sorted(ALLOWED_STRATEGIES),
        "roles": sorted(ALLOWED_ROLES),
        "role_teams": dict(ROLE_TEAMS),
        "seat_roles": dict(DEFAULT_6P_SEAT_ROLES),
        "seat_ids": list(DEFAULT_SEAT_IDS),
        "prompt_max_len": PROMPT_MAX_LEN,
    }


def load_profile(path: Path) -> dict:
    """Read and parse a profile JSON file; raise ProfileValidationError on
    malformed JSON or non-object content.  Error messages use the basename
    only — never the absolute path — so server responses cannot leak local
    paths."""
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProfileValidationError(f"invalid JSON in {p.name}: {exc}") from exc
    except OSError:
        raise ProfileValidationError(f"cannot read profile {p.name}")
    if not isinstance(data, dict):
        raise ProfileValidationError("profile file must contain a JSON object")
    return data


def save_profile(profile: dict, profiles_dir: Path) -> Path:
    """Validate then write ``<profiles_dir>/<name>.json``.  Pure helper — not a
    server endpoint this slice."""
    validate_profile(profile)
    name = profile["name"]
    if not _SAFE_NAME_RE.match(name):
        raise ProfileValidationError(f"unsafe profile name: {name!r}")
    target_dir = Path(profiles_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{name}.json"
    target.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def list_profiles(profiles_dir: Path) -> list[dict]:
    """Return per-file metadata; malformed files are reported valid=False and
    never raise."""
    target_dir = Path(profiles_dir)
    entries: list[dict] = []
    if not target_dir.is_dir():
        return entries
    for path in sorted(target_dir.glob("*.json")):
        entry: dict[str, Any] = {
            "name": path.stem,
            "template": None,
            "valid": False,
            "error": None,
        }
        try:
            data = load_profile(path)
            validate_profile(data)
            entry["template"] = data.get("template")
            entry["valid"] = True
        except ProfileValidationError as exc:
            entry["error"] = str(exc)
        entries.append(entry)
    return entries


def build_default_profile(name: str = "default_6p") -> dict:
    """A baseline, always-valid starter profile: the default 6-player template,
    deterministic-simulation providers, and pre-filled editable role prompts. Used
    to seed an empty profiles dir so a fresh setup page is never an empty
    'no profiles' state — users customise per-seat in the client from here."""
    roles = sorted(set(DEFAULT_6P_SEAT_ROLES.values()))
    role_defaults = {
        role: {
            "provider": "fake_deterministic",
            "model": "none",
            "strategy": "default",
            "prompt": DEFAULT_ROLE_PROMPTS.get(role, ""),
        }
        for role in roles
    }
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "name": name,
        "template": "default_6p_fake",
        "role_defaults": role_defaults,
        "seat_personas": dict(DEFAULT_SEAT_PERSONAS),
    }
