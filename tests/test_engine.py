from __future__ import annotations

import pandas as pd
import pytest

from quant.engine.backtest import ASSUMED_FUNDING_PER_8H, CostModel, SignalError, backtest
from tests.conftest import bars_from_opens

ZERO = CostModel(fee_bps=0, slippage_bps=0)
NO_FUNDING = pd.Series([0.0], index=pd.DatetimeIndex(["2020-01-01"], tz="UTC"))


def test_signal_trades_at_next_open_not_at_its_own_bar() -> None:
    bars = bars_from_opens([100, 110, 121, 121])
    signal = pd.Series([1.0, 0, 0, 0], index=bars.index)
    result = backtest(bars, signal, ZERO, NO_FUNDING)
    assert result.net.tolist() == pytest.approx([0.0, 0.10, 0.0, 0.0])


def test_costs_charge_each_unit_of_turnover() -> None:
    bars = bars_from_opens([100, 100, 100, 100, 100])
    signal = pd.Series([1.0, -1, 0, 0, 0], index=bars.index)
    costs = CostModel(fee_bps=5, slippage_bps=3)
    result = backtest(bars, signal, costs, NO_FUNDING)
    assert result.net.tolist() == pytest.approx([0, -0.0008, -0.0016, -0.0008, 0])
    assert result.trades["ret"].tolist() == pytest.approx([-0.0016, -0.0016])


def test_short_receives_positive_funding_when_history_covers_it() -> None:
    bars = bars_from_opens([100] * 10)
    funding = pd.Series([0.001], index=pd.DatetimeIndex([bars.index[3]]))
    signal = pd.Series([-1.0] * 10, index=bars.index)
    result = backtest(bars, signal, ZERO, funding)
    assert result.net.iloc[3] == pytest.approx(0.001)


def test_missing_funding_history_is_charged_against_both_sides() -> None:
    bars = bars_from_opens([100] * 10)
    for side in (1.0, -1.0):
        result = backtest(bars, pd.Series(side, index=bars.index), ZERO, None)
        assert result.net.iloc[5] == pytest.approx(-ASSUMED_FUNDING_PER_8H / 8)


@pytest.mark.parametrize("bad", [[0.5, 0, 0], [float("nan"), 0, 0], [2.0, 0, 0]])
def test_engine_rejects_signals_outside_minus_one_zero_one(bad: list[float]) -> None:
    bars = bars_from_opens([100, 101, 102])
    with pytest.raises(SignalError):
        backtest(bars, pd.Series(bad, index=bars.index), ZERO, NO_FUNDING)


def test_funding_at_time_t_is_paid_by_a_position_held_from_the_open_at_t() -> None:
    bars = bars_from_opens([100] * 6)
    funding = pd.Series([0.0, 0.002], index=pd.DatetimeIndex([bars.index[0], bars.index[3]]))
    entered_at_t = pd.Series([0.0, 0, 1, 1, 1, 1], index=bars.index)
    closed_at_t = pd.Series([1.0, 1, 0, 0, 0, 0], index=bars.index)
    assert backtest(bars, entered_at_t, ZERO, funding).net.iloc[3] == pytest.approx(-0.002)
    assert backtest(bars, closed_at_t, ZERO, funding).net.iloc[3] == pytest.approx(0.0)


def test_before_funding_history_each_side_pays_the_worse_of_assumed_and_observed() -> None:
    bars = bars_from_opens([100] * 200)
    observed = pd.Series(-0.0004, index=bars.index[100::8])
    short = backtest(bars, pd.Series(-1.0, index=bars.index), ZERO, observed)
    long = backtest(bars, pd.Series(1.0, index=bars.index), ZERO, observed)
    assert short.net.iloc[50] == pytest.approx(-0.0004 / 8)
    assert long.net.iloc[50] == pytest.approx(-ASSUMED_FUNDING_PER_8H / 8)
