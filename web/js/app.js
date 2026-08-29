// State, fetching and wiring. All maths happens on the server.

import { render } from "./render/registry.js";
import "./render/plot2d.js";
import { initSplitters } from "./splitters.js";
import { applyView, renderSteps, state } from "./steps.js";

const DEFAULTS = {
  growth: ["n", "n*log(n)", "n^2", "2^n"],
  functions: ["f(x) = 2x", "g(x) = x^2", "h(x) = f(g(x))"],
};

const MAX_ROWS = 6;
// Names the add button can reach for. A row may only call names defined above
// it, and a repeated name is rejected, so a fixed literal would fail on the
// second click.
const NAME_POOL = "fghkpqrstuvw".split("");

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

function nextFreeName() {
  const used = new Set(
    rows.map((row) => (row.split("=")[0].match(/[A-Za-z]\w*/) || [])[0])
  );
  return NAME_POOL.find((name) => !used.has(name)) ?? "z";
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

    const remove = document.createElement("button");
    remove.className = "remove";
    remove.textContent = "\u00d7";
    remove.title = "remove this row";
    remove.disabled = rows.length === 1;
    remove.onclick = () => { rows.splice(i, 1); renderRows(); refresh(); };

    row.append(swatch, input, remove);
    rowsBox.append(row);
  });
  document.getElementById("add").disabled = rows.length >= MAX_ROWS;
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
  if (rows.length >= MAX_ROWS) return;
  rows.push(topic() === "growth" ? "n" : `${nextFreeName()}(x) = x`);
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

// The canvas element changes size for reasons other than a window resize: a
// step with a tall table grows the panel, and the drag handles resize it
// directly. Without this the bitmap keeps its old size and the previous frame
// shows through underneath the step panel.
new ResizeObserver(drawCurrentStep).observe(canvas);

initSplitters(drawCurrentStep);

window.addEventListener("resize", drawCurrentStep);

applyView("both");
renderRows();
refresh();
