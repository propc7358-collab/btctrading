from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from quant.data.store import load_bars, load_funding
from quant.data.universe import UNIVERSES, Instrument
from quant.research.gates import GATES
from quant.research.ledger import Ledger
from quant.research.pooled import POOLS, research_pooled
from quant.research.run import Candidate, candidates_frame, research
from quant.strategies import REGISTRY
from quant.types import Timeframe

REPORTS = Path(__file__).resolve().parents[2] / "research" / "reports"


def load(inst: Instrument, tf: Timeframe) -> tuple[pd.DataFrame, pd.Series]:
    return load_bars(inst, tf), load_funding(inst)


def render(run_id: str, candidates: list[Candidate], n_trials: int) -> str:
    frame = candidates_frame(candidates).sort_values("oos_sharpe", ascending=False)
    accepted = frame[frame["accepted"]]
    lines = [
        f"# 研究回合 {run_id}",
        "",
        f"- 候選組合（策略 × 標的 × 時間窗口）：{len(frame)}",
        f"- 帳本累計樣本外嘗試次數（多重檢定用）：{n_trials}",
        f"- 通過全部 {len(GATES)} 道門檻：**{len(accepted)}**",
        "",
        "## 門檻",
        "",
    ]
    if candidates:
        lines += [f"- `{g.gate}`：{g.meaning}（門檻 {g.threshold:g}）" for g in candidates[0].gates]
    lines += ["", "## 通過的策略", ""]
    if accepted.empty:
        lines.append("沒有任何組合通過全部門檻。")
    else:
        lines.append(_table(accepted))
    near = frame[~frame["accepted"]].copy()
    near["n_failed"] = near["failed"].str.count(",") + 1
    near = near.sort_values(["n_failed", "oos_sharpe"], ascending=[True, False]).head(25)
    lines += ["", "## 最接近通過的 25 個（給角色質詢用）", "", _table(near, with_failed=True)]
    passes: dict[str, int] = {}
    for c in candidates:
        for g in c.gates:
            passes[g.gate] = passes.get(g.gate, 0) + int(g.passed)
    lines += ["", "## 各門檻通過數", ""]
    lines += [f"- {k}: {v}/{len(candidates)}" for k, v in passes.items()]
    return "\n".join(lines) + "\n"


def _table(frame: pd.DataFrame, with_failed: bool = False) -> str:
    cols = [
        "strategy",
        "label",
        "timeframe",
        "params",
        "is_sharpe",
        "oos_sharpe",
        "oos_total_return",
        "oos_max_drawdown",
        "oos_n_trades",
        "gate_deflated_sharpe",
    ]
    if with_failed:
        cols.append("failed")
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "---|" * len(cols)
    body = []
    for _, row in frame[cols].iterrows():
        cells = []
        for col in cols:
            value = row[col]
            cells.append(f"{value:.3f}" if isinstance(value, float) else str(value))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one research round over the universe")
    parser.add_argument("--universe", default="core", choices=sorted(UNIVERSES))
    parser.add_argument("--timeframes", nargs="*", default=[t.value for t in Timeframe])
    parser.add_argument("--strategies", nargs="*", default=sorted(REGISTRY))
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--pooled", action="store_true", help="test each strategy on asset pools")
    parser.add_argument(
        "--ledger", type=Path, default=None, help="ledger for a pre-registered study"
    )
    parser.add_argument("--reports", type=Path, default=REPORTS)
    args = parser.parse_args(argv)
    run_id = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    instruments = [
        i for i in UNIVERSES[args.universe] if not args.only or i.inst_id.split("-")[0] in args.only
    ]
    ledger = Ledger(args.ledger) if args.ledger else Ledger()
    timeframes = [Timeframe(t) for t in args.timeframes]
    strategies = [REGISTRY[s] for s in args.strategies]
    if args.pooled:
        run_id = f"{run_id}-pooled"
        candidates = research_pooled(POOLS, timeframes, strategies, load, ledger, run_id)
    else:
        candidates = research(instruments, timeframes, strategies, load, ledger, run_id)
    reports: Path = args.reports
    reports.mkdir(parents=True, exist_ok=True)
    n_trials = ledger.oos_trial_count()
    (reports / f"{run_id}.md").write_text(render(run_id, candidates, n_trials))
    candidates_frame(candidates).to_csv(reports / f"{run_id}.csv", index=False)
    accepted = sum(c.accepted for c in candidates)
    print(
        f"{run_id}: {len(candidates)} candidates, {accepted} accepted, report {reports}/{run_id}.md"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
