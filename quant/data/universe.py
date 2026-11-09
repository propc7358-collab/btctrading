from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant.engine.backtest import DEFAULT_COSTS, CostModel
from quant.types import AssetClass, InstId


@dataclass(frozen=True)
class Instrument:
    inst_id: InstId
    label: str
    asset_class: AssetClass
    history_start: pd.Timestamp | None = None
    costs: CostModel = DEFAULT_COSTS
    base_bar: str = "5m"
    inst_type: str = "SWAP"
    funding_from: InstId | None = None
    source: str = "okx"
    price_scale: float = 1.0
    history_end: pd.Timestamp | None = None


MEASURED_SLIPPAGE_BPS: dict[str, float] = {
    "BTC": 1,
    "ETH": 1,
    "XAU": 1,
    "XAG": 2,
    "CL": 3,
    "QQQ": 2,
    "SPY": 3,
    "NVDA": 3,
    "MU": 3,
    "AMD": 7,
    "TSM": 6,
}
UNMEASURED_SLIPPAGE_BPS = 5.0


def _inst(code: str, label: str, asset_class: AssetClass, start: str | None = None) -> Instrument:
    slippage = MEASURED_SLIPPAGE_BPS.get(code, UNMEASURED_SLIPPAGE_BPS)
    return Instrument(
        inst_id=InstId(f"{code}-USDT-SWAP"),
        label=label,
        asset_class=asset_class,
        history_start=pd.Timestamp(start, tz="UTC") if start else None,
        costs=CostModel(fee_bps=5.0, slippage_bps=slippage),
    )


CORE: tuple[Instrument, ...] = (
    _inst("XAU", "黃金", AssetClass.METAL),
    _inst("XAG", "白銀", AssetClass.METAL),
    _inst("XPT", "鉑金", AssetClass.METAL),
    _inst("XCU", "銅", AssetClass.METAL),
    _inst("CL", "WTI 原油", AssetClass.ENERGY),
    _inst("BZ", "布蘭特原油", AssetClass.ENERGY),
    _inst("NG", "天然氣", AssetClass.ENERGY),
    _inst("SPY", "S&P 500 ETF", AssetClass.US_EQUITY),
    _inst("QQQ", "Nasdaq 100 ETF", AssetClass.US_EQUITY),
    _inst("NVDA", "NVIDIA", AssetClass.US_EQUITY),
    _inst("MU", "Micron", AssetClass.US_EQUITY),
    _inst("GOOGL", "Alphabet", AssetClass.US_EQUITY),
    _inst("AAPL", "Apple", AssetClass.US_EQUITY),
    _inst("TSLA", "Tesla", AssetClass.US_EQUITY),
    _inst("AMD", "AMD", AssetClass.US_EQUITY),
    _inst("MSTR", "MicroStrategy", AssetClass.US_EQUITY),
    _inst("TSM", "台積電 ADR", AssetClass.TAIWAN),
    _inst("BTC", "BTC 對照組", AssetClass.CRYPTO_CONTROL, "2025-01-01"),
    _inst("ETH", "ETH 對照組", AssetClass.CRYPTO_CONTROL, "2025-01-01"),
)

XAUT = Instrument(
    inst_id=InstId("XAUT-USDT"),
    label="XAUT 代幣化黃金（長歷史代理）",
    asset_class=AssetClass.METAL,
    costs=CORE[0].costs,
    base_bar="1H",
    inst_type="SPOT",
    funding_from=CORE[0].inst_id,
)

LONGHIST_END = pd.Timestamp("2025-04-01", tz="UTC")
LONGHIST_START = pd.Timestamp("2005-01-01", tz="UTC")


def _long(
    symbol: str, label: str, asset_class: AssetClass, okx_code: str, scale: float
) -> Instrument:
    perp = next(i for i in CORE if i.inst_id == f"{okx_code}-USDT-SWAP")
    return Instrument(
        inst_id=InstId(f"DUKA:{symbol}"),
        label=label,
        asset_class=asset_class,
        history_start=LONGHIST_START,
        costs=perp.costs,
        base_bar="1H",
        inst_type="CFD",
        source="dukascopy",
        price_scale=scale,
        history_end=LONGHIST_END,
    )


LONGHIST: tuple[Instrument, ...] = (
    _long("XAUUSD", "黃金（長歷史）", AssetClass.METAL, "XAU", 1000),
    _long("XAGUSD", "白銀（長歷史）", AssetClass.METAL, "XAG", 1000),
    _long("COPPERCMDUSD", "銅（長歷史）", AssetClass.METAL, "XCU", 10000),
    _long("LIGHTCMDUSD", "WTI 原油（長歷史）", AssetClass.ENERGY, "CL", 1000),
    _long("BRENTCMDUSD", "布蘭特原油（長歷史，追蹤偏差大）", AssetClass.ENERGY, "BZ", 1000),
    _long("GASCMDUSD", "天然氣（長歷史，追蹤很差）", AssetClass.ENERGY, "NG", 10000),
)

UNIVERSES: dict[str, tuple[Instrument, ...]] = {
    "core": CORE,
    "smoke": (CORE[0], CORE[7], CORE[16]),
    "xaut": (XAUT,),
    "longhist": LONGHIST,
}


def by_id(inst_id: str) -> Instrument:
    for universe in UNIVERSES.values():
        for inst in universe:
            if inst.inst_id == inst_id:
                return inst
    raise KeyError(inst_id)
