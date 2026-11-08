from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any

import pandas as pd

from quant.types import InstId, validate_bars

BASE_URL = "https://www.okx.com"
PAGE_LIMIT = 100
MIN_INTERVAL_S = 0.11
MAX_RETRIES = 6

Fetcher = Callable[[str, dict[str, str]], dict[str, Any]]


class OkxError(RuntimeError):
    pass


def http_get(path: str, params: dict[str, str]) -> dict[str, Any]:
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "quant-research/0.1"})
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload: dict[str, Any] = json.load(response)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == MAX_RETRIES - 1:
                raise OkxError(f"GET {url} failed: {exc}") from exc
            time.sleep(2**attempt)
            continue
        if payload.get("code") == "0":
            return payload
        if payload.get("code") in {"50011", "50013"} and attempt < MAX_RETRIES - 1:
            time.sleep(2**attempt)
            continue
        raise OkxError(f"GET {url} returned {payload.get('code')}: {payload.get('msg')}")
    raise OkxError(f"GET {url} exhausted retries")


def parse_candles(rows: list[list[str]]) -> pd.DataFrame:
    confirmed = [r for r in rows if r[8] == "1"]
    frame = pd.DataFrame(
        {
            "ts": pd.to_datetime([int(r[0]) for r in confirmed], unit="ms", utc=True),
            "open": [float(r[1]) for r in confirmed],
            "high": [float(r[2]) for r in confirmed],
            "low": [float(r[3]) for r in confirmed],
            "close": [float(r[4]) for r in confirmed],
            "volume": [float(r[7]) for r in confirmed],
        }
    )
    return frame.set_index("ts").sort_index()


def _pages(
    fetch: Fetcher, path: str, params: dict[str, str], ts_of: Callable[[Any], int], stop_ms: int
) -> Iterator[list[Any]]:
    cursor: str | None = None
    while True:
        query = dict(params)
        if cursor is not None:
            query["after"] = cursor
        started = time.monotonic()
        rows: list[Any] = fetch(path, query)["data"]
        if not rows:
            return
        yield rows
        oldest = min(ts_of(r) for r in rows)
        if oldest <= stop_ms:
            return
        cursor = str(oldest)
        elapsed = time.monotonic() - started
        if elapsed < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - elapsed)


def fetch_candles(
    inst_id: InstId, bar: str, since: pd.Timestamp, fetch: Fetcher = http_get
) -> pd.DataFrame:
    stop_ms = int(since.timestamp() * 1000)
    params = {"instId": inst_id, "bar": bar, "limit": str(PAGE_LIMIT)}
    rows: list[list[str]] = []
    for page in _pages(fetch, "/api/v5/market/history-candles", params, lambda r: int(r[0]), stop_ms):
        rows.extend(page)
    frame = parse_candles(rows)
    frame = frame[~frame.index.duplicated(keep="last")]
    return validate_bars(frame[frame.index >= since])


def fetch_funding(inst_id: InstId, since: pd.Timestamp, fetch: Fetcher = http_get) -> pd.Series:
    stop_ms = int(since.timestamp() * 1000)
    params = {"instId": inst_id, "limit": "100"}
    rows: list[dict[str, str]] = []
    path = "/api/v5/public/funding-rate-history"
    for page in _pages(fetch, path, params, lambda r: int(r["fundingTime"]), stop_ms):
        rows.extend(page)
    series = pd.Series(
        [float(r["realizedRate"] or r["fundingRate"]) for r in rows],
        index=pd.to_datetime([int(r["fundingTime"]) for r in rows], unit="ms", utc=True),
        name="funding_rate",
    ).sort_index()
    return series[~series.index.duplicated(keep="last")]


def list_time(inst_id: InstId, fetch: Fetcher = http_get) -> pd.Timestamp:
    data = fetch("/api/v5/public/instruments", {"instType": "SWAP", "instId": inst_id})["data"]
    if not data:
        raise OkxError(f"unknown instrument {inst_id}")
    return pd.Timestamp(int(data[0]["listTime"]), unit="ms", tz="UTC")
