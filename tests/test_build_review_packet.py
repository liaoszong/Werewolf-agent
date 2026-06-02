from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dev" / "build_review_packet.py"


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


class BuildReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        run(["git", "init"], self.repo)
        run(["git", "config", "user.email", "test@example.com"], self.repo)
        run(["git", "config", "user.name", "Test User"], self.repo)
        (self.repo / "sample.py").write_text('print("base")\n', encoding="utf-8")
        run(["git", "add", "sample.py"], self.repo)
        run(["git", "commit", "-m", "base"], self.repo)
        run(["git", "branch", "-M", "main"], self.repo)
        (self.repo / "sample.py").write_text('import os\nprint("changed")\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _minimal_args(self):
        return {
            "base": "main",
            "branch": "main",
            "changed_files": ["sample.py"],
            "diff_stat": "sample.py | 2 +-",
            "diff_check": "(clean)",
            "diff_text": "",
            "shortstat": "1 file changed, 1 insertion(+), 1 deletion(-)",
            "allowlist": ["sample.py"],
            "test_commands": [],
            "acceptance_items": [],
        }

    def test_packet_too_large_reported_when_acceptance_pushes_over_300_lines(self):
        from scripts.dev.build_review_packet import build_packet

        args = self._minimal_args()
        # Each acceptance item renders 2 lines (1 evidence map row + 1 checklist row).
        # Minimal packet with 0 items is ~41 sections. With N items,
        # pre_lines ≈ 41 + 2N. N=130 → ~301 pre-trigger lines > 300.
        args["acceptance_items"] = [
            f"item_{i:03d} | test_{i:03d} PASS | PASS" for i in range(130)
        ]

        packet = build_packet(**args)
        self.assertIn("PACKET_TOO_LARGE = YES", packet)
        self.assertIn("PACKET_TOO_LARGE=YES", packet)

    def test_packet_too_large_reported_when_trigger_section_pushes_over_300_lines(
        self,
    ):
        from scripts.dev.build_review_packet import build_packet

        args = self._minimal_args()
        # Pre-trigger body at ~291 lines (≤ 300).
        args["acceptance_items"] = [
            f"item_{i:03d} | test_{i:03d} PASS | PASS" for i in range(125)
        ]
        # Trigger section with 12 high_risk_file entries pushes final packet
        # to 291 + 4 (header) + 12 (triggers) = 307 > 300.
        args["changed_files"] = [
            "sample.py",
            *(f"docs/gold-game/file_{i:03d}.py" for i in range(12)),
        ]

        packet = build_packet(**args)
        self.assertIn("PACKET_TOO_LARGE = YES", packet)
        self.assertIn("PACKET_TOO_LARGE=YES", packet)
        for i in range(12):
            self.assertIn(
                f"high_risk_file=docs/gold-game/file_{i:03d}.py", packet
            )

    def test_packet_too_large_not_reported_when_under_300_lines(self):
        from scripts.dev.build_review_packet import build_packet

        args = self._minimal_args()
        args["acceptance_items"] = [
            "single item | test PASS | PASS"
        ]

        packet = build_packet(**args)
        self.assertIn("PACKET_TOO_LARGE = NO", packet)

    def test_packet_contains_required_sections(self):
        out = self.repo / ".logs" / "review" / "latest" / "review-packet.md"
        run(
            [sys.executable, str(SCRIPT), "--base", "main", "--out", str(out)],
            self.repo,
        )
        packet = out.read_text(encoding="utf-8")
        for heading in [
            "# Review Packet",
            "## Metadata",
            "## Changed Files",
            "## Diff Stat",
            "## Diff Check",
            "## Allowed Files Check",
            "## Forbidden Patterns Check",
            "## Dependency / Import Diff",
            "## Test Summary",
            "## Key Hunks",
            "## Evidence Map",
            "## Acceptance Checklist",
            "## Implementer Risk Notes",
            "## Review Trigger Result",
        ]:
            self.assertIn(heading, packet)
        self.assertIn("PACKET_TOO_LARGE = NO", packet)

    def test_packet_records_manual_allowlist_when_no_allowlist_is_provided(self):
        out = self.repo / ".logs" / "review" / "latest" / "review-packet.md"
        run(
            [sys.executable, str(SCRIPT), "--base", "main", "--out", str(out)],
            self.repo,
        )
        packet = out.read_text(encoding="utf-8")
        self.assertIn("ALLOWLIST_CHECK = MANUAL_REVIEW_REQUIRED", packet)

    def test_packet_marks_forbidden_pattern_hits(self):
        out = self.repo / ".logs" / "review" / "latest" / "review-packet.md"
        (self.repo / "sample.py").write_text(
            'provider = "demo"\nprint(provider)\n', encoding="utf-8"
        )
        run(
            [sys.executable, str(SCRIPT), "--base", "main", "--out", str(out)],
            self.repo,
        )
        packet = out.read_text(encoding="utf-8")
        self.assertIn("FORBIDDEN_PATTERN_SCAN = WARN", packet)
        self.assertIn("provider", packet)


if __name__ == "__main__":
    unittest.main()
