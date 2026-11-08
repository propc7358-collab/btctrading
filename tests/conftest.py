from __future__ import annotations

import numpy as np
import pandas as pd


def make_bars(
    n: int,
    seed: int = 0,
    vol: float = 0.004,
    autocorr: float = 0.0,
    freq: str = "1h",
    start: str = "2026-01-01",
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    shocks = rng.normal(0, vol, n)
    returns = np.empty(n)
    previous = 0.0
    for i in range(n):
        previous = autocorr * previous + shocks[i]
        returns[i] = previous
    close = 100 * np.exp(np.cumsum(returns))
    open_ = np.concatenate([[100.0], close[:-1]])
    spread = np.abs(rng.normal(0, vol / 2, n)) * close
    index = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread,
            "low": np.minimum(open_, close) - spread,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=index,
    )


def bars_from_opens(opens: list[float], freq: str = "1h") -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=len(opens), freq=freq, tz="UTC")
    values = np.array(opens, dtype=float)
    return pd.DataFrame(
        {
            "open": values,
            "high": values * 1.01,
            "low": values * 0.99,
            "close": values,
            "volume": 1.0,
        },
        index=index,
    )
