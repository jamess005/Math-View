"""Compare how fast functions grow.

Five steps, of which the third carries the weight: asymptotic order tells you
what wins eventually, not what wins at the input size you actually have, and
the crossover is where that distinction becomes visible.
"""

from __future__ import annotations

import sympy

from mathview.core.parse import ParseError, parse_expression
from mathview.core.registry import register_topic
from mathview.core.step import Sequence, Step, VisualSpec
from mathview.topics.asymptotics import classify, dominance_order
from mathview.topics.crossover import find_crossovers
from mathview.topics.sampling import sample_curve

VARIABLE = "n"
MAX_ROWS = 6  # one per palette series slot
SMALL_VALUES = (1, 5, 10, 20)


def _parse_rows(rows: list[str]) -> list[tuple[str, sympy.Expr]]:
    if not rows:
        raise ParseError("enter at least one function", 0, "")
    if len(rows) > MAX_ROWS:
        raise ParseError(f"at most {MAX_ROWS} functions can be compared", 0, "")
    return [(row, parse_expression(row, VARIABLE)) for row in rows]


def _plot(
    parsed: list[tuple[str, sympy.Expr]],
    n_max: float,
    markers: list[dict] | None = None,
    shaded: list[dict] | None = None,
) -> VisualSpec:
    curves = [
        {
            "label": sympy.latex(expr),
            "slot": slot,
            "points": sample_curve(expr, VARIABLE, 0.0, n_max),
        }
        for slot, (_, expr) in enumerate(parsed)
    ]
    return VisualSpec(
        kind="plot2d",
        data={
            "curves": curves,
            "markers": markers or [],
            "shaded": shaded or [],
            "xlabel": "n",
            "ylabel": "operations",
            "xrange": [0.0, n_max],
        },
    )


def _step_entered(parsed, n_max) -> Step:
    notation = r" \quad ".join(sympy.latex(expr) for _, expr in parsed)
    return Step(
        index=0,
        title="The functions as entered",
        notation=notation,
        prose="Each function plotted over the same range of n.",
        visual=_plot(parsed, n_max),
    )


def _step_small(parsed, n_max) -> Step:
    header = " & ".join(["n", *[sympy.latex(expr) for _, expr in parsed]])
    body_rows = []
    for value in SMALL_VALUES:
        cells = [str(value)]
        for _, expr in parsed:
            evaluated = expr.subs(sympy.Symbol(VARIABLE), value)
            cells.append(sympy.latex(sympy.nsimplify(evaluated).evalf(6)))
        body_rows.append(" & ".join(cells))
    columns = "c" * (len(parsed) + 1)
    table = (
        r"\begin{array}{" + columns + "}" + header + r" \\ \hline "
        + r" \\ ".join(body_rows) + r"\end{array}"
    )
    return Step(
        index=1,
        title="Evaluated small",
        notation=table,
        prose="At small n the difference is often invisible. That is the trap.",
        visual=_plot(parsed, n_max),
    )


def _step_crossovers(parsed, n_max) -> Step:
    markers: list[dict] = []
    sentences: list[str] = []
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            _, expr_a = parsed[i]
            _, expr_b = parsed[j]
            for x in find_crossovers(expr_a, expr_b, VARIABLE, 0.5, n_max):
                y = expr_a.subs(sympy.Symbol(VARIABLE), x)
                markers.append({"kind": "crossover", "x": float(x), "y": float(y)})
                sentences.append(
                    f"{sympy.latex(expr_a)} and {sympy.latex(expr_b)} cross at "
                    f"n = {x:g}."
                )

    prose = (
        " ".join(sentences)
        + " Before a crossing, the asymptotically worse function is the faster one."
        if sentences
        else "These functions do not cross in this range."
    )
    return Step(
        index=2,
        title="Crossover points",
        notation=None,
        prose=prose,
        visual=_plot(parsed, n_max, markers=markers),
    )


def _step_dominance(parsed, n_max) -> Step:
    ordered = dominance_order([expr for _, expr in parsed], VARIABLE)
    chain = r" \prec ".join(sympy.latex(expr) for expr in ordered)
    return Step(
        index=3,
        title="Dominance chain",
        notation=chain,
        prose="Slowest-growing first. Each is eventually overtaken by the next.",
        visual=_plot(parsed, n_max),
    )


def _step_classification(parsed, n_max) -> Step:
    lines = [
        rf"{sympy.latex(expr)} \in O({classify(expr, VARIABLE)})" for _, expr in parsed
    ]
    return Step(
        index=4,
        title="Big-O classification",
        notation=r" \\ ".join(lines),
        prose="  ".join(
            f"{row} is O({classify(expr, VARIABLE)})." for row, expr in parsed
        ),
        visual=_plot(parsed, n_max),
    )


def build(rows: list[str], params: dict[str, float]) -> Sequence:
    """Build the five-step growth comparison sequence."""
    parsed = _parse_rows(rows)
    n_max = float(params.get("n_max", 50))

    return Sequence(
        topic="growth",
        steps=(
            _step_entered(parsed, n_max),
            _step_small(parsed, n_max),
            _step_crossovers(parsed, n_max),
            _step_dominance(parsed, n_max),
            _step_classification(parsed, n_max),
        ),
    )


register_topic("growth", build)
