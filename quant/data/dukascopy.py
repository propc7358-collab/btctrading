from __future__ import annotations

import lzma
import struct
import time
import urllib.error
import urllib.request
from collections.abc import Callable

import pandas as pd

from quant.types import validate_bars

BASE_URL = "https://datafeed.dukascopy.com/datafeed"
RECORD = struct.Struct(">IIIIIf")
MIN_INTERVAL_S = 1.0
MAX_RETRIES = 8

Fetcher = Callable[[str], bytes | None]


class DukascopyError(RuntimeError):
    pass


def http_get(url: str) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": "quant-research/0.1"})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body: bytes = response.read()
                return body
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code not in {429, 500, 502, 503} or attempt == MAX_RETRIES - 1:
                raise DukascopyError(f"GET {url} failed: {exc}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == MAX_RETRIES - 1:
                raise DukascopyError(f"GET {url} failed: {exc}") from exc
        time.sleep(min(2**attempt, 60))
    raise DukascopyError(f"GET {url} exhausted retries")


def month_url(symbol: str, month: pd.Timestamp) -> str:
    return f"{BASE_URL}/{symbol}/{month.year}/{month.month - 1:02d}/BID_candles_hour_1.bi5"


def parse_month(payload: bytes, month: pd.Timestamp, scale: float) -> pd.DataFrame:
    raw = lzma.decompress(payload) if payload else b""
    records = [RECORD.unpack_from(raw, i) for i in range(0, len(raw) - len(raw) % 24, 24)]
    start = month.tz_localize("UTC") if month.tzinfo is None else month
    frame = pd.DataFrame(
        {
            "ts": [start + pd.Timedelta(seconds=r[0]) for r in records],
            "open": [r[1] / scale for r in records],
            "close": [r[2] / scale for r in records],
            "low": [r[3] / scale for r in records],
            "high": [r[4] / scale for r in records],
            "volume": [float(r[5]) for r in records],
        }
    )
    return frame.set_index("ts")[["open", "high", "low", "close", "volume"]]


def fetch_hourly(
    symbol: str,
    scale: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    fetch: Fetcher = http_get,
    progress: Callable[[str], None] | None = None,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for month in pd.date_range(start.tz_localize(None), end.tz_localize(None), freq="MS"):
        started = time.monotonic()
        payload = fetch(month_url(symbol, month))
        if payload:
            frames.append(parse_month(payload, month, scale))
        if progress:
            progress(f"{symbol} {month:%Y-%m} {'ok' if payload else 'missing'}")
        elapsed = time.monotonic() - started
        if elapsed < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - elapsed)
    if not frames:
        raise DukascopyError(f"no data for {symbol} between {start} and {end}")
    bars = pd.concat(frames).sort_index()
    bars = bars[~bars.index.duplicated(keep="last")]
    bars = bars[(bars.index >= start) & (bars.index < end)]
    return validate_bars(bars)
