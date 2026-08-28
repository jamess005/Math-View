"""The five-step growth comparison sequence."""

import pytest

from mathview.core.parse import ParseError
from mathview.topics.growth import MAX_ROWS, build


def _titles(sequence):
    return [step.title for step in sequence.steps]


def test_sequence_has_the_five_named_steps():
    sequence = build(["n", "n^2"], {})

    assert sequence.topic == "growth"
    assert _titles(sequence) == [
        "The functions as entered",
        "Evaluated small",
        "Crossover points",
        "Dominance chain",
        "Big-O classification",
    ]


def test_first_step_has_notation_and_a_plot():
    sequence = build(["n", "n^2"], {})
    first = sequence.steps[0]

    assert first.notation is not None
    assert first.visual is not None
    assert first.visual.kind == "plot2d"
    assert len(first.visual.data["curves"]) == 2


def test_curves_take_palette_slots_in_row_order():
    sequence = build(["n", "n^2", "2^n"], {})
    curves = sequence.steps[0].visual.data["curves"]

    assert [c["slot"] for c in curves] == [0, 1, 2]


def test_crossover_step_marks_the_known_crossing():
    sequence = build(["100n", "n^2"], {"n_max": 200})
    crossover_step = sequence.steps[2]

    markers = crossover_step.visual.data["markers"]
    assert any(abs(m["x"] - 100.0) < 1e-6 for m in markers)
    assert "100" in crossover_step.prose


def test_dominance_chain_orders_slowest_first():
    sequence = build(["2^n", "n", "n^2"], {})

    assert sequence.steps[3].notation == r"n \prec n^{2} \prec 2^{n}"


def test_big_o_step_classifies_each_row():
    sequence = build(["3n^2 + 5n"], {})

    assert "n^2" in sequence.steps[4].prose


def test_identical_functions_produce_no_crossover_markers():
    # Comparing a function against itself is a plausible slip in a row-based
    # picker. Before the Task 6 fix this produced one marker per scan step.
    sequence = build(["n^2", "n^2"], {})

    assert sequence.steps[2].visual.data["markers"] == []


def test_no_rows_is_a_parse_error():
    with pytest.raises(ParseError):
        build([], {})


def test_too_many_rows_is_a_parse_error():
    with pytest.raises(ParseError):
        build(["n"] * (MAX_ROWS + 1), {})
