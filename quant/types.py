from __future__ import annotations

from enum import Enum
from typing import NewType

import pandas as pd

InstId = NewType("InstId", str)

BAR_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close", "volume")


class AssetClass(Enum):
    METAL = "metal"
    ENERGY = "energy"
    US_EQUITY = "us_equity"
    TAIWAN = "taiwan"
    CRYPTO_CONTROL = "crypto_control"


class Timeframe(Enum):
    M10 = "10m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"

    @property
    def offset(self) -> pd.Timedelta:
        return pd.Timedelta(self.value.replace("m", "min"))

    @property
    def hours(self) -> float:
        return self.offset / pd.Timedelta(hours=1)


class BarsError(ValueError):
    pass


def validate_bars(bars: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in BAR_COLUMNS if c not in bars.columns]
    if missing:
        raise BarsError(f"missing columns {missing}")
    if not isinstance(bars.index, pd.DatetimeIndex) or bars.index.tz is None:
        raise BarsError("index must be a tz-aware DatetimeIndex")
    if not bars.index.is_monotonic_increasing or bars.index.has_duplicates:
        raise BarsError("index must be strictly increasing")
    if bars[list(BAR_COLUMNS)].isna().any().any():
        raise BarsError("bars contain NaN")
    bad = (bars["high"] < bars[["open", "close", "low"]].max(axis=1)) | (
        bars["low"] > bars[["open", "close", "high"]].min(axis=1)
    )
    if bad.any():
        raise BarsError(
            f"{int(bad.sum())} bars violate high/low bounds, first at {bars.index[bad][0]}"
        )
    return bars
