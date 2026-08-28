"""Growth ordering and complexity classification.

Both work through limits of ratios, which is the definition rather than a
heuristic: a grows slower than b exactly when a/b tends to zero, and a is
O(g) exactly when a/g tends to a finite value.
"""

from __future__ import annotations

from functools import cmp_to_key

import sympy

_MAX_POLY_DEGREE = 10


def _ladder(symbol: sympy.Symbol) -> list[tuple[sympy.Expr, str]]:
    """Standard complexity classes, slowest-growing first.

    The polynomial rungs run one degree at a time up to _MAX_POLY_DEGREE rather
    than jumping n^3 -> 2^n. classify() returns the FIRST rung with a finite
    ratio limit, so a gap there is not merely imprecise: with no n^4 rung,
    n^4 skips n^3 (ratio -> oo) and lands on 2^n, telling a student that a
    quartic algorithm is exponential-class. True, and badly misleading.
    """
    polynomials = [
        (symbol**power, "n" if power == 1 else f"n^{power}")
        for power in range(1, _MAX_POLY_DEGREE + 1)
    ]
    return [
        (sympy.Integer(1), "1"),
        (sympy.log(symbol), "log n"),
        polynomials[0],
        (symbol * sympy.log(symbol), "n log n"),
        *polynomials[1:],
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
            # Known limitation: treating "SymPy could not decide" as "same
            # order" makes the comparator non-transitive, so the result can
            # depend on the order the caller listed the functions in. Every
            # standard complexity class resolves symbolically, so this cannot
            # fire for the inputs this topic is for; a numeric fallback was
            # prototyped and rejected because it could not reliably separate
            # O(1) from O(log n) without probing absurdly far out.
            return 0
        if limit.is_zero:
            return -1
        if limit.is_infinite:
            return 1
        return 0

    return sorted(exprs, key=cmp_to_key(compare))
