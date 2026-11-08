from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd

Params = dict[str, Any]
SignalFn = Callable[..., pd.Series]


class Family(Enum):
    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"


@dataclass(frozen=True)
class Strategy:
    name: str
    family: Family
    rationale: str
    grid: dict[str, tuple[Any, ...]]
    fn: SignalFn

    def param_sets(self) -> list[Params]:
        keys = list(self.grid)
        return [
            dict(zip(keys, combo, strict=True)) for combo in itertools.product(*self.grid.values())
        ]

    def neighbours(self, params: Params) -> list[Params]:
        out: list[Params] = []
        for key, values in self.grid.items():
            position = values.index(params[key])
            for step in (-1, 1):
                if 0 <= position + step < len(values):
                    out.append({**params, key: values[position + step]})
        return out

    def signal(self, bars: pd.DataFrame, params: Params) -> pd.Series:
        raw = self.fn(bars, **params)
        return raw.reindex(bars.index).fillna(0.0).clip(-1, 1).round()


REGISTRY: dict[str, Strategy] = {}


class RegistrationError(ValueError):
    pass


def register(
    family: Family, rationale: str, **grid: tuple[Any, ...]
) -> Callable[[SignalFn], SignalFn]:
    def decorate(fn: SignalFn) -> SignalFn:
        if len(rationale.strip()) < 40:
            raise RegistrationError(f"{fn.__name__}: state the economic rationale, not a label")
        if fn.__name__ in REGISTRY:
            raise RegistrationError(f"{fn.__name__} registered twice")
        REGISTRY[fn.__name__] = Strategy(fn.__name__, family, rationale, grid, fn)
        return fn

    return decorate
