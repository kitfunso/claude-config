---
name: prune-tests
description: "Make a repo's commit gate (CI) fast and green: time each hook, fix red tests, narrow what a change runs, and cut tests that catch no bug another test catches, proved with planted bugs and replayed past fixes. Use when asked to clean up, dedupe or trim tests, cut useless or redundant tests, make tests or CI faster, or get CI green."
---

# prune-tests

The rule (fewer-tests, Keith 2026-10-16): a test stays only if it catches a plausible bug no other
test catches. This skill makes that rule a measurement. A **mutant** is a planted bug: one small edit
to the code (`<` to `<=`, `+` to `-`, a constant plus one, `return x` to `return None`). A test
**kills** a mutant when it goes red on it. The **kill matrix** records which tests kill which mutants.
A test whose kills are all shared with other tests adds run time and no protection.

"CI" on Keith's boxes is the commit **gate**: the pre-commit hooks (code-health's ratchet, env-lock,
venv-run tests, gitleaks) that run before each commit; there is no CI server. The goal is a gate that
runs **green** and fast on a typical change. Three levers, in the order they usually pay: fix the red
tests, narrow what a change runs, cut tests with no unique catch. Cuts alone rarely move the minutes
(one app repo: removed tests saved 69 s of 991 s); a few **heavy** tests hold them. Measure
the gate first. Across many repos, run stage 1 everywhere, then spend the long stages on the repos
whose gate holds the minutes.

## Setup

- `PY` = the repo's own venv interpreter (full path). It needs pytest 8.2+ (argument files) and
  coverage. Run every script with it: `$PY $SK/scripts/<script>.py`, with `SK=~/.claude/skills/prune-tests`.
  A venv without coverage gets it from `PYTHONPATH=<code-health>/.tools/cov312` (coverage 7.16,
  py3.12), never a pip install: the env-lock hook fails a venv that drifts from its lock.
- Read the box load first (CPU percent, other sessions' python processes). Another session's run can
  hold most cores; keep your workers under what is left, and time nothing until the box is quiet.
- `RUN` = a run folder in the session scratchpad; every JSON and the report land there.
- Every pytest run the scripts start runs at Windows Low integrity (`scripts/sandbox.py`): it reads
  every file, but it can write only under its own LocalLow temp folder (`TEMP`, `tmp_path`). A planted
  bug that sends a write to a live data folder, a main checkout or the profile gets access denied,
  whatever library writes. Before this sandbox, a mutant wrote two fixture rows into a live data file.
  A test that writes outside its temp folder goes red at baseline and drops out, as it must. Profile,
  map and kills record the sandbox; kill, verify and replay refuse inputs made outside it, and a
  `.partial.jsonl` older than its inputs. Each run first proves that the sandbox blocks a write.
- The scripts rewrite source files while they work, so they only run in scratch worktrees:
  `git -C <repo> worktree add --detach $WT/base/<repo-folder-name> <upstream tip>`. Fetch first and
  take the upstream tip, never the local branch: one repo's local branch sat a week and 119
  commits behind origin while other sessions worked. Keep the repo's folder name: a repo root
  holding `__init__.py` imports its tests through that name.
- Put the ignored files the tests read into the worktree
  (`git ls-files --others --ignored --exclude-standard`): hardlink secrets (`.env`, creds) so no
  second copy lands on disk, and copy the rest, since a planted bug can write through a hardlink.
  Extra workers get the same: a hardlink where the worktree has one, else a copy. Copy in one bulk
  pass (`tar` or a Python loop): a per-file shell loop takes an hour on a 10k-file data folder.
  Leave `.venv` out; junction a tool folder the tests call (code-health's tests run `.tools/jscpd`).
- Copy the untracked files a test reads too: a test can check untracked `docs/*.html` pages that a
  tracked index names.
- A repo that finds a sibling repo by a path relative to its own folder loses it in a scratchpad
  worktree: set the env var the repo reads that path from. Profile and map
  stop on a collection error rather than write an empty file.
- A sub-project with its own venv (`<repo>/<sub-project>`) imports itself through an editable
  install that points at the main checkout: put the worktree's `src` first on `PYTHONPATH`, root
  pytest in the sub-project (`PYTEST_ADDOPTS="--rootdir=. -c pyproject.toml"`, else node ids carry
  the parent's prefix), and run one worker, since extra workers are whole-repo worktrees.

## Stages

Each stage ends on its done-when line. Write findings to `$RUN/notes.md` as you go.

**0. Read.** Find what runs the tests (pytest.ini, pyproject, conftest, hooks, the repo's CLAUDE.md
test rules). Check for a **freeze**: code that hashes files into a ledger (td3c, brent-structure and
wb-forecast do; grep `hashlib` near ledger, freeze or lock). If test files are inside the hash,
stop and tell the user: cutting them voids the track. Name the **exempt** globs: guards born from
incidents (no-typed-numbers, call style, desk-check guards), contract tests against outside data,
and tests that read source files as text. Planted bugs do not model what these protect.
Done when: runner, freeze status and exempt globs are in notes.md.

**1. Profile and time the gate.** `prune.py profile --repo $BASE --python $PY --out $RUN/profile-before.json --runs 1`.
Then time the gate on two or three typical changes, the source files `git log -50 --name-only`
shows most often. In a scratch worktree with the ignored files and a `.venv` junction, stage a
one-line edit, run `pre-commit run --verbose`, and note each hook's duration and the test files the
change reaches (code-health `ratchet.affected.tests_reached`). Done when, for each typical change,
you can say where the gate's minutes go: which hook, which test files, which heavy tests.

**2. Green.** List the tests that fail before any change. Rerun each alone with plain pytest in the
repo's own environment: one that passes there is a runner artifact (a harness that spawns its own
Python can fail under the runner's environment); note it. One that still fails is **red**. Fix each
red at its root, one `fix:` commit through the gate, when the repo is ours; report it to its owner
otherwise. A red test catches nothing, and every later stage leaves it out, so start them from the
green commit. Done when every baseline failure is an artifact, fixed, or reported in notes.md.

**3. Map and candidates.**
`prune.py map --repo $BASE --python $PY --out $RUN/map.json` runs the suite under coverage with
one context per test (the bundled `prune_plugin.py`), giving each test's line set.
`prune.py subsets --map $RUN/map.json --profile $RUN/profile-before.json --exempt <globs> --out $RUN/candidates.json`
flags each **candidate**: a test whose lines all sit inside another test's lines.
Every other test is a **keeper**. Done when candidates.json exists and you have read its
`no_coverage` list (tests that ran no repo line: guards that read source, constant pins).

**4. Kill matrix.**
`mutate.py kill --repo $BASE --python $PY --map $RUN/map.json --candidates $RUN/candidates.json --profile $RUN/profile-before.json --out $RUN/kills.json --workers N`.
It plants mutants on lines the candidates run. Per mutant it runs the covering candidates in full,
then, if one killed it, the covering keepers fastest-first and stopping at the first red.
It first breaks a target file outright and refuses to go on if the covering tests stay green (a
blind run). Pick N near a third of the cores for a suite with heavy tests, and run it in the
background. Each result is saved as it finishes, so rerunning the same command resumes a crashed
run. Tests that fail before any change are left out of every pass. Then:
`prune.py plan --kills $RUN/kills.json --candidates $RUN/candidates.json --profile $RUN/profile-before.json --map $RUN/map.json --out $RUN/plan.json`.

When heavy candidates (page renders, seconds each) sit on many lines, one pass can run for days:
size it first by summing each mutant's covering-candidate seconds plus one pytest start per mutant
(4-8 s on Windows, often the larger term). Then run two passes. `prune.py
split --seconds 2` writes the light and heavy candidate files and a skip list for each.
Pass 1 scores the light candidates with `--skip skip-heavy.txt`. Pass 2 scores the heavy ones
with `--skip plan-light.json` after pass 1, or with `--skip skip-light.txt` alongside it, in its
own base worktree. Either way no cut leans on a test the other pass may cut. A test whose only
twin sits in the other pass stays, the safe direction. `--max-mutants` may sample pass 2; the report then
says those cuts rest on a sample. `prune.py merge --plans plan-light.json plan-heavy.json --out
plan.json` joins them, and verify takes both kills and plans in the same order.
A greedy **set cover** keeps the fewest candidates that still kill every mutant only candidates
kill (fastest test wins a tie); the rest form the cut ledger, each row naming the tests that now
catch its bugs. Done when plan.json exists.

**5. Judge the ledger.** Read the body of every cut test and every no-coverage test.
- Keep a cut test that guards what mutants cannot plant: string keys that feed a join, an
  exception contract, a file format read outside the repo. Note why in notes.md.
- Cut, even with a unique kill: tests that pin a constant, a message or a format, and tests of a
  one-off script whose run is done (the script stays).
- No-coverage tests: a guard joins the exempt list; a pin is cut; anything else stays.
Done when every ledger and no-coverage row has a decision in notes.md.

**6. Cut and narrow.** In a second worktree at the base commit (`git worktree add --detach $SLIM <base sha>`),
delete the cut tests, and fold near-duplicates (same body, different values) into one
`parametrize` table. Touch tests only; source must stay byte-identical or verify refuses.
Narrow what a change runs where stage 1 shows one heavy file on most changes. The gate picks whole
test files by import, so a helper imported at the top of a page-render file pulls every page into
every edit of that helper. Give each heavy case its target (the page it renders) and skip a case
whose target the change does not reach: code-health's `venv-run` hands pytest the reached files in
`RATCHET_AFFECTED` (`--each` always, `--tests` from branch feat/tests-name-reached), and
one app repo's characterisation and page-smoke render-only cases skip on it. Skip only a
case that asserts nothing beyond its page; one that asserts through a shared helper runs whenever
its file does. Where the gate cannot hand over the reached set, mark heavy tests
(`@pytest.mark.heavy`, registered in the pytest config) for a per-change `-m "not heavy"`. The
default run keeps every test: a heavy test that alone catches its bugs is still protection, and the
stopwatch must compare like with like. Remove fixtures and helpers the cut left unused. Commit on
the detached HEAD: stage 7 runs on that commit. Done when the slim suite passes, minus the stage 2
runner artifacts.

**7. Prove it.** Four checks, none of them your own judgement:
- Planted bugs: `mutate.py verify --repo $SLIM --python $PY --kills $RUN/kills.json --plan $RUN/plan.json --out $RUN/verify.json`
  re-plants every bug a cut test killed and runs the tests the plan says now catch it (`--workers`
  as in stage 4). Lost must be 0; each lost bug means restore its cut test.
- Past bugs: `replay.py --base $BASE --slim $SLIM --python $PY --map $RUN/map.json --plan $RUN/plan.json --profile-before $RUN/profile-before.json --profile-after $RUN/profile-after.json --out $RUN/replay.json`
  takes up to 20 recent `fix:` commits, reverse-applies each fix's source diff onto today's code
  in both worktrees, and runs the cut tests and the slim tests that cover the rewritten lines.
  A row reads **lost** when only a cut test went red; restore that test.
- Stopwatch: on a quiet machine, `profile --runs 3` on base then on slim
  (`profile-before.json`, `profile-after.json`), and the same for one typical per-change selection
  (`change-before.json`, `change-after.json`, pytest args after `--`).
- Gate: re-time the stage 1 typical changes on the slim commit, per hook (`gate-before.txt`,
  `gate-after.txt`). Each must run green.
Then `prune.py report --dir $RUN --out $RUN/report.html`, open it, and copy it next to the repo's
other reports if it has a docs folder. Now name the branch, on a fresh commit of the slim tree whose
message carries the numbers: gate minutes per typical change before and after, tests before and
after, full-run and per-change medians, both lost counts.
`git -C $SLIM branch chore/prune-tests $(git -C $SLIM commit-tree HEAD^{tree} -p <base sha> -F msg.txt)`.
Done when lost is 0 on both bug checks, the gate runs green on every typical change, all timing
files exist, and the branch carries the numbers.

## Grading a cut that already landed

When tests were already cut by hand or by another session, grade that cut before cutting more.
Run the profile (stage 1) and the map (stage 3) on the commit before it (`$BASE`), put the cut commit in `$SLIM`, then
`prune.py grade --map $RUN/map.json --profile $RUN/profile-before.json --slim $SLIM --python $PY --out-dir $RUN`.
It lists the removed tests and the **orphaned** lines, source lines that only removed tests ran.
`mutate.py kill` with `--map map-orphan.json --candidates candidates-removed.json` plants bugs on
those lines: no remaining test runs them, so every catch is a catch the cut lost. That count is
a floor: a removed test can also be the only one that checks a line others merely run, which a
kill run over the removed tests' full lines finds. `replay.py
--plan removed.json` replays fix commits across the cut. Restore, on a branch, each removed test
that alone catches a planted bug or a replayed fix. Judge each restore as in stage 5, so a pin stays
cut, and pick the set by run time: a unit test beats a page render that catches the same bug.

## Handover

Chat: gate minutes per typical change before and after, reds fixed or reported, tests before and
after, and the two lost counts. Everything else is in the report. Remove the scratch worktrees
(`git worktree remove --force`) once the branch is committed.

## Gotchas

- Session-scoped fixture setup is credited to the first test that triggers it, so that test looks
  broader than it is. Coverage only flags candidates; the kill matrix decides.
- Lines run at import (module constants) belong to no test, so no mutant lands there.
- Each parametrized case is its own node id; cutting one case means editing its parameter list.
- The runner sets `PYTHONDONTWRITEBYTECODE` and deletes the mutated file's `.pyc`: a mutant of the
  same size, written in the same second, can otherwise run from stale bytecode.
- A busy box times batches out, not just bugs: after a timeout each unfinished test re-runs alone,
  and only one that fails or hangs alone counts. Keep all workers, across every session, under the
  core count, or those re-runs eat the pass.
- A keeper run that hits `--budget` counts as no keeper kill, so its candidates stay. The report
  counts these; raise the budget if they are many.
- mutmut and cosmic-ray record one killed-or-survived result per mutant, and mutmut needs `os.fork`
  (WSL on Windows). The kill matrix needs every killing test, hence the bundled runner.
