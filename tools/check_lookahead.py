from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

STRATEGY_DIR = Path(__file__).resolve().parents[1] / "quant" / "strategies"
BACKFILL_METHODS = {"bfill", "backfill"}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _negative(node: ast.expr) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return True
    return isinstance(node, ast.Constant) and isinstance(node.value, int | float) and node.value < 0


def check_source(source: str, path: Path) -> list[Violation]:
    found: list[Violation] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        name = node.func.attr
        line = node.lineno
        if name == "shift" and node.args and _negative(node.args[0]):
            found.append(
                Violation(
                    path,
                    line,
                    "shift(-n) reads future bars. Strategies see only "
                    "the past; the engine already executes at the next open.",
                )
            )
        if name == "shift" and any(
            k.arg == "periods" and _negative(k.value) for k in node.keywords
        ):
            found.append(Violation(path, line, "shift(periods=-n) reads future bars."))
        if name in BACKFILL_METHODS:
            found.append(
                Violation(
                    path,
                    line,
                    f".{name}() copies future values backwards. Use ffill() or fillna(0.0).",
                )
            )
        for keyword in node.keywords:
            if keyword.arg == "center" and not (
                isinstance(keyword.value, ast.Constant) and keyword.value.value is False
            ):
                found.append(Violation(path, line, "rolling(center=True) uses future bars."))
            if (
                keyword.arg == "method"
                and isinstance(keyword.value, ast.Constant)
                and (keyword.value.value in BACKFILL_METHODS)
            ):
                found.append(Violation(path, line, "fillna(method='bfill') copies future values."))
    return found


def main(paths: list[str]) -> int:
    targets = [Path(p) for p in paths] or sorted(STRATEGY_DIR.rglob("*.py"))
    violations = [v for p in targets for v in check_source(p.read_text(), p)]
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
