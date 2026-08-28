"""Turning an expression into points the frontend can stroke.

Growth functions overflow fast - 2**n leaves float range around n = 1024 - and
log is undefined at or below zero, so a sampler that raises on either would be
useless here. Both cases become a `None` y, which the renderer draws as a gap.
"""

from __future__ import annotations

import math

import sympy

# Beyond this the frontend's scaling stops being meaningful, and float64 is
# about to overflow anyway.
_MAX_MAGNITUDE = 1e300


def _finite_or_none(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or abs(number) > _MAX_MAGNITUDE:
        return None
    return number


def sample_curve(
    expr: sympy.Expr,
    variable: str,
    start: float,
    stop: float,
    count: int = 240,
) -> list[list[float | None]]:
    """Evaluate `expr` at `count` evenly spaced points across [start, stop]."""
    symbol = sympy.Symbol(variable)
    func = sympy.lambdify(symbol, expr, "math")

    step = (stop - start) / (count - 1) if count > 1 else 0.0
    points: list[list[float | None]] = []
    for i in range(count):
        x = start + step * i
        try:
            y = _finite_or_none(func(x))
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            y = None
        points.append([x, y])
    return points
