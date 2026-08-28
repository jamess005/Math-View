"""Parsing, and the errors that point at what broke."""

import pytest
import sympy

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
    with pytest.raises(ParseError):
        parse_expression('__import__("os").getpid()', "n")
