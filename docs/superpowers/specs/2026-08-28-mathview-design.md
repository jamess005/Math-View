# MathView — Design

**Date:** 2026-08-28
**Status:** Approved for planning
**Scope:** Phase 1 — engine, shell, and the `growth` + `functions` topics

---

## 1. Purpose

A desktop app for seeing how maths works. The user types an expression and gets
back a **sequence of steps**, each of which can be viewed as notation, as a
visual, or as both — the user's choice, never the topic's.

The immediate need is asymptotic analysis and Big-O notation. The architecture
must extend to induction proofs, Turing machines, context-free languages, sets
and graphs without rework.

**Non-goal:** reading or writing the Obsidian vault. The vault informed the
scope of the maths; the app does not depend on it.

---

## 2. Core model

Everything the app displays is a `Sequence`: an ordered list of `Step`s produced
by a topic generator from user input.

```python
@dataclass(frozen=True)
class Step:
    index: int
    title: str
    notation: str | None      # LaTeX
    prose: str | None         # explanation
    visual: VisualSpec | None # declarative drawing instruction
```

Any face may be absent. Nothing else about a step varies between topics.

### View modes

A global toggle — `Notation` / `Visual` / `Both` — with a per-step override.
This works uniformly because every step has the same shape. **A topic can never
dictate how it is viewed.** When a step has no visual, the panel says so
explicitly rather than collapsing silently.

Layout per mode:

| Mode     | Canvas      | Step panel   |
| -------- | ----------- | ------------ |
| Notation | hidden      | full width   |
| Visual   | full bleed  | hidden       |
| Both     | centre      | bottom       |

### VisualSpec — the extension point

Python never draws. Topic generators emit declarative data:

```json
{ "kind": "plot2d",
  "curves":  [{"label": "n^2", "slot": 5, "points": [[0,0], [1,1]]}],
  "markers": [{"kind": "crossover", "x": 100, "y": 10000}],
  "xrange": [0, 200], "yrange": [0, 40000], "yscale": "linear" }
```

The frontend holds a registry mapping `kind` → renderer. Adding a future module
means writing one Python generator and one JS renderer. **No changes to the
engine, shell, view toggle, or any existing topic.**

---

## 3. Architecture

```
┌─ PyQt5 QtWebEngine window ──────────────┐
│ ┌─ web frontend ───────────────────────┐│
│ │ KaTeX notation · canvas plots        ││
│ └──────────────┬───────────────────────┘│
└────────────────┼────────────────────────┘
                 │  HTTP (localhost)
┌────────────────┴────────────────────────┐
│ FastAPI + SymPy                         │
│ parse → generate steps → serialise      │
└─────────────────────────────────────────┘
```

Chosen over pure-Qt (weak maths typography, fights the neon aesthetic) and pure
TypeScript (JS symbolic maths too weak for step derivations). Matches the
existing `stock-manager` pattern: uv, ruff, `src/` layout, `.desktop` launcher.

Because the frontend is genuinely web, the same code runs as a desktop window
(`mathview`) or in a browser (`mathview --web`).

### Data flow

1. User types input; frontend `POST /api/sequence {topic, input, params}`.
2. Python parses via SymPy, generates steps, serialises the whole sequence.
3. Frontend renders. **Step scrubbing is client-side** — the entire sequence
   arrives at once, so stepping is instant with no round-trip.

### Error handling

Malformed input is the normal case in a maths tool, not an exception. Parse
failures return a structured error with a character offset:

```json
{"error": "unexpected '^'", "offset": 3, "input": "x^^2"}
```

The input box underlines the offending character. A stack trace or a silently
empty graph is a bug.

---

## 4. Phase 1 topics

Both share the `plot2d` renderer — the reason this pair is the cheapest first
build.

### `growth` — compare growth rates

Input: between one and six expressions in `n` (six being the number of series
slots in the palette; the UI disables "add" at six). Produces five steps:

1. **The functions as entered** — notation only.
2. **Evaluated small** — table at n = 1, 5, 10, 20.
3. **Crossover points** — found numerically (a sign change plus bisection;
   `sympy.solve` returns Lambert-W forms for exponential-vs-polynomial pairs)
   and marked on the plot. Candidates that fall on a pole are discarded: a sign
   change across an asymptote is not a meeting point.
4. **Dominance chain** — `n ≺ n log n ≺ n² ≺ 2ⁿ`. Same-order functions are
   joined by `∼`, not `≺`: `n` and `100n` differ only by a constant, so neither
   ever overtakes the other.
5. **Big-O classification** — each function with its bound.

Step 3 carries the pedagogical weight: asymptotic order says what wins
*eventually*, not what wins at a given input size. It states that and no more —
a blanket claim about which function leads before a crossing is false in
general, and specifically backwards for `2ⁿ` against `n²`, which is the larger
curve everywhere before their first crossing at n = 2.

Controls: n-range slider, log-scale toggle.

### `functions` — explore a function

Input: one or more **named** definitions, one per row — `f(x) = 2x + 3`,
`g(x) = x^2`. A row may reference an earlier name, so composition is written
directly as `h(x) = f(g(x))`. Produces:

- Sliders auto-generated for each free parameter — a symbol that is neither the
  bound variable nor a defined function name. `f(x) = a*x^2 + b` yields `a`, `b`.
- A **value trace**: pick an `x`, and one step per hop — x-axis → curve →
  y-axis. For a composition the trace expands to one hop per nested call, inner
  to outer, so with `f(x) = 2x` and `g(x) = x^2`, `h(4)` steps through
  `g(4) = 16` then `f(16) = 32`. A hop that has no real value — `sqrt` below
  zero, `1/x` at zero — stops the trace with a step saying so, rather than
  raising.

Covers the function types in the Discrete Maths vault: linear, quadratic,
exponential, logarithmic, floor, ceiling.

---

## 5. Project structure

One purpose per file. **Any file crossing ~200 lines gets split.**

```
mathview/
├── pyproject.toml              uv + ruff, hatchling, src layout
├── README.md
├── mathview.desktop
├── docs/superpowers/specs/
├── src/mathview/
│   ├── cli.py                  typer: `mathview` | `mathview --web`
│   ├── shell.py                PyQt5 QtWebEngine window
│   ├── server.py               FastAPI routes
│   ├── core/
│   │   ├── step.py             Step, Sequence, VisualSpec
│   │   ├── parse.py            text → SymPy, structured errors
│   │   └── registry.py         topic lookup
│   └── topics/
│       ├── growth.py
│       ├── functions.py
│       ├── definitions.py      named rows, reference resolution
│       ├── tracing.py          walking a value through calls
│       ├── sampling.py         expression → plottable points
│       ├── crossover.py        crossing detection and validation
│       └── asymptotics.py      dominance order, Big-O class
├── web/
│   ├── index.html
│   ├── css/tokens.css          palette — single source of truth
│   ├── css/app.css
│   └── js/
│       ├── app.js              state + wiring
│       ├── steps.js            step list, view toggle
│       └── render/
│           ├── registry.js     kind → renderer
│           └── plot2d.js       canvas drawing
└── tests/                      mirrors src/
```

### The rule that keeps the codebase small

**All logic lives in Python; JavaScript only draws.** Crossover solving,
sampling, axis ranges and tick selection are computed into the `VisualSpec`.
`plot2d.js` receives finished numbers and strokes paths. The JS stays a few
hundred lines, needs no test toolchain of its own, and holds no logic to test.

---

## 6. Palette

Reference: the Oblivity aim trainer — matte black and dark grey ground, red
identity, bright neon marking the data.

```
GROUND                 IDENTITY  (chrome only, never a data series)
#08080a  page          #ff2740  signal red — active tab, focus ring,
#121215  panel                              current-step marker   5.0:1
#1c1c21  input         #8c0f1e  deep red   — pressed states
#2a2a31  grid
                       SERIES  (neon — data only, cool to hot)
TEXT                   slot 1  #2cdcff  cyan     O(1)
#f4f4f6  primary 17.0  slot 2  #00c571  green    O(log n)
#9a9aa6  second   6.7  slot 3  #ffdf1f  yellow   O(n)
#6a6a76  muted    3.5  slot 4  #ff8734  orange   O(n log n)
                       slot 5  #ff4a9a  pink     O(n²)
                       slot 6  #b4a9ff  violet   O(2ⁿ)
```

**Rules:**

- Red is chrome only. Never a data series — this is what prevents "is that line
  important, or just selected?" confusion. Same discipline as `stock-manager`'s
  neon accent.
- Series assigned by slot order per series identity. Never cycle, never repaint
  on filtering.
- For `growth`, slot order follows complexity order, so the ramp runs cool → hot
  as growth worsens and the palette itself carries meaning.
- "Glossy" is a subtle panel gradient plus canvas `shadowBlur` glow per curve.
- All values live in `web/css/tokens.css` as custom properties. No hex literal
  appears anywhere else in the codebase.

**Validation outcome.** Measured with the dataviz palette checker against the
panel: colour-blind separation ΔE 14.4 (target 8), normal-vision ΔE 19.2, all
six series above 3:1 contrast. It deliberately fails the checker's dark-mode
lightness band (L 0.48–0.67). That band guards against colours washing out
toward white on a dark ground; the measured separation numbers show that is not
happening here. The band-compliant alternative was muted — teal, olive, brown —
and traded the band pass for two series below 3:1 contrast, which is a real
readability cost and not the look this app is for.

## 7. Testing

pytest, mirroring `src/`:

- `test_parse.py` — valid expressions, and malformed input producing correct
  error offsets.
- `test_growth.py` — crossover maths against known values (`n² = 100n` at
  n = 100), dominance ordering, Big-O classification.
- `test_functions.py` — parameter detection, trace step generation.
- `test_step.py` — `VisualSpec` serialisation round-trip.

No JS test toolchain, per the logic-in-Python rule.

---

## 8. Out of scope for Phase 1

Deferred, each a self-contained later module against the same engine:

| Module           | Adds                                            |
| ---------------- | ----------------------------------------------- |
| Induction proofs | base case / hypothesis / inductive step steps    |
| Automata & TMs   | `kind: "automaton"` renderer, tape animation     |
| Sets & relations | `kind: "venn"`, `kind: "mapping"` renderers      |
| Graphs & trees   | `kind: "graph"` node-link renderer               |
| Vault read/write | Obsidian integration in either direction         |
