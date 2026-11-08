from __future__ import annotations

import io
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNED = ("quant", "tools", "tests")


def comments(source: str) -> list[tuple[int, str]]:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return [(t.start[0], t.string) for t in tokens if t.type == tokenize.COMMENT]


def main(paths: list[str]) -> int:
    targets = [Path(p) for p in paths] or [
        p for d in SCANNED for p in sorted((ROOT / d).rglob("*.py"))
    ]
    found = 0
    for path in targets:
        for line, text in comments(path.read_text()):
            found += 1
            print(
                f"{path}:{line}: comment {text!r}. Agents copy comments as rules. "
                "Make the code say it (rename, extract, type), "
                "or encode the constraint as a test or check."
            )
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
