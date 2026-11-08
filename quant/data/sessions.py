from __future__ import annotations

import numpy as np
import pandas as pd

from quant.data.universe import Instrument
from quant.types import AssetClass

MIN_BURN_IN = pd.Timedelta(days=7)
MAX_THIN_SHARE = 0.02
THIN_WINDOW_DAYS = 5
EXCHANGE_TZ = "America/New_York"
FRIDAY, SUNDAY = 4, 6
CLOSE_HOUR_ET = 17
REOPEN_HOUR_ET = 18
REGULAR_OPEN_MIN, REGULAR_CLOSE_MIN = 9 * 60 + 30, 16 * 60

US_MARKET_HOLIDAYS = pd.DatetimeIndex(
    [
        "2025-05-26",
        "2025-06-19",
        "2025-07-04",
        "2025-09-01",
        "2025-11-27",
        "2025-12-25",
        "2026-01-01",
        "2026-01-19",
        "2026-02-16",
        "2026-04-03",
        "2026-05-25",
        "2026-06-19",
        "2026-07-03",
        "2026-09-07",
        "2026-11-26",
        "2026-12-25",
        "2027-01-01",
        "2027-01-18",
        "2027-02-15",
        "2027-03-26",
    ]
)


def _exchange_clock(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.tz_convert(EXCHANGE_TZ)


def tradfi_closed(index: pd.DatetimeIndex) -> pd.Series:
    local = _exchange_clock(index)
    day, hour = local.day_of_week, local.hour
    weekend = (
        ((day == FRIDAY) & (hour >= CLOSE_HOUR_ET))
        | (day == FRIDAY + 1)
        | ((day == SUNDAY) & (hour < REOPEN_HOUR_ET))
    )
    daily_break = hour == CLOSE_HOUR_ET
    session_date = local.normalize().tz_localize(None)
    next_session_date = session_date + pd.Timedelta(days=1)
    holiday = (session_date.isin(US_MARKET_HOLIDAYS) & (hour < REOPEN_HOUR_ET)) | (
        next_session_date.isin(US_MARKET_HOLIDAYS) & (hour >= CLOSE_HOUR_ET)
    )
    return pd.Series(np.asarray(weekend | daily_break | holiday), index=index)


def regular_session(index: pd.DatetimeIndex) -> np.ndarray:
    local = _exchange_clock(index)
    minutes = local.hour * 60 + local.minute
    open_day = (local.day_of_week < FRIDAY + 1) & ~tradfi_closed(index).to_numpy()
    return np.asarray(open_day & (minutes >= REGULAR_OPEN_MIN) & (minutes < REGULAR_CLOSE_MIN))


def liquid_from(base: pd.DataFrame) -> pd.Timestamp:
    index = pd.DatetimeIndex(base.index)
    earliest = index[0] + MIN_BURN_IN
    regular = base.iloc[regular_session(index).nonzero()[0]]
    if regular.empty:
        return earliest
    thin = ((regular["volume"] == 0) | (regular["high"] == regular["low"])).astype(float)
    daily = thin.groupby(_exchange_clock(pd.DatetimeIndex(regular.index)).date).mean()
    rolling = daily.rolling(THIN_WINDOW_DAYS, min_periods=THIN_WINDOW_DAYS).mean()
    liquid_days = rolling.index[(rolling < MAX_THIN_SHARE).to_numpy()]
    if len(liquid_days) == 0:
        return index[-1] + pd.Timedelta(minutes=5)
    first_liquid = pd.Timestamp(liquid_days[0]).tz_localize(EXCHANGE_TZ).tz_convert("UTC")
    return max(earliest, first_liquid + pd.Timedelta(days=1))


def tradable_bars(inst: Instrument, base: pd.DataFrame) -> pd.DataFrame:
    index = pd.DatetimeIndex(base.index)
    if inst.asset_class is AssetClass.CRYPTO_CONTROL:
        keep = np.asarray(index >= index[0] + MIN_BURN_IN)
    else:
        keep = np.asarray(index >= liquid_from(base)) & ~tradfi_closed(index).to_numpy()
    return base.iloc[np.flatnonzero(keep)]
