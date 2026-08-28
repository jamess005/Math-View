"""Explore a function: plot it, and walk a value through it.

The last row entered is the one traced, so adding `h(x) = f(g(x))` under two
existing rows switches the trace to the composition without any extra control.
"""

from __future__ import annotations

import sympy

from mathview.core.parse import ParseError, free_parameters
from mathview.core.registry import register_topic
from mathview.core.step import Sequence, Step, VisualSpec
from mathview.topics.definitions import Definition, expand, parse_definitions
from mathview.topics.sampling import sample_curve
from mathview.topics.tracing import call_chain, real_value

X_RANGE = (-10.0, 10.0)


def _substitute_parameters(
    expr: sympy.Expr, variable: str, params: dict[str, float]
) -> sympy.Expr:
    """Bake slider values into `expr`, leaving the row's own variable free.

    It must be the row's variable, not the literal "x": parse_definitions
    accepts any identifier, so `f(t) = a*t` with the slider at t=3 baked t in
    too and plotted a flat line at 15 instead of a line through the origin.
    """
    for name, value in params.items():
        if name != variable:
            expr = expr.subs(sympy.Symbol(name), sympy.Float(value))
    return expr


def _numeric_params(params: dict[str, float]) -> dict[str, float]:
    """Coerce slider values to floats, as a ParseError rather than a traceback."""
    numeric: dict[str, float] = {}
    for name, value in params.items():
        try:
            numeric[name] = float(value)
        except (TypeError, ValueError):
            raise ParseError(f"{name} must be a number", 0, str(value)) from None
    return numeric


def _plot(
    definitions: dict[str, Definition], params: dict[str, float], markers: list[dict]
) -> VisualSpec:
    curves = []
    parameter_names: set[str] = set()
    for slot, definition in enumerate(definitions.values()):
        resolved = _substitute_parameters(
            expand(definition.body, definitions), definition.variable, params
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
    params = _numeric_params(params)
    x_value = params.get("x", 0.0)

    traced = list(definitions.values())[-1]
    chain = call_chain(traced.body, definitions) or [traced.name]

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
            expand(definition.body, definitions), definition.variable, params
        )
        previous = value
        result, reason = real_value(
            body.subs(sympy.Symbol(definition.variable), previous)
        )
        if result is None:
            steps.append(
                Step(
                    index=hop,
                    title=f"{name}({previous:g}) {reason}",
                    notation=rf"{name}({previous:g}) \notin \mathbb{{R}}",
                    prose=(
                        f"{name}({previous:g}) {reason}, so the trace stops here."
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
                prose=(
                    f"Up from the x-axis to the curve of {name}, then across to "
                    f"the y-axis."
                    if hop == 2
                    else f"That result becomes the next input: across to the "
                    f"x-axis, up to the curve of {name}, then back to the y-axis."
                ),
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
