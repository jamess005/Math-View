// Draggable dividers between the rail, the canvas and the step panel.
//
// The sizes live in CSS custom properties on :root, so the grid templates in
// app.css stay declarative and nothing here has to know the layout. They are
// remembered per browser: a size you dragged is a preference, not state the
// server should hold.

const STORE = "mathview.layout";

const clamp = (value, lo, hi) => Math.min(Math.max(value, lo), hi);

function save(rail, steps) {
  try {
    localStorage.setItem(STORE, JSON.stringify({ rail, steps }));
  } catch {
    // A private window or blocked site data is not a reason to fail a drag.
  }
}

function restore() {
  try {
    return JSON.parse(localStorage.getItem(STORE) ?? "{}");
  } catch {
    return {};
  }
}

function apply(name, value) {
  document.documentElement.style.setProperty(name, `${value}px`);
}

export function initSplitters(onResize) {
  const root = document.documentElement;
  const saved = restore();
  if (saved.rail) apply("--rail-w", saved.rail);
  if (saved.steps) apply("--steps-h", saved.steps);

  const current = () => ({
    rail: parseFloat(getComputedStyle(root).getPropertyValue("--rail-w")) || 260,
    steps: parseFloat(getComputedStyle(root).getPropertyValue("--steps-h")) || 260,
  });

  function drag(handle, move) {
    handle.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      handle.setPointerCapture(event.pointerId);
      handle.classList.add("dragging");
      const start = current();

      const onMove = (e) => {
        move(e, start);
        onResize();
      };
      const onUp = (e) => {
        handle.releasePointerCapture(e.pointerId);
        handle.classList.remove("dragging");
        handle.removeEventListener("pointermove", onMove);
        handle.removeEventListener("pointerup", onUp);
        const now = current();
        save(now.rail, now.steps);
      };
      handle.addEventListener("pointermove", onMove);
      handle.addEventListener("pointerup", onUp);
    });
    // Double-click restores the default, which is quicker than dragging back.
    handle.addEventListener("dblclick", () => {
      root.style.removeProperty(handle.id === "split-x" ? "--rail-w" : "--steps-h");
      const now = current();
      save(now.rail, now.steps);
      onResize();
    });
  }

  drag(document.getElementById("split-x"), (event) => {
    apply("--rail-w", clamp(event.clientX, 180, window.innerWidth - 320));
  });

  drag(document.getElementById("split-y"), (event) => {
    const fromBottom = window.innerHeight - event.clientY;
    apply("--steps-h", clamp(fromBottom, 90, window.innerHeight - 220));
  });
}
