# Incident & measurement archive

Stories evicted from the always-loaded rules. This file is never injected; rules
point here with one-liners. Append new entries at the top; do not rewrite history.

## 2026-09-14: the work box cut the same file a day later, then merged

The work box (kit.sofun) audited its copy on 14 September without knowing the home
box had cut it on the 13th, and rewrote CLAUDE.md to about 3,400 tokens (chars / 3.8)
with a `docs/rulebook.md` for the maintainer material. Merged on the 14th with the
home box core as the base: it carries the Haiku ban, the Fable exec budget, the
harness-override section, tests and this log, none of which the work box had. Kept
from the work box: Outside Voice narrowed to contracts, migrations, new architecture
or an explicit review ask (the ">3 steps" trigger fired on routine work); the
reply-shape lines (like I'm 5, 2 options max); a conditional GPU line, since the two
boxes differ; the think-before-coding bullet that karpathy-guidelines.md now points
to; a Python port of the PS stderr guard; and a `git_guard.py` fix so `git -C /c/...`,
`$VAR` paths and `cd X && git` no longer report "not a git repository".
`measure_context.py` now derives the home and project paths instead of hardcoding
skf_s. `rulebook.md` is dropped as a duplicate of the hooks table, precedence and
rulebook discipline already in the core. Work-box hooks registered as of this date:
capability existence, git guard, backup, PS stderr, comment budget (all `.py`). The
tripwire and Fable budget are not registered there yet.

## 2026-09-13: the per-prompt tax cut to a core

Keith asked whether the .md files and the harness were limiting the models. Measured
with tiktoken cl100k_base on the injected text: 27,164 tokens of Keith-controlled
context on every prompt (skill listing 8,987; global CLAUDE.md 7,779; MEMORY.md
5,301; agent listing 1,779; hippo 1,474; rules 1,171; ~/CLAUDE.md 673). Five weeks
of transcripts: 174 cache-read tokens per output token; 25 of 160 skills used in
September; Bash 64% of main-thread tool calls against 5.5% for Read, Grep and Glob;
the diagnosis block on 6.3% of prompts. Report:
https://claude.ai/code/artifact/392d6fa1-d9ea-4471-8165-615fd821f575.

Applied the same day on "go" then "apply": 72 skill dirs to `skills-archive/` and 20
agents to `agents-archive/`, each with a MANIFEST.md restore command; the global
CLAUDE.md cut from 313 lines to a 145-line core, the pre-cut text frozen verbatim in
`docs/claude-md-extended.md`; MEMORY.md back to a pointer index; hippo pin hygiene;
the 2chain key out of settings into an env var; sentry and suggest-compact
deregistered. Cut sheet:
https://claude.ai/code/artifact/36ac0822-189c-4a5d-9c13-70dcdf0996e1.

Corrected later the same day. Archiving by transcript usage count broke live skills:
32 of the 72 dirs were dependencies of kept skills and were restored in two closure
passes. All 9 hyperframes dirs are routed to from general-video, product-launch-video,
frontend-mix and media-use, which also read `../hyperframes-core/references/...`; 23
gstack command dirs are reached through a shared router menu duplicated across about
15 kept SKILL.md files, clearest copy at `skills/_gstack-command/SKILL.md:275-593`,
plus design-html and design-shotgun from `skills/frontend-build/SKILL.md:26,46` and
`skills/frontend-mix/SKILL.md:72`. Thirty-nine dirs stay archived: 31 seo, plus
ios-clean, ios-design-review, ios-fix, ios-qa, ios-sync, landing-report, scrape and
skillify. The lesson is its own memory, `archive-skills-by-dependency-closure`: grep
every kept skill for `/name`, `../name`, `skills/name` and `name/SKILL.md` before
moving a dir, and repeat until a pass finds nothing.

The same defect was then found in an older archive. A 2026-09-12 prune had parked 54
zero-use skill dirs in `skills-parked/` by the same transcript count, and nobody had
closure-checked it. Fourteen were dependencies and are restored: gstack-upgrade,
browse, careful, guard, learn, make-pdf, open-gstack-browser and devex-review from the
router menu in `skills/_gstack-command/SKILL.md`; benchmark-models and eval-driven-dev
from `skills/dev-framework/overlays/ai-agent.md:13,29`; search-first and commit from
`skills/dev-framework/scripts/status.ps1:14,20`; test-driven-development from
`skills/dev-framework/PIPELINE.md:65`; and git-commit-helper from
`docs/agent-routing.md:42`. Those had been broken since 12 September. A fifteenth,
thermo-nuclear-code-quality-review, went back later the same day: the check had
rejected `skills/improve-docs-architecture/SKILL.md:10` as design lineage rather than
a route, which reads correctly, but the line still prints a slash command that would
not resolve and the skill carries `disable-model-invocation: true`, so restoring it
costs nothing in the listing. Where the hit is arguable and the token cost is zero,
restore. Thirty-nine stay parked. Of 129 candidate lines, 91 were rejected, most of them paths into
`skills/gstack/`, which is a separate checkout carrying its own copies of the same
names.

That restore then broke the first archive's closure, which had been certified while
the parked check was still running. `make-pdf` came back from `skills-parked/` and its
line 655 routes to `/diagram`, still sitting in `skills-archive/`, so `diagram` is
restored too and the archive drops to 39. A re-run over all 79 names still held in the
two archives leaves two hits, both rejected: a sheetjs CDN URL in
`skills/skill-creator/eval-viewer/viewer.html:10`, and `skills/diagram/SKILL.md:857`
warning that a browser tab may belong to "a live /qa or /scrape session sharing the
daemon", which names `scrape` as a concurrent user of the daemon and not a route to
it. Second lesson: two closure checks running at once each certify a set the other is
about to widen. Run them in sequence, or re-run the earlier one after the later lands.

Post-restore measurement, all figures from `scripts/measure_context.py` on this date:
17,428 tokens a prompt (skill listing 4,646 for 111 model-invocable skills; global
CLAUDE.md 3,757; MEMORY.md 3,693; agent listing 784 for 8 agents; hippo memory block
1,991 plus a 713-token Active Task Snapshot left by another session; rules 1,171;
~/CLAUDE.md 673). Against a 13 September baseline of 26,050 that is a 33 percent cut,
not the 41 percent first reported. Only 14,724 of that total is config text and holds
still; the two hippo lines float by a hundred tokens either way from one prompt to the
next, because the hook fills a fixed budget and the snapshot tracks the live session,
so a re-run lands near 17,430 rather than on it. The archive is worth 2,633 tokens a prompt across
39 skill dirs and 854 across 20 agents, against the roughly 6,000 the cut list
projected for skills alone; the parked set still holds 1,204 tokens across the 34
model-invocable of its 39 dirs. The script that produced the 27,164 and 15,930 figures
above died with the session scratchpad and counted the skill listing about a third
higher, so treat the two pairs as non-comparable at the level; trust deltas taken
within one script. Three counts that look inconsistent and are not: `skills/` holds
136 directories, 125 of them with a top-level SKILL.md, and 111 of those reach the
model, because the rest carry `disable-model-invocation: true` and the script counts
only what is injected. Hippo self-reports 1,500 for what costs 1,991
in cl100k.

Hippo pass, same day, after Keith asked what it costs. It was 2,663 of 17,387, a
sixth of the whole prompt, and the block was serving the wrong 17 entries. Two causes.
First, the snapshot: `hippo context` prepends the Active Task Snapshot, so the
UserPromptSubmit hook reprinted 821 tokens of the last pre-compact summary on every
prompt, while SessionStart already runs `hippo compact-resume`, which delivers the same
snapshot once, at the only moment a discarded transcript makes it worth anything.
`scripts/hooks/hippo_context_cached.py` now cuts everything before `## Project Memory`
before it writes the cache; the fix belongs in the wrapper, not in hippo, because
compact-resume needs the snapshot. Second, the pins: 23 pinned memories held 3,355
tokens against a 1,500 budget, so hippo dropped six by a ranking that kept a March 2026
roadmap for work already shipped and dropped an item marked OPEN on 10 September. Four
were forgotten for being wrong, not merely old: two stale hippo roadmaps that describe
the SQLite and DAG backbone as future work, a `NEVER use --no-verify` pin that
contradicts the Git Operations rule allowing it on an explicit ask, and one of two
same-day entries that disagreed on whether 3 or 8 mattpocock skills were vendored.
Eight more were unpinned rather than forgotten, so they stay recallable: the two
largest were `bitfall` at 371 and `fifty` at 604, project state that MEMORY.md already
points at through a file that is the source of truth and does not rot in place. The
pinned pool is 11 entries and fits under the budget, so nothing is silently dropped;
the injection is 13 entries and 1,651 tokens here, and the total is 16,375. Rule for a
pin: it earns its place only if it changes behaviour on an arbitrary prompt in an
arbitrary project. `hippo.db.bak-20260913-pre-pin-prune` holds the state before all of
it.

Quote the total as a level with a stated spread, not a constant. 14,724 of it is config
text and does not move. The hippo line does: `--include-recent 5` takes the last five
writes, so it differs by working directory and after every `hippo remember`. Two live
caches an hour apart read 1,651 and 1,758. A figure of 16,428 went into this file, the
audit memory and the cut sheet before that spread was measured; the level is 16,375
here and lands between roughly 16,375 and 16,500 elsewhere.

The deadlock behind it, now fixed. Two concurrent `hippo context` processes deadlock on
the SQLite store: each ran past ten minutes and returned nothing, against 0.9 to 1.6
seconds for a single run, and the tell is a node process holding near-zero CPU. The
cause was in the wrapper, not in hippo: `spawn_refresh` took a lock named after the
working directory, so it serialised refreshes within one cwd and did nothing at all
across cwds, which is the only case that collides. The lock is now one file for the
whole store, `cache/hippo-context/refresh.lock`, and `LOCK_TTL` drops from 300s to 60s
because a crashed refresh now blocks every directory rather than one. That wedge is
what let the cache serve entries forgotten hours earlier, so it was also the reason 51
of 52 cached payloads still held the pruned pins; those were deleted, and a cold read
repopulates each one correctly in about 0.9s on its next prompt.

`scripts/hooks/test/test_hippo_context_cached.py` covers the strip and the lock, 15
tests, run with `python -m unittest discover -s scripts/hooks/test -p "test_*.py"`. It
earned its place on the first run: a payload whose `additionalContext` is null crashed
`strip_snapshot` with an AttributeError the except clause did not name, which in the
hook means a traceback instead of an injection.

Also corrected: the comment-budget guards were closing a comment run at a blank line,
so narration split by blanks evaded the 3-in-a-row rule. Both `comment-budget-guard.js`
and `comment_budget_guard.py` now continue a run across blank-only lines and only a
code line resets it. The retired ad-hoc runner `scripts/test-comment-budget.js` is
deleted and its cases live in the node suite, 32 tests green via
`node --test C:/Users/skf_s/.claude/scripts/hooks/test/*.test.js`. One old case was
dropped on purpose: a divider, a blank and a 3-line jsdoc is a 4-line run and now
denies.

Ten contradictions between this file and the harness prompt now resolve in the core
section "How this file wins over harness defaults": reads go through Read, Grep and
Glob (which is also what keeps the Fable budget and the backup hook honest); the hard
stops are the closed ASK-FIRST list, hand-maintained rewrites and consolidated plan
revisions; one framing pass per task; em dashes banned only in commits, UI text and
release notes. Hippo's injection is budget-filled: forgetting entries changes which
entries appear, never the count; the lever is the hook's `--budget`.

Trap hit once: `hippo_context_cached.py --refresh` hashes the directory string as
given, so a backslash path writes a cache file the hook never reads. Pass the
forward-slash form. Re-measure any one file with
`python -c "import tiktoken,pathlib;print(len(tiktoken.get_encoding('cl100k_base').encode(pathlib.Path('C:/Users/skf_s/.claude/CLAUDE.md').read_text(encoding='utf-8'))))"`.

## 2026-09-08: the tripwire hook owns its own budget

`UserPromptSubmit hook timed out after 10s - output discarded` fired on most
prompts. `resource_tripwire.py` was the only UserPromptSubmit hook at 10s; the
other three sit at 15s. The script itself is fast: measured 1.14s for a cold full
parse of a 156MB transcript, 0.17s warm, 0.36s for `load_tool_uses` in process.
So the stall is load, not the algorithm, the same shape already recorded for
`hippo context` on 2026-09-06 (0.57s idle, 28-57s under 24-core load).

Fix: the script now carries `DEADLINE` (`TRIPWIRE_BUDGET_S`, default 6s).
`scan()` breaks on the deadline every 5000 lines and returns the bytes it
actually consumed, so the cached offset only ever advances over scanned lines and
the next call resumes. A busy box costs a partial scan, never a killed hook. The
harness timeout moved 10 to 15 to match its siblings, as headroom for interpreter
start, not as the fix. Check: `python scripts/hooks/test_resource_tripwire.py`.

Measurement trap hit twice while diagnosing this: a `cat > f <<'EOF'` heredoc
collapsed the `\\` in a Windows path, so the hook got invalid JSON, returned
silently, and looked like a 115ms run that had done the work. Build hook payloads
with `json.dump` or forward slashes. See `feedback_bash_heredoc_backslash_collapse`.

## Rule edit history

Stamps stripped from rule headings on 2026-09-04, so the changelog stops riding in
every turn's context. As they stood:

- Delegating to sub-agents: "tightened for Opus 5" (section folded into Sub-agents).
- Speed: "Opus 5 and Fable 5 sessions, user directive 2026-08-14" (section deleted;
  its one live clause folded into Sub-agents).
- Lazy-Smart mandatory output artifact: "tightened 2026-06-10" (section merged into
  Root Cause Over Patches, one `<diagnosis>` block).
- Verification mandatory output artifact: "provenance-scoped 2026-07-03"; "What this
  rule does NOT authorise": "scoped 2026-07-26" (both merged into Sourcing).
- Rulebook Discipline: "added 2026-07-04, restored 2026-08-14".
- Banned AI-isms: "user directive 2026-07-17" on the "canonical" ban.
- STE-100 Response Style: "user directive 2026-07-29"; its short-responses addendum:
  "user directive 2026-08-14" (both merged into Output prose).
- Subagent model routing: "added 2026-07-02, re-based on roles 2026-07-26".
- Shell Discipline: "measured via Mirror, 2026-07-18".
- Comments (rules/coding-standards.md): "Keith 2026-08-30, all projects".
- Dependencies & Compatibility (rules/coding-standards.md): "probation, added
  2026-07-31, no incident yet".

## No Fabrication (global CLAUDE.md, now the Sourcing section)

Incident 2026-06-24 (quanthack): asserted "the 30-strat book = the 29-strat book plus
one sleeve" from inference instead of reading `final_universe.json.bak-prefinal`, then
computed and presented a full performance-metrics table on that fabricated book as if
real. The actual 30-book differed by 5 sleeves; hours of comparison were built on a
membership never read from disk. Root cause: stated a set's contents from memory
instead of reading the file. The rule exists because that broke user trust.

## Shell discipline measurements (Mirror, 2026-07-18)

`cd X; cmd` compounds were 61% of measured PowerShell errors, and `cd` was the number
one shell command at 6,349 calls. Detail: memory files
`feedback_shell_absolute_paths_over_cd.md` and
`feedback_ps51_no_native_stderr_redirect.md`; refresh the data with
`python ~/.claude/mirror/mirror.py` where Mirror is installed.

## Banned AI-isms provenance

The core of the list (delve, underscore, showcase, pivotal, intricate, meticulous,
realm, boast, enhance, notably, surpass, garner, strategically) is corpus-backed:
post-ChatGPT "excess vocabulary" studies of PubMed abstracts (Science Advances 2025,
adt3813) and an FSU follow-up finding spillover into spoken language. The rest
("canonical", leverage, seamless, tapestry, and the others) is house style.

## Rule provenance

- rules/karpathy-guidelines.md is adapted from
  https://github.com/forrestchang/andrej-karpathy-skills.
- The Simplicity First ladder and the `SHORTCUT:` comment convention come from
  github.com/dietrichgebert/ponytail, adopted 2026-09-01, with ladder rung 3
  rewritten to defer to project law.
- Rulebook Discipline came from ARC Prize harness notes (cheap generator, hard
  verifier, measurement-fed refinement): `clawd/memory/arc-harness-notes.md` on the
  home box. The ARChitects scored 72.5% on ARC-AGI-1 and 2.5% on ARC-AGI-2, the
  single-benchmark risk the probation tag guards against.
- Root Cause Over Patches and its `<diagnosis>` block come from the 2026-05-05
  2chain incident: five first-party scrapers, a reddit proxy and a promote script
  were all written as patches, when the root cause was one upstream defect, the
  mcp-bridge importer never registered spawn config, so 3,000 catalog entries were
  dead. Recorded here 2026-09-13 from the pinned hippo entry, because the core
  CLAUDE.md cites the incident.

## 2026-09-01 — rulebook restructure (this file created)

The global CLAUDE.md's numbered "Priority Order" families and the per-hook
biography paragraphs were collapsed into the Precedence block and the Hooks table
(via /improve-docs-architecture). History that lived in the deleted block:

- The families ran 1–8: CRITICAL/user overrides, Root Cause Over Patches,
  Lazy-Smart, Verification, Karpathy framing, Decisiveness, Token Discipline,
  Stop Slop.
- "Done means done" was folded into Honest Reporting; "Act. Don't ask" and
  "A question is a question" into Decisiveness; "Speed" into Token Discipline;
  "Short responses" into the STE-100 section (added 2026-08-14, folded
  2026-09-01).
- The project CLAUDE.md at the user root carried second, drifting copies of
  Decisiveness / Token Discipline / Stop Slop until 2026-09-01; its two
  ASK-FIRST lists had diverged. The dedupe merge fixed that.
- Hook prose named the home box's `.js` files while this box runs Python ports —
  a machine fact asserted in a shared doc. The Hooks table now binds by rule
  name, with `settings.json` as the per-box registry.

## Comment budget (rules/coding-standards.md)

Incident: aura `src/decide.js` — 53 comment lines out of 106; a one-line change
carried a 12-line comment block. Led to the comment-budget hook.

## PS 5.1 stderr redirect (Shell Discipline)

21 measured incidents of `2>&1` on native exes (git/gh/node) wrapping stderr in
NativeCommandError and faking failure (Mirror data, 2026-07-18). Led to the
PS-stderr hook.

## Capability existence (global CLAUDE.md)

Incident 2026-06-16: claimed `/project-scaffold` didn't exist — it did — then
substituted a self-authored plan. Two failures stacked: asserted absence without
checking, plus silent pivot. (The story was trimmed from the rule section on
2026-09-04; the one-line rule stays there and this file holds the story.)

## UserPromptSubmit hooks timing out (2026-09-06)

Reported as three simultaneous failures: 5s, 10s and 15s hooks all discarded on
one prompt. The advice in the error ("raise the timeout") had already been tried
and did not hold.

Measured, not guessed. Idle, the five UserPromptSubmit hooks run in 3s wall
clock in parallel. With all 24 cores saturated the same five took 6s
(check-skill-references), 8s (triage-prompt), 11s (ponytail-mode-tracker), 12s
(resource_tripwire) and 28s (hippo context) — reproducing the reported triple
failure exactly. The hooks are not slow; the box stalls and every hook starves
together.

Two contributors:

1. `resource_tripwire.py` re-parsed the whole transcript on every prompt AND
   every Bash/PowerShell PreToolUse call. Transcripts here reach 208MB. Fixed
   by caching a slimmed block list keyed on a byte offset and parsing only
   appended bytes; the cache lives in `~/.claude/cache/tripwire/`. Verified
   identical counts against the old full parse, across an append and a
   half-written trailing line. 208MB transcript, 856KB cache.
2. Leaked processes. At the time of the report: 86 node, 52 bash, 41 cmd, 67
   conhost, 22 tail, 21 grep — 68 of the node processes older than two hours,
   including `astro preview` dev servers from 2026-09-02 still watching
   `boring-maths`. File-watching dev servers left running for days are the
   background load that makes the hook batch starve. Cleared the same day: 18
   astro preview processes and 41 tail/grep orphans older than six hours.

Follow-up, same day. Tests: `dev-framework/tests/test_transcript_cache.py`, seven
cases pinning the incremental reader against a full parse (cold read, append,
half-written last line, shrunken transcript, cached shell commands, TTL prune,
missing file). Four mutations each fail exactly one case. The cache prunes
entries past seven days on write, so the directory stops growing one file per
session forever.

One claim in the first pass was wrong and is corrected here: the hook was NOT
polluting the real cache during tests. `test_the_tripwire_denies_and_records`
passes `transcript_path: ""`, which returns before any cache write. Measured by
diffing the cache directory across a test run, not reasoned about.

Third contributor, and the last one fixed: the memory-injection hook ran
`hippo context` synchronously on the prompt's critical path. Under 24 CPU
burners it measured 56.75s then 28.36s against a 15s budget, so the injection
was discarded on every busy prompt.

That run also kills a claim made earlier in this file, which said process-spawn
latency ate most of the budget for the trivial hooks. It does not. Measured
under the same 24-core saturation: node spawn 0.08s, python spawn 1.49s, and
the tripwire hook 0.11s on the 217MB transcript. Spawning is free; the cost was
all inside `hippo context`, which slows 50-100x under contention against 0.57s
idle. Its read path is clean, so this is scheduling, not a hippo defect: a
traced run shows `--pinned-only` never reads or writes `embeddings.json`, whose
only writer is `saveEmbeddingIndex` (hippo `src/embeddings.ts:413`), reachable
from remember/capture/embed/sleep and not from `getContext`.

Fixed at root by taking the variable-cost work off the deadline path.
`scripts/hooks/hippo_context_cached.py` prints the last computed context from
`~/.claude/cache/hippo-context/<cwd hash>.json` and spawns a detached refresh,
with a 300s lock so a crashed refresh cannot wedge the cache and no pile-up
under load. Cold start runs hippo inline once. A missing or failing hippo
prints nothing and still exits 0, because injecting nothing is survivable and
failing every prompt is not. Same saturation, after: 1.42s then 0.92s, full
7553-byte payload, 10x inside budget. Six tests in
`dev-framework/tests/test_hippo_context_cache.py`; five mutations each fail at
least one.

Raising the timeout was the error message's own advice and was rejected: it
leaves work of unbounded cost under a fixed deadline, so the next load spike
drops the injection again.

## episode_store `_now()` ties on a coarse clock (2026-09-06)

Found while clearing the suite for the hook fix above, and unrelated to it.
`test_learn_effect.py::test_recurred_when_same_failure_comes_back` failed once
in a 779-test run and passed 15/15 alone.

`failure_mode_effect` (`dev-framework/scripts/episode_store.py`) counts
post-fix activity with a strict string `>` on the stamp `_now()` writes. The
events it orders are close together: measured over 120 runs, `applied_at` to
the next episode's `started_at` is 4.05ms at minimum and 6.53ms median, and to
the next step 10.48ms. Windows timer resolution is a global, time-varying
setting. The box ticked at 0.5ms during the investigation, which is why the
test passed alone; at the 15.625ms Windows default those events land in one
tick, `exposure` reads 0, the verdict flips to `untested` and `recurred` reads
0.

The raw clock ties in ordinary use too: 2000 back-to-back `datetime.now()`
calls returned 5 distinct values, and 5000 `_now()` calls returned duplicates.

Fixed at the producer: `_now()` is now strictly increasing, so the ordering its
18 call sites already assume is guaranteed. Falsified before fixing, with the
clock quantized to 15.625ms: the assertion failed 34/60 runs on the old code
and 0/60 on the new. Three tests pin it (`test_now_is_strictly_increasing`,
`test_now_still_increases_on_a_coarse_clock`,
`test_recurred_survives_a_coarse_clock`); all three fail when the guard is
removed. The guard is process-local, so two processes writing inside one tick
can still tie; that needs ordering on step id.
