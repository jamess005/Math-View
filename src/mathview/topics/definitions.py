"""Named function rows: `f(x) = 2x + 3`, and references between them.

Naming rows is what makes composition writable directly - `h(x) = f(g(x))` -
rather than needing a separate composition UI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy
from sympy.core.function import AppliedUndef

from mathview.core.parse import ParseError, parse_expression

_LHS = re.compile(r"^\s*([A-Za-z]\w*)\s*\(\s*([A-Za-z]\w*)\s*\)\s*$")

# Bounds substitution so a cycle terminates with an error instead of hanging.
# parse_definitions only lets a row call names defined on earlier rows, so the
# reference graph it produces is a DAG and a cycle can't reach this guard that
# way; it stays as defence for a Definition dict built by hand rather than
# through parse_definitions.
_MAX_EXPANSIONS = 16


@dataclass(frozen=True)
class Definition:
    name: str
    variable: str
    body: sympy.Expr


def parse_definitions(rows: list[str]) -> dict[str, Definition]:
    """Parse `name(var) = body` rows, in order, into a name-keyed mapping."""
    if not rows:
        raise ParseError("enter at least one definition", 0, "")

    definitions: dict[str, Definition] = {}
    for row in rows:
        if "=" not in row:
            raise ParseError(
                "give the function a name, like f(x) = 2x + 3", 0, row
            )
        left, _, right = row.partition("=")
        match = _LHS.match(left)
        if match is None:
            raise ParseError("the left side must look like f(x)", 0, row)

        name, variable = match.group(1), match.group(2)
        # Only names defined on EARLIER rows are callable here. That ordering is
        # what makes a forward reference an error rather than a silent product:
        # with `g` undeclared, implicit multiplication reads `g(x)` as `g * x`.
        known = {defined: sympy.Function(defined) for defined in definitions}
        definitions[name] = Definition(
            name=name,
            variable=variable,
            body=parse_expression(right, variable, known),
        )
    return definitions


def expand(expr: sympy.Expr, definitions: dict[str, Definition]) -> sympy.Expr:
    """Replace every call to a defined name with that definition's body."""
    for _ in range(_MAX_EXPANSIONS):
        calls = [
            call
            for call in expr.atoms(AppliedUndef)
            if call.func.__name__ in definitions and len(call.args) == 1
        ]
        if not calls:
            return expr
        for call in calls:
            definition = definitions[call.func.__name__]
            substituted = definition.body.subs(
                sympy.Symbol(definition.variable), call.args[0]
            )
            expr = expr.subs(call, substituted)

    raise ParseError(
        "these definitions refer to each other in a circle", 0, str(expr)
    )
