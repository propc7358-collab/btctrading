from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant.engine.backtest import Result
from quant.research.stats import deflated_sharpe

MIN_OOS_TRADES = 15
MIN_OOS_SHARPE = 1.0
MIN_DEFLATED_SHARPE = 0.95
COST_STRESS_FACTOR = 2.0
PLATEAU_RATIO = 0.5
TOP_TRADES_REMOVED = 3


@dataclass(frozen=True)
class Evidence:
    oos: Result
    oos_stressed: Result
    buy_hold_oos: Result
    best_is_sharpe: float
    neighbour_is_sharpes: tuple[float, ...]
    n_trials: int


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    value: float
    threshold: float
    meaning: str


Gate = Callable[[Evidence], GateResult]


def enough_trades(e: Evidence) -> GateResult:
    return GateResult(
        "enough_trades",
        e.oos.n_trades >= MIN_OOS_TRADES,
        e.oos.n_trades,
        MIN_OOS_TRADES,
        "樣本外交易次數夠多，結果不是幾筆運氣單",
    )


def oos_sharpe(e: Evidence) -> GateResult:
    return GateResult(
        "oos_sharpe",
        e.oos.sharpe >= MIN_OOS_SHARPE,
        e.oos.sharpe,
        MIN_OOS_SHARPE,
        "樣本外、扣成本後的年化 Sharpe",
    )


def deflated(e: Evidence) -> GateResult:
    null_variance = 1 / max(len(e.oos.net), 1)
    value = deflated_sharpe(e.oos.net, null_variance, e.n_trials)
    return GateResult(
        "deflated_sharpe",
        value >= MIN_DEFLATED_SHARPE,
        value,
        MIN_DEFLATED_SHARPE,
        f"扣掉 {e.n_trials} 次嘗試的多重檢定後，Sharpe 仍為真的機率",
    )


def survives_cost_stress(e: Evidence) -> GateResult:
    value = e.oos_stressed.total_return
    return GateResult("cost_stress_2x", value > 0, value, 0.0, "手續費與滑價加倍後樣本外仍賺錢")


def parameter_plateau(e: Evidence) -> GateResult:
    if not e.neighbour_is_sharpes:
        return GateResult("parameter_plateau", False, 0.0, PLATEAU_RATIO, "沒有相鄰參數可比")
    median = float(pd.Series(e.neighbour_is_sharpes).median())
    ratio = median / e.best_is_sharpe if e.best_is_sharpe > 0 else 0.0
    return GateResult(
        "parameter_plateau",
        ratio >= PLATEAU_RATIO and median > 0,
        ratio,
        PLATEAU_RATIO,
        "相鄰參數也好，最佳參數不是孤立尖峰",
    )


def not_concentrated(e: Evidence) -> GateResult:
    rets = e.oos.trades["ret"].sort_values(ascending=False)
    value = float(rets.iloc[TOP_TRADES_REMOVED:].sum()) if len(rets) else 0.0
    return GateResult(
        "not_concentrated", value > 0, value, 0.0, f"拿掉最賺的 {TOP_TRADES_REMOVED} 筆交易後仍賺錢"
    )


def stable_halves(e: Evidence) -> GateResult:
    growth = 1 + e.oos.net.to_numpy(dtype=float)
    middle = len(growth) // 2
    first = float(np.prod(growth[:middle]) - 1)
    second = float(np.prod(growth[middle:]) - 1)
    return GateResult(
        "stable_halves",
        first > 0 and second > 0,
        min(first, second),
        0.0,
        "樣本外前半段與後半段都賺錢",
    )


def beats_buy_and_hold(e: Evidence) -> GateResult:
    edge = e.oos.sharpe - abs(e.buy_hold_oos.sharpe)
    return GateResult(
        "beats_buy_and_hold",
        edge > 0,
        edge,
        0.0,
        "Sharpe 高於單純持有（或放空）標的，不是只吃到行情 beta",
    )


GATES: tuple[Gate, ...] = (
    enough_trades,
    oos_sharpe,
    deflated,
    survives_cost_stress,
    parameter_plateau,
    not_concentrated,
    stable_halves,
    beats_buy_and_hold,
)


def judge(evidence: Evidence) -> list[GateResult]:
    return [gate(evidence) for gate in GATES]
