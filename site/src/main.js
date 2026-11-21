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
    const m = data.manifest;
    document.getElementById("run-info").innerHTML =
      `Results computed ${date(m.results_run_utc)} · data exported ${date(m.exported_utc)}`;
    watchStages(document);
    mountLab(document, data);
    mountPlacebo(document, data);
    mountTimeline(document, data);
    mountExplainer(document);
  } catch (err) {
    main.innerHTML = `<div class="wrap"><p role="alert">The data could not be loaded: ${escapeHtml(err.message)}.
      Run <code>python pipeline/07_export_site_data.py</code> to create <code>site/data/</code>.</p></div>`;
    console.error(err);
  }
}

start();
