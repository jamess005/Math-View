"""Function exploration: sliders, and tracing a value through the hops."""

import pytest

from mathview.core.parse import ParseError
from mathview.topics.functions import build


def _titles(sequence):
    return [step.title for step in sequence.steps]


def test_a_plain_function_traces_one_hop():
    sequence = build(["f(x) = 2x + 3"], {"x": 4})

    assert sequence.topic == "functions"
    assert _titles(sequence) == ["The functions as entered", "Input x = 4", "f(4) = 11"]


def test_a_composition_traces_inner_then_outer():
    rows = ["f(x) = 2x", "g(x) = x^2", "h(x) = f(g(x))"]

    sequence = build(rows, {"x": 4})

    assert _titles(sequence)[1:] == ["Input x = 4", "g(4) = 16", "f(16) = 32"]


def test_free_parameters_are_reported_for_sliders():
    sequence = build(["f(x) = a*x^2 + b"], {"x": 1, "a": 1, "b": 0})

    assert sequence.steps[0].visual.data["parameters"] == ["a", "b"]


def test_parameter_values_are_substituted_into_the_curve():
    sequence = build(["f(x) = a*x"], {"x": 3, "a": 5})

    assert sequence.steps[-1].title == "f(3) = 15"


def test_last_row_is_the_one_traced():
    sequence = build(["f(x) = x + 1", "g(x) = x + 100"], {"x": 1})

    assert sequence.steps[-1].title == "g(1) = 101"


def test_an_undefined_point_stops_the_trace_instead_of_crashing():
    # The x slider runs -10 to 10, so sqrt below zero is reached by dragging.
    # This used to raise TypeError: Cannot convert complex to float.
    sequence = build(["f(x) = sqrt(x)"], {"x": -4})

    assert sequence.steps[-1].title == "f(-4) is undefined"


def test_division_by_zero_in_a_trace_is_not_a_crash():
    sequence = build(["f(x) = 1/x"], {"x": 0})

    assert "undefined" in sequence.steps[-1].title


def test_an_undefined_hop_stops_a_composition_early():
    rows = ["f(x) = sqrt(x)", "g(x) = 2x", "h(x) = g(f(x))"]

    sequence = build(rows, {"x": -4})

    assert _titles(sequence) == [
        "The functions as entered",
        "Input x = -4",
        "f(-4) is undefined",
    ]


def test_no_rows_is_a_parse_error():
    with pytest.raises(ParseError):
        build([], {"x": 1})


def test_a_bound_variable_other_than_x_is_not_baked_into_the_curve():
    # parse_definitions accepts any identifier. Substituting the literal "x"
    # instead of the row's own variable plotted f(t) = a*t as a flat line at 15.
    sequence = build(["f(t) = a*t"], {"x": 3, "a": 5})
    points = sequence.steps[0].visual.data["curves"][0]["points"]

    assert points[0][1] == -50.0
    assert points[-1][1] == 50.0
    assert sequence.steps[-1].title == "f(3) = 15"


def test_the_bound_variable_is_not_offered_as_a_slider():
    sequence = build(["f(t) = a*t"], {"x": 3, "a": 5})

    assert sequence.steps[0].visual.data["parameters"] == ["a"]


def test_a_composition_across_different_variable_names():
    rows = ["f(t) = 2t", "g(u) = u^2", "h(v) = f(g(v))"]

    sequence = build(rows, {"x": 4})

    assert _titles(sequence)[2:] == ["g(4) = 16", "f(16) = 32"]


def test_overflow_is_worded_differently_from_undefined():
    # 2^1024 exists and merely exceeds float64, so "check the domain" of 2^x
    # would be false advice.
    rows = ["f(x) = 2^x", "g(x) = 2^x", "h(x) = g(f(x))"]

    sequence = build(rows, {"x": 10})

    assert sequence.steps[-1].title == "g(1024) is too large to show"


def test_a_non_numeric_parameter_is_a_parse_error():
    with pytest.raises(ParseError):
        build(["f(x) = x + 1"], {"x": "banana"})


def test_later_hops_narrate_the_move_back_to_the_x_axis():
    rows = ["f(x) = 2x", "g(x) = x^2", "h(x) = f(g(x))"]

    sequence = build(rows, {"x": 4})

    assert "starts on the x-axis" in sequence.steps[1].prose
    assert "Up from the x-axis" in sequence.steps[2].prose
    assert "becomes the next input" in sequence.steps[3].prose
