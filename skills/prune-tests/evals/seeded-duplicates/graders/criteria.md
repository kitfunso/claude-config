---
type: script
command: python grade.py <repo> <run-folder>
---

The fixture plants three duplicate tests, one lone catcher and one heavy test. `grade.py` checks
the committed branch and the run folder. Pass only if all hold:

1. `test_band_low_again` and `test_clamp_low_dup` are gone, and exactly one of `test_spread` and
   `test_spread_copy` remains (the pair is symmetric).
2. `test_band_edge` remains. Its lines sit inside `test_band_cases`, but it alone catches the
   `x < 10` to `x <= 10` bug, the bug the history's fix commit removed.
3. `test_band_cases`, `test_clamp_all` and `test_rolling_total` remain.
4. `pricing.py` is byte-identical to master.
5. The run folder holds a plan.json whose heavy list names `test_rolling_total`, and a report.html.
6. The default run still collects every kept test: no `-m` in the pytest config's addopts. A heavy
   test that alone catches its bugs is marked for per-change runs, never dropped from the default.
7. The branch's commit message carries the numbers, the lost counts included.
