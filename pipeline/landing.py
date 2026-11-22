"""Root article page (index.html) for GitHub Pages.

Both are plain static HTML (no JavaScript), so link previews and search engines can read them.
Every number comes from site/data/*.json (written by step 07); nothing is typed by hand.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

MINUS = "−"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@125,600..800&family=DM+Mono:wght@400;500'
         '&family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400&display=swap">')

e = html.escape


def pct(x, d=1, signed=True):
    if x is None:
        return "n/a"
    v = round(x * 100, d)
    if v == 0:
        return f"{0:.{d}f}%"
    s = "+" if v > 0 and signed else (MINUS if v < 0 else "")
    return f"{s}{abs(v):.{d}f}%"


def pval(p):
    if p is None:
        return "n/a"
    return "< 0.001" if p < 0.001 else (f"{p:.3f}" if p < 0.01 else f"{p:.2f}")


def day(iso):
    d = datetime.fromisoformat(str(iso)[:10])
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def month(iso):
    d = datetime.fromisoformat(str(iso)[:10])
    return f"{MONTHS[d.month - 1]} {d.year}"


def ordinal(n):
    n = int(round(n))
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def facts(data: dict) -> dict:
    """All numbers the article uses, derived from the exported data."""
    res, fails, fes = data["results"], data["failures"], data["firmEvents"]
    prim = res["primary"]
    cases = res.get("provider_case_series") or []
    pc = [c["car_primary"] for c in cases if c.get("car_primary") is not None]
    years = [int(str(f["launch_utc"])[:4]) for f in fails if f.get("launch_utc")]
    robust = res.get("robustness") or []
    rob_p = [r for r in robust if r.get("p") is not None]
    pl = res.get("placebo") or {}
    e1 = next((r for r in (res.get("exploratory_confounding") or {}).get("results", []) if r.get("id") == "E1"), None)
    return {
        "n_failures": len(fails), "first_year": min(years) if years else None, "last_year": max(years) if years else None,
        "n_cases": len(pc), "case_lo": min(pc) if pc else None, "case_hi": max(pc) if pc else None,
        "case_firms": sorted({c.get("firm") or c.get("ticker") for c in cases}),
        "prim": prim, "n_rival_failures": prim.get("n_failures"), "n_rival_firms": prim.get("n_firms"),
        "n_clusters": prim.get("n_clusters"), "n_robust": len(rob_p),
        "n_robust_same": sum(1 for r in rob_p if (r["p"] >= 0.05) == (prim["p"] >= 0.05)),
        "placebo": pl, "e1": e1,
        "rival_names": sorted({r["firm"] for r in fes if r["group"] == "rival"}),
        "rob_min": min((r["mean_car"] for r in rob_p), default=None), "rob_max": max((r["mean_car"] for r in rob_p), default=None),
        "rob_min_name": min(rob_p, key=lambda r: r["mean_car"])["name"] if rob_p else None,
        "rob_max_name": max(rob_p, key=lambda r: r["mean_car"])["name"] if rob_p else None,
        "n_robust_sig": sum(1 for r in rob_p if r["p"] < 0.05),
        **_diag(fes, prim, e1),
    }


def _diag(fes, prim, e1):
    import diagnostics as D
    riv = [r for r in fes if r["group"] == "rival"]
    if not riv or prim.get("ci_low") is None:
        return {"w": None, "pw": None, "firms": [], "w_e1": None, "top_firm": None, "top_firm_clusters": 0, "pA": None}
    firms = D.per_firm(fes)
    et = D.estimand_tests(fes, prim, draws=999)
    return {"w": D.weighting(fes), "pw": D.power(prim), "firms": firms, "pA": et["A"]["p"],
            "w_e1": D.weighting(fes, drop=e1.get("dropped") or []) if e1 else None,
            "top_firm": firms[0]["firm"], "top_firm_clusters": firms[0]["clusters"]}


def _shell(title, desc, url, body, css, canonical=None, image=None, body_class=""):
    og_url = e(url) if url else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}"><meta name="author" content="Nahian Ibnat">
<meta property="og:type" content="article"><meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">{f'<meta property="og:url" content="{og_url}">' if og_url else ""}
<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">{f'<meta property="og:image" content="{e(image)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{e(title)}">' if image else ""}{f'<link rel="canonical" href="{e(canonical)}">' if canonical else ""}
{FONTS}
<style>
{css}
</style>
</head>
<body{f' class="{body_class}"' if body_class else ""}>
{body}
</body>
</html>
"""


def article(data: dict, meta: dict, root: Path, css: str) -> str:
    f = facts(data)
    p, pl, e1 = f["prim"], f["placebo"], f["e1"]
    m = data["manifest"]
    updated = month(m.get("results_run_utc") or datetime.now(timezone.utc).isoformat())
    span = f"{f['first_year']} to {f['last_year']}" if f["first_year"] else ""
    detect = "is not statistically detectable" if p["p"] >= 0.05 else "is statistically detectable"
    all_fell = f["case_hi"] is not None and f["case_hi"] < 0
    maker = (f"its shares fell by between {pct(abs(f['case_hi']), 1, False)} and {pct(abs(f['case_lo']), 1, False)}" if all_fell
             else f"its two-day abnormal return ranged from {pct(f['case_lo'])} to {pct(f['case_hi'])}")
    pw, w = f["pw"], f["w"]
    n_firms = f["n_rival_firms"]
    sign_flips = bool(w) and (min(w["observation_weighted"], w["event_weighted"], w["precision_weighted"], w["firm_balanced"]) < 0
                              < max(w["observation_weighted"], w["event_weighted"], w["precision_weighted"], w["firm_balanced"]))
    mde = pw["mde80"] if pw else None
    abstract = (
        f"When an orbital rocket fails, does the stock market punish only the company that built it, or its listed competitors too? "
        f"Using {f['n_failures']} orbital launch failures from {span}, this study measures abnormal stock returns over the two trading days "
        f"after each failure became public, with a market model and a prespecified event-study test. In the {f['n_cases']} cases where the "
        f"rocket's maker was listed, {maker} after allowing for the market. Across {f['n_rival_failures']} failures with listed competitors "
        f"({f['prim']['n_firm_events']} stock reactions, {n_firms} firms, {f['n_clusters']} independent events), the average reaction was "
        f"{pct(p['mean_car'], 2)} (95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}"
        + (f", p = {pval(f['pA'])}" if f.get("pA") is not None else "")
        + f"; the prespecified standardized test gives p = {pval(p['p'])}). "
        + ("The data therefore do not establish either contagion or competitive gains among these firms. " if not p["p"] < 0.05 else "")
        + (f"They also do not show that the effect is small: average reactions of about {pct(mde, 1, False)} in either direction could not "
           f"have been reliably detected. " if mde and p["p"] >= 0.05 else "")
        + f"The evidence comes from {n_firms} listed firms" + (f", with {e(f['top_firm'])} in every independent event" if f["top_firm_clusters"] == f["n_clusters"] else "")
        + (", and the sign of the average changes with how events and firms are weighted." if sign_flips else "."))
    pdf_ok = (root / "case-study.pdf").exists()
    paper_card = ('<div class="read-card"><span class="rc-kicker">Working paper</span><h3>The full study</h3>'
                  '<p><em>Rocket Launch Failures and Equity-Market Spillovers.</em> Methods, results, power, robustness, confounding news, '
                  'limits and appendices.' + (' The same paper is available as a web page and as a PDF.' if pdf_ok else '') + '</p>'
                  '<span class="rc-actions"><a class="rc-go" href="case-study.html">Read the paper</a>'
                  + ('<a class="rc-dl" href="case-study.pdf" download>Download PDF</a>' if pdf_ok else '') + '</span></div>')
    repo = meta.get("repo_url")
    code_card = (f'<a class="read-card" href="{e(repo)}"><span class="rc-kicker">GitHub</span><h3>Code and pipeline</h3>'
                 f'<p>Python pipeline from raw launch records to the published statistics, with tests.</p><span class="rc-go">View the code</span></a>'
                 if repo else
                 '<div class="read-card muted-card"><span class="rc-kicker">On request</span><h3>Code and pipeline</h3>'
                 '<p>A tested Python pipeline from raw launch records to every published number. Available on request.</p></div>')
    tiles = [
        ((f"{pct(f['case_hi'])} to {pct(f['case_lo'])}", f"two-day abnormal return of the rocket's maker: a loss in each of the {f['n_cases']} listed cases", "loss")
         if all_fell else
         (f"{pct(f['case_lo'])} to {pct(f['case_hi'])}", f"range of two-day abnormal returns of the rocket's maker across the {f['n_cases']} listed cases", "neutral")),
        (pct(p["mean_car"], 2), f"average two-day reaction of listed competitors; 95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}; not statistically detectable" if p["p"] >= 0.05 else f"average two-day reaction of listed competitors; 95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}", "neutral" if p["p"] >= 0.05 else ("gain" if p["mean_car"] > 0 else "loss")),
    ]
    if pl.get("actual_percentile") is not None:
        tiles.append((ordinal(pl["actual_percentile"]), f"percentile of the real competitor result among {pl['draws']} random sets of ordinary trading days", "neutral"))
    tiles_html = "".join(f'<div class="tile {c}"><div class="tile-num">{e(n)}</div><p>{e(t)}</p></div>' for n, t, c in tiles)
    we1 = f.get("w_e1")
    e1_txt = (f" An exploratory check added after the results leaves out the {len(e1.get('dropped') or [])} days when competitors announced large contracts: "
              f"the average moves to {pct(e1['mean_car'], 2)} (95% interval {pct(e1['ci_low'], 2)} to {pct(e1['ci_high'], 2)})"
              + (f", while the median moves only from {pct(w['median'], 2)} to {pct(we1['median'], 2)}, so the average is sensitive to a few large moves" if w and we1 else "")
              + ". It is exploratory and does not replace the main result." if e1 else "")
    cite_url = meta.get("live_url") or ""
    import casestudy as _cs
    _nodes, _edges = _cs.sample_graph(m.get("sample") or {}, f, p)
    sample_svg = ('<figure class="cs-fig">' + _cs.fig_sample(_nodes, _edges) + '<figcaption class="cs-cap">Each box gives a count and its unit. Source: GCAT and the project pipeline.</figcaption></figure>') if _nodes else ""
    blob = (repo.rstrip("/") + "/blob/master/") if repo else None
    ev = [("Feasibility report (before results)", "reports/04_feasibility_report.md"), ("Results report", "reports/05_results.md"),
          ("Confounding-news checks", "docs/CONFOUNDING_NEWS.md"), ("Exploratory confounding sensitivity", "reports/06_confounding_sensitivity.md"),
          ("Independent audit and verification", "audit/AUDIT_REPORT.md"), ("Reproduction guide", "README.md")]
    evidence = ('<p class="evidence"><strong>Evidence:</strong> ' + " · ".join(f'<a href="{e(blob + path)}">{e(lab)}</a>' for lab, path in ev) + "</p>") if blob else ""
    body = f"""<a class="skip-link" href="#main">Skip to the article</a>
<header class="masthead"><div class="wrap">
  <div class="kicker"><span>T-Minus Markets</span><span>Research article · Event study</span></div>
  <h1>When a rocket blows up, who loses money, and does anyone win?</h1>
  <p class="dek">How stock markets react to orbital launch failures, {e(span)}.</p>
  <p class="byline">{e(meta.get('author', 'Nahian Ibnat'))} · Independent research · Updated {e(updated)}</p>
</div></header>
<main id="main" class="wrap article">
  <section class="tiles" aria-label="Key findings">{tiles_html}</section>

  <section class="abstract"><h2>In short</h2><p>{e(abstract)}</p>
    <p class="cta"><a class="btn" href="site/index.html">Open the interactive report</a> <a class="btn ghost" href="case-study.html">Read the working paper</a>{' <a class="dl-link" href="case-study.pdf" download>Download PDF</a>' if pdf_ok else ''}</p></section>

  <section id="a1"><h2>1. The research question</h2>
  <p>Orbital launch is a small industry with a handful of listed firms, and every launch is a public, all-or-nothing test. A failure destroys hardware and often a customer's satellite, so the rocket's maker should lose value. The open question is the competitors. If investors read a failure as a reminder that spaceflight is risky for everyone, rival launch stocks fall too: <strong>contagion</strong>. If they expect customers to move to a rocket that works, rivals rise: <strong>competitive gain</strong>. The two stories point in opposite directions, and both could operate at once.</p>
  <p>The same question appears wherever one firm's bad news may spread to similar firms: bank failures, product recalls, sovereign debt crises. Launch failures are useful because they are sudden, public and easy to date.</p></section>

  <section id="a2"><h2>2. What the data include</h2>
  <p>The numbers below count different things, so they cannot be read as one shrinking funnel:</p>
  {sample_svg}
  <ul class="method">
    <li><strong>Launch failures ({f['n_failures']}):</strong> every orbital launch from {e(span)} that GCAT scores below 0.75.</li>
    <li><strong>Listed-maker cases ({f['n_cases']}):</strong> failures whose rocket was built by a company listed on a stock exchange at the time.</li>
    <li><strong>Rival-eligible failures ({f['n_rival_failures']}):</strong> failures with at least one listed direct competitor (similar rocket size, same customers, launch a major business).</li>
    <li><strong>Rival reactions ({p['n_firm_events']}):</strong> one per listed rival per failure; one failure can produce several.</li>
    <li><strong>Independent events ({f['n_clusters']}):</strong> failures that share a firm within a few trading days are grouped, because their reactions are not independent.</li>
    <li><strong>Distinct rival firms ({n_firms}):</strong> {e(", ".join(f["rival_names"]))}.</li>
  </ul>
  <p><strong>Method in brief.</strong> For each stock, a market model fitted on about a year of earlier data predicts the return given its home market index; the <em>abnormal return</em> is the actual return minus that prediction, summed over the two trading days after the failure became public. Only derived statistics are published, never stock prices. The rules were committed to the public repository before results (commit record in the working paper, Appendix G); they were not filed with an independent registry.</p></section>

  <section id="a3"><h2>3. What happened to the rocket's maker?</h2>
  <p>{"In every listed case the maker's shares fell over the two days after the failure became public, after allowing for the market." if all_fell else "For the rocket's maker, the cases do not all point the same way."} Two-day abnormal returns ranged from {e(pct(f['case_hi']))} to {e(pct(f['case_lo']))}. With {f['n_cases']} cases from {len(f['case_firms'])} firms, these are case studies, not a general launch-provider effect, and abnormal returns are not exact monetary losses caused by the failure.</p></section>

  <section id="a4"><h2>4. What happened to its competitors?</h2>
  <p>The average two-day reaction was {e(pct(p['mean_car'], 2))} (95% interval {e(pct(p['ci_low'], 2))} to {e(pct(p['ci_high'], 2))}{f", p = {e(pval(f['pA']))}" if f.get('pA') is not None else ""}), which {e(detect)}. The prespecified standardized test, which gives less weight to volatile stocks and so asks a slightly different question, also finds nothing detectable (p = {e(pval(p['p']))}). Each p-value is reported next to the quantity it tests.</p></section>

  <section id="a5"><h2>5. How reliable is the result?</h2>
  {f'<p>The sample is small and concentrated: {n_firms} firms, and ' + e(f["top_firm"]) + ' is in every one of the ' + str(f["n_clusters"]) + ' independent events, so the events are not independent draws from the whole industry.</p>' if w else ''}
  {f'<p>With this sample, an average effect smaller than about {e(pct(pw["mde80"], 1, False))} in either direction would usually go undetected (80% power at the 5% level); the chance of detecting a true 1% effect is about {pw["power"][0.01] * 100:.0f}%. So "not detectable" here does not mean "no effect": the interval contains economically meaningful losses and gains.</p>' if pw and p["p"] >= 0.05 else ''}
  <p>The result is consistent with several explanations: contagion and competitive gain cancelling out, customers being unable to switch rockets quickly, or investors treating a failure mainly as news about the failed firm. The data cannot tell these apart.</p></section>

  <section id="a6"><h2>6. What changes under robustness checks?</h2>
  <p><strong>Prespecified checks.</strong> {"None of the" if f["n_robust_sig"] == 0 else str(f["n_robust_sig"]) + " of the"} {f['n_robust']} checks fixed in advance {"detects" if f["n_robust_sig"] == 0 else "detect"} a significant average at the 5% level{f", but the estimates range from {e(pct(f['rob_min'], 2))} to {e(pct(f['rob_max'], 2))}: the lack of a detectable effect is stable, its direction and size are not" if f['rob_min'] is not None and f['rob_min'] < 0 < f['rob_max'] else ""}.{f" The real result sits at the {ordinal(pl['actual_percentile'])} percentile of averages on random ordinary days." if pl.get('actual_percentile') is not None else ""}</p>
  {f'<p><strong>Weighting (sensitivity, added after the results).</strong> {e(pct(w["observation_weighted"], 2))} with every reaction equal (the prespecified estimate), {e(pct(w["event_weighted"], 2))} with every event equal, {e(pct(w["precision_weighted"], 2))} weighting calm stocks more, {e(pct(w["firm_balanced"], 2))} with every firm equal. No weighting is statistically preferred.</p>' if w else ''}
  <p><strong>Exploratory.</strong>{e(e1_txt) if e1_txt else " No exploratory checks have been run."}</p></section>

  <section id="a7"><h2>7. What does the evidence establish?</h2>
  <ul class="method">
    <li><strong>Shown:</strong> {"large two-day abnormal losses for the listed maker in each observed case" if all_fell else "the maker's reaction in each listed case"}; no detectable average reaction among the {n_firms} listed competitors studied.</li>
    <li><strong>Not shown:</strong> that competitors systematically lose (contagion) or gain (competition); that the effect is negligible; that customers switch providers; that industry-wide reactions are absent; that the pattern holds for private, state-owned or diversified aerospace firms.</li>
  </ul></section>

  <section id="a8" aria-label="Read the research"><h2>8. Read the research</h2>
  <div class="read-grid">
    {paper_card}
    <a class="read-card" href="site/index.html"><span class="rc-kicker">Interactive</span><h3>The report</h3>
      <p>Five countdown stages from the question to the checks, with four tools: Failure Timeline, Expected vs Actual, Event Study Lab and Placebo Simulator.</p><span class="rc-go">Open the report</span></a>
    {code_card}
  </div>
  <p class="evidence"><strong>Also:</strong> {" · ".join(x for x in [
      '<a href="site/index.html#methods">Data and methods</a>',
      (f'<a href="{e(repo.rstrip("/") + "#reproduction-and-verification")}">Replication instructions</a>' if repo else "")] if x)}</p>
  {evidence}</section>

  <section class="cite"><h2>Cite</h2>
  <p class="mono">Ibnat, N. ({e(str(datetime.fromisoformat(str(m.get('results_run_utc', '2026'))[:10]).year if m.get('results_run_utc') else ''))}). When a rocket blows up, who loses money, and does anyone win? An event study of orbital launch failures. T-Minus Markets.{(' ' + e(cite_url)) if cite_url else ''}</p></section>
</main>
<footer class="site-foot"><div class="wrap cols">
  <div><h3>Author</h3><p>{e(meta.get('author', 'Nahian Ibnat'))}</p></div>
  <div><h3>Sources</h3><p>Launch data: GCAT, J. McDowell, CC-BY. Prices: Yahoo Finance, used only to compute statistics.</p></div>
  <div><h3>Note</h3><p>Research, not investment advice.</p></div>
</div></footer>"""
    desc = (f"Event study of {f['n_failures']} orbital launch failures: the rocket's maker loses {pct(f['case_hi'])} to {pct(f['case_lo'])} in two days; "
            f"listed competitors show no detectable reaction ({pct(p['mean_car'], 2)}, 95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}).")
    image = (meta["live_url"].rstrip("/") + "/og.png") if meta.get("live_url") else None
    return _shell("T-Minus Markets: when a rocket blows up, who loses money?", desc, meta.get("live_url"), body, css, meta.get("live_url"), image, body_class="theme-sky")
