"""Text to SymPy, with errors that point at the character that broke.

Malformed input is the normal case in a maths tool, not an exception, so a
parse failure carries an offset the UI can underline. A stack trace or a
silently empty graph reaching the user is a bug.
"""

from __future__ import annotations

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    standard_transformations,
)

# convert_xor makes `^` mean power, which is what people type;
# implicit_multiplication_application makes `2n` and `n log(n)` work.
TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


class ParseError(Exception):
    """A parse failure the UI can render against the input box."""

    def __init__(self, message: str, offset: int, text: str) -> None:
        super().__init__(message)
        self.message = message
        self.offset = offset
        self.text = text

    def to_dict(self) -> dict[str, object]:
        return {"error": self.message, "offset": self.offset, "input": self.text}


def parse_expression(text: str, variable: str) -> sympy.Expr:
    """Parse `text` into a SymPy expression, raising ParseError on failure."""
    stripped = text.strip()
    if not stripped:
        raise ParseError("empty expression", 0, text)

    try:
        expr = sympy.parsing.sympy_parser.parse_expr(
            stripped, transformations=TRANSFORMS, evaluate=True
        )
    except SyntaxError as exc:
        # The transformations rewrite the source before Python compiles it, so
        # the reported offset is against the rewritten string and can land well
        # past the end of what the user typed - `n^^2` (4 chars) reports offset
        # 16, because convert_xor expands each `^` to `**`. Clamping keeps the
        # caret inside the input; it marks the neighbourhood, not the exact
        # character. Good enough to orient the user, and never out of bounds.
        raw = (exc.offset or 1) - 1
        offset = max(0, min(raw, max(len(text) - 1, 0)))
        raise ParseError(
            f"unexpected syntax near here: {exc.msg}", offset, text
        ) from exc
    except (TypeError, ValueError, AttributeError, RecursionError) as exc:
        raise ParseError(str(exc) or "could not parse expression", 0, text) from exc

    if not isinstance(expr, sympy.Expr):
        raise ParseError("that is not an expression", 0, text)

    _ = sympy.Symbol(variable)  # validates the variable name is usable
    return expr


def free_parameters(expr: sympy.Expr, variable: str) -> list[str]:
    """Symbol names in `expr` other than the bound variable, sorted."""
    bound = sympy.Symbol(variable)
    return sorted(str(s) for s in expr.free_symbols if s != bound)
