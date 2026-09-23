# The steering bank: questions that caught what checklists missed

Two uses. **Self**: fire these at yourself at the marked stage, in writing,
before the stage closes. **Write-up**: present the second set beside the
stage 10 page so the reader can attack the method, not only the numbers.
Every row was paid for by a real failure or a review catch; the campaign and
date are named. Stage numbers follow the 2026-09-22 ten-stage list.

## Self: fire at yourself, per stage

| Stage | Question | What it caught |
|---|---|---|
| 1 | "How many INDEPENDENT observations do I really have?" | bd-forecast 2026-08: overlapping 7-week windows turned about 600 anchors into about 55 observations; SE(IC) 0.135 reframed every later "discovery" as noise-sized |
| 1 | "What is the market already paying, for free?" | bd-forecast v0 scored 57-65% hit on raw moves; the forward curve priced the whole drift, so the "skill" was collectible by anyone holding the position |
| 1 | "Which years choose and which years judge, and is that written down?" | td3c 2026-09: nomination and judge years named on the plan page before stage 1 closed, so no later read could be a second look |
| 1 | "Which earlier reads already touched the judge years?" | td3c plan review 2026-09-22: the champion was quoted pooled 2022-2025 with 2025 a judge year; the page now lists every earlier read and the champion is restated on the nomination years |
| 1 | "Can this test say yes?" | critique 2026-09-22: enumerate-everything, a campaign-wide maximum and B = 20 stacked to a bar above any plausible incremental effect (td3c had 203,700 cells planned on about 100 honest independent observations); the power line and the screen-null-first rule came from it |
| 2 | "Did I search the whole table family, or one keyword?" | td3c 2026-09-22: a wide screen missed six daily VLCC tonnage lists because the search stopped at one table name; the family was found by prefix a stage later |
| 2 | "Is any input stored-revised rather than vintaged?" | bd-forecast's predecessor shipped balances revised three months into the past; the successor stress-lagged its top driver (IC 0.44 to 0.35 at +8 weeks) and started day-one snapshots |
| 2 | "Does the derived series reconcile with the published count?" | td3c 2026-09-22: the daily AG list vs the vendor's 1-10-day count table, best definition corr 0.37, exact match 4% of days; the count table became its own feature, never a splice |
| 4 | "Can 'every' be checked against a list?" | td3c 2026-09-22: "every available feature" only meant something once the universe was enumerated from the schema and listed on a page with table, base series and first date |
| 4 | "Is the count exact, or an estimate wearing a count's clothes?" | td3c plan review 2026-09-22: `approx_count_distinct` gave 1732 for a date column with 1477 distinct dates, and the same estimate decided which columns survived a cardinality cutoff |
| 4 | "Can the leak test fail for the right reason?" | td3c plan review 2026-09-22: a "+1-day shift lowers IC" test passes clean slow features and leaking fast ones alike; replaced by an availability-time assertion and a future-mutation test |
| 5 | "Is the cutoff a number I chose, or the null's?" | bd-forecast 2026-08: an 11,872-cell search found +0.099 real while all 20 shift replays of the same recipe found more (mean +0.23); nothing was promoted, correctly |
| 5 | "Does the null keep the champion?" | td3c plan review 2026-09-22: shifting every source series set the bar for "does anything predict" when the question was "does anything add after a champion at 0.44"; the null became the champion fit plus the shifted residual, and calendar columns got a bar for the first time |
| 5 | "Is this a second feature, or the champion again?" | td3c 2026-09: with a one-feature champion at rank IC 0.44, raw IC ranks the champion's copies first; incremental IC after the champion is the screening statistic |
| 5 | "Was the shortlist chosen with outcomes the walk-forward has not seen yet?" | td3c plan review 2026-09-22: one screen on all three nomination years, then a grid predicting the first two with it; screening moved inside the walk-forward at each annual refit |
| 5 | "Are twenty shifts twenty draws?" | critique 2026-09-22: offsets closer than a horizon are near-duplicate replays (td3c's B = 200 on about 750 daily anchors put them four apart at a 5-day horizon); the v1 effective-draws rule had been cut in the rewrite; the two-horizon spacing and the stated B came back from it |
| 6 | "Is the cap arithmetic on the window I am actually using?" | td3c 2026-09-22: rows / 8 gives about 25 clusters on an expanding fit and about 3 on a 26-week rolling fit for the same data; one cap for both was wrong |
| 6 | "Which count feeds the cap (n_cap) and which feeds power (n_rank or n_anchor), each named?" | critique 2026-09-22: "usable training rows / 8" beside "independent observations = anchors / overlap" was a fourfold gap at a 4-week horizon; the cap moved to effective rows |
| 7 | "Did I import a sibling project's answer as a prior?" | td3c 2026-09-22: "expanding window, annual refit" was written as the primary because bd found it; the user caught it; it became one cell of a 132-cell grid |
| 7 | "Is the hyperparameter grid itself sane?" | bd-forecast 2026-08: a grid reaching C = 0.003 shrank small specs to the base rate; the "tie" between specs was over-regularisation |
| 7 | "Did the richer model BEAT or merely TIE the simple one?" | bd-forecast 2026-08: Optuna over boosting, nets and GPs never beat plain L2 logistic at this sample size; ties promote the simpler model |
| 7 | "How many cells does the tie rule send to the judge?" | td3c plan review 2026-09-22: "every tied cell goes to the judge read" on a 132-cell grid was a second selection on the judge years; now one cell per family by a written tie-break, the tie set reported as a range |
| 7 | "What is the tie rule, and was it written before the run?" | td3c 2026-09: cells inside one paired interval are a flat surface; without the rule, a flat surface gets read as a winner |
| 8 | "Which of the judge reads is the result?" | critique 2026-09-22: one cell per family was still four looks at the judge years with none named binding; the standing family is fixed at stage 7 and its read is the result |
| 8 | "What did selecting cost me?" | bd-forecast 2026-08: choose-on-early, judge-on-late put the selection haircut at +0.08 to +0.17 of apparent IC; the honest expectation is the judge number |
| 9 | "Is this direction skill, or a volatility artefact?" | bd-forecast 2026-08: one feature's gain survived time-shifting the feature; linear sizing scales up in persistent-vol regimes even when misaligned |
| 10 | "What else is wrong with what you did?" | bd-forecast 2026-08: asked cold, produced a 12-finding self-audit (overstated p-values, cross-campaign selection unadjusted, thin families without their own nulls) that no checklist had surfaced |
| 10 | "What price is the entry, really, and when does the mark freeze?" | bd-forecast 2026-08: an intraday pull carried a partial-day mark into the settle panel; the freeze time had to be measured with a probe |
| 10 | "Why is this row here?" | bd-forecast 2026-08: an off-grid promotion-day call confused the ledger; rows are explained and labelled, never deleted |
| 10 | "What is the ledger's read rule, and was it written before the first row?" | critique 2026-09-22: "the only judge of the model" had no statistic, no minimum count and no schedule; the v1 anytime-valid rule had been cut in the rewrite; the read rule came back from it |
| 9 | "Did a judge diagnostic just edit the spec?" | outside review 2026-09-22: stage 9's knockouts and separating-feature list invited "remove X before the ledger starts", which would have made the judge years a second development set |
| 5 | "Does the null keep the clock?" | outside review 2026-09-22 (third): a whole-block circular shift puts crisis residuals into calm years; the scale check and the standardise-and-rescale option came from it |
| 10 | "Is the ledger minimum in the metric's own units?" | outside review 2026-09-22 (second and third): (2 / IC)^2 was applied to a Brier reduction; the standardised effect over the long-run s.d. came from it |

## Write-up: present beside the stage 10 page

1. **"What was covered, and what was not?"** The enumerated lists: tables
   profiled and not, cells screened, grid cells run and not fittable, rungs
   skipped with the reason. (prc26 2026-09-05: the user had to ask "what have
   you tried, what features, Optuna?" cold; the answers existed across four
   files and no page had them side by side.)
2. **"Tied on WHAT?"** Every comparison with its paired interval. (bd 2026-08:
   an "all tied" verdict was IC-only; a second metric separated the
   candidates.)
3. **"What market structure could explain or refute this?"** Domain events
   the model cannot know. (bd 2026-08: a dismissed 2022+ gain was re-weighed
   after the user supplied benchmark-inclusion and reroute events.)
4. **"Is the capacity right for the data frequency?"** (bd 2026-08: "9
   features is too many for our freq" preceded any statistic saying so.)
5. **"What would make you say no?"** If nothing on the page could block the
   conclusion, the page is theatre; name the blocking conditions.
6. **"What would have made you say yes?"** The search bar: the smallest
   effect worth having beside the null cutoff, with the signal-injection
   power when it ran. If the effect did not clear the bar by the power
   margin, or the injection power fell short of the declared power, the
   page says the search was underpowered for the minimum effect we care
   about, whatever the data held. (critique 2026-09-22.)
7. **"What is on the re-test list, and when is each due?"** Late-start and
   thin columns are scheduled, not forgotten, and not quietly promoted.
