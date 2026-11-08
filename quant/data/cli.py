from __future__ import annotations

import argparse
import sys

from quant.data.store import sync
from quant.data.universe import UNIVERSES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download OKX 5m candles and funding history")
    parser.add_argument("--universe", default="core", choices=sorted(UNIVERSES))
    parser.add_argument("--only", nargs="*", default=None, help="instrument codes, e.g. XAU SPY")
    args = parser.parse_args(argv)
    failures = 0
    for inst in UNIVERSES[args.universe]:
        if args.only and inst.inst_id.split("-")[0] not in args.only:
            continue
        try:
            bars = sync(inst)
        except Exception as exc:
            failures += 1
            print(f"FAIL {inst.inst_id}: {exc}", flush=True)
            continue
        print(
            f"ok   {inst.inst_id:16s} {len(bars):7d} bars  {bars.index[0]} -> {bars.index[-1]}",
            flush=True,
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
