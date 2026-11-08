from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

LEDGER_PATH = Path(__file__).resolve().parents[2] / "research" / "ledger.csv"


@dataclass(frozen=True)
class Trial:
    run_id: str
    phase: str
    strategy: str
    params: str
    inst_id: str
    timeframe: str
    sharpe_per_bar: float
    sharpe: float
    n_trades: int
    total_return: float


class Ledger:
    """Append-only record of every evaluation. Deflated Sharpe reads its trial count from here,
    so a configuration cannot be tried without counting against later acceptances."""

    def __init__(self, path: Path = LEDGER_PATH) -> None:
        self.path = path
        self._pending: list[Trial] = []

    def record(self, trial: Trial) -> None:
        self._pending.append(trial)

    def flush(self) -> None:
        if not self._pending:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.path.exists()
        with self.path.open("a", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(self._pending[0])))
            if new_file:
                writer.writeheader()
            writer.writerows(asdict(t) for t in self._pending)
        self._pending.clear()

    def frame(self) -> pd.DataFrame:
        frames = [pd.read_csv(self.path)] if self.path.exists() else []
        if self._pending:
            frames.append(pd.DataFrame([asdict(t) for t in self._pending]))
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def oos_trial_count(self) -> int:
        frame = self.frame()
        return 0 if frame.empty else int((frame["phase"] == "oos").sum())

    def oos_trials(self) -> pd.DataFrame:
        frame = self.frame()
        if frame.empty:
            return frame
        oos = frame[frame["phase"] == "oos"]
        return oos.drop_duplicates(["strategy", "params", "inst_id", "timeframe"], keep="last")


def params_key(params: dict[str, object]) -> str:
    return json.dumps(params, sort_keys=True)
