from __future__ import annotations

import numpy as np
import pandas as pd

from quant.research.stats import deflated_sharpe, expected_max_sharpe, probabilistic_sharpe


def test_more_trials_raise_the_bar() -> None:
    assert expected_max_sharpe(0.01, 10) < expected_max_sharpe(0.01, 1000)
    assert expected_max_sharpe(0.01, 1) == 0.0


def test_probabilistic_sharpe_is_near_one_for_a_clear_edge() -> None:
    returns = pd.Series(np.random.default_rng(0).normal(0.002, 0.01, 5000))
    assert probabilistic_sharpe(returns, 0.0) > 0.99


def test_deflation_removes_an_edge_explained_by_many_trials() -> None:
    returns = pd.Series(np.random.default_rng(1).normal(0.0004, 0.01, 2000))
    assert probabilistic_sharpe(returns, 0.0) > 0.8
    assert deflated_sharpe(returns, trial_sharpe_variance=0.001, n_trials=500) < 0.5
