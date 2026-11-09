from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from quant.data.okx import fetch_candles
from quant.data.resample import resample
from quant.types import BarsError, InstId, Timeframe, validate_bars
from tests.conftest import make_bars


def test_resample_aggregates_ohlcv_and_drops_the_incomplete_last_bucket() -> None:
    base = make_bars(14, freq="5min")
    bars = resample(base, Timeframe.M30)
    assert len(bars) == 2
    first = base.iloc[:6]
    assert bars.iloc[0].to_dict() == pytest.approx(
        {
            "open": first["open"].iloc[0],
            "high": first["high"].max(),
            "low": first["low"].min(),
            "close": first["close"].iloc[-1],
            "volume": first["volume"].sum(),
        }
    )


def test_ten_minute_bars_come_from_pairs_of_five_minute_bars() -> None:
    bars = resample(make_bars(12, freq="5min"), Timeframe.M10)
    assert len(bars) == 6
    assert (bars.index[1] - bars.index[0]) == pd.Timedelta(minutes=10)


def test_validate_rejects_high_below_close() -> None:
    bars = make_bars(5)
    bars.iloc[2, bars.columns.get_loc("high")] = bars["close"].iloc[2] - 1
    with pytest.raises(BarsError):
        validate_bars(bars)


def test_fetch_paginates_backwards_and_drops_unconfirmed_candles() -> None:
    start = pd.Timestamp("2026-01-01", tz="UTC")
    stamps = [int((start + pd.Timedelta(minutes=5 * i)).timestamp() * 1000) for i in range(250)]
    rows = [[str(t), "1", "2", "0.5", "1.5", "0", "0", "10", "1"] for t in reversed(stamps)]
    rows[0][8] = "0"
    calls: list[dict[str, str]] = []

    def fake(path: str, params: dict[str, str]) -> dict[str, Any]:
        calls.append(params)
        after = int(params.get("after", str(10**15)))
        page = [r for r in rows if int(r[0]) < after][:100]
        return {"code": "0", "data": page}

    bars = fetch_candles(InstId("XAU-USDT-SWAP"), "5m", start, fetch=fake)
    assert len(bars) == 249
    assert bars.index[0] == start
    assert len(calls) == 3


def test_four_hour_bars_can_be_built_from_hourly_base_bars() -> None:
    bars = resample(make_bars(24, freq="1h"), Timeframe.H4)
    assert len(bars) == 6
    with pytest.raises(ValueError):
        resample(make_bars(24, freq="1h"), Timeframe.M30)


def test_dukascopy_records_parse_open_close_low_high_with_scale() -> None:
    import lzma
    import struct

    from quant.data.dukascopy import parse_month

    month = pd.Timestamp("2020-06-01")
    raw = struct.pack(">IIIIIf", 3600, 1739715, 1735058, 1734368, 1739725, 1.5)
    bars = parse_month(lzma.compress(raw), month, 1000)
    assert bars.index[0] == pd.Timestamp("2020-06-01 01:00", tz="UTC")
    assert bars.iloc[0].to_dict() == pytest.approx(
        {"open": 1739.715, "high": 1739.725, "low": 1734.368, "close": 1735.058, "volume": 1.5}
    )


def test_long_history_instruments_never_load_data_after_the_cutoff(tmp_path: Path) -> None:
    from quant.data.store import bars_path, load_bars
    from quant.data.universe import LONGHIST, LONGHIST_END

    inst = LONGHIST[0]
    base = make_bars(24 * 120, freq="1h", start="2025-01-01")
    base.to_parquet(bars_path(inst, tmp_path))
    assert load_bars(inst, Timeframe.H4, tmp_path).index.max() < LONGHIST_END
