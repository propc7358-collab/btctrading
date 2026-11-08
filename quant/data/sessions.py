from __future__ import annotations

import pandas as pd

from quant.data.universe import Instrument
from quant.types import AssetClass

LISTING_BURN_IN = pd.Timedelta(days=7)
FRIDAY, SUNDAY = 4, 6
CLOSE_HOUR_UTC = 21
REOPEN_HOUR_UTC = 22


def tradfi_closed(index: pd.DatetimeIndex) -> pd.Series:
    day = index.day_of_week
    hour = index.hour
    weekend = (
        ((day == FRIDAY) & (hour >= CLOSE_HOUR_UTC))
        | (day == FRIDAY + 1)
        | ((day == SUNDAY) & (hour < REOPEN_HOUR_UTC))
    )
    daily_break = hour == CLOSE_HOUR_UTC
    return pd.Series(weekend | daily_break, index=index)


def tradable_bars(inst: Instrument, base: pd.DataFrame) -> pd.DataFrame:
    index = pd.DatetimeIndex(base.index)
    keep = index >= index[0] + LISTING_BURN_IN
    if inst.asset_class is not AssetClass.CRYPTO_CONTROL:
        keep &= ~tradfi_closed(index).to_numpy()
    return base.iloc[keep.nonzero()[0]]
