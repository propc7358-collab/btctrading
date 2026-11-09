from __future__ import annotations

import pandas as pd

from quant.types import Timeframe, validate_bars


def base_interval(base: pd.DataFrame) -> pd.Timedelta:
    steps = pd.Series(pd.DatetimeIndex(base.index)).diff().dropna()
    return pd.Timedelta(steps.min()) if len(steps) else pd.Timedelta(minutes=5)


def resample(base: pd.DataFrame, timeframe: Timeframe) -> pd.DataFrame:
    validate_bars(base)
    step = base_interval(base)
    if timeframe.offset < step:
        raise ValueError(f"cannot build {timeframe.value} bars from {step} base bars")
    grouped = base.resample(timeframe.offset, label="left", closed="left")
    bars = grouped.agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    counts = grouped["close"].count()
    expected = int(timeframe.offset / step)
    bars = bars[counts >= max(1, expected // 2)]
    if len(bars) and bars.index[-1] + timeframe.offset > base.index[-1] + step:
        bars = bars.iloc[:-1]
    return validate_bars(bars)
