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
