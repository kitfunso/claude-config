---
name: which-skill
description: "Skill router: names every installed skill and when to reach for it, so you have one thing to remember instead of many."
disable-model-invocation: true
---

# Which Skill

Recommend the right skill, or a short chain of skills, for the task at hand.

## Method

1. **Read the live list first.** The available-skills list injected in context is the only authority. Do not recommend from memory. Never say a skill "does not exist" without checking that list: an unfamiliar name means "look it up", not "it's not there". If the user named a capability and the list truly lacks it, say "I checked the list; it is not there", not "it doesn't exist".
2. **Classify the task.** Pick its stage and domain: idea, plan, build, debug, verify, ship, QA, design, docs, content, safety, quant, meta.
3. **Match against the map.** Read [references/routing-map.md](references/routing-map.md) for the stage tables, mandated skills, and common chains. The map is a point-in-time snapshot; when it disagrees with the live list, the live list wins.
4. **Consider agents too.** If the work fits a sub-agent better than a skill, check `C:/Users/kit.sofun/.claude/rules/agent-routing.md`.
5. **Recommend.** One primary skill. Add a chain only when the task spans stages: one skill per stage, no padding.

## Ranking heuristics

When several skills match, pick in this order:

- **Mandated beats optional.** Some skills are house policy (the map marks them in bold). Recommend them as "required", not "consider".
- **Project rules beat the map.** If the working repo's CLAUDE.md defines its own workflow for a stage (deploy path, review gates, QA tools), route to that and say so. Example: a repo that deploys by push + pull on a VM gets its documented deploy steps, not a generic `/ship` PR flow.
- **Specific beats general.** For a bug, `investigate` beats `full-power`. For a futures roll issue, `roll-check` beats `quant-report`.
- **Stage fit beats keyword fit.** A "review" ask during planning wants `plan-eng-review`, not `code-review`.
- If two skills still compete, name both and give the tiebreaker in one line (e.g. `/qa` fixes what it finds; `/qa-only` only reports).

## Output format

Keep it short. Give the exact `/name` the user can type.

```
Use: /primary-skill: <one-line why>
Chain (only if multi-step):
1. /first: <what stage it covers>
2. /second: <what stage it covers>
Close miss: /other-skill: <why not, one line>
```

Include "Close miss" only when the user would plausibly pick that skill wrongly. If no skill fits, say so plainly, "No skill fits this. Do it directly.", and stop. Do not force a match; a wrong recommendation costs more than none.

## Examples

**"my streamlit page crashes when I pick a route, which skill?"**
```
Use: /investigate: root-cause debugging; no fix without cause.
Chain:
1. /investigate: find the cause
2. /test-driven-development: repro test first, then fix
3. /verification-before-completion: before claiming fixed
```

**"is there a skill for turning markdown into a pdf?"**
Check the live list → `make-pdf` is there.
```
Use: /make-pdf: converts a markdown file into a publication-quality PDF.
```

**"rename this variable across the repo"**
```
No skill fits this. Do it directly.
```
