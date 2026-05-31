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
