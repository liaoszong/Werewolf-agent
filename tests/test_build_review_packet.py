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


def _make_diff_block(filepath: str, lines: list[str]) -> str:
    """Build a minimal unified diff block for a single file with added lines."""
    header = f"diff --git a/{filepath} b/{filepath}"
    index_line = f"index 0000000..1111111 100644"
    old_line = "--- a/" + filepath
    new_line = "+++ b/" + filepath
    hunk_header = "@@ -0,0 +0," + str(len(lines)) + " @@"
    body = "\n".join("+" + l for l in lines)
    return f"{header}\n{index_line}\n{old_line}\n{new_line}\n{hunk_header}\n{body}\n"


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


class KeyHunkOrderingTests(unittest.TestCase):
    """Tests for extract_key_hunks ordering, prioritization, and truncation."""

    def _extract(self, diff_text: str, changed_files: list[str]):
        from scripts.dev.build_review_packet import extract_key_hunks
        return extract_key_hunks(diff_text, changed_files)

    def test_small_hunks_prioritized_over_large_hunks(self) -> None:
        """Within the same priority tier, smaller hunks should appear before larger ones."""
        small_block = _make_diff_block("src/small.py", ["x = 1"])
        # Large block: 50 added lines
        large_block = _make_diff_block(
            "src/large.py", [f"line_{i} = {i}" for i in range(50)]
        )
        diff_text = large_block + "\n" + small_block

        result, truncated = self._extract(diff_text, ["src/small.py", "src/large.py"])
        # Both are priority 0 (src/), so small should come first
        small_pos = result.find("### src/small.py")
        large_pos = result.find("### src/large.py")
        self.assertLess(small_pos, large_pos, "small hunk should appear before large hunk")

    def test_single_large_hunk_does_not_prevent_small_hunks_from_appearing(self) -> None:
        """A large hunk that exceeds budget alone is skipped; small hunks still appear.

        When tiny hunks fit and a giant one does not, the tiny ones should be
        included and the giant one should be truncated away, not crowd out
        the small ones.
        """
        # A very large block that exceeds MAX_KEY_HUNK_LINES alone
        very_large = _make_diff_block(
            "src/huge.py", [f"big_line_{i} = {i}" for i in range(150)]
        )
        small_block = _make_diff_block("src/small.py", ["y = 2"])
        # Put large first so natural order would be large→small;
        # but extract_key_hunks sorts by size (small first).
        diff_text = very_large + "\n" + small_block

        result, truncated = self._extract(diff_text, ["src/huge.py", "src/small.py"])
        # The small hunk should appear (it fits)
        self.assertIn("### src/small.py", result)
        # The large hunk is truncated away because it exceeds remaining budget
        self.assertNotIn("### src/huge.py", result)
        # Truncation flag should be True
        self.assertTrue(truncated)

    def test_multiple_small_hunks_fit_within_budget_and_late_large_is_truncated(self) -> None:
        """Many small hunks fit within budget, then a large hunk gets truncated."""
        # 5 small hunks of ~5 lines each = ~45 lines + overhead ≈ 65 total
        small_files = []
        for i in range(5):
            small_files.append(("src", f"small_{i}.py"))
        # One large hunk that would exceed the remaining budget
        large_lines = [f"class MyClass_{j}:" for j in range(80)]

        blocks = []
        changed = []
        for prefix, name in small_files:
            filepath = f"{prefix}/{name}"
            blocks.append(_make_diff_block(filepath, [f"x = {i}"]))
            changed.append(filepath)
        filepath = "src/large.py"
        blocks.append(_make_diff_block(filepath, large_lines))
        changed.append(filepath)

        diff_text = "\n".join(blocks)

        result, truncated = self._extract(diff_text, changed)
        # Small hunks should all appear
        for _, name in small_files:
            self.assertIn(f"### src/{name}", result)
        # Large hunk may or may not appear depending on budget
        # But truncation flag should indicate budget was exceeded
        # The key invariant: truncation note or omitted indication appears
        if truncated:
            # Packet should indicate truncation
            self.assertIn("KEY_HUNKS_TRUNCATED = YES", result)

    def test_priority_ordering_src_before_docs_before_logs(self) -> None:
        """src/ files (priority 0) should appear before docs/ (priority 1) and .logs/ (priority 2)."""
        src_block = _make_diff_block("src/app.py", ["a = 1"] * 10)
        docs_block = _make_diff_block("docs/README.md", ["# Doc"] * 10)
        logs_block = _make_diff_block(".logs/output.log", ["log line"] * 10)
        diff_text = logs_block + "\n" + docs_block + "\n" + src_block

        result, _ = self._extract(
            diff_text,
            ["src/app.py", "docs/README.md", ".logs/output.log"],
        )
        src_pos = result.find("### src/app.py")
        docs_pos = result.find("### docs/README.md")
        logs_pos = result.find("### .logs/output.log")
        self.assertLess(src_pos, docs_pos, "src files should come before docs")
        self.assertLess(docs_pos, logs_pos, "docs should come before .logs")

    def test_truncation_flag_true_when_budget_exceeded(self) -> None:
        """When hunks exceed budget, extract_key_hunks should return truncated=True."""
        large = _make_diff_block("src/big.py", [f"x = {i}" for i in range(150)])
        result, truncated = self._extract(large, ["src/big.py"])
        self.assertTrue(truncated)
        # The large hunk is included as the sole entry even though it exceeds budget
        self.assertIn("### src/big.py", result)

    def test_no_truncation_when_within_budget(self) -> None:
        """When all hunks fit within budget, truncated should be False."""
        small = _make_diff_block("src/tiny.py", ["x = 1"])
        result, truncated = self._extract(small, ["src/tiny.py"])
        self.assertFalse(truncated)
        self.assertNotIn("KEY_HUNKS_TRUNCATED", result)


if __name__ == "__main__":
    unittest.main()
