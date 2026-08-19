# The steering bank — questions that caught what checklists missed

Two uses. **Self**: the model fires these at itself at the marked stages,
in writing, before any verdict. **Gate**: at every promotion gate the model
presents these to the user as invitations to attack — because the tier-3
catches (the ones no checklist held) came only from a human.

## §Self — fire at yourself, per stage

| Stage | Question | What it caught (war story) |
|---|---|---|
| 0 | "How many INDEPENDENT observations do I really have?" | Overlapping 7-week windows turned ~600 anchors into ~55 obs; SE(IC)=0.135 reframed every later 'discovery' as noise-sized |
| 0 | "Can the instrument mechanically carry the trade?" | The front tenor died ~2 weeks into a 7-week horizon; measured, the second month was the shortest holdable tenor |
| 0/3 | "What is the market already paying, for free?" | THE CARRY ILLUSION: v0 scored 57-65% hit predicting raw moves — a decomposition showed the forward curve priced the entire drift; the 'skill' was collectible by anyone holding the position |
| 1 | "Is any input stored-revised rather than vintaged?" | A predecessor project shipped balances revised 3 months into the past — its whole backtest was fiction; the successor stress-lagged its top driver (IC 0.44→0.42→0.35 at +4w/+8w) and started day-one vintage snapshots |
| 2 | "What did I declare and then not run?" | The NOT-DONE table exists because a declared check silently skipped reads as passed; one campaign's atlas ran a weaker check than declared and was caught only by a code-vs-declaration diff |
| 4 | "Is the hyperparameter grid itself sane?" | A grid reaching C=0.003 shrank small specs to the base rate — the 'tie' between specs was an artifact of over-regularization; trimming the grid changed the ranking |
| 4 | "Did the richer model BEAT or merely TIE the simple one?" | Optuna over boosting/nets/GPs never beat plain L2 logistic at this sample size; ties promote the simpler model |
| 5 | "What does my WHOLE process find in pure noise?" | THE SEARCH-WIDTH TRAP, measured twice: an 11,872-cell search found +0.099 real while ALL 20 noise replays of the same recipe found more (mean +0.23) — nothing was promoted, correctly |
| 5 | "What did selecting cost me?" | Choose-on-early / judge-on-late measured the selection haircut at +0.08–0.17 of apparent IC — the honest expectation is the held-out number, not the as-run one |
| 5 | "Is this dollar gain direction skill or a sizing artifact?" | One feature's money gain SURVIVED time-shifting the feature — linear sizing scales up in persistent-vol regimes even misaligned; it was reframed as a sizing input, flagged, not sold as direction skill |
| 5/6 | "What else is wrong with what you did?" | Asked cold, produced a 12-finding self-audit (overstated p-values, cross-campaign selection unadjusted, thin families lacking own nulls, backtest drift vs live data, ...) that no checklist had surfaced |
| 7 | "What price is the entry, really, and when does the mark freeze?" | An intraday pull carried a partial-day mark into the 'settle' panel (fixed with per-series cutoffs); the daily mark's freeze time had to be MEASURED with a probe, not assumed to be the local close |
| 7 | "Why is this row here?" | A promotion-day off-grid Wednesday call confused the record — it forced the schedule-grid guard and the labeled archive for prior-spec rows (append-only: explained, never deleted) |

## §Gate — present to the user at every promotion gate

Ask these verbatim, and wait:

1. **"Attack the decision rule, not just the numbers."** The rule that ranks
   candidates is a choice. (War story: 'nulls as vetoes' was overturned by
   the user — "the way you decide what is best is questionable" — and
   replaced with expected out-of-sample performance on two primaries, nulls
   demoted to open caution flags. The verdict flipped; the flag rides every
   report since.)
2. **"Tied on WHAT?"** Demand every metric with a paired interval. (War
   story: an 'all candidates tied' verdict was IC-only; under the money
   metric with costs, several candidates separated and the final spec beat
   the incumbent with an interval clearing zero.)
3. **"What market structure could explain or refute this?"** Explicitly
   collect domain events the model cannot know. (War story: a dismissed
   2022+ gain was re-weighed after the user supplied benchmark-inclusion
   and trade-reroute events that changed the feature's economic story.)
4. **"Is the capacity right for the data frequency?"** (War story: "9
   features is too many for our freq" preceded any statistic saying so;
   parsimony became the declared tie-break.)
5. **"What would make you say no?"** If nothing presented tonight could
   block promotion, the gate is theater — name the blocking conditions.
6. **"What is on the accrual list, and when is each re-test?"** Near-misses
   are scheduled, not forgotten — and not quietly promoted either.

## Standing behavioral rules (from the same record)

- When the user pushes back on any claim: VERIFY first (re-read, re-run,
  re-grep), never defend first. Concede to evidence immediately.
- Effect size and its noise yardstick live in the same sentence; "best",
  "dead weight", "top driver" are banned without the yardstick.
- Null, flat, or worse-than-baseline results are stated plainly, first,
  with no softening frame.
- The ledger is append-only and its rows are never edited; a confusing row
  gets an explanation and a label, never deletion.
- Two methods optimizing the same metric on the same rows are ONE witness,
  not two.
- If the same kind of fix appears a third time, stop patching and fix the
  producer.
