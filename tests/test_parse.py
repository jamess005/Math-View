"""Parsing, and the errors that point at what broke."""

import pytest
import sympy
from sympy.core.function import AppliedUndef

from mathview.core.parse import ParseError, free_parameters, parse_expression


def test_caret_means_power():
    n = sympy.Symbol("n")

    assert parse_expression("n^2", "n") == n**2


def test_implicit_multiplication():
    n = sympy.Symbol("n")

    assert parse_expression("2n", "n") == 2 * n


def test_log_and_products_parse():
    n = sympy.Symbol("n")

    assert parse_expression("n*log(n)", "n") == n * sympy.log(n)


def test_empty_input_is_a_parse_error_at_offset_zero():
    with pytest.raises(ParseError) as excinfo:
        parse_expression("   ", "n")

    assert excinfo.value.offset == 0
    assert excinfo.value.to_dict()["error"] == "empty expression"


def test_malformed_input_reports_an_offset_inside_the_string():
    text = "n^^2"

    with pytest.raises(ParseError) as excinfo:
        parse_expression(text, "n")

    error = excinfo.value
    assert 0 <= error.offset < len(text)
    assert error.to_dict()["input"] == text


def test_free_parameters_excludes_the_bound_variable():
    expr = parse_expression("a*x^2 + b", "x")

    assert free_parameters(expr, "x") == ["a", "b"]


def test_free_parameters_is_empty_for_a_plain_function():
    expr = parse_expression("x^2", "x")

    assert free_parameters(expr, "x") == []


def test_unmatched_parentheses_are_parse_errors_not_crashes():
    for text in ["(1+2", "1+2)", "((n"]:
        with pytest.raises(ParseError):
            parse_expression(text, "n")


def test_builtins_are_not_reachable_from_parsed_input():
    # The bare call returns an int, which the isinstance guard would reject for
    # reasons unrelated to security - so it proves nothing. Wrapping it to
    # return a clean Symbol gets it past that guard, leaving the stripped
    # __builtins__ as the only thing standing between user text and eval.
    with pytest.raises(ParseError):
        parse_expression('n + __import__("os").getpid()*0', "n")


def test_a_declared_function_parses_as_a_call_not_a_product():
    # Without local_dict the implicit-multiplication transformation reads
    # g(x) as g*x, so f(g(x)) becomes f*g*x and composition is impossible.
    known = {"f": sympy.Function("f"), "g": sympy.Function("g")}

    expr = parse_expression("f(g(x))", "x", known)

    assert expr.atoms(AppliedUndef) == {expr, sympy.Function("g")(sympy.Symbol("x"))}


def test_calling_an_undefined_function_is_rejected():
    with pytest.raises(ParseError) as excinfo:
        parse_expression("f(g(x))", "x", {"f": sympy.Function("f")})

    assert "g" in excinfo.value.message
    assert excinfo.value.offset == 2


def test_a_digit_prefixed_call_is_still_checked():
    # `\b` is not a boundary between two word characters, and a digit is one,
    # so `2f(x)` hid the call entirely and became the product 2*f*x.
    with pytest.raises(ParseError):
        parse_expression("2f(x)", "x")


def test_non_callable_sympy_names_are_rejected():
    # pi, E, I, oo and nan are all names in SymPy's namespace but none are
    # callable; nan(x) quietly became nan, dropping the argument entirely.
    for text in ["E(x)", "pi(x)", "nan(x)", "oo(x)"]:
        with pytest.raises(ParseError):
            parse_expression(text, "x")


def test_bracket_errors_are_readable():
    # tokenize.TokenError stringifies as a raw Python tuple, and the API hands
    # this message straight to the UI.
    for text in ["(1+2", "1+2)", "((n", "sqrt(x"]:
        with pytest.raises(ParseError) as excinfo:
            parse_expression(text, "n")

        assert excinfo.value.message == "check the brackets - they do not match"
