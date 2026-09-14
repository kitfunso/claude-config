# Rulebook maintenance

Reached from the global CLAUDE.md pointer. This file is never injected; it holds
the material a maintainer needs when editing rules, hooks or model routing. The
operating rules themselves live in CLAUDE.md and rules/.

## Precedence, in full

- Project CLAUDE.md overrides the global file where they conflict. Read the project
  file first; global rules are defaults. A project rule that says "do X via Y" makes
  Y the first move, not a fallback after A fails.
- Collision order: CRITICAL rules and explicit user instructions, then Root Cause,
  then Sourcing, then Decisiveness, then Token Discipline, then Output prose.
- `(CRITICAL)` means never violate, override only via explicit user instruction.
  Everything else is `(DEFAULT)` and yields to project CLAUDE.md or user intent.
- Speed directives (`/fast`, `/full-power`, `/ship`, quick mode, "just do it") buy
  less ceremony, never less rigour: they never skip the framing pass, the source
  reads, or the plan review.
- History of the 2026-09-01 restructure and later edits: `docs/incidents.md`.

## Hooks (deterministic backstops)

Per-box binding lives in `settings.json`; which guards a box registers (the `.js`
originals, the `.py` ports, the tripwire) differs by box. The hook is the verifier;
the prose rule still binds where the hook is blind.

| Guards | Fires on | Blind spots | Escape hatch |
|---|---|---|---|
| Capability existence: `/name` refs get a `[CAPABILITY EXISTS]` notice; never blocks | UserPromptSubmit | bundled skills not on disk, plugin commands, refs without a leading slash | none |
| Git guard: injects the current branch before a mutating git command; warns on banned AI-isms in inline `git commit` text | Bash / PowerShell | `-F <file>` messages are not inspected | none |
| Backup: saves a `.old` copy before any write under `~/.claude/` or to a `CLAUDE.md` | Edit / Write | shell-side edits (`sed`, heredocs, `node -e`) | none |
| PS 5.1 stderr: blocks `2>&1` on native exes (NativeCommandError fakes failure) | PowerShell | none | none |
| Comment budget: denies >3 comment lines in a row, or >20% density at 15+ lines; skips markdown/JSON/config, `docs/`, docstrings, JSDoc with `@param`/`@returns` | Edit / Write | shell writes; cannot judge a WHY comment from a WHAT one | `CLAUDE_COMMENT_BUDGET=off` |
| Resource tripwire: 40+ tool calls with 0 Skill/Agent/Workflow gets a `[RESOURCE TRIPWIRE]` notice; a command matching a rule in the nearest `.claude/tripwires.json` is denied while the protocol file is missing, and run N x every is denied until `AUDIT <sid8> #N` is in the rule's audit file | UserPromptSubmit; Bash / PowerShell | regex on the command text: a loop counts once, a quoted invocation inside an echo can count, denied attempts still count; repos without `tripwires.json` | none |

Registered on the work box (kit.sofun) as of 2026-09-14: capability existence,
git guard, backup, and (proposed) PS stderr and comment budget, all as Python ports
under `scripts/hooks/`. The tripwire is home-box only.

## Rulebook discipline

- A rule without a verifier is a claim. When you write or strengthen a CRITICAL
  rule, propose its deterministic form in the same turn (hook, pre-commit grep, CI
  check). Prose is the search; the hook is the verifier.
- Probation before CRITICAL. Mark a rule distilled from one incident `(probation)`
  beside its incident; promote only after a second, different context confirms it.
- Prune on evidence. The monthly config audit
  (`clawd/memory/cron-prompts/claude-config-audit.md`, check 7, home box) classifies
  rules ACTIVE / LATENT / DEAD and proposes removals.
- Every line in CLAUDE.md and rules/ is context load on every turn. Measured
  2026-09-14 on the work box before this rewrite: CLAUDE.md 8,372 tokens, rules/
  1,279 (chars / 3.8). Re-measure with the section script in `docs/incidents.md`.

## Model routing table

Names rotate, roles don't. Verify against the session environment line before citing
a name.

| Role | Who fills it (verify against env) |
|---|---|
| Highest capability, premium price | Fable 5.1 `claude-fable-5-1`, only on explicit ask |
| Default worker (sub-agents, fan-outs) | Sonnet 5 `claude-sonnet-5` |
| Trivial / mechanical | Haiku 4.5 `claude-haiku-4-5` |
| Legacy Opus | Opus 4.8 `claude-opus-4-8` |

Effort ladder `low | medium | high | xhigh | max` (`output_config.effort`, default
`high`). The prose-voice gap was seen on Opus 4.7 and is unconfirmed since.
