# Cycle 1 evidence record

Every measurement behind `SKILL.md`, with the numbers and the source. Read this
when you need the detail; `SKILL.md` carries the decisions. Primary source is
`C:/Users/skf_s/alphanova/research/SCOREBOARD.md` (39 rounds, append-only).

Cycle 1: opened 15 Aug 2026, closed ~1 Sep 2026. 34 uploads, 20 counted slots
(rejections refund), 20 admitted, 14 rejected. Best `otv_k25` +0.0003 at rank 19.

---

## 1. The data

**Target.** Undisclosed, but solved to a working model in phase 1
(`research/01_target_map.py`, `research/FINDINGS.md`): it is approximately the
cross-sectionally z-scored **120-hour forward sum** of the proprietary returns,
clipped at ±5. The horizon scan peaks exactly at h=120 in every frame tested
(IC 0.938 in period 031, 0.966 in period 015). You are forecasting 5-day relative
performance, re-estimated hourly.

Consequences that bite:
- Embargo the last 120 rows of any training window. The label overlaps them.
- Anything faster than ~24h is mostly noise against this label.
- The ±5 clip destroys tail information, so an MSE fit chases a censored target.
  (Fixing that with rank labels was tried and lost: see §4.)

**Features.** Six anonymised panels, 20 assets, hourly.

| Feature | Character | Linear IC |
|---|---|---|
| F1-F4 | ONE factor: pairwise corr 0.96-0.985, hourly autocorr ~0.97, xs-std ~0.037 | ~0.000 |
| F5 | Fast (autocorr 0.13), large scale (4.4) | +0.001 |
| F6 | Very slow (lag-24 autocorr 0.61), tiny scale (2e-4) | -0.007 |

All linear ICs are ~0, exactly as `COMPETITION.md` advertises. F6's -0.007 is
mostly static tilt (-0.003 de-tilted) and its sign flipped in the two most recent
year-chunks. The factor (F1-F4) is the crowded, mean-reverting dimension and was
the poisoned input in every ablation.

**Panel mechanics.**
- The `returns` panel is AlphaNova-proprietary, not price returns. Do not try to
  replicate it from outside data.
- Ticker identities are NOT stable across periods. Cross-sectional structure only;
  never learn per-ticker habits.
- Period files are cumulative. Never concatenate them (duplicates early history).
- Leading exact-0.0 rows are warm-up, not a bug. The first 3,462 rows of a panel
  are exact zeros, far longer than 120h, so the returns construction itself has a
  long warm-up. Drop them in `train()`.

**Rotation.** Each period file is independently rotated in asset space. Inner
products survive rotation (so the scoring is invariant) but **ranks and absolute
values do not**. Any single-frame IC is partly frame luck: the same construct
measured +0.0115 in frame 031, -0.000 in frame 015 and +0.0075 in frame 022.
Single-frame probes are idea generators only. `runner.py --full` walks forward
across periods and kills frame luck automatically.

**The static-tilt trap (phase 1, and it recurs everywhere).** A fully causal
expanding mean of the target's own past rows scores IC **+0.074**, the largest
number in the data. It is a trap: a static long/short tilt survives label
shuffling, because permuting rows does not change per-column means. So the gate's
null contains the tilt's full performance and the signal fails. Every signal must
be causally de-tilted. The k>1 discovery (§3) is the *inversion* of this trap, not
an exception to it.

---

## 2. Scoring and the field

**Net Sharpe** with a 5 bp turnover charge:
`r(i) = <P(i-1), X(i)> − 0.0005·Σ|P(i-1) − P(i-2)|`.

**Metric definitions** (`comp6_scientist_release/city_tools.py`,
`walkforward.py:240`):
- `concentration` = ‖mean of the gauge-fixed unit vectors‖ = directional
  stability of the signal over time. Measured in the rotating target frame.
- `compression_loss` = `IC·(1 − 1/concentration)` **exactly** (verified: f0d
  -0.0151·(1−1/0.0572) = +0.2487 vs server 0.2487). It carries no independent
  information; it is the IC sign wearing a costume. Round 11's "compression
  mechanism" was an artifact of not knowing this.

**The field regression** (`research/33_leaderboard_study.py`, n=64 scored
signals, competitive core n=58, in-sample R² 0.502, **leave-one-out R² 0.237**):

```
Sharpe ≈ 0.58·IC + 0.024·concentration − 0.013·IC_std − 0.011
```

- `concentration` correlates **+0.477** with official Sharpe, the strongest
  single correlate on the board. Positive-Sharpe signals average 0.201, negative
  average 0.145, the two leaders sit at 0.337 and 0.397.
- City novelty r = -0.262, global novelty r = -0.216, both ~0 coefficients.
  **Novelty does not drive score.** It is a separate eligibility gate.
- The control that proves IC alone is not enough: #47 radiant-allomancer has
  IC +0.0210 (3rd best on the board) and scores -0.0114, because concentration is
  only 0.120. TaroKogawa #4 is the same story (IC 0.0256, conc 0.122, +0.0041).
- **It does not rank within a family.** It puts `otv_k3` (-0.0036) above
  `otv_k25` (-0.0039); the server returned -0.0050 and +0.0003. Fitted across
  heterogeneous constructs, applied within one, it fails.

**Board shape.** ~102 entrants, 83+ scored signals by cycle close. The field is
one crowded trade: median nearest-neighbour angle 28.3°, p90 57.2°, the leaders'
neighbours 2-8° away. **Only ONE signal on the entire board was prize-eligible**,
because everyone else correlates >0.5 with something ranked above them.

**Prize mechanics** (`COMPETITION.md`). Pot = `100 + 2400·q^0.75` where
`q = min(Q/13, 1)`, capped at $2,500/cycle, where Q is the number of quality
signals. Top 3 split 60/25/15; unpaid shares roll into the next cycle's pot.
Quality set = greedy: **statistically significant positive Sharpe**, ranked by
Sharpe, each joining only if `|corr| ≤ 0.5` against every signal already
occupying space (higher-ranked entries, the season legacy pot, and the fund's
background signals).

---

## 3. The k-curve: the campaign's one real result

All at span 96 on f1's model and features unless noted. Server numbers.

| file | k | spans | capacity | Sharpe | IC | IC_std | conc | city nov |
|---|---|---|---|---|---|---|---|---|
| **otv_k25** | 25 | 96 | f1 | **+0.0003** | +0.0034 | 0.1823 | 0.3110 | 6.61 |
| otv_k15 | 15 | 96 | f1 | -0.0003 | +0.0038 | 0.1852 | 0.3078 | 2.41 |
| otv_minimal | 7 | 96 | minimal | -0.0012 | **+0.0065** | 0.1953 | 0.2963 | 4.12 |
| ml_overtilt | 7 | 96 | f1 | -0.0019 | +0.0049 | 0.1941 | 0.2960 | 55.57 |
| otv_s2k7 | 7 | 240/480 | f1 | -0.0023 | +0.0026 | 0.1923 | 0.2992 | 6.34 |
| ml_apex | 25 | 240/480 | f1 | -0.0031 | -0.0039 | 0.1794 | 0.3157 | 11.74 |
| otv_k3 | 3 | 96 | f1 | -0.0050 | +0.0067 | 0.2102 | 0.2620 | 22.74 |

**Mechanism.** The persistent cross-sectional component is anti-predictive (a
market effect: persistent positions mean-revert). So `sig − k·tilt` with k>1
leaves (k−1) units of the **negated** tilt, a component that is predictive
*because* the tilt is anti-predictive, and persistent *because* a tilt is what
persistence means. It is the only construction found in cycle 1 that raised IC
and directional stability together.

**Readings:**
1. Sharpe is monotone in k: -0.0050, -0.0019, -0.0003, +0.0003. Gaps shrink
   (+0.0031, +0.0016, +0.0006), so the curve converges near +0.0005. Little
   headroom left on k alone.
2. **IC falls as k rises** (+0.0067 → +0.0034) while Sharpe rises. Stability is
   doing the work: conc 0.2620 → 0.3110, IC_std 0.2102 → 0.1823. k trades IC for
   stability and the trade pays.
3. **The slow-span blend, not k, killed `ml_apex`.** At k=7 the 240/480 blend
   costs 0.0004; at k=25 it costs 0.0034. It gets worse as k rises.
4. **Capacity down works.** `otv_minimal` (depth 2, 3 leaves, min_data_in_leaf
   4000, lambda_l2 40, 25 rounds) posts IC +0.0065 vs +0.0049 at the identical
   output stage, and beat `ml_overtilt` on Sharpe.
5. **Never combined: minimal capacity at k=25.** One line.

**Retraction on record:** round 36 concluded "k=25 broke the sign". It did not.
That inference came from comparing two constructs that differed in two variables.

---

## 4. Everything that was measured and failed

Grouped by lane. Every number is runner- or server-measured unless flagged.

**Model class — exhausted.** LightGBM, XGBoost, HistGradientBoosting, ExtraTrees,
RandomForest, MLP, KNN, ElasticNet, Ridge, CatBoost, a cross-sectional context
MLP, and LightGBM `lambdarank`. Six of the eight Optuna-tuned zoo families were
admitted with positive server IC (+0.0004 to +0.0047) and all scored negative on
turnover. Model class is not the constraint; information content is.

**Optuna — actively harmful, and worth understanding.** 8 families × 25 trials,
objective = honest train→forward IC on the selection window. Tuned selection ICs
came back +0.073 to +0.100 for every family, *including KNN and ElasticNet
matching gradient boosting*, which is not credible. With ~120h autocorrelation a
period's mean IC has se ≈ 0.035, so the expected maximum of 25 noise draws is
≈ +0.07. Every value sat in that band. On the confirm window: **mean selection IC
+0.0876 → mean confirm IC -0.0206, zero of eight positive**, and
`corr(selection, confirm) across families = -0.582` — the tuning ranked families
*inversely* to how they generalised. Optuna also pushed every family toward more
capacity, which server data later showed is the wrong direction. **If you tune,
tune capacity downward and validate on a window the tuner never saw.**

**Label engineering.** `ml_ranksmooth` vs `f1_interactions`: identical features,
model, hyperparameters and output span, only the label differs. Runner IC
+0.0058 → **-0.0092**. A rank-smoothed label hurt. (This had looked like a 58x
win on the retired custom harness — see §5.)

**Learning-to-rank.** LightGBM `lambdarank`, one group per hour: IC **-0.0140**,
Sharpe -0.0234. NDCG is top-weighted; IC weights the whole cross-section
uniformly. Optimising NDCG optimises the wrong part of the ordering. Design-time
error, not an implementation bug.

**Ensembling across families.** 5-family rank-average: IC +0.0051 at concentration
**0.0843**, below its own components' 0.21. Averaging different biases destroyed
directional stability rather than buying it.

**Multi-timescale output blending.** At unit de-tilt: REJECTED by the gate. At
k=25: admitted but scored worse than the single span (§3).

**Turnover and cost engineering — the whole lane.** Step-hold, banding,
tranching, band-pass, longer holds. `MFB240` halved the turnover of an admitted
signal and scored **worse** (-0.0073 → -0.0103, IC -0.0131 → -0.0237). The fitted
drag model (`gross = 0.388·IC − drag`, drag120 ≈ 0.0022) predicted -0.0036 ±
0.0015 and pre-registered a cluster landing as falsification. It landed below the
cluster. **Costs were never the binding constraint**; at step 240 the bill is only
~0.0011, so a zero-alpha signal would have scored better than our best.

**Feature engineering as a decorrelation route.** `alt_feat` shares *no* inputs
with `ml_apex` (extremeness dropped, factor + F5/F6 instead) and still correlates
**0.954** with it. At high k the output collapses to the negated persistent
structure, and every model's persistent structure converges to the same object
because it is driven by the features' persistence, not by the model. **All
over-de-tilted signals are one signal wearing different hats.** Only a different
*mechanism* decorrelates.

**Three never-touched axes, diagnosed before building
(`research/37_untried_axes.py`):**
- Hour-of-day / day-of-week: IC spread across hour buckets 0.0064 vs per-bucket
  se 0.0027, under the pre-set 3× bar. **Dead.**
- Confidence-based book sizing: IC autocorrelation +0.899 at lag 1 but **-0.002
  at lag 120**, and 120h is the rebalance horizon. The lag-1 figure is mechanical
  (EWM smoothing makes consecutive predictions near-identical), not skill
  persistence. `corr(target dispersion, |IC|) = -0.016`, so dispersion is not a
  confidence proxy either. **Dead.**
- Recency weighting: **LIVE.** A fixed signal's IC decays monotonically through
  every panel (period 020: +0.0140, +0.0137, -0.0118, -0.0139 by quarter; same
  shape in 3 of 4 panels) and the block that gets scored is the tail. Built as
  `otv_recency.py` and never verdicted.

**Also dead:** side-asymmetry, dispersion-tercile conditioning, factor momentum,
F5 flow, spread levels (6 pairs, both signs), interaction levels, tranching,
lookbacks ≥ 720 (structurally impossible against 800-row predict blocks).

---

## 5. Instruments that lied, and how they lied

**The custom evaluation harness (retired).** Built as an alternative to
`runner.py`; it disagreed twice. First a 6× underestimate on `f1_exact` (all_IC
+0.0010 vs the runner's +0.0058, same sign, cause = a 150k-row subsample where
the real `train()` uses every row). Then a **sign flip** on the label experiment
(+0.0117 vs runner -0.0092), which produced a "58× label-engineering win" that had
to be retracted. Every number it produced is non-evidence, including its
"0/8 zoo families confirm-negative" verdict and its capacity-vs-null table.
**Never build a second harness when the contest ships one.**

**The shuffle rehearsal** (`research/04_shuffle_gate.py`) — retrain on permuted
labels, compare the real in-sample score against the null. It is *not* a server
predictor and failed in both directions:
- `zoo_xgb` had our 2nd-best margin (+0.076) and was REJECTED.
- `zoo_hgb` had the worst (+0.019) and was ADMITTED.
- It FAILED `ml_overtilt`, which the server then admitted at our best rank.
Keep it as a crash screen only. It did correctly kill the round-7 context MLP
(real +0.0662 vs permuted max +0.0829), so it catches gross errors. Never a
blocking or ranking device.

**The gate/cost trap map** (round 21, 7 configs). The rehearsal claimed exactly
one output configuration clears the gate — fast and unsmoothed — and concluded
"the admissible region and the profitable region are disjoint at our edge
magnitude". **The server contradicted this**: it admitted `ml_overtilt`, the most
persistence-leaning signal we ever built, which the rehearsal had failed. Treat
the whole map as rehearsal output, i.e. as non-evidence.

**Raw-position stability as a concentration proxy.** Pre-registered a bar of
concentration ≥ 0.10 on a raw-position proxy reading 0.114; the real gauge-fixed
value came back 0.0709. Recorded as a failed prediction. Concentration is measured
in the rotating target frame; a raw-position proxy does not track it.

**Runner novelty vs server novelty.** The runner computes novelty against the
shipped city database, which the organiser said in Discussions to ignore ("there
are no legacy signals in Cycle 1"). Runner 66.5° vs server 55.57° on the same
signal: direction and rough magnitude hold, the scale does not. Do not quote a
runner novelty number as a server-equivalent.

**Runner concentration.** Construct-dependent. `f1`: runner 0.0758 vs server
0.2265 (3× apart). `ml_overtilt`: runner 0.3153 vs server 0.2960 (close). There
is no fixed conversion.

**Validation score vs test score on the dashboard.** They disagree hard and the
test score is what ranks you. `mid_fac_blend` posted validation +0.0373 and test
-0.0073; `mfb_slow` +0.0264 and -0.0103. A high validation score is not good news.

---

## 6. The six dead gate theories

Each fitted the verdicts available at the time, then died. Listed so nobody
rebuilds them.

| # | Theory | Killed by |
|---|---|---|
| 1 | Temporal ops in features fail; output-side ops pass | LTRIO used the same pipeline as admitted f0d and was rejected |
| 2 | Slow signals fail, fast ones pass | FBP was fast and strong, rejected |
| 3 | Correlation with fund city signals causes rejection | Organiser: "ignore the city data... there are no legacy signals in Cycle 1" |
| 4 | Local compression loss separates verdicts | FSM had *better* compression than the admitted MFB and was rejected |
| 5 | A walk-forward strength ceiling in (+0.0096, +0.0120) | XT5 rejected at +0.0075, below the admitted MFB's +0.0096 |
| 6 | Full-history in-sample Sharpe separates verdicts | It interleaves verdicts completely |

**What actually solved it** was a designed experiment, not a curve fit:
`MFB240` (admitted, scored -0.0103) and `mfb_inverse` are byte-identical except
one sign. One admitted, one rejected ⇒ the gate is sign-sensitive ⇒ it reads
performance, not construction. Combined with `COMPETITION.md`'s description, that
gives the degenerate-null mechanism for model-free rules. Confirmed independently
by `f0d_inverse`, rejected exactly as pre-registered.

Supporting counts: 6 admitted model-free signals carried server IC -0.0053,
-0.0124, -0.0131, -0.0151, -0.0164, -0.0237 — **all negative, admitted for
anti-predicting**. Ten rejected signals were our strongest. `f1_interactions`,
the only trained model submitted at that point, was the only admitted signal with
positive server IC.

---

## 7. Statistical discipline that held up

These were adopted mid-campaign and none of them was later falsified.

- **The noise bar.** Block bootstrap (120-row blocks, 2000 resamples) of the
  confirm-window net Sharpe gives std = **0.0127**. Any confirm-window
  improvement under ~0.013 is luck. This retroactively justified every
  plateau-over-argmax decision.
- **Plateau, not argmax.** Pick a config whose grid neighbours are also good.
  Applied to span/step (killed a lone spike at span96/step300 whose neighbours
  were half its value) and to k (k=7 chosen with k=5 and k=10 both within 0.0005).
- **The two-window protocol.** Selection = periods 001-024, confirm = 025-031.
  One look per decision at the confirm window, spent deliberately. By round 7 the
  confirm window had had 12+ looks and was partially burned; after that only
  server history was clean.
- **Multiplicity honesty.** The ledger carries a "Tried" count per family, so a
  best-of-13 number is never presented as a single measurement.
- **Pre-registration.** Write the bars, the candidate, and what each verdict will
  prove *before* running. Rounds 7, 9, 10, 11, 12, 16, 17 and 18 were all
  pre-registered, and it is what made the failed predictions legible instead of
  rationalisable.
- **Overlap-adjusted significance.** The 120h-overlapping target means naive
  t-stats must be divided by ~sqrt(120). With 120-240h holds the effective sample
  is ~100-200 observations, so a mean IC of -0.013 is only t ≈ -0.87. Six
  correlated signals are ~one independent observation, not six.

---

## 8. Operations

- Dashboard: `https://www.alphanova.tech/competition/biweekly/season-1/cycle-N`,
  tabs `?tab=submissions` and `?tab=leaderboard`. Account `cookedjay`.
- Uploads are manual through the browser file picker. Verify the counter moved
  after each upload; matching the picker's filename label is not proof the upload
  landed (this produced a false "submitted" claim in cycle 1).
- Verdict classes seen: `OK`, `Overfitted submission`, `Failed to run`,
  `Processing`. `Processing` is the path admitted signals take; rejections flip
  straight to `Overfitted submission`.
- Rejections refund the slot and never enter the legacy pot. Admitted signals
  claim their neighbourhood permanently for the season.
- Local env: `.venv` in the repo root,
  `pip install -r comp6_scientist_release/requirements.txt`. Run the runner from
  inside `comp6_scientist_release/`. Data (1.8 GB) is gitignored; re-extract from
  `Downloads/files.zip`.
