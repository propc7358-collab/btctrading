from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant.research.portfolio import MAX_GROSS_LEVERAGE, Sleeve, build, select

DAYS = pd.date_range("2010-01-01", periods=800, freq="D", tz="UTC")


def _sleeve(name: str, inst: str, sharpe: float, series: np.ndarray, trades: int = 50) -> Sleeve:
    daily = pd.Series(series, index=DAYS)
    return Sleeve(name, inst, sharpe, trades, daily, daily, daily)


def _noise(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0005, 0.01, len(DAYS))


def test_select_skips_correlated_weak_and_overused_instruments() -> None:
    base = _noise(1)
    sleeves = [
        _sleeve("a", "X", 2.0, base),
        _sleeve("a_clone", "Y", 1.9, base + _noise(2) * 0.05),
        _sleeve("b", "X", 1.5, _noise(3)),
        _sleeve("c", "X", 1.4, _noise(4)),
        _sleeve("weak", "Z", 0.1, _noise(5)),
        _sleeve("few_trades", "Z", 3.0, _noise(6), trades=5),
        _sleeve("d", "Z", 1.0, _noise(7)),
    ]
    assert [s.name for s in select(sleeves)] == ["a", "b", "d"]


def test_build_targets_ten_percent_in_sample_vol_within_leverage_cap() -> None:
    sleeves = [_sleeve(f"s{i}", f"I{i}", 1.0, _noise(10 + i)) for i in range(5)]
    result = build(sleeves)
    assert len(result.sleeves) == 5
    assert float(result.is_daily.std(ddof=1)) * np.sqrt(252) == pytest.approx(0.10, rel=1e-6)
    assert sum(result.weights) <= MAX_GROSS_LEVERAGE + 1e-9


def test_empty_pool_fails_instead_of_passing() -> None:
    result = build([_sleeve("weak", "X", 0.0, _noise(1))])
    assert not result.passed
