import unittest
import os

from datetime import datetime
import json
from unittest.mock import patch

from types import SimpleNamespace

from env import _parse_target
from main import _name
from scheduler import _next_run
from env import parse_time as _parse_signin_time


class TestParseTarget(unittest.TestCase):
    def test_bare_username(self):
        self.assertEqual(_parse_target("username"), "username")

    def test_at_username(self):
        self.assertEqual(_parse_target("@username"), "username")

    def test_tme_url_username(self):
        self.assertEqual(_parse_target("t.me/username"), "username")

    def test_https_tme_url_username(self):
        self.assertEqual(_parse_target("https://t.me/username"), "username")

    def test_http_tme_url_username(self):
        self.assertEqual(_parse_target("http://t.me/username"), "username")

    def test_case_insensitive_prefix(self):
        self.assertEqual(_parse_target("HTTP://T.ME/UserName"), "UserName")

    def test_tme_url_with_at(self):
        self.assertEqual(_parse_target("https://t.me/@user"), "user")

    def test_positive_numeric_id(self):
        self.assertEqual(_parse_target("123"), 123)

    def test_negative_channel_id(self):
        self.assertEqual(_parse_target("-1001234567890"), -1001234567890)

    def test_tme_url_numeric_id(self):
        self.assertEqual(_parse_target("t.me/123"), 123)

    def test_at_numeric_id(self):
        self.assertEqual(_parse_target("@123"), 123)

    def test_whitespace_stripped(self):
        self.assertEqual(_parse_target("  @user  "), "user")

    def test_empty_string(self):
        self.assertEqual(_parse_target(""), "")


class TestName(unittest.TestCase):
    def test_username_wins(self):
        entity = SimpleNamespace(username="alice", title="G", first_name="A", id=1)
        self.assertEqual(_name(entity), "@alice")

    def test_title_fallback(self):
        entity = SimpleNamespace(title="My Channel", first_name="Alice", id=2)
        self.assertEqual(_name(entity), "My Channel")

    def test_first_name_fallback(self):
        entity = SimpleNamespace(first_name="Bob", id=3)
        self.assertEqual(_name(entity), "Bob")

    def test_id_fallback(self):
        entity = SimpleNamespace(id=42)
        self.assertEqual(_name(entity), "42")

    def test_username_present_empty_title(self):
        entity = SimpleNamespace(username="bot", title="", first_name="X", id=4)
        self.assertEqual(_name(entity), "@bot")

    def test_empty_title_falls_through_to_first_name(self):
        entity = SimpleNamespace(title="", first_name="Y", id=5)
        self.assertEqual(_name(entity), "Y")

    def test_none_username(self):
        entity = SimpleNamespace(first_name="Z", id=6)
        self.assertEqual(_name(entity), "Z")

    def test_plain_int_entity(self):
        self.assertEqual(_name(123), "123")


class TestScheduler(unittest.TestCase):
    def test_parse_signin_time(self):
        self.assertEqual(_parse_signin_time("08:30"), (8, 30))

    def test_parse_signin_time_rejects_bad_format(self):
        with self.assertRaises(ValueError):
            _parse_signin_time("8")

    def test_parse_signin_time_rejects_invalid_time(self):
        with self.assertRaises(ValueError):
            _parse_signin_time("24:00")

    def test_next_run_today(self):
        now = datetime(2026, 6, 6, 8, 0, 0)
        self.assertEqual(_next_run(now, 9, 30), datetime(2026, 6, 6, 9, 30, 0))

    def test_next_run_tomorrow(self):
        now = datetime(2026, 6, 6, 9, 30, 0)
        self.assertEqual(_next_run(now, 9, 30), datetime(2026, 6, 7, 9, 30, 0))


class TestEnvConfig(unittest.TestCase):
    @patch.dict(os.environ, {
        "SIGNIN_CONFIG": json.dumps([
            {"session": "alice", "target": "@bot1", "time": "08:30", "message": "msg1"},
            {"session": "bob", "target": "123456", "time": "12:00", "message": "msg2"}
        ])
    })
    def test_load_tasks_success(self):
        from env import load_tasks
        tasks = load_tasks()
        self.assertEqual(len(tasks), 2)

        self.assertEqual(tasks[0]["session"], "alice")
        self.assertTrue(tasks[0]["session_path"].endswith("alice"))
        self.assertEqual(tasks[0]["target"], "@bot1")
        self.assertEqual(tasks[0]["parsed_target"], "bot1")
        self.assertEqual(tasks[0]["time"], "08:30")
        self.assertEqual(tasks[0]["message"], "msg1")

        self.assertEqual(tasks[1]["session"], "bob")
        self.assertTrue(tasks[1]["session_path"].endswith("bob"))
        self.assertEqual(tasks[1]["target"], "123456")
        self.assertEqual(tasks[1]["parsed_target"], 123456)
        self.assertEqual(tasks[1]["time"], "12:00")
        self.assertEqual(tasks[1]["message"], "msg2")

    @patch.dict(os.environ, {"SIGNIN_CONFIG": "invalid-json"})
    def test_load_tasks_invalid_json(self):
        from env import load_tasks
        with self.assertRaises(ValueError) as ctx:
            load_tasks()
        self.assertIn("not a valid JSON", str(ctx.exception))

    @patch.dict(os.environ, {"SIGNIN_CONFIG": json.dumps([{"session": "alice", "target": "@bot1", "time": "08:30"}])})
    def test_load_tasks_missing_message(self):
        from env import load_tasks
        with self.assertRaises(ValueError) as ctx:
            load_tasks()
        self.assertIn("missing required field 'message'", str(ctx.exception))

    @patch.dict(os.environ, {"SIGNIN_CONFIG": json.dumps([{"target": "@bot1", "time": "08:30", "message": "msg"}])})
    def test_load_tasks_missing_session(self):
        from env import load_tasks
        with self.assertRaises(ValueError) as ctx:
            load_tasks()
        self.assertIn("missing required field 'session'", str(ctx.exception))

    @patch.dict(os.environ, {"SIGNIN_CONFIG": json.dumps([{"session": "alice", "target": "@bot1", "time": "25:00", "message": "msg"}])})
    def test_load_tasks_invalid_time(self):
        from env import load_tasks
        with self.assertRaises(ValueError) as ctx:
            load_tasks()
        self.assertIn("valid 24-hour time", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
