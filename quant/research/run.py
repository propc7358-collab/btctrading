from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from quant.data.universe import Instrument
from quant.engine.backtest import DEFAULT_COSTS, CostModel, Result, backtest
from quant.research.gates import COST_STRESS_FACTOR, Evidence, GateResult, judge
from quant.research.ledger import Ledger, Trial, params_key
from quant.strategies.base import Params, Strategy
from quant.types import Timeframe

IS_FRACTION = 0.6
MIN_BARS = 500
WATCH_MIN_DEFLATED_SHARPE = 0.5

Loader = Callable[[Instrument, Timeframe], tuple[pd.DataFrame, pd.Series]]


@dataclass(frozen=True)
class Candidate:
    strategy: Strategy
    params: Params
    inst: Instrument
    timeframe: Timeframe
    is_result: Result
    oos_result: Result
    evidence: Evidence
    gates: tuple[GateResult, ...]

    @property
    def accepted(self) -> bool:
        return self.verdict is Verdict.ACCEPT

    @property
    def verdict(self) -> Verdict:
        if not self.failed:
            return Verdict.ACCEPT
        dsr = next(g for g in self.gates if g.gate == "deflated_sharpe")
        if self.failed == ["deflated_sharpe"] and dsr.value >= WATCH_MIN_DEFLATED_SHARPE:
            return Verdict.WATCH
        return Verdict.REJECT

    @property
    def failed(self) -> list[str]:
        return [g.gate for g in self.gates if not g.passed]


class Verdict(Enum):
    ACCEPT = "accept"
    WATCH = "watch"
    REJECT = "reject"


@dataclass(frozen=True)
class _Pending:
    strategy: Strategy
    params: Params
    inst: Instrument
    timeframe: Timeframe
    is_result: Result
    oos_result: Result
    stressed: Result
    buy_hold: Result
    neighbours: tuple[float, ...]


def split_point(index: pd.DatetimeIndex, fraction: float = IS_FRACTION) -> pd.Timestamp:
    return pd.Timestamp(index[int(len(index) * fraction)])


def research(
    instruments: Iterable[Instrument],
    timeframes: Iterable[Timeframe],
    strategies: Iterable[Strategy],
    load: Loader,
    ledger: Ledger,
    run_id: str,
    costs: CostModel = DEFAULT_COSTS,
) -> list[Candidate]:
    strategies = list(strategies)
    timeframes = list(timeframes)
    pending: list[_Pending] = []
    for inst in instruments:
        for tf in timeframes:
            bars, funding = load(inst, tf)
            if len(bars) < MIN_BARS:
                continue
            cut = split_point(pd.DatetimeIndex(bars.index))
            start, end = bars.index[0], bars.index[-1] + tf.offset
            buy_hold = backtest(bars, pd.Series(1.0, index=bars.index), costs, funding)
            for strategy in strategies:
                pending.append(
                    _select_and_test(
                        strategy,
                        inst,
                        tf,
                        bars,
                        funding,
                        costs,
                        cut,
                        start,
                        end,
                        buy_hold.window(cut, end),
                        ledger,
                        run_id,
                    )
                )
    ledger.flush()
    oos = ledger.oos_trials()
    n_trials = max(len(oos), 1)
    return [_judge(p, n_trials) for p in pending]


def _select_and_test(
    strategy: Strategy,
    inst: Instrument,
    tf: Timeframe,
    bars: pd.DataFrame,
    funding: pd.Series,
    costs: CostModel,
    cut: pd.Timestamp,
    start: pd.Timestamp,
    end: pd.Timestamp,
    buy_hold_oos: Result,
    ledger: Ledger,
    run_id: str,
) -> _Pending:
    is_sharpes: dict[str, float] = {}
    best: tuple[float, Params, Result] | None = None
    for params in strategy.param_sets():
        full = backtest(bars, strategy.signal(bars, params), costs, funding)
        in_sample = full.window(start, cut)
        is_sharpes[params_key(params)] = in_sample.sharpe
        ledger.record(_trial(run_id, "is", strategy, params, inst, tf, in_sample))
        if best is None or in_sample.sharpe > best[0]:
            best = (in_sample.sharpe, params, full)
    if best is None:
        raise ValueError(f"{strategy.name} has an empty parameter grid")
    _, params, full = best
    signal = strategy.signal(bars, params)
    stressed = backtest(bars, signal, costs.scaled(COST_STRESS_FACTOR), funding).window(cut, end)
    oos_result = full.window(cut, end)
    ledger.record(_trial(run_id, "oos", strategy, params, inst, tf, oos_result))
    neighbours = tuple(is_sharpes[params_key(n)] for n in strategy.neighbours(params))
    return _Pending(
        strategy,
        params,
        inst,
        tf,
        full.window(start, cut),
        oos_result,
        stressed,
        buy_hold_oos,
        neighbours,
    )


def _judge(p: _Pending, n_trials: int) -> Candidate:
    evidence = Evidence(
        oos=p.oos_result,
        oos_stressed=p.stressed,
        buy_hold_oos=p.buy_hold,
        best_is_sharpe=p.is_result.sharpe,
        neighbour_is_sharpes=p.neighbours,
        n_trials=n_trials,
    )
    return Candidate(
        p.strategy,
        p.params,
        p.inst,
        p.timeframe,
        p.is_result,
        p.oos_result,
        evidence,
        tuple(judge(evidence)),
    )


def _trial(
    run_id: str,
    phase: str,
    strategy: Strategy,
    params: Params,
    inst: Instrument,
    tf: Timeframe,
    result: Result,
) -> Trial:
    return Trial(
        run_id,
        phase,
        strategy.name,
        params_key(params),
        inst.inst_id,
        tf.value,
        result.sharpe_per_bar,
        result.sharpe,
        result.n_trades,
        result.total_return,
    )


def candidates_frame(candidates: list[Candidate]) -> pd.DataFrame:
    rows = []
    for c in candidates:
        row: dict[str, object] = {
            "strategy": c.strategy.name,
            "family": c.strategy.family.value,
            "inst_id": c.inst.inst_id,
            "label": c.inst.label,
            "asset_class": c.inst.asset_class.value,
            "timeframe": c.timeframe.value,
            "params": params_key(c.params),
            "is_sharpe": c.is_result.sharpe,
            "accepted": c.accepted,
            "verdict": c.verdict.value,
            "failed": ",".join(c.failed),
        }
        row.update({f"oos_{k}": v for k, v in c.oos_result.summary().items()})
        row.update({f"gate_{g.gate}": g.value for g in c.gates})
        rows.append(row)
    return pd.DataFrame(rows)
