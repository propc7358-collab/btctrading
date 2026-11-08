from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.data.sessions import tradfi_closed
from quant.strategies import REGISTRY
from quant.strategies.base import Family, Strategy
from tests.conftest import make_bars


def _session_bars() -> pd.DataFrame:
    bars = make_bars(6 * 24 * 40, seed=8, autocorr=0.1, freq="10min", start="2026-05-04")
    volume = np.random.default_rng(9).lognormal(7, 1, len(bars))
    bars = bars.assign(volume=volume)
    return bars[~tradfi_closed(pd.DatetimeIndex(bars.index)).to_numpy()]


DATASETS = {
    "continuous": make_bars(900, seed=7, autocorr=0.1),
    "sessions_with_gaps_and_volume": _session_bars(),
}
CUT_FRACTIONS = (0.33, 0.57, 0.99)


def leaks_future(strategy: Strategy, params: dict[str, object]) -> bool:
    for bars in DATASETS.values():
        full = strategy.signal(bars, params)
        for fraction in CUT_FRACTIONS:
            cut = int(len(bars) * fraction)
            if not strategy.signal(bars.iloc[:cut], params).equals(full.iloc[:cut]):
                return True
    return False


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_every_registered_strategy_is_causal_for_every_parameter_set(name: str) -> None:
    strategy = REGISTRY[name]
    leaking = [p for p in strategy.param_sets() if leaks_future(strategy, p)]
    assert not leaking, f"{name} changes past signals when future bars are added: {leaking[:3]}"


def test_the_causality_check_catches_a_planted_leak() -> None:
    def peeks(bars: pd.DataFrame, n: int) -> pd.Series:
        return (bars["close"].rolling(n, center=True).mean() > bars["close"]).astype(float)

    planted = Strategy("peeks", Family.TREND, "test-only leak", {"n": (5,)}, peeks)
    assert leaks_future(planted, {"n": 5})


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_causality_data_actually_triggers_every_strategy(name: str) -> None:
    strategy = REGISTRY[name]
    active = [
        (label, p)
        for label, bars in DATASETS.items()
        for p in strategy.param_sets()
        if (strategy.signal(bars, p) != 0).any()
    ]
    assert active, f"{name} never trades on the causality datasets, so its check is vacuous"
