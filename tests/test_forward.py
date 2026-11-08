from __future__ import annotations

import pandas as pd

from quant.data.universe import Instrument
from quant.research.forward import evaluate_forward
from quant.types import Timeframe
from tests.conftest import make_bars

BARS = make_bars(3000, seed=4)


def _load(inst: Instrument, tf: Timeframe) -> tuple[pd.DataFrame, pd.Series]:
    return BARS, pd.Series(dtype=float)


def test_forward_evaluation_uses_only_bars_after_registration() -> None:
    registered = BARS.index[2000]
    registry = pd.DataFrame(
        {
            "registered_at": [registered.isoformat()],
            "strategy": ["tsmom"],
            "inst_id": ["XAU-USDT-SWAP"],
            "timeframe": ["1h"],
            "params": ['{"lookback": 24, "min_move_atr": 0.0}'],
        }
    )
    (result,) = evaluate_forward(registry, _load)
    assert result.result.net.index.min() >= registered
    assert len(result.result.net) == 1000
