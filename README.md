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
  size. A log-scale toggle keeps `n` visible next to `2^n`.
- **Functions** — plot named definitions, drag sliders for free parameters, and
  trace a value through the hops. Compositions are written directly:
  `h(x) = f(g(x))`. A row may only call names defined above it.

## Offline

Everything is vendored — KaTeX ships in `web/vendor/katex` (the two dist files
byte-identical to upstream 0.16.11, woff2 fonts only). The app makes no network
request at all, so notation renders on a train.

## Design

- `docs/superpowers/specs/2026-08-28-mathview-design.md` — the design
- `docs/superpowers/plans/2026-08-28-mathview-phase1.md` — the build plan
- All logic is Python; JavaScript only draws.
- Any file over ~200 lines gets split.
- Every colour lives in `web/css/tokens.css`. No hex literal appears anywhere
  else. The palette is validated for contrast and colour-vision deficiency.

## Known limitations

- `dominance_order` treats a growth comparison SymPy cannot decide as "same
  order", which is not transitive. Every standard complexity class resolves
  symbolically, so this cannot fire for the inputs the topic is for.
- Trigonometric functions draw spikes across their asymptotes rather than
  breaking the line.
