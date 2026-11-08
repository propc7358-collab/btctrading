from __future__ import annotations

from pathlib import Path

import pytest

from tools import check_lookahead, check_no_comments

LEAKS = {
    "negative shift": "s = close.shift(-1)",
    "negative periods": "s = close.shift(periods=-3)",
    "bfill": "s = close.bfill()",
    "fillna bfill": "s = close.fillna(method='bfill')",
    "centered window": "s = close.rolling(5, center=True).mean()",
}


@pytest.mark.parametrize("snippet", LEAKS.values(), ids=LEAKS.keys())
def test_lookahead_checker_rejects_known_leaks(snippet: str) -> None:
    assert check_lookahead.check_source(snippet, Path("x.py"))


@pytest.mark.parametrize(
    "snippet", ["s = close.shift(1)", "s = close.rolling(5).mean()", "s = close.ffill()"]
)
def test_lookahead_checker_allows_past_only_operations(snippet: str) -> None:
    assert not check_lookahead.check_source(snippet, Path("x.py"))


def test_strategies_directory_has_no_lookahead() -> None:
    assert check_lookahead.main([]) == 0


def test_comment_checker_finds_comments_but_not_strings() -> None:
    source = 'x = "# not a comment"\ny = 1  # a comment\n'
    assert check_no_comments.comments(source) == [(2, "# a comment")]


def test_repository_has_no_comments() -> None:
    assert check_no_comments.main([]) == 0
