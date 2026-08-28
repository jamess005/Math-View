// Cartesian plotting. Receives finished numbers from Python - it computes no
// maths of its own, only the pixel mapping.

import { registerRenderer } from "./registry.js";

const PAD = { left: 64, right: 16, top: 16, bottom: 40 };

function token(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function seriesColour(slot) {
  return token(`--s${slot % 6}`);
}

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
  if (lo === Infinity) return [0, 1];

  if (logMode) {
    const top = hi > 0 ? hi : 1;
    // Floor at the smallest positive sample: anything at or below zero has no
    // log and is drawn as a gap, so it must not drag the axis down with it.
    const bottom = loPositive < Infinity ? loPositive : top / 1e6;
    return [bottom === top ? top / 10 : bottom, top];
  }

  // A curve that dips a hair below zero - log(n) near n=0, against 2^n at
  // 1e15 - must not stretch the axis into the negatives, or every other curve
  // flattens onto the baseline.
  if (lo >= 0 || (hi > 0 && -lo < hi * 0.02)) lo = 0;
  else {
    const pad = (hi - lo) * 0.08;
    lo -= pad;
    hi += pad;
  }
  if (hi === lo) hi = lo + 1;
  return [lo, hi];
}

function makeScales(spec, width, height, logMode) {
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
