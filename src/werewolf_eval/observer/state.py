"""Shared observer-server state container (SYS-C2 split)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Callable

from werewolf_eval.credential_store import CredentialStore
from werewolf_eval.participant_controller import InMemoryParticipantActionController
from werewolf_eval.participant_protocol import ParticipantSession
from werewolf_eval.release_metadata import read_version

RunLauncher = Callable[[str, Path], int]


@dataclass
class ObserverServerState:
    runs_dir: Path
    launcher: RunLauncher
    profiles_dir: Path = field(default_factory=lambda: Path("profiles"))
    configs_dir: Path = field(default_factory=lambda: Path(".runs/user-configs"))
    run_status: dict[str, str] = field(default_factory=dict)
    run_errors: dict[str, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)
    # G3-1 live opt-in: ``live_enabled`` reflects ``--allow-live-api``.
    # B5 closeout: the deepseek-only env-key fallback has been retired.
    # Live launches now require a client-supplied credential for every provider
    # (including deepseek) via POST /api/credentials → CredentialStore.
    live_enabled: bool = False
    # P2-B-1 BYO-key: in-memory client credentials. env_key_available,
    # live_launcher, and the vestigial single-provider live_launcher_factory
    # (write-only — never read by the launch path) were all removed in B5 closeout.
    credential_store: CredentialStore = field(default_factory=CredentialStore)
    # P2-B-3/B-4: per-seat multi-provider launcher builder. Given the resolved
    # seats + a {provider: ProviderCredential} map, returns a RunLauncher that runs
    # the game with each seat on its own provider/model/persona. Injectable so
    # tests can pass a fake (no network); built with the server live limits in
    # create_observer_server.
    multi_provider_launcher_factory: Callable[..., RunLauncher] | None = None
    # P3-C-1b: fake profile launches with a human seat must use a profile-aware
    # emergent fake launcher (resolved roles + participant controller). Tests may
    # leave this unset to exercise dispatch with a tiny fake launcher.
    human_profile_fake_launcher_factory: Callable[..., RunLauncher] | None = None
    # R0 release metadata — populated from CLI args or sensible defaults.
    # instance_id is generated once per server start; owner_token comes from
    # --release-owner-token; release_version defaults to the VERSION file.
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    owner_token: str = ""
    release_version: str = field(default_factory=read_version)
    protocol_version: int = 1
    # P3-C participant sessions remain local-dev and in-memory. Action windows
    # are owned by the controller so route stubs and game-loop integration share
    # the same validation/idempotency semantics.
    participant_sessions: dict[str, ParticipantSession] = field(default_factory=dict)
    participant_controller: InMemoryParticipantActionController = field(
        default_factory=InMemoryParticipantActionController
    )
