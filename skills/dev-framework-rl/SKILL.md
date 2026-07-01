---
name: dev-framework-rl
description: Experiential-RL orchestrator that runs a problem from idea generation through ship with auto-critic gates, trajectory logging to SQLite, and per-episode learning. Wraps /dev-framework. Use when asked to "run an RL episode", "/dev-framework-rl", "solve this end-to-end with the learning loop", "run the orchestrator", or "/dev-framework-rl loop <target>" / "continuously improve <repo>" for the self-sourcing continuous-improvement loop.
---

# /dev-framework-rl — Experiential-RL Orchestrator

Runs a development problem as an **episode**: brainstorm a framing, walk the `/dev-framework` stages, gate each stage with a critic sub-agent, log the whole trajectory to SQLite, and (later phases) compute a reward and learn from it.

The policy is prompts + memories — Claude's weights are frozen. This is experiential-RL: the system improves by accumulating trajectories and updating skill prompts, not by gradient descent.

## Status

Phase MVP + Phase Learn + Phase Elevate complete (2026-05-23, 7-tier elevation; 535 tests green). Codex promoted from shadow-only (Tier 5) to a mandatory gating critic at the `review` stage (2026-05-24); `/self-review` wired into `execute`, `/review` into `review`, `/ship-check` into `ship`. **Phase Elevate v2** opened 2026-05-24 with **Tier 8 — counterfactual critic-trust attribution** shipped: per-critic empirical trust scores computed from real episode outcomes (`learn-attribute` + `critic-trust` CLIs, migration 0008). Tier 8 is observation-only; Tiers 9-13 scoped in `RL-PLAN.md` v0.7. **`/grill-me`** wired 2026-05-24 as the orchestrator's self-interrogation hook — the orchestrator is the subject ("me" = the orchestrator's own work), invoked at brainstorm-post-selection, plan-stage tail (before plan-eng-critic), and (optionally, opt-in) as a meta-critic on any `pass` verdict to test whether the pass survives adversarial pressure.

Wired and tested (real-DB test suite under `tests/`):
- Episode lifecycle — init, host lock, steps, finalize, reward — `episodes.db`
- Per-stage manifest contract with `/dev-framework`
- 7 verdict critics (`adapters/critics.py`); 8 per-type reward rubrics
- Secret/PII scrubbing on every DB write
- Per-episode learn step, cross-episode failure clustering, and the `learn` mode below
- **Tier 0.0** `devrl.py status` operator dashboard
- **Tier 0.1** post-deploy scheduler (migration 0003): `postdeploy-due`, `episode-deploy-meta`; finalize auto-populates `post_deploy_due_at = ended_at + 7d`
- **Tier 0.2** finalize CLI wiring: `--user-satisfaction N|deferred`, `--redirects N`, `satisfaction-record` follow-up
- **Tier 0.3** `step-record` records `step_prompts` via `--prompt` + `--memory-ref`
- **Tier 0.4** post-deploy outcome reminder: `postdeploy-prompt [--within-days N] [--json]` is the operator-facing summarizer (table mode for humans, JSON mode for cron). Episodes ended in the last 24h are excluded as too-fresh-to-assess. The live cron `devrl-post-deploy` (daily 09:00 Europe/London, openclaw + Telegram, agent `openai-codex/gpt-5.5` thinking high) was already installed prior to Tier 0.4 work; its prompt file lives at `C:/Users/skf_s/clawd/memory/cron-prompts/devrl-post-deploy.md` and runs a verification protocol (`gh pr checks` + `git log --grep="revert"` per episode) — NEVER mass-marks `--clean` without evidence. The CLI added in Tier 0.4 complements that protocol but does not replace it. Hard guard (from the live prompt, mirrored here): never guess `--clean` to clear the queue; uncertain outcomes stay as `unknown` and surface to Telegram for human decision.
- **Tier 1** embedding clustering (migration 0004): `learn-cluster --mode embedding` + `embed-cache-prune`
- **Tier 2** brainstorm-judge ranking critic: `brainstorm-rank $EID candidates.json --judge <file>|--select-idx N` (separate CLI, NOT in critic-check)
- **Tier 3** synchronous friction→memory: finalize `--learn-emit` emits `pending_apply/$EID.json`; `apply-pending` views/clears
- **Tier 4** critic A/B (migration 0006): `episode-init --critic-set default|minimal|full|random`; `critic-ab-report`
- **Tier 5** codex shadow (migration 0005): `codex-shadow $EID <stage> --local-verdict <v> --max-wait-sec 90`; `codex-shadow-report`; **DEPRECATED 2026-05-24** — superseded by `codex-review-critic` (gates at the `review` stage). CLI now prints a deprecation warning on every invocation; retained for backwards-compat + cross-stage A/B logging (plan-stage codex consultations) where the gating critic does not run.
- **Tier 6** auto-confirm probation memories on use (requires `warning_pattern:` in memory frontmatter); `memory-needs-pattern` lists missing ones
- **Tier 7** batch ritual (migration 0007): `batch-init`, `batch-add`, `batch-finalize` (auto-clusters), `batch-deploy --decision shipped|aborted|partial`; sole-writer of `post_deploy_due_at` for batched episodes
- **Tier 8** counterfactual critic-trust attribution (migration 0008): `learn-attribute [--since DATE]` recomputes per-critic empirical trust from the trajectory store; `critic-trust [--critic NAME] [--json]` reads the dashboard. Pure observation — Tier 9 (verdict weighting) reads this table but never modifies it. Score = Beta(2,2)-smoothed `(verdict-matched-outcome)` rate; NULL until n_seen ≥ 5.

## Prerequisites

`episodes.db` must be migrated:

```bash
python ~/.claude/dev-framework/scripts/migrate.py
```

**Invoking devrl — use the absolute path; do NOT leave the shell `cd`-ed into dev-framework (CRITICAL anti-drift rule, learned the hard way 2026-06-02).** The Bash-tool cwd PERSISTS across calls. If you `cd ~/.claude/dev-framework` to run a devrl command (init / lock / heartbeat / step-record / critic-check), the NEXT feature-repo command (git / npm / vitest / codex / grep) silently runs in dev-framework — cwd-drift. This is the single most recurring orchestrator friction (it bit 6+ times in ONE hippo episode despite a memory warning — memory-recalled discipline demonstrably fails under load). The mechanical fix: invoke devrl by its **absolute path, run from the feature repo** — `python ~/.claude/dev-framework/scripts/devrl.py <cmd>` — and never run a bare `cd ~/.claude/dev-framework`. The `python scripts/devrl.py …` snippets below are shorthand for that absolute form; in practice prefix `~/.claude/dev-framework/`, OR wrap in a non-persisting subshell `( cd ~/.claude/dev-framework && python scripts/devrl.py … )`. And give EVERY feature-repo command its own explicit `cd <feature-repo> &&` in the SAME Bash call — never rely on inherited cwd.

## Episode lifecycle

### 1. Init and lock

```bash
python scripts/devrl.py episode-init "<problem statement>" --token-budget 200000 --wallclock-budget-sec 5400
```

Capture the printed 26-char episode id as `$EID`. Then claim the host lock:

```bash
python scripts/devrl.py lock-acquire $EID --session "<this-session-id>"
```

Exit 1 / "denied" → another session owns this episode. **Stop.** Do not proceed.

Heartbeat the lock (`lock-heartbeat $EID`) at least every few minutes during long stages — a lock un-heartbeated for 5 minutes is reaped and the episode marked `stalled`.

**Background-op heartbeat discipline (learned 2026-05-29, boring-math episode `01KSRA0R8FEVMVYRJXNAC8NY22`).** Long *background* operations — a `Workflow` build run, a full test suite, a `codex review` (each minutes long) — silently burn the 5-minute window with no orchestrator-side heartbeat, so the lock reaps mid-stage and the episode flips to `stalled`. Heartbeat immediately BEFORE and AFTER every such op, and if a heartbeat returns `lock-vanished` re-acquire with `lock-acquire` and continue. Also: never `&&`-chain a manifest write (or any required step) after `lock-heartbeat` — a vanished lock exits non-zero and aborts the rest of the chain, so the manifest never gets written. Write the manifest unconditionally; put the heartbeat on its own line.

**Isolate into a dedicated git worktree at episode START for high-contention repos (learned 2026-06-02, hippo sleep enqueue-hook `01KT4CP9K6BEQ4ESCTFV49A8DX`).** Repos with heavy concurrent multi-agent activity (e.g. hippo, with many `.claude/worktrees/` agents) can have a SIBLING session edit your branch's MAIN working tree mid-episode AND merge a version ahead of you — forcing a reactive worktree-isolation + rebase + version-collision bump late in the episode (it happened: a7-recall-trace edited my `api.ts` and merged v1.18.0 while I worked, so I had to isolate + rebase + bump 1.18.0→1.19.0). Pre-empt it: right after `lock-acquire`, create a dedicated worktree off `master` for the WHOLE episode — `git worktree add -b <feat-branch> <path> origin/master`, then symlink `node_modules` (`ln -s <main-repo>/node_modules <path>/node_modules`) for build/test — and do ALL edits/commits/codex/build/test there, leaving the main working tree to the other session. Clean it up at deploy (`git worktree remove <path> --force`). ALSO: `git fetch origin && git show origin/master:package.json | grep version` right BEFORE the version bump, so a concurrent version merge is caught and you bump PAST it (not into a collision). Tear-down note: `git worktree remove --force` deletes the worktree dir but a symlinked `node_modules` is removed as a link (the main repo's `node_modules` target is NOT followed/deleted) — verify the main `node_modules` survives.

**Probation-memory exposure (R9, 2026-06-09).** Right after `lock-acquire`, run `python scripts/devrl.py memory-list --status probation`. Carry the relevant memories into this episode's stage briefs tagged `[PROBATION]` — they are unconfirmed hints, not settled law — and record each one's id on the steps where it was in scope (`step-record ... --memory-ref <id>`). This is what lets a useful memory earn its 3 shipped-episode confirmations and a useless one earn its deprecation; a probation memory kept out of context can never do either.

### 1.5 Codex availability probe (recommended)

The `review` stage gates on `codex-review-critic`, which requires the `codex` CLI. Probe at episode-init so an unreachable codex doesn't surface as a surprise blocker mid-episode. Run:

```bash
_CODEX_BIN=$(which codex 2>/dev/null || echo "")
if [ -z "$_CODEX_BIN" ]; then
  echo "WARN: codex CLI not installed. codex-review-critic at the review stage will fail."
  echo "  Either install: npm install -g @openai/codex"
  echo "  Or proceed knowing the review stage will need manual /codex from another session"
  echo "  (paste the verdict back to the orchestrator)."
  python scripts/devrl.py episode-friction $EID --note "codex CLI not installed at episode-init; codex-review-critic will need manual /codex from another session."
fi
```

If codex is missing, decide upfront whether to (a) install it, (b) skip codex-review-critic with explicit human override at the review stage, or (c) defer the episode entirely. Surfacing this at init beats surfacing it at review-stage round 1.

Learned 2026-05-26 from episode `01KSHTN0RYYSCXCAJCTN5TJJDC` (hippo-memory C5 WYSIATI): mid-episode codex unavailability forced a pause at the review stage. The episode shipped clean after the operator ran `/codex` manually in another session, but the friction was avoidable with an init-time probe.

**Pin cwd when running `codex review --uncommitted` (review stage).** `codex review --uncommitted` reviews the git repo of the CURRENT working directory. The orchestrator's `lock-heartbeat` / `devrl.py` commands `cd` to `~/.claude/dev-framework`, so a codex review launched right after one silently reviews dev-framework's OWN uncommitted changes instead of the feature repo — a wasted round whose findings name the wrong files. ALWAYS pin the cwd in the same command (`cd <feature-repo> && codex review --uncommitted`) and confirm the `workdir:` line in codex's output names the feature repo before trusting any finding. Learned 2026-05-30 (E2 project_brief `01KSWQDQQN3YJ9FMSBG64S0X19`): codex round 2 reviewed `dev-framework/scripts/*.py` (its own uncommitted Tier-8 work), not the hippo diff; caught only by reading the workdir line, forcing a pinned re-run.

### 1.6 Publish credentials probe (recommended for `library` / package releases)

If the episode will publish a package at the deploy stage (npm, PyPI, crates,
etc.), the publish credentials live with the human, not the orchestration
session. An episode that bumps versions, passes every gate, and merges, only to
hit a 401 at `npm publish`, has surfaced an avoidable blocker after the work is
already done. Probe at episode-init, the same way §1.5 probes codex:

```bash
# npm — only if this release publishes to npm
npm whoami >/dev/null 2>&1 || {
  echo "WARN: not authenticated to npm; deploy-stage 'npm publish' will 401."
  python scripts/devrl.py episode-friction $EID --note "npm not authenticated at episode-init; publish will be a manual operator step or needs 'npm login' first."
}
# PyPI — only if this release publishes a Python package
[ -n "$TWINE_PASSWORD" ] || [ -f ~/.pypirc ] || {
  echo "WARN: no PyPI token in env or ~/.pypirc; deploy-stage twine upload will hang/fail."
  python scripts/devrl.py episode-friction $EID --note "no PyPI token at episode-init; SDK publish will be a manual operator step (TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-... --non-interactive)."
}
```

If creds are missing, decide upfront whether to (a) have the operator authenticate (`! npm login`, export the PyPI token) so the deploy stage can publish, (b) treat publish as a documented manual handoff and tag-only, or (c) defer. Either way the deploy-gate human checkpoint should state the publish path explicitly rather than discovering the 401 after merge.

Learned 2026-05-28 from episode `01KSR5424D5845DMXSAQQBEBRX` (hippo-memory v1.15.0 release): all six gates passed and PR #79 merged, then `npm publish` could not run (401, no PyPI token in session), forcing the publish + git tag into a manual operator step after the fact. A §1.5-style init probe would have surfaced the credential path before the work, not after.

### 2. Brainstorm pre-stage

Run `/office-hours` (builder mode) or `/brainstorming` to generate 3-5 candidate framings of the problem. Pick the strongest.

**Then grill your own pick.** Run `/grill-me` against the chosen framing — "me" is the orchestrator (you). The grill is adversarial: interrogate the assumptions in your own selection, name the weakest premise, surface what would have to be true for this framing to win, and what would falsify it. If the grill breaks the framing, return to the candidate list and pick a different one (or refine). Record the chosen framing + the grill's strongest counter-point + your response in the step summary:

```bash
python scripts/devrl.py step-record $EID brainstorm --skill /office-hours --critic-status n/a --summary "<chosen framing + grill's strongest objection + how you addressed it>"
```

(The `brainstorm-judge` critic that ranks candidates automatically is a separate follow-up — it needs a ranking contract distinct from the pass/fail verdict critics. For now, choose deliberately, grill your own choice, and record your reasoning in the summary.)

### 3. Discover and stage plan

Invoke `/dev-framework discover` with `$EID` in context. It emits `trajectories/$EID/stage-plan.json`. Validate it:

```bash
python scripts/validate_manifest.py plan trajectories/$EID/stage-plan.json
```

Read the plan's `project_type` and `rubric_file`, then:

```bash
python scripts/devrl.py set-project-type $EID <project_type> <rubric_file>
python scripts/devrl.py step-record $EID discover --skill /dev-framework --critic-status n/a --summary "<what discover found>"
```

### 3b. Pre-plan codebase audit (mandatory between discover and the first plan stage)

Two friction signals in 2026-05-23/24 pointed at the same root cause: plan-eng-critic
caught drifts (parallel allow-lists missed, version-bump targets under-counted,
TODOS items already shipped) that an earlier codebase grep would have surfaced for
free, before any sub-agent dispatch. The fix is a deterministic audit pass between
discover and the first plan invocation.

Run these greps in ONE batch of parallel `Grep` calls before invoking `/dev-framework plan`:

1. **TODOS staleness reproduce-check.** For each item this episode's brief references,
   grep the codebase for the symbol/test/CLI flag/file path named in the item. If the
   item is already shipped (file exists with the named contents OR test passes OR the
   CLI command is wired), **abort the episode** — record the friction note
   `"TODOS-stale item X already resolved at <file:line>"`, sync `TODOS.md` with a
   DONE-by-design line, commit, finalize as `aborted` with the reproduce-check WIN
   in the summary. This is a successful episode (work was identifying staleness).

2. **Parallel allow-list grep.** For any allow-list / registry / `Set<>` / `Map<>` the
   plan adds an entry to (e.g. `VALID_AUDIT_OPS`, `STAGE_CRITICS`, route tables),
   grep the EXACT pattern across the repo. If N>1 sites exist, the plan MUST enumerate
   all N. Drift between them is a plan-eng-critic CRIT preventable here.
   **Hardcoded CLI-flag allow-lists are one such list.** When an episode adds a
   *repeatable* CLI flag, grep the argv parser's repeatable-flag allow-list (e.g.
   hippo's `parseArgs` `key === 'tag' || key === 'artifact' || ...` in `src/cli.ts`)
   and add the new flag there. A repeatable flag NOT in the list is silently
   last-wins (only the final `--flag` value survives) — a bug a code-review critic
   often misses but a CLI test catches. Learned 2026-05-29 on the E2 `process`
   episode: `--step` was last-wins because it was absent from the allow-list.

3. **Version-bump target count.** If the plan ships a version bump, enumerate every
   manifest:
   ```bash
   git grep -l 'version' package.json **/package.json **/*.plugin.json src/version.ts
   ```
   (or the project's equivalent). The plan MUST list every file. Missing any causes
   the v1.10.1-class manifest drift that ships under-tagged releases.

   When the bump is to a version **constant in code** (e.g. `CURRENT_SCHEMA_VERSION`
   / `SCHEMA_VERSION`), the manifest grep is NOT enough — grep its TEST assertions too
   (`getCurrentSchemaVersion` / `getSchemaVersion` / `getMeta('schema_version')`-style
   checks hard-code the old number and break in lockstep). Enumerate every assertion
   site, not just the manifest. Learned 2026-05-28 (E2 decision): bumping
   `CURRENT_SCHEMA_VERSION` 29->30 broke 10 test sites caught only at the verify stage.

4. **Roadmap-sync sweep — `docs/evals/` freshness.** If the episode references a
   "canonical roadmap" claim (e.g. "feature F never measured locally", "Track X is
   blocked"), grep `docs/evals/` for results docs post-dating the canonical doc's
   last modification time. Negative-result eval docs that bypassed canonical-doc
   updates under v1.7.9-class retraction discipline WILL be missed by reading only
   `ROADMAP.md` / `TODOS.md` / `ROADMAP-RESEARCH.md`.

5. **Public-API caller audit.** If the plan changes a function signature, grep for
   callers at every import surface (`from X import`, `sys.path` insert,
   `importlib.util.spec_from_file_location`, dynamic `require()`). Don't only audit
   internal helpers. (Promoted from a `feedback_audit_public_callers_not_helpers`
   probation memory.)

6. **Functional-duplicate check (when the plan ADDS a user-facing artifact).** A
   slug / name / path collision check is NOT enough: a new page, calculator, route, or
   endpoint can duplicate an existing one's *capability* under a different name. For each
   new artifact the plan adds, grep the existing artifacts' titles AND
   descriptions/feature lists for the same capability, not just the same slug. If an
   existing artifact already does the job, the plan must fold / differentiate / drop the
   new one. Learned 2026-05-29 (boring-math `01KSRA0R8FEVMVYRJXNAC8NY22`): "Days Between
   Dates" and "Business Days" both passed the slug gap-check but functionally duplicated
   the existing DateDifferenceCalculator (which already had a business-days toggle); only
   plan-design-critic caught it, costing a plan retry.

7. **Temporal / as-of / point-in-time query check.** If the plan builds a query that
   answers "what was X at time T" (as-of, effective-dating, bi-temporal, valid-time vs
   transaction-time, version-history-at-a-date), STOP and do two things before the plan
   stage: (a) grep for an existing temporal pattern in the codebase to MIRROR rather than
   reinvent (hippo's `src/recall-history.ts` has a correct successor-aware `asOf` filter:
   include a superseded/historical row only while its successor's `valid_from > asOf`;
   exclude retired/closed rows); (b) the plan MUST explicitly enumerate the **valid-time
   vs transaction-time axes**, **which row statuses the query includes** (a naive
   `status='active'`-only filter silently drops historically-valid superseded versions —
   that conflates the two axes), and the **date-granularity contract** (a date-only input
   vs a datetime — midnight vs end-of-day; whether the stored timestamp is backdated or
   the read side resolves the day). These are subtle and pass plausible-but-wrong:
   learned 2026-05-30 (E2 policy `01KSW4XHBGTKT7HAJ37TBS1W79`) — plan-eng + both Claude
   review gates passed a flawed as-of query; codex needed 3 rounds to converge it.

8. **Sibling-clone audit (don't clone a latent bug).** When the plan mirrors an existing
   sibling route / module / handler (the dominant pattern for these E2-object episodes),
   the copied code inherits the sibling's latent bugs — audit the pattern you are cloning,
   do not just replicate it, and prefer extracting a shared helper over an Nth copy. Known
   instance: list-route `?limit=` validation must use `Number.isInteger` (not
   `Number.isFinite`, which accepts `1.5` that SQLite `LIMIT ?` then rejects with a
   datatype-mismatch 500). Learned 2026-05-30 (E2 policy): the fractional-limit hole was
   copied from the decision/incident/process/prediction list routes; codex caught it and
   the root fix was one shared `parseListLimit` across all five.

9. **Cross-cap consistency (generate-then-store-in-a-capped-column).** When the plan
   ASSEMBLES / generates a value that is then written to a length-capped storage field,
   the generation caps must be provably `<=` the storage cap, OR the assembly must be
   budget-bounded. A feature whose generation caps (`N items x per-item cap`) can exceed
   the destination column / validation cap will THROW for inputs within its OWN advertised
   caps. Grep the generation caps and the destination cap; if `N x per_item_cap + overhead
   > column_cap`, require budget-aware assembly (include items until the cap, note the
   omitted remainder) rather than a naive join. Learned 2026-05-30 (E2 project_brief
   `01KSWQDQQN3YJ9FMSBG64S0X19`): `refreshBrief` built an ~11KB digest from
   `MAX_BRIEF_RECEIPTS(50) x MAX_RECEIPT_HEADLINE_LEN(200)` but the `summary` column caps
   at 8192, so refresh threw within its own caps; all three Claude gates missed it, codex
   caught it round 1.

10. **Migration column-name reserved-word check.** When the plan adds a COLUMN in a
    migration, check each new column name against SQL reserved words (`trigger`, `order`,
    `group`, `check`, `default`, `references`, `index`, `table`, `column`, `select`,
    `where`, ...). A reserved name either errors at `CREATE TABLE` or forces brittle
    quoting everywhere; rename with a safe suffix (`_text` / `_at`) and map it back to the
    domain field. Learned 2026-05-30 (E2 skill `01KSWHXW8G8X8YGDB0G58MKFM2`): the `trigger`
    field collided with the SQLite TRIGGER keyword, so it is stored in a `trigger_text`
    column (TS field `trigger`, mapped in `rowToSkill`); caught in the grill, not by an
    audit rule — this rule closes that gap.

11. **Bidirectional guard for a denormalized-parent-value invariant.** When the plan
    has a CHILD row denormalize a value from a PARENT row (e.g. a copied `source_kind`,
    a cached tenant_id, a snapshotted status) AND a guard enforces "child matches
    parent", a FORWARD guard (CHECK / BEFORE INSERT + BEFORE UPDATE trigger on the
    CHILD) is necessary but NOT sufficient: the invariant is still bypassable by later
    MUTATING the PARENT. The plan MUST also specify a REVERSE guard (a BEFORE UPDATE
    trigger on the PARENT that blocks — or a cascade/repair path that fixes — parent
    changes which would invalidate the child's copy or the invariant), OR explicitly
    accept the parent as immutable-while-referenced. Enumerate BOTH directions before
    the plan stage. Learned 2026-06-01 (E3.3 graph guard `01KT1N4XC3JFJ5YK7FQ4XXZKCE`):
    `entities.source_kind` copied `memories.kind` and the forward graph-table triggers
    enforced "never raw" on insert/update, but `UPDATE memories SET kind='raw'` after a
    graph row referenced the memory bypassed every forward trigger; plan-eng,
    code-review, AND an empirical independent-review probe all missed the reverse
    direction — codex caught it (P1). Fixed with `trg_memories_graph_referenced_guard`
    (parent-side BEFORE UPDATE). The "make bad rows unrepresentable" principle is
    DIRECTIONAL; cover both.

12. **Fail-soft side-effect after a committed write — enumerate the post-commit failure
    windows UP FRONT.** When the plan adds a best-effort / fail-soft side-effect that runs
    AFTER a committed write (enqueue a job, mark-dirty, notify, cache-invalidate), the
    "fail-soft" framing hides a family of windows where the write commits but the
    side-effect is silently lost: (a) the host process CRASHES between commit and the
    side-effect; (b) a LATER step in the same write path throws before the side-effect runs
    (e.g. a post-commit mirror/index write fails); (c) the side-effect opens a SECOND DB
    connection while the write's transaction is still OPEN → `database is locked` / deadlock.
    The plan MUST enumerate these windows for the specific write path and state, per window,
    whether it is closed (run the side-effect via a post-commit hook that fires BEFORE any
    later fallible step; share the write's connection; or make it atomic-with-rollback) or
    accepted as a self-healing residual (and exactly how it self-heals). Learned 2026-06-02
    (hippo sleep enqueue-hook `01KT4CP9K6BEQ4ESCTFV49A8DX`): codex took **4 rounds**, each
    surfacing one such window of a fail-soft `markGraphDirty` enqueue (a mirror
    cascade-delete dropped the dirty row; a snapshot-read failure aborted core sleep;
    concurrent rebuilds duped rows; a post-commit mirror-write failure left a committed save
    unflagged). All real, all fixable, but each cost a full codex round because they weren't
    enumerated at plan time. A `writeEntry`-style `afterCommit` hook (runs post-commit,
    pre-mirror, on the committed idle connection) closes (a)/(b); a single `BEGIN IMMEDIATE`
    rebuild closes (c). Note (c) is also the trap when making a multi-write op atomic: a
    transaction that holds the write lock cannot open a second connection for its reads —
    preload reads before the transaction.

13. **Bounded-neighbourhood / subgraph / focus query — enumerate the correctness
    dimensions UP FRONT.** When the plan builds a "focus / subgraph / k-hop /
    neighbourhood / show-X-and-what's-near-it" query (a node + its neighbours + the
    edges among them, bounded by a `limit`), it has a KNOWN FAMILY of correctness
    dimensions that each fail plausible-but-wrong and each cost a separate review
    round if discovered one at a time. The plan MUST state, per dimension, how it is
    handled: (a) **find the seed BEFORE the global cap** — look the focus node up
    directly (by name/key), never filter it out of a globally-capped list (else a seed
    beyond the cap falsely reports "not found"); (b) **edges AMONG the result set, not
    merely TOUCHING the seed** — a `both-endpoints-in-set` query, so neighbour-to-
    neighbour edges appear and a `LIMIT` can't evict a valid in-set edge in favour of
    out-of-set rows; (c) **push the bound into SQL** (`LIMIT`/`WHERE` in the query),
    never an app-layer `.slice()` after materialising every matching row (a name shared
    by thousands of rows otherwise loads them all); (d) **truncation honesty** — set the
    `truncated`/incomplete flag when ANY cap fills (the seed-match cap, the
    neighbour-scan cap, the node-set cap, the edge cap, or an early `break`), not just
    one of them; (e) **align the input cap to the DOMAIN cap** — validate a name/key
    param against the field's real max (e.g. a 512-char entity-name cap), not an
    id-shaped 256 that rejects valid nodes the rest of the system accepts; (f) **one read
    SNAPSHOT across multi-table reads** — if the model is assembled from ≥2 separate
    loader reads, run them inside a single read transaction (one WAL snapshot) so a
    concurrent rebuild that clears+reinserts rows can't make the model mix old ids
    (entities) with new ids (relations). Learned 2026-06-02 (hippo graph observability
    `01KT4V9ZS1QAYZMY091FFFHECW`): the `--entity` focus subgraph took **7 codex rounds**,
    one per dimension above (find-before-cap, edges-among-union, SQL-vs-app bound,
    truncation-honesty ×2, domain-cap alignment, read-snapshot) — all real, all
    enumerable at plan time. This mirrors rule 12 for fail-soft writes: a query shape
    with a known failure family gets its checklist up front, not one review round each.

14. **FK-action / trigger-firing interactions — verify EMPIRICALLY in the target runtime,
    not from the SQLite docs.** When a migration adds a FK `ON DELETE SET NULL` / `CASCADE`
    AND a `BEFORE INSERT`/`BEFORE UPDATE` trigger on the same table, do NOT reason from the
    docs about whether the FK action fires the trigger — TEST it. `node:sqlite` fires a
    `BEFORE UPDATE` trigger from an `ON DELETE SET NULL` action EVEN WITH `recursive_triggers`
    OFF, contradicting the documented SQLite behavior. A guard that aborts on the resulting
    row state then blocks the parent delete and every cascade-driven lifecycle op (forget,
    sleep-prune). Probe pattern: build the table + FK + trigger in a `:memory:` db, run the
    delete, observe. Learned 2026-06-03 (hippo graph/E2 provenance
    `01KT6PY1H6EWDQF85R30Z15XWJ`): the plan AND plan-eng-critic both asserted "SET NULL won't
    fire the guard (recursive_triggers OFF)" from the docs; a 3-line probe proved the
    opposite; codex caught the resulting core-`sleep` break as a P1.

15. **Dual-provenance / denormalized-invariant guard — write ONE invariant + enumerate the
    combinatorial matrix UP FRONT.** When a row's validity depends on >1 provenance source
    (e.g. memory-pointer OR object-pointer) or a denormalized copy, the guard surface is
    COMBINATORIAL: {insert, explicit-update, FK-action-update} × {source A present/absent} ×
    {source B absent/incomplete/valid/invalid} × {tenant change} × {extraction race}. Do NOT
    discover these corners one review round at a time — enumerate the matrix at plan time and
    implement ONE shared invariant helper applied at EVERY write path (insert + the explicit-
    update path + the producer/extractor), with the FK-action-update transition explicitly
    carved out (validate on an EXPLICIT column change, never on the FK-driven one). Also: a
    feature that invalidates a GLOBALLY-derived cache must design the tenant-level
    REBUILD-SCHEDULING up front — a per-row/per-memory write signal cannot express "rebuild
    this whole tenant," so cache-drop-on-migration and a delete that changes OTHER rows'
    derived state both silently under-derive until the next unrelated write. Learned
    2026-06-03 (hippo graph/E2 provenance `01KT6PY1H6EWDQF85R30Z15XWJ`): a dual-provenance
    (memory-OR-object) graph guard took **6 codex rounds** (guard hole, close-no-rebuild,
    dual-set-not-validated, all-null-on-SET-NULL, extraction-race, all-or-none pair,
    tenant-move-revalidation, plus the globally-derived-cache rebuild-scheduling gap) — each a
    corner of that matrix found in a SEPARATE round because it was spot-patched, not
    enumerated. All three Claude critics passed a diff codex then showed had a P1.

Record the audit as a step:
```bash
python scripts/devrl.py step-record $EID codebase-audit --skill /dev-framework-rl --critic-status n/a --summary "<grep results: N TODOS items reproduce-checked; M allow-list sites identified; K version-bump targets enumerated; J docs/evals/ results-docs scanned; L public-API caller surfaces audited>"
```

**Then record which rules FIRED (C1 policy decay).** For every rule above that surfaced a finding this episode:
```bash
python scripts/devrl.py audit-record $EID --rule <slug>[:what-it-prevented]   # repeatable
```
Stable slugs (never renumbered; rule № → slug): 1=`todos-staleness`, 2=`parallel-allow-list`, 3=`version-bump-targets`, 4=`roadmap-evals-freshness`, 5=`public-api-callers`, 6=`functional-duplicate`, 7=`temporal-as-of`, 8=`sibling-clone`, 9=`cross-cap-consistency`, 10=`reserved-word-column`, 11=`bidirectional-guard`, 12=`fail-soft-post-commit`, 13=`bounded-neighbourhood`, 14=`fk-trigger-empirical`, 15=`dual-provenance-matrix`. A fired rule is positive evidence it earns its per-episode token cost; `policy-compact-report` proposes demoting rules that never fire across instrumented episodes (propose-only — absence alone never demotes, the human decides).

If the audit surfaces a reproduce-check WIN, jump to finalize (skip plan/execute/verify/review/ship). The win IS the deliverable.

### 4. Stage loop

Iterate the `stages` list from `stage-plan.json` (NOT a hardcoded 9). For each stage after `discover`:

1. Invoke `/dev-framework <stage>` with `$EID` in context.
2. Validate the emitted manifest:
   ```bash
   python scripts/validate_manifest.py manifest trajectories/$EID/<stage>.manifest.json
   ```
   Validation failure → record the step with `--critic-status error` and **escalate to the human**.
3. If the stage has critic(s) — `critic_registry.STAGE_CRITICS` maps each gated stage to its critics (`plan` → `plan-eng-critic` + `plan-design-critic`, `execute` → `code-review-critic`, `review` → `independent-review-critic` + `codex-review-critic`, `ship` → `ship-readiness-critic`, `deploy` → `canary-monitor`). These are the exact names `critic-check` accepts — pass them verbatim (every critic carries the `-critic` suffix except `canary-monitor`). For each critic of this stage:
   - Launch a `senior-code-reviewer` sub-agent. Brief it with the full contents of that critic's briefing (`prompts/critic-<role>.md`) plus the milestone goal and the stage's artifacts from the manifest. (`plan-design-critic` runs only for UI projects.)
   - **If the plan artifact is an existing repo doc** (e.g. `docs/.../plans/<date>-<name>.md`) rather than an in-episode draft, brief the critic explicitly that any `Status: Draft` or `not yet reviewed` marker means the doc has NOT been engineering-reviewed yet; fresh-eyes scrutiny is the point. A pre-existing plan author's reasoning is not pre-vetted, and the orchestrator should not defer to its existing prose. Learned 2026-05-23 from the resona admin-dashboard Phase A episode (`01KSA2C6YSMSFFDE0X37PZ3EK0`): the round-1 plan-eng-critic caught a cross-org schema leak in a 5-day-old draft plan exactly because the brief said to judge it fresh.
   - **For the `plan` stage specifically: pre-stage brainstorm concerns must be carried forward into the revised plan.** When entering `plan`, re-read the brainstorm step's `summary` field (via `episode-steps`). Each concern surfaced there must be either explicitly addressed in the revised plan artifact OR explicitly noted as out-of-scope in the plan manifest. Don't let brainstorm-stage framing dissolve before the plan-eng-critic runs — the critic only judges what's IN the revised plan, not what was flagged during brainstorm. Learned 2026-05-23 from the resona admin-dashboard Phase B Task B2 episode (`01KSAYQBNY2EDHXPRKQ76BS362`): rate-limiting + UUID enumeration were flagged as known re-identification surfaces during brainstorm but didn't appear in the revised plan; plan-eng-critic round 1 passed without them, and independent-review-critic caught the rate-limit gap as HIGH at the review stage, costing a round-1 retry.
   - **Confirm the sub-agent actually read the artifacts.** If its result reports zero tool calls, it produced a verdict from the prompt text without opening the diff / plan / files — discard it, do NOT `step-record` it, and re-launch the critic. If a re-launched critic again returns zero tool calls, record `--critic-status error` and escalate. A critic that read nothing has not reviewed; the critic briefings mandate file reads for the same reason.
   - Save the sub-agent's response to a temp file, then:
     ```bash
     python scripts/devrl.py critic-check <critic-name> <temp-file>
     ```
   - **Exit 0 (pass)** → `step-record ... --critic-status pass --critic-score <n>`.
   - **Exit 1 (fail)** → `step-record ... --critic-status fail --critic-score <n> --must-fix "..."`. Re-run the stage with the must-fix fed back, up to the per-stage cap (plan 3, execute 2, review 1, ship 1; `--retry-count <n+1> --retry-strategy revise_with_feedback`). Cap hit → **escalate to the human**. **Cap-extension carve-out (learned 2026-06-02, hippo A7 recall-trace):** when a plan round returns score ≥ 75, 0 `crit`, and the SOLE remaining finding is a one-clause fix the orchestrator introduced in its OWN prior revision, a single one-round cap extension (with operator notification) is permitted before full escalation; escalate if that extension round also fails or introduces a new finding. The cap exists to stop thrashing on a broken plan, not to block a converged one over a self-inflicted typo.
   - **Exit 2 (parse error)** → `step-record ... --critic-status error`, **escalate to the human**.
   The stage advances only when all of its critics pass.

   **CI gate (`ship` / `deploy` stages) — a critic verdict is not the repo's CI.**
   Before the `ship` stage opens a PR and before the `deploy` stage merges one,
   run `gh pr checks <PR>` and require every *required* check green. A red
   required check blocks — do not merge. A red *non-required* check must be
   explicitly classified as pre-existing (`gh run list` evidence it failed on
   the base branch before this episode) or fixed first. Never tell the human
   "all gates passed" meaning the critic gates while repo CI is red — they are
   different gates; report both.
4. If the stage has no critic → `step-record $EID <stage> --critic-status n/a --summary "..."`, advance.
5. Heartbeat the lock.

### 4a. Mandatory skill hooks per stage

Three Keith-validated release-chain skills are wired into the stage loop. They are NOT critics (no `critic-check` parsing) — they run *before* the stage's critics so the diff arriving at each critic has already been self-reviewed and sanity-checked. Skip them and the critics waste sub-agent budget on issues the skill would have caught.

- **`execute` stage — run `/self-review` as the tail step before manifest emit.** Same-session pass over the diff just produced. Catches missed requirements, regressions, and forgotten edge cases that `code-review-critic` would otherwise spend a sub-agent finding. Record the summary in the manifest's `self_review_summary` field — the schema enforces this at `stage: execute, status: completed`, so the validator will reject the manifest without it. If `/self-review` surfaces a must-fix, address it in-stage before emitting the manifest — do not advance.

- **`review` stage — `/review` is the canonical implementation of `independent-review-critic`.** The review-stage sub-agent brief should *invoke* `/review` against the base branch and grade its output into the critic contract. Both `independent-review-critic` and `codex-review-critic` gate independently; codex provides the cross-model second opinion.

- **`ship` stage — run `/ship-check` as the first step.** Pre-PR sanity pass: what shipped, is it worth shipping, did we do enough QA? Save the output to the manifest's `ship_check_summary` field — the schema enforces this at `stage: ship, status: completed`, so the validator will reject the manifest without it. Pass the summary to `ship-readiness-critic` as input. A blocker from `/ship-check` short-circuits the stage — escalate to the human rather than asking the critic to rubber-stamp it.

- **`ship` stage — record deploy metadata right after the PR opens.** `python ~/.claude/dev-framework/scripts/devrl.py episode-deploy-record $EID --pr-url <PR-URL>` (the ship manifest schema now REQUIRES a `pr_url` artifact at `status: completed`; a sanctioned no-PR ship — direct-commit / quant pipelines — records the literal `none`). At the `deploy` stage after merge, re-run with `--merge-commit <SHA>`. This is the producer feeding `episode-deploy-meta`, the `devrl-post-deploy` cron, and every outcome-weighted learning leg — an episode that skips it can never resolve a post-deploy outcome (the 0/95 outcome-starvation root cause, fixed 2026-06-09, PLAN-continuous-loop Phase A).

- **`ship` stage — run `/quiz-me from-diff HEAD` after `/ship-check`, before `ship-readiness-critic`.** Operator-knowledge gate. Generates 5 MC + 1 explain-back from the episode's diff, quizzes the human operator interactively, grades honestly. Then runs `python ~/.claude/skills/quiz-me/scripts/quiz.py gate` — exit 1 blocks the ship stage until the operator clears any failed cards via a follow-up `/quiz-me` session. Save the quiz summary in the manifest's `quiz_me_summary` field (optional schema field today; may be promoted to required in a future iteration once the workflow shape stabilises). This is what enforces "no new features until the operator understands the last one" — the orchestrator's other gates protect against bad code, this one protects against bad operator mental models. Skip this gate in headless / spawned-session mode (no human at the keyboard to quiz); record `quiz_me_summary: "skipped (headless)"` in the manifest so the gap is visible. **Loop mode: defer, don't skip** — record `quiz_me_summary: "deferred to batch gate (loop mode)"` and run the accumulated quizzes (plus `quiz.py gate`) at the batch deploy gate, one sitting with the human present, before the deploy decision.

- **`plan` stage — run `/grill-me` as the tail step before plan-eng-critic.** "Me" here is the orchestrator (you). The grill interrogates the orchestrator's own plan: weakest premise, hidden assumptions, what would have to be true for this plan to work, what would falsify it, which scope claims are unsupported. The grill output is INPUT to plan-eng-critic — the critic should judge whether the plan addresses the grill's objections or explicitly accepts them as out-of-scope. Save the grill summary in the manifest's `self_grill_summary` field (optional schema field today; may be promoted to required in a future iteration once the workflow shape stabilises). If the grill destroys the plan (a premise can't be defended), revise the plan before plan-eng-critic runs — do not present a known-broken plan to the critic.

- **(Optional, opt-in) Meta-critic mode** — when a critic returns `pass`, the orchestrator MAY run `/grill-me` against the critic's verdict + reasoning, asking "did this pass actually hold up under adversarial pressure?" If the grill breaks the pass (surfaces an issue the critic missed), the verdict becomes provisional: record as `friction` via `episode-friction` and either re-run the stage with the missed concern in the must-fix, or escalate to the human. This is expensive (extra sub-agent per pass) and OFF by default — opt-in via `episode-init --meta-critic-grill`. Reserve for high-stakes episodes (production deploys, schema migrations, security-touched diffs). Tier 10's `learn-evolve` reads `friction` notes flagged this way to propose critic-prompt mutations.

`/full-power` is deliberately NOT wired — the orchestrator already fans out sub-agents per critic, so layering it on inflates token cost without changing behaviour. `/grill-me` is wired because it's targeted adversarial pressure on a specific artifact (framing / plan / verdict) at a specific decision point, not a general "try harder" mode.

### 5. Finalize

The **final ship gate is human-in-loop** — the orchestrator never auto-marks an episode `shipped`. Present the trajectory (`episode-get $EID` + `episode-steps $EID`), let the human confirm, then:

```bash
python scripts/devrl.py episode-finalize $EID --status <shipped|aborted|cap-exceeded>
python scripts/devrl.py reward $EID --automated-score <0-100>
python scripts/devrl.py lock-release $EID
```

`reward` loads the per-type rubric, derives the gates (shipped, all-critics-passed) and the user-satisfaction component from the DB, and writes `final_reward` + `reward_breakdown`. Pass `--automated-score` from the verify-stage results. Downstream-stability is left deferred — it resolves after the next episode — so the score is **provisional** until then. The scalar is a dashboard metric; the learn step keys off the trajectory, not this number.

Roughly 7 days after a shipped episode's deploy, record whether it held up: `python scripts/devrl.py episode-postdeploy $EID --clean` (or `--regressed`). This feeds the learn mode's `regression_rate` weighting.

At the start of any orchestrator session, run `devrl.py status` — it surfaces pending satisfaction prompts; record them then (`satisfaction-pending` prints ready-to-run commands, `satisfaction-record-batch ID=SCORE ...` records several at once).

### 6. Learn step (per-episode)

After finalize + reward, run the learn check:

```bash
python scripts/devrl.py learn-check $EID
```

Exit 0 → nothing to learn; the episode is done. Exit 1 → a learn trigger fired (`critic_pass_rate < 0.6`, `human_redirects >= 2`, or `operator_friction` — any recorded friction note). The command prints a JSON report of the trajectory facts: failed stages, retried stages, the aggregated `must_fix` items from the failing critics, and `friction_items`.

**Recording friction.** If at any point during the episode you hit operator friction — a missing command, a manifest that misled, a doc that lied, a step painful for a reason no critic would catch — record it:

```bash
python scripts/devrl.py episode-friction $EID --note "<what was painful / what should improve>"
```

Notes accumulate on a single `friction` step and are inert to the critic, reward, and budget math. A clean episode with friction has nothing for the critics to fail, so friction is the channel that carries that signal into the learn step.

When triggered, read the report and propose **1-3** concrete deltas — each a change to a hippo memory, a skill prompt, or (rarely) a CLAUDE.md, per the 3-tier model under Learn mode — that would have prevented the observed failure or friction pattern. Present them as a consolidated-revisions blob: section reference, one-sentence issue, concrete fix.

**Never auto-apply tier-2 (skill prompts) or tier-3 (CLAUDE.md) deltas** — even headless; wait for the human's explicit "apply" and the human makes the edit. **The single exception (B4, Keith-approved 2026-06-09): tier-1 hippo probation memories.** The per-episode learn step MAY write the hippo memory and register it without waiting:

```bash
python scripts/devrl.py memory-register <memory-id> --auto-tier1 --episode $EID [--cluster <cluster-id>] --summary "<one-line delta summary>"
```

The command REJECTS memories lacking a valid `warning_pattern:` frontmatter (add the regex first — never accept-and-flag) and writes the `policy_updates(trigger='auto-tier1')` audit row in the same transaction. Auto-added memories auto-promote at 3 QUALIFYING confirmations (the confirming episode terminated `shipped`) and auto-deprecate on 0 qualifying confirmations across the next 10 terminal episodes OR a regressed-scope hit (the memory was in `step_prompts.hippo_memory_refs` of a failing stage of a later-regressed episode). The weekly digest lists every auto-added / promoted / deprecated memory.

Base the proposal on the *trajectory* (the failed stages, their `must_fix` items, and any `friction_items`), not on `final_reward`. The scalar reward is a dashboard metric; the structured trajectory is the learning signal.

The batch `learn` mode below does cross-episode failure-mode clustering and owns the `policy_updates` audit trail. This per-episode step is deliberately thin: detect, surface, propose.

## Learn mode (`/dev-framework-rl learn`)

A separate mode from running an episode — the cross-episode pass. Run it periodically (weekly, or after a batch of episodes): cluster recurring failures, propose policy deltas, record what gets applied.

### Where a delta lands — the 3-tier model

Pick the tier by how settled and how cross-cutting the lesson is:

1. **Hippo memory** — the default. Small or tentative lessons. Cheap, decays, probation-gated (`--memory-added`). Reach here unless the lesson clearly belongs higher.
2. **Skill prompt** — when a workflow or critic actually behaved wrong. Medium weight. Recorded with `--skill-changed <path>`.
3. **CLAUDE.md (project or global)** — the top tier, deliberately rare. Only a lesson that recurred across many episodes, is a genuine cross-cutting rule, and would keep happening otherwise — a "law", not a tip. Tips go to tier 1.

Tier 3's bar is high because a CLAUDE.md loads into every session: it costs tokens every run and is the highest-blast-radius place to be wrong. A cluster qualifies only when its `regression_rate` is non-trivial — it recurred *and* caused real post-deploy regressions — not merely high `occurrences`. Record it like a skill: `--skill-changed <path-to-that-CLAUDE.md>` (the audit trail hashes any path). Two guards apply automatically: the learn loop never auto-applies, and the global Hand-Maintained-Files rule forces show-content + explicit-apply + a `.old` backup before any CLAUDE.md edit. Episodes record `project_type`, not a project path — the human names the exact file at approval time.

### 1. Recompute clusters

```bash
python scripts/devrl.py learn-cluster
```

Re-clusters every failed step's `must_fix` item and every operator `friction` note across all episodes into lexical failure modes. Human-acted clusters (applied / rejected) keep their status across the recompute.

### 2. List actionable clusters

```bash
python scripts/devrl.py learn-list
```

Prints the `pending` clusters — those with at least 5 occurrences — each with its pattern, example snippets, and `regression_rate` (the fraction of its occurrences whose episode regressed post-deploy; `null` until outcomes are known).

### 3. Propose deltas

For each actionable cluster, propose **one** policy delta — a change to a hippo memory, a skill prompt, or (rarely) a CLAUDE.md, per the 3-tier model above — that would prevent that failure pattern. Weight attention by `regression_rate` first (clusters whose failures led to real post-deploy regressions), then by `occurrences`. Present all proposals as a single consolidated-revisions blob: cluster id, one-sentence pattern, concrete fix.

**Never auto-apply** — even headless. Wait for the human's explicit "apply" / "reject" per cluster. (Tier-1 probation memories are the single auto-apply exception — but ONLY in the per-episode learn step, never in this weekly/batch mode: the weekly pass stays strictly propose-only, R8.)

### 4. Record the decision

On apply — the human (or you, with approval) makes the edit, then:

```bash
python scripts/devrl.py learn-apply --summary "<what changed>" --failure-mode <id> [--failure-mode <id> ...] [--skill-changed <path> ...] [--memory-added <id> ...]
```

Writes a `policy_updates` audit row, a `policy_skill_changes` row per edited skill file (with its post-edit SHA-256), and marks the addressed clusters `applied`.

A delta that adds a hippo memory passes `--memory-added <id>` — the memory enters on **probation**, not yet trusted. Probation memories DO recall into episodes: at episode init run `memory-list --status probation`, carry the relevant ones into stage briefs tagged `[PROBATION]` (an unconfirmed hint — weigh it accordingly, never as settled law), and record their ids via `step-record --memory-ref <id>` so the auto-confirm machinery sees them as active. (R9 fix, 2026-06-09: the old "keep out of episode context until promoted" rule was a deadlock — a memory that is never in context can never earn confirmations; 5 sat stuck with 0 promotions ever.) Promotion to `active` takes 3 QUALIFYING confirmations — auto-confirm only counts episodes that terminated `shipped` (`devrl.py memory-confirm <id>` for manual ones); `memory-deprecate <id>` retires one that is not helping; `memory-list --status probation` shows what is still on probation.

On reject:

```bash
python scripts/devrl.py learn-reject --failure-mode <id> [--failure-mode <id> ...]
```

Applied and rejected clusters are not re-proposed on the next `learn-cluster`. Weight the deltas by what kept failing, not by `final_reward` — see RL-PLAN "Scalar Reward vs Learning Signal".

## Loop mode (`/dev-framework-rl loop <target> [--batch N] [--max-episodes M]`)

The continuous-improvement mode (added 2026-06-10, Keith-approved): one
command, episodes run back-to-back, and the orchestrator SOURCES ITS OWN WORK
when nothing is queued. `<target>` is ONE repo per loop run (e.g. `hippo`) —
a multi-repo product gets one loop per repo, never one loop spanning repos.
Defaults: `--batch 5`, `--max-episodes 15` per loop run.

**No external scheduler is required.** Loop mode runs cycle after cycle
within the live session — finishing an episode starts the next one; ending
the turn mid-loop is a bug, not a feature. External re-entry is only for
session-boundary survival: wrap with `/loop` for self-paced re-invocation
across idle periods, or use the Phase D nightly cron (gated; see
PLAN-continuous-loop.md) for fully headless runs.

### Run state + compaction protocol (context is scratch; files are truth)

All run-level state lives in `<repo>/.devrl-loop-state.json`, rewritten at
every cycle boundary — never carried in conversation memory:

```json
{"run_id": "<ULID>", "target": "<repo>", "batch_id": null,
 "episodes_run": 0, "max_episodes": 15, "batch_size": 5,
 "started_at": "<ISO>", "in_flight_eid": null, "breaker_tally": 0,
 "status": "running"}
```

- **Compact at cycle boundaries, deliberately.** After each episode's
  finalize + reward + lock-release + state-file write — and at every batch
  deploy gate — run `/compact` with a focus instruction naming `run_id`,
  `batch_id`, `episodes_run`/`max_episodes`, and the next backlog item.
  Never let autocompact fire mid-stage: at the boundary everything
  load-bearing is externalized by construction, so compaction is lossless;
  mid-stage (sub-agent verdicts, unrecorded must-fix text) it is not. The
  boundary compact doubles as the externalization test — anything lost there
  was a bookkeeping bug, surfaced immediately instead of at a random
  autocompact.
- **Re-hydrate after any compaction or session resume.** Treat remembered
  context as untrusted: re-read `.devrl-loop-state.json`, `devrl.py status`,
  `batch-get <batch_id>`, `.devrl-backlog.md`, and `episode-steps
  <in_flight_eid>` (if any) BEFORE the next action. Memory-recalled loop
  state fails under load exactly like cwd discipline does; mechanical
  re-derivation doesn't.
- **Run-level caps are wallclock-honest.** Enforce `--max-episodes` from the
  state file's `episodes_run`, never from conversation memory. Check the
  run-level wallclock cap from `started_at` at every boundary. Token totals
  stay advisory, as ever. In loop mode run `budget-check $EID` after EVERY
  stage (not just headless) — it is the PAUSE-sentinel and per-episode
  wallclock enforcement point.

### Target-level loop lock

Episode host-locks do not cover triage/sourcing collisions between two loops
on the same repo. Before the first cycle, claim `<repo>/.devrl-loop.lock`
(JSON: `{"session": "<id>", "heartbeat": "<ISO>"}`; refresh at each cycle
boundary). Another session's lock with a heartbeat younger than 10 minutes →
do NOT loop this target; report and stop. Stale lock → take it over and note
the takeover in `## Done`. Remove the lock on EVERY exit path (see Stop
epilogue).

### Per-cycle procedure

0. **Batch lifecycle.** If the state file has no open `batch_id`:
   `batch-init "<target>-loop-<run_id>-<n>"` and record the returned id in
   the state file. (Tier 7 requires an open batch before any `batch-add`; a
   fresh batch is opened after every deploy gate, never reused across gates.)
1. **Source the backlog** (priority order; reproduce-check every item per the
   triage rules above before it qualifies as an A-item):
   a. `<repo>/.devrl-backlog.md` — the ordered episode backlog this mode
      maintains (create via triage if missing; keep it ordered, dated, with
      one-line acceptance criteria per item).
   b. The repo's `TODOS.md` / issue tracker.
   c. **Trajectory-derived follow-ups for this repo**: low-severity critic
      advisories from PASSED gates, `episode-friction` follow-ups, and
      actionable clusters (`learn-list`) scoped to this target. These are
      pre-vetted by real reviews — they outrank speculative work. NOTE:
      nothing indexes pass-verdict advisories after the fact (`failure_modes`
      stores only failing must-fix items), so capture them AT THE MOMENT a
      pass verdict is parsed — append them to `.devrl-backlog.md`'s candidate
      section right then, while they are still in context.
   d. Known bugs in memory (hippo context / Claude memory files) that
      reproduce-check against current master.
   e. **Opportunity scan — the "go out of your way" stage.** Only when a-d
      are dry: run an improvement audit (standards/security pass, performance
      profile, DX/help-text review, dead-code sweep, test-coverage gaps) and
      GENERATE candidate episodes, ranked by user-visible impact.
2. **Anti-make-work guard (hard).** Every episode entering the backlog —
   especially scan-generated ones — must state (i) the user-visible benefit
   OR a named risk-reduction with a falsifiable failure scenario (security,
   data-loss, correctness debt — "cleaner code" alone does not qualify)
   and (ii) a falsifiable acceptance criterion. A candidate that can't name
   both is logged in `.devrl-backlog.md` under `## Below the bar` and NOT
   run. When a scan yields nothing above the bar, the loop STOPS honestly
   ("backlog dry, no above-bar opportunities") — continuous improvement
   never means inventing busywork.
3. **Run the top item as a full episode** — every gate, hook, and worktree
   rule in this skill applies unchanged, with two loop-mode adjustments:
   (a) **`/quiz-me` is deferred, not skipped** — record
   `quiz_me_summary: "deferred to batch gate (loop mode)"` in the ship
   manifest and run the accumulated quizzes at the batch deploy gate (the
   human is present there anyway); N synchronous quiz interrupts between
   gates would defeat back-to-back execution. (b) **Remove the episode
   worktree right after the ship-stage PR push** (the branch survives;
   `rmdir` a junctioned `node_modules` first, per the worktree section) —
   do not accumulate N worktrees waiting for the batch gate. Ship stage
   stops before deploy; `batch-add` the episode (Tier 7); update the state
   file (`episodes_run += 1`, `in_flight_eid: null`); then compact per the
   protocol above.
4. **Batch deploy gate** every `--batch` episodes, when the backlog empties,
   or on operator request: `batch-finalize`, run the deferred `/quiz-me`
   sessions (then `quiz.py gate` — a failed gate blocks the deploy decision
   exactly as it blocks a ship stage), present the PRs together, ONE human
   deploy decision, `batch-deploy`, then `episode-deploy-record
   --merge-commit` per merged PR. A project CLAUDE.md may set a standing
   pre-authorization (e.g. "patch-level, all-gates-clean episodes
   auto-merge") — that standing rule IS the human decision, made once (the
   closed-list "Final ship gate" carve-out); without one, deploy always
   waits for the human. After the gate, clear `batch_id` in the state file —
   the next cycle's step 0 opens a fresh batch.
5. **Learn pass after each batch** (`learn-cluster` + `learn-list` +
   propose-only blob; per-episode auto-tier1 memory rules apply as ever),
   then the next cycle begins.

### Stop conditions (closed list)

- `--max-episodes` reached (from the state file's `episodes_run`), or the
  run-level wallclock cap spent (from `started_at`; per-episode budgets as
  usual — token totals stay advisory)
- `PAUSE` sentinel (`~/.claude/dev-framework/PAUSE`) — surfaced by the
  per-stage `budget-check`
- Any operator message mid-loop: heartbeat the lock and **answer the
  operator FIRST** (direct messages pre-empt loop work — global rule), then
  resume the in-flight stage; pause at the next clean boundary only if the
  operator asked for a stop. The lock heartbeat + worktree isolation are
  what make mid-stage resumption safe.
- Two consecutive episodes ending `aborted`/`cap-exceeded` — circuit
  breaker: stop and report instead of burning budget on a stuck pipeline.
  **Reproduce-check WINs are excluded from the tally** (§3b finalizes a
  stale-TODOS win as `aborted`, but a win is not a failure — record it as a
  WIN in `## Done` and leave `breaker_tally` untouched).
- Backlog dry after an opportunity scan with nothing above the bar

### Stop epilogue (mandatory on EVERY exit path, including errors)

1. **Never exit with a silently open batch.** If the current batch has
   members: run the deploy gate now if the human is present; otherwise
   append a `## Handoff` block to `.devrl-backlog.md` naming the open
   `batch_id`, member episode ids, and PR URLs — and say so in the stop
   report. Rationale: `batch-add` NULLs `post_deploy_due_at` and
   `batch-deploy` is its SOLE re-writer (`batch_store.py`), so an abandoned
   open batch makes its episodes invisible to `postdeploy-due` forever —
   the 0/95 outcome-starvation hole, selectively re-opened.
2. Write the state file with `status: "stopped:<reason>"`.
3. Remove `<repo>/.devrl-loop.lock`.

### Loop-mode bookkeeping

Record the loop run itself as friction-free trajectory data: each episode is
normal; additionally append one line per cycle to `.devrl-backlog.md`'s
`## Done` section — `<run_id> | <episode id> | <item> | <outcome>`. The
run_id attribution is what makes `--max-episodes` accounting reconstructable
across compactions and distinguishes concurrent or historical runs. The
weekly learn cron picks up everything else automatically.

## Running across a multi-item roadmap

A single episode is one shippable problem. A project roadmap (a `TODOS.md`, an
issue tracker, a backlog) is not a flat list of episodes: its items range from
one-line fixes to multi-week projects. Do not iterate a backlog top-to-bottom
feeding each line in as an episode. Triage it into episode-sized units first.
This procedure is project-agnostic — it works on any backlog.

### 1. Triage pass (cheap — not itself an episode)

Bucket every open backlog item:

- **A — episode-sized.** A coherent fix or self-contained feature that ships as
  roughly one PR. One `/dev-framework-rl` episode each.
- **B — trivial.** A one-line test gap, a defensive guard, a doc typo. The nine
  stages and the critic sub-agents cost far more than the work and have nothing
  to catch. Batch 4-6 into ONE "hardening pass" episode, or do them as an
  ordinary small PR outside this orchestrator.
- **C — project-sized.** A multi-week effort (a redesign, a new subsystem). Not
  an episode. Run a decomposition pass first (`/office-hours` or
  `/plan-ceo-review`) that splits it into A-sized episodes.

**Reproduce-check every A-item before it enters the backlog.** A backlog item
describes a defect as it was when the item was written; an unrelated refactor
may already have fixed it. Before listing an A-item as an episode, open the
code it names and confirm the described behaviour still exists in current
`master`. An item that no longer reproduces is not an episode — move it to
backlog hygiene and mark the source TODO done, citing the fixing commit. A
`TODOS.md`-internal consistency pass does not catch this; staleness left by a
refactor is only visible in the code.

Also record dependencies and clusters: items that must ship in order, or
together. The output is an **ordered episode backlog**, not a flat checklist.

### 2. Run a batch, holding the gates

Run the backlog about five episodes at a time. Take each episode through
`discover` to `ship` — all the reversible work, including local commits — and
**stop before `deploy`**. Deploy is irreversible (publish, merge, tag) and is a
human-in-loop gate; do not spend that gate once per episode.

### 3. One batched deploy gate

Present the batch's ship-ready episodes together: the human reviews N PRs in one
sitting and makes one deploy decision, instead of N separate interrupts. A
project may instead set a standing pre-authorization (for example "a patch-level
episode that passed every critic clean auto-deploys; minor or major needs the
gate"), recorded in that project's `CLAUDE.md`.

### 4. Learn pass after the batch

After 5-10 episodes, run `/dev-framework-rl learn` (the cross-episode
clustering). One episode's `learn-check` is thin signal; recurring failure modes
only surface across a batch. Apply the policy deltas, then start the next batch.

### Scaling notes

- Fix orchestrator defects before scaling a batch. Running N episodes on a
  known-buggy pipeline multiplies the friction N times.
- Episode cost is real (nine stages, several critic sub-agents, repeated
  build/test). Triage is what keeps the spend proportionate to the work.
- Nothing in this procedure or the critic/reward machinery is project-specific.
  If a future gate genuinely needs project-specific behaviour, key it off the
  `project_type` from `stage-plan.json`, never off a hardcoded project path.

## Human-in-loop gates (closed list — auto-progress everywhere else)

- Schema/migration changes to live data
- Production deploys, force pushes, irreversible shared-infra ops
- Destructive ops (>100 lines deleted, file/branch deletion, DB drops, locked-signal overwrites)
- Paid services / new external services
- Critic retry-cap exceeded (per-stage cap)
- Critic parse error (`critic-check` exit 2)
- Manifest validation failure
- Final ship gate — always (a standing pre-authorization recorded in the project's CLAUDE.md counts as that human decision, made once — see Loop mode step 4 / "One batched deploy gate"; absent one, per-episode or per-batch human confirmation)

## Worktree isolation for code episodes (execute stage)

For any CODE episode in a repo with concurrent multi-agent activity (check `git worktree list` — if `.claude/worktrees/` shows active/locked agents, or another session may `git checkout` the shared tree), do the **execute** stage in a DEDICATED worktree from the START:

```bash
git worktree add <tmp-path> -b feat/<episode> origin/master
```

Edit + build + test there; never edit the shared main working tree. A concurrent session can `git checkout <other-branch>` on the main tree mid-stage — and during a multi-minute execute sub-agent run it WILL — silently moving your uncommitted edits onto the wrong branch. **Edit-in-place is unsafe even pre-commit**: the hazard is the branch switching under you, not just a mis-targeted commit. Recovery (capture `git diff` → worktree → `git apply` → reverse-apply `git apply -R` off the wrong tree, `--check`-guarded) is non-destructive but costs a full detour. Learned twice on hippo (2026-06-02 analytics commit landed on the E3.2 branch; 2026-06-02 A7 recall-trace — the main tree switched master → a concurrent E-session's branch during a 9-minute execute sub-agent). Reuse the same worktree for the ship-stage commit/push so the work never touches the shared tree.

node_modules in the worktree: junction from the main checkout (`mklink /J node_modules <main>\node_modules` on Windows) to skip a full reinstall — but remove the junction with `rmdir` (Windows) BEFORE `git worktree remove`, or the worktree removal can follow the junction and delete the MAIN repo's node_modules.

## Real test-DB convention (`verify` stage)

If the project's tests need a real database (per the global `always use real DB for tests` rule), start it **outside the execute agent's process group** so the verify stage can re-run against it cheaply.

- Project should ship a `scripts/test-db-up.sh` (or equivalent) the orchestrator session invokes before the execute stage. Port and auth pinned in `.env.example`.
- The execute agent uses the existing instance; it does NOT bootstrap its own. If the execute agent stands up an ad-hoc DB inside its own subprocess tree, the DB dies with the agent and the verify stage cannot re-run.
- The verify agent re-runs `npm test` (or equivalent) against the same instance — second confirmation is cheap.
- If the DB ends up bootstrapped inside the execute agent regardless, document the limitation in the verify manifest (`status: completed` with caveat) and recommend the human re-run before merge. Do NOT auto-fail verify on a one-shot run; do NOT pretend the run is a second confirmation when it is not.

Learned 2026-05-23 from the resona admin-dashboard Phase A episode (`01KSA2C6YSMSFFDE0X37PZ3EK0`): the execute agent bootstrapped a `/tmp/pgdata` trust-auth PG that died with its process group, and the NetworkService-owned surviving backends held the port from re-bind without admin, so the verify stage had no way to re-run.

## Headless mode

Run an episode unattended: `claude -p "/dev-framework-rl '<problem>'" --output-format json`. Set the wallclock budget at init — `episode-init --wallclock-budget-sec N`.

After each stage, run the safety check:

```bash
python scripts/devrl.py budget-check $EID --consecutive-fail-cap 3
```

Exit 0 → continue. Exit 1 → stop; the JSON `verdict` is one of:
- `paused` — the `~/.claude/dev-framework/PAUSE` sentinel file exists
- `wallclock-exceeded` — elapsed time is past the episode's `wallclock_budget_sec`
- `consecutive-fail-cap` — too many critic failures in a row

On a stop verdict, finalize the episode (`--status cap-exceeded`, or `aborted` for a pause) and stop the run.

Enforced caps are wallclock, consecutive-fail, and the PAUSE sentinel — all reliably checkable. Token budget is recorded (`episode-init --token-budget`) but advisory only: Claude cannot reliably self-count tokens mid-run, so wallclock is the honest hard cap.

To pause every running episode: `touch ~/.claude/dev-framework/PAUSE` — remove the file to resume.

## CLI reference (`python scripts/devrl.py <cmd>`)

| Command | Purpose | Exit codes |
|---|---|---|
| `status [--json]` | operator dashboard: in-flight + last cluster + last shipped (Tier 0.0) | 0 |
| `episode-init "<problem>" [--critic-set <s>]` | create episode; `--critic-set default\|minimal\|full\|random` (Tier 4) | 0 |
| `episode-get <id>` | print episode JSON | 0 / 2 missing |
| `episode-steps <id>` | print the episode's recorded steps as JSON | 0 / 2 missing |
| `episode-friction <id> --note S` | record an operator friction note (feeds learn-check) | 0 / 2 missing |
| `set-project-type <id> <type> <rubric>` | set type + rubric | 0 |
| `episode-finalize <id> --status <s> [--user-satisfaction N\|deferred] [--redirects N] [--learn-emit] [--no-prompt]` | close episode; `--learn-emit` writes pending_apply blob (Tier 0.2 / Tier 3) | 0 / 2 |
| `satisfaction-record <id> N` | fill in deferred user_satisfaction post-hoc (Tier 0.2) | 0 / 2 missing |
| `episode-postdeploy <id> --clean/--regressed` | record 7-day post-deploy outcome | 0 / 2 missing |
| `postdeploy-due` | list shipped episodes whose 7-day window has passed (Tier 0.1) | 0 |
| `postdeploy-prompt [--within-days N] [--json]` | operator-facing pending summary (table or cron-friendly JSON) (Tier 0.4) | 0 |
| `episode-deploy-meta <id>` | emit pr_url + merge_commit (+ `*_source` provenance) + ended_at (Tier 0.1 / Phase A) | 0 / 2 missing |
| `episode-deploy-record <id> --pr-url U [--merge-commit C] [--source backfill]` | record deploy metadata on the latest ship/deploy step (Phase A producer; `none` = sanctioned no-PR ship) | 0 / 2 |
| `satisfaction-pending [--limit N] [--unnotified-only] [--mark-notified] [--json]` | list deferred satisfaction scores, oldest first (Phase A) | 0 |
| `satisfaction-record-batch ID=SCORE [ID=SCORE ...]` | bulk-record deferred scores, all-or-none (Phase A) | 0 / 2 |
| `lock-acquire <id> --session <s>` | claim host lock | 0 ok / 1 denied |
| `lock-heartbeat <id>` | refresh lock | 0 ok / 1 vanished |
| `lock-release <id>` | release lock | 0 |
| `reap` | mark stale episodes stalled | 0 |
| `step-record <id> <stage> [--prompt SKILL] [--memory-ref ID ...] [--artifact KIND=VALUE ...] [...]` | log a step + optional step_prompts row + value-artifacts (Tier 0.3 / Phase A) | 0 / 2 bad artifact spec |
| `critic-check <critic-name> <file>` | parse critic response | 0 pass / 1 fail / 2 error |
| `brainstorm-rank <id> <candidates.json> --judge <file>\|--select-idx N` | record candidates + ranking (Tier 2) | 0 / 2 |
| `reward <id> [--automated-score N]` | compute + store episode reward | 0 / 2 missing |
| `learn-check <id>` | per-episode learn-trigger check | 0 none / 1 triggered / 2 missing |
| `budget-check <id> [--consecutive-fail-cap N]` | headless safety check | 0 continue / 1 stop / 2 missing |
| `learn-cluster [--mode lexical\|embedding] [--threshold F]` | recompute failure-mode clusters (Tier 1) | 0 |
| `learn-list` | list actionable clusters | 0 |
| `learn-apply --summary S --failure-mode ID ...` | record an applied policy delta | 0 / 2 |
| `learn-reject --failure-mode ID ...` | reject a cluster | 0 |
| `apply-pending <id> [--clear]` | view or clear pending_apply/<id>.json (Tier 3) | 0 / 2 |
| `embed-cache-prune [--older-than N]` | remove embed cache entries older than N days (Tier 1) | 0 |
| `codex-shadow <id> <stage> --local-verdict <v> [--max-wait-sec N] [--brief <file>]` | log codex second opinion; never gates (Tier 5) | 0 / 2 |
| `codex-shadow-report [--since DATE]` | list codex disagreements (Tier 5) | 0 |
| `critic-ab-report [--since DATE]` | per critic_set aggregates over shipped episodes (Tier 4) | 0 |
| `batch-init <name>` | create a batch (Tier 7); fails if name exists | 0 / 2 |
| `batch-add <batch_id> <episode_id>` | add episode (clears its `post_deploy_due_at`) (Tier 7) | 0 / 1 / 2 |
| `batch-list [--open-only]` | list batches (Tier 7) | 0 |
| `batch-get <batch_id>` | show batch + members (Tier 7) | 0 / 2 |
| `batch-finalize <batch_id>` | finalize batch + auto-cluster (Tier 7) | 0 / 1 / 2 |
| `batch-deploy <batch_id> --decision shipped\|aborted\|partial` | record deploy + set due_at for shipped members (Tier 7) | 0 / 1 / 2 |
| `learn-attribute [--since DATE] [--include-backfill]` | recompute critic_trust_scores incl. v2 (Tier 8/9; backfill outcomes excluded by default per R4) | 0 |
| `critic-trust [--critic NAME] [--json]` | read view over critic_trust_scores (Tier 8) | 0 |
| `stage-gate <id> <stage> [--weighted]` | evaluate a stage's gate from recorded verdicts; trust-weighted when episode opted in (Tier 9c) | 0 pass / 1 fail / 2 error |
| `audit-record <id> --rule SLUG[:note] ...` | record fired §3b audit rules (C1) | 0 / 2 |
| `policy-compact-report [--min-episodes N]` | propose-only policy-decay report over rule firings (C1) | 0 |
| `memory-register <id> [--auto-tier1 --episode E --summary S [--cluster C]]` | register a learn-added memory (probation); auto-tier1 = B4 auto-apply path, rejects without valid warning_pattern | 0 / 2 dup or rejected |
| `memory-confirm <id>` | confirm a memory useful | 0 / 2 missing |
| `memory-deprecate <id>` | retire a memory | 0 / 2 missing |
| `memory-status <id>` | show memory lineage | 0 / 2 missing |
| `memory-list [--status S]` | list memories by lineage status | 0 |
| `memory-needs-pattern` | list probation memories missing `warning_pattern` (Tier 6) | 0 |

All free-text fields are secret-scrubbed before they reach the DB.

## Files

Orchestrator infrastructure lives in `~/.claude/dev-framework/` (see its `README.md`):
- `RL-PLAN.md` — full design (v0.6)
- `episodes.db` — SQLite trajectory store
- `scripts/devrl.py` — the CLI this skill drives
- `scripts/` — `episode_store`, `scrubber`, `critic_contract`, `critic_registry`, `rubric`, `reward`, `learn`, `clustering`, `ulid_gen`, `validate_manifest`, `migrate`
- `adapters/critics.py` — the 6 verdict critics (data-driven)
- `prompts/critic-*.md` — the 6 critic sub-agent briefings
- `rubrics/REWARD.*.md` — 8 per-project-type reward rubrics
- `schemas/` — stage-manifest + stage-plan JSON schemas
- `tests/` — real-DB test suite (`python -m pytest tests/`)
