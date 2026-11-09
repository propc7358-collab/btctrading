from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from quant.data.store import load_bars, load_funding
from quant.data.universe import LONGHIST, Instrument, by_id
from quant.engine.backtest import Result
from quant.research.cli import render
from quant.research.ledger import Ledger
from quant.research.pooled import pool_legs, pooled_evaluator, research_pooled
from quant.research.portfolio import PortfolioResult, build, sleeve_from_candidate
from quant.research.run import Candidate, candidates_frame, research, single_evaluator
from quant.research.stats import deflated_sharpe
from quant.strategies import REGISTRY
from quant.types import Timeframe

STUDY_DIR = Path(__file__).resolve().parents[2] / "research" / "longhist"
STRATEGIES = ("tsmom", "donchian_breakout", "ema_trend")
TIMEFRAMES = (Timeframe.H4, Timeframe.H1)
LONG_POOLS: dict[str, tuple[Instrument, ...]] = {
    "metals_long": tuple(by_id(f"DUKA:{s}") for s in ("XAUUSD", "XAGUSD", "COPPERCMDUSD")),
    "energy_long": tuple(by_id(f"DUKA:{s}") for s in ("LIGHTCMDUSD", "BRENTCMDUSD", "GASCMDUSD")),
}


@dataclass(frozen=True)
class Frozen:
    strategy: str
    params: dict[str, float]
    target: str
    timeframe: Timeframe


CONFIRMATORY = (
    Frozen("tsmom", {"lookback": 24, "min_move_atr": 0.0}, "DUKA:LIGHTCMDUSD", Timeframe.H4),
    Frozen("tsmom", {"lookback": 192, "min_move_atr": 0.0}, "DUKA:XAUUSD", Timeframe.H4),
    Frozen("donchian_breakout", {"entry": 20, "exit": 20}, "POOL:energy_long", Timeframe.H4),
)


def load(inst: Instrument, tf: Timeframe) -> tuple[pd.DataFrame, pd.Series]:
    return load_bars(inst, tf), load_funding(inst)


def _frozen_results(frozen: Frozen) -> tuple[Result, Result]:
    strategy = REGISTRY[frozen.strategy]
    if frozen.target.startswith("POOL:"):
        members = LONG_POOLS[frozen.target.removeprefix("POOL:")]
        evaluate = pooled_evaluator(strategy, pool_legs(members, frozen.timeframe, load))
    else:
        inst = by_id(frozen.target)
        bars, funding = load(inst, frozen.timeframe)
        evaluate = single_evaluator(strategy, bars, funding, inst.costs)
    return evaluate(frozen.params, 1.0), evaluate(frozen.params, 2.0)


def confirmatory_section() -> list[str]:
    lines = [
        "## A. 確認性檢定（凍結參數，N = 3）",
        "",
        "| 策略 | 標的 | 期間 | 交易 | 報酬 | Sharpe | DSR "
        "| 成本加倍 | 去掉前 3 大 | 前半／後半 | 通過 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for frozen in CONFIRMATORY:
        result, stressed = _frozen_results(frozen)
        dsr = deflated_sharpe(result.net, 1 / max(len(result.net), 1), len(CONFIRMATORY))
        rets = result.trades["ret"].sort_values(ascending=False)
        without_top = float(rets.iloc[3:].sum())
        growth = 1 + result.net.to_numpy(dtype=float)
        middle = len(growth) // 2
        halves = (float(np.prod(growth[:middle]) - 1), float(np.prod(growth[middle:]) - 1))
        passed = dsr >= 0.95 and stressed.total_return > 0 and without_top > 0 and min(halves) > 0
        span = f"{result.net.index[0]:%Y-%m}–{result.net.index[-1]:%Y-%m}"
        lines.append(
            f"| {frozen.strategy} {json.dumps(frozen.params)} | {frozen.target} "
            f"{frozen.timeframe.value} | {span} | {result.n_trades} | "
            f"{result.total_return:+.1%} | {result.sharpe:.2f} | {dsr:.2f} | "
            f"{stressed.total_return:+.1%} | {without_top:+.3f} | "
            f"{halves[0]:+.1%} / {halves[1]:+.1%} | {'通過' if passed else '未通過'} |"
        )
    return lines


def portfolio_section(portfolio: PortfolioResult) -> list[str]:
    lines = ["## C. 五策略組合（N = 1）", ""]
    if not portfolio.sleeves:
        return [*lines, "沒有任何策略符合樣本內挑選條件，組合為空：未通過。"]
    lines += ["| 成員 | 樣本內 Sharpe | 權重 |", "|---|---|---|"]
    lines += [
        f"| {s.name} | {s.is_sharpe:.2f} | {w:.2f} |"
        for s, w in zip(portfolio.sleeves, portfolio.weights, strict=True)
    ]
    first, second = portfolio.oos_halves
    lines += [
        "",
        f"- 樣本內年化 Sharpe：{portfolio.annual_sharpe(portfolio.is_daily):.2f}",
        f"- 樣本外期間：{portfolio.oos_daily.index[0]:%Y-%m-%d} 到 "
        f"{portfolio.oos_daily.index[-1]:%Y-%m-%d}",
        f"- 樣本外總報酬：{portfolio.oos_total_return:+.1%}，"
        f"年化 Sharpe {portfolio.annual_sharpe(portfolio.oos_daily):.2f}，"
        f"PSR {portfolio.oos_psr:.3f}",
        f"- 成本加倍後：{portfolio.oos_stressed_return:+.1%}",
        f"- 前半／後半：{first:+.1%} / {second:+.1%}",
        f"- 最大回撤：{portfolio.oos_max_drawdown:.1%}",
        "",
    ]
    lines += [f"- `{k}`：{'通過' if v else '未通過'}" for k, v in portfolio.checks().items()]
    lines += ["", f"**組合結論：{'通過' if portfolio.passed else '未通過'}**"]
    return lines


def exploratory(run_id: str) -> tuple[list[Candidate], list[Candidate]]:
    ledger = Ledger(STUDY_DIR / "ledger.csv")
    strategies = [REGISTRY[s] for s in STRATEGIES]
    single = research(LONGHIST, TIMEFRAMES, strategies, load, ledger, run_id)
    pooled = research_pooled(LONG_POOLS, TIMEFRAMES, strategies, load, ledger, f"{run_id}-pooled")
    for name, found in (("single", single), ("pooled", pooled)):
        candidates_frame(found).to_csv(STUDY_DIR / f"{run_id}-{name}.csv", index=False)
        n_trials = ledger.oos_trial_count()
        (STUDY_DIR / f"{run_id}-{name}.md").write_text(render(f"{run_id}-{name}", found, n_trials))
    return single, pooled


def main() -> int:
    run_id = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"# 長歷史研究結果 {run_id}", "", "依 `research/longhist/plan.md` 執行。", ""]
    lines += confirmatory_section()
    single, pooled = exploratory(run_id)
    verdicts = pd.Series([c.verdict.value for c in [*single, *pooled]]).value_counts()
    lines += [
        "",
        "## B. 探索性檢定",
        "",
        f"- 單一標的 {len(single)} 個、組合 {len(pooled)} 個候選",
        f"- 判定：{verdicts.to_dict()}",
        f"- 細節：`{run_id}-single.md`、`{run_id}-pooled.md`",
        "",
    ]
    lines += portfolio_section(build([sleeve_from_candidate(c) for c in single]))
    report = "\n".join(lines) + "\n"
    (STUDY_DIR / f"report-{run_id}.md").write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
