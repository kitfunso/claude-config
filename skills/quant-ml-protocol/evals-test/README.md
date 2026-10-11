# quant-ml-protocol: held-out test split

This folder is the test split. The session that edits `SKILL.md` never opens it. That session sees pass counts
and criterion numbers only, so a skill change cannot be fitted to these cases. Train cases live in `evals/`.

- A fresh agent writes every case here, never the editing session. Cases come from production material:
  campaign ledgers, result docs, incident write-ups and memory files. Line 1 of each `case.yaml` names its source.
- A case is picked because an expert judges the moment hard, never because today's model fails it.
- The mix: notice cases, where the flaw sits in the situation and nobody names it; at least one allow case, where
  over-refusing fails; exactly one should-not-fire case, tagged `should-not-fire`.
- Criteria are 3 to 6 numbered pass/fail claims that judge the decision, never the skill's wording.
- Never copy a case's content or phrasing into `SKILL.md` or into `evals/`. To add a case, brief a fresh agent
  with the production sources and this file.

Method and run command: `~/.claude/scripts/skill-evals/README.md`.

Cases (written 2026-10-11, against the v2 skill of the same date):

| case | type |
|---|---|
| `btlab-one-book-signoff` | notice |
| `natgas-r8-breakthrough` | notice |
| `prc26-more-keys` | notice |
| `prc26-adsb-stage` | allow |
| `btlab-worker-tripwire` | should-not-fire |
