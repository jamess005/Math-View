"""Finding where one growth function overtakes another."""

import sympy

from mathview.topics.crossover import find_crossovers, meeting_point


def test_quadratic_overtakes_linear_at_the_known_point():
    n = sympy.Symbol("n")

    crossings = find_crossovers(n**2, 100 * n, "n", 1.0, 200.0)

    assert len(crossings) == 1
    assert crossings[0] == 100.0


def test_parallel_functions_never_cross():
    n = sympy.Symbol("n")

    assert find_crossovers(n, n + 5, "n", 1.0, 100.0) == []


def test_exponential_and_quadratic_cross_twice():
    n = sympy.Symbol("n")

    crossings = find_crossovers(2**n, n**2, "n", 1.0, 20.0)

    # 2^2 = 2^2 = 4 and 2^4 = 4^2 = 16, so they are equal at n = 2 AND n = 4.
    # Between those two points the quadratic is the larger of the pair; only
    # after n = 4 does the exponential pull away for good. Verified against
    # SymPy before this plan was written.
    assert crossings == [2.0, 4.0]


def test_identical_functions_report_no_crossing():
    # Without the "leaving zero" guard this returns one crossing per scan step -
    # 600 markers smeared across the plot for a plausible user slip.
    n = sympy.Symbol("n")

    assert find_crossovers(n**2, n**2, "n", 1.0, 50.0) == []


def test_a_crossing_exactly_at_start_is_reported():
    n = sympy.Symbol("n")

    assert find_crossovers(n, sympy.Integer(5), "n", 5.0, 15.0) == [5.0]


def test_a_crossing_exactly_at_stop_is_reported():
    # The asymmetric case: a zero at `stop` never becomes `previous`.
    n = sympy.Symbol("n")

    assert find_crossovers(n, sympy.Integer(15), "n", 5.0, 15.0) == [15.0]


def test_meeting_point_rejects_a_pole():
    # find_crossovers reports the sign change across 1/(n-1)'s asymptote; the
    # curves are nowhere near each other there, so it is not a meeting point.
    n = sympy.Symbol("n")

    assert meeting_point(1 / (n - 1), sympy.Integer(1), "n", 1.0) is None


def test_meeting_point_returns_the_shared_y_where_curves_really_meet():
    n = sympy.Symbol("n")

    assert meeting_point(n**2, 100 * n, "n", 100.0) == 10000.0
