# Skill Design Vocabulary

Concepts distilled from Matt Pocock's `writing-great-skills` (github.com/mattpocock/skills, fetched 2026-07-04). Complements SKILL.md's process rules with a cost model and diagnostic tests.

## Model-invoked vs user-invoked

Two ways a skill reaches the agent:
- **Model-invoked** (default): the description is always in context; the model decides when to trigger. Costs context every conversation.
- **User-invoked**: set `disable-model-invocation: true` in frontmatter. The description leaves the agent's reach; only the user typing the skill's name invokes it. Costs nothing per turn, but costs the human remembering it exists.

Choose per skill. A skill only ever reached by explicit slash-command is a natural user-invoked candidate.

## Context load vs cognitive load

The two opposing costs every skill decision trades between:
- **Context load**: tokens and attention consumed by always-loaded descriptions and bodies. This is the general cost model behind SKILL.md's "Token Efficiency" word-count targets.
- **Cognitive load**: the human cost of remembering which user-invoked skill to reach for.

Cutting one raises the other. Name the trade explicitly when picking invocation mode.

## Router skill

When user-invoked skills multiply past what you can remember, add one user-invoked **router skill** that names the others and when to reach for each. Cures piled-up cognitive load without re-loading every description into context.

## The no-op test

A line the model already obeys by default is a no-op: it costs tokens and changes nothing. The test is falsifiable: **does this line change behaviour versus the default?** If you cannot name the behaviour it changes, delete it. (The sharper form of "ALWAYS/NEVER in caps is a yellow flag".)

## Completion criterion: two axes, cheap fix first

A completion criterion can fail on two independent axes:
- **Clarity** (checkable): can the agent tell done from not-done?
- **Demand** (exhaustive): "every modified file accounted for" vs "produce a change list".

Remedy ordering: sharpen the bound first — cheap and local. Only split the skill to hide post-completion steps if sharpening fails AND you have actually observed the premature-completion rush.

## Context-pointer variance bug

A must-have target behind a weakly worded pointer is a **variance bug**: sometimes followed, sometimes not. Fix the pointer's wording first; inline the material only if sharpening fails. (Extends progressive disclosure: SKILL.md covers what to disclose; this diagnoses a disclosure that isn't reliably followed.)

## Leading words (Leitwort)

Reuse a concept already living in the model's pretraining to compress a restated quality into one anchor token:
- "fast, deterministic, low-overhead checks" → "tight checks"
- "review with maximum skepticism, assume it's broken" → "red-team the diff"

Front-load the leading word in descriptions. One trigger per branch — synonyms restating the same branch are duplication, not coverage.

## Sediment vs duplication vs sprawl

Three distinct bloat failure modes — diagnose before cutting:
- **Sediment**: stale accumulation — rules whose originating incident is long resolved.
- **Duplication**: the same meaning stated twice in different words.
- **Sprawl**: sheer length, regardless of cause.

Each needs a different fix: delete sediment, merge duplicates, restructure sprawl (progressive disclosure).
