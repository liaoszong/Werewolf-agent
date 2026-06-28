"""Velopack bootstrapper runtime hook."""
from __future__ import annotations

_APP_RUN_CALLED = False


def run_velopack_app_once() -> None:
    """Run Velopack app hooks once, and only from the bootstrapper entry."""
    global _APP_RUN_CALLED
    if _APP_RUN_CALLED:
        return
    _APP_RUN_CALLED = True
    try:
        import velopack
    except ImportError:
        return
    velopack.App().set_auto_apply_on_startup(False).run()
