"""The one shape everything is displayed as, and its wire format."""

from mathview.core.step import Sequence, Step, VisualSpec


def test_visual_spec_flattens_kind_and_data():
    spec = VisualSpec(kind="plot2d", data={"curves": [], "xrange": [0, 10]})

    assert spec.to_dict() == {"kind": "plot2d", "curves": [], "xrange": [0, 10]}


def test_step_with_no_visual_serialises_none():
    step = Step(index=0, title="The functions as entered", notation=r"n^2")

    assert step.to_dict() == {
        "index": 0,
        "title": "The functions as entered",
        "notation": r"n^2",
        "prose": None,
        "visual": None,
    }


def test_sequence_round_trips_nested_steps():
    step = Step(
        index=1,
        title="Crossover points",
        prose="They cross at n = 100.",
        visual=VisualSpec(kind="plot2d", data={"curves": []}),
    )
    sequence = Sequence(topic="growth", steps=(step,))

    assert sequence.to_dict() == {
        "topic": "growth",
        "steps": [
            {
                "index": 1,
                "title": "Crossover points",
                "notation": None,
                "prose": "They cross at n = 100.",
                "visual": {"kind": "plot2d", "curves": []},
            }
        ],
    }
