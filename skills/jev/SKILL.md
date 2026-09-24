---
name: jev
description: Wire TypeSafe Jev into a hook, script or repo the measured way. Our question-writing rules, the lint, the labelled bench against a free baseline, the transcript replay, and the go-live rule. Use with /typesafe-ai whenever a Jev call is being written, changed or reviewed.
---

# Jev, the measured way

`/typesafe-ai` points at the vendor docs. This skill holds what WE measured and the
tools that check a question set before it goes live. Read both. The vendor docs win
on API shape; our numbers win on what to trust.

## 1. Should Jev be here at all?

Jev is faster only where it replaces a model call or a human look. Where no model
call existed, it ADDS a network call: p50 263 ms, p95 701 ms for four questions
(2026-09-19, 136 requests, `docs/EXPERIMENT-PROTOCOL.md` J1).

- A pick an LLM makes today (route, filter, grade, "is this relevant"): replace it.
- A judgment nobody makes today because an LLM was too slow or dear: new feature.
- Text generation, summaries, rewrites, counting, date maths, anything a regex or a
  lookup already gets right: not Jev.
- A blocking hook on every prompt or tool call: only if the bench shows it beats a
  free regex by a wide margin. Log-only data comes from a replay, not a live hook.

## 2. The loop, in order

1. Write a pack: `~/.claude/scripts/jev-packs/<name>.js` exporting
   `{ name, build(input) -> { state, questions }, cases, baselines }`.
   Copy `bash-gate.js`.
2. Write the labelled cases BEFORE the first run, half flag and half no-flag, with
   boundary cases and one trap that only mentions the risky words.
3. Add at least two free baselines: what exists today, and the lazy regex upgrade.
4. Declare the campaign in the project's `docs/EXPERIMENT-PROTOCOL.md`: arms,
   threshold, decision rule, cost cap. The threshold is picked before the run.
5. `node ~/.claude/scripts/jev-bench.js <pack> --repeat 2`. The lint runs first and
   stops on a shape that would 422.
6. Replay real inputs with no labels (`--cases file.json`), then grade the flagged
   rows by hand. The labelled set is a DEV set once wording is tuned on it; the
   replay is the honest judge.
7. Go live only on the declared rule. Reworded questions are a new lane.

Key: `TYPESAFE_API_KEY`, User env var only. A session that started before the key
was set does not have it; launch with
`$env:TYPESAFE_API_KEY = [Environment]::GetEnvironmentVariable('TYPESAFE_API_KEY','User')`.

## 3. Writing the questions

Vendor rules, read 2026-09-19 (`concepts/how-to-build-with-system-one.md`,
`primitives/*.md`, `model-jaggedness/jev-1.13.md`):

- One property per question. "Is this risky?" becomes destroys / sends out / costs
  money / touches a live schema, and code combines them.
- `instructions` is an object: `{ question, context, focus }`. `focus` names the
  boundary ("judge what the command does, not words inside quoted text").
- `noul` criteria is `{ true: {...}, false: {...} }`, each with `what`, `not_for`,
  `examples`. `choice` criteria is a MAP of option to the same object. `score`
  criteria is a LIST of 2 to 10 levels. A wrong shape is a 422.
- State is an object with named fields. Point at fields with backticks:
  `` `command` ``, `` `ticket.messages[0].text` ``. The lint fails any backticked
  token that is not a real state path, so never backtick an example.
- Jev reads literally. State the exact condition and put the boundary cases in
  `not_for`. No double negatives.
- Send only the fields the question needs. Clip long text in code.
- Counting, date order, arithmetic and unit changes happen in code.
- Build the option list in code. Give every `choice` a no-match option.
- Batch every independent question into one request; they cannot see each other.
- Criteria examples must differ from the bench cases, or the bench is a memory test.

## 4. Reading the answers

- `noul` has no confidence. Near 0.5 means unsure. Repeats of one input moved a
  noul by up to 0.06, so never set a threshold inside a 0.06 band of your cases.
- `score` is a probability-weighted mean. Read `probabilities` and sum the mass at
  or over the action level. Never `int(score)`.
- Jev never abstains. It picked an answer on 76 of 76 unanswerable queries in
  hippo. Check reachability or presence in code, or ask it as its own noul.
- Jev favours long text. A ranking win did not become an answer win in hippo at
  k=5: grade what the consumer does with the answer, not the rank.
- A baseline that flags nothing, or nouls with no spread, means the run is void.
  The bench prints DEAD ARM.

## 5. Client rules

- Fail open: no key means no call, any error means the old behaviour. Hooks use
  `~/.claude/scripts/hooks/lib/jev.js` (`ask`, `lint`). hippo and fifty keep their
  own clients (`hippo/src/rerankers/jev.ts`, `fifty/ops/watchdog.py`); copy that shape
  in a new repo, do not build a shared package.
- Everything sent to Jev leaves the machine. Drop secret-shaped input in code first
  (`extract-shell-cases.js` has the pattern).
- 2chain and any repo with a no-phone-home rule: off by default, on by env var.
- Log input tokens from `usage`. Price read 2026-09-19: $0.042 per Mtok input.

## Files

- `~/.claude/scripts/hooks/lib/jev.js` and `hooks/test/jev-lib.test.js`
- `~/.claude/scripts/jev-bench.js`
- `~/.claude/scripts/jev-packs/bash-gate.js`, `extract-shell-cases.js`
- `~/.claude/docs/EXPERIMENT-PROTOCOL.md`
- Memory: `reference_typesafe_jev_usage.md`, `project_jev_everywhere_survey.md`
