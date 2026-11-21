// Countdown stage indicator: T-3 ... T+1. Marks the stage in view with aria-current="step".
export const STAGES = [
  { id: "t-3", t: "T−3", name: "The Question" },
  { id: "t-2", t: "T−2", name: "The Failures" },
  { id: "t-1", t: "T−1", name: "The Method" },
  { id: "t0", t: "T0", name: "The Reaction" },
  { id: "t+1", t: "T+1", name: "Is It Real?" },
  { id: "methods", t: "\u00a7", name: "Methods" },
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
