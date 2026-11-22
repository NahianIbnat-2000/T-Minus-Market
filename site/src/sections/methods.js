// Data and methods: the final section of the single page. All values come from data.
import { escapeHtml, tLabel } from "../format.js";
import { STAGES } from "../components/stageNav.js";

const win = (w) => `${tLabel(w[0])} to ${tLabel(w[1])}`;

export function methodsSection({ manifest: m, results: r }) {
  const s = r.settings || {};
  return `<section class="stage methods" id="methods" aria-labelledby="h-methods"><div class="wrap">
  <div class="stage-label"><span class="t">${STAGES.find((x) => x.id === "methods").t}</span><span>Data and methods</span></div>
  <h2 id="h-methods">How this study was done</h2>
  <p>Main window ${win(s.windows?.primary || [0, 1])}; market model estimated over trading days ${win(s.estimation_window || [-250, -30])}; independent events are failures that share a firm within ${escapeHtml(s.cluster_gap)} trading days. The rules were fixed and committed before any stock reaction was measured; checks added later are labelled exploratory.</p>
  <p>Sources, sample definitions, event timing, firm classification, the tests, data quality and replication are documented on one page:</p>
  <p class="r-actions"><a class="btn" href="../methods.html">Data &amp; Methods</a> <a class="btn ghost" href="../paper.html">Paper</a></p>
  </div></section>`;
}
