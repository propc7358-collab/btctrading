from __future__ import annotations

import pandas as pd
import pytest

from quant.strategies import REGISTRY
from quant.strategies.base import Family, Strategy
from tests.conftest import make_bars

BARS = make_bars(900, seed=7, autocorr=0.1)
CUTS = (300, 517, 899)


def leaks_future(strategy: Strategy, params: dict[str, object]) -> bool:
    full = strategy.signal(BARS, params)
    for cut in CUTS:
        prefix = BARS.iloc[:cut]
        if not strategy.signal(prefix, params).equals(full.iloc[:cut]):
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
