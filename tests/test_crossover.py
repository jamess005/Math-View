"""Finding where one growth function overtakes another."""

import sympy

from mathview.topics.crossover import find_crossovers


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
