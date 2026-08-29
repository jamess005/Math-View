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
  // Both classes are needed: one collapses the canvas column, the other hands
  // the freed vertical space to the step panel. Without the second, notation
  // mode leaves a large empty void where the canvas used to be.
  document.body.classList.toggle("notation-only", view === "notation");
  document.getElementById("main").classList.toggle(
    "notation-only", view === "notation"
  );
  for (const button of document.querySelectorAll(".views button")) {
    button.classList.toggle("active", button.dataset.view === view);
  }
}
