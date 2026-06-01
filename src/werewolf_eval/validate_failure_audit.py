from __future__ import annotations

import argparse

from werewolf_eval.failure_audit import load_failure_audit
from werewolf_eval.game_log import load_game_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Werewolf-agent Failure Audit JSON file.")
    parser.add_argument("failure_audit_path", help="Path to Failure Audit JSON")
    parser.add_argument("game_log_path", help="Path to matching Game Log JSON")
    args = parser.parse_args()

    game = load_game_log(args.game_log_path)
    audit = load_failure_audit(args.failure_audit_path, game)

    print(f"validated failure_audit game_id={audit.game_id}")
    print(f"failures={len(audit.failures)}")
    print(f"source_label={audit.source_label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
