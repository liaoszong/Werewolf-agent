"""Unit tests for the declarative route table (SYS-C2 split).

The table IS the dispatch order: these tests pin pattern matching semantics
(literal-before-capture via declaration order, single-segment capture,
trailing-segment tolerance) and the per-method guard flags, which previously
lived as an if-chain inside do_GET/do_POST/do_DELETE.
"""

from __future__ import annotations

import unittest

from werewolf_eval.observer.routes import (
    DELETE_ROUTES,
    GET_ROUTES,
    POST_ROUTES,
    RUN_SUB_ROUTES,
    Route,
    match_route,
)


def _match(routes, segments):
    return match_route(routes, segments)


class MatchSemanticsTests(unittest.TestCase):
    def test_exact_match_and_capture(self) -> None:
        routes = (
            Route(("api", "profiles", "schema"), "schema"),
            Route(("api", "profiles", "{name}"), "detail"),
        )
        m = _match(routes, ["api", "profiles", "schema"])
        self.assertEqual(m[0].handler_name, "schema")
        m = _match(routes, ["api", "profiles", "mine"])
        self.assertEqual(m[0].handler_name, "detail")
        self.assertEqual(m[1], {"name": "mine"})

    def test_no_match_returns_none(self) -> None:
        routes = (Route(("health",), "health"),)
        self.assertIsNone(_match(routes, ["nope"]))
        self.assertIsNone(_match(routes, ["health", "extra"]))

    def test_trailing_segments_ignored_when_allowed(self) -> None:
        routes = (Route(("snapshots", "{name}"), "snap", allow_trailing=True),)
        m = _match(routes, ["snapshots", "s1", "junk", "more"])
        self.assertEqual(m[1], {"name": "s1"})
        # but the capture segment itself is still required
        self.assertIsNone(_match(routes, ["snapshots"]))

    def test_declaration_order_wins(self) -> None:
        routes = (
            Route(("a", "{x}"), "first"),
            Route(("a", "b"), "second"),
        )
        self.assertEqual(_match(routes, ["a", "b"])[0].handler_name, "first")


class GetTableTests(unittest.TestCase):
    def _handler_for(self, segments) -> str:
        m = _match(GET_ROUTES, segments)
        self.assertIsNotNone(m, f"no GET route for {segments}")
        return m[0].handler_name

    def test_core_get_endpoints(self) -> None:
        self.assertEqual(self._handler_for(["health"]), "_route_health")
        self.assertEqual(
            self._handler_for(["api", "runtime", "capabilities"]),
            "_route_capabilities",
        )
        self.assertEqual(self._handler_for(["api", "runs"]), "_route_runs_list")
        self.assertEqual(
            self._handler_for(["api", "profiles", "schema"]), "_route_profile_schema"
        )
        self.assertEqual(self._handler_for(["api", "profiles"]), "_route_profiles_list")
        self.assertEqual(
            self._handler_for(["api", "profiles", "mine"]), "_route_profile_detail"
        )
        self.assertEqual(
            self._handler_for(["api", "providers", "deepseek", "models"]),
            "_route_provider_models",
        )
        self.assertEqual(
            self._handler_for(["api", "runs", "r1", "participant", "state"]),
            "_route_participant_state",
        )
        self.assertEqual(
            self._handler_for(["api", "runs", "r1", "participant", "events"]),
            "_route_participant_events",
        )

    def test_schema_wins_over_profile_name_capture(self) -> None:
        m = _match(GET_ROUTES, ["api", "profiles", "schema"])
        self.assertEqual(m[0].handler_name, "_route_profile_schema")
        self.assertEqual(m[1], {})

    def test_run_scoped_group_takes_any_subpath(self) -> None:
        for segs in (
            ["api", "runs", "r1"],
            ["api", "runs", "r1", "events"],
            ["api", "runs", "r1", "snapshots", "s1", "extra"],
        ):
            m = _match(GET_ROUTES, segs)
            self.assertEqual(m[0].handler_name, "_route_run_scoped", segs)
            self.assertEqual(m[1], {"run_id": "r1"}, segs)

    def test_providers_models_is_loopback_only_without_same_origin(self) -> None:
        # Guard matrix is ASYMMETRIC by design — do not "fix" it.
        m = _match(GET_ROUTES, ["api", "providers", "deepseek", "models"])
        self.assertEqual(m[0].loopback_message, "providers endpoint is loopback-only")
        self.assertFalse(m[0].same_origin)


class RunSubTableTests(unittest.TestCase):
    def _handler_for(self, sub) -> str:
        m = _match(RUN_SUB_ROUTES, sub)
        self.assertIsNotNone(m, f"no run sub-route for {sub}")
        return m[0].handler_name

    def test_sub_endpoints(self) -> None:
        self.assertEqual(self._handler_for([]), "_route_run_detail")
        self.assertEqual(self._handler_for(["events"]), "_route_run_events")
        self.assertEqual(self._handler_for(["stream"]), "_route_run_stream")
        self.assertEqual(self._handler_for(["snapshots"]), "_route_run_snapshots")
        self.assertEqual(
            self._handler_for(["snapshots", "s1"]), "_route_run_snapshot_detail"
        )
        self.assertEqual(self._handler_for(["projection"]), "_route_run_projection")
        self.assertEqual(self._handler_for(["artifacts"]), "_route_run_artifacts")
        self.assertEqual(self._handler_for(["settlement"]), "_route_run_settlement")
        self.assertEqual(
            self._handler_for(["artifacts", "a.json"]), "_route_run_artifact_detail"
        )
        for alias in ("manifest", "provider-trace", "failure-audit"):
            self.assertEqual(
                self._handler_for([alias]), "_route_run_artifact_alias", alias
            )

    def test_unknown_subpath_has_no_route(self) -> None:
        self.assertIsNone(_match(RUN_SUB_ROUTES, ["bogus"]))


class PostDeleteTableTests(unittest.TestCase):
    def test_post_routes_and_guards(self) -> None:
        m = _match(POST_ROUTES, ["api", "credentials"])
        self.assertEqual(m[0].handler_name, "_route_credentials_post")
        self.assertEqual(m[0].loopback_message, "credentials endpoint is loopback-only")
        self.assertTrue(m[0].same_origin)

        m = _match(POST_ROUTES, ["api", "runs"])
        self.assertEqual(m[0].handler_name, "_route_runs_post")
        self.assertIsNone(m[0].loopback_message)  # cross-origin ONLY — asymmetric
        self.assertTrue(m[0].same_origin)

        m = _match(POST_ROUTES, ["api", "runs", "r1", "participants", "join"])
        self.assertEqual(m[0].handler_name, "_route_participants_join")
        self.assertIsNone(m[0].loopback_message)
        self.assertFalse(m[0].same_origin)

        m = _match(POST_ROUTES, ["api", "runs", "r1", "participant", "actions"])
        self.assertEqual(m[0].handler_name, "_route_participant_actions")
        self.assertIsNone(m[0].loopback_message)
        self.assertFalse(m[0].same_origin)

        m = _match(POST_ROUTES, ["api", "profiles", "validate"])
        self.assertEqual(m[0].handler_name, "_route_profile_validate")
        self.assertIsNone(m[0].loopback_message)
        self.assertFalse(m[0].same_origin)

    def test_delete_routes_and_guards(self) -> None:
        m = _match(DELETE_ROUTES, ["api", "credentials", "deepseek"])
        self.assertEqual(m[0].handler_name, "_route_credentials_delete")
        self.assertEqual(m[0].loopback_message, "credentials endpoint is loopback-only")
        self.assertTrue(m[0].same_origin)

        m = _match(DELETE_ROUTES, ["api", "runs", "r1"])
        self.assertEqual(m[0].handler_name, "_route_runs_delete")
        # "runs delete is loopback-only" — verbatim, no word "endpoint"
        self.assertEqual(m[0].loopback_message, "runs delete is loopback-only")
        self.assertTrue(m[0].same_origin)


class FacadeParityTests(unittest.TestCase):
    """The 25-name import surface of ``werewolf_eval.observer_server`` is a
    frozen contract: do-not-touch test files and ``run_observer_server`` import
    these names (public AND underscore-private) from the facade. Pin every one;
    extend this list when adding names, never prune it."""

    FACADE_NAMES = (
        "ObserverRequestHandler",
        "ObserverServerState",
        "RunLauncher",
        "create_observer_server",
        "default_fake_launcher",
        "_CREDENTIAL_PROVIDERS",
        "_LOOPBACK_HOSTNAMES",
        "_PROFILE_NAME_RE",
        "_build_capabilities_payload",
        "_check_live_capability",
        "_check_live_profile_shape",
        "_credentials_delete_result",
        "_credentials_post_result",
        "_hostname_of",
        "_is_loopback_hostname",
        "_map_launcher_exit_reason",
        "_provider_live_posture",
        "_provider_models_result",
        "_read_events_jsonl_safe",
        "_read_execution_mode",
        "_resolve_live_launcher_for_launch",
        "_run_delete_result",
        "_sanitize_launcher_error",
        "_schema_payload",
        "_seed_default_profile",
    )

    def test_all_25_names_importable_from_facade(self) -> None:
        import werewolf_eval.observer_server as facade

        self.assertEqual(len(self.FACADE_NAMES), 25)
        for name in self.FACADE_NAMES:
            self.assertTrue(
                hasattr(facade, name), f"facade lost re-export: {name}"
            )


if __name__ == "__main__":
    unittest.main()
