"""Explore a function: plot it, and walk a value through it.

The last row entered is the one traced, so adding `h(x) = f(g(x))` under two
existing rows switches the trace to the composition without any extra control.
"""

from __future__ import annotations

import math

import sympy
from sympy.core.function import AppliedUndef

from mathview.core.parse import ParseError, free_parameters
from mathview.core.registry import register_topic
from mathview.core.step import Sequence, Step, VisualSpec
from mathview.topics.definitions import Definition, expand, parse_definitions
from mathview.topics.sampling import sample_curve

X_RANGE = (-10.0, 10.0)


def _substitute_parameters(expr: sympy.Expr, params: dict[str, float]) -> sympy.Expr:
    for name, value in params.items():
        if name != "x":
            expr = expr.subs(sympy.Symbol(name), sympy.Float(value))
    return expr


def _real_value(expr: sympy.Expr) -> float | None:
    """`expr` as a real number, or None where it has none.

    Tracing a value through a function lands on undefined points constantly:
    the x slider runs -10 to 10, so sqrt(x) below zero and 1/x at zero are
    reached by ordinary dragging. subs() returns a complex number or zoo there
    and float() raises, so every one of those was a crash.
    """
    try:
        number = complex(expr)
    except (TypeError, ValueError, OverflowError):
        return None
    if abs(number.imag) > 1e-12 or not math.isfinite(number.real):
        return None
    return number.real


def _call_chain(body: sympy.Expr, definitions: dict[str, Definition]) -> list[str]:
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


def _plot(
    definitions: dict[str, Definition], params: dict[str, float], markers: list[dict]
) -> VisualSpec:
    curves = []
    parameter_names: set[str] = set()
    for slot, definition in enumerate(definitions.values()):
        resolved = _substitute_parameters(
            expand(definition.body, definitions), params
        )
        parameter_names.update(free_parameters(definition.body, definition.variable))
        curves.append(
            {
                "label": f"{definition.name}({definition.variable})",
                "slot": slot,
                "points": sample_curve(
                    resolved, definition.variable, *X_RANGE
                ),
            }
        )

    return VisualSpec(
        kind="plot2d",
        data={
            "curves": curves,
            "markers": markers,
            "shaded": [],
            "parameters": sorted(
                name for name in parameter_names if name not in definitions
            ),
            "xlabel": "x",
            "ylabel": "y",
            "xrange": list(X_RANGE),
        },
    )


def build(rows: list[str], params: dict[str, float]) -> Sequence:
    """Plot each definition, then trace `x` through the last one."""
    definitions = parse_definitions(rows)
    x_value = float(params.get("x", 0))

    traced = list(definitions.values())[-1]
    chain = _call_chain(traced.body, definitions) or [traced.name]
    if chain == [traced.name] and traced.name not in definitions:
        raise ParseError("nothing to trace", 0, rows[-1])

    steps = [
        Step(
            index=0,
            title="The functions as entered",
            notation=r" \quad ".join(
                rf"{d.name}({d.variable}) = {sympy.latex(d.body)}"
                for d in definitions.values()
            ),
            prose="Drag any slider to change a parameter and watch the curve move.",
            visual=_plot(definitions, params, markers=[]),
        ),
        Step(
            index=1,
            title=f"Input x = {x_value:g}",
            notation=rf"x = {x_value:g}",
            prose="The value starts on the x-axis.",
            visual=_plot(
                definitions, params, markers=[{"kind": "input", "x": x_value, "y": 0.0}]
            ),
        ),
    ]

    value = x_value
    for hop, name in enumerate(chain, start=2):
        definition = definitions[name]
        body = _substitute_parameters(
            expand(definition.body, definitions), params
        )
        previous = value
        result = _real_value(body.subs(sympy.Symbol(definition.variable), previous))
        if result is None:
            steps.append(
                Step(
                    index=hop,
                    title=f"{name}({previous:g}) is undefined",
                    notation=rf"{name}({previous:g}) \notin \mathbb{{R}}",
                    prose=(
                        f"{name} has no real value at {previous:g}, so the trace "
                        f"stops here. Move x, or check the domain."
                    ),
                    visual=_plot(definitions, params, markers=[]),
                )
            )
            break
        value = result
        steps.append(
            Step(
                index=hop,
                title=f"{name}({previous:g}) = {value:g}",
                notation=rf"{name}({previous:g}) = {value:g}",
                prose=f"Up to the curve of {name}, then across to the y-axis.",
                visual=_plot(
                    definitions,
                    params,
                    markers=[
                        {"kind": "hop", "x": previous, "y": value, "label": name}
                    ],
                ),
            )
        )

    return Sequence(topic="functions", steps=tuple(steps))


register_topic("functions", build)
