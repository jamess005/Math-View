"""Text to SymPy, with errors that point at the character that broke.

Malformed input is the normal case in a maths tool, not an exception, so a
parse failure carries an offset the UI can underline. A stack trace or a
silently empty graph reaching the user is a bug.
"""

from __future__ import annotations

import re

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

# parse_expr() calls eval(), so the namespace it evaluates against is the
# security boundary. Sympy's own docs warn against running it on unsanitised
# input, and this module is exactly that - the front door for user-typed text.
# Stripping __builtins__ removes the route to __import__ and the file and
# network primitives behind it. Note Python re-inserts the real builtins into
# any globals dict that lacks the key, so setting it explicitly to {} is
# required - omitting the key is NOT the same thing.
_SAFE_GLOBALS: dict[str, object] = {
    name: getattr(sympy, name) for name in dir(sympy) if not name.startswith("_")
}
_SAFE_GLOBALS["__builtins__"] = {}

# Anything of the form `name(` in user text.
_CALL = re.compile(r"\b([A-Za-z]\w*)\s*\(")


class ParseError(Exception):
    """A parse failure the UI can render against the input box."""

    def __init__(self, message: str, offset: int, text: str) -> None:
        super().__init__(message)
        self.message = message
        self.offset = offset
        self.text = text

    def to_dict(self) -> dict[str, object]:
        return {"error": self.message, "offset": self.offset, "input": self.text}


def parse_expression(
    text: str, variable: str, functions: dict[str, object] | None = None
) -> sympy.Expr:
    """Parse `text` into a SymPy expression, raising ParseError on failure.

    `functions` names the user-defined functions that may be called. Declaring
    them matters: with `g` unknown, the implicit-multiplication transformation
    reads `g(x)` as `g * x`, so `f(g(x))` silently becomes `f*g*x` and
    composition is impossible. Anything called but neither declared here nor a
    known SymPy name is rejected rather than quietly turned into a product.
    """
    stripped = text.strip()
    if not stripped:
        raise ParseError("empty expression", 0, text)

    known = functions or {}
    for match in _CALL.finditer(stripped):
        name = match.group(1)
        if name not in known and name not in _SAFE_GLOBALS:
            raise ParseError(
                f"no function named {name} is defined yet", match.start(1), text
            )

    try:
        expr = sympy.parsing.sympy_parser.parse_expr(
            stripped,
            transformations=TRANSFORMS,
            global_dict=_SAFE_GLOBALS,
            local_dict=dict(known),
            evaluate=True,
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
    except Exception as exc:
        # parse_expr is an eval-based third-party parser and its failure
        # vocabulary is not a stable contract: unmatched parentheses alone
        # raise tokenize.TokenError and IndexError, neither a SyntaxError
        # subclass. Enumerating types means the next unlisted one reaches the
        # user as a stack trace, so catch broadly and convert.
        raise ParseError(str(exc) or "could not parse expression", 0, text) from exc

    if not isinstance(expr, sympy.Expr):
        raise ParseError("that is not an expression", 0, text)

    return expr


def free_parameters(expr: sympy.Expr, variable: str) -> list[str]:
    """Symbol names in `expr` other than the bound variable, sorted."""
    bound = sympy.Symbol(variable)
    return sorted(str(s) for s in expr.free_symbols if s != bound)
