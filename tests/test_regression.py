"""Regression tests for pure-function behavior in config and main modules.

Locks behaviour before AI slop cleanup.  No dependencies beyond stdlib.
Run:  python -m unittest discover -s tests
"""

import unittest
from types import SimpleNamespace

from config import _parse_target
from main import _name


class TestParseTarget(unittest.TestCase):
    """Cover every normalisation path in config._parse_target."""

    # -- username forms --------------------------------------------------

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
        """Prefix matching is case-insensitive; username case is preserved."""
        self.assertEqual(_parse_target("HTTP://T.ME/UserName"), "UserName")

    def test_tme_url_with_at(self):
        self.assertEqual(_parse_target("https://t.me/@user"), "user")

    # -- numeric id forms ------------------------------------------------

    def test_positive_numeric_id(self):
        self.assertEqual(_parse_target("123"), 123)

    def test_negative_channel_id(self):
        self.assertEqual(_parse_target("-1001234567890"), -1001234567890)

    def test_tme_url_numeric_id(self):
        self.assertEqual(_parse_target("t.me/123"), 123)

    def test_at_numeric_id(self):
        self.assertEqual(_parse_target("@123"), 123)

    # -- edge cases ------------------------------------------------------

    def test_whitespace_stripped(self):
        self.assertEqual(_parse_target("  @user  "), "user")

    def test_empty_string(self):
        self.assertEqual(_parse_target(""), "")


class TestName(unittest.TestCase):
    """Cover every fallback path in main._name."""

    # -- priority: username > title > first_name > id --------------------

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

    # -- edge cases ------------------------------------------------------

    def test_username_present_empty_title(self):
        """Username still wins when title is present but empty."""
        entity = SimpleNamespace(username="bot", title="", first_name="X", id=4)
        self.assertEqual(_name(entity), "@bot")

    def test_empty_title_falls_through_to_first_name(self):
        """Empty-string title is falsy in or-chain, so first_name is used."""
        entity = SimpleNamespace(title="", first_name="Y", id=5)
        self.assertEqual(_name(entity), "Y")

    def test_none_username(self):
        """getattr returns None when attribute absent."""
        entity = SimpleNamespace(first_name="Z", id=6)
        self.assertEqual(_name(entity), "Z")

    def test_plain_int_entity(self):
        """When entity is a bare int _name falls back to str(id)."""
        self.assertEqual(_name(123), "123")


if __name__ == "__main__":
    unittest.main()
