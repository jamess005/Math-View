# MathView Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A desktop app that turns a typed maths expression into a sequence of steps, each viewable as notation, as a visual, or both — shipping with asymptotic growth comparison and function exploration.

**Architecture:** SymPy generates a `Sequence` of `Step`s from user input; each step may carry a declarative `VisualSpec` that the frontend renders through a `kind` → renderer registry. FastAPI serves both the API and a static web frontend; PyQt5 `QtWebEngine` wraps it in a native window. All logic is Python — JavaScript only draws.

**Tech Stack:** Python 3.12, SymPy, FastAPI, uvicorn, Typer, PyQt5 + PyQtWebEngine (via qtpy), KaTeX, HTML canvas. Tooling: uv, ruff, pytest.

**Reference spec:** `docs/superpowers/specs/2026-08-28-mathview-design.md`

---

## File Structure

| File | Responsibility |
| --- | --- |
| `pyproject.toml` | deps, ruff, pytest config |
| `src/mathview/cli.py` | Typer entry points: window or browser |
| `src/mathview/shell.py` | PyQt5 QtWebEngine window |
| `src/mathview/server.py` | FastAPI app, routes, static mount |
| `src/mathview/core/step.py` | `Step`, `Sequence`, `VisualSpec` |
| `src/mathview/core/parse.py` | text → SymPy, `ParseError` with offset |
| `src/mathview/core/registry.py` | topic name → generator lookup |
| `src/mathview/topics/growth.py` | asymptotic comparison, 5 steps |
| `src/mathview/topics/functions.py` | named definitions, params, value trace |
| `src/mathview/topics/tracing.py` | walking a value through nested calls |
| `web/css/tokens.css` | palette — single source of truth |
| `web/css/app.css` | layout and chrome |
| `web/index.html` | shell markup |
| `web/js/app.js` | state, fetch, wiring |
| `web/js/steps.js` | step panel, view toggle |
| `web/js/render/registry.js` | `kind` → renderer |
| `web/js/render/scales.js` | axis bounds and pixel mapping |
| `web/js/render/plot2d.js` | canvas plotting |
| `tests/` | pytest, mirrors `src/` |

**Hard rule:** any file crossing ~200 lines gets split.

---

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/mathview/__init__.py`, `src/mathview/core/__init__.py`, `src/mathview/topics/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create the package directories**

```bash
cd /home/james/uni/mathview
mkdir -p src/mathview/core src/mathview/topics web/css web/js/render tests
touch src/mathview/__init__.py src/mathview/core/__init__.py \
      src/mathview/topics/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "mathview"
version = "0.1.0"
description = "See how maths works: step sequences you can view as notation, visually, or both"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "sympy>=1.13",
    "numpy>=1.26",
    "fastapi>=0.115",
    "uvicorn>=0.32",
    "typer>=0.12",
    "qtpy>=2.4.3",
    "pyqt5>=5.15.11",
    "pyqtwebengine>=5.15.7",
]

[project.scripts]
mathview = "mathview.cli:app"

[dependency-groups]
dev = [
    "pytest>=8.2",
    "httpx>=0.27",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mathview"]

[tool.ruff]
target-version = "py312"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "N"]

[tool.ruff.lint.isort]
known-first-party = ["mathview"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

- [ ] **Step 3: Install and verify**

```bash
uv sync
```

Expected: creates `.venv`, resolves all dependencies, exits 0.

- [ ] **Step 4: Verify lint passes on the empty package**

```bash
uv run ruff check .
```

Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock src tests
git commit -m "chore: scaffold mathview package"
```

---

### Task 2: The step model

**Files:**
- Create: `src/mathview/core/step.py`
- Test: `tests/test_step.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_step.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.core.step'`

- [ ] **Step 3: Write the implementation**

```python
"""The one shape everything in MathView is displayed as.

A topic generator turns user input into a Sequence of Steps. Every Step has the
same three faces - notation, prose, visual - any of which may be absent. The
view toggle in the UI can switch between them uniformly precisely because no
topic is allowed to vary this shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VisualSpec:
    """A declarative drawing instruction. Python never draws; it emits these.

    `kind` selects a renderer in the frontend's registry; `data` is whatever
    that renderer needs. Adding a new visual means adding a kind and a renderer,
    and touching nothing else.
    """

    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        # Flattened, not nested: renderers key off "kind" and read their fields
        # directly, with no `data` unwrap. Nesting would look tidier and break
        # every renderer.
        return {"kind": self.kind, **self.data}


@dataclass(frozen=True)
class Step:
    """One step of a sequence. Any face may be absent."""

    index: int
    title: str
    notation: str | None = None
    prose: str | None = None
    visual: VisualSpec | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "title": self.title,
            "notation": self.notation,
            "prose": self.prose,
            "visual": self.visual.to_dict() if self.visual is not None else None,
        }


@dataclass(frozen=True)
class Sequence:
    """An ordered list of steps produced by one topic from one input."""

    topic: str
    steps: tuple[Step, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"topic": self.topic, "steps": [s.to_dict() for s in self.steps]}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_step.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/core/step.py tests/test_step.py
git commit -m "feat: add Step, Sequence and VisualSpec model"
```

---

### Task 3: Parsing with structured errors

**Files:**
- Create: `src/mathview/core/parse.py`
- Test: `tests/test_parse.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_parse.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.core.parse'`

- [ ] **Step 3: Write the implementation**

```python
"""Text to SymPy, with errors that point at the character that broke.

Malformed input is the normal case in a maths tool, not an exception, so a
parse failure carries an offset the UI can underline. A stack trace or a
silently empty graph reaching the user is a bug.
"""

from __future__ import annotations

import re
from tokenize import TokenError

import sympy
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    standard_transformations,
)

# convert_xor makes `^` mean power, which is what people type;
# implicit_multiplication_application makes `2n` and `n log(n)` work.
TRANSFORMS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

# parse_expr() calls eval(), so the namespace it evaluates against is the
# security boundary. Sympy's own docs warn against running it on unsanitised
# input, and this module is exactly that - the front door for user-typed text.
# Stripping __builtins__ removes the route to __import__ and the file and
# network primitives behind it. Note Python re-inserts the real builtins into
# any globals dict that lacks the key, so setting it explicitly to {} is
# required - omitting the key is NOT the same thing.
_SAFE_GLOBALS: dict[str, object] = {
    name: getattr(sympy, name) for name in dir(sympy) if not name.startswith("_")
}
_SAFE_GLOBALS["__builtins__"] = {}

# Anything of the form `name(` in user text. `\b` will not do: it is not a
# boundary between two word characters, and a digit is one - so `2f(x)` would
# hide the call entirely and slip straight back into being the product 2*f*x.
_CALL = re.compile(r"(?:(?<=[^A-Za-z_])|^)([A-Za-z]\w*)\s*\(")


class ParseError(Exception):
    """A parse failure the UI can render against the input box."""

    def __init__(self, message: str, offset: int, text: str) -> None:
        super().__init__(message)
        self.message = message
        self.offset = offset
        self.text = text

    def to_dict(self) -> dict[str, object]:
        return {"error": self.message, "offset": self.offset, "input": self.text}


def is_builtin_name(name: str) -> bool:
    """True if `name` already means something in SymPy's namespace.

    Definitions must refuse these. SymPy's parser rewrites bare identifiers into
    Symbol(...) calls, so a row named `Symbol` intercepts those and corrupts the
    parse of every other row; shadowing `log` or `sqrt` is merely confusing.
    """
    return name in _SAFE_GLOBALS


def parse_expression(
    text: str, variable: str, functions: dict[str, object] | None = None
) -> sympy.Expr:
    """Parse `text` into a SymPy expression, raising ParseError on failure.

    `functions` names the user-defined functions that may be called. Declaring
    them matters: with `g` unknown, the implicit-multiplication transformation
    reads `g(x)` as `g * x`, so `f(g(x))` silently becomes `f*g*x` and
    composition is impossible. Anything called but neither declared here nor a
    known SymPy name is rejected rather than quietly turned into a product.
    """
    stripped = text.strip()
    if not stripped:
        raise ParseError("empty expression", 0, text)

    known = functions or {}
    for match in _CALL.finditer(stripped):
        name = match.group(1)
        if name in known:
            continue
        # Membership in the SymPy namespace is not enough: pi, E, I, oo and nan
        # are all names there but none are callable, so `nan(x)` quietly became
        # `nan` with the argument dropped entirely.
        if not callable(_SAFE_GLOBALS.get(name)):
            raise ParseError(
                f"no function named {name} is defined yet", match.start(1), text
            )

    try:
        expr = sympy.parsing.sympy_parser.parse_expr(
            stripped,
            transformations=TRANSFORMS,
            global_dict=_SAFE_GLOBALS,
            local_dict=dict(known),
            evaluate=True,
        )
    except SyntaxError as exc:
        # The transformations rewrite the source before Python compiles it, so
        # the reported offset is against the rewritten string and can land well
        # past the end of what the user typed - `n^^2` (4 chars) reports offset
        # 16, because convert_xor expands each `^` to `**`. Clamping keeps the
        # caret inside the input; it marks the neighbourhood, not the exact
        # character. Good enough to orient the user, and never out of bounds.
        raw = (exc.offset or 1) - 1
        offset = max(0, min(raw, max(len(text) - 1, 0)))
        raise ParseError(
            f"unexpected syntax near here: {exc.msg}", offset, text
        ) from exc
    except (TokenError, IndexError) as exc:
        # Unmatched brackets surface as tokenize.TokenError (too few closers) or
        # IndexError (too many), and neither stringifies into anything a reader
        # can act on - TokenError renders as a raw Python tuple, which the UI
        # would show verbatim.
        raise ParseError("check the brackets - they do not match", 0, text) from exc
    except Exception as exc:
        # parse_expr is an eval-based third-party parser and its failure
        # vocabulary is not a stable contract: unmatched parentheses alone
        # raise tokenize.TokenError and IndexError, neither a SyntaxError
        # subclass. Enumerating types means the next unlisted one reaches the
        # user as a stack trace, so catch broadly and convert.
        raise ParseError(str(exc) or "could not parse expression", 0, text) from exc

    if not isinstance(expr, sympy.Expr):
        raise ParseError("that is not an expression", 0, text)

    return expr


def free_parameters(expr: sympy.Expr, variable: str) -> list[str]:
    """Symbol names in `expr` other than the bound variable, sorted."""
    bound = sympy.Symbol(variable)
    return sorted(str(s) for s in expr.free_symbols if s != bound)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_parse.py -v
```

Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/core/parse.py tests/test_parse.py
git commit -m "feat: parse expressions with offset-carrying errors"
```

---

### Task 4: Topic registry

**Files:**
- Create: `src/mathview/core/registry.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
"""Topic lookup: the seam that lets modules be added without engine changes."""

import pytest

from mathview.core.registry import (
    UnknownTopicError,
    available_topics,
    get_topic,
    register_topic,
)
from mathview.core.step import Sequence


def _dummy(rows, params):
    return Sequence(topic="dummy", steps=())


def test_registered_topic_can_be_fetched():
    register_topic("dummy", _dummy)

    assert get_topic("dummy") is _dummy


def test_unknown_topic_raises():
    with pytest.raises(UnknownTopicError):
        get_topic("no-such-topic")


def test_available_topics_is_sorted():
    register_topic("zebra", _dummy)
    register_topic("alpha", _dummy)

    names = available_topics()
    assert names == sorted(names)
    assert "alpha" in names and "zebra" in names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_registry.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.core.registry'`

- [ ] **Step 3: Write the implementation**

```python
"""Topic name to generator lookup.

A topic generator has the signature:

    (rows: list[str], params: dict[str, float]) -> Sequence

Adding a module means registering one of these. The engine, the shell and the
view toggle never change.
"""

from __future__ import annotations

from collections.abc import Callable

from mathview.core.step import Sequence

TopicGenerator = Callable[[list[str], dict[str, float]], Sequence]

_TOPICS: dict[str, TopicGenerator] = {}


class UnknownTopicError(KeyError):
    """Asked for a topic nobody registered."""


def register_topic(name: str, generator: TopicGenerator) -> None:
    _TOPICS[name] = generator


def get_topic(name: str) -> TopicGenerator:
    try:
        return _TOPICS[name]
    except KeyError as exc:
        raise UnknownTopicError(name) from exc


def available_topics() -> list[str]:
    return sorted(_TOPICS)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_registry.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/core/registry.py tests/test_registry.py
git commit -m "feat: add topic registry"
```

---

### Task 5: Curve sampling

**Files:**
- Create: `src/mathview/topics/sampling.py`
- Test: `tests/test_sampling.py`

Sampling is shared by both Phase 1 topics, so it lives beside them rather than
inside either.

- [ ] **Step 1: Write the failing test**

```python
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
    # The fourth member of the except tuple needs a witness, and this is not a
    # contrived one: n = 0 is the growth topic's default range start.
    n = sympy.Symbol("n")

    points = sample_curve(1 / n, "n", 0.0, 2.0, count=3)

    assert points[0] == [0.0, None]
    assert points[-1][1] == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_sampling.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.topics.sampling'`

- [ ] **Step 3: Write the implementation**

```python
"""Turning an expression into points the frontend can stroke.

Growth functions overflow fast - 2**n leaves float range around n = 1024 - and
log is undefined at or below zero, so a sampler that raises on either would be
useless here. Both cases become a `None` y, which the renderer draws as a gap.
"""

from __future__ import annotations

import math

import sympy

# Beyond this the frontend's scaling stops being meaningful, and float64 is
# about to overflow anyway.
_MAX_MAGNITUDE = 1e300


def _finite_or_none(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number) or abs(number) > _MAX_MAGNITUDE:
        return None
    return number


def sample_curve(
    expr: sympy.Expr,
    variable: str,
    start: float,
    stop: float,
    count: int = 240,
) -> list[list[float | None]]:
    """Evaluate `expr` at `count` evenly spaced points across [start, stop]."""
    symbol = sympy.Symbol(variable)
    func = sympy.lambdify(symbol, expr, "math")

    step = (stop - start) / (count - 1) if count > 1 else 0.0
    points: list[list[float | None]] = []
    for i in range(count):
        x = start + step * i
        try:
            y = _finite_or_none(func(x))
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            y = None
        points.append([x, y])
    return points
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_sampling.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/topics/sampling.py tests/test_sampling.py
git commit -m "feat: sample expressions into points with gaps for overflow"
```

---

### Task 6: Crossover detection

**Files:**
- Create: `src/mathview/topics/crossover.py`
- Test: `tests/test_crossover.py`

Solved numerically rather than symbolically: `sympy.solve` fails or returns
Lambert-W forms for the mixed cases that matter most here (`2**n` against
`n**2`), whereas a sign change plus bisection always terminates.

- [ ] **Step 1: Write the failing test**

```python
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
```

This is exactly the confusion the crossover step exists to clear up: "exponential
beats quadratic" is true only eventually, and a scan that reported one crossing
would be hiding the interesting half of the story.

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_crossover.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.topics.crossover'`

- [ ] **Step 3: Write the implementation**

```python
"""Where one function overtakes another.

Numeric, not symbolic: sympy.solve either fails or returns Lambert-W forms for
the mixed exponential/polynomial comparisons that matter most here. Scanning
for a sign change in (a - b) and bisecting always terminates and always yields
a number the UI can put a marker on.
"""

from __future__ import annotations

import math

import sympy

_SCAN_STEPS = 600
_BISECT_STEPS = 60
_TOLERANCE = 1e-9


def _difference(expr_a: sympy.Expr, expr_b: sympy.Expr, variable: str):
    symbol = sympy.Symbol(variable)
    func = sympy.lambdify(symbol, expr_a - expr_b, "math")

    def evaluate(x: float) -> float | None:
        try:
            value = float(func(x))
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            return None
        return value if math.isfinite(value) else None

    return evaluate


def _bisect(evaluate, low: float, low_value: float, high: float) -> float:
    # `low_value` is passed in rather than recomputed: the caller already has it,
    # and guarding a None here would be an unsound branch that can silently
    # converge on a bogus root.
    for _ in range(_BISECT_STEPS):
        middle = (low + high) / 2
        middle_value = evaluate(middle)
        if middle_value is None or abs(middle_value) < _TOLERANCE:
            return middle
        if (middle_value > 0) == (low_value > 0):
            low, low_value = middle, middle_value
        else:
            high = middle
    return (low + high) / 2


def meeting_point(
    expr_a: sympy.Expr,
    expr_b: sympy.Expr,
    variable: str,
    x: float,
) -> float | None:
    """The shared y where two curves meet, or None if they do not really meet.

    find_crossovers reports a sign change in (a - b), and that also occurs
    across a pole, where the curves are nowhere near each other: bisection
    lands on the asymptote and subs() returns complex infinity. 1/(n-1)
    against a constant crashed on exactly this. Both sides must be finite AND
    equal there for the candidate to count as a crossing.
    """
    symbol = sympy.Symbol(variable)
    try:
        y_a = float(expr_a.subs(symbol, x))
        y_b = float(expr_b.subs(symbol, x))
    except (TypeError, ValueError, OverflowError):
        return None
    if not (math.isfinite(y_a) and math.isfinite(y_b)):
        return None
    scale = max(1.0, abs(y_a), abs(y_b))
    if abs(y_a - y_b) > 1e-6 * scale:
        return None
    return y_a


def find_crossovers(
    expr_a: sympy.Expr,
    expr_b: sympy.Expr,
    variable: str,
    start: float,
    stop: float,
) -> list[float]:
    """Points in [start, stop] where `expr_a` and `expr_b` cross, ascending."""
    evaluate = _difference(expr_a, expr_b, variable)
    step = (stop - start) / _SCAN_STEPS

    crossings: list[float] = []
    previous_x = start
    previous = evaluate(start)
    for i in range(1, _SCAN_STEPS + 1):
        x = start + step * i
        current = evaluate(x)
        if previous is not None and current is not None:
            # `+ 0.0` throughout normalises -0.0 to 0.0, so a crossing at the
            # origin never renders as "n = -0".
            if previous == 0.0 and current != 0.0:
                # Only when the difference is LEAVING zero. Without that guard,
                # two identical functions report one crossing per scan step.
                crossings.append(previous_x + 0.0)
            elif (previous > 0) != (current > 0):
                crossings.append(
                    round(_bisect(evaluate, previous_x, previous, x), 9) + 0.0
                )
            elif current == 0.0 and i == _SCAN_STEPS and previous != 0.0:
                # A zero exactly at `stop` never becomes `previous`, and `0 > 0`
                # is False so it reads as no sign change against a negative
                # sample either. The right edge needs its own probe.
                crossings.append(x + 0.0)
        previous_x, previous = x, current

    return crossings
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_crossover.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/topics/crossover.py tests/test_crossover.py
git commit -m "feat: find crossover points numerically"
```

---

### Task 7: Dominance ordering and Big-O classification

**Files:**
- Create: `src/mathview/topics/asymptotics.py`
- Test: `tests/test_asymptotics.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_asymptotics.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.topics.asymptotics'`

- [ ] **Step 3: Write the implementation**

```python
"""Growth ordering and complexity classification.

Both work through limits of ratios, which is the definition rather than a
heuristic: a grows slower than b exactly when a/b tends to zero, and a is
O(g) exactly when a/g tends to a finite value.
"""

from __future__ import annotations

from functools import cmp_to_key

import sympy

_MAX_POLY_DEGREE = 10


def _ladder(symbol: sympy.Symbol) -> list[tuple[sympy.Expr, str]]:
    """Standard complexity classes, slowest-growing first.

    The polynomial rungs run one degree at a time up to _MAX_POLY_DEGREE rather
    than jumping n^3 -> 2^n. classify() returns the FIRST rung with a finite
    ratio limit, so a gap there is not merely imprecise: with no n^4 rung,
    n^4 skips n^3 (ratio -> oo) and lands on 2^n, telling a student that a
    quartic algorithm is exponential-class. True, and badly misleading.
    """
    polynomials = [
        (symbol**power, "n" if power == 1 else f"n^{power}")
        for power in range(1, _MAX_POLY_DEGREE + 1)
    ]
    return [
        (sympy.Integer(1), "1"),
        (sympy.log(symbol), "log n"),
        polynomials[0],
        (symbol * sympy.log(symbol), "n log n"),
        *polynomials[1:],
        (sympy.Integer(2) ** symbol, "2^n"),
        (sympy.factorial(symbol), "n!"),
    ]


def _ratio_limit(expr_a: sympy.Expr, expr_b: sympy.Expr, symbol: sympy.Symbol):
    try:
        return sympy.limit(expr_a / expr_b, symbol, sympy.oo)
    except (NotImplementedError, ValueError, TypeError, RecursionError):
        return None


def classify(expr: sympy.Expr, variable: str) -> str:
    """The tightest standard class bounding `expr`, as a display label."""
    symbol = sympy.Symbol(variable)
    for candidate, label in _ladder(symbol):
        limit = _ratio_limit(expr, candidate, symbol)
        if limit is None:
            continue
        if limit.is_finite:
            return label
    return "greater than n!"


def compare_growth(expr_a: sympy.Expr, expr_b: sympy.Expr, variable: str) -> int:
    """-1 if `expr_a` grows strictly slower, 1 if strictly faster, 0 if same order.

    Same order covers a finite non-zero ratio limit - n and 100n differ only by a
    constant, so neither ever overtakes the other. Callers that render an
    ordering need that distinction: writing `n < 100n` would be false.
    """
    return _compare(expr_a, expr_b, sympy.Symbol(variable))


def _compare(expr_a: sympy.Expr, expr_b: sympy.Expr, symbol: sympy.Symbol) -> int:
    limit = _ratio_limit(expr_a, expr_b, symbol)
    if limit is None:
        # Known limitation: treating "SymPy could not decide" as "same order"
        # makes the comparator non-transitive, so the result can depend on the
        # order the caller listed the functions in. Every standard complexity
        # class resolves symbolically, so this cannot fire for the inputs this
        # topic is for; a numeric fallback was prototyped and rejected because
        # it could not reliably separate O(1) from O(log n) without probing
        # absurdly far out.
        return 0
    if limit.is_zero:
        return -1
    if limit.is_infinite:
        return 1
    # Finite non-zero: the same order, differing only by a constant factor.
    return 0


def dominance_order(exprs: list[sympy.Expr], variable: str) -> list[sympy.Expr]:
    """Sort `exprs` slowest-growing first."""
    symbol = sympy.Symbol(variable)
    return sorted(exprs, key=cmp_to_key(lambda a, b: _compare(a, b, symbol)))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_asymptotics.py -v
```

Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/topics/asymptotics.py tests/test_asymptotics.py
git commit -m "feat: add dominance ordering and Big-O classification"
```

---

### Task 8: The `growth` topic

**Files:**
- Create: `src/mathview/topics/growth.py`
- Test: `tests/test_growth.py`

- [ ] **Step 1: Write the failing test**

```python
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


def test_a_pole_does_not_crash_and_is_not_a_crossing():
    # A sign change across a pole is not a meeting point. Before the fix this
    # raised TypeError: Cannot convert complex to float.
    sequence = build(["1/(n-1)", "1"], {"n_max": 10})
    markers = sequence.steps[2].visual.data["markers"]

    # The genuine crossing at n = 2 survives; the pole at n = 1 does not.
    assert len(markers) == 1
    assert abs(markers[0]["x"] - 2.0) < 1e-6


def test_curves_separated_by_a_pole_are_not_reported_as_crossing():
    sequence = build(["1/n", "1/(n-5)"], {"n_max": 20})

    assert sequence.steps[2].visual.data["markers"] == []
    assert "do not cross" in sequence.steps[2].prose


def test_crossover_prose_does_not_claim_which_function_is_faster():
    # 2^n is the asymptotically worse function but is the LARGER one before
    # their first crossing at n = 2, so any blanket claim is backwards here.
    sequence = build(["2^n", "n^2"], {"n_max": 20})

    assert "worse function is the faster" not in sequence.steps[2].prose
    assert "eventually begins" in sequence.steps[2].prose


def test_same_order_functions_are_not_a_strict_chain():
    # n and 100n differ only by a constant, so neither overtakes the other.
    sequence = build(["n", "100*n"], {})

    assert sequence.steps[3].notation == r"n \sim 100 n"


def test_non_positive_range_is_a_parse_error():
    for bad in (0, -50):
        with pytest.raises(ParseError):
            build(["n", "n^2"], {"n_max": bad})


def test_no_rows_is_a_parse_error():
    with pytest.raises(ParseError):
        build([], {})


def test_too_many_rows_is_a_parse_error():
    with pytest.raises(ParseError):
        build(["n"] * (MAX_ROWS + 1), {})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_growth.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.topics.growth'`

- [ ] **Step 3: Write the implementation**

```python
"""Compare how fast functions grow.

Five steps, of which the third carries the weight: asymptotic order tells you
what wins eventually, not what wins at the input size you actually have, and
the crossover is where that distinction becomes visible.
"""

from __future__ import annotations

import math

import sympy

from mathview.core.parse import ParseError, parse_expression
from mathview.core.registry import register_topic
from mathview.core.step import Sequence, Step, VisualSpec
from mathview.topics.asymptotics import classify, compare_growth, dominance_order
from mathview.topics.crossover import find_crossovers, meeting_point
from mathview.topics.sampling import sample_curve

VARIABLE = "n"
MAX_ROWS = 6  # one per palette series slot
SMALL_VALUES = (1, 5, 10, 20)


def _parse_rows(rows: list[str]) -> list[tuple[str, sympy.Expr]]:
    if not rows:
        raise ParseError("enter at least one function", 0, "")
    if len(rows) > MAX_ROWS:
        raise ParseError(f"at most {MAX_ROWS} functions can be compared", 0, "")
    return [(row, parse_expression(row, VARIABLE)) for row in rows]


def _plot(
    parsed: list[tuple[str, sympy.Expr]],
    n_max: float,
    markers: list[dict] | None = None,
    shaded: list[dict] | None = None,
) -> VisualSpec:
    curves = [
        {
            "label": sympy.latex(expr),
            "slot": slot,
            "points": sample_curve(expr, VARIABLE, 0.0, n_max),
        }
        for slot, (_, expr) in enumerate(parsed)
    ]
    return VisualSpec(
        kind="plot2d",
        data={
            "curves": curves,
            "markers": markers or [],
            "shaded": shaded or [],
            "xlabel": "n",
            "ylabel": "operations",
            "xrange": [0.0, n_max],
        },
    )


def _step_entered(parsed, n_max) -> Step:
    notation = r" \quad ".join(sympy.latex(expr) for _, expr in parsed)
    return Step(
        index=0,
        title="The functions as entered",
        notation=notation,
        prose="Each function plotted over the same range of n.",
        visual=_plot(parsed, n_max),
    )


def _step_small(parsed, n_max) -> Step:
    header = " & ".join(["n", *[sympy.latex(expr) for _, expr in parsed]])
    body_rows = []
    for value in SMALL_VALUES:
        cells = [str(value)]
        for _, expr in parsed:
            evaluated = expr.subs(sympy.Symbol(VARIABLE), value)
            cells.append(sympy.latex(sympy.nsimplify(evaluated).evalf(6)))
        body_rows.append(" & ".join(cells))
    columns = "c" * (len(parsed) + 1)
    table = (
        r"\begin{array}{" + columns + "}" + header + r" \\ \hline "
        + r" \\ ".join(body_rows) + r"\end{array}"
    )
    return Step(
        index=1,
        title="Evaluated small",
        notation=table,
        prose="At small n the difference is often invisible. That is the trap.",
        visual=_plot(parsed, n_max),
    )


def _step_crossovers(parsed, n_max) -> Step:
    markers: list[dict] = []
    sentences: list[str] = []
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            _, expr_a = parsed[i]
            _, expr_b = parsed[j]
            for x in find_crossovers(expr_a, expr_b, VARIABLE, 0.5, n_max):
                y = meeting_point(expr_a, expr_b, VARIABLE, x)
                if y is None:
                    continue
                markers.append({"kind": "crossover", "x": float(x), "y": y})
                sentences.append(
                    f"{sympy.latex(expr_a)} and {sympy.latex(expr_b)} cross at "
                    f"n = {x:g}."
                )

    # The old wording claimed the asymptotically worse function is faster
    # before a crossing. That is backwards for 2^n against n^2, which is larger
    # than n^2 everywhere before their first crossing at n = 2.
    prose = (
        " ".join(sentences)
        + " Asymptotic order says which function wins eventually;"
        + " a crossing is where eventually begins."
        if sentences
        else "These functions do not cross in this range."
    )
    return Step(
        index=2,
        title="Crossover points",
        notation=None,
        prose=prose,
        visual=_plot(parsed, n_max, markers=markers),
    )


def _step_dominance(parsed, n_max) -> Step:
    ordered = dominance_order([expr for _, expr in parsed], VARIABLE)
    parts = [sympy.latex(ordered[0])]
    for earlier, later in zip(ordered, ordered[1:], strict=False):
        # `n \prec 100n` would be false - they differ only by a constant, so
        # neither ever overtakes the other. Same-order pairs get \sim.
        strict = compare_growth(earlier, later, VARIABLE) < 0
        parts.append((r" \prec " if strict else r" \sim ") + sympy.latex(later))
    return Step(
        index=3,
        title="Dominance chain",
        notation="".join(parts),
        prose=(
            "Slowest-growing first. ≺ means eventually overtaken; "
            "∼ means the same order, differing only by a constant factor."
        ),
        visual=_plot(parsed, n_max),
    )


def _step_classification(parsed, n_max) -> Step:
    lines = [
        rf"{sympy.latex(expr)} \in O({classify(expr, VARIABLE)})" for _, expr in parsed
    ]
    return Step(
        index=4,
        title="Big-O classification",
        notation=r" \\ ".join(lines),
        prose="  ".join(
            f"{row} is O({classify(expr, VARIABLE)})." for row, expr in parsed
        ),
        visual=_plot(parsed, n_max),
    )


def build(rows: list[str], params: dict[str, float]) -> Sequence:
    """Build the five-step growth comparison sequence."""
    parsed = _parse_rows(rows)
    n_max = float(params.get("n_max", 50))
    if not math.isfinite(n_max) or n_max <= 0:
        # n is an input size. A zero or negative range produced a degenerate
        # plot and reported the bisection tolerance (1e-09) as a real crossing.
        raise ParseError("the range of n must be greater than zero", 0, "")

    return Sequence(
        topic="growth",
        steps=(
            _step_entered(parsed, n_max),
            _step_small(parsed, n_max),
            _step_crossovers(parsed, n_max),
            _step_dominance(parsed, n_max),
            _step_classification(parsed, n_max),
        ),
    )


register_topic("growth", build)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_growth.py -v
```

Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/topics/growth.py tests/test_growth.py
git commit -m "feat: add growth comparison topic"
```

---

### Task 9: Named definitions and expansion

**Files:**
- Create: `src/mathview/topics/definitions.py`
- Test: `tests/test_definitions.py`

- [ ] **Step 1: Write the failing test**

```python
"""Named function rows, and resolving references between them."""

import pytest
import sympy

from mathview.core.parse import ParseError
from mathview.topics.definitions import Definition, expand, parse_definitions


def test_parses_name_variable_and_body():
    definitions = parse_definitions(["f(x) = 2x + 3"])

    assert list(definitions) == ["f"]
    assert definitions["f"] == Definition(
        name="f", variable="x", body=2 * sympy.Symbol("x") + 3
    )


def test_a_row_without_equals_is_a_parse_error():
    with pytest.raises(ParseError) as excinfo:
        parse_definitions(["2x + 3"])

    assert "name" in excinfo.value.message


def test_a_malformed_left_hand_side_is_a_parse_error():
    with pytest.raises(ParseError):
        parse_definitions(["f = 2x"])


def test_expand_resolves_a_composition():
    definitions = parse_definitions(["f(x) = 2x", "g(x) = x^2", "h(x) = f(g(x))"])
    x = sympy.Symbol("x")

    assert expand(definitions["h"].body, definitions) == 2 * x**2


def test_expand_resolves_three_levels():
    rows = ["f(x) = 2x", "g(x) = x^2", "h(x) = x + 1", "k(x) = f(g(h(x)))"]
    definitions = parse_definitions(rows)
    x = sympy.Symbol("x")

    assert expand(definitions["k"].body, definitions) == 2 * (x + 1) ** 2


def test_a_forward_reference_is_rejected():
    # Rows may only call names defined above them, so this cannot silently
    # become the product h = f * x.
    with pytest.raises(ParseError):
        parse_definitions(["h(x) = f(x)", "f(x) = 2x"])


def test_a_self_reference_is_rejected():
    with pytest.raises(ParseError):
        parse_definitions(["f(x) = f(x)"])


def test_sympy_functions_are_still_callable():
    definitions = parse_definitions(["f(x) = sqrt(x) + log(x)"])
    x = sympy.Symbol("x")

    assert definitions["f"].body == sympy.sqrt(x) + sympy.log(x)


def test_a_parameter_is_not_mistaken_for_a_function():
    definitions = parse_definitions(["f(x) = a*x^2 + b"])
    x, a, b = sympy.symbols("x a b")

    assert definitions["f"].body == a * x**2 + b


def test_no_rows_is_a_parse_error():
    with pytest.raises(ParseError):
        parse_definitions([])


def test_a_builtin_name_cannot_be_redefined():
    # SymPy's parser rewrites bare identifiers into Symbol(...) calls, so a row
    # named Symbol intercepts those and corrupts every other row's parse.
    with pytest.raises(ParseError):
        parse_definitions(["Symbol(x) = x^2", "g(x) = x + 1"])


def test_shadowing_a_sympy_function_is_rejected():
    with pytest.raises(ParseError):
        parse_definitions(["log(x) = x^2"])


def test_a_repeated_name_is_rejected():
    # Keeping only the last would retroactively change what earlier rows mean:
    # g, written against f(x) = x, would expand using f(x) = 2x.
    with pytest.raises(ParseError):
        parse_definitions(["f(x) = x", "g(x) = f(x) + 1", "f(x) = 2x"])


def test_deep_nesting_is_not_reported_as_a_circle():
    # 17 strictly acyclic levels used to hit a fixed bound of 16 and be
    # reported as a circular reference.
    rows = ["f1(x) = x + 1"] + [f"f{i}(x) = f{i - 1}(x) + 1" for i in range(2, 18)]
    definitions = parse_definitions(rows)

    assert expand(definitions["f17"].body, definitions) == sympy.Symbol("x") + 17
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_definitions.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.topics.definitions'`

- [ ] **Step 3: Write the implementation**

```python
"""Named function rows: `f(x) = 2x + 3`, and references between them.

Naming rows is what makes composition writable directly - `h(x) = f(g(x))` -
rather than needing a separate composition UI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy
from sympy.core.function import AppliedUndef

from mathview.core.parse import ParseError, is_builtin_name, parse_expression

_LHS = re.compile(r"^\s*([A-Za-z]\w*)\s*\(\s*([A-Za-z]\w*)\s*\)\s*$")


@dataclass(frozen=True)
class Definition:
    name: str
    variable: str
    body: sympy.Expr


def parse_definitions(rows: list[str]) -> dict[str, Definition]:
    """Parse `name(var) = body` rows, in order, into a name-keyed mapping."""
    if not rows:
        raise ParseError("enter at least one definition", 0, "")

    definitions: dict[str, Definition] = {}
    for row in rows:
        if "=" not in row:
            raise ParseError(
                "give the function a name, like f(x) = 2x + 3", 0, row
            )
        left, _, right = row.partition("=")
        match = _LHS.match(left)
        if match is None:
            raise ParseError("the left side must look like f(x)", 0, row)

        name, variable = match.group(1), match.group(2)
        if name in definitions:
            raise ParseError(f"{name} is already defined above", 0, row)
        if is_builtin_name(name):
            raise ParseError(f"{name} is a built-in name, choose another", 0, row)
        # Only names defined on EARLIER rows are callable here. That ordering is
        # what makes a forward reference an error rather than a silent product:
        # with `g` undeclared, implicit multiplication reads `g(x)` as `g * x`.
        known = {defined: sympy.Function(defined) for defined in definitions}
        definitions[name] = Definition(
            name=name,
            variable=variable,
            body=parse_expression(right, variable, known),
        )
    return definitions


def expand(expr: sympy.Expr, definitions: dict[str, Definition]) -> sympy.Expr:
    """Replace every call to a defined name with that definition's body."""
    # One pass resolves one level of nesting, and a row can only call rows above
    # it, so the chain is never deeper than the number of definitions. The bound
    # is belt-and-braces for a hand-built dict containing a cycle; it cannot be
    # reached through parse_definitions.
    for _ in range(len(definitions) + 1):
        calls = [
            call
            for call in expr.atoms(AppliedUndef)
            if call.func.__name__ in definitions and len(call.args) == 1
        ]
        if not calls:
            return expr
        for call in calls:
            definition = definitions[call.func.__name__]
            substituted = definition.body.subs(
                sympy.Symbol(definition.variable), call.args[0]
            )
            expr = expr.subs(call, substituted)

    raise ParseError("these definitions nest too deeply to resolve", 0, str(expr))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_definitions.py -v
```

Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/topics/definitions.py tests/test_definitions.py
git commit -m "feat: parse named definitions and expand compositions"
```

---

### Task 10: The `functions` topic

**Files:**
- Create: `src/mathview/topics/functions.py`
- Test: `tests/test_functions.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_functions.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.topics.functions'`

- [ ] **Step 3: Write the implementation**

```python
"""Explore a function: plot it, and walk a value through it.

The last row entered is the one traced, so adding `h(x) = f(g(x))` under two
existing rows switches the trace to the composition without any extra control.
"""

from __future__ import annotations

import sympy

from mathview.core.parse import ParseError, free_parameters
from mathview.core.registry import register_topic
from mathview.core.step import Sequence, Step, VisualSpec
from mathview.topics.definitions import Definition, expand, parse_definitions
from mathview.topics.sampling import sample_curve
from mathview.topics.tracing import call_chain, real_value

X_RANGE = (-10.0, 10.0)


def _substitute_parameters(
    expr: sympy.Expr, variable: str, params: dict[str, float]
) -> sympy.Expr:
    """Bake slider values into `expr`, leaving the row's own variable free.

    It must be the row's variable, not the literal "x": parse_definitions
    accepts any identifier, so `f(t) = a*t` with the slider at t=3 baked t in
    too and plotted a flat line at 15 instead of a line through the origin.
    """
    for name, value in params.items():
        if name != variable:
            expr = expr.subs(sympy.Symbol(name), sympy.Float(value))
    return expr


def _numeric_params(params: dict[str, float]) -> dict[str, float]:
    """Coerce slider values to floats, as a ParseError rather than a traceback."""
    numeric: dict[str, float] = {}
    for name, value in params.items():
        try:
            numeric[name] = float(value)
        except (TypeError, ValueError):
            raise ParseError(f"{name} must be a number", 0, str(value)) from None
    return numeric


def _plot(
    definitions: dict[str, Definition], params: dict[str, float], markers: list[dict]
) -> VisualSpec:
    curves = []
    parameter_names: set[str] = set()
    for slot, definition in enumerate(definitions.values()):
        resolved = _substitute_parameters(
            expand(definition.body, definitions), definition.variable, params
        )
        parameter_names.update(free_parameters(definition.body, definition.variable))
        curves.append(
            {
                "label": f"{definition.name}({definition.variable})",
                "slot": slot,
                "points": sample_curve(
                    resolved, definition.variable, *X_RANGE
                ),
            }
        )

    return VisualSpec(
        kind="plot2d",
        data={
            "curves": curves,
            "markers": markers,
            "shaded": [],
            "parameters": sorted(
                name for name in parameter_names if name not in definitions
            ),
            "xlabel": "x",
            "ylabel": "y",
            "xrange": list(X_RANGE),
        },
    )


def build(rows: list[str], params: dict[str, float]) -> Sequence:
    """Plot each definition, then trace `x` through the last one."""
    definitions = parse_definitions(rows)
    params = _numeric_params(params)
    x_value = params.get("x", 0.0)

    traced = list(definitions.values())[-1]
    chain = call_chain(traced.body, definitions) or [traced.name]

    steps = [
        Step(
            index=0,
            title="The functions as entered",
            notation=r" \quad ".join(
                rf"{d.name}({d.variable}) = {sympy.latex(d.body)}"
                for d in definitions.values()
            ),
            prose="Drag any slider to change a parameter and watch the curve move.",
            visual=_plot(definitions, params, markers=[]),
        ),
        Step(
            index=1,
            title=f"Input x = {x_value:g}",
            notation=rf"x = {x_value:g}",
            prose="The value starts on the x-axis.",
            visual=_plot(
                definitions, params, markers=[{"kind": "input", "x": x_value, "y": 0.0}]
            ),
        ),
    ]

    value = x_value
    for hop, name in enumerate(chain, start=2):
        definition = definitions[name]
        body = _substitute_parameters(
            expand(definition.body, definitions), definition.variable, params
        )
        previous = value
        result, reason = real_value(
            body.subs(sympy.Symbol(definition.variable), previous)
        )
        if result is None:
            steps.append(
                Step(
                    index=hop,
                    title=f"{name}({previous:g}) {reason}",
                    notation=rf"{name}({previous:g}) \notin \mathbb{{R}}",
                    prose=(
                        f"{name}({previous:g}) {reason}, so the trace stops here."
                    ),
                    visual=_plot(definitions, params, markers=[]),
                )
            )
            break
        value = result
        steps.append(
            Step(
                index=hop,
                title=f"{name}({previous:g}) = {value:g}",
                notation=rf"{name}({previous:g}) = {value:g}",
                prose=(
                    f"Up from the x-axis to the curve of {name}, then across to "
                    f"the y-axis."
                    if hop == 2
                    else f"That result becomes the next input: across to the "
                    f"x-axis, up to the curve of {name}, then back to the y-axis."
                ),
                visual=_plot(
                    definitions,
                    params,
                    markers=[
                        {"kind": "hop", "x": previous, "y": value, "label": name}
                    ],
                ),
            )
        )

    return Sequence(topic="functions", steps=tuple(steps))


register_topic("functions", build)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_functions.py -v
```

Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/topics/functions.py tests/test_functions.py
git commit -m "feat: add function exploration topic with value tracing"
```

---

### Task 11: The HTTP API

**Files:**
- Create: `src/mathview/server.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write the failing test**

```python
"""API contract: sequences out, structured parse errors on bad input."""

from fastapi.testclient import TestClient

from mathview.server import create_app

client = TestClient(create_app())


def test_topics_are_listed():
    response = client.get("/api/topics")

    assert response.status_code == 200
    assert set(response.json()["topics"]) >= {"growth", "functions"}


def test_growth_sequence_returns_five_steps():
    response = client.post(
        "/api/sequence", json={"topic": "growth", "rows": ["n", "n^2"], "params": {}}
    )

    assert response.status_code == 200
    assert len(response.json()["steps"]) == 5


def test_parse_error_returns_400_with_an_offset():
    response = client.post(
        "/api/sequence", json={"topic": "growth", "rows": ["n^^2"], "params": {}}
    )

    assert response.status_code == 400
    body = response.json()["detail"]
    assert body["input"] == "n^^2"
    assert isinstance(body["offset"], int)


def test_unknown_topic_returns_404():
    response = client.post(
        "/api/sequence", json={"topic": "nope", "rows": ["n"], "params": {}}
    )

    assert response.status_code == 404


def test_index_is_served():
    response = client.get("/")

    assert response.status_code == 200
    assert "MathView" in response.text


def test_unmatched_brackets_return_a_readable_400():
    response = client.post(
        "/api/sequence", json={"topic": "growth", "rows": ["(1+2"], "params": {}}
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "check the brackets - they do not match"


def test_too_many_rows_returns_400():
    response = client.post(
        "/api/sequence", json={"topic": "growth", "rows": ["n"] * 7, "params": {}}
    )

    assert response.status_code == 400


def test_a_non_positive_range_returns_400():
    response = client.post(
        "/api/sequence",
        json={"topic": "growth", "rows": ["n"], "params": {"n_max": 0}},
    )

    assert response.status_code == 400


def test_the_functions_topic_is_reachable():
    response = client.post(
        "/api/sequence",
        json={"topic": "functions", "rows": ["f(x) = 2x + 3"], "params": {"x": 4}},
    )

    assert response.status_code == 200
    assert response.json()["steps"][-1]["title"] == "f(4) = 11"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_server.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.server'`

- [ ] **Step 3: Write the implementation**

```python
"""FastAPI app: the API, plus the static frontend.

Importing the topic modules is what registers them, so the imports below are
load-bearing rather than incidental.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mathview.core.parse import ParseError
from mathview.core.registry import UnknownTopicError, available_topics, get_topic
from mathview.topics import functions as _functions  # noqa: F401  (registers topic)
from mathview.topics import growth as _growth  # noqa: F401  (registers topic)

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"


class SequenceRequest(BaseModel):
    topic: str
    rows: list[str]
    params: dict[str, float] = {}


def create_app() -> FastAPI:
    app = FastAPI(title="MathView")

    @app.get("/api/topics")
    def topics() -> dict[str, list[str]]:
        return {"topics": available_topics()}

    @app.post("/api/sequence")
    def sequence(request: SequenceRequest) -> dict:
        try:
            generator = get_topic(request.topic)
        except UnknownTopicError:
            raise HTTPException(status_code=404, detail=f"no topic {request.topic!r}") from None

        try:
            return generator(request.rows, request.params).to_dict()
        except ParseError as error:
            raise HTTPException(status_code=400, detail=error.to_dict()) from None

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB_ROOT / "index.html")

    app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")
    return app
```

- [ ] **Step 4: Create a placeholder index so the static test passes**

```bash
printf '<!doctype html><title>MathView</title>\n' > web/index.html
```

- [ ] **Step 5: Run test to verify it passes**

```bash
uv run pytest tests/test_server.py -v
```

Expected: 9 passed

- [ ] **Step 6: Commit**

```bash
git add src/mathview/server.py tests/test_server.py web/index.html
git commit -m "feat: add HTTP API for sequences and topics"
```

---

### Task 12: Palette tokens and page shell

**Files:**
- Create: `web/css/tokens.css`
- Create: `web/css/app.css`
- Modify: `web/index.html` (replace the placeholder from Task 11)

- [x] **Step 1: Validate the palette — DONE, values below are the result**

Already run. The original proposal failed: five of six series sat outside the
dark-mode lightness band, and violet/magenta were only dE 7.4 apart under
protanopia (3.0 tritan) — effectively one colour to a colour-blind reader.

A search over 4000 candidates produced the values below: CVD dE 14.4,
normal-vision dE 19.2, all six above 3:1 contrast. The one remaining failure is
the lightness band, accepted deliberately and explained in the file's own
comment. The fully band-compliant alternative was muted (teal, olive, brown) and
traded the band pass for two series below 3:1 contrast; the user chose neon with
that trade-off stated.

- [ ] **Step 2: Write `web/css/tokens.css`**

```css
/* MathView palette. Single source of truth - no hex literal appears anywhere
   else in the codebase.

   Matte black and dark grey ground; red is chrome only and never a data
   series, so "important" and "selected" can never be confused; neon is
   reserved for data. Series run cool to hot as growth worsens, which makes the
   palette itself carry meaning in the growth topic.

   Validated with the dataviz palette checker against the panel (#121215):
   colour-blind separation dE 14.4 (target 8), normal-vision dE 19.2, and all
   six series above 3:1 contrast. It deliberately fails the checker's dark-mode
   lightness band (L 0.48-0.67): that band guards against colours washing out
   toward white on a dark ground, and the measured separation numbers show that
   is not happening here. The alternative that passed the band traded it for two
   series below 3:1 contrast - harder to read, and not the look this app wants. */

:root {
  /* Ground */
  --page: #08080a;
  --panel: #121215;
  --panel-hi: #17171b;  /* header gradient top - a shade above --panel */
  --panel-lo: #0e0e11;  /* step-panel gradient foot - toward --page   */
  --input: #1c1c21;
  --grid: #2a2a31;
  --border: rgba(255, 255, 255, 0.07);

  /* Text */
  --ink: #f4f4f6;      /* 17.0:1 on panel */
  --ink-2: #9a9aa6;    /*  6.7:1 */
  --ink-muted: #6a6a76;/*  3.5:1 */

  /* Identity - chrome only, never a data series */
  --red: #ff2740;      /*  5.0:1 */
  --red-deep: #8c0f1e;
  --red-glow: rgba(255, 39, 64, 0.45);

  /* Series - data only, cool to hot as growth worsens */
  --s0: #2cdcff;  /* cyan    O(1)      */
  --s1: #00c571;  /* green   O(log n)  */
  --s2: #ffdf1f;  /* yellow  O(n)      */
  --s3: #ff8734;  /* orange  O(n log n)*/
  --s4: #ff4a9a;  /* pink    O(n^2)    */
  --s5: #b4a9ff;  /* violet  O(2^n)    */

  --glow: 10px;
  --radius: 10px;
  --font: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
  --mono: ui-monospace, "JetBrains Mono", "Fira Code", monospace;
}
```

- [ ] **Step 3: Write `web/css/app.css`**

```css
/* Layout and chrome. Colour comes only from tokens.css. */

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--page);
  color: var(--ink);
  font-family: var(--font);
  height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr auto;
}

/* Header */
header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: linear-gradient(180deg, var(--panel-hi), var(--panel));
  border-bottom: 1px solid var(--border);
}

h1 {
  font-size: 1rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  margin: 0;
  padding-bottom: 2px;
  border-bottom: 2px solid var(--red);
  text-shadow: 0 0 var(--glow) var(--red-glow);
}

select, input, button {
  background: var(--input);
  color: var(--ink);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.4rem 0.6rem;
  font-family: var(--mono);
  font-size: 0.85rem;
}

input:focus, select:focus, button:focus {
  outline: 2px solid var(--red);
  outline-offset: 1px;
}

/* View toggle */
.views { margin-left: auto; display: flex; gap: 0.25rem; }
.views button.active {
  border-color: var(--red);
  box-shadow: 0 0 var(--glow) var(--red-glow);
}

/* Body: input rail + canvas */
main { display: grid; grid-template-columns: 260px 1fr; min-height: 0; }
main.notation-only { grid-template-columns: 260px 0; }
main.notation-only #canvas-wrap { display: none; }

#rail {
  background: var(--panel);
  border-right: 1px solid var(--border);
  padding: 0.75rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.row { display: flex; gap: 0.35rem; }
.row input { flex: 1; min-width: 0; }
.row .swatch { width: 4px; border-radius: 2px; }

.error {
  color: var(--red);
  font-family: var(--mono);
  font-size: 0.75rem;
  white-space: pre;
}

#canvas-wrap { position: relative; min-width: 0; }
canvas { display: block; width: 100%; height: 100%; }

/* Step panel */
#steps {
  background: linear-gradient(180deg, var(--panel), var(--panel-lo));
  border-top: 1px solid var(--border);
  padding: 0.75rem 1rem;
  max-height: 38vh;
  overflow-y: auto;
}
body.visual-only #steps { display: none; }

.step-nav { display: flex; align-items: center; gap: 0.75rem; }
.step-title { color: var(--ink); font-weight: 600; }
.step-count { color: var(--ink-muted); font-size: 0.8rem; }
.step-prose { color: var(--ink-2); margin-top: 0.5rem; line-height: 1.5; }
.step-notation { margin-top: 0.5rem; overflow-x: auto; }
.absent { color: var(--ink-muted); font-style: italic; }

/* Slider row under the inputs */
#params { display: flex; flex-direction: column; gap: 0.35rem; }
#params label {
  color: var(--ink-2);
  font-family: var(--mono);
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
#params input[type="range"] { flex: 1; min-width: 0; accent-color: var(--red); }

/* KaTeX inherits the page ink rather than its own default */
.katex { color: var(--ink); }
.step-notation .katex-display { margin: 0; }

/* Log-scale toggle */
.toggle {
  color: var(--ink-2);
  font-family: var(--mono);
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
}
.toggle input { accent-color: var(--red); }
```

- [ ] **Step 4: Write `web/index.html`**

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MathView</title>
  <link rel="stylesheet" href="/static/css/tokens.css">
  <link rel="stylesheet" href="/static/css/app.css">
  <link rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
  <script defer
          src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
</head>
<body>
  <header>
    <h1>MathView</h1>
    <select id="topic">
      <option value="growth">Growth</option>
      <option value="functions">Functions</option>
    </select>
    <div class="views">
      <button data-view="notation">Notation</button>
      <button data-view="visual">Visual</button>
      <button data-view="both" class="active">Both</button>
    </div>
  </header>

  <main id="main">
    <div id="rail">
      <div id="rows"></div>
      <button id="add">+ add</button>
      <label class="toggle"><input type="checkbox" id="logscale"> log scale</label>
      <div id="params"></div>
      <div id="error" class="error"></div>
    </div>
    <div id="canvas-wrap"><canvas id="canvas"></canvas></div>
  </main>

  <section id="steps"></section>

  <script type="module" src="/static/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 5: Verify the page serves**

```bash
uv run pytest tests/test_server.py::test_index_is_served -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web/css web/index.html
git commit -m "feat: add palette tokens and page shell"
```

---

### Task 13: The plot2d renderer

**Files:**
- Create: `web/js/render/registry.js`
- Create: `web/js/render/scales.js`
- Create: `web/js/render/plot2d.js`

No JS tests, per the logic-in-Python rule — this file receives finished numbers
and strokes paths. Verification is visual, in Task 16.

**The y-scaling was corrected against real data before this task was dispatched.**
An earlier draft computed only a maximum and mapped `v / yMax`, which put every
negative value off-canvas — and the `functions` topic routinely produces them
(`f(x) = 2x + 3` spans -17 to 23; `sin(x)` spans -1 to 1). It also had no log
mode, so `2^n` at 1.1e15 flattened `n`, `n log n` and `n^2` onto the baseline.
Both are fixed here and verified: all four real specs map entirely inside the
plot box in both linear and log mode.

- [ ] **Step 1: Write `web/js/render/registry.js`**

```javascript
// kind -> renderer. Adding a future visual (automaton, venn, graph) means
// registering one function here and changing nothing else.

const renderers = new Map();

export function registerRenderer(kind, fn) {
  renderers.set(kind, fn);
}

export function render(canvas, spec, options) {
  const context = canvas.getContext("2d");
  const ratio = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * ratio;
  canvas.height = canvas.clientHeight * ratio;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);

  if (!spec) return;
  const renderer = renderers.get(spec.kind);
  if (renderer) {
    renderer(context, canvas.clientWidth, canvas.clientHeight, spec, options ?? {});
  }
}
```

- [ ] **Step 2: Write `web/js/render/scales.js`**

```javascript
// Turning data ranges into pixel positions. Separate from the drawing because
// the choice of axis bounds is the part with judgement in it: where to anchor,
// when a dip below zero is noise, and how a log axis floors.

const PAD = { left: 64, right: 16, top: 16, bottom: 40 };

export { PAD };

function yBounds(spec, logMode) {
  let lo = Infinity;
  let hi = -Infinity;
  let loPositive = Infinity;
  for (const curve of spec.curves) {
    for (const [, y] of curve.points) {
      if (y === null || !Number.isFinite(y)) continue;
      if (y < lo) lo = y;
      if (y > hi) hi = y;
      if (y > 0 && y < loPositive) loPositive = y;
    }
  }
  // A log axis cannot start at zero: log10(0) is -Infinity and every axis
  // label downstream becomes NaN.
  if (lo === Infinity) return logMode ? [1, 10] : [0, 1];

  if (logMode) {
    const top = hi > 0 ? hi : 1;
    // Floor at the smallest positive sample: anything at or below zero has no
    // log and is drawn as a gap, so it must not drag the axis down with it.
    const bottom = loPositive < Infinity ? loPositive : top / 1e6;
    return [bottom === top ? top / 10 : bottom, top];
  }

  const span = hi - lo;
  if (lo >= 0) {
    // Anchor to the baseline only when the data comes near it. A curve running
    // 5.01 to 5.99 drawn on a 0-6 axis reads as a flat line, hiding a fifth of
    // its own variation - misleading in a tool for looking at how functions
    // behave.
    if (lo <= span) lo = 0;
    else {
      lo -= span * 0.08;
      hi += span * 0.08;
    }
  } else if (hi > 0 && -lo < hi * 0.02) {
    // A dip a hair below zero - log(n) near n=0, against 2^n at 1e15 - must
    // not stretch the axis into the negatives, or every other curve flattens
    // onto the baseline.
    lo = 0;
  } else {
    lo -= span * 0.08;
    hi += span * 0.08;
  }
  if (hi === lo) hi = lo + 1;
  return [lo, hi];
}

export function makeScales(spec, width, height, logMode) {
  const [x0, x1] = spec.xrange;
  const [lo, hi] = yBounds(spec, logMode);
  const plotWidth = width - PAD.left - PAD.right;
  const plotHeight = height - PAD.top - PAD.bottom;
  const a = logMode ? Math.log10(lo) : 0;
  const b = logMode ? Math.log10(hi) : 0;
  return {
    lo,
    hi,
    logMode,
    x: (v) => PAD.left + ((v - x0) / (x1 - x0)) * plotWidth,
    y: (v) =>
      logMode
        ? v <= 0
          ? null
          : PAD.top + plotHeight - ((Math.log10(v) - a) / (b - a)) * plotHeight
        : PAD.top + plotHeight - ((v - lo) / (hi - lo)) * plotHeight,
  };
}
```

- [ ] **Step 3: Write `web/js/render/plot2d.js`**

```javascript
// Cartesian plotting. Receives finished numbers from Python - it computes no
// maths of its own, only the pixel mapping.

import { registerRenderer } from "./registry.js";
import { makeScales, PAD } from "./scales.js";

function token(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function seriesColour(slot) {
  return token(`--s${slot % 6}`);
}

function label(value, logMode) {
  if (value === 0) return "0";
  const magnitude = Math.abs(value);
  if (logMode || magnitude >= 1e5 || magnitude < 1e-3) return value.toExponential(1);
  return Number(value.toPrecision(4)).toString();
}

function drawAxes(context, spec, scales, width, height) {
  context.strokeStyle = token("--grid");
  context.lineWidth = 1;
  context.font = "11px ui-monospace, monospace";
  const plotHeight = height - PAD.top - PAD.bottom;

  for (let i = 0; i <= 5; i++) {
    const py = PAD.top + (plotHeight / 5) * i;
    context.beginPath();
    context.moveTo(PAD.left, py);
    context.lineTo(width - PAD.right, py);
    context.stroke();
    const fraction = 1 - i / 5;
    const value = scales.logMode
      ? 10 ** (Math.log10(scales.lo) + fraction * (Math.log10(scales.hi) - Math.log10(scales.lo)))
      : scales.lo + fraction * (scales.hi - scales.lo);
    context.fillStyle = token("--ink-muted");
    context.fillText(label(value, scales.logMode), 6, py + 4);
  }

  // The x-axis itself, only when zero is actually in view.
  const zero = scales.y(0);
  if (zero !== null && zero >= PAD.top && zero <= height - PAD.bottom) {
    context.strokeStyle = token("--border");
    context.lineWidth = 1.5;
    context.beginPath();
    context.moveTo(PAD.left, zero);
    context.lineTo(width - PAD.right, zero);
    context.stroke();
  }

  const [x0, x1] = spec.xrange;
  context.fillStyle = token("--ink-muted");
  for (let i = 0; i <= 5; i++) {
    const value = x0 + ((x1 - x0) / 5) * i;
    context.fillText(label(value, false), scales.x(value) - 12, height - 22);
  }
  context.fillStyle = token("--ink-2");
  context.fillText(spec.xlabel ?? "x", width / 2, height - 6);
}

function drawCurves(context, spec, scales) {
  context.lineWidth = 2;
  context.lineJoin = "round";
  for (const curve of spec.curves) {
    const colour = seriesColour(curve.slot);
    context.strokeStyle = colour;
    context.shadowColor = colour;
    context.shadowBlur = 10; // the "glow" half of the neon look
    context.beginPath();
    let pen = false;
    for (const [x, y] of curve.points) {
      const py = y === null ? null : scales.y(y);
      if (py === null || !Number.isFinite(py)) {
        pen = false;
        continue;
      }
      const px = scales.x(x);
      if (pen) context.lineTo(px, py);
      else {
        context.moveTo(px, py);
        pen = true;
      }
    }
    context.stroke();
  }
  context.shadowBlur = 0;
}

function drawMarkers(context, spec, scales, height) {
  context.font = "11px ui-monospace, monospace";
  for (const marker of spec.markers ?? []) {
    const px = scales.x(marker.x);
    const py = scales.y(marker.y);
    if (py === null || !Number.isFinite(py)) continue;
    const foot = scales.y(0) ?? height - PAD.bottom;

    context.strokeStyle = token("--red");
    context.fillStyle = token("--red");
    context.shadowColor = token("--red");
    context.shadowBlur = 12;
    context.setLineDash([4, 4]);
    context.beginPath();
    context.moveTo(px, py);
    context.lineTo(px, Math.min(Math.max(foot, PAD.top), height - PAD.bottom));
    context.stroke();
    context.setLineDash([]);
    context.beginPath();
    context.arc(px, py, 4, 0, Math.PI * 2);
    context.fill();
    context.shadowBlur = 0;

    context.fillStyle = token("--ink");
    context.fillText(`${marker.label ?? ""} ${label(marker.x, false)}`, px + 8, py - 8);
  }
}

function drawLegend(context, spec) {
  context.font = "12px ui-monospace, monospace";
  let y = PAD.top + 12;
  for (const curve of spec.curves) {
    context.fillStyle = seriesColour(curve.slot);
    context.fillRect(PAD.left + 8, y - 8, 10, 3);
    context.fillStyle = token("--ink-2");
    context.fillText(curve.label, PAD.left + 24, y);
    y += 16;
  }
}

registerRenderer("plot2d", (context, width, height, spec, options = {}) => {
  const scales = makeScales(spec, width, height, Boolean(options.logScale));
  drawAxes(context, spec, scales, width, height);
  drawCurves(context, spec, scales);
  drawMarkers(context, spec, scales, height);
  drawLegend(context, spec);
});
```

- [ ] **Step 4: Commit**

```bash
git add web/js/render
git commit -m "feat: add plot2d canvas renderer and renderer registry"
```

---

### Task 14: Frontend state, view toggle and step panel

**Files:**
- Create: `web/js/steps.js`
- Create: `web/js/app.js`

- [ ] **Step 1: Write `web/js/steps.js`**

```javascript
// The step panel and the view toggle.
//
// The toggle works uniformly across every topic because every step has the
// same three faces. A step missing a face says so rather than collapsing.

const panel = () => document.getElementById("steps");

export const state = { sequence: null, index: 0, view: "both" };

function typeset(element, latex) {
  if (window.katex) {
    window.katex.render(latex, element, { throwOnError: false, displayMode: true });
  } else {
    element.textContent = latex;
  }
}

export function renderSteps(onChange) {
  const root = panel();
  root.innerHTML = "";
  if (!state.sequence) return;

  const step = state.sequence.steps[state.index];
  const total = state.sequence.steps.length;

  const nav = document.createElement("div");
  nav.className = "step-nav";

  const back = document.createElement("button");
  back.textContent = "◀";
  back.disabled = state.index === 0;
  back.onclick = () => { state.index -= 1; renderSteps(onChange); onChange(); };

  const forward = document.createElement("button");
  forward.textContent = "▶";
  forward.disabled = state.index >= total - 1;
  forward.onclick = () => { state.index += 1; renderSteps(onChange); onChange(); };

  const count = document.createElement("span");
  count.className = "step-count";
  count.textContent = `Step ${state.index + 1} of ${total}`;

  const title = document.createElement("span");
  title.className = "step-title";
  title.textContent = step.title;

  nav.append(back, forward, count, title);
  root.append(nav);

  if (step.notation) {
    const notation = document.createElement("div");
    notation.className = "step-notation";
    typeset(notation, step.notation);
    root.append(notation);
  }

  if (step.prose) {
    const prose = document.createElement("div");
    prose.className = "step-prose";
    prose.textContent = step.prose;
    root.append(prose);
  }

  if (state.view === "notation" && !step.notation) {
    const absent = document.createElement("div");
    absent.className = "absent";
    absent.textContent = "This step has no notation — only a visual.";
    root.append(absent);
  }
}

export function applyView(view) {
  state.view = view;
  document.body.classList.toggle("visual-only", view === "visual");
  document.getElementById("main").classList.toggle(
    "notation-only", view === "notation"
  );
  for (const button of document.querySelectorAll(".views button")) {
    button.classList.toggle("active", button.dataset.view === view);
  }
}
```

- [ ] **Step 2: Write `web/js/app.js`**

```javascript
// State, fetching and wiring. All maths happens on the server.

import { render } from "./render/registry.js";
import "./render/plot2d.js";
import { applyView, renderSteps, state } from "./steps.js";

const DEFAULTS = {
  growth: ["n", "n*log(n)", "n^2", "2^n"],
  functions: ["f(x) = 2x", "g(x) = x^2", "h(x) = f(g(x))"],
};

const canvas = document.getElementById("canvas");
const logBox = document.getElementById("logscale");
const rowsBox = document.getElementById("rows");
const paramsBox = document.getElementById("params");
const errorBox = document.getElementById("error");

let rows = [...DEFAULTS.growth];
let params = { n_max: 50 };

function topic() {
  return document.getElementById("topic").value;
}

function drawCurrentStep() {
  if (!state.sequence) return;
  render(canvas, state.sequence.steps[state.index].visual, {
    logScale: logBox.checked,
  });
}

function showError(detail) {
  if (typeof detail === "string") { errorBox.textContent = detail; return; }
  const caret = " ".repeat(detail.offset ?? 0) + "^";
  errorBox.textContent = `${detail.input}\n${caret}\n${detail.error}`;
}

// A full growth build is real SymPy work - measured 87 ms for the default four
// functions and 143 ms for six including n!. Firing on every keystroke or
// slider tick would queue requests faster than they finish, so input is
// debounced into one request, and stale replies are discarded: without the
// requestId guard a slow earlier request can land after a fast later one and
// overwrite the newer result with older data.
const DEBOUNCE_MS = 180;
let debounceTimer = null;
let requestId = 0;

function scheduleRefresh() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(refresh, DEBOUNCE_MS);
}

async function refresh() {
  const mine = ++requestId;
  const response = await fetch("/api/sequence", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic: topic(), rows, params }),
  });
  if (mine !== requestId) return;

  if (!response.ok) {
    showError((await response.json()).detail);
    return;
  }

  errorBox.textContent = "";
  state.sequence = await response.json();
  state.index = Math.min(state.index, state.sequence.steps.length - 1);
  renderSteps(drawCurrentStep);
  drawCurrentStep();
  renderParams();
}

function renderRows() {
  rowsBox.innerHTML = "";
  rows.forEach((value, i) => {
    const row = document.createElement("div");
    row.className = "row";

    const swatch = document.createElement("div");
    swatch.className = "swatch";
    swatch.style.background = `var(--s${i % 6})`;

    const input = document.createElement("input");
    input.value = value;
    input.oninput = () => { rows[i] = input.value; scheduleRefresh(); };

    row.append(swatch, input);
    rowsBox.append(row);
  });
}

function renderParams() {
  const spec = state.sequence?.steps[state.index]?.visual;
  const names = spec?.parameters ?? (topic() === "growth" ? ["n_max"] : []);
  paramsBox.innerHTML = "";

  for (const name of names) {
    const label = document.createElement("label");
    label.textContent = `${name} `;
    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = name === "n_max" ? 5 : -10;
    slider.max = name === "n_max" ? 500 : 10;
    slider.step = name === "n_max" ? 5 : 0.1;
    slider.value = params[name] ?? (name === "n_max" ? 50 : 1);
    params[name] = Number(slider.value);
    slider.oninput = () => { params[name] = Number(slider.value); scheduleRefresh(); };
    label.append(slider);
    paramsBox.append(label);
  }

  if (topic() === "functions") {
    const label = document.createElement("label");
    label.textContent = "x ";
    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = -10; slider.max = 10; slider.step = 0.5;
    slider.value = params.x ?? 4;
    params.x = Number(slider.value);
    slider.oninput = () => { params.x = Number(slider.value); scheduleRefresh(); };
    label.append(slider);
    paramsBox.append(label);
  }
}

document.getElementById("add").onclick = () => {
  if (rows.length >= 6) return;
  rows.push(topic() === "growth" ? "n" : `k(x) = x`);
  renderRows();
  refresh();
};

document.getElementById("topic").onchange = () => {
  rows = [...DEFAULTS[topic()]];
  params = topic() === "growth" ? { n_max: 50 } : { x: 4 };
  state.index = 0;
  renderRows();
  refresh();
};

for (const button of document.querySelectorAll(".views button")) {
  button.onclick = () => { applyView(button.dataset.view); drawCurrentStep(); };
}

// A log axis is a different mapping of numbers the page already has, so it
// redraws locally - no request, no debounce, instant.
logBox.onchange = drawCurrentStep;

window.addEventListener("resize", drawCurrentStep);

applyView("both");
renderRows();
refresh();
```

- [ ] **Step 3: Commit**

```bash
git add web/js/app.js web/js/steps.js
git commit -m "feat: add frontend state, view toggle and step panel"
```

---

### Task 15: The desktop window

**Files:**
- Create: `src/mathview/shell.py`
- Test: `tests/test_shell.py`

Carries over the minimize/restore repaint fix from `stock-manager` — the same
QtWebEngine visibility-throttling bug applies here.

- [ ] **Step 1: Write the failing test**

```python
"""The Qt window's minimize/restore white-screen fix.

Runs against the offscreen QPA platform so it needs no real display. Patches
QApplication.exec to drive one minimize -> restore cycle and return instead of
blocking, and spies on QWebEnginePage.setVisible to confirm open_window()
toggles it off then on across that cycle.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

pytest.importorskip("qtpy")

from qtpy.QtCore import Qt  # noqa: E402
from qtpy.QtWebEngineWidgets import QWebEnginePage  # noqa: E402
from qtpy.QtWidgets import QApplication  # noqa: E402

from mathview.shell import open_window  # noqa: E402


@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="QtWebEngine (Chromium) aborts on display-less CI runners",
)
def test_minimize_then_restore_toggles_page_visibility(monkeypatch):
    calls: list[bool] = []
    monkeypatch.setattr(
        QWebEnginePage, "setVisible", lambda self, visible: calls.append(visible)
    )

    def fake_exec(self):
        window = next(w for w in QApplication.topLevelWidgets() if w.isVisible())
        window.setWindowState(Qt.WindowMinimized)
        window.setWindowState(Qt.WindowNoState)
        QApplication.processEvents()
        return 0

    monkeypatch.setattr(QApplication, "exec_", fake_exec, raising=False)
    monkeypatch.setattr(QApplication, "exec", fake_exec, raising=False)

    open_window("http://127.0.0.1:1/")

    assert False in calls and True in calls
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_shell.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.shell'`

- [ ] **Step 3: Write the implementation**

```python
"""Native desktop window (QtWebEngine) pointed at the local server."""

from __future__ import annotations

import sys


def open_window(url: str, title: str = "MathView") -> None:
    """Open `url` in a native window; blocks until the window closes."""
    from qtpy.QtCore import QEvent, QTimer, QUrl
    from qtpy.QtWebEngineWidgets import (
        QWebEnginePage,  # pyright: ignore[reportAttributeAccessIssue]
        QWebEngineProfile,  # pyright: ignore[reportAttributeAccessIssue]
        QWebEngineView,  # pyright: ignore[reportAttributeAccessIssue]
    )
    from qtpy.QtWidgets import QApplication

    class _View(QWebEngineView):
        """Recovers from the "minimize, then restore" white screen.

        Iconifying on X11 doesn't fire Qt's show/hide events, so QtWebEngine's
        visibility throttling never learns the window came back and leaves the
        last composited frame - often blank - on screen. Toggling page
        visibility off then on, on the real WindowStateChange event, forces a
        fresh compositor frame with no user action needed.
        """

        def changeEvent(self, event) -> None:  # noqa: N802 (Qt override name)
            super().changeEvent(event)
            is_state_change = (
                event.type() == QEvent.WindowStateChange  # pyright: ignore[reportAttributeAccessIssue]
            )
            if is_state_change and not self.isMinimized():
                page = self.page()
                if page is not None:
                    page.setVisible(False)
                    QTimer.singleShot(0, lambda: page.setVisible(True))

    app = QApplication.instance() or QApplication(sys.argv[:1])

    view = _View()
    # Off-the-record profile: the default profile's disk cache can be left
    # locked or corrupt by an unclean exit, which shows up as a white window.
    profile = QWebEngineProfile()
    page = QWebEnginePage(profile)
    view.setPage(page)
    view.setWindowTitle(title)
    view.resize(1280, 860)
    view.load(QUrl(url))
    view.show()

    runner = getattr(app, "exec", None) or app.exec_
    runner()

    # Python controls destruction order (page before profile); Qt's
    # parent-child teardown does not guarantee it.
    view.setPage(None)
    del page
    del profile
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_shell.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/mathview/shell.py tests/test_shell.py
git commit -m "feat: add QtWebEngine desktop window"
```

---

### Task 16: CLI, launcher, README and end-to-end check

**Files:**
- Create: `src/mathview/cli.py`
- Create: `mathview.desktop`
- Create: `README.md`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
"""The CLI picks a free port and hands it to the right front end."""

from typer.testing import CliRunner

from mathview.cli import app, find_free_port

runner = CliRunner()


def test_find_free_port_returns_a_usable_port():
    port = find_free_port()

    assert 1024 < port < 65536


def test_web_mode_starts_the_server_without_a_window(monkeypatch):
    started: dict[str, object] = {}
    monkeypatch.setattr(
        "mathview.cli.serve_forever", lambda port: started.update(port=port)
    )

    result = runner.invoke(app, ["--web"])

    assert result.exit_code == 0
    assert "port" in started
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mathview.cli'`

- [ ] **Step 3: Write the implementation**

```python
"""Entry point: a native window by default, a browser URL with --web."""

from __future__ import annotations

import socket
import threading

import typer
import uvicorn

from mathview.server import create_app


def find_free_port() -> int:
    """Ask the OS for an unused port, so two instances never collide."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def serve_forever(port: int) -> None:
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="warning")


def _serve_background(port: int) -> None:
    server = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()


app = typer.Typer(add_completion=False, help="See how maths works.")


@app.command()
def main(
    web: bool = typer.Option(False, "--web", help="Serve in a browser instead."),
) -> None:
    port = find_free_port()

    if web:
        typer.echo(f"MathView on http://127.0.0.1:{port}")
        serve_forever(port)
        return

    from mathview.shell import open_window

    _serve_background(port)
    open_window(f"http://127.0.0.1:{port}/")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: 2 passed

- [ ] **Step 5: Write `mathview.desktop`**

```ini
[Desktop Entry]
Name=MathView
Comment=See how maths works: graphs and step-by-step derivations
Exec=/home/james/uni/mathview/.venv/bin/mathview
Icon=accessories-calculator
Terminal=false
Type=Application
Categories=Education;Science;Math;
StartupNotify=true
Path=/home/james/uni/mathview
```

- [ ] **Step 6: Write `README.md`**

```markdown
# MathView

See how maths works. Type an expression, get a sequence of steps — each
viewable as notation, as a visual, or both. Your choice, never the topic's.

## Run

```bash
uv sync
uv run mathview          # native window
uv run mathview --web    # browser
```

Install the launcher:

```bash
cp mathview.desktop ~/.local/share/applications/
```

## Topics

- **Growth** — compare growth rates, with crossover points marked. Asymptotic
  order says what wins eventually; the crossover says what wins at your input
  size.
- **Functions** — plot named definitions, drag sliders for free parameters, and
  trace a value through the hops. Compositions are written directly:
  `h(x) = f(g(x))`.

## Design

- `docs/superpowers/specs/2026-08-28-mathview-design.md`
- All logic is Python; JavaScript only draws.
- Any file over ~200 lines gets split.
```

- [ ] **Step 7: Run the whole suite and the linter**

```bash
uv run pytest -q && uv run ruff check .
```

Expected: all tests pass, `All checks passed!`

- [ ] **Step 8: Verify file sizes are within budget**

```bash
find src web -name "*.py" -o -name "*.js" -o -name "*.css" | xargs wc -l | sort -n
```

Expected: no file over ~200 lines. Split any that is.

- [ ] **Step 9: End-to-end visual check**

Use the `run` skill to launch the app and confirm by screenshot:

1. `uv run mathview` opens a window on a matte-black page with the red
   MathView underline.
2. Growth defaults (`n`, `n*log(n)`, `n^2`, `2^n`) draw four glowing neon
   curves in slot order cyan / green / yellow / orange.
3. Stepping to "Crossover points" shows red markers with dashed drop lines.
4. The **Notation** toggle hides the canvas; **Visual** hides the step panel;
   **Both** restores the split.
5. Switching to Functions and dragging the `x` slider moves the trace.
6. Typing `n^^2` into a row underlines the offending character with a caret and
   an error message, and does not blank the graph.

- [ ] **Step 10: Commit**

```bash
git add src/mathview/cli.py tests/test_cli.py mathview.desktop README.md
git commit -m "feat: add CLI, desktop launcher and README"
```

---

## Self-Review Record

**Spec coverage:** §2 step model → Task 2; view modes → Task 14; VisualSpec
extension point → Tasks 2, 13. §3 architecture → Tasks 11, 15, 16; data flow →
Tasks 11, 14; error handling → Tasks 3, 11, 14 (and verified in Task 16 step 9).
§4 growth → Tasks 5–8; functions → Tasks 9–10. §5 structure → Task 1, enforced
in Task 16 step 8. §6 palette → Task 12, validated in Task 12 step 1. §7 testing
→ every task. §8 out of scope → no tasks, correctly.

**Naming consistency checked:** `VisualSpec.to_dict` flattens `kind` into `data`
(Tasks 2, 13 agree). `build(rows, params)` is the topic generator signature
throughout (Tasks 4, 8, 10, 11). `slot` — not `series` or `index` — names the
palette slot in Tasks 8, 10, 13, 14. Series tokens are `--s0`…`--s5` in Tasks
12, 13, 14. `sample_curve(expr, variable, start, stop, count)` is called with
that signature in Tasks 8 and 10.

**Maths verified against SymPy before writing** (not assumed):

| Assertion | Verified result |
| --- | --- |
| `n^2`, `2n`, `100n`, `n*log(n)`, `3n^2 + 5n` parse as intended | all correct |
| `classify` on `3n²+5n`, `100n`, `n log n`, `7`, `2ⁿ` | `n^2`, `n`, `n log n`, `1`, `2^n` |
| `dominance_order([2ⁿ, n, n², log n])` | `[log n, n, n², 2ⁿ]` |
| LaTeX chain for `[2ⁿ, n, n²]` | `n \prec n^{2} \prec 2^{n}` |
| `n²` vs `100n` crossings on `[0.5, 200]` | `[100.0]` exactly |
| `n` vs `n+5` crossings | `[]` |
| `2ⁿ` vs `n²` crossings on `[1, 20]` | `[2.0, 4.0]` — **two**, not one |
| `n^^2` SyntaxError offset | 16, for a 4-character input — clamp required |

**Corrections made during execution** (found by the review pipeline, verified
independently before acting, and folded back into Task 3 above):

| Found | Reality | Fix |
| --- | --- | --- |
| `(1+2`, `1+2)`, `((n` | escape as `tokenize.TokenError` / `IndexError` — neither a `SyntaxError` subclass | broadened to `except Exception` |
| `n + __import__("os").getpid()*0` | `os.getpid()` **executed**, returned a clean `Symbol`, sailed past the `isinstance` guard | `global_dict=_SAFE_GLOBALS` with `__builtins__` stripped |
| the first draft of the builtins test | `__import__("os").getpid()` returns an `int`, so the `isinstance` guard rejected it for an unrelated reason — the test passed with *and* without the fix | rewritten to use the Symbol-returning form, which only `_SAFE_GLOBALS` catches |

The unmatched-parenthesis case is the one that mattered most: it is the commonest
maths typo there is, and it contradicted this spec's own error-handling promise.

The last two rows of the verification table corrected the plan before execution. An earlier draft of Task 6 asserted a single
`2ⁿ`/`n²` crossing between 4 and 5; that is wrong, and the test now asserts
`[2.0, 4.0]`. Task 3's offset clamp is load-bearing rather than defensive.

**Deviation protocol:** if the palette validation in Task 12 step 1 changes any
hex value, update the spec §6 in the same commit.
