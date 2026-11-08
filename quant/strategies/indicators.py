from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def atr(bars: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = bars["close"].shift(1)
    true_range = pd.concat(
        [
            bars["high"] - bars["low"],
            (bars["high"] - prev_close).abs(),
            (bars["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    return 100 - 100 / (1 + gain / loss.where(loss > 0))


def prior_high(bars: pd.DataFrame, window: int) -> pd.Series:
    return bars["high"].rolling(window, min_periods=window).max().shift(1)


def prior_low(bars: pd.DataFrame, window: int) -> pd.Series:
    return bars["low"].rolling(window, min_periods=window).min().shift(1)


def hold_until(
    enter_long: pd.Series, exit_long: pd.Series, enter_short: pd.Series, exit_short: pd.Series
) -> pd.Series:
    long_state = pd.Series(float("nan"), index=enter_long.index)
    long_state[exit_long.fillna(False).astype(bool)] = 0.0
    long_state[enter_long.fillna(False).astype(bool)] = 1.0
    short_state = pd.Series(float("nan"), index=enter_short.index)
    short_state[exit_short.fillna(False).astype(bool)] = 0.0
    short_state[enter_short.fillna(False).astype(bool)] = -1.0
    combined = long_state.ffill().fillna(0.0) + short_state.ffill().fillna(0.0)
    return combined.clip(-1, 1)
