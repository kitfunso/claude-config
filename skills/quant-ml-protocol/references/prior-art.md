# Prior art

Read at stage 0. The round answers one question before the first draft: what
is already known about forecasting this exact asset or task, and how good that
knowledge is. Its output is one page, `docs/prior-art-<date>.html`, and rows in
the idea pool.

## The rings

Search outward from the target, in order; each ring gets its own queries and
its own rows in the search log.

1. **The asset**: the exact instrument, route, grade, spread or differential,
   under every name the market uses (TD3C, VLCC MEG-China, AG-China 270kt;
   Brent-Dubai EFS, Brent-Dubai swap spread). Its mechanics too: what sets
   the price (price-reporter assessment window, exchange settlement, broker
   panel), who trades it, and what the market already prices (forward curve,
   FFA).
2. **The family**: the market it belongs to (tanker freight, crude quality
   and location spreads, physical differentials to a benchmark) and the
   drivers documented there.
3. **The method class**: forecasting approaches evaluated on similar series
   (same frequency, horizon and noise level), the failures included.

Internal prior art enters ring 1: earlier campaigns on the same asset and
sibling project pages (bd, wb, td3c), graded like any paper. A prior-art page
under a year old on the same asset is refreshed with searches dated after it,
not redone.

## Sources

Per ring, at least one query in each source family; a family with no hit is
logged as searched.

- Academic indexes: Google Scholar, SSRN, RePEc/IDEAS, arXiv q-fin, and the
  journals where this asset's work lands (Energy Economics, The Energy
  Journal, Journal of Futures Markets, Journal of Commodity Markets,
  International Journal of Forecasting; for freight, Maritime Economics &
  Logistics, Maritime Policy & Management, Transportation Research Part E).
- Agency and institute working papers: OIES, IEA, EIA, KAPSARC, central
  banks, IMF, BIS.
- The target's own definition: the price reporter's methodology (Platts,
  Argus) and the exchange contract specification, read in full, because
  the target's seam rule, roll-clean construction and mark come from them.
- Practitioner work: broker and bank research where reachable, graded
  claimed unless its validation is shown.
- Open work on the same task: public repos, notebooks, competition write-ups
  and forum threads, and every external data source they use, each marked
  held, obtainable or gap. prc26's largest single gain (ADS-B pushback times,
  +14.81 s) came from a competitor's public repo.

WebSearch finds; WebFetch or a downloaded PDF reads (Read with page ranges,
or the pdf skill, for a PDF over 10 pages). A paywalled paper is read
through its preprint, SSRN or author copy; one reached only as an abstract
is logged abstract-only and graded claimed.

Search is mechanical and fans out: one Sonnet search agent per ring, each returning
its search-log rows and a candidate list. Reading the core set, grading and
writing the feed list are judgement and stay with the session model.

## Depth: citation chasing and saturation

From every core paper, one hop back (its references on this asset or
family) and one hop forward (papers citing it, from Scholar's cited-by). The
round stops at saturation: the last two searches or hops added no new
driver, baseline, method result or documented failure, and the page names
those two. A round that stops at the first page of hits, or at a paper
count, has not reached saturation.

## The core set and the extraction row

The core set is every paper that could change a decision: a baseline, a
source, a regime, a driver, a family. Each is read
in full (data, target construction, validation design, out-of-sample
results, sensitivity checks). One row per paper:

citation and link; asset and sample span; frequency and horizon; target
construction (level, change, log, roll or seam rule); drivers used; method;
validation design (split type, refit rule, whether selection ran inside the
walk-forward); baselines beaten (no-change, random walk, futures or FFA
curve) or none; out-of-sample result in its metric, with the size; evidence
grade; final-read overlap (years, or none); red flags; what it feeds.

## Evidence grades

- **Replicated**: an independent study, or our own data, reproduces the
  out-of-sample result.
- **Walk-forward**: chronological out-of-sample evaluation with selection
  and fitting inside the training windows.
- **Pseudo out-of-sample**: a held-out tail, but the specification was
  chosen with it in view, or preprocessing spanned it.
- **In-sample**: fit statistics only (full-sample R squared or t-stats,
  Granger tests).
- **Claimed**: abstract only, practitioner assertion, or validation not
  shown.

A published skill is an upper bound: published predictability tends to
shrink out of sample and after publication, and a paper that searched many
specifications reports its best. The grade sets the weight an item carries
on the feed list; every item that is tested still goes through the
evaluator.

## Red flags

Marked on the row, each lowering the grade and never deleting the row: a
random or k-fold split on a time series; no no-change or random-walk
baseline; revised data presented as real-time; a monthly-average target
forecast from inside the month; many specifications with the best reported;
a sample ending on a regime peak; skill in one sub-period only.

## The feed list

Every item the round suggests, with where it goes and its source rows:

- the evaluator: domain baselines, the horizons the market uses, the effect
  sizes the literature reports (context for the effect worth having, never
  the effect itself);
- the data audit: data sources the literature and open work use, each
  marked held, obtainable or gap; free and already-licensed data are pulled
  as part of the work, and only paid or new-licence data goes to the user;
- the error map: documented events and structural breaks;
- the idea pool: the driver survey, every driver ranked with its citations,
  whether our data holds it and from when, primary drivers (graded
  walk-forward or replicated, or named by two or more core papers) marked;
- stage 1: model families with walk-forward or replicated evidence on this
  asset or family.

## Timing and the final-read window

The round closes before the first draft. A paper whose out-of-sample years
cover our final-read window has shown us final-read outcomes: it goes on the
campaign page's list of earlier reads of that window, and a feed item
supported only by that evidence is labelled so. A paper found mid-campaign
enters the idea pool like any other idea, with its final-read overlap beside
it. A campaign already past stage 0 runs the round as a retro under the same
rule.

## The page

`docs/prior-art-<date>.html`, self-contained: the search log (ring, source,
query, date, hits, screened, kept), the saturation note, the core-set table,
the feed list, the final-read overlaps, and the searches that found
nothing ("no published forecast of X at this horizon" is a finding, shown
with the queries behind it).
