"""Tests for the hippo UserPromptSubmit cache wrapper.

Run: python -m unittest discover -s scripts/hooks/test -p "test_*.py"
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hippo_context_cached as hook  # noqa: E402


def payload(context: str) -> str:
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": context}})


def context_of(raw: str) -> str:
    return json.loads(raw)["hookSpecificOutput"]["additionalContext"]


SNAPSHOT = "## Active Task Snapshot\n\n- Task: something\n- Status: active\n\n"
MEMORY = "## Project Memory (2 entries, 40 tokens)\n\n- **[verified] a thing**\n"


class StripSnapshot(unittest.TestCase):
    def test_drops_the_snapshot_and_keeps_the_memory(self):
        out = hook.strip_snapshot(payload(SNAPSHOT + MEMORY))
        self.assertEqual(context_of(out), MEMORY)

    def test_is_idempotent(self):
        once = hook.strip_snapshot(payload(SNAPSHOT + MEMORY))
        self.assertEqual(hook.strip_snapshot(once), once)

    def test_keeps_the_event_name(self):
        out = json.loads(hook.strip_snapshot(payload(SNAPSHOT + MEMORY)))
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")

    def test_payload_with_no_snapshot_is_unchanged(self):
        raw = payload(MEMORY)
        self.assertEqual(hook.strip_snapshot(raw), raw)

    def test_payload_with_no_memory_heading_is_unchanged(self):
        raw = payload(SNAPSHOT)
        self.assertEqual(hook.strip_snapshot(raw), raw)

    def test_non_json_passes_through(self):
        self.assertEqual(hook.strip_snapshot("not json at all"), "not json at all")

    def test_unexpected_shape_passes_through(self):
        raw = json.dumps({"somethingElse": 1})
        self.assertEqual(hook.strip_snapshot(raw), raw)

    def test_null_context_passes_through(self):
        raw = json.dumps({"hookSpecificOutput": {"additionalContext": None}})
        self.assertEqual(hook.strip_snapshot(raw), raw)


class RefreshLock(unittest.TestCase):
    """Two concurrent refreshes deadlock SQLite, so the lock cannot be per cwd."""

    def test_one_lock_serves_every_working_directory(self):
        self.assertEqual(hook.lock_file(), hook.CACHE_DIR / "refresh.lock")

    def test_lock_is_not_derived_from_the_cwd(self):
        a = hook.cache_file("C:/one").with_suffix(".lock")
        b = hook.cache_file("C:/two").with_suffix(".lock")
        self.assertNotEqual(a, b)
        self.assertNotIn(hook.lock_file(), (a, b))

    def test_a_stale_lock_expires(self):
        lock = hook.CACHE_DIR / "expired.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("1", encoding="utf-8")
        import os
        import time
        old = time.time() - hook.LOCK_TTL - 1
        os.utime(lock, (old, old))
        try:
            self.assertFalse(hook.refresh_running(lock))
        finally:
            lock.unlink()

    def test_a_fresh_lock_blocks(self):
        lock = hook.CACHE_DIR / "fresh.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.write_text("1", encoding="utf-8")
        try:
            self.assertTrue(hook.refresh_running(lock))
        finally:
            lock.unlink()

    def test_a_missing_lock_does_not_block(self):
        self.assertFalse(hook.refresh_running(hook.CACHE_DIR / "no-such.lock"))


class CacheFile(unittest.TestCase):
    def test_the_name_is_the_hash_of_the_cwd_string(self):
        self.assertEqual(hook.cache_file("C:/Users/skf_s").name,
                         "c6ee4209f2ca5659.json")

    def test_a_backslash_path_is_a_different_cache(self):
        self.assertNotEqual(hook.cache_file("C:/Users/skf_s"),
                            hook.cache_file("C:\\Users\\skf_s"))


class Dedupe(unittest.TestCase):
    """One send per session per text; SessionStart clears the marker."""

    def setUp(self):
        import uuid
        self.sid = f"test-{uuid.uuid4()}"
        self.addCleanup(hook.reset, self.sid)

    def test_the_first_send_goes_out_and_the_repeat_does_not(self):
        self.assertFalse(hook.already_sent(self.sid, payload(MEMORY)))
        self.assertTrue(hook.already_sent(self.sid, payload(MEMORY)))

    def test_changed_text_goes_out_again(self):
        hook.already_sent(self.sid, payload(MEMORY))
        self.assertFalse(hook.already_sent(self.sid, payload(MEMORY + "- new\n")))

    def test_reset_makes_the_same_text_go_out_again(self):
        hook.already_sent(self.sid, payload(MEMORY))
        hook.reset(self.sid)
        self.assertFalse(hook.already_sent(self.sid, payload(MEMORY)))

    def test_another_session_is_not_silenced(self):
        hook.already_sent(self.sid, payload(MEMORY))
        other = self.sid + "-b"
        self.addCleanup(hook.reset, other)
        self.assertFalse(hook.already_sent(other, payload(MEMORY)))

    def test_no_session_id_never_silences(self):
        self.assertFalse(hook.already_sent("", payload(MEMORY)))
        self.assertFalse(hook.already_sent("", payload(MEMORY)))

    def test_the_env_switch_turns_it_off(self):
        import os
        from unittest import mock
        hook.already_sent(self.sid, payload(MEMORY))
        with mock.patch.dict(os.environ, {"CLAUDE_HIPPO_DEDUPE": "off"}):
            self.assertFalse(hook.already_sent(self.sid, payload(MEMORY)))


if __name__ == "__main__":
    unittest.main()
