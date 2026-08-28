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


def _bisect(evaluate, low: float, low_value: float, high: float) -> float:
    for _ in range(_BISECT_STEPS):
        middle = (low + high) / 2
        middle_value = evaluate(middle)
        if middle_value is None or abs(middle_value) < _TOLERANCE:
            return middle
        if (middle_value > 0) == (low_value > 0):
            low, low_value = middle, middle_value
        else:
            high = middle
    return (low + high) / 2


def meeting_point(
    expr_a: sympy.Expr,
    expr_b: sympy.Expr,
    variable: str,
    x: float,
) -> float | None:
    """The shared y where two curves meet, or None if they do not really meet.

    find_crossovers reports a sign change in (a - b), and that also occurs
    across a pole, where the curves are nowhere near each other: bisection
    lands on the asymptote and subs() returns complex infinity. 1/(n-1)
    against a constant crashed on exactly this. Both sides must be finite AND
    equal there for the candidate to count as a crossing.
    """
    symbol = sympy.Symbol(variable)
    try:
        y_a = float(expr_a.subs(symbol, x))
        y_b = float(expr_b.subs(symbol, x))
    except (TypeError, ValueError, OverflowError):
        return None
    if not (math.isfinite(y_a) and math.isfinite(y_b)):
        return None
    scale = max(1.0, abs(y_a), abs(y_b))
    if abs(y_a - y_b) > 1e-6 * scale:
        return None
    return y_a


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
            # `+ 0.0` throughout normalises -0.0 to 0.0, so a crossing at the
            # origin never renders as "n = -0".
            if previous == 0.0 and current != 0.0:
                # Only when the difference is LEAVING zero. Without that guard,
                # two identical functions report one crossing per scan step.
                crossings.append(previous_x + 0.0)
            elif (previous > 0) != (current > 0):
                crossings.append(
                    round(_bisect(evaluate, previous_x, previous, x), 9) + 0.0
                )
            elif current == 0.0 and i == _SCAN_STEPS and previous != 0.0:
                # A zero exactly at `stop` never becomes `previous`, and `0 > 0`
                # is False so it reads as no sign change against a negative
                # sample either. The right edge needs its own probe.
                crossings.append(x + 0.0)
        previous_x, previous = x, current

    return crossings
