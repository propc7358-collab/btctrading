from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant.data import okx
from quant.data.resample import resample
from quant.data.universe import Instrument
from quant.types import Timeframe, validate_bars

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
BASE_BAR = "5m"


def bars_path(inst: Instrument, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / f"{inst.inst_id}_{BASE_BAR}.parquet"


def funding_path(inst: Instrument, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / f"{inst.inst_id}_funding.parquet"


def sync(inst: Instrument, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = bars_path(inst, data_dir)
    listed = okx.list_time(inst.inst_id)
    start = max(listed, inst.history_start) if inst.history_start else listed
    existing = pd.read_parquet(path) if path.exists() else None
    since = existing.index.max() if existing is not None else start
    fresh = okx.fetch_candles(inst.inst_id, BASE_BAR, since)
    merged = fresh if existing is None else pd.concat([existing, fresh])
    merged = validate_bars(merged[~merged.index.duplicated(keep="last")].sort_index())
    merged.to_parquet(path)
    funding = okx.fetch_funding(inst.inst_id, start)
    fpath = funding_path(inst, data_dir)
    if fpath.exists():
        old = pd.read_parquet(fpath)["funding_rate"]
        funding = pd.concat([old, funding])
        funding = funding[~funding.index.duplicated(keep="last")].sort_index()
    funding.to_frame().to_parquet(fpath)
    return merged


def load_bars(inst: Instrument, timeframe: Timeframe, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return resample(pd.read_parquet(bars_path(inst, data_dir)), timeframe)


def load_funding(inst: Instrument, data_dir: Path = DATA_DIR) -> pd.Series:
    path = funding_path(inst, data_dir)
    if not path.exists():
        return pd.Series(dtype=float, name="funding_rate")
    return pd.read_parquet(path)["funding_rate"]
