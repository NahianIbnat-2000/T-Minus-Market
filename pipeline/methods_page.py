"""Data & Methods page (methods.html at the site root).

A reference page: how the data were built, how events and firms are defined, how the model and tests work, what can
go wrong with the data, and how to reproduce everything. It is written as structured definitions, not prose, and it
links to the working paper for derivations, so the two pages do not repeat each other. Every count is read from the
exported data; nothing is typed in by hand.
"""
from __future__ import annotations

import html
from collections import Counter
from pathlib import Path

e = html.escape


def build(data: dict, meta: dict, root: Path, css: str, pdf_name: str | None) -> str:
    import casestudy as CS
    import diagnostics as D
    import landing as L
    import sitechrome as SC

    f = L.facts(data)
    res, man, fails, fes = data["results"], data["manifest"], data["failures"], data["firmEvents"]
    p, pl = f["prim"], f["placebo"]
    st = res.get("settings") or {}
    sample = man.get("sample") or {}
    est = st.get("estimation_window", [-250, -30])
    win = st.get("windows", {"primary": [0, 1], "robust": [-1, 3], "descriptive": [0, 20]})
    t = lambda k: f"T{win[k][0]:+d} to T{win[k][1]:+d}".replace("T+0", "T0").replace("+", "+").replace("-", "−")
    span = f"{f['first_year']} to {f['last_year']}" if f["first_year"] else ""
    repo = meta.get("repo_url")
    blob = (repo.rstrip("/") + "/blob/master/") if repo else None
    tm = D.timing(fes)
    riv = [r for r in fes if r["group"] == "rival"]
    tc = tm["rival_reactions"]["counts"]
    flags = Counter((r.get("flag") or {}).get("verdict") for r in riv if r.get("flag"))
    nodes, edges = CS.sample_graph(sample, f, p)
    why = Counter()
    for x in fails:
        if not (x.get("in_rival_test") or x.get("in_provider_case_series")):
            for code in str(x.get("why_not_in_sample") or "no listed maker or listed competitor").split(";"):
                why[CS.WHY.get(code.strip(), code.strip().replace("_", " "))] += 1
    drops = sample.get("failure_firm_events_dropped") or {}
    robust = [r for r in (res.get("robustness") or []) if r.get("name")]
    year = str(man.get("results_run_utc", ""))[:4]
    updated = L.month(man.get("results_run_utc")) if man.get("results_run_utc") else ""

    def row(k, v):
        return f"<tr><th scope=\"row\">{k}</th><td>{v}</td></tr>"

    def tbl(caption, rows):
        return (f'<div class="table-wrap" tabindex="0" role="region" aria-label="{e(caption)}"><table class="def">'
                f'<caption>{e(caption)}</caption><tbody>{"".join(row(k, v) for k, v in rows)}</tbody></table></div>')

    sections = [("sources", "Data sources"), ("sample", "Sample definitions"), ("events", "Event identification and timing"),
                ("firms", "Firm classification"), ("model", "Market model and event windows"), ("inference", "Statistical inference"),
                ("robust", "Robustness procedures"), ("quality", "Data quality and limitations"), ("replicate", "Replication")]
    toc = "".join(f'<li><a href="#{k}">{i}. {e(v)}</a></li>' for i, (k, v) in enumerate(sections, 1))

    sample_rows = [
        ("Historical launch failures", f"<strong>{f['n_failures']}</strong> orbital launch attempts, {e(span)}, with a GCAT success score below 0.75. Pad explosions before launch are kept separately."),
        ("Failures in the study", f"<strong>{e(str(sample.get('failures_in_study', 'n/a')))}</strong> failures with a listed maker or at least one listed Tier 1 or 2 rival." if sample else "Failures with a listed maker or a listed Tier 1 or 2 rival."),
        ("Listed-maker cases", f"<strong>{f['n_cases']}</strong> failures whose rocket was built by a listed company ({e(', '.join(f['case_firms']))}). Reported one by one as case studies."),
        ("Failures with listed rivals", f"<strong>{f['n_rival_failures']}</strong> failures with at least one listed rival that has a usable price history."),
        ("Rival reactions (firm-events)", f"<strong>{p['n_firm_events']}</strong>: one per listed rival per failure. The unit of each CAR, not an independent observation."),
        ("Independent events (clusters)", f"<strong>{f['n_clusters']}</strong>: failures that share a firm within {st.get('cluster_gap', 5)} trading days form one cluster. The unit of inference."),
        ("Distinct listed rivals", f"<strong>{f['n_rival_firms']}</strong>: {e(', '.join(f['rival_names']))}."),
    ]
    timing_rows = [
        ("Day 0", "The first trading session at or after the failure became public, on the stock's own exchange calendar (holidays and half days included)."),
        ("Overnight and after-hours events", "A failure that becomes public after the close, at night or on a non-trading day moves day 0 to the next session of that exchange."),
        ("Disclosure-time sources", f"Company statement, high confidence: {tc.get('high', 0)} rival reactions. Company statement, low confidence: {tc.get('low', 0)}. GCAT launch time, not separately verified: {tc.get('provisional', 0)} (of {tm['rival_reactions']['n']}). Maker cases using GCAT time: {tm['maker_cases']['counts'].get('provisional', 0)} of {tm['maker_cases']['n']}."),
        ("When GCAT time is allowed", "Only where day 0 would not change if the true disclosure came 10 minutes earlier or up to 180 minutes later. Otherwise a sourced time is required; no time is invented."),
        ("Sensitivity", "Check R5 drops or shifts the uncertain disclosure times."),
    ]
    firm_rows = [
        ("Maker", "The company that built the failed rocket, if listed at the time of the failure."),
        ("Tier 1 rival", "Listed; launch is a pure-play or major business; sells a rocket of the same size class to the same customer market; has flown that rocket in the previous 730 days."),
        ("Tier 2 rival", "Listed and close, but missing one Tier 1 condition (recorded per row in the firm map). Enters the test with Tier 1."),
        ("Tier 3", "Diversified aerospace groups where launch is a minor business. Descriptive only, never in the test."),
        ("Point in time", "Each link uses listing dates, ownership and exposure as they were on the failure date (<code>data/manual/firm_map.csv</code>, <code>data/manual/vehicle_segments.csv</code>). Prices from before a firm's real listing (a pre-merger shell company) are dropped."),
    ]
    model_rows = [
        ("Returns", "Simple daily returns from adjusted closes; CARs are sums of simple abnormal returns."),
        ("Benchmark", "Each firm's home market index."),
        ("Expected return", f"Market model by OLS on trading days {e(str(est[0]))} to {e(str(est[1]))} before day 0; at least {e(str(st.get('min_obs', 100)))} returns. With 30 to 99 returns, a market-adjusted model (alpha 0, beta 1), flagged. Fewer: dropped."),
        ("Abnormal return", "Actual return minus the market-model prediction."),
        ("CAR variance", "Includes the prediction error of the estimated model (window length, estimation length and market moves in the window)."),
        ("Main window", f"{t('primary')}: the confirmatory test (H2)."),
        ("Wider window", f"{t('robust')}: robustness check R4."),
        ("One-month window", f"{t('descriptive')}: description only."),
    ]
    inf_rows = [
        ("Prespecified test", f"Standardized test of Boehmer, Musumeci and Poulsen (1991), with the Kolari and Pynnönen (2010) correction for correlation between rivals reacting to the same failure, applied within clusters. Null: mean standardized CAR is zero. p from a t distribution with clusters minus one degrees of freedom. Result: <strong>p = {e(L.pval(p['p']))}</strong>."),
        ("Mean test", f"Cluster-robust test of the plain equal-weighted average CAR (the published estimate, {e(L.pct(p['mean_car'], 2))}, 95% interval {e(L.pct(p['ci_low'], 2))} to {e(L.pct(p['ci_high'], 2))})" + (f", <strong>p = {e(L.pval(f['pA']))}</strong>" if f.get("pA") is not None else "") + ", with a wild cluster bootstrap as a check."),
        ("Why two p-values", "The standardized test gives volatile stocks less weight; the mean test weights every reaction equally. They test different quantities, so their p-values are not interchangeable. Each is reported next to the quantity it tests."),
        ("Weighting", "Averages that weight every event, every firm, or calmer stocks more answer different questions. When one firm has many reactions, weighting firms equally can change the sign. These are sensitivity analyses added after the results; none is statistically preferred."),
        ("Power", (f"Minimum detectable average effect about {e(L.pct(f['pw']['mde80'], 1, False))} (80% power, 5% level); not detecting an effect does not show that there is none." if f.get("pw") else "Reported in the paper.")),
        ("Maker cases", "Each CAR with a 95% interval of CAR ± 1.96 prediction-error standard deviations. No average is tested."),
    ]
    rob_items = "".join(f"<li>{e(r['name'])}{(' <span class=\"muted\">(' + e(r['note']) + ')</span>') if r.get('note') else ''}</li>" for r in robust)
    quality = [
        ("Announcement timestamps", "Sourced company statements where available; otherwise GCAT launch times under the rule above."),
        ("GCAT launch-time proxies", f"{tc.get('provisional', 0)} of {tm['rival_reactions']['n']} rival reactions rely on them. Clock or time-zone errors beyond the allowed band would shift day 0."),
        ("Trading calendars", "Each exchange's own calendar (Milan, Nasdaq, NYSE). A failure can fall on different calendar days for different rivals."),
        ("Confounding company news", f"News around the largest reactions was checked against public sources ({', '.join(f'{v} {k.replace(chr(95), chr(32))}' for k, v in flags.items()) or 'none flagged'}). Flagged reactions stay in the confirmatory test; dropping them is exploratory (E1 to E3)."),
        ("Overlapping launch events", f"Failures sharing a firm within {st.get('cluster_gap', 5)} trading days are one cluster; check R7 drops multi-failure clusters."),
        ("Missing return data", ("Firm-events dropped at the price-coverage step: " + ", ".join(f"{e(k.replace('_', ' '))} {v}" for k, v in drops.items()) + ".") if drops else "Firm-events without a full window or estimation history are dropped and counted in the paper (Appendix E)."),
        ("Thin trading and volatility", "Young listed firms are volatile; the standardized test scales each CAR by its own uncertainty, and fallback-model events are dropped in check R6."),
        ("Survivorship", "Listed launch firms that later delisted (Orbital Sciences/Orbital ATK, Astra, Virgin Orbit) are absent from the free price source."),
        ("What is published", e(man.get("data_policy") or "Only derived statistics; prices are never republished.")),
    ]
    steps = [("01_ingest_launches.py", "Download GCAT and classify launches"), ("02_map_firms.py", "Apply the point-in-time firm map"),
             ("03_pull_prices.py", "Download prices (Yahoo Finance, not redistributed)"), ("04_check_coverage.py", "Coverage and feasibility gate"),
             ("05_event_study.py", "Prespecified analysis (H2, checks R1 to R9)"), ("06_confounding_sensitivity.py", "Exploratory confounding checks"),
             ("07_export_site_data.py", "Export derived statistics to site/data/"), ("08_build_html.py", "Build this site and the paper"),
             ("09_audit_exploratory.py", "Exploratory audit checks (R9b)")]
    step_rows = "".join(f"<tr><td><code>python pipeline/{e(a)}</code></td><td>{e(b)}</td></tr>" for a, b in steps)
    ev = [("Feasibility report (written before results)", "reports/04_feasibility_report.md"), ("Results report", "reports/05_results.md"),
          ("Confounding-news checks", "docs/CONFOUNDING_NEWS.md"), ("Independent audit", "audit/AUDIT_REPORT.md"),
          ("Verification of published statistics", "audit/VERIFICATION.md"), ("Reproduction guide", "README.md")]
    ev_html = "".join(f'<li><a href="{e(blob + path)}">{e(lab)}</a></li>' for lab, path in ev) if blob else ""

    body = f"""<a class="skip-link" href="#main">Skip to content</a>
{SC.header("methods", "", bool(pdf_name), repo)}
<header class="paper-head"><div class="wrap ph-in">
  <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="index.html">Overview</a></li><li aria-current="page">Data &amp; Methods</li></ol></nav>
  <h1>Data &amp; Methods</h1>
  <p class="dek">How the sample was built, how events and firms are defined, how abnormal returns are tested, what can go wrong with the data, and how to reproduce every number. The full derivations are in the <a href="case-study.html">research paper</a>.</p>
  <p class="byline">Rules version v{e(str(res.get('plan_version', '')))} · results {e(updated)}</p>
</div></header>
<div class="wrap paper-grid">
<aside class="paper-toc" aria-label="On this page"><p class="pt-h">On this page</p><ol>{toc}</ol></aside>
<main id="main" class="article cs methods-page">
<section id="sources"><h2>1. Data sources</h2>
{tbl("Data sources", [("Launches", e(man.get("sources", {}).get("launches") or "GCAT, J. McDowell, CC-BY")),
                      ("Prices", e(man.get("sources", {}).get("prices") or "Yahoo Finance") + ". Used on the author's computer only."),
                      ("Firm map", "Hand-built, point in time, with a source for every row (<code>data/manual/</code>)."),
                      ("Disclosure times", "Company statements with sources and confidence (<code>data/manual/disclosure_times.csv</code>).")])}
</section>
<section id="sample"><h2>2. Sample definitions</h2>
<p>The counts measure different units. Firm-event reactions are not independent events.</p>
{f'<figure class="cs-fig">{CS.fig_sample(nodes, edges)}<figcaption class="cs-cap">Sample construction. Each box gives a count and its unit. Source: GCAT and the project pipeline.</figcaption></figure>' if nodes else ''}
{tbl("Sample definitions", sample_rows)}
{tbl("Failures not in the study, by reason (a failure can have several)", [(e(k), str(v)) for k, v in why.most_common()]) if why else ''}
</section>
<section id="events"><h2>3. Event identification and timing</h2>{tbl("Event timing rules", timing_rows)}</section>
<section id="firms"><h2>4. Firm classification</h2>{tbl("Firm classification", firm_rows)}</section>
<section id="model"><h2>5. Market model and event windows</h2>{tbl("Model and windows", model_rows)}
<p>Equations: <a href="case-study.html#s5">paper, section 5</a>.</p></section>
<section id="inference"><h2>6. Statistical inference</h2>{tbl("Tests and estimands", inf_rows)}
<p>Estimands and the four weightings: <a href="case-study.html#s5">paper, section 5.1</a>; sample concentration: <a href="case-study.html#s6">section 6.3</a>.</p></section>
<section id="robust"><h2>7. Robustness procedures</h2>
<p><span class="badge confirm">Prespecified</span> {len(robust)} checks fixed before the results:</p><ul class="method">{rob_items}</ul>
<p><span class="badge robust">Benchmark</span> Placebo R9: {e(str(pl.get('draws', '')))} sets of random ordinary trading days (seed {e(str(pl.get('seed', '')))}), one per reaction. The real result's percentile is a description, not a p-value.</p>
<p><span class="badge explore">Exploratory</span> Analyses designed after the results (confounding drops E1 to E3, weighting, a shared-date placebo R9b) are labelled wherever they appear and never replace the prespecified test. Results: <a href="case-study.html#s7">paper, sections 7 and 8</a>.</p></section>
<section id="quality"><h2>8. Data quality and limitations</h2>{tbl("Data quality", quality)}</section>
<section id="replicate"><h2>9. Replication</h2>
<p>Python 3.11+, <code>pip install -r requirements.txt</code>, then run the steps in order. Prices are downloaded on your machine and never committed.</p>
<div class="table-wrap" tabindex="0" role="region" aria-label="Pipeline steps"><table><caption>Pipeline steps</caption><thead><tr><th scope="col">Command</th><th scope="col">What it does</th></tr></thead><tbody>{step_rows}
<tr><td><code>python audit/verify_published.py</code></td><td>Recompute every published statistic independently</td></tr>
<tr><td><code>python -m pytest tests</code></td><td>Test suite</td></tr></tbody></table></div>
{f'<p class="r-actions"><a class="btn small" href="{e(repo)}">Source code on GitHub</a></p><h3>Supporting evidence</h3><ul class="method">{ev_html}</ul>' if repo else ''}
<h3>References</h3>
<ul class="refs">
<li>Boehmer, E., Musumeci, J. and Poulsen, A. B. (1991). Event-study methodology under conditions of event-induced variance. <em>Journal of Financial Economics</em> 30(2), 253-272.</li>
<li>Kolari, J. W. and Pynnönen, S. (2010). Event study testing with cross-sectional correlation of abnormal returns. <em>Review of Financial Studies</em> 23(11), 3996-4025.</li>
<li>Campbell, J. Y., Lo, A. W. and MacKinlay, A. C. (1997). <em>The Econometrics of Financial Markets</em>. Princeton University Press.</li>
<li>McDowell, J. C. GCAT: General Catalog of Artificial Space Objects. planet4589.org/space/gcat.</li>
</ul></section>
</main></div>
{SC.footer("", meta, bool(pdf_name), SC.cite(year, meta))}"""
    desc = "Data and methods of Space Shock: sources, sample definitions, event timing, firm classification, the market model, tests, data quality and replication."
    url = (meta["live_url"].rstrip("/") + "/methods.html") if meta.get("live_url") else None
    return L._shell("Data & Methods · Space Shock", desc, url, body, css, url, None, body_class="paper methods")
