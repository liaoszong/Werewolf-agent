"""Shared observer-server state container (SYS-C2 split)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Callable

from werewolf_eval.credential_store import CredentialStore

RunLauncher = Callable[[str, Path], int]


@dataclass
class ObserverServerState:
    runs_dir: Path
    launcher: RunLauncher
    profiles_dir: Path = field(default_factory=lambda: Path("profiles"))
    run_status: dict[str, str] = field(default_factory=dict)
    run_errors: dict[str, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)
    # G3-1 live opt-in: ``live_enabled`` reflects ``--allow-live-api``.
    # B5 closeout: the deepseek-only env-key fallback has been retired.
    # Live launches now require a client-supplied credential for every provider
    # (including deepseek) via POST /api/credentials → CredentialStore.
    live_enabled: bool = False
    # P2-B-1 BYO-key: in-memory client credentials + a per-launch live launcher
    # factory (built from a key at launch). env_key_available and live_launcher
    # (the old env-key back-compat hooks) were removed in B5 closeout.
    credential_store: CredentialStore = field(default_factory=CredentialStore)
    live_launcher_factory: Callable[..., RunLauncher] | None = None
    # P2-B-3/B-4: per-seat multi-provider launcher builder. Given the resolved
    # seats + a {provider: ProviderCredential} map, returns a RunLauncher that runs
    # the game with each seat on its own provider/model/persona. Injectable so
    # tests can pass a fake (no network); built with the server live limits in
    # create_observer_server.
    multi_provider_launcher_factory: Callable[..., RunLauncher] | None = None
