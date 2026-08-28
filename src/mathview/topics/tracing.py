"""Walking a value through a chain of nested calls.

Tracing a composition is one concern: resolve which names are called,
innermost first, then decide what each hop's result actually is - a real
number, or none, with a reason. That is separate from plotting a curve or
assembling steps for display, so it lives here rather than in functions.py.
"""

from __future__ import annotations

import math

import sympy
from sympy.core.function import AppliedUndef

from mathview.topics.definitions import Definition


def call_chain(body: sympy.Expr, definitions: dict[str, Definition]) -> list[str]:
    """Names in a nested call like f(g(x)), innermost first."""
    chain: list[str] = []
    node = body
    while (
        isinstance(node, AppliedUndef)
        and node.func.__name__ in definitions
        and len(node.args) == 1
    ):
        chain.append(node.func.__name__)
        node = node.args[0]
    return list(reversed(chain))


def real_value(expr: sympy.Expr) -> tuple[float | None, str]:
    """`expr` as a real number, or None with a phrase saying why not.

    The two cases are genuinely different and must not share wording: sqrt(-4)
    has no real value at all, while 2^1024 has one and merely exceeds float64.
    Telling someone to "check the domain" of 2^x is false advice.

    Tracing a value through a function lands on undefined points constantly:
    the x slider runs -10 to 10, so sqrt(x) below zero and 1/x at zero are
    reached by ordinary dragging. subs() returns a complex number or zoo there
    and float() raises, so every one of those was a crash.
    """
    # An infinity that SymPy produced exactly - zoo from 1/0, -oo from log(0) -
    # means the point is outside the domain, not that the answer is merely big.
    if expr.has(sympy.zoo, sympy.nan) or expr.is_infinite:
        return None, "is undefined"
    try:
        number = complex(expr)
    except OverflowError:
        # A finite value SymPy holds exactly but float64 cannot: 2^1024 exists.
        return None, "is too large to show"
    except (TypeError, ValueError):
        return None, "is undefined"
    if abs(number.imag) > 1e-12:
        return None, "is undefined"
    if not math.isfinite(number.real):
        return None, "is too large to show"
    return number.real, ""
