// Report section navigation (sticky). Marks the stage in view with aria-current="step".
export const STAGES = [
  { id: "t-3", t: "1", name: "Question" },
  { id: "t-2", t: "2", name: "Failures" },
  { id: "t-1", t: "3", name: "Method" },
  { id: "t0", t: "4", name: "Results" },
  { id: "t+1", t: "5", name: "Checks" },
  { id: "methods", t: "6", name: "Data & methods" },
];

export function stageNavHtml() {
  return `<nav class="stage-nav" aria-label="Report stages"><ol>${
    STAGES.map((s) => `<li><a href="#${s.id}"><span class="t">${s.t}</span>${s.name}</a></li>`).join("")
  }</ol></nav>`;
}

export function watchStages(root = document) {
  const links = new Map(STAGES.map((s) => [s.id, root.querySelector(`.stage-nav a[href="#${s.id}"]`)]));
  const set = (id) => links.forEach((a, k) => (k === id ? a?.setAttribute("aria-current", "step") : a?.removeAttribute("aria-current")));
  if (!("IntersectionObserver" in window)) return;
  const obs = new IntersectionObserver((entries) => {
    const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
    if (vis[0]) set(vis[0].target.id);
  }, { rootMargin: "-20% 0px -60% 0px" });
  STAGES.forEach((s) => { const el = root.getElementById(s.id); if (el) obs.observe(el); });
}
