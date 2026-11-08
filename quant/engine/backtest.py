from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from quant.types import validate_bars

ASSUMED_FUNDING_PER_8H = 0.0001


@dataclass(frozen=True)
class CostModel:
    fee_bps: float = 5.0
    slippage_bps: float = 3.0

    @property
    def per_unit_turnover(self) -> float:
        return (self.fee_bps + self.slippage_bps) / 1e4

    def scaled(self, factor: float) -> CostModel:
        return replace(self, fee_bps=self.fee_bps * factor, slippage_bps=self.slippage_bps * factor)


DEFAULT_COSTS = CostModel()


@dataclass(frozen=True)
class Result:
    net: pd.Series
    held: pd.Series
    trades: pd.DataFrame
    bars_per_year: float

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def total_return(self) -> float:
        return float(np.expm1(np.log1p(self.net).sum()))

    @property
    def sharpe_per_bar(self) -> float:
        std = float(self.net.std(ddof=1))
        return 0.0 if std == 0 or math.isnan(std) else float(self.net.mean()) / std

    @property
    def sharpe(self) -> float:
        return self.sharpe_per_bar * math.sqrt(self.bars_per_year)

    @property
    def max_drawdown(self) -> float:
        equity = (1 + self.net).cumprod()
        return float((equity / equity.cummax() - 1).min()) if len(equity) else 0.0

    @property
    def win_rate(self) -> float:
        return float((self.trades["ret"] > 0).mean()) if self.n_trades else 0.0

    @property
    def profit_factor(self) -> float:
        wins = float(self.trades.loc[self.trades["ret"] > 0, "ret"].sum())
        losses = -float(self.trades.loc[self.trades["ret"] < 0, "ret"].sum())
        return math.inf if losses == 0 and wins > 0 else (wins / losses if losses else 0.0)

    @property
    def exposure(self) -> float:
        return float((self.held != 0).mean()) if len(self.held) else 0.0

    def window(self, start: pd.Timestamp, end: pd.Timestamp) -> Result:
        mask = (self.net.index >= start) & (self.net.index < end)
        trades = self.trades[(self.trades["entry"] >= start) & (self.trades["entry"] < end)]
        return Result(self.net[mask], self.held[mask], trades, self.bars_per_year)

    def summary(self) -> dict[str, float]:
        return {
            "sharpe": self.sharpe,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "n_trades": float(self.n_trades),
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "exposure": self.exposure,
        }


class SignalError(ValueError):
    pass


def _validate_signal(signal: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    if not signal.index.equals(index):
        raise SignalError("signal index must equal bars index")
    if signal.isna().any():
        raise SignalError("signal contains NaN; strategies must emit 0 when flat")
    if not signal.isin([-1, 0, 1]).all():
        raise SignalError("signal values must be -1, 0 or 1")
    return signal.astype(float)


def bars_per_year(index: pd.DatetimeIndex) -> float:
    if len(index) < 2:
        return 1.0
    years = (index[-1] - index[0]) / pd.Timedelta(days=365.25)
    return len(index) / years if years > 0 else 1.0


def _funding_cost(held: pd.Series, bar_hours: float, funding: pd.Series | None) -> pd.Series:
    index = pd.DatetimeIndex(held.index)
    assumed_per_hour = ASSUMED_FUNDING_PER_8H / 8
    if funding is None or funding.empty:
        return held.abs() * assumed_per_hour * bar_hours
    observed_per_hour = _observed_funding_per_hour(funding)
    worst_side_rate = np.maximum(assumed_per_hour, np.sign(held) * observed_per_hour)
    pre_coverage = held.abs() * worst_side_rate * bar_hours
    bucket = index.searchsorted(funding.index, side="right") - 1
    valid = (bucket >= 0) & (funding.index < index[-1] + pd.Timedelta(hours=bar_hours))
    actual = (
        pd.Series(funding.to_numpy()[valid], index=index[bucket[valid]])
        .groupby(level=0)
        .sum()
        .reindex(index, fill_value=0.0)
    )
    covered = index >= funding.index[0]
    return (held * actual).where(covered, pre_coverage)


def _observed_funding_per_hour(funding: pd.Series) -> float:
    if len(funding) < 2:
        return 0.0
    interval = pd.Series(funding.index).diff().median()
    span = funding.index[-1] - funding.index[0] + interval
    hours = float(span / pd.Timedelta(hours=1))
    return float(funding.sum()) / hours


def funding_coverage(index: pd.DatetimeIndex, funding: pd.Series | None) -> float:
    if funding is None or funding.empty or len(index) == 0:
        return 0.0
    return float((index >= funding.index[0]).mean())


def backtest(
    bars: pd.DataFrame,
    signal: pd.Series,
    costs: CostModel = DEFAULT_COSTS,
    funding: pd.Series | None = None,
) -> Result:
    validate_bars(bars)
    index = pd.DatetimeIndex(bars.index)
    decided = _validate_signal(signal, index)
    held = decided.shift(1, fill_value=0.0)
    open_to_open = (bars["open"].shift(-1) / bars["open"] - 1).fillna(0.0)
    gross = held * open_to_open
    turnover = (held - held.shift(1, fill_value=0.0)).abs()
    bar_hours = (
        float(pd.Series(index).diff().median() / pd.Timedelta(hours=1)) if len(index) > 1 else 1.0
    )
    funding_cost = _funding_cost(held, bar_hours, funding)
    net = gross - turnover * costs.per_unit_turnover - funding_cost
    trades = _trades(held, gross - funding_cost, costs)
    return Result(net, held, trades, bars_per_year(index))


def _trades(held: pd.Series, carry: pd.Series, costs: CostModel) -> pd.DataFrame:
    segment = (held != held.shift(1)).cumsum()
    active = held != 0
    if not active.any():
        no_time = pd.DatetimeIndex([], tz=pd.DatetimeIndex(held.index).tz)
        return pd.DataFrame(
            {"entry": no_time, "exit": no_time, "side": [], "bars": [], "ret": []}
        ).astype({"side": float, "bars": int, "ret": float})
    frame = pd.DataFrame(
        {
            "seg": segment[active],
            "side": held[active],
            "carry": carry[active],
            "ts": held.index[active],
        }
    )
    grouped = frame.groupby("seg")
    out = pd.DataFrame(
        {
            "entry": grouped["ts"].first(),
            "exit": grouped["ts"].last(),
            "side": grouped["side"].first(),
            "bars": grouped.size(),
            "ret": grouped["carry"].sum() - 2 * costs.per_unit_turnover,
        }
    )
    return out.reset_index(drop=True)
