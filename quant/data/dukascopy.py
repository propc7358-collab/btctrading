from __future__ import annotations

import lzma
import struct
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from quant.types import validate_bars

BASE_URL = "https://datafeed.dukascopy.com/datafeed"
RECORD = struct.Struct(">IIIIIf")
MIN_INTERVAL_S = 2.0
MAX_RETRIES = 10

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
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == MAX_RETRIES - 1:
                raise DukascopyError(f"GET {url} failed: {exc}") from exc
        time.sleep(min(5 * 2**attempt, 120))
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


def _cached(fetch: Fetcher, url: str, cache: Path | None) -> bytes | None:
    if cache is None:
        return fetch(url)
    path = cache / url.removeprefix(BASE_URL + "/").replace("/", "_")
    missing = path.with_suffix(".missing")
    if path.exists():
        return path.read_bytes()
    if missing.exists():
        return None
    payload = fetch(url)
    cache.mkdir(parents=True, exist_ok=True)
    if payload is None:
        missing.touch()
    else:
        path.write_bytes(payload)
    return payload


def fetch_hourly(
    symbol: str,
    scale: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    fetch: Fetcher = http_get,
    progress: Callable[[str], None] | None = None,
    cache: Path | None = None,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for month in pd.date_range(start.tz_localize(None), end.tz_localize(None), freq="MS"):
        started = time.monotonic()
        url = month_url(symbol, month)
        was_cached = cache is not None and any(
            (cache / url.removeprefix(BASE_URL + "/").replace("/", "_")).with_suffix(s).exists()
            for s in (".bi5", ".missing")
        )
        payload = _cached(fetch, url, cache)
        if payload:
            frames.append(parse_month(payload, month, scale))
        if progress:
            progress(f"{symbol} {month:%Y-%m} {'ok' if payload else 'missing'}")
        elapsed = time.monotonic() - started
        if not was_cached and elapsed < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - elapsed)
    if not frames:
        raise DukascopyError(f"no data for {symbol} between {start} and {end}")
    bars = pd.concat(frames).sort_index()
    bars = bars[~bars.index.duplicated(keep="last")]
    bars = bars[(bars.index >= start) & (bars.index < end)]
    return validate_bars(bars)
