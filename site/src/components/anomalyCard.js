// Mission Anomaly Report card: one per provider failure (and reusable for rival events).
import { ci, date, escapeHtml, pct, signClass, tLabel } from "../format.js";

/**
 * @param {object} rec   firm_events.json record
 * @param {object} cs    matching results.provider_case_series entry (has 95% intervals)
 * @param {number} index report number
 */
export function anomalyCard(rec, cs, index) {
  const car = rec.windows.primary.car;
  const lo = cs?.car_primary_ci?.[0], hi = cs?.car_primary_ci?.[1];
  const robust = rec.windows.robust.car;
  const no = String(index).padStart(2, "0");
  return `<li class="anomaly" aria-labelledby="anomaly-${no}">
    <header><span class="no">ANOMALY REPORT No. ${no}</span><span class="stamp" aria-hidden="true">ANOMALY</span></header>
    <h3 id="anomaly-${no}">${escapeHtml(rec.vehicle)}, ${date(rec.day0)}</h3>
    <dl>
      <dt>Launch</dt><dd class="mono">${escapeHtml(rec.launch_tag)}</dd>
      <dt>Listed firm</dt><dd>${escapeHtml(rec.firm)} <span class="mono">(${escapeHtml(rec.ticker)})</span></dd>
      <dt>Day 0</dt><dd>${date(rec.day0)} <span class="muted">(${escapeHtml(rec.exchange)})</span></dd>
      <dt>Model</dt><dd>${rec.model === "market_model" ? "Market model" : "Market-adjusted (short history)"}</dd>
    </dl>
    <div class="finding">
      <span class="muted">Post-flight finding: two-day abnormal return, T0 to T+1</span><br>
      <span class="big ${signClass(car)}">${pct(car)}</span><br>
      <span class="mono">95% interval ${Number.isFinite(lo) ? ci(lo, hi) : "n/a"}</span><br>
      <span class="muted">${tLabel(-1)} to ${tLabel(3)}: ${pct(robust)}</span>
    </div>
    ${rec.flag ? `<p class="flag">Note: ${escapeHtml(rec.flag.reason)}.</p>` : ""}
  </li>`;
}
