from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant.data import dukascopy, okx
from quant.data.resample import resample
from quant.data.sessions import tradable_bars
from quant.data.universe import Instrument, by_id
from quant.types import Timeframe, validate_bars

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def bars_path(inst: Instrument, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / f"{inst.inst_id}_{inst.base_bar}.parquet"


def funding_path(inst: Instrument, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / f"{inst.inst_id}_funding.parquet"


def _sync_dukascopy(inst: Instrument, data_dir: Path) -> pd.DataFrame:
    if inst.history_start is None or inst.history_end is None:
        raise ValueError(f"{inst.inst_id} needs history_start and history_end")
    symbol = inst.inst_id.removeprefix("DUKA:")
    bars = dukascopy.fetch_hourly(symbol, inst.price_scale, inst.history_start, inst.history_end)
    bars.to_parquet(bars_path(inst, data_dir))
    return bars


def sync(inst: Instrument, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    data_dir.mkdir(parents=True, exist_ok=True)
    if inst.source == "dukascopy":
        return _sync_dukascopy(inst, data_dir)
    path = bars_path(inst, data_dir)
    listed = okx.list_time(inst.inst_id, inst.inst_type)
    start = max(listed, inst.history_start) if inst.history_start else listed
    existing = pd.read_parquet(path) if path.exists() else None
    since = existing.index.max() if existing is not None else start
    fresh = okx.fetch_candles(inst.inst_id, inst.base_bar, since)
    merged = fresh if existing is None else pd.concat([existing, fresh])
    merged = validate_bars(merged[~merged.index.duplicated(keep="last")].sort_index())
    merged.to_parquet(path)
    if inst.inst_type != "SWAP":
        return merged
    funding = okx.fetch_funding(inst.inst_id, start)
    fpath = funding_path(inst, data_dir)
    if fpath.exists():
        old = pd.read_parquet(fpath)["funding_rate"]
        funding = pd.concat([old, funding])
        funding = funding[~funding.index.duplicated(keep="last")].sort_index()
    funding.to_frame().to_parquet(fpath)
    return merged


def load_bars(inst: Instrument, timeframe: Timeframe, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    base = pd.read_parquet(bars_path(inst, data_dir))
    if inst.history_end is not None:
        base = base[base.index < inst.history_end]
    return resample(tradable_bars(inst, base), timeframe)


def load_funding(inst: Instrument, data_dir: Path = DATA_DIR) -> pd.Series:
    source = by_id(inst.funding_from) if inst.funding_from else inst
    path = funding_path(source, data_dir)
    if not path.exists():
        return pd.Series(dtype=float, name="funding_rate")
    return pd.read_parquet(path)["funding_rate"]
