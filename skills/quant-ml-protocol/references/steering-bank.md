# The steering bank: questions that caught what checklists missed

Two uses. **Self**: fire these at yourself, in writing, before the marked stage
closes. **Write-up**: present the second set beside the closing report so the reader
can attack the method, not only the numbers. Every row was paid for by a real
failure or a review catch, named with its campaign and date. Stage labels follow
SKILL.md: B is the build (data audit, evaluator, ledger), then stages 0 to 5. The
questions about null replays live in `audit.md`.

## Self: fire at yourself, per stage

| Stage | Question | What it caught |
|---|---|---|
| B | "How many INDEPENDENT observations do I really have?" | bd-forecast 2026-08: overlapping 7-week windows turned about 600 anchors into about 55 observations; SE(IC) 0.135 reframed every later "discovery" as noise-sized |
| B | "Which windows score, which window is the final read, and is that written down?" | td3c 2026-09: the windows named on the page before any run, so no later read could be a second look |
| B | "Which earlier reads already touched the final-read window?" | td3c plan review 2026-09-22: the champion was quoted pooled 2022-2025 with 2025 held back; the page now lists every earlier read |
| B | "Does the evaluator rank the external scores the way the board does?" | prc26 v1 2026-09: holdout and board disagreed on which model was better (`docs/CEIL.md`), and v19 beat v20 on holdout but lost on the board |
| B | "Did I search the whole table family, or one keyword?" | td3c 2026-09-22: a search stopped at one table name and missed six daily VLCC tonnage lists |
| B | "Is any input stored-revised rather than vintaged?" | bd-forecast's predecessor shipped balances revised three months into the past; the successor stress-lagged its top driver (IC 0.44 to 0.35 at +8 weeks) |
| B | "Does the derived series reconcile with the published count?" | td3c 2026-09-22: a derived daily list matched the vendor's count table on 4% of days; the count table became its own feature, never a splice |
| B | "Is the count exact, or an estimate wearing a count's clothes?" | td3c plan review 2026-09-22: `approx_count_distinct` gave 1732 for a column with 1477 distinct dates |
| B | "Can the leak test fail for the right reason?" | td3c plan review 2026-09-22: a "+1-day shift lowers IC" test passed clean slow features and leaking fast ones alike; replaced by an availability-time assertion and a future-mutation test |
| B | "Is feature selection inside the fold?" | td3c plan review 2026-09-22: one screen on all scoring years, then models predicting those years with it |
| 0 | "What do the public repos and forums already know?" | prc26 2026-10-10: ADS-B pushback times, read out of a competitor's public repo, gave +14.81 s in one step, more than any model change |
| 0 | "What is the market already paying, for free?" | bd-forecast v0 scored 57-65% hit on raw moves; the forward curve priced the whole drift (-0.028 a week against carry roll-down -0.066) |
| 0 | "Where does the loss sit, and what would a perfect version of this idea recover?" | prc26 2026-09-13: 1.6% of rows carried 52.7% of squared error; window-state features later recovered 4.42 of a 7.98 s oracle ceiling |
| 0 | "Is every primary driver in the data, and if not, have I gone and got it?" | natgas 2026-09-28: storage and weather, the drivers the literature ranks first, were left out as "a new pipeline"; the campaign closed null |
| 0 | "Was this campaign built for this market, or copied from a sibling?" | natgas 2026-09-28: its feature set was "HO's by name and WTI's by family", so four markets tested one hypothesis |
| 0 | "Did I import a sibling project's answer as a prior?" | td3c 2026-09-22: "expanding window, annual refit" was written as the answer because bd found it; it became one option among many |
| 1 | "Did the models see the information, or only the champion's value?" | natgas 2026-09-28: 108 model runs, every one fitted to the champion's value alone; they tested model shape, never the information |
| 2 | "Did a tuning study run and finish?" | prc26 2026-09-08: three studies declared, zero finished, because budgets were set in hours before a trial was priced; natgas 2026-09-28 ran zero trials |
| 2 | "Is the hyperparameter grid itself sane?" | bd-forecast 2026-08: a grid reaching C = 0.003 shrank small models to the base rate; the "tie" was over-regularisation |
| 3 | "Is a floor refusing a real gain?" | prc26 2026-09-08: a challenger at +1.7 s, 95% CI [+1.1, +2.3], was refused by a hand-set 2 s floor |
| 3 | "Is this the fourth variant of a stagnant construct?" | alphanova cycle 2 2026-09-02: 30 of 32 uploads were parameter variants of one ridge, every one inside the noise bar |
| 3 | "Did a weak result lead to more information, or to a narrower search?" | natgas 2026-09-28: low power cut the feature set to 3 and left the pre-2015 history unpulled |
| 3 | "Did this round change one thing, and is it in the ledger?" | bd-forecast 2026-08: numbered iterations, one change each against the champion, reached a champion that held its sign leaving out any year |
| 3 | "Is this a second feature, or the champion again?" | td3c 2026-09: with a champion at rank IC 0.44, raw IC ranked the champion's copies first; gains are measured over the champion |
| 3 | "Did the richer model beat the simpler one, or tie it?" | bd-forecast 2026-08: Optuna over boosting, nets and GPs never beat plain L2 logistic at this sample size |
| 3 | "What has not been tried, and why?" | 2026-09-29: four campaigns closed valid and null with no one asked about breadth |
| 3 | "Is this direction skill, or a volatility artefact?" | bd-forecast 2026-08: one feature's gain survived time-shifting the feature; linear sizing scales up in persistent-vol regimes |
| 5 | "Which read of the final window is the result?" | critique 2026-09-22: four models read on the final window with none named binding; one frozen spec reads it, the rest are context |
| 5 | "What did selecting cost me?" | bd-forecast 2026-08: the haircut was +0.08 to +0.17 of apparent IC; the honest expectation is the final-read number |
| 5 | "Did a final-read diagnostic just edit the spec?" | outside review 2026-09-22: knockouts on the final window invited "remove X before the ledger starts", which would make it a second development set |
| 5 | "What else is wrong with what you did?" | bd-forecast 2026-08: asked cold, produced a 12-finding self-audit that no checklist had surfaced |
| 5 | "What price is the entry, really, and when does the mark freeze?" | bd-forecast 2026-08: an intraday pull carried a partial-day mark into the settle panel |
| 5 | "What is the ledger's read rule, and was it written before the first row?" | critique 2026-09-22: "the only judge of the model" had no statistic, no minimum count and no schedule |
| 5 | "Is the ledger minimum in the metric's own units?" | outside review 2026-09-22: (2 / IC)^2 was applied to a Brier reduction |
| 5 | "Why is this row here?" | bd-forecast 2026-08: an off-grid call confused the ledger; rows are explained and labelled, never deleted |

## Write-up: present beside the closing report

1. **"What was tried, and what was not?"** The ledger, the stage list with done,
   partial or skipped, and the idea pool with what is still untried. (prc26
   2026-09-05: the user had to ask "what have you tried, what features, Optuna?"
   cold; the answers existed across four files.)
2. **"Tied on WHAT?"** Every comparison with its paired interval. (bd 2026-08: an
   "all tied" verdict was IC-only; a second metric separated the candidates.)
3. **"What market structure could explain or refute this?"** Domain events the
   model cannot know. (bd 2026-08: a dismissed 2022+ gain was re-weighed after the
   user supplied benchmark-inclusion and reroute events.)
4. **"Is the capacity right for the data frequency?"** (bd 2026-08: "9 features is
   too many for our freq" preceded any statistic saying so.)
5. **"What would make you say no?"** If nothing on the page could block the
   conclusion, the page is theatre; name the blocking conditions.
6. **"What would have made you say yes?"** The smallest effect worth having beside
   the interval the evaluator can resolve. When the interval is wider than that
   effect, the page says the campaign could not have seen it.
7. **"What is on the re-test list, and when is each due?"** Late-start and thin
   features are scheduled, not forgotten, and not quietly promoted.
8. **"What is missing that we should try?"** At least one untried input (new data),
   one untried mechanism, one untried model family and one untried target
   treatment, each with a cost estimate.
