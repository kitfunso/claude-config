# Skill evals: build, run, climb

The method from Anthropic's [Automating eval design and hillclimbing](https://claude.dev/blog/automating-eval-design-and-hillclimbing/),
applied to skills that sub-agents run in a clean copy. First used on quant-ml-protocol, 2026-09-29.

## Cases

- Each skill has two splits. `evals/` is train: the session that edits the skill reads these cases and fixes
  against them. `evals-test/` is held out: a fresh agent writes it from production material, and the editing
  session never opens it. It sees pass counts and criterion numbers only.
- Where cases come from, in order: real transcripts and campaign artefacts; incidents the user raised; cases
  written by hand; synthetic cases anchored to a real one. Pick a case because an expert judges it hard, never
  because today's model fails it: that builds a failure fingerprint, not a measure.
- Case mix: notice cases, where the flaw sits in the situation and nobody names it; refuse cases; allow cases,
  where the protocol permits the ask, so over-refusing fails; and at least one should-not-fire case, labelled.
- Criteria: 3 to 6 numbered claims, each pass or fail, never a scale. Two experts would reach the same verdict.
  Judge the decision, never whether the reply uses the skill's words.

## Run

    python ~/.claude/scripts/skill-evals/build_run.py SKILL ROOT --without-split test [--without NAME ...]

Then call Workflow with `scriptPath` set to `~/.claude/scripts/skill-evals/run-evals.js` and `args` set to the
contents of `ROOT/args.json`. Each reply gets a blind Opus grader, and the test split gets a second one. Save
the returned JSON beside the run folder; it is the baseline the next round compares with.

## Read these before changing the skill

- Noise: `noise_2se` per split. A change smaller than that is noise.
- Headroom: a split above 95% cannot show a gain, so add harder cases before climbing on it.
- Variance: a noisy case (mixed runs) is read across all its runs. An always-fail case is checked for a case or
  grader bug before anyone edits the skill.
- Discrimination: a case the model passes without the skill measures the model, not the skill.
- Grader agreement on the regraded split. A disagreement points at an ambiguous criterion; rewrite it.
- Config: model and effort are set on every agent, and each run writes only to its own project folder.

## Climb

1. Make one change per round, aimed at the root cause of a train failure and written as a general rule.
   Never paste a failing case's content or phrasing into the skill.
2. Rerun both splits.
3. If train rises while test stays flat or falls, revert the change: it fitted the train cases.
4. Stop when two or three rounds change nothing. Then sort the remaining failures by root cause and look for
   eval bugs before any further skill edit.
5. Report the best test-split score with its 2 SE, beside train.

## Known limits

- Opus runs and Opus grades. CLAUDE.md puts every judgement on Opus and bans Haiku, so instead of the blog's
  separate judge model we use blind grading, a second independent grader on the test split, and a sample the
  user reviews.
- Sub-agents load the user's CLAUDE.md and memory index, so both arms know the project history (an r6 baseline
  reply cited a real campaign). The without-skill arm measures the model plus that context, not a bare model.
- The skill-fired check counts a read of SKILL.md made only to decide whether the skill applies. A
  should-not-fire case can therefore show 0/3 on trigger while its answer passes.
