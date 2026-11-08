from __future__ import annotations

import pandas as pd

from quant.types import Timeframe, validate_bars

BASE = pd.Timedelta(minutes=5)


def resample(base: pd.DataFrame, timeframe: Timeframe) -> pd.DataFrame:
    validate_bars(base)
    grouped = base.resample(timeframe.offset, label="left", closed="left")
    bars = grouped.agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    counts = grouped["close"].count()
    expected = int(timeframe.offset / BASE)
    bars = bars[counts >= max(1, expected // 2)]
    if len(bars) and bars.index[-1] + timeframe.offset > base.index[-1] + BASE:
        bars = bars.iloc[:-1]
    return validate_bars(bars)
