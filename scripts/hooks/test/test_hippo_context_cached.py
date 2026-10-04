"""Tests for the hippo UserPromptSubmit cache wrapper.

Run: python -m unittest discover -s scripts/hooks/test -p "test_*.py"
"""

import json
import sys
import unittest
from unittest import mock
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
    def test_the_name_is_the_hash_of_the_cwd_and_the_query(self):
        with mock.patch.object(hook, "ARGS", ["context", "--pinned-only"]):
            old = hook.cache_file("C:/Users/skf_s")
        self.assertNotEqual(hook.cache_file("C:/Users/skf_s"), old)

    def test_a_backslash_path_is_the_same_cache(self):
        self.assertEqual(hook.cache_file("C:/Users/skf_s"),
                         hook.cache_file("C:\\Users\\skf_s\\"))


class Dedupe(unittest.TestCase):
    """One send per armed session per text; SessionStart arms the marker."""

    def setUp(self):
        import uuid
        self.sid = f"test-{uuid.uuid4()}"
        self.arm(self.sid)

    def arm(self, sid):
        hook.reset(sid)
        self.addCleanup(lambda: hook.seen_file(sid).unlink(missing_ok=True))

    def test_a_session_the_reset_hook_never_armed_is_not_silenced(self):
        cold = self.sid + "-cold"
        self.assertFalse(hook.already_sent(cold, payload(MEMORY)))
        self.assertFalse(hook.already_sent(cold, payload(MEMORY)))
        self.assertFalse(hook.seen_file(cold).exists())

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
        self.arm(other)
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


RECALL = "## Prompt-Relevant Memory (1 entries, 30 tokens)\n\n- **[verified] a lesson**"


class PromptRecall(unittest.TestCase):
    """The cache holds pinned rules only, so the prompt must reach a live hippo call."""

    def setUp(self):
        hook.backoff_file().unlink(missing_ok=True)
        self.addCleanup(lambda: hook.backoff_file().unlink(missing_ok=True))

    def test_the_recall_section_is_cut_from_the_live_block(self):
        self.assertEqual(hook.recall_section(payload(MEMORY + "\n" + RECALL)), RECALL)

    def test_a_block_with_no_recall_gives_nothing(self):
        self.assertEqual(hook.recall_section(payload(MEMORY)), "")
        self.assertEqual(hook.recall_section(None), "")
        self.assertEqual(hook.recall_section("not json"), "")

    def test_the_hook_payload_goes_to_hippo_on_stdin(self):
        stdin = json.dumps({"prompt": "which benchmark scores hippo"})
        with mock.patch.object(hook, "exec_hippo", return_value=payload(RECALL)) as run:
            self.assertEqual(hook.prompt_recall("C:/x", stdin, "which benchmark", 5.0), RECALL)
        self.assertEqual(run.call_args.args[2], stdin)

    def test_an_empty_prompt_skips_the_live_call(self):
        with mock.patch.object(hook, "exec_hippo") as run:
            self.assertEqual(hook.prompt_recall("C:/x", "{}", "  ", 5.0), "")
        run.assert_not_called()

    def test_no_time_left_skips_the_live_call(self):
        with mock.patch.object(hook, "exec_hippo") as run:
            self.assertEqual(hook.prompt_recall("C:/x", "{}", "a prompt", 0.5), "")
        run.assert_not_called()

    def test_the_env_switch_turns_recall_off(self):
        import os
        with mock.patch.dict(os.environ, {"CLAUDE_HIPPO_RECALL": "off"}), \
                mock.patch.object(hook, "exec_hippo") as run:
            self.assertEqual(hook.prompt_recall("C:/x", "{}", "a prompt", 5.0), "")
        run.assert_not_called()

    def test_a_timeout_pauses_recall_for_the_backoff(self):
        boom = hook.subprocess.TimeoutExpired("hippo", 6)
        with mock.patch.object(hook, "exec_hippo", side_effect=boom):
            self.assertEqual(hook.prompt_recall("C:/x", "{}", "a prompt", 5.0), "")
        with mock.patch.object(hook, "exec_hippo") as run:
            self.assertEqual(hook.prompt_recall("C:/x", "{}", "a prompt", 5.0), "")
        run.assert_not_called()

    def test_an_expired_backoff_lets_recall_run_again(self):
        import os
        import time
        hook.write_cache(hook.backoff_file(), "1")
        old = time.time() - hook.RECALL_BACKOFF - 1
        os.utime(hook.backoff_file(), (old, old))
        with mock.patch.object(hook, "exec_hippo", return_value=payload(RECALL)):
            self.assertEqual(hook.prompt_recall("C:/x", "{}", "a prompt", 5.0), RECALL)


class Merge(unittest.TestCase):
    def test_pinned_and_recall_travel_as_one_block(self):
        out = hook.merge(payload(MEMORY), RECALL)
        self.assertEqual(context_of(out), MEMORY + "\n\n" + RECALL)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")

    def test_recall_goes_out_after_the_pinned_block_was_deduped(self):
        self.assertEqual(context_of(hook.merge(None, RECALL)), RECALL)

    def test_no_recall_leaves_the_pinned_block_untouched(self):
        raw = payload(MEMORY)
        self.assertEqual(hook.merge(raw, ""), raw)
        self.assertIsNone(hook.merge(None, ""))


if __name__ == "__main__":
    unittest.main()
