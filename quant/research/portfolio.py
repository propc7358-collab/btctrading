from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant.research.run import Candidate
from quant.research.stats import probabilistic_sharpe

MIN_IS_SHARPE = 0.3
MIN_IS_TRADES = 30
MAX_CORRELATION = 0.5
MAX_PER_INSTRUMENT = 2
PORTFOLIO_SIZE = 5
TARGET_ANNUAL_VOL = 0.10
MAX_GROSS_LEVERAGE = 3.0
MAX_DRAWDOWN_LIMIT = -0.25
MIN_PSR = 0.95


@dataclass(frozen=True)
class Sleeve:
    name: str
    inst_id: str
    is_sharpe: float
    is_trades: int
    is_daily: pd.Series
    oos_daily: pd.Series
    oos_stressed_daily: pd.Series


@dataclass(frozen=True)
class PortfolioResult:
    sleeves: tuple[Sleeve, ...]
    weights: tuple[float, ...]
    is_daily: pd.Series
    oos_daily: pd.Series
    oos_stressed_daily: pd.Series

    @property
    def oos_total_return(self) -> float:
        return _compound(self.oos_daily)

    @property
    def oos_stressed_return(self) -> float:
        return _compound(self.oos_stressed_daily)

    @property
    def oos_psr(self) -> float:
        return probabilistic_sharpe(self.oos_daily, 0.0)

    @property
    def oos_halves(self) -> tuple[float, float]:
        middle = len(self.oos_daily) // 2
        return _compound(self.oos_daily.iloc[:middle]), _compound(self.oos_daily.iloc[middle:])

    @property
    def oos_max_drawdown(self) -> float:
        equity = (1 + self.oos_daily).cumprod()
        return float((equity / equity.cummax() - 1).min()) if len(equity) else 0.0

    def annual_sharpe(self, daily: pd.Series) -> float:
        std = float(daily.std(ddof=1))
        return 0.0 if std == 0 or math.isnan(std) else float(daily.mean()) / std * math.sqrt(252)

    def checks(self) -> dict[str, bool]:
        first, second = self.oos_halves
        return {
            "oos_profitable_psr": self.oos_total_return > 0 and self.oos_psr >= MIN_PSR,
            "cost_stress_2x": self.oos_stressed_return > 0,
            "both_halves_profitable": first > 0 and second > 0,
            "max_drawdown_within_limit": self.oos_max_drawdown >= MAX_DRAWDOWN_LIMIT,
        }

    @property
    def passed(self) -> bool:
        return bool(self.sleeves) and all(self.checks().values())


def _compound(daily: pd.Series) -> float:
    return float(np.prod(1 + daily.to_numpy(dtype=float)) - 1) if len(daily) else 0.0


def _daily(series: pd.Series) -> pd.Series:
    return series.groupby(pd.DatetimeIndex(series.index).floor("1D")).sum()


def sleeve_from_candidate(candidate: Candidate) -> Sleeve:
    return Sleeve(
        name=f"{candidate.strategy.name} {candidate.inst.inst_id} {candidate.timeframe.value}",
        inst_id=candidate.inst.inst_id,
        is_sharpe=candidate.is_result.sharpe,
        is_trades=candidate.is_result.n_trades,
        is_daily=_daily(candidate.is_result.net),
        oos_daily=_daily(candidate.oos_result.net),
        oos_stressed_daily=_daily(candidate.evidence.oos_stressed.net),
    )


def select(sleeves: Sequence[Sleeve]) -> list[Sleeve]:
    eligible = [s for s in sleeves if s.is_sharpe >= MIN_IS_SHARPE and s.is_trades >= MIN_IS_TRADES]
    chosen: list[Sleeve] = []
    for sleeve in sorted(eligible, key=lambda s: s.is_sharpe, reverse=True):
        if sum(c.inst_id == sleeve.inst_id for c in chosen) >= MAX_PER_INSTRUMENT:
            continue
        if any(_correlation(sleeve.is_daily, c.is_daily) >= MAX_CORRELATION for c in chosen):
            continue
        chosen.append(sleeve)
        if len(chosen) == PORTFOLIO_SIZE:
            break
    return chosen


def _correlation(a: pd.Series, b: pd.Series) -> float:
    joined = pd.concat([a, b], axis=1).fillna(0.0).to_numpy(dtype=float)
    value = float(np.corrcoef(joined[:, 0], joined[:, 1])[0, 1])
    return 1.0 if math.isnan(value) else value


def _combine(series: Sequence[pd.Series], weights: Sequence[float]) -> pd.Series:
    frame = pd.concat(series, axis=1).fillna(0.0)
    return (frame * np.asarray(weights)).sum(axis=1)


def build(sleeves: Sequence[Sleeve]) -> PortfolioResult:
    chosen = select(sleeves)
    if not chosen:
        empty = pd.Series(dtype=float)
        return PortfolioResult((), (), empty, empty, empty)
    raw = [1 / float(s.is_daily.std(ddof=1)) for s in chosen]
    unscaled = _combine([s.is_daily for s in chosen], raw)
    scale = TARGET_ANNUAL_VOL / (float(unscaled.std(ddof=1)) * math.sqrt(252))
    weights = [w * scale for w in raw]
    gross = sum(weights)
    if gross > MAX_GROSS_LEVERAGE:
        weights = [w * MAX_GROSS_LEVERAGE / gross for w in weights]
    return PortfolioResult(
        tuple(chosen),
        tuple(weights),
        _combine([s.is_daily for s in chosen], weights),
        _combine([s.oos_daily for s in chosen], weights),
        _combine([s.oos_stressed_daily for s in chosen], weights),
    )
