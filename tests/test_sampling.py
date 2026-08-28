"""Sampling expressions into plottable points, including the overflow cases."""

import sympy

from mathview.topics.sampling import sample_curve


def test_samples_include_both_endpoints():
    n = sympy.Symbol("n")

    points = sample_curve(n**2, "n", 0.0, 10.0, count=11)

    assert len(points) == 11
    assert points[0] == [0.0, 0.0]
    assert points[-1] == [10.0, 100.0]


def test_overflowing_values_become_none_gaps():
    n = sympy.Symbol("n")

    points = sample_curve(2**n, "n", 0.0, 2000.0, count=5)

    assert points[0][1] == 1.0
    assert points[-1][1] is None


def test_undefined_regions_become_none_gaps():
    n = sympy.Symbol("n")

    points = sample_curve(sympy.log(n), "n", -1.0, 1.0, count=3)

    assert points[0][1] is None
    assert points[-1][1] == 0.0


def test_division_by_zero_becomes_a_gap():
    n = sympy.Symbol("n")

    points = sample_curve(1 / n, "n", 0.0, 2.0, count=3)

    assert points[0] == [0.0, None]
    assert points[-1][1] == 0.5
