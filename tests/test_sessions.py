from __future__ import annotations

import pandas as pd
import pytest

from quant.data.sessions import liquid_from, tradable_bars, tradfi_closed
from quant.data.universe import by_id
from tests.conftest import make_bars


def _closed_at(stamp: str) -> bool:
    return bool(tradfi_closed(pd.DatetimeIndex([pd.Timestamp(stamp, tz="UTC")])).iloc[0])


@pytest.mark.parametrize(
    ("stamp", "closed"),
    [
        ("2026-07-06 21:30", True),
        ("2026-11-02 22:30", True),
        ("2026-11-02 21:30", False),
        ("2026-11-06 21:30", False),
        ("2026-11-06 22:00", True),
        ("2026-11-07 12:00", True),
        ("2026-11-08 22:30", True),
        ("2026-11-08 23:00", False),
        ("2026-07-12 22:00", False),
        ("2026-04-03 15:00", True),
        ("2026-11-25 23:30", True),
        ("2026-11-26 15:00", True),
        ("2026-11-26 23:30", False),
        ("2026-11-10 15:00", False),
    ],
)
def test_closed_hours_follow_new_york_time_and_us_holidays(stamp: str, closed: bool) -> None:
    assert _closed_at(stamp) is closed


def test_tradfi_instruments_keep_only_open_hours_after_burn_in() -> None:
    base = make_bars(30 * 288, freq="5min", start="2026-05-04")
    kept = tradable_bars(by_id("XAU-USDT-SWAP"), base)
    assert kept.index[0] >= base.index[0] + pd.Timedelta(days=7)
    assert not tradfi_closed(pd.DatetimeIndex(kept.index)).any()


def test_burn_in_waits_until_regular_session_bars_stop_being_thin() -> None:
    base = make_bars(40 * 288, freq="5min", start="2026-05-04")
    illiquid = base.index < pd.Timestamp("2026-05-25", tz="UTC")
    base.loc[illiquid, "volume"] = 0.0
    assert liquid_from(base) >= pd.Timestamp("2026-05-29", tz="UTC")


def test_crypto_controls_keep_weekends() -> None:
    base = make_bars(14 * 288, freq="5min", start="2026-03-02")
    kept = tradable_bars(by_id("BTC-USDT-SWAP"), base)
    assert (kept.index.day_of_week >= 5).any()
