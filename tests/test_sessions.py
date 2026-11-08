from __future__ import annotations

import pandas as pd

from quant.data.sessions import tradable_bars, tradfi_closed
from quant.data.universe import by_id
from tests.conftest import make_bars


def _closed_at(stamp: str) -> bool:
    return bool(tradfi_closed(pd.DatetimeIndex([pd.Timestamp(stamp, tz="UTC")])).iloc[0])


def test_weekend_and_daily_break_are_closed_but_weekday_sessions_are_open() -> None:
    assert _closed_at("2026-11-06 21:00")
    assert _closed_at("2026-11-07 12:00")
    assert _closed_at("2026-11-08 21:55")
    assert _closed_at("2026-11-10 21:30")
    assert not _closed_at("2026-11-08 22:00")
    assert not _closed_at("2026-11-06 20:55")
    assert not _closed_at("2026-11-10 14:00")


def test_tradfi_instruments_drop_closed_hours_and_listing_week() -> None:
    base = make_bars(14 * 288, freq="5min", start="2026-03-02")
    kept = tradable_bars(by_id("XAU-USDT-SWAP"), base)
    assert kept.index[0] >= base.index[0] + pd.Timedelta(days=7)
    assert not tradfi_closed(pd.DatetimeIndex(kept.index)).any()


def test_crypto_controls_keep_weekends() -> None:
    base = make_bars(14 * 288, freq="5min", start="2026-03-02")
    kept = tradable_bars(by_id("BTC-USDT-SWAP"), base)
    assert (kept.index.day_of_week >= 5).any()
