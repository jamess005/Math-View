"""Compare how fast functions grow.

Five steps, of which the third carries the weight: asymptotic order tells you
what wins eventually, not what wins at the input size you actually have, and
the crossover is where that distinction becomes visible.
"""

from __future__ import annotations

import math

import sympy

from mathview.core.parse import ParseError, parse_expression
from mathview.core.registry import register_topic
from mathview.core.step import Sequence, Step, VisualSpec
from mathview.topics.asymptotics import classify, compare_growth, dominance_order
from mathview.topics.crossover import find_crossovers, meeting_point
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
                y = meeting_point(expr_a, expr_b, VARIABLE, x)
                if y is None:
                    continue
                markers.append({"kind": "crossover", "x": float(x), "y": y})
                sentences.append(
                    f"{sympy.latex(expr_a)} and {sympy.latex(expr_b)} cross at "
                    f"n = {x:g}."
                )

    # The old wording claimed the asymptotically worse function is faster
    # before a crossing. That is backwards for 2^n against n^2, which is larger
    # than n^2 everywhere before their first crossing at n = 2.
    prose = (
        " ".join(sentences)
        + " Asymptotic order says which function wins eventually;"
        + " a crossing is where eventually begins."
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
    parts = [sympy.latex(ordered[0])]
    for earlier, later in zip(ordered, ordered[1:], strict=False):
        # `n \prec 100n` would be false - they differ only by a constant, so
        # neither ever overtakes the other. Same-order pairs get \sim.
        strict = compare_growth(earlier, later, VARIABLE) < 0
        parts.append((r" \prec " if strict else r" \sim ") + sympy.latex(later))
    return Step(
        index=3,
        title="Dominance chain",
        notation="".join(parts),
        prose=(
            "Slowest-growing first. ≺ means eventually overtaken; "
            "∼ means the same order, differing only by a constant factor."
        ),
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
    if not math.isfinite(n_max) or n_max <= 0:
        # n is an input size. A zero or negative range produced a degenerate
        # plot and reported the bisection tolerance (1e-09) as a real crossing.
        raise ParseError("the range of n must be greater than zero", 0, "")

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
