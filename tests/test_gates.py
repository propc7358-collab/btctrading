from __future__ import annotations

from dataclasses import replace

import pandas as pd

from quant.engine.backtest import backtest
from quant.research.gates import Evidence, in_sample_edge, split_robust
from tests.conftest import make_bars

BARS = make_bars(500, seed=3)
RESULT = backtest(BARS, pd.Series(1.0, index=BARS.index))
BASE = Evidence(
    oos=RESULT,
    oos_stressed=RESULT,
    buy_hold_oos=RESULT,
    best_is_sharpe=1.8,
    neighbour_is_sharpes=(1.5, 1.6),
    alt_split_oos_sharpes=(0.9, 2.9),
    n_trials=10,
)


def test_in_sample_edge_rejects_the_least_bad_of_an_all_losing_grid() -> None:
    assert in_sample_edge(BASE).passed
    assert not in_sample_edge(replace(BASE, best_is_sharpe=-1.68)).passed


def test_split_robust_rejects_a_candidate_that_loses_when_the_split_moves() -> None:
    assert split_robust(BASE).passed
    assert not split_robust(replace(BASE, alt_split_oos_sharpes=(-1.48, 2.6))).passed
