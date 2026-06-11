import os
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from werewolf_eval.artifacts import collect_provider_trace, write_json
from werewolf_eval.provider_agent import ProviderAgent


@dataclass(frozen=True)
class _Item:
    request_id: str


class _FakeProvider:
    def __init__(self, requests=(), responses=()):
        self.requests = list(requests)
        self.responses = list(responses)


def _agent(seat, requests=(), responses=()):
    return ProviderAgent(seat, _FakeProvider(requests, responses))


class WriteJsonTests(unittest.TestCase):
    def test_writes_utf8_json_with_trailing_newline_and_parents(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "dir" / "artifact.json"
            write_json(target, {"name": "狼人", "n": 1})
            raw = target.read_bytes()
            # 契约保真:历史 _write_json 用文本模式 write_text(newline 翻译随平台),
            # Windows 下落盘即 CRLF;搬移保留该行为,不收紧为 LF。
            expected = '{\n  "name": "狼人",\n  "n": 1\n}\n'.replace("\n", os.linesep)
            self.assertEqual(raw, expected.encode("utf-8"))

    def test_accepts_str_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = str(Path(tmp) / "a" / "b.json")
            write_json(target, [])
            self.assertEqual(Path(target).read_bytes(), ("[]" + os.linesep).encode("utf-8"))


class CollectProviderTraceTests(unittest.TestCase):
    def test_dedups_by_request_id_across_agents_preserving_order(self):
        shared = _Item("dup")
        a1 = _agent("p1", requests=[_Item("r1"), shared], responses=[_Item("r1")])
        a2 = _agent("p2", requests=[shared, _Item("r2")], responses=[_Item("r2")])
        trace = collect_provider_trace("g1", [a1, a2], provider_name="x", source_label="[x]")
        self.assertEqual([r.request_id for r in trace.requests], ["r1", "dup", "r2"])
        self.assertEqual([r.request_id for r in trace.responses], ["r1", "r2"])

    def test_dedup_false_preserves_duplicates(self):
        # run_fake_provider_game 历史无去重行为的保真开关(漂移按用户裁决原样保留)
        shared = _Item("dup")
        a1 = _agent("p1", requests=[shared])
        a2 = _agent("p2", requests=[shared])
        trace = collect_provider_trace(
            "g1", [a1, a2], provider_name="x", source_label="[x]", dedup=False
        )
        self.assertEqual([r.request_id for r in trace.requests], ["dup", "dup"])

    def test_non_provider_agents_filtered_and_missing_attrs_tolerated(self):
        bare = ProviderAgent("p9", object())
        trace = collect_provider_trace(
            "g1",
            [object(), bare, _agent("p1", requests=[_Item("r1")])],
            provider_name="x",
            source_label="[x]",
        )
        self.assertEqual([r.request_id for r in trace.requests], ["r1"])

    def test_metadata_and_failures_passthrough(self):
        failures = []
        trace = collect_provider_trace(
            "g7", [], provider_name="deepseek", source_label="[live]", failures=failures
        )
        self.assertEqual(trace.game_id, "g7")
        self.assertEqual(trace.provider_name, "deepseek")
        self.assertEqual(trace.source_label, "[live]")
        self.assertIs(trace.failures, failures)
        trace2 = collect_provider_trace("g7", [], provider_name="d", source_label="[l]")
        self.assertEqual(trace2.failures, [])


if __name__ == "__main__":
    unittest.main()
