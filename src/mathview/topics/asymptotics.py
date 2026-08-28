"""Growth ordering and complexity classification.

Both work through limits of ratios, which is the definition rather than a
heuristic: a grows slower than b exactly when a/b tends to zero, and a is
O(g) exactly when a/g tends to a finite value.
"""

from __future__ import annotations

from functools import cmp_to_key

import sympy


def _ladder(symbol: sympy.Symbol) -> list[tuple[sympy.Expr, str]]:
    """Standard complexity classes, slowest-growing first."""
    return [
        (sympy.Integer(1), "1"),
        (sympy.log(symbol), "log n"),
        (symbol, "n"),
        (symbol * sympy.log(symbol), "n log n"),
        (symbol**2, "n^2"),
        (symbol**3, "n^3"),
        (sympy.Integer(2) ** symbol, "2^n"),
        (sympy.factorial(symbol), "n!"),
    ]


def _ratio_limit(expr_a: sympy.Expr, expr_b: sympy.Expr, symbol: sympy.Symbol):
    try:
        return sympy.limit(expr_a / expr_b, symbol, sympy.oo)
    except (NotImplementedError, ValueError, TypeError, RecursionError):
        return None


def classify(expr: sympy.Expr, variable: str) -> str:
    """The tightest standard class bounding `expr`, as a display label."""
    symbol = sympy.Symbol(variable)
    for candidate, label in _ladder(symbol):
        limit = _ratio_limit(expr, candidate, symbol)
        if limit is None:
            continue
        if limit.is_finite:
            return label
    return "greater than n!"


def dominance_order(exprs: list[sympy.Expr], variable: str) -> list[sympy.Expr]:
    """Sort `exprs` slowest-growing first."""
    symbol = sympy.Symbol(variable)

    def compare(expr_a: sympy.Expr, expr_b: sympy.Expr) -> int:
        limit = _ratio_limit(expr_a, expr_b, symbol)
        if limit is None:
            return 0
        if limit.is_zero:
            return -1
        if limit.is_infinite:
            return 1
        return 0

    return sorted(exprs, key=cmp_to_key(compare))
