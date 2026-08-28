"""Ordering functions by growth, and naming their complexity class."""

import sympy

from mathview.topics.asymptotics import classify, dominance_order


def test_classify_ignores_constant_factors_and_lower_terms():
    n = sympy.Symbol("n")

    assert classify(3 * n**2 + 5 * n, "n") == "n^2"


def test_classify_linear():
    n = sympy.Symbol("n")

    assert classify(100 * n, "n") == "n"


def test_classify_linearithmic():
    n = sympy.Symbol("n")

    assert classify(n * sympy.log(n), "n") == "n log n"


def test_classify_constant():
    assert classify(sympy.Integer(7), "n") == "1"


def test_classify_exponential():
    n = sympy.Symbol("n")

    assert classify(2**n, "n") == "2^n"


def test_dominance_order_sorts_slowest_growing_first():
    n = sympy.Symbol("n")
    exprs = [2**n, n, n**2, sympy.log(n)]

    ordered = dominance_order(exprs, "n")

    assert ordered == [sympy.log(n), n, n**2, 2**n]


def test_classify_quartic_does_not_report_exponential():
    # With a ladder that jumps n^3 -> 2^n, classify() returns the first rung
    # with a finite ratio limit, which for n^4 is 2^n: true, but it tells a
    # student a quartic algorithm is exponential-class.
    n = sympy.Symbol("n")

    assert classify(n**4, "n") == "n^4"


def test_classify_high_degree_polynomial():
    n = sympy.Symbol("n")

    assert classify(n**10, "n") == "n^10"


def test_classify_falls_back_to_a_looser_rung_off_ladder():
    # No fractional rung exists, so n^2.5 is honestly reported as bounded by
    # n^3. Loose but true - unlike the n^4 case, there is no tighter standard
    # class to offer.
    n = sympy.Symbol("n")

    assert classify(n**2.5, "n") == "n^3"
