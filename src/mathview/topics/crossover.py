"""Where one function overtakes another.

Numeric, not symbolic: sympy.solve either fails or returns Lambert-W forms for
the mixed exponential/polynomial comparisons that matter most here. Scanning
for a sign change in (a - b) and bisecting always terminates and always yields
a number the UI can put a marker on.
"""

from __future__ import annotations

import math

import sympy

_SCAN_STEPS = 600
_BISECT_STEPS = 60
_TOLERANCE = 1e-9


def _difference(expr_a: sympy.Expr, expr_b: sympy.Expr, variable: str):
    symbol = sympy.Symbol(variable)
    func = sympy.lambdify(symbol, expr_a - expr_b, "math")

    def evaluate(x: float) -> float | None:
        try:
            value = float(func(x))
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            return None
        return value if math.isfinite(value) else None

    return evaluate


def _bisect(evaluate, low: float, high: float) -> float:
    low_value = evaluate(low)
    for _ in range(_BISECT_STEPS):
        middle = (low + high) / 2
        middle_value = evaluate(middle)
        if middle_value is None or abs(middle_value) < _TOLERANCE:
            return middle
        if (middle_value > 0) == (low_value is not None and low_value > 0):
            low, low_value = middle, middle_value
        else:
            high = middle
    return (low + high) / 2


def find_crossovers(
    expr_a: sympy.Expr,
    expr_b: sympy.Expr,
    variable: str,
    start: float,
    stop: float,
) -> list[float]:
    """Points in [start, stop] where `expr_a` and `expr_b` cross, ascending."""
    evaluate = _difference(expr_a, expr_b, variable)
    step = (stop - start) / _SCAN_STEPS

    crossings: list[float] = []
    previous_x = start
    previous = evaluate(start)
    for i in range(1, _SCAN_STEPS + 1):
        x = start + step * i
        current = evaluate(x)
        if previous is not None and current is not None:
            if previous == 0.0:
                crossings.append(previous_x)
            elif (previous > 0) != (current > 0):
                crossings.append(round(_bisect(evaluate, previous_x, x), 9))
        previous_x, previous = x, current

    return crossings
