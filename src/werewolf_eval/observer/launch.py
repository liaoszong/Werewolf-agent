"""Profile-launch orchestration (SYS-C2 split).

``execute_profile_launch`` runs the full gate sequence and the synchronous
side effects (run_dir mkdir + resolved-profile write) but NEVER spawns the run
thread — the handler shell dispatches the returned launcher through its own
``_launch_run_async`` (a frozen test override point: LiveDispatchTests
intercepts it to run launchers synchronously).

Gate ORDER is contract (each step has regression tests):
capability (BEFORE load/validate) → load (named) → validate → shuffle gate →
shape → 409-exists → launcher resolve → mkdir → synchronous artifact write.
"""

from __future__ import annotations

import json
from pathlib import Path

from werewolf_eval.observer.release_manifest import write_release_manifest
from werewolf_eval.observer.run_manager import (
    _check_live_capability,
    _check_live_profile_shape,
    _resolve_live_launcher_for_launch,
)
from werewolf_eval.observer.state import ObserverServerState, RunLauncher
from werewolf_eval.observer_protocol import parse_profile_launch_request
from werewolf_eval.profile_config import (
    ProfileValidationError,
    build_resolved_profile_artifact,
    load_profile,
    resolve_profile_for_run,
    validate_profile,
)

# ("error", status, code, message) | ("launch", run_id, run_dir, launcher, payload_202)
LaunchOutcome = (
    tuple[str, int, str, str] | tuple[str, str, Path, RunLauncher, dict[str, object]]
)


def _human_seat_ids(resolved_seats: list[dict]) -> list[str]:
    return [
        str(seat["player_id"])
        for seat in resolved_seats
        if seat.get("provider") == "human"
    ]


def execute_profile_launch(
    state: ObserverServerState, body: dict[str, object]
) -> LaunchOutcome:
    """Decide and prepare a profile launch. Raises ``ObserverProtocolError``
    on a malformed launch request (the handler's do_POST mapping owns that),
    otherwise returns an outcome tuple — exactly ONE response per call."""
    plr = parse_profile_launch_request(body)
    mode = str(plr["mode"])

    # CAPABILITY gate (BEFORE load/validate) — live only.  Capability
    # precedes validity/shape: an un-provisioned server returns
    # live_api_disabled/missing_api_key even for a malformed or
    # non-deepseek profile, and never creates a run_dir.
    cap_reject = _check_live_capability(state, mode)
    if cap_reject is not None:
        return ("error", *cap_reject)

    if plr["kind"] == "named":
        ppath = state.profiles_dir / f"{plr['profile_name']}.json"
        if not ppath.exists():
            return ("error", 404, "not_found", "profile not found")
        try:
            profile = load_profile(ppath)
        except ProfileValidationError as exc:
            return ("error", 400, "invalid_profile", str(exc))
    else:
        profile = plr["profile"]  # type: ignore[assignment]
    try:
        validate_profile(profile)
    except ProfileValidationError as exc:
        return ("error", 400, "invalid_profile", str(exc))

    # role_shuffle requires the live multi-provider path; fake mode runs a FIXED board and
    # would mislabel the artifact (artifact would record shuffled roles, engine would not).
    # Fail closed — no silent fallback (spec §1.1 alignment).
    if mode != "live" and profile.get("role_shuffle", {}).get("enabled", False):
        return (
            "error",
            400,
            "shuffle_requires_live",
            "role_shuffle requires live mode (multi-provider path); fake mode runs a fixed "
            "board and would mislabel the artifact",
        )

    run_id = str(plr["run_id"])
    # Resolve seats once (role-shuffle applied via run_id) so launcher selection,
    # participant wiring, and resolved-profile artifact all agree.
    resolved_seats = resolve_profile_for_run(profile, run_id=run_id)
    human_seats = _human_seat_ids(resolved_seats)
    if len(human_seats) > 1:
        return ("error", 400, "invalid_profile", "only one human-controlled seat is supported")

    # SHAPE gate (AFTER validate) — live only. Reuses resolved seats for the
    # per-seat credential check.
    if mode == "live":
        shape_reject = _check_live_profile_shape(resolved_seats)
        if shape_reject is not None:
            return ("error", *shape_reject)

    run_dir = state.runs_dir / run_id
    if run_dir.exists():
        return ("error", 409, "conflict", f"Run already exists: {run_id}")

    is_live = mode == "live"
    if is_live:
        base, live_reject = _resolve_live_launcher_for_launch(state, resolved_seats)
        if live_reject is not None:
            return ("error", *live_reject)
    else:
        base = state.launcher
        if human_seats and state.human_profile_fake_launcher_factory is not None:
            base = state.human_profile_fake_launcher_factory(
                state.participant_controller,
                resolved_seats=resolved_seats,
                human_seat_ids=human_seats,
            )
    run_dir.mkdir(parents=True)

    # Write release-manifest.json synchronously (R0). Must succeed or the run
    # must not proceed -- a missing manifest means release provenance is lost.
    try:
        write_release_manifest(
            run_dir=run_dir,
            release_version=state.release_version,
            observer_protocol_version=state.protocol_version,
        )
    except OSError as exc:
        return ("error", 500, "release_manifest_failed", f"release-manifest write failed: {exc}")

    # Write the resolved-profile (which carries execution_mode) SYNCHRONOUSLY here,
    # before the async run starts and before the 202 returns. The artifact is built
    # entirely from launch-time inputs, so the content is identical to writing it
    # after the run — but writing it up front means the client's immediate openRun
    # finds execution_mode, so the HUD shows the real live/fake posture DURING the
    # run (the run-detail execution_mode is read from this file), not only after it
    # completes. Previously it was written in the launcher thread, which raced the
    # client's openRun → the HUD was stuck on SIMULATION for the whole live run.
    artifact = build_resolved_profile_artifact(
        profile,
        run_id,
        execution_mode="live" if is_live else "fake",
        live_api="used" if is_live else "not_used",
    )
    (run_dir / "resolved-profile.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    def _profile_launcher(rid: str, rdir: Path, base: RunLauncher = base) -> int:
        for seat_id in human_seats:
            state.participant_controller.configure_human_seat(rid, seat_id)
        return base(rid, rdir)

    payload: dict[str, object] = {
        "run_id": run_id,
        "profile_name": profile["name"],
        "mode": plr["mode"],
        "status": "queued",
    }
    if human_seats:
        payload["participant"] = {"seat_id": human_seats[0]}
    return ("launch", run_id, run_dir, _profile_launcher, payload)
