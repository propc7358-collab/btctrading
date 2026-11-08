from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import pandas as pd

from quant.data.universe import CORE, Instrument
from quant.engine.backtest import Result, backtest, bars_per_year, funding_coverage
from quant.research.ledger import Ledger
from quant.research.run import (
    MIN_BARS,
    Candidate,
    Evaluator,
    Loader,
    Pending,
    judge_all,
    select_and_test,
    split_point,
)
from quant.strategies.base import Params, Strategy
from quant.types import AssetClass, InstId, Timeframe

TRADFI = tuple(i for i in CORE if i.asset_class is not AssetClass.CRYPTO_CONTROL)
POOLS: dict[str, tuple[Instrument, ...]] = {
    "metals": tuple(i for i in CORE if i.asset_class is AssetClass.METAL),
    "energy": tuple(i for i in CORE if i.asset_class is AssetClass.ENERGY),
    "equities": tuple(
        i for i in CORE if i.asset_class in {AssetClass.US_EQUITY, AssetClass.TAIWAN}
    ),
    "all_tradfi": TRADFI,
}


@dataclass(frozen=True)
class Leg:
    inst: Instrument
    bars: pd.DataFrame
    funding: pd.Series


def pool_instrument(name: str) -> Instrument:
    return Instrument(InstId(f"POOL:{name}"), f"組合:{name}", AssetClass.US_EQUITY)


def _daily(series: pd.Series) -> pd.Series:
    index = pd.DatetimeIndex(series.index)
    return series.groupby(index.floor("1D")).sum()


def pooled_evaluator(strategy: Strategy, legs: Sequence[Leg]) -> Evaluator:
    weight = 1 / len(legs)

    def evaluate(params: Params | None, cost_factor: float) -> Result:
        nets, exposures, trades = [], [], []
        for leg in legs:
            signal = (
                pd.Series(1.0, index=leg.bars.index)
                if params is None
                else strategy.signal(leg.bars, params)
            )
            result = backtest(leg.bars, signal, leg.inst.costs.scaled(cost_factor), leg.funding)
            nets.append(_daily(result.net))
            held_index = pd.DatetimeIndex(result.held.index)
            exposures.append(result.held.abs().groupby(held_index.floor("1D")).mean())
            trades.append(result.trades.assign(ret=result.trades["ret"] * weight))
        net = pd.concat(nets, axis=1).fillna(0.0).mean(axis=1)
        held = pd.concat(exposures, axis=1).fillna(0.0).mean(axis=1)
        index = pd.DatetimeIndex(net.index)
        all_trades = pd.concat(trades, ignore_index=True).sort_values("entry")
        return Result(net, held, all_trades.reset_index(drop=True), bars_per_year(index))

    return evaluate


def pool_legs(members: Iterable[Instrument], tf: Timeframe, load: Loader) -> list[Leg]:
    loaded = [(inst, *load(inst, tf)) for inst in members]
    loaded = [(i, b, f) for i, b, f in loaded if len(b) >= MIN_BARS]
    if len(loaded) < 2:
        return []
    start = max(b.index[0] for _, b, _ in loaded)
    end = min(b.index[-1] for _, b, _ in loaded)
    return [Leg(i, b[(b.index >= start) & (b.index <= end)], f) for i, b, f in loaded]


def research_pooled(
    pools: dict[str, tuple[Instrument, ...]],
    timeframes: Iterable[Timeframe],
    strategies: Iterable[Strategy],
    load: Loader,
    ledger: Ledger,
    run_id: str,
) -> list[Candidate]:
    strategies = list(strategies)
    pending: list[Pending] = []
    for name, members in pools.items():
        for tf in timeframes:
            legs = pool_legs(members, tf, load)
            if not legs:
                continue
            probe = pooled_evaluator(strategies[0], legs)(None, 1.0)
            index = pd.DatetimeIndex(probe.net.index)
            cut = split_point(index)
            coverage = min(
                funding_coverage(
                    pd.DatetimeIndex(leg.bars.index[leg.bars.index >= cut]), leg.funding
                )
                for leg in legs
            )
            for strategy in strategies:
                pending.append(
                    select_and_test(
                        strategy,
                        pool_instrument(name),
                        tf,
                        pooled_evaluator(strategy, legs),
                        index,
                        ledger,
                        run_id,
                        coverage,
                    )
                )
    return judge_all(pending, ledger)
