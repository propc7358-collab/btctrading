from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant.data.universe import Instrument
from quant.research.ledger import Ledger
from quant.research.pooled import research_pooled
from quant.research.run import Loader, Verdict, research
from quant.strategies import REGISTRY
from quant.strategies.base import Family
from quant.types import AssetClass, InstId, Timeframe
from tests.conftest import make_bars

NOISE_SEEDS = tuple(range(12))


def _instrument(code: str) -> Instrument:
    return Instrument(InstId(f"{code}-USDT-SWAP"), code, AssetClass.METAL)


def _loader(series: dict[str, pd.DataFrame]) -> Loader:
    def load(inst: Instrument, tf: Timeframe) -> tuple[pd.DataFrame, pd.Series]:
        return series[inst.inst_id], pd.Series(dtype=float)

    return load


def test_pure_noise_produces_no_accepted_or_watched_strategy(tmp_path: Path) -> None:
    instruments = [_instrument(f"N{s}") for s in NOISE_SEEDS]
    data = {
        i.inst_id: make_bars(6000, seed=s) for i, s in zip(instruments, NOISE_SEEDS, strict=True)
    }
    candidates = research(
        instruments,
        [Timeframe.H1],
        REGISTRY.values(),
        _loader(data),
        Ledger(tmp_path / "ledger.csv"),
        "noise",
    )
    surviving = [
        (c.strategy.name, c.inst.inst_id) for c in candidates if c.verdict is not Verdict.REJECT
    ]
    assert len(candidates) == len(instruments) * len(REGISTRY)
    assert surviving == []


def test_planted_momentum_is_accepted_only_for_trend_strategies_on_the_trending_series(
    tmp_path: Path,
) -> None:
    trending, noise = _instrument("TREND"), _instrument("NOISE")
    data = {
        trending.inst_id: make_bars(30000, seed=100, autocorr=0.4),
        noise.inst_id: make_bars(30000, seed=101),
    }
    candidates = research(
        [trending, noise],
        [Timeframe.H1],
        REGISTRY.values(),
        _loader(data),
        Ledger(tmp_path / "ledger.csv"),
        "planted",
    )
    accepted = {(c.strategy.family, c.inst.inst_id) for c in candidates if c.accepted}
    assert (Family.TREND, trending.inst_id) in accepted
    assert all(family is Family.TREND and inst == trending.inst_id for family, inst in accepted)


def test_pooled_noise_produces_nothing_and_a_pooled_planted_trend_is_found(tmp_path: Path) -> None:
    noise = {f"N{s}": make_bars(6000, seed=200 + s) for s in range(4)}
    trend = {f"T{s}": make_bars(30000, seed=300 + s, autocorr=0.4) for s in range(3)}
    members = {name: _instrument(name) for name in [*noise, *trend]}
    data = {members[n].inst_id: bars for n, bars in {**noise, **trend}.items()}
    pools = {
        "noise": tuple(members[n] for n in noise),
        "trend": tuple(members[n] for n in trend),
    }
    candidates = research_pooled(
        pools,
        [Timeframe.H1],
        REGISTRY.values(),
        _loader(data),
        Ledger(tmp_path / "ledger.csv"),
        "pooled",
    )
    surviving = {
        (c.inst.inst_id, c.strategy.family) for c in candidates if c.verdict is not Verdict.REJECT
    }
    assert ("POOL:trend", Family.TREND) in surviving
    assert all(inst == "POOL:trend" for inst, _ in surviving)
