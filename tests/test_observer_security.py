"""Unit tests for the observer security guard seam (SYS-C2 split).

These cover the previously-untestable internals behind ``_is_loopback`` /
``_reject_cross_origin``: hostname parsing edges and the combined guard
decision function. The HTTP-level behavior stays pinned by
``test_observer_server.py`` (the contract oracle).
"""

from __future__ import annotations

import unittest

from werewolf_eval.observer.security import (
    CROSS_ORIGIN_MESSAGE,
    _hostname_of,
    _is_loopback_hostname,
    evaluate_request_guards,
    is_loopback_client,
    is_same_origin_local,
)


class HostnameOfTests(unittest.TestCase):
    def test_strips_scheme_port_and_path(self) -> None:
        self.assertEqual(_hostname_of("http://localhost:8765/path"), "localhost")

    def test_bare_host_port(self) -> None:
        self.assertEqual(_hostname_of("127.0.0.1:8765"), "127.0.0.1")

    def test_lowercases(self) -> None:
        self.assertEqual(_hostname_of("LOCALHOST:1"), "localhost")

    def test_bracketed_ipv6_with_port(self) -> None:
        self.assertEqual(_hostname_of("[::1]:8765"), "::1")

    def test_bare_ipv6_is_not_split_on_colon(self) -> None:
        self.assertEqual(_hostname_of("::1"), "::1")

    def test_userinfo_spoof_resolves_to_real_host(self) -> None:
        # http://127.0.0.1:8765@attacker.example.com -> the REAL host is after '@'
        self.assertEqual(
            _hostname_of("http://127.0.0.1:8765@attacker.example.com"),
            "attacker.example.com",
        )


class LoopbackHostnameTests(unittest.TestCase):
    def test_loopback_names_accepted(self) -> None:
        for value in ("localhost", "127.0.0.1:8765", "[::1]:1", "http://localhost"):
            self.assertTrue(_is_loopback_hostname(value), value)

    def test_non_loopback_rejected(self) -> None:
        self.assertFalse(_is_loopback_hostname("attacker.example.com:8765"))

    def test_loopback_prefix_subdomain_rejected(self) -> None:
        self.assertFalse(_is_loopback_hostname("127.0.0.1.attacker.example.com:8765"))


class LoopbackClientTests(unittest.TestCase):
    def test_ipv4_and_ipv6_loopback(self) -> None:
        self.assertTrue(is_loopback_client("127.0.0.1"))
        self.assertTrue(is_loopback_client("::1"))

    def test_remote_and_empty_rejected(self) -> None:
        self.assertFalse(is_loopback_client("192.168.1.5"))
        self.assertFalse(is_loopback_client(""))


class SameOriginLocalTests(unittest.TestCase):
    def test_no_headers_allowed(self) -> None:
        # Non-browser clients that omit Host/Origin are unaffected.
        self.assertTrue(is_same_origin_local(None))
        self.assertTrue(is_same_origin_local({}))

    def test_loopback_host_without_origin_allowed(self) -> None:
        self.assertTrue(is_same_origin_local({"Host": "127.0.0.1:8765"}))

    def test_loopback_host_and_origin_allowed(self) -> None:
        self.assertTrue(
            is_same_origin_local(
                {"Host": "localhost:8765", "Origin": "http://localhost:8765"}
            )
        )

    def test_dns_rebind_host_rejected(self) -> None:
        self.assertFalse(is_same_origin_local({"Host": "attacker.example.com:8765"}))

    def test_cross_origin_rejected(self) -> None:
        self.assertFalse(
            is_same_origin_local(
                {"Host": "127.0.0.1:8765", "Origin": "http://attacker.example.com"}
            )
        )

    def test_userinfo_origin_spoof_rejected(self) -> None:
        self.assertFalse(
            is_same_origin_local(
                {
                    "Host": "127.0.0.1:8765",
                    "Origin": "http://127.0.0.1:8765@attacker.example.com",
                }
            )
        )


class EvaluateRequestGuardsTests(unittest.TestCase):
    """Decision matrix for the combined guard. NOTE: the production guard matrix
    is asymmetric by design (some endpoints loopback-only, some same-origin-only);
    this function only ever applies what the caller asks for."""

    def test_no_guards_requested_passes(self) -> None:
        self.assertIsNone(
            evaluate_request_guards("203.0.113.9", {"Host": "evil.example.com"})
        )

    def test_loopback_gate_rejects_remote_peer_with_given_message(self) -> None:
        result = evaluate_request_guards(
            "203.0.113.9",
            {},
            loopback_message="credentials endpoint is loopback-only",
        )
        self.assertEqual(
            result, (403, "forbidden", "credentials endpoint is loopback-only")
        )

    def test_loopback_gate_passes_local_peer(self) -> None:
        self.assertIsNone(
            evaluate_request_guards(
                "127.0.0.1", {}, loopback_message="runs delete is loopback-only"
            )
        )

    def test_loopback_gate_checked_before_same_origin(self) -> None:
        # Both guards would reject; the loopback message must win (current
        # endpoint behavior: peer-IP gate runs first).
        result = evaluate_request_guards(
            "203.0.113.9",
            {"Host": "attacker.example.com"},
            loopback_message="runs delete is loopback-only",
            require_same_origin=True,
        )
        self.assertEqual(result, (403, "forbidden", "runs delete is loopback-only"))

    def test_same_origin_rejection_uses_canonical_message(self) -> None:
        result = evaluate_request_guards(
            "127.0.0.1",
            {"Host": "attacker.example.com:8765"},
            require_same_origin=True,
        )
        self.assertEqual(result, (403, "forbidden", CROSS_ORIGIN_MESSAGE))
        self.assertEqual(
            CROSS_ORIGIN_MESSAGE, "cross-origin or non-loopback Host rejected"
        )

    def test_same_origin_passes_loopback_browser(self) -> None:
        self.assertIsNone(
            evaluate_request_guards(
                "127.0.0.1",
                {"Host": "127.0.0.1:8765", "Origin": "http://127.0.0.1:8765"},
                require_same_origin=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
