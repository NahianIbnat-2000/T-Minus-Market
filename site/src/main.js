import { loadAll } from "./data.js";
import { stageNavHtml, watchStages } from "./components/stageNav.js";
import { renderReport } from "./sections/render.js";
import { date, escapeHtml } from "./format.js";
import { mountLab } from "./tools/lab.js";
import { mountPlacebo } from "./tools/placebo.js";
import { mountTimeline } from "./tools/timeline.js";
import { mountExplainer } from "./tools/explainer.js";

async function start() {
  const main = document.getElementById("main");
  document.getElementById("stage-nav-slot").outerHTML = stageNavHtml();
  try {
    const data = await loadAll();
    main.innerHTML = renderReport(data);
    // tables scroll sideways on phones: make them reachable by keyboard
    main.querySelectorAll("table").forEach((t) => t.setAttribute("tabindex", "0"));
    const m = data.manifest;
    document.getElementById("run-info").innerHTML =
      `Results computed ${date(m.results_run_utc)} · data exported ${date(m.exported_utc)}`;
    watchStages(document);
    mountLab(document, data);
    mountPlacebo(document, data);
    mountTimeline(document, data);
    mountExplainer(document);
  } catch (err) {
    main.innerHTML = `<div class="wrap"><div class="load-error" role="alert"><h2>The interactive report could not load its data</h2>
      <p>Reason: ${escapeHtml(err.message)}. The main results are still available in the <a href="../index.html">overview</a> and the
      <a href="../case-study.html">research paper</a>.</p>
      <p class="muted">For maintainers: rebuild with <code>python pipeline/07_export_site_data.py</code> and <code>python pipeline/08_build_html.py</code>.</p></div></div>`;
    const ri = document.getElementById("run-info");
    if (ri) ri.textContent = "data unavailable";
    console.error(err);
  }
}

start();
