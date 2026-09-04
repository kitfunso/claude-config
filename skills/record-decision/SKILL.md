---
name: record-decision
description: "Recording a durable decision: at ship time, or when asked to 'record this decision' or 'write an ADR'."
---

# Record Decision

Capture WHY a decision made sense given the constraints and evidence at the time, in the repo, so any future session (either box, any model, Codex reviews) can grep it. Adapted from Eric Clemmons' ADR gist (gist.github.com/ericclemmons/96cc6c774e2062e6660f1acb97506940).

## When a record is warranted (the worthiness test)

Write one when the work:
- chose among meaningful alternatives (real options existed and were weighed)
- abandoned a preferred design because evidence exposed a constraint
- established a convention that spans components or repos
- accepted a real trade-off (perf vs simplicity, cost vs coverage, ...)
- reversed or superseded an earlier recorded decision

Skip it for: routine maintenance, straightforward bug fixes, implementation detail with one obvious shape, or choices already dictated by an existing record. When skipping at a ship gate, say "no decision record needed" explicitly — silence is not a verdict.

## Where

- `docs/decisions/YYYY-MM-DD-<short-slug>.md` in the current repo. If the repo already uses `docs/adr/`, use that instead — do not create a second directory.
- Land the record in the SAME commit/PR as the change it documents.
- Never rewrite an old record. A changed decision gets a NEW record that names the one it supersedes; add a one-line `Superseded by <file>` note at the top of the old one.
- Hippo repos (a repo with `.hippo/` or the hippo project itself): additionally mirror via `hippo decide "<one-line decision>" --supersedes <id-if-any>` so the decision enters memory lifecycle. The file remains the source of truth.

## Template

```markdown
# <Decision title>

Date: YYYY-MM-DD
Status: accepted | superseded by <file>
Links: <PR / issue / eval doc / plan file>

## Context
<What prompted this. One short paragraph max.>

## Constraints and evidence
- <what was true at the time: measurements, limits, failed attempts — cite files/commands>

## Decision
<The choice made, stated plainly.>

## Alternatives considered
- <option> — <why rejected, one line each>

## Consequences
- <what gets better, what gets harder, known risks>

## Reconsider when
- <the assumption or constraint whose change should reopen this>
```

## Rules

- Terse and scannable: bullets over paragraphs; the whole record under ~40 lines.
- Evidence over opinion: cite the measurement, incident, or failed attempt that actually drove the choice.
- This skill is advisory judgment, not a hook-enforceable gate. The ship-time prompt lives in /ship-check item 10 and the dev-framework SHIP gate.
- Memory writeback: when a record captures something a memory file also tracks, point the memory at the record instead of restating it.
