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
