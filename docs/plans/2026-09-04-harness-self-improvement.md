# Harness Self-Improvement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Close the one write-back arm the harness already has (Part A), then record component use automatically so every skill, agent and hook gets the same used/helped/trusted scoreboard the critics already have (Part B).

**Architecture:** Nothing new is invented. `devrl.py` already ships `learn-apply`, `learn-effect`, `policy-compact-report`, `audit-record` and `critic_trust.py`. Every one of them terminates in a report that a human must act on, and the one path that writes back (`learn-apply --failure-mode`) has a free escape hatch (`--unlinked`) that has been taken 45 times out of 45. Part A removes the free escape hatch and backfills what can be recovered. Part B feeds the same store from a PostToolUse hook so `used` stops depending on a human remembering to type it.

**Tech Stack:** Python 3.12, SQLite (`~/.claude/dev-framework/episodes.db`), pytest, Node hooks
registered in `~/.claude/settings.json`. **Node is v24.13.0 on this box and `require('node:sqlite')`
loads** (verified 2026-09-04), so the Part B hook writes SQLite with no new dependency. Do not add
`better-sqlite3`; it is absent and would need native build tooling on Windows.

**Revision 1 (2026-09-04):** eng review found the Revision 0 root cause incomplete. Two further leaks
are now Tasks A0b and A0c, and both must ship before anything else in Part A. Revision 0 would have
created `fix_applied_to` links that normal use silently erased, then reported the loop closed.

**Revision 2 (2026-09-04):** the rest of the consolidated eng review, applied. Nine items:

| # | Section | Change |
|---|---|---|
| 1 | A0b | new task: carry `fix_applied_to` through a recompute |
| 2 | A0c | new task: close the auto-tier1 bypass |
| 3 | Tech Stack | Node is v24.13.0 and `node:sqlite` loads; the review's "no SQLite driver" CRIT was based on my own wrong "Node 20" line |
| 4 | B1 | explicit WAL and `busy_timeout` step, with the failing-first test that proves it |
| 5 | A3 | names `_tokens` (`clustering.py:62`) and `_jaccard` (`clustering.py:67`) instead of a grep that finds neither |
| 6 | B4 | reuse the scoring discipline, write new SQL; `compute_trust_counts` is not callable on component rows |
| 7 | A0a | per-task fixture consumer table; B2 dropped from its prerequisite list |
| 8 | B5 | retires `log-gate.ps1` and `telemetry-report.ps1`, not just the JSONL |
| 9 | Verification | `learn-effect` twice around a `learn-cluster`, to prove the links survive a recompute |

---

## Execution status (2026-09-04, end of session)

All of Part A and Part B shipped. Keith cleared the three gated items on 2026-09-04.

| Task | State | Where |
|---|---|---|
| A0a-A0c, A1-A3 | shipped | see the A6 correction block after Step 5 |
| A4 backfill | shipped | `--min-score 0.5`, 2 of 45 linked (`failure_modes` 11527, 11644), 43 left alone |
| A5 cron | shipped and verified | manual run 2026-09-04: `lastRunStatus: ok`, `lastDelivered: true`, `lastDeliveryStatus: delivered`, `consecutiveErrors` 2 to 0, 978s. The earlier `error` state was stale, since the config edit landed after the last failing run |
| A6 | shipped, but all three of the plan's premises were wrong. Read the correction block before trusting this section |
| B1 migration 0020 | shipped | dev-framework `67fa8d0` |
| B2 recorder + B3 guards | shipped | ~/.claude `76a2ed6`; registered in `settings.json`, which is gitignored, so THIS BOX ONLY |
| B4 component-report | shipped | dev-framework `07f62bd`, clawd `9f613ee` |
| B5 producer + import | shipped | dev-framework `6e89fec`, ~/.claude `c29ecae` |
| B5 deletions | shipped | ~/.claude `81912c7`, all four files gone |

Two corrections to the plan as written, both found by running it:

- **B1's concurrency step was a no-op.** `migrate.py:67` already sets WAL, and Python's
  `sqlite3.connect` defaults to `timeout=5.0`, which is `busy_timeout = 5000`. The plan's
  proposed `PRAGMA busy_timeout = 3000` would have lowered it. Skipped, and mutation-checked
  instead: setting it to 0 turns the test red with `database is locked`.
- **B4 cannot score anything yet, by construction.** The hook writes `episode_id = NULL`, so
  `in_episodes` is 0 and `trust` is null on every row. That is the honest state the plan
  anticipated. The next piece of work, not in this plan, is stamping the current episode id
  onto rows written inside an episode.

## Evidence this plan is built on

Every number below came from a command run on 2026-09-04. Re-run any of them.

| Fact | Command |
|---|---|
| 45/45 policy updates unlinked, 0 fixes scorable | `python C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py learn-effect` |
| 0 of 182 failure_modes carry `fix_applied_to` | `python -c "import sqlite3;print(sqlite3.connect(r'C:/Users/skf_s/.claude/dev-framework/episodes.db').execute('select count(*) from failure_modes where fix_applied_to is not null').fetchone())"` |
| 114 audit firings unscored (pre-2026-08-24), 13 scored (2026-09-02) | `python -c "import sqlite3;print(sqlite3.connect(r'C:/Users/skf_s/.claude/dev-framework/episodes.db').execute(\"select case when caught is null then 'NULL' else 'scored' end k,count(*),min(created_at),max(created_at) from audit_rule_firings group by k\").fetchall())"` |
| trigger mix: manual 20, auto-tier1 18, operator_friction 7 | `python -c "import sqlite3;print(sqlite3.connect(r'C:/Users/skf_s/.claude/dev-framework/episodes.db').execute('select trigger,count(*) from policy_updates group by trigger').fetchall())"` |
| `claude-config-audit` cron: 2 consecutive errors, 581s run, not delivered | `openclaw cron get 05558fba-d91c-4cc8-9d6f-dd5fbd6aed50` |
| Skill name is `tool_input.skill`, agent type is `tool_input.subagent_type` | `grep -o '"name":"Skill","input":{"skill":"[^"]*"' C:/Users/skf_s/.claude/projects/C--Users-skf-s/*.jsonl \| head` |

### Non-goal, recorded on purpose

**Do not prune the zero-catch audit rules.** 114 of 127 firings predate the `caught` column
(added 2026-09-01, see `episodes.db.bak-20260901-pre-caught`). `todos-staleness`, `functional-duplicate`
and `roadmap-evals-freshness` show catch_rate 0 or null because they are unmeasured, not because they
are useless. `policy_compact_report` already encodes this ("Absence alone never demotes"). Revisit
after 20 instrumented episodes carry a scored `caught` value.

---

## Part A — close the apply arm

### Task A0a: Test fixtures (prerequisite for A0b, A1, A3, A4)

`tests/conftest.py` defines only `db_path`, `migrated_db` and `conn`. The fixtures the later tasks
use do not exist anywhere in `tests/` — verify with
`grep -rn "tmp_db\|tmp_db_with_pending_clusters" C:/Users/skf_s/.claude/dev-framework/tests/`
(expect zero hits). Write them before the tasks that need them, or every later test fails on a
missing fixture rather than on the behaviour under test.

**Files:** Modify `C:/Users/skf_s/.claude/dev-framework/tests/conftest.py`

- `tmp_db` — a migrated empty DB path, built on the existing `migrated_db`. Do not duplicate its logic.
- `tmp_db_with_pending_clusters` — `tmp_db` plus at least two `failure_modes` rows with
  `status='pending'` and distinguishable `pattern` text, so A3's similarity suggestion has something
  real to rank. Seed through the store API, not raw INSERTs, so the fixture cannot drift from schema.

**Which task consumes which fixture.** Both fixtures must satisfy every consumer below, so read this
list before deciding their shape. A fixture that only fits A1 forces a rewrite at A3.

| Fixture | Used by | Needs |
|---|---|---|
| `tmp_db` | A0b `test_link_survives_a_recompute_that_changes_cluster_id` | at least one `acted_observations` row carrying a non-null `fix_applied_to`, reachable through the store API |
| `tmp_db` | A1 `test_unlinked_without_reason_is_rejected`, `test_unlinked_with_reason_is_accepted` | nothing beyond a migrated empty DB |
| `tmp_db` | A4 `test_dry_run_writes_nothing`, `test_apply_requires_confidence_threshold` | at least one unlinked `policy_updates` row, so `_count_linked` has a real before-value |
| `tmp_db_with_pending_clusters` | A3 `test_missing_link_prints_candidate_clusters` | two-plus pending `failure_modes` whose `pattern` text differs enough that `_jaccard` ranks them apart |

A0b and A4 each need seeded rows that a bare `tmp_db` does not have. Either add the rows inside those
tests, or add two more named fixtures here. Decide now and write it down; do not leave it to execute.

**B2 does not use these.** Its test drives a Node hook through stdin against its own temp SQLite
file, so it never imports `conftest.py`. That is why B2 is off this task's prerequisite list.

Commit before starting A0b.

---

### Task A0b: Carry `fix_applied_to` through a recompute (CRIT)

**This is the first real fix. Without it every link Part A creates is erased by normal use.**

**Files:**
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/episode_store.py:1046-1061` (`replace_failure_modes`)
- Create: `C:/Users/skf_s/.claude/dev-framework/migrations/0018_acted_fix_applied_to.sql`
- Test: `C:/Users/skf_s/.claude/dev-framework/tests/test_failure_mode_link_durability.py`

**The defect.** `replace_failure_modes` initialises `fix_applied_to = None` at line 1047. The
`prior_status` branch (1048) restores it by matching `cluster_id`. The `elif acted_statuses` branch
(1052-1061) — the occurrence-level fallback added precisely because cluster ids churn — restores
`status` and `applied_at` and **never touches `fix_applied_to`**, so it stays `None`.
`_cluster_id` (`clustering.py:73-84`) derives the id from top-3 token frequencies across the
cluster's observations, so one new occurrence can change the id and push a row down the `elif`
branch. That branch runs on every `--learn-emit` finalize (`devrl.py:216`), every `batch-finalize`
(`devrl.py:760`) and every `learn-cluster` (`devrl.py:1079`). This is the routine path, not a rare one.

**Step 1: Write the failing durability test**

```python
def test_link_survives_a_recompute_that_changes_cluster_id(tmp_db):
    """A0b - the regression that makes every other Part A task pointless."""
    # 1. seed a cluster, link it via learn-apply
    # 2. add an observation that changes the cluster's derived id
    # 3. re-run replace_failure_modes
    # 4. assert fix_applied_to is STILL set
    assert linked_after == linked_before
```

**Step 2: Run it, watch it fail.** Expect `fix_applied_to` to be `None` after the recompute. Do not
skip watching it fail — a durability test that never went red proves nothing
(`feedback_mutation_test_before_moving_on.md`).

**Step 3: Add the column and carry the value**

`acted_observations` currently stores only `status` and `acted_at`, so the `elif` branch has nothing
to restore from. Add it:

```sql
-- 0018_acted_fix_applied_to.sql
ALTER TABLE acted_observations ADD COLUMN fix_applied_to TEXT;
```

Then in the `elif acted_statuses` branch, restore `fix_applied_to` alongside `applied_at`, taking the
value from the same observation that supplied the `max(acted_at)`.

**Step 4: Run the test, confirm PASS. Then run the whole suite** — this function is load-bearing:
`python -m pytest C:/Users/skf_s/.claude/dev-framework/tests/ -q`

**Step 5: Back up the DB and migrate**, per the A2 pattern (`.bak-20260904-pre-0018`).

**Step 6: Commit.** `fix: carry fix_applied_to through occurrence-level cluster recovery`

**DONE 2026-09-04, commit `cd45511`.** Two corrections to the analysis above, both found during
execution:

1. The churn is worse than "one new occurrence can change the id". `_cluster_id` breaks top-3 token
   frequency ties by iterating a set, whose order is hash-randomised per process. An unchanged
   cluster gets a different id in a different process: PYTHONHASHSEED 0 and 2 give
   `markdown-parser-unit`, 1 and 3 give `markdown-tests-unit`. Every `learn-cluster` run is a fresh
   process, so the `elif` fallback is the normal path. A determinism fix for `_cluster_id` is worth
   doing but must land *after* A0b, because making ids stable shifts every tied cluster's id exactly
   once, and without A0b that one shift drops every link.
2. Live `episodes.db` before the fix: 44 occurrences marked `applied`, **0** failure modes carrying
   `applied` status, **0** carrying a fix link, against 45 policy updates. `learn-effect` had nothing
   to score at all. Reproduce with
   `python -c "import sqlite3;c=sqlite3.connect('episodes.db');print(c.execute('SELECT status,COUNT(*) FROM acted_observations GROUP BY status').fetchall(),c.execute('SELECT COUNT(*) FROM failure_modes WHERE fix_applied_to IS NOT NULL').fetchone())"`
   from `C:/Users/skf_s/.claude/dev-framework`.

The historical 44 stay unlinked: `acted_observations.fix_applied_to` is NULL for every pre-migration
row and the policy update that acted on each one is not recoverable from the schema. A2's backfill is
the only route to them, and it must not guess.

---

### Task A0c: Close the auto-tier1 bypass (CRIT)

**Files:**
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/episode_store.py:1314-1353` (`register_memory_auto_tier1`)
- Test: `C:/Users/skf_s/.claude/dev-framework/tests/test_auto_tier1_linking.py`

**The defect.** `register_memory_auto_tier1` runs its own raw `INSERT INTO policy_updates` at line
1349 and never calls `record_policy_update`. Its `cluster_id` argument only reaches
`hippo_memory_lineage.source_cluster_id` (line 1344), an unrelated provenance field. So the
`auto-tier1` trigger — **18 of the 45 unlinked rows**, the second-largest source — cannot be linked
at all, and A1's guard lives in a function this path never enters. Guarding one door while the
second stands open is the patch smell the global CLAUDE.md names.

**Step 1: Write the failing test** — call the auto-tier1 path with a `cluster_id`, assert the matching
`failure_modes` row ends up with `fix_applied_to = 'policy_update:<id>'`.

**Step 2: Run it, watch it fail.**

**Step 3: Fix at the root — route auto-tier1 through `record_policy_update`** rather than adding a
second `fix_applied_to` write beside the raw INSERT. Two writers of the same column is how this
drifted in the first place. If the transactional shape genuinely differs, say why in one line and
extract the shared write instead of duplicating it.

**Step 4: Run the test and the full suite. Commit.**
`fix: route auto-tier1 policy updates through record_policy_update`

---

### Task A1: Refuse a silent `--unlinked`

**Files:**
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py:1140-1152` (the `--unlinked` guard in `cmd_learn_apply`)
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py` (argparse block for `learn-apply`)
- Test: `C:/Users/skf_s/.claude/dev-framework/tests/test_learn_apply_linking.py`

**Step 1: Write the failing test**

```python
"""A1 - an unlinked policy update must cost the operator a reason."""
import json
import subprocess
import sys
from pathlib import Path

DEVRL = Path.home() / ".claude" / "dev-framework" / "scripts" / "devrl.py"


def _run(args, db):
    return subprocess.run(
        [sys.executable, str(DEVRL), "--db", str(db), *args],
        capture_output=True, text=True,
    )


def test_unlinked_without_reason_is_rejected(tmp_db):
    r = _run(["learn-apply", "--unlinked", "--summary", "x", "--trigger", "manual"], tmp_db)
    assert r.returncode == 2
    assert "--unlinked-reason" in r.stderr


def test_unlinked_with_reason_is_accepted(tmp_db):
    r = _run([
        "learn-apply", "--unlinked",
        "--unlinked-reason", "orphan skill edit, friction did not cluster",
        "--summary", "x", "--trigger", "manual",
    ], tmp_db)
    assert r.returncode == 0
    assert json.loads(r.stdout)["unlinked_reason"]
```

**Step 2: Run it to verify it fails**

Run: `python -m pytest C:/Users/skf_s/.claude/dev-framework/tests/test_learn_apply_linking.py -v`
Expected: FAIL, `--unlinked-reason` is not a recognised argument.

**Step 3: Add the argument and the guard**

In the `learn-apply` argparse block, beside the existing `--unlinked`:

```python
    p.add_argument(
        "--unlinked-reason", default=None,
        help="required with --unlinked: why this delta fixes no cluster. "
             "An unlinked delta is invisible to learn-effect forever, so the "
             "reason is the only record of why it was chosen.",
    )
```

In `cmd_learn_apply`, replace the existing `if not args.failure_mode and not args.unlinked:` guard body with a two-branch check:

```python
    if not args.failure_mode:
        if not args.unlinked:
            print(
                "learn-apply: pass --failure-mode <id> to link this delta to the "
                "cluster it fixes, or --unlinked with --unlinked-reason.",
                file=sys.stderr,
            )
            return 2
        if not args.unlinked_reason:
            print(
                "learn-apply: --unlinked requires --unlinked-reason. "
                "45/45 prior policy updates were unlinked and are unmeasurable; "
                "this flag exists so that number stops growing by accident.",
                file=sys.stderr,
            )
            return 2
```

Add `unlinked_reason` to the JSON printed at the end of `cmd_learn_apply`, and persist it: extend
`record_policy_update` in `episode_store.py` with an `unlinked_reason: str | None = None` keyword and
a matching column (Task A2 migration).

**Step 4: Run the test to verify it passes**

Run: `python -m pytest C:/Users/skf_s/.claude/dev-framework/tests/test_learn_apply_linking.py -v`
Expected: PASS, 2 passed.

**Step 5: Commit**

```bash
git -C C:/Users/skf_s/.claude add dev-framework/scripts/devrl.py dev-framework/tests/test_learn_apply_linking.py
git -C C:/Users/skf_s/.claude commit -F <message file>
```

Message: `feat: require --unlinked-reason on unlinked learn-apply deltas`

---

### Task A2: Migration for `unlinked_reason`

**Files:**
- Create: `C:/Users/skf_s/.claude/dev-framework/migrations/0018_unlinked_reason.sql`
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/episode_store.py:1136-1180` (`record_policy_update`)
- Test: `C:/Users/skf_s/.claude/dev-framework/tests/test_episode_store.py`

**Step 1: Read the existing migration convention**

Run: `ls C:/Users/skf_s/.claude/dev-framework/migrations/ && cat C:/Users/skf_s/.claude/dev-framework/migrations/0017_*.sql`
There are 17 rows in `schema_migrations`; match the numbering and the file shape exactly.

**Step 2: Write the failing store test**

```python
def test_record_policy_update_persists_unlinked_reason(store):
    pid = store.record_policy_update(
        trigger="manual", delta_summary="x", episodes_reviewed=None,
        failure_mode_ids=[], skill_changes=[],
        unlinked_reason="orphan skill edit",
    )
    row = store.get_policy_update(pid)
    assert row["unlinked_reason"] == "orphan skill edit"
```

**Step 3: Run it, confirm it fails**

Run: `python -m pytest C:/Users/skf_s/.claude/dev-framework/tests/test_episode_store.py -k unlinked_reason -v`
Expected: FAIL, unexpected keyword argument.

**Step 4: Write the migration and the store change**

```sql
-- 0018_unlinked_reason.sql
ALTER TABLE policy_updates ADD COLUMN unlinked_reason TEXT;
```

**Step 5: Back up the DB, then migrate**

The repo convention is a dated `.bak-` copy before any schema change (see
`episodes.db.bak-20260901-pre-caught`).

```bash
cp C:/Users/skf_s/.claude/dev-framework/episodes.db \
   C:/Users/skf_s/.claude/dev-framework/episodes.db.bak-20260904-pre-0018
python C:/Users/skf_s/.claude/dev-framework/scripts/migrate.py
```

**Step 6: Run the test, confirm PASS, commit**

Message: `feat: persist unlinked_reason on policy updates (migration 0018)`

---

### Task A3: Suggest the cluster instead of making the operator find it

The escape hatch was taken because linking means looking up an integer. Remove that cost.

**Files:**
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py` (`cmd_learn_apply`, before the guard)
- Reuse: `C:/Users/skf_s/.claude/dev-framework/scripts/clustering.py` (existing lexical similarity; do NOT write a new one)
- Test: `C:/Users/skf_s/.claude/dev-framework/tests/test_learn_apply_linking.py`

**Step 1: Use the two helpers that already exist**

`clustering.py:62` defines `_tokens(text) -> frozenset[str]` (lowercases, strips words of 2 chars or
less and a stopword list). `clustering.py:67` defines `_jaccard(a, b) -> float` over two token sets.
Together they are the scorer, and `_cluster_id` at line 73 already uses `_tokens` the same way.

Import both into `devrl.py` and score with `_jaccard(_tokens(summary), _tokens(pattern))`. Do not
write a `difflib` or `SequenceMatcher` variant beside them; a second similarity function is the DRY
violation the eng critic catches. Both are underscore-private inside `clustering.py`, so either
import them directly or promote one thin public wrapper. Do not copy the bodies.

**Step 2: Write the failing test**

```python
def test_missing_link_prints_candidate_clusters(tmp_db_with_pending_clusters):
    r = _run(["learn-apply", "--summary", "critic returned a well-formed fail verdict",
              "--trigger", "manual"], tmp_db_with_pending_clusters)
    assert r.returncode == 2
    assert "did you mean" in r.stderr.lower()
    assert "--failure-mode" in r.stderr
```

**Step 3: Implement**

When `--failure-mode` is absent, call `store.get_pending_failure_modes()`, score each `pattern`
against `--summary` with the existing helper, and print the top 3 as a copy-pasteable line:

```
did you mean one of these? (occurrences x id  pattern)
  x26  --failure-mode 11502   independent-review-critic sub-agent returned a well-formed fail verdict...
  x10  --failure-mode 11546   Plan-stage cap hit (3 fails). Score trajectory 38-58-6 inverted on...
```

**Step 4: Run, confirm PASS, commit**

Message: `feat: suggest matching failure-mode clusters when learn-apply is unlinked`

---

### Task A4: Backfill proposer for the 45 historical updates

Propose-only. A human confirms before anything is written, because `delta_summary`-to-`pattern`
matching is fuzzy and a wrong link corrupts `learn-effect` worse than no link.

**Files:**
- Create: `C:/Users/skf_s/.claude/dev-framework/scripts/backfill_policy_links.py`
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py` (register `learn-backfill` subcommand)
- Test: `C:/Users/skf_s/.claude/dev-framework/tests/test_backfill_policy_links.py`

**Step 1: Write the failing test**

```python
def test_dry_run_writes_nothing(tmp_db):
    before = _count_linked(tmp_db)
    r = _run(["learn-backfill", "--dry-run"], tmp_db)
    assert r.returncode == 0
    assert _count_linked(tmp_db) == before


def test_apply_requires_confidence_threshold(tmp_db):
    r = _run(["learn-backfill", "--apply"], tmp_db)
    assert r.returncode == 2
    assert "--min-score" in r.stderr
```

**Step 2: Run, confirm it fails (no such command).**

**Step 3: Implement**

- `--dry-run` (default): print each of the 45 `policy_updates` rows with its best-matching cluster,
  a 0-1 score, and the reason (summary text overlap, plus episode-id overlap when the summary names
  an episode, e.g. `01M1H905JWGMPA1GGC9PR24JBB`).
- `--apply --min-score X`: write `fix_applied_to = 'policy_update:<id>'` only on rows scoring above X.
- Refuse `--apply` without `--min-score`. Never auto-link below 1.0 without a human.

**Step 4: Run the dry run against the live DB and read every row**

Run: `python C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py learn-backfill --dry-run`
Expected: a 45-row table. **STOP here and show Keith.** He picks the threshold. This is an
ASK-FIRST trigger (schema-affecting write to live data).

**Step 5: Commit the tool, not the backfill.**

Message: `feat: add learn-backfill proposer for unlinked policy updates`

---

### Task A5: Fix the `claude-config-audit` cron

**Files:**
- Modify: `C:/Users/skf_s/clawd/memory/cron-prompts/claude-config-audit.md`
- Cron id: `05558fba-d91c-4cc8-9d6f-dd5fbd6aed50`

**Step 1: Reproduce before changing anything**

Evidence gathered 2026-09-04 from `openclaw cron get 05558fba-d91c-4cc8-9d6f-dd5fbd6aed50`:

| Field | Value | Reading |
|---|---|---|
| `payload.timeoutSeconds` | 2400 | 40-minute budget |
| `lastDurationMs` | 581023 | died at 9.7 minutes |
| `lastError` | `Process: quiet-meadow failed` | the agent process crashed |
| `consecutiveErrors` | 2 | reproducible, not a one-off |
| `lastDeliveryStatus` | not-delivered | Keith never saw the failure |

**This is not a timeout.** The budget is 40 minutes and the run died at 9.7, so it crashed on a
command. Do not "fix" it by splitting the cron or raising the budget — that would be treating the
symptom. Find the failing command first.

Prime suspect is check 5, which shells three `hippo` calls (`status`, `dedup --dry-run`,
`conflicts --status open`) — the prompt's own "Execution guardrails" section was written after
earlier command failures, which says this cron has a history of dying on shell calls. Reproduce by
running each check-5 command by hand and watching for a non-zero exit:

```bash
hippo status
hippo dedup --dry-run --threshold 0.85
hippo conflicts --status open
```

If those pass, walk checks 1-8 in order until one crashes.

**Step 2: Apply the narrowest fix the reproduction supports**

Fix the command that actually failed. Only if the reproduction proves a resource ceiling should the
cron be split. Do not delete checks either way — check 7 (rule vitality) is the one place the
rulebook gets pruned on evidence, and it is the last check to run, so it has almost certainly never
executed since this crash started.

**Step 3: Verify**

Run the cron manually and confirm `lastRunStatus: ok` and `lastDelivered: true`.

**Step 4: Commit the prompt change** in the `clawd` repo (check `git -C C:/Users/skf_s/clawd branch` first).

**DONE 2026-09-04. The diagnosis above was wrong and the prompt needed no change.**

The reproduction cleared check 5: `hippo status`, `hippo dedup --dry-run --threshold 0.85` and
`hippo conflicts --status open` all exit 0 today. So the failing session was read directly:
`C:/Users/skf_s/.openclaw/agents/main/sessions/f56b949b-8d7a-44e1-9b4e-7b6880e43e7a.jsonl`, 79 rows,
08:01:41Z to 08:11:22Z on 2026-09-01. **All eight checks completed and the full report was written**,
ending "No audit changes were made, so no commit was created." The run did not crash on a command.

The report never left the machine. `openclaw cron list` shows every healthy cron delivering
`announce -> telegram:7853053271 (explicit)`; this one alone read
`(resolved from last, main session)`, because its `delivery.channel` was `"last"` rather than a named
channel, and it carried no `agentId`. Resolution failed, openclaw recorded
`Process: quiet-meadow failed` against both the delivery and the run, and a completed audit was
reported as a crash Keith never saw.

Fix applied to the job, not the prompt:

```bash
openclaw cron edit 05558fba-d91c-4cc8-9d6f-dd5fbd6aed50 --channel telegram --to 7853053271 --agent main
```

`openclaw cron list` now shows `(explicit)` and agent `main`, matching the eleven crons that work.
**Verification is outstanding and is Keith's to trigger**: proving delivery means running the real
audit, which sends a Telegram message to his phone, so it is not something to fire unasked. The
command is `openclaw cron run 05558fba-d91c-4cc8-9d6f-dd5fbd6aed50`, and `openclaw cron list` should
then read `ok` with `lastDelivered: true`.

Read this before trusting the next cron diagnosis: the plan asserted a failing shell command from
`lastError` plus a plausible suspect, and the session transcript said the opposite. Read the
transcript first.

---

### Task A6: The memory consolidation loop is a silent no-op

Found while reproducing A5. This is probably the highest-value item in Part A, because every other
loop leans on hippo.

**Observed 2026-09-04, cwd `C:/Users/skf_s`:**

```
$ hippo status                                 -> "No .hippo directory found. Run `hippo init` first."  exit 0
$ hippo dedup --dry-run --threshold 0.85       -> "No .hippo directory found. Run `hippo init` first."  exit 0
$ hippo conflicts --status open                -> "No .hippo directory found. Run `hippo init` first."  exit 0
$ ls C:/Users/skf_s/.hippo                     -> config.json, embeddings.json (13MB, modified today), episodic/, buffer/, conflicts/
$ hippo context --pinned-only --include-recent 2 -> returns 20 memories, works fine
```

The store exists and `hippo context` reads it every prompt. `status`, `dedup` and `conflicts` do not
find it from the same directory. Two consequences, both silent:

1. The `SessionStart` hook prints `consolidating memory... No .hippo directory found` at the top of
   every session in this directory. Consolidation has never run here.
2. Check 5 of the monthly config audit is a no-op, so dedup and conflict resolution never happen.

**The failure mode that matters: all three commands exit 0.** A caller cannot tell "nothing to do"
from "I could not find your data". Every wrapper reports success.

**Root cause confirmed 2026-09-04.** The same command from a project directory works:

```
$ cd C:/Users/skf_s/clawd && hippo status
Total memories: 630   Episodic: 564   Semantic: 66   Pinned: 5   At risk (<0.2): 223
```

So `~/.hippo` is the **global** store and the resolver deliberately does not treat home as a project
store. The resolver is right. The bug is in the harness: **the SessionStart hook and the config-audit
cron both run at cwd `C:/Users/skf_s`, where there is no project store, so they no-op forever.**
This is a wiring fix, not a hippo fix. Do not change hippo's resolver.

**Files:**
- Modify: `C:/Users/skf_s/.claude/settings.json` SessionStart hook (hand-maintained: show Keith, wait for "apply")
- Modify: `C:/Users/skf_s/clawd/memory/cron-prompts/claude-config-audit.md` check 5

**Step 1: Find the flag that targets the global store.**

Run: `hippo status --help` and `hippo --help`. Confirm whether a `--global` flag or `HIPPO_HOME`
env var makes these three commands read `~/.hippo`. `HIPPO_HOME` support shipped in v0.19.0
(memory `project_hippo.md`), so it likely exists. Do not guess the flag — read the help output.

**Step 2: Rewire the SessionStart consolidation hook** to pass that flag, or to run against a real
project store. Verify by starting a session and confirming the notice is replaced by a real
consolidation line.

**Step 3: Rewire config-audit check 5** the same way, and add the expected non-empty output to the
check so a future no-op is visible as a FLAG rather than a silent PASS.

**Step 4: Raise the exit-code issue upstream in the hippo repo** (`C:/Users/skf_s/hippo`, see
`AGENTS.md`). `hippo status` exits 0 when it finds no store, so every wrapper reads "success". That
is worth a non-zero exit or a distinct message, and it is the reason this went unnoticed for months.
Separate commit, separate repo, lower priority than steps 1-3.

**Step 5: While the store is readable, note the decay number.** clawd's store reports 223 of 630
memories at risk (strength <0.2) and avg strength 0.44. That is a Part B input, not an A6 fix —
record it, do not act on it here.

**DONE 2026-09-04. Both premises above are wrong. Corrected below.**

Wrong claim 1: "all three commands exit 0". They exit **1**. The plan measured
`hippo status 2>&1 | tail -12; echo "exit=$?"`, so `$?` was `tail`'s status, not hippo's.
`requireInit` in `hippo/src/cli.ts:288-293` prints the message and calls `process.exit(1)`.
Step 4 (raise the exit-code issue upstream) is therefore moot and is dropped.

Wrong claim 2: "`~/.hippo` is the global store and the resolver deliberately does not treat home
as a project store." The opposite is true. Reproduce:

```
$ (cd C:/Users/skf_s        && hippo status)   -> Total memories: 1665   exit 0
$ (cd C:/Users/skf_s/.claude && hippo status)  -> No .hippo directory found   exit 1
$ (cd C:/Users/skf_s/clawd   && hippo status)  -> Total memories: 630    exit 0
```

Home works. Every subdirectory fails. Hippo resolves the store as `<cwd>/.hippo` with no
upward walk, and `status`, `dedup` and `conflicts` ignore both `--global` and `HIPPO_HOME`
even though `init` and `remember` accept them. That selector gap is the real root cause.

Wrong claim 3: "check 5 of the config audit is a no-op". It runs. The preflight sets
`--workspace C:\Users\skf_s\clawd`, which has its own store, so check 5 has been auditing
clawd's 630 memories every month while the 1665-memory home store was never audited. The
2026-09-01 report's "627 memories" is clawd's number, which is what made this look healthy.

**Fixed:** `clawd/memory/cron-prompts/claude-config-audit.md` check 5 now pins both store
directories with `Push-Location`, reports a count per store, and treats the not-found line or a
non-zero exit as a FLAG rather than a silent PASS.

**Not fixed, for Keith:**
1. `status`, `dedup` and `conflicts` should honour `--global` / `HIPPO_HOME` like `init` and
   `remember` do. That is a change in `C:/Users/skf_s/hippo`, a published npm package. The repo
   working tree is on `antislop-migration` at 1.29.0 while the installed CLI is 1.38.0, so this
   needs its own branch and release cycle.
2. `hippo session-end` (the SessionEnd hook, `settings.json:113`) inherits the session's cwd, so
   the consolidation silently does nothing for any session started outside a directory that has a
   `.hippo`. That is what wrote `consolidating memory... No .hippo directory found` into the
   SessionStart banner at 2026-09-04T12:00:38Z. Until item 1 lands there is no flag to pin it,
   and wrapping the hook in a `cd` is a downstream patch, so it waits.
3. `session-end` is not listed in `hippo --help`.

Step 5 stands: the decay numbers are a Part B input. Home store: 1665 memories, 472 at risk
(<0.2), avg strength 0.56, 686 stale. clawd store: 630 memories, 223 at risk, avg strength 0.44.

---

## Part B — give every component a scoreboard

Part B is worthless until Part A proves the write-back path works, so it starts only when A4's
backfill has landed and `learn-effect` reports a non-zero `applied fixes` count.

### Task B1: `component_outcomes` table

**Files:**
- Create: `C:/Users/skf_s/.claude/dev-framework/migrations/0019_component_outcomes.sql`
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/episode_store.py`
- Test: `C:/Users/skf_s/.claude/dev-framework/tests/test_component_outcomes.py`

**Design note (read before writing the DDL):** this goes in `episodes.db`, not a new file.
`critic_trust_scores`, `audit_rule_firings` and `policy_updates` already live there, and the
weekly cron already opens it. A second database would split the exact join the scoreboard needs.

**Concurrency step, do this before B2 registers the hook.** `episode_store.py` sets exactly one
PRAGMA today, `foreign_keys = ON`, at line 77 in `_write` and line 92 in `_read`. There is no WAL
and no busy timeout. `_write` opens with `BEGIN IMMEDIATE`, which takes the write lock for the
whole block, so in rollback-journal mode a devrl run holds the database and the hook's insert fails
instantly with `database is locked` rather than waiting. Under WAL the same insert proceeds.

Add to both context managers, next to the existing PRAGMA:

```python
conn.execute("PRAGMA journal_mode = WAL")
conn.execute("PRAGMA busy_timeout = 3000")
```

`journal_mode` is persistent once set and is a no-op on later connections; `busy_timeout` is
per-connection and must be set every time. The hook in B2 sets both itself, because it opens its
own connection and never goes through this class.

Its test: open a `_write` block against a temp DB, hold it, and from a second connection insert one
`component_outcomes` row. Expect the insert to succeed. Run that test against the pre-PRAGMA code
first and watch it fail with `database is locked`, or the test is not proving anything.

```sql
-- 0019_component_outcomes.sql
CREATE TABLE component_outcomes (
    id           INTEGER PRIMARY KEY,
    kind         TEXT NOT NULL,        -- 'skill' | 'agent' | 'hook' | 'rule' | 'cron'
    name         TEXT NOT NULL,        -- skill slug, subagent_type, hook filename
    session_id   TEXT,
    episode_id   TEXT,                 -- nullable: most invocations sit outside an episode
    invoked_at   TEXT NOT NULL,
    blocked      INTEGER DEFAULT 0,    -- hook denials only
    cwd          TEXT
);
CREATE INDEX idx_component_outcomes_name ON component_outcomes(kind, name);
CREATE INDEX idx_component_outcomes_session ON component_outcomes(session_id);
```

Steps follow the A2 pattern exactly: failing test, `.bak-20260904-pre-0019` copy, migrate, pass, commit.

---

### Task B2: PostToolUse recorder hook

**Files:**
- Create: `C:/Users/skf_s/.claude/scripts/hooks/component-recorder.js`
- Modify: `C:/Users/skf_s/.claude/settings.json` (PostToolUse block)
- Test: `C:/Users/skf_s/.claude/dev-framework/tests/test_component_recorder.py`

**Template:** copy `C:/Users/skf_s/.claude/scripts/hooks/suggest-compact.js` — it is the only
currently registered PostToolUse hook, so its stdin-read / never-block shape is proven on this box.
Take the field-access pattern (`input.tool_name`, `input.tool_input`) from
`comment-budget-guard.js:87-89`.

**Verified input contract:**
- `tool_name` is `"Skill"` or `"Agent"` (both confirmed in live transcripts under
  `C:/Users/skf_s/.claude/projects/C--Users-skf-s/*.jsonl`).
- Skill slug is `tool_input.skill`. Agent type is `tool_input.subagent_type`.
- Also available: `session_id`, `cwd`, `transcript_path`.

**Step 1: Write the failing test** — pipe a recorded PostToolUse payload into the hook, assert one
row lands in a temp DB with `kind='skill'`, `name='writing-plans'`.

**Step 2: Run, confirm it fails.**

**Step 3: Implement.** Hard requirements, in order of importance:
1. **Never block.** Wrap everything in try/catch, always `process.exit(0)`, print nothing on success.
   A recorder that breaks a tool call is worse than no recorder.
2. Single INSERT, WAL mode, no reads.
3. Register with `"timeout": 5` to match the other JS guards.

**Step 4: Register in settings.json.**

This file is hand-maintained. Show Keith the proposed block and wait for "apply" before writing
(global CLAUDE.md, Hand-Maintained Files). Proposed addition to the existing PostToolUse array:

```json
{
  "matcher": "Skill|Agent",
  "hooks": [{ "type": "command", "command": "node \"C:/Users/skf_s/.claude/scripts/hooks/component-recorder.js\"", "timeout": 5 }]
}
```

**Step 5: Verify live.** Invoke any skill, then:
`python -c "import sqlite3;print(sqlite3.connect(r'C:/Users/skf_s/.claude/dev-framework/episodes.db').execute('select kind,name,invoked_at from component_outcomes order by id desc limit 5').fetchall())"`
Expected: the skill you just ran, at the top.

**Step 6: Commit.**

---

### Task B3: Record hook denials

A denied tool call never reaches PostToolUse, so blocks are invisible to B2. The five PreToolUse
guards already know when they deny.

**Files:**
- Modify: `pre-bash-guard.js`, `commit-msg-guard.js`, `ps-stderr-guard.js`, `pre-write-guard.js`,
  `comment-budget-guard.js` (each in `C:/Users/skf_s/.claude/scripts/hooks/`)
- Create: `C:/Users/skf_s/.claude/scripts/hooks/lib/record-component.js` (one shared writer)

**Do not paste the same insert into five files.** That is the "same one-line guard in N call-sites"
patch smell from the global CLAUDE.md. Extract `record-component.js` first, then have each guard
call it on its deny path with `kind='hook'`, `blocked=1`.

Steps: failing test on one guard, extract the helper, wire all five in one pass (Bug Fixes rule:
fix all instances in one pass), verify each still denies correctly, commit.

---

### Task B4: `component-report` and the weekly read

**Files:**
- Modify: `C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py` (new `component-report` subcommand)
- Read as a pattern, do not call: `C:/Users/skf_s/.claude/dev-framework/scripts/critic_trust.py`
- Modify: `C:/Users/skf_s/clawd/memory/cron-prompts/devrl-weekly-learn.md`

**Reuse the pattern, write new SQL.** `compute_trust_counts` (`critic_trust.py:138`) is not callable
here. It walks `steps` JOIN `episodes` (line 178-179) and counts critic verdicts, retry caps and
linkage cells. A component invocation has none of those: `component_outcomes` has no verdict and
usually no `episode_id` at all. Calling it would mean forcing component rows into a critic shape,
which is the wrapping-a-broken-thing patch smell.

What to copy is the scoring discipline in `TrustCounts.trust_score` (`critic_trust.py:79-92`), which
is three rules worth reusing verbatim:
1. Return `None` below `MIN_OBS_FOR_SCORE`, never a score from two data points.
2. Score as matches over matches-plus-mismatches with the same Beta prior constants.
3. Keep raw counts in the row beside the score, so a null is auditable.

Write a separate `component_counts` aggregation with its own SQL over `component_outcomes`. Put the
shared prior constants in one place rather than retyping the numbers.

**Defining "helped" honestly.** `used` is free. `helped` is an attribution problem. For a component
used inside an episode, join to that episode's `post_deploy_clean`. Components used outside an
episode get `used` counts only and an explicit `trust: null`. **Report null, never a made-up score.**
The same rule that governs `policy_compact_report` governs this: absence never demotes.

Output shape:

```
kind    name                  used  in_episodes  clean  regressed  trust
skill   writing-plans           47           12     11          1   0.92
skill   frontend-mix             3            0      -          -   null
agent   senior-code-reviewer    31            9      7          2   0.78
hook    comment-budget-guard    88            -      -          -   null (blocks: 12)
```

Then add one line to the weekly cron prompt so the number is read every Monday. The cron stays
propose-only for pruning; the same reasoning as the audit rules.

---

### Task B5: Fold the manual telemetry sink into the same table

`C:/Users/skf_s/.claude/skills/dev-framework/logs/telemetry.jsonl` is a hand-written gate log
(`{timestamp, project, gate, phase, outcome, notes}`, 4055 bytes, last written 2026-09-02). It is a
third sink for the same question. One sink, or the join in B4 lies by omission.

**Files:**
- Create: `C:/Users/skf_s/.claude/dev-framework/scripts/import_gate_telemetry.py` (one-shot importer)
- Delete: `C:/Users/skf_s/.claude/skills/dev-framework/scripts/log-gate.ps1` (1251 bytes)
- Delete: `C:/Users/skf_s/.claude/skills/dev-framework/scripts/telemetry-report.ps1` (3237 bytes)
- Modify: `C:/Users/skf_s/.claude/skills/dev-framework/SKILL.md` (lines 91-115 and 138-141)

**Step 1: Import the history.** Read the JSONL, write one `component_outcomes` row per entry with
`kind='gate'`, `name=<gate>`, `invoked_at=<timestamp>`, `cwd=<project>`. Map `outcome` to the
existing columns: `caught` and `failed` are the blocking outcomes, so set `blocked=1` for those and
0 for `passed` and `skipped`. Keep `notes` by adding one nullable `notes TEXT` column in 0019 rather
than dropping the text; the "you've never used /cso but caught 3 auth bugs" read in B4 depends on it.

**Step 2: Retire the two PowerShell scripts.** They are the writer and the reader for a sink that no
longer exists. `log-gate.ps1` appends to the JSONL; `telemetry-report.ps1` aggregates it. Leaving
either in place means a future session logs a gate outcome into a file nothing reads, which is the
same silent no-op as A6. Delete both, and delete `logs/telemetry.jsonl` and `telemetry.jsonl.old`
only after the importer's row count matches the file's line count.

**Step 3: Repoint SKILL.md.** Its "Telemetry: log which gates caught real issues" section (lines
91-115) documents both scripts with worked examples, and the file list at lines 138-141 names all
three artifacts. Replace with the `devrl.py` equivalents. This file is hand-maintained: the edits are
targeted, so they proceed, but do not rewrite the file wholesale.

**Retirement is a deletion, so it is ASK-FIRST.** Show Keith the two script paths and the row-count
proof before removing anything.

---

## Verification for the whole plan

Done means all of these, run in one pass:

```bash
python -m pytest C:/Users/skf_s/.claude/dev-framework/tests/ -q
python C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py learn-effect
python C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py learn-cluster
python C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py learn-effect
python C:/Users/skf_s/.claude/dev-framework/scripts/devrl.py component-report
openclaw cron get 05558fba-d91c-4cc8-9d6f-dd5fbd6aed50
```

Pass conditions:
1. Full devrl suite green.
2. `learn-effect` reports a non-zero `applied fixes` count, so the loop can finally be scored.
3. **The two `learn-effect` runs report the same count.** `learn-cluster` between them recomputes
   clusters and calls `replace_failure_modes`, the exact path A0b fixes. A count that drops across a
   recompute means the links are not durable and A0b did not hold, whatever its unit test says. This
   is the gate that matters: a one-shot backfill that a routine recompute silently erases is worth
   nothing, and the count-before / count-after pair is the only check that catches it.
4. `component-report` lists real skill and agent rows recorded by the hook, not by hand.
5. `claude-config-audit` shows `lastRunStatus: ok`.

If 2 still reads `applied fixes: 0` after A4, Part A has not landed and Part B must not start.
If 3 fails, Part A has half-landed, which is worse: the report reads healthy right after a backfill
and decays on its own. Fix A0b before touching Part B.

Take a `.bak` of `episodes.db` before this pass. `learn-cluster` writes.
