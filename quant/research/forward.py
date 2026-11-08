from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from quant.data.store import load_bars, load_funding
from quant.data.universe import Instrument, by_id
from quant.engine.backtest import Result
from quant.research.pooled import POOLS, pool_legs, pooled_evaluator
from quant.research.run import Evaluator, Loader, single_evaluator
from quant.research.stats import deflated_sharpe
from quant.strategies import REGISTRY
from quant.types import Timeframe

FORWARD_DIR = Path(__file__).resolve().parents[2] / "research" / "forward"
REGISTRATION = FORWARD_DIR / "preregistered.csv"
MIN_FORWARD_TRADES = 15
MIN_FORWARD_DSR = 0.95


@dataclass(frozen=True)
class ForwardResult:
    strategy: str
    inst_id: str
    timeframe: str
    result: Result
    deflated_sharpe: float
    stressed_return: float

    @property
    def verdict(self) -> str:
        if self.result.n_trades < MIN_FORWARD_TRADES:
            return "pending"
        good = self.deflated_sharpe >= MIN_FORWARD_DSR and self.stressed_return > 0
        return "good" if good else "failing"


def _evaluator(row: pd.Series, load: Loader) -> Evaluator:
    strategy = REGISTRY[str(row["strategy"])]
    tf = Timeframe(str(row["timeframe"]))
    inst_id = str(row["inst_id"])
    if inst_id.startswith("POOL:"):
        return pooled_evaluator(strategy, pool_legs(POOLS[inst_id.removeprefix("POOL:")], tf, load))
    inst = by_id(inst_id)
    bars, funding = load(inst, tf)
    return single_evaluator(strategy, bars, funding, inst.costs)


def evaluate_forward(registry: pd.DataFrame, load: Loader) -> list[ForwardResult]:
    out: list[ForwardResult] = []
    n_registered = len(registry)
    for _, row in registry.iterrows():
        since = pd.Timestamp(str(row["registered_at"]))
        params = json.loads(str(row["params"]))
        evaluate = _evaluator(row, load)
        far = pd.Timestamp.max.tz_localize("UTC")
        result = evaluate(params, 1.0).window(since, far)
        stressed = evaluate(params, 2.0).window(since, far)
        dsr = deflated_sharpe(result.net, 1 / max(len(result.net), 1), n_registered)
        out.append(
            ForwardResult(
                str(row["strategy"]),
                str(row["inst_id"]),
                str(row["timeframe"]),
                result,
                dsr,
                stressed.total_return,
            )
        )
    return out


def _load(inst: Instrument, tf: Timeframe) -> tuple[pd.DataFrame, pd.Series]:
    return load_bars(inst, tf), load_funding(inst)


def main() -> int:
    registry = pd.read_csv(REGISTRATION)
    results = evaluate_forward(registry, _load)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    lines = [
        f"# 前向測試 {stamp}",
        "",
        f"預先登記 {len(registry)} 個候選，只用登記之後的資料評估，多重檢定 N = {len(registry)}。",
        f"GOOD：交易 ≥ {MIN_FORWARD_TRADES}、DSR ≥ {MIN_FORWARD_DSR}、成本加倍仍賺錢。",
        "",
        "| strategy | inst | tf | trades | return | sharpe | DSR | verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.strategy} | {r.inst_id} | {r.timeframe} | {r.result.n_trades} | "
            f"{r.result.total_return:+.3f} | {r.result.sharpe:.2f} | {r.deflated_sharpe:.2f} | "
            f"{r.verdict} |"
        )
    report = "\n".join(lines) + "\n"
    (FORWARD_DIR / f"report-{stamp}.md").write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
