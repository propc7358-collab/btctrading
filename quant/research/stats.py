from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649015329
_N = NormalDist()


def expected_max_sharpe(trial_sharpe_variance: float, n_trials: int) -> float:
    if n_trials <= 1 or trial_sharpe_variance <= 0:
        return 0.0
    a = _N.inv_cdf(1 - 1 / n_trials)
    b = _N.inv_cdf(1 - 1 / (n_trials * math.e))
    return math.sqrt(trial_sharpe_variance) * ((1 - EULER_GAMMA) * a + EULER_GAMMA * b)


def probabilistic_sharpe(returns: pd.Series, benchmark_sharpe: float) -> float:
    values = returns.to_numpy(dtype=float)
    n = len(values)
    std = float(values.std(ddof=1)) if n > 1 else 0.0
    if n < 3 or std == 0 or math.isnan(std):
        return 0.0
    sharpe = float(values.mean()) / std
    standardized = (values - values.mean()) / values.std(ddof=0)
    skew = float(np.mean(standardized**3))
    kurt = float(np.mean(standardized**4))
    denominator = 1 - skew * sharpe + (kurt - 1) / 4 * sharpe**2
    if denominator <= 0:
        return 0.0
    return _N.cdf((sharpe - benchmark_sharpe) * math.sqrt(n - 1) / math.sqrt(denominator))


def deflated_sharpe(returns: pd.Series, trial_sharpe_variance: float, n_trials: int) -> float:
    return probabilistic_sharpe(returns, expected_max_sharpe(trial_sharpe_variance, n_trials))
