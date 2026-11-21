// Data and methods: the final section of the single page. All values come from data.
import { escapeHtml, tLabel } from "../format.js";

const win = (w) => `${tLabel(w[0])} to ${tLabel(w[1])}`;

export function methodsSection({ manifest: m, results: r }) {
  const s = r.settings || {};
  const checks = (r.robustness || []).map((x) => `<li>${escapeHtml(x.name)}${x.note ? ` <span class="muted">(${escapeHtml(x.note)})</span>` : ""}</li>`).join("");
  return `<section class="stage methods" id="methods" aria-labelledby="h-methods"><div class="wrap">
  <div class="stage-label"><span class="t">Appendix</span><span>Data and methods</span></div>
  <h2 id="h-methods">How this study was done</h2>
  <h3>The rules came first</h3>
  <p>Every choice below was fixed and committed to version control before any stock reaction was measured (commit record: working paper, Appendix G). It was not filed with an independent registry. Checks added after seeing results are labelled exploratory everywhere in this report.</p>
  <h3>Data</h3>
  <table><tbody>
    <tr><th scope="row">Launches</th><td>${escapeHtml(m.sources?.launches)}</td></tr>
    <tr><th scope="row">Failure</th><td>Orbital or deep-space launch with a GCAT success score below 0.75 (GCAT's own pass or fail line).</td></tr>
    <tr><th scope="row">Prices</th><td>${escapeHtml(m.sources?.prices)}. Each firm's prices are used only from the day after its verified listing date, so earlier shell-company (SPAC) prices never enter.</td></tr>
    <tr><th scope="row">Published data</th><td>${escapeHtml(m.data_policy)}</td></tr>
  </tbody></table>
  <h3>Model</h3>
  <table><tbody>
    <tr><th scope="row">Expected return</th><td>Market model on each firm's home index, estimated over trading days ${win(s.estimation_window || [-250, -30])}; at least ${escapeHtml(s.min_obs)} days, otherwise market-adjusted returns (flagged).</td></tr>
    <tr><th scope="row">Returns</th><td>Simple daily returns.</td></tr>
    <tr><th scope="row">Main window</th><td>${win(s.windows?.primary || [0, 1])}</td></tr>
    <tr><th scope="row">Robustness window</th><td>${win(s.windows?.robust || [-1, 3])}</td></tr>
    <tr><th scope="row">Descriptive window</th><td>${win(s.windows?.descriptive || [0, 20])}</td></tr>
    <tr><th scope="row">Day 0</th><td>First trading session at or after the failure became public, on each firm's own exchange calendar.</td></tr>
    <tr><th scope="row">Independent events</th><td>Failures sharing a firm within ${escapeHtml(s.cluster_gap)} trading days form one cluster, the unit of inference.</td></tr>
  </tbody></table>
  <h3>Tests</h3>
  <p><strong>Main test:</strong> the standardized cross-sectional test of Boehmer, Musumeci and Poulsen (1991), with the Kolari and Pynnonen (2010) adjustment for correlation between firms reacting to the same failure. Applying that adjustment within clusters across many event dates is this study's extension of the single-date case in the original paper. Two-sided, 5% level; p-values from a t distribution with (clusters minus one) degrees of freedom; 95% intervals are cluster-robust.</p>
  <p><strong>Prespecified checks:</strong></p><ul>${checks}</ul>
  <p><strong>Placebo benchmark:</strong> ${escapeHtml(r.placebo?.draws)} draws of random non-event days, seed ${escapeHtml(r.placebo?.seed)}. A benchmark for context, not an exact permutation test.</p>
  <h3>References</h3>
  <ul class="refs">
    <li>Boehmer, E., Musumeci, J. and Poulsen, A. (1991). Event-study methodology under conditions of event-induced variance. <em>Journal of Financial Economics</em> 30(2), 253-272.</li>
    <li>Kolari, J. and Pynnonen, S. (2010). Event study testing with cross-sectional correlation of abnormal returns. <em>Review of Financial Studies</em> 23(11), 3996-4025.</li>
    <li>Corrado, C. (1989). A nonparametric test for abnormal security-price performance in event studies. <em>Journal of Financial Economics</em> 23(2), 385-395.</li>
    <li>Lang, L. and Stulz, R. (1992). Contagion and competitive intra-industry effects of bankruptcy announcements. <em>Journal of Financial Economics</em> 32(1), 45-60.</li>
    <li>Bosch, J.-C., Eckard, E. W. and Singal, V. (1998). The competitive impact of air crashes: stock market evidence. <em>Journal of Law and Economics</em> 41(2), 503-519.</li>
    <li>McDowell, J. C. GCAT: General Catalog of Artificial Space Objects. planet4589.org/space/gcat.</li>
  </ul>
  </div></section>`;
}
