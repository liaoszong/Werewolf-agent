import unittest

from werewolf_eval.participant_protocol import (
    ActionIdempotencyTracker,
    ActionWindow,
    ParticipantActionSubmission,
    ParticipantProtocolError,
    ParticipantSession,
    build_participant_error_envelope,
    parse_reconnect_cursor,
    validate_game_revision,
)


def _window(**overrides):
    values = {
        "action_window_id": "aw_0001",
        "run_id": "run_001",
        "seat_id": "p3",
        "phase": "day_discussion",
        "round": 1,
        "game_revision": 7,
        "opened_at_event_id": "evt_0042",
        "deadline_at": "2026-07-03T12:00:00Z",
        "allowed_actions": ("speech", "pass"),
        "required": False,
        "default_on_timeout": "pass",
        "status": "open",
        "reconnect_cursor": "event:42",
    }
    values.update(overrides)
    return ActionWindow(**values)


class ParticipantProtocolTests(unittest.TestCase):
    def test_session_perspective_is_derived_from_seat_id(self):
        session = ParticipantSession(
            run_id="run_001",
            seat_id="p4",
            participant_session_token="secret-token",
            issued_at="2026-07-03T10:00:00Z",
            expires_at="2026-07-04T10:00:00Z",
            last_seen_cursor="event:12",
        )

        self.assertEqual(session.perspective, "role:p4")
        self.assertEqual(session.to_payload()["perspective"], "role:p4")
        self.assertNotIn("last_seen_cursor", session.to_payload())
        self.assertEqual(session.to_payload()["reconnect_cursor"], "event:12")
        self.assertNotIn("participant_session_token", session.to_payload())
        self.assertEqual(
            session.to_payload(include_token=True)["participant_session_token"],
            "secret-token",
        )

    def test_invalid_seat_rejected(self):
        with self.assertRaises(ParticipantProtocolError) as ctx:
            ParticipantSession(
                run_id="run_001",
                seat_id="p7",
                participant_session_token="secret-token",
                issued_at="2026-07-03T10:00:00Z",
                expires_at="2026-07-04T10:00:00Z",
                last_seen_cursor="event:12",
            )

        self.assertEqual(ctx.exception.error_code, "invalid_payload")

    def test_token_not_leaked_in_repr_str_or_error_envelope(self):
        token = "very-secret-token"
        session = ParticipantSession(
            run_id="run_001",
            seat_id="p2",
            participant_session_token=token,
            issued_at="2026-07-03T10:00:00Z",
            expires_at="2026-07-04T10:00:00Z",
            last_seen_cursor="event:12",
        )
        envelope = build_participant_error_envelope(
            "invalid_payload",
            "Bad payload",
            run_id="run_001",
            seat_id="p2",
            details={
                "participant_session_token": token,
                "Authorization": f"Bearer {token}",
                "join_code": "local-dev-code",
                "safe": "value",
            },
        )

        rendered = repr(session) + str(session) + repr(envelope)
        self.assertNotIn(token, rendered)
        self.assertNotIn("local-dev-code", rendered)
        self.assertNotIn("Authorization", repr(envelope))
        self.assertEqual(envelope["details"], {"safe": "value"})

    def test_reconnect_cursor_parse_and_order(self):
        older = parse_reconnect_cursor("event:9")
        newer = parse_reconnect_cursor("event:10")

        self.assertLess(older, newer)
        self.assertEqual(str(newer), "event:10")

        with self.assertRaises(ParticipantProtocolError):
            parse_reconnect_cursor("evt:10")

    def test_game_revision_validation_rejects_negative_and_non_int(self):
        self.assertEqual(validate_game_revision(0), 0)
        self.assertEqual(validate_game_revision(11), 11)

        for value in (-1, "1", 1.2, True):
            with self.subTest(value=value):
                with self.assertRaises(ParticipantProtocolError):
                    validate_game_revision(value)

    def test_text_cap_rejects_over_2000_and_envelope_includes_cap(self):
        with self.assertRaises(ParticipantProtocolError) as ctx:
            ParticipantActionSubmission(
                action_window_id="aw_0001",
                game_revision=7,
                idempotency_key="idem-1",
                action_type="speech",
                payload={"text": "x" * 2001},
            )

        envelope = ctx.exception.to_envelope()
        self.assertEqual(envelope["error_code"], "invalid_payload")
        self.assertEqual(envelope["details"]["text_cap"], 2000)

    def test_idempotency_same_key_same_payload_returns_original_result(self):
        tracker = ActionIdempotencyTracker()
        submission = ParticipantActionSubmission(
            action_window_id="aw_0001",
            game_revision=7,
            idempotency_key="idem-1",
            action_type="speech",
            payload={"text": "I think p5 is suspicious"},
        )
        original = {
            "schema_version": "p3c.action_submit_result.v1",
            "status": "accepted",
            "accepted_event_id": "evt_0043",
        }

        stored = tracker.record_or_duplicate(submission, original)
        duplicate = tracker.record_or_duplicate(
            submission,
            {"status": "accepted", "accepted_event_id": "evt_SHOULD_NOT_WIN"},
        )

        self.assertEqual(stored.status, "stored")
        self.assertEqual(duplicate.status, "duplicate")
        self.assertEqual(duplicate.result, original)

    def test_idempotency_same_key_different_payload_raises_conflict(self):
        tracker = ActionIdempotencyTracker()
        first = ParticipantActionSubmission(
            action_window_id="aw_0001",
            game_revision=7,
            idempotency_key="idem-1",
            action_type="speech",
            payload={"text": "first"},
        )
        second = ParticipantActionSubmission(
            action_window_id="aw_0001",
            game_revision=7,
            idempotency_key="idem-1",
            action_type="speech",
            payload={"text": "second"},
        )
        tracker.record_or_duplicate(first, {"status": "accepted"})

        with self.assertRaises(ParticipantProtocolError) as ctx:
            tracker.record_or_duplicate(second, {"status": "accepted"})

        self.assertEqual(ctx.exception.error_code, "idempotency_conflict")

    def test_closed_window_rejects_action(self):
        window = _window(status="accepted")
        submission = ParticipantActionSubmission(
            action_window_id="aw_0001",
            game_revision=7,
            idempotency_key="idem-1",
            action_type="speech",
            payload={"text": "too late"},
        )

        with self.assertRaises(ParticipantProtocolError) as ctx:
            from werewolf_eval.participant_protocol import validate_submission_for_window

            validate_submission_for_window(submission, window)

        envelope = ctx.exception.to_envelope()
        self.assertEqual(envelope["error_code"], "action_window_closed")
        self.assertEqual(envelope["run_id"], "run_001")
        self.assertEqual(envelope["seat_id"], "p3")
        self.assertEqual(envelope["action_window_id"], "aw_0001")

    def test_missing_session_error_has_no_run_seat_or_window_fields(self):
        envelope = build_participant_error_envelope(
            "missing_or_invalid_session",
            "Missing participant session",
        )

        self.assertEqual(envelope["schema_version"], "p3c.error.v1")
        self.assertEqual(envelope["error_code"], "missing_or_invalid_session")
        self.assertNotIn("run_id", envelope)
        self.assertNotIn("seat_id", envelope)
        self.assertNotIn("action_window_id", envelope)

    def test_stale_revision_error_includes_current_game_revision(self):
        window = _window(game_revision=9, reconnect_cursor="event:50")
        submission = ParticipantActionSubmission(
            action_window_id="aw_0001",
            game_revision=7,
            idempotency_key="idem-1",
            action_type="speech",
            payload={"text": "stale"},
        )

        with self.assertRaises(ParticipantProtocolError) as ctx:
            from werewolf_eval.participant_protocol import validate_submission_for_window

            validate_submission_for_window(submission, window)

        envelope = ctx.exception.to_envelope()
        self.assertEqual(envelope["error_code"], "stale_game_revision")
        self.assertEqual(envelope["current_game_revision"], 9)
        self.assertEqual(envelope["reconnect_cursor"], "event:50")

    def test_role_action_payloads_validate_target_seats(self):
        for action_type in (
            "werewolf_kill",
            "seer_check",
            "witch_save",
            "witch_poison",
            "guard_protect",
            "hunter_shoot",
        ):
            with self.subTest(action_type=action_type):
                submission = ParticipantActionSubmission(
                    action_window_id="aw_0001",
                    game_revision=7,
                    idempotency_key=f"idem-{action_type}",
                    action_type=action_type,
                    payload={"target": "p1"},
                )
                self.assertEqual(submission.payload, {"target": "p1"})

    def test_role_action_payloads_reject_bad_target(self):
        with self.assertRaises(ParticipantProtocolError) as ctx:
            ParticipantActionSubmission(
                action_window_id="aw_0001",
                game_revision=7,
                idempotency_key="idem-bad-seer",
                action_type="seer_check",
                payload={"target": "p9"},
            )

        self.assertEqual(ctx.exception.error_code, "invalid_payload")


if __name__ == "__main__":
    unittest.main()
