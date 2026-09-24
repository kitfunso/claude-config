"""Tests for scorecard.py: scoring math, CRITICAL and probation parsing, the reply-check log and the eval JSON reader."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scorecard as sc  # noqa: E402
import time_ledger  # noqa: E402
import token_ledger  # noqa: E402

WEEK_START = datetime(2026, 9, 17, tzinfo=timezone.utc)
GOAL = {g.key: g for g in sc.GOALS}
PRECEDENCE_PROSE = (
    "- Order when two rules collide: CRITICAL rules and explicit user instructions (Human Voice is one), then Root Cause.",
    "- `(CRITICAL)` means never violate, override only via explicit user instruction.",
    "- A rule without a verifier is a claim: propose the hook or grep in the same turn you strengthen a CRITICAL rule.",
)
RULES_MD = "\n".join((
    "# Global Claude Code Configuration",
    "## Precedence (when rules conflict)",
    *PRECEDENCE_PROSE,
    "- **Reports are local HTML files, never claude.ai pages (CRITICAL).** Never publish. Set 2026-09-23 (probation) after a page.",
    "- **Prose:** no em dashes in commits.",
    "## Sourcing (CRITICAL)",
    "A paragraph that says (CRITICAL) is prose.",
    "**Bold paragraph (CRITICAL)** without a bullet is prose too.",
    "## Human Voice (CRITICAL)",
    "- First sentence is the answer.",
    "- Backstop: the human-voice hook. Set 2026-09-22 (probation) after two reports.",
    "### Outside Voice (CRITICAL for plans)",
    "## Question Triage (DEFAULT)",
    "- New rules from one incident carry `(probation)`.",
))


def reply(ts: str, flags: list[str]) -> str:
    return json.dumps({"ts": ts, "session": "s1", "lines": 4, "words": 60, "tools": 2, "flags": flags})


def write_eval(skills: Path, skill: str, started: str, passed: int, total: int, case: str = "c1") -> Path:
    """One case whose with-skill arm passes `passed` of `total` runs; the without arm always passes and must be ignored."""
    (skills / skill / "evals" / case).mkdir(parents=True, exist_ok=True)
    path = skills / skill / "evals" / "results" / started / "aggregate-result.json"
    path.parent.mkdir(parents=True)
    arms = {"with": [{"passed": i < passed} for i in range(total)], "without": [{"passed": True}] * 3}
    path.write_text(json.dumps({"schemaVersion": 1, "cases": [{"name": case, "arms": arms}]}), encoding="utf-8")
    return path


@pytest.mark.parametrize("value, floor, target, want", [
    (43.5, 77, 10, 0.5), (77, 77, 10, 0.0), (10, 77, 10, 1.0),
    (0.725, 0.5, 0.95, 0.5), (1.25, 1.5, 1.0, 0.5), (0.25, 1.0, 0.0, 0.75),
])
def test_score_is_linear_from_floor_to_target(value: float, floor: float, target: float, want: float) -> None:
    assert sc.score(value, floor, target) == pytest.approx(want)


@pytest.mark.parametrize("value, floor, target, want", [
    (3, 77, 10, 1.0), (120, 77, 10, 0.0), (0.99, 0.5, 0.95, 1.0),
    (0.2, 0.5, 0.95, 0.0), (0.9, 1.5, 1.0, 1.0), (2.0, 1.5, 1.0, 0.0),
])
def test_score_clips_outside_the_band(value: float, floor: float, target: float, want: float) -> None:
    assert sc.score(value, floor, target) == want


def test_no_data_scores_zero() -> None:
    assert sc.score(None, 77, 10) == 0.0
    assert sc.score(None, 0.5, 0.95) == 0.0


def test_overall_is_the_equal_weight_mean_out_of_100() -> None:
    assert sc.overall([1, 1, 1, 1, 1, 1, 1]) == pytest.approx(100)
    assert sc.overall([1, 0, 0.5, 1, 1, 0, 0]) == pytest.approx(50)


def test_goals_are_seven_with_a_band_to_score_across() -> None:
    assert len(GOAL) == 7
    assert all(g.floor != g.target for g in sc.GOALS)
    assert sc.goal_text(GOAL["approvals"]) == "at most 10"
    assert sc.goal_text(GOAL["reply_check"]) == "at least 95%"


def test_critical_rules_are_headings_and_bold_lead_bullets_only() -> None:
    names = [sc.rule_name(line) for line in sc.critical_rules(RULES_MD)]
    assert names == ["Reports are local HTML files, never claude.ai pages", "Sourcing", "Human Voice", "Outside Voice"]


@pytest.mark.parametrize("line", PRECEDENCE_PROSE)
def test_precedence_prose_that_mentions_critical_is_not_a_rule(line: str) -> None:
    assert sc.critical_rules(line) == []


def test_hook_scripts_reads_command_and_args() -> None:
    settings = {"hooks": {
        "PreToolUse": [{"matcher": "Bash", "hooks": [{"command": "python.exe", "args": ["C:\\hooks\\git_guard.py"]}]}],
        "Stop": [{"hooks": [{"command": 'python "C:/x y/hooks/reply_check.py" --quiet'}]}],
    }}
    assert {"git_guard.py", "reply_check.py"} <= sc.hook_scripts(settings)


def critical_setup(tmp_path: Path, on_disk: tuple[str, ...], wired: tuple[str, ...], deny: list[str]) -> sc.Result:
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    for name in on_disk:
        (hooks / name).write_text("", encoding="utf-8")
    md = tmp_path / "CLAUDE.md"
    md.write_text(RULES_MD, encoding="utf-8")
    groups = [{"hooks": [{"type": "command", "command": "python", "args": [str(hooks / name)]}]} for name in wired]
    return sc.critical_metric([md], {"permissions": {"deny": deny}, "hooks": {"Stop": groups}}, hooks)


def test_rule_is_checked_only_when_every_script_is_on_disk_and_wired(tmp_path: Path) -> None:
    result = critical_setup(tmp_path, ("human_voice.py", "reply_check.py"), ("human_voice.py", "reply_check.py"), ["Artifact"])
    assert result.value == pytest.approx(3 / 4)
    assert result.note == "unchecked: Outside Voice (no mapping)"


def test_missing_or_unwired_scripts_and_absent_deny_leave_rules_unchecked(tmp_path: Path) -> None:
    result = critical_setup(tmp_path, ("human_voice.py",), ("reply_check.py",), [])
    assert result.value == 0.0
    text = "\n".join(result.details)
    assert "reply_check.py missing from scripts/hooks" in text
    assert "human_voice.py not wired in settings.json" in text
    assert "Artifact not in permissions.deny" in text


def test_probation_is_owned_by_the_nearest_rule_line() -> None:
    assert sc.probation_rules(RULES_MD) == [
        ("Reports are local HTML files, never claude.ai pages", date(2026, 9, 23)),
        ("Human Voice", date(2026, 9, 22)),
    ]


def test_probation_overdue_only_after_30_days(tmp_path: Path) -> None:
    md = tmp_path / "CLAUDE.md"
    md.write_text("## Old Rule\n- Set 2026-08-01 (probation) after x.\n## Edge Rule\n- Set 2026-08-25 (probation).\n"
                  "## New Rule\n- Set 2026-09-20 (probation) after y.\n", encoding="utf-8")
    result = sc.probation_metric([md], date(2026, 9, 24), None)
    assert result.note == "overdue: Old Rule"
    assert result.value == pytest.approx(1 / 3)
    assert sc.score(result.value, GOAL["probation"].floor, GOAL["probation"].target) == pytest.approx(2 / 3)
    assert "30 days old;" in result.details[1]


def test_no_probation_rules_scores_full(tmp_path: Path) -> None:
    md = tmp_path / "CLAUDE.md"
    md.write_text("## Rule\n- New rules carry `(probation)`.\n", encoding="utf-8")
    result = sc.probation_metric([md], date(2026, 9, 24), None)
    assert sc.score(result.value, GOAL["probation"].floor, GOAL["probation"].target) == 1.0


def test_fires_counts_only_the_rules_own_flags() -> None:
    replies = [{"flags": ["long", "banned:word", "sweeping"]}, {"flags": []}, {"flags": ["table", "other"]}]
    assert sc.fires("Human Voice", replies) == "3"
    assert sc.fires("Do It Properly", replies) == "1"
    assert sc.fires("Reports are local HTML files, never claude.ai pages", replies) == "n/a"
    assert sc.fires("Human Voice", None) == "no data yet"


def test_missing_reply_log_is_no_data(tmp_path: Path) -> None:
    log = sc.read_reply_log(tmp_path / "reply_check.jsonl", WEEK_START)
    assert log is None
    result = sc.reply_metric(log)
    assert (result.value, result.shown) == (None, "no data yet")


def test_reply_log_keeps_the_window_and_counts_bad_lines(tmp_path: Path) -> None:
    path = tmp_path / "reply_check.jsonl"
    path.write_text("\n".join((
        reply("2026-09-23T10:00:00Z", []),
        reply("2026-09-23T11:00:00Z", ["long", "banned:word"]),
        reply("2026-09-24T09:00:00+00:00", []),
        reply("2026-09-10T10:00:00Z", ["table"]),
        '{"ts": "2026-09-23T12:00:00Z"}',
        "not json",
        '{"flags": []}',
        "",
    )) + "\n", encoding="utf-8")
    records, unreadable = sc.read_reply_log(path, WEEK_START)
    assert (len(records), unreadable) == (3, 3)
    result = sc.reply_metric((records, unreadable))
    assert result.value == pytest.approx(2 / 3)
    assert "banned:word 1" in result.details[0]


def test_reply_log_with_nothing_in_the_window_is_no_data(tmp_path: Path) -> None:
    path = tmp_path / "reply_check.jsonl"
    path.write_text(reply("2026-09-01T10:00:00Z", []) + "\n", encoding="utf-8")
    assert sc.reply_metric(sc.read_reply_log(path, WEEK_START)).value is None


def test_eval_metric_counts_with_skill_runs_only(tmp_path: Path) -> None:
    write_eval(tmp_path, "critique", "2026-09-22T10-31-27-554Z", 1, 3)
    assert sc.eval_metric(tmp_path).note == "lowest: critique 1/3"


def test_eval_metric_takes_the_newest_run_of_each_case(tmp_path: Path) -> None:
    write_eval(tmp_path, "wtf", "2026-09-22T10-00-00-000Z", 0, 3, case="c1")
    write_eval(tmp_path, "wtf", "2026-09-22T11-00-00-000Z", 3, 3, case="c2")
    write_eval(tmp_path, "wtf", "2026-09-24T12-00-00-000Z", 2, 3, case="c1")
    result = sc.eval_metric(tmp_path)
    assert result.note == "lowest: wtf 5/6"
    assert "newest run per case, dated 2026-09-22 to 2026-09-24" in result.details


def test_eval_metric_ignores_cases_no_longer_on_disk(tmp_path: Path) -> None:
    write_eval(tmp_path, "wtf", "2026-09-22T10-00-00-000Z", 3, 3, case="kept")
    write_eval(tmp_path, "wtf", "2026-09-22T11-00-00-000Z", 0, 3, case="gone")
    (tmp_path / "wtf" / "evals" / "gone").rmdir()
    assert sc.eval_metric(tmp_path).note == "lowest: wtf 3/3"


def test_eval_metric_skips_skills_that_cannot_fire_in_an_eval(tmp_path: Path) -> None:
    for skill, passed in (("fine", 3), ("manual", 0), ("mentions", 0)):
        write_eval(tmp_path, skill, "2026-09-22T10-00-00-000Z", passed, 3)
    (tmp_path / "manual" / "SKILL.md").write_text("---\nname: manual\ndisable-model-invocation: true\n---\nBody.\n",
                                                  encoding="utf-8")
    (tmp_path / "mentions" / "SKILL.md").write_text("---\nname: mentions\n---\ndisable-model-invocation: true\n",
                                                    encoding="utf-8")
    result = sc.eval_metric(tmp_path)
    assert result.value == 0.5
    assert "not scored, disable-model-invocation never fires in an eval: manual" in result.details


def test_eval_metric_uses_the_latest_run_of_a_rerun_case(tmp_path: Path) -> None:
    write_eval(tmp_path, "critique", "2026-09-22T09-49-05-940Z", 0, 3)
    write_eval(tmp_path, "critique", "2026-09-22T10-31-27-554Z", 3, 3)
    write_eval(tmp_path, "wtf", "2026-09-22T10-28-40-308Z", 1, 2)
    write_eval(tmp_path, "learn", "2026-09-22T10-06-21-788Z", 0, 2)
    write_eval(tmp_path, "grill-me", "2026-09-22T09-49-05-974Z", 2, 4)
    result = sc.eval_metric(tmp_path)
    assert result.value == pytest.approx((1 + 0.5 + 0 + 0.5) / 4)
    assert result.note == "lowest: learn 0/2, grill-me 2/4, wtf 1/2"


def test_eval_metric_names_unreadable_results_and_skips_them(tmp_path: Path) -> None:
    write_eval(tmp_path, "fine", "2026-09-22T10-00-00-000Z", 1, 1)
    broken = tmp_path / "broken" / "evals" / "results" / "2026-09-22T10-00-00-000Z" / "aggregate-result.json"
    broken.parent.mkdir(parents=True)
    broken.write_text("{", encoding="utf-8")
    result = sc.eval_metric(tmp_path)
    assert result.value == 1.0
    assert any(line.startswith("unreadable: broken") for line in result.details)


def test_eval_metric_without_results_is_no_data(tmp_path: Path) -> None:
    assert sc.eval_metric(tmp_path).value is None


def test_approval_gaps_counts_short_go_prompts_within_one_session() -> None:
    t = datetime(2026, 9, 23, 10, tzinfo=timezone.utc)

    def row(session: str, prompt: str, start: int, end: int) -> dict:
        return {"session": session, "prompt": prompt, "t0": t + timedelta(minutes=start),
                "t1": t + timedelta(minutes=end), "last_text": ""}

    rows = [row("a", "build the scorecard", 0, 10), row("a", "go", 14, 30),
            row("a", "yes, and also change every button on the settings page to blue", 31, 40), row("b", "continue", 50, 60)]
    assert [round(gap, 1) for gap, _, _ in time_ledger.approval_gaps(rows)] == [4.0]
    assert sc.approvals_metric(rows, WEEK_START, 7).value == 1
    assert sc.approvals_metric([], WEEK_START, 7).value is None


def test_approval_gaps_skip_a_go_after_a_usage_limit() -> None:
    t = datetime(2026, 9, 23, 10, tzinfo=timezone.utc)
    replies = [("build it", "You've hit your weekly limit · resets Sep 28, 5am (Europe/London)"),
               ("continue", "Built. You've hit your weekly limit on nothing else."), ("go", "")]
    rows = [{"session": "a", "prompt": prompt, "t0": t + timedelta(minutes=10 * i),
             "t1": t + timedelta(minutes=10 * i + 5), "last_text": text} for i, (prompt, text) in enumerate(replies)]
    assert [r["prompt"] for _, _, r in time_ledger.approval_gaps(rows)] == ["go"]


def assistant_row(rid: str, ts: str) -> str:
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 90, "output_tokens": 5}
    msg = {"model": "claude-opus-5-5", "usage": usage, "content": [{"type": "text", "text": "ok"}]}
    return json.dumps({"type": "assistant", "timestamp": ts, "requestId": rid, "message": msg}) + "\n"


def test_token_ledger_prices_one_read_of_a_transcript_that_grows_while_read() -> None:
    rows = [assistant_row("req_1", "2026-09-23T10:00:00Z"), assistant_row("req_2", "2026-09-23T10:01:00Z")]
    opened = []

    class Growing:
        def open(self, **_: object) -> io.StringIO:
            opened.append(1)
            return io.StringIO("".join(rows[:len(opened)]))

    ledger = token_ledger.Ledger()
    token_ledger.walk(Growing(), ledger, "", "s1", "main")
    assert ledger.sessions["s1"]["requests"] == 1


def test_sync_is_zero_outside_a_checkout_and_half_without_origin(tmp_path: Path) -> None:
    assert sc.sync_metric(tmp_path, fetch=False).value == 0.0
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    result = sc.sync_metric(tmp_path, fetch=False)
    assert result.value == 0.5
    assert "no origin/main" in result.shown
