from __future__ import annotations

import numpy as np
import pandas as pd

from quant.data.sessions import EXCHANGE_TZ
from quant.strategies.base import Family, register
from quant.strategies.indicators import atr, ema, hold_until, prior_high, prior_low, rsi


@register(
    Family.TREND,
    "Breakouts of a multi-day range attract momentum and stop-loss flows; "
    "trends in metals and energy persist because supply responds slowly.",
    entry=(20, 40, 80),
    exit=(10, 20),
)
def donchian_breakout(bars: pd.DataFrame, entry: int, exit: int) -> pd.Series:
    close = bars["close"]
    return hold_until(
        enter_long=close > prior_high(bars, entry),
        exit_long=close < prior_low(bars, exit),
        enter_short=close < prior_low(bars, entry),
        exit_short=close > prior_high(bars, exit),
    )


@register(
    Family.TREND,
    "Moving-average regimes capture slow-moving information diffusion; the ATR "
    "filter skips flat regimes where crossovers churn and costs dominate.",
    fast=(10, 20),
    slow=(50, 100, 200),
    min_gap_atr=(0.0, 0.5),
)
def ema_trend(bars: pd.DataFrame, fast: int, slow: int, min_gap_atr: float) -> pd.Series:
    gap = (ema(bars["close"], fast) - ema(bars["close"], slow)) / atr(bars)
    return (gap > min_gap_atr).astype(float) - (gap < -min_gap_atr).astype(float)


@register(
    Family.TREND,
    "Time-series momentum: past returns predict near-future returns across "
    "commodities and equity indices, documented in futures since the 1980s.",
    lookback=(24, 48, 96, 192),
    min_move_atr=(0.0, 2.0),
)
def tsmom(bars: pd.DataFrame, lookback: int, min_move_atr: float) -> pd.Series:
    move = (bars["close"] - bars["close"].shift(lookback)) / atr(bars)
    return (move > min_move_atr).astype(float) - (move < -min_move_atr).astype(float)


@register(
    Family.MEAN_REVERSION,
    "Short-horizon overreaction: liquidity-driven selloffs in deep markets "
    "partially revert once forced sellers are absorbed.",
    period=(7, 14),
    entry=(20, 30),
    exit=(50, 60),
)
def rsi_reversion(bars: pd.DataFrame, period: int, entry: int, exit: int) -> pd.Series:
    value = rsi(bars["close"], period)
    return hold_until(
        enter_long=value < entry,
        exit_long=value > exit,
        enter_short=value > 100 - entry,
        exit_short=value < 100 - exit,
    )


@register(
    Family.MEAN_REVERSION,
    "Price stretched beyond a volatility band relative to its recent mean tends "
    "to revert when no new information arrives, typical of range-bound regimes.",
    window=(20, 50),
    width=(2.0, 2.5),
)
def bollinger_reversion(bars: pd.DataFrame, window: int, width: float) -> pd.Series:
    close = bars["close"]
    mean = close.rolling(window, min_periods=window).mean()
    band = width * close.rolling(window, min_periods=window).std()
    return hold_until(
        enter_long=close < mean - band,
        exit_long=close > mean,
        enter_short=close > mean + band,
        exit_short=close < mean,
    )


@register(
    Family.TREND,
    "Buy pullbacks inside an established trend: dips in an uptrend are often "
    "liquidity events rather than information, so the trend resumes.",
    slow=(100, 200),
    entry=(30, 40),
)
def trend_pullback(bars: pd.DataFrame, slow: int, entry: int) -> pd.Series:
    close = bars["close"]
    trend = ema(close, slow)
    rising = trend > trend.shift(10)
    falling = trend < trend.shift(10)
    value = rsi(close, 14)
    return hold_until(
        enter_long=rising & (close > trend) & (value < entry),
        exit_long=(value > 60) | (close < trend),
        enter_short=falling & (close < trend) & (value > 100 - entry),
        exit_short=(value < 40) | (close > trend),
    )


@register(
    Family.TREND,
    "Volatility expansion after compression signals new information arriving; "
    "the opening-range style breakout rides the first impulse of a swing.",
    squeeze=(48, 96),
    k=(1.0, 1.5),
)
def volatility_breakout(bars: pd.DataFrame, squeeze: int, k: float) -> pd.Series:
    close = bars["close"]
    width = atr(bars)
    compressed = width < width.rolling(squeeze, min_periods=squeeze).median()
    anchor = ema(close, 20)
    return hold_until(
        enter_long=compressed.shift(1, fill_value=False) & (close > anchor + k * width),
        exit_long=close < anchor,
        enter_short=compressed.shift(1, fill_value=False) & (close < anchor - k * width),
        exit_short=close > anchor,
    )


def _bar_spacing(index: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    steps = index.to_series().diff().dt.total_seconds() / 3600
    return steps, steps.cummin()


def _reopen_bars(index: pd.DatetimeIndex) -> pd.Series:
    steps, spacing = _bar_spacing(index)
    return (steps > spacing * 1.5).fillna(False).astype(bool)


def _bars_for_hours(index: pd.DatetimeIndex, hours: float) -> pd.Series:
    _, spacing = _bar_spacing(index)
    return (hours / spacing).apply(np.ceil)


def _bars_since(events: pd.Series) -> pd.Series:
    group = events.astype(int).cumsum()
    return events.groupby(group).cumcount().astype(float)


def _time_of_day(index: pd.DatetimeIndex) -> np.ndarray:
    local = index.tz_convert(EXCHANGE_TZ)
    return np.asarray(local.hour * 60 + local.minute)


@register(
    Family.MEAN_REVERSION,
    "OKX stock and commodity perps keep trading through the weekend and daily break while "
    "the underlying is shut, so crypto-native traders set the price with no hedgeable "
    "reference; the reopen print overshoots and market makers who can hedge again pull it "
    "back, and the edge persists because harvesting it means carrying closed-market gap risk.",
    z=(0.25, 0.5),
    hold_hours=(8.0, 24.0),
)
def reopen_gap_fade(bars: pd.DataFrame, z: float, hold_hours: float) -> pd.Series:
    index = pd.DatetimeIndex(bars.index)
    close = bars["close"]
    reopen = _reopen_bars(index)
    step = np.log(close).diff().where(~reopen)
    _, spacing = _bar_spacing(index)
    per_day = (24 / spacing) ** 0.5
    daily_sigma = step.rolling(100, min_periods=50).std().shift(1) * per_day
    pre_close = close.shift(1).where(reopen).ffill()
    gap = np.log(bars["open"] / close.shift(1)) / daily_sigma
    since = _bars_since(reopen)
    timed_out = since >= _bars_for_hours(index, hold_hours)
    return hold_until(
        enter_long=reopen & (gap < -z) & (close < pre_close),
        exit_long=reopen | timed_out | (close >= pre_close),
        enter_short=reopen & (gap > z) & (close > pre_close),
        exit_short=reopen | timed_out | (close <= pre_close),
    )


@register(
    Family.MEAN_REVERSION,
    "A bar whose move and volume are both abnormal for that time of day on a leveraged perp "
    "is usually a liquidation or stop cascade, not news: forced sellers pay for immediacy "
    "and the price partially retraces once the cascade ends, while capital that absorbs "
    "cascades stays scarce because it must sit through the move against it.",
    k=(3.0, 4.0),
    hold_hours=(6.0, 24.0),
)
def volume_shock_reversal(bars: pd.DataFrame, k: float, hold_hours: float) -> pd.Series:
    index = pd.DatetimeIndex(bars.index)
    close = bars["close"]
    reopen = _reopen_bars(index)
    step = np.log(close).diff().where(~reopen)
    slot = _time_of_day(index)
    usual_move = step.groupby(slot).transform(
        lambda s: s.rolling(20, min_periods=10).std().shift(1)
    )
    usual_volume = (
        bars["volume"]
        .groupby(slot)
        .transform(lambda s: s.rolling(20, min_periods=10).median().shift(1))
    )
    busy = bars["volume"] > 3 * usual_volume
    shock_up = busy & (step > k * usual_move)
    shock_down = busy & (step < -k * usual_move)
    shock = shock_up | shock_down
    anchor = bars["open"].where(shock).ffill()
    timed_out = _bars_since(shock) >= _bars_for_hours(index, hold_hours)
    return hold_until(
        enter_long=shock_down,
        exit_long=shock_up | reopen | timed_out | (close >= anchor),
        enter_short=shock_up,
        exit_short=shock_down | reopen | timed_out | (close <= anchor),
    )
