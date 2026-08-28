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
