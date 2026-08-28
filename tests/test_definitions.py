"""Named function rows, and resolving references between them."""

import pytest
import sympy

from mathview.core.parse import ParseError
from mathview.topics.definitions import Definition, expand, parse_definitions


def test_parses_name_variable_and_body():
    definitions = parse_definitions(["f(x) = 2x + 3"])

    assert list(definitions) == ["f"]
    assert definitions["f"] == Definition(
        name="f", variable="x", body=2 * sympy.Symbol("x") + 3
    )


def test_a_row_without_equals_is_a_parse_error():
    with pytest.raises(ParseError) as excinfo:
        parse_definitions(["2x + 3"])

    assert "name" in excinfo.value.message


def test_a_malformed_left_hand_side_is_a_parse_error():
    with pytest.raises(ParseError):
        parse_definitions(["f = 2x"])


def test_expand_resolves_a_composition():
    definitions = parse_definitions(["f(x) = 2x", "g(x) = x^2", "h(x) = f(g(x))"])
    x = sympy.Symbol("x")

    assert expand(definitions["h"].body, definitions) == 2 * x**2


def test_expand_resolves_three_levels():
    rows = ["f(x) = 2x", "g(x) = x^2", "h(x) = x + 1", "k(x) = f(g(h(x)))"]
    definitions = parse_definitions(rows)
    x = sympy.Symbol("x")

    assert expand(definitions["k"].body, definitions) == 2 * (x + 1) ** 2


def test_a_forward_reference_is_rejected():
    # Rows may only call names defined above them, so this cannot silently
    # become the product h = f * x.
    with pytest.raises(ParseError):
        parse_definitions(["h(x) = f(x)", "f(x) = 2x"])


def test_a_self_reference_is_rejected():
    with pytest.raises(ParseError):
        parse_definitions(["f(x) = f(x)"])


def test_sympy_functions_are_still_callable():
    definitions = parse_definitions(["f(x) = sqrt(x) + log(x)"])
    x = sympy.Symbol("x")

    assert definitions["f"].body == sympy.sqrt(x) + sympy.log(x)


def test_a_parameter_is_not_mistaken_for_a_function():
    definitions = parse_definitions(["f(x) = a*x^2 + b"])
    x, a, b = sympy.symbols("x a b")

    assert definitions["f"].body == a * x**2 + b


def test_no_rows_is_a_parse_error():
    with pytest.raises(ParseError):
        parse_definitions([])


def test_a_builtin_name_cannot_be_redefined():
    # SymPy's parser rewrites bare identifiers into Symbol(...) calls, so a row
    # named Symbol intercepts those and corrupts every other row's parse.
    with pytest.raises(ParseError):
        parse_definitions(["Symbol(x) = x^2", "g(x) = x + 1"])


def test_shadowing_a_sympy_function_is_rejected():
    with pytest.raises(ParseError):
        parse_definitions(["log(x) = x^2"])


def test_a_repeated_name_is_rejected():
    # Keeping only the last would retroactively change what earlier rows mean:
    # g, written against f(x) = x, would expand using f(x) = 2x.
    with pytest.raises(ParseError):
        parse_definitions(["f(x) = x", "g(x) = f(x) + 1", "f(x) = 2x"])


def test_deep_nesting_is_not_reported_as_a_circle():
    # 17 strictly acyclic levels used to hit a fixed bound of 16 and be
    # reported as a circular reference.
    rows = ["f1(x) = x + 1"] + [f"f{i}(x) = f{i - 1}(x) + 1" for i in range(2, 18)]
    definitions = parse_definitions(rows)

    assert expand(definitions["f17"].body, definitions) == sympy.Symbol("x") + 17
