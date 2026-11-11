"""Protocol boundary checks, independent of the participant's strategy."""

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import create_router
from models import GameEndRequest, GameStartRequest


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(create_router("test-token"))
        self.client = TestClient(app)
        self.auth = {"Authorization": "Bearer test-token"}
        self.ids = {
            "protocol": "poker-bot.v2",
            "match_id": "m-test",
            "table_id": "t-test",
            "entrant_id": "e-test",
        }
        self.start = {
            **self.ids,
            "starting_stack": 20000,
            "blinds": {"small_blind": 100, "big_blind": 200, "big_blind_ante": 0},
        }
        self.end = {
            **self.ids,
            "status": "completed",
            "standings": [{"entrant_id": "e-test", "position": 1, "final_stack": 40000}],
        }
        self.ack = {key: self.ids[key] for key in ("protocol", "match_id", "entrant_id")}

    def test_all_protected_routes_require_token(self):
        for route in ("/verify", "/action", "/game/start", "/game/end"):
            for header in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": "Basic test-token"}):
                with self.subTest(route=route, header=header):
                    response = self.client.post("/v1" + route, json={}, headers=header)
                    self.assertEqual(response.status_code, 401)

    def test_lifecycle_dispatch_and_acknowledgement(self):
        cases = (
            ("start", self.start, "on_game_start", GameStartRequest),
            ("end", self.end, "on_game_end", GameEndRequest),
        )
        for event, payload, hook, model in cases:
            with self.subTest(event=event), patch("bot." + hook) as handler:
                response = self.client.post("/v1/game/" + event, json=payload, headers=self.auth)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), self.ack)
                self.assertTrue(response.headers["content-type"].startswith("application/json"))
                handler.assert_called_once_with(model.model_validate(payload))

    def test_invalid_lifecycle_requests_do_not_reach_hooks(self):
        cases = (
            ("start", {**self.start, "protocol": "poker-bot.v1"}),
            ("start", {**self.start, "starting_stack": 0}),
            ("start", {**self.start, "blinds": {}}),
            ("end", {**self.end, "status": "running"}),
            ("end", {**self.end, "standings": [{"entrant_id": "e-test", "position": 0, "final_stack": -1}]}),
            ("end", {key: value for key, value in self.end.items() if key != "match_id"}),
        )
        for event, payload in cases:
            with self.subTest(event=event, payload=payload), patch("bot.on_game_" + event) as hook:
                response = self.client.post("/v1/game/" + event, json=payload, headers=self.auth)
                self.assertEqual(response.status_code, 422)
                hook.assert_not_called()

    def test_default_hooks_allow_end_without_start_and_repeated_events(self):
        for payload in (self.end, {**self.ids, "status": "cancelled"}):
            for _ in range(2):
                self.assertEqual(self.client.post("/v1/game/end", json=payload, headers=self.auth).json(), self.ack)
        for _ in range(2):
            self.assertEqual(self.client.post("/v1/game/start", json=self.start, headers=self.auth).json(), self.ack)

    def test_connection_routes_preserve_responses(self):
        self.assertEqual(self.client.get("/v1/health").json(), {"protocol": "poker-bot.v2", "status": "ready"})
        payload = {"protocol": "poker-bot.v2", "challenge": "unchanged-challenge"}
        response = self.client.post("/v1/verify", json=payload, headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)

    def test_action_preserves_decision_identifiers_and_default_strategy(self):
        payload = {
            "protocol": "poker-bot.v2",
            "match_id": "m-test",
            "table_id": "t-test",
            "hand_id": "h-test",
            "decision_id": "d-test",
            "table_version": 7,
            "deadline_at": "2026-11-11T23:00:00Z",
            "table": {
                "street": "preflop", "button_seat": 0,
                "blinds": self.start["blinds"], "seats": [], "pot": 300,
            },
            "player": {"seat": 0, "stack": 19800, "committed_this_street": 200, "hole_cards": ["As", "Kd"]},
        }
        for actions, expected in ((["fold", "call", "check"], "check"), (["fold", "call"], "call"), (["fold"], "fold")):
            with self.subTest(actions=actions):
                response = self.client.post("/v1/action", json={**payload, "legal_actions": [{"action": action} for action in actions]}, headers=self.auth)
                self.assertEqual(response.status_code, 200)
                expected_response = {key: payload[key] for key in ("protocol", "match_id", "table_id", "hand_id", "decision_id", "table_version")}
                self.assertEqual(response.json(), {**expected_response, "action": expected, "amount_to": None})


if __name__ == "__main__":
    unittest.main()
