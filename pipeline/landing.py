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
    fes_all = data.get("firmEvents") or []
    makers = sorted([r for r in fes_all if r["group"] == "provider_failure" and r["windows"]["primary"]["car"] is not None],
                    key=lambda r: r["day0"])
    rivals = [r for r in fes_all if r["group"] == "rival" and r["windows"]["primary"]["car"] is not None]

    # ---------------------------------------------------------------- ticker (real reactions, newest first)
    tick = [(r["day0"], f'{r["vehicle"]} fails', r["ticker"], r["windows"]["primary"]["car"], "maker") for r in makers]
    tick += [(r["day0"], f'{r["vehicle"]} fails', r["ticker"], r["windows"]["primary"]["car"], "rival")
             for r in sorted(rivals, key=lambda r: -abs(r["windows"]["primary"]["car"]))[:10]]
    tick.sort(key=lambda t: t[0], reverse=True)
    def _tk(t):
        cls = "dn" if t[3] < 0 else "up"
        return (f'<span class="tk"><span class="tk-d">{e(t[0])}</span> {e(t[1])} <span class="tk-role">{"maker" if t[4] == "maker" else "rival"}</span> '
                f'{e(t[2])} <span class="{cls}">{e(pct(t[3]))}</span></span>')
    ticker_items = "".join(_tk(t) for t in tick)
    ticker = (f'<div class="ticker" aria-hidden="true"><span class="ticker-label">Two-day abnormal returns</span>'
              f'<div class="ticker-track"><div class="ticker-run">{ticker_items}{ticker_items}</div></div></div>') if tick else ""

    # ---------------------------------------------------------------- maker chart: cumulative abnormal return paths
    def maker_chart():
        if not makers:
            return ""
        W, H, l, r_, t_, b_ = 560, 250, 44, 120, 16, 30
        T0, T1 = -1, 10
        paths = []
        for r in makers:
            ar = {pt["t"]: pt["ar"] for pt in r.get("path", []) if pt.get("ar") is not None}
            cum, pts = 0.0, [(T0, 0.0)]
            for t in range(0, T1 + 1):
                if t not in ar:
                    break
                cum += ar[t]
                pts.append((t, cum))
            paths.append((r, pts))
        lo = min(min(v for _, v in pts) for _, pts in paths)
        lo = min(lo, -0.05)
        lo = -0.05 * (int(-lo / 0.05) + 1)
        hi = 0.05
        X = lambda t: l + (t - T0) / (T1 - T0) * (W - l - r_)
        Y = lambda v: t_ + (hi - v) / (hi - lo) * (H - t_ - b_)
        g = []
        v = hi
        while v >= lo - 1e-9:
            g.append(f'<line x1="{l}" x2="{W - r_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="{"zero" if abs(v) < 1e-9 else "grid"}"/>'
                     f'<text x="{l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" class="ax">{pct(v, 0)}</text>')
            v -= 0.05
        for t in (0, 1, 5, 10):
            g.append(f'<text x="{X(t):.1f}" y="{H - 10}" text-anchor="middle" class="ax">{"Day 0" if t == 0 else "+" + str(t)}</text>')
        g.append(f'<rect x="{X(0):.1f}" y="{t_}" width="{X(1) - X(0):.1f}" height="{H - t_ - b_}" class="win"/>')
        for r, pts in paths:
            d = " ".join(f'{"M" if i == 0 else "L"}{X(t):.1f},{Y(v):.1f}' for i, (t, v) in enumerate(pts))
            lt, lv = pts[-1]
            g.append(f'<path d="{d}" class="mk"/><circle cx="{X(lt):.1f}" cy="{Y(lv):.1f}" r="3" class="mkd"/>'
                     f'<text x="{X(lt) + 8:.1f}" y="{Y(lv) + 4:.1f}" class="lab">{e(r["vehicle"])} {e(r["day0"][:4])}</text>')
        desc = "; ".join(f'{r["vehicle"]} {r["day0"][:4]}: {pct(r["windows"]["primary"]["car"])} over days 0 to 1' for r, _ in paths)
        return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Cumulative abnormal return of the rocket maker after each failure. {e(desc)}">'
                + "".join(g) + "</svg>")

    # ---------------------------------------------------------------- rival interval chart
    def rival_chart():
        W, H, l, r_ = 560, 120, 20, 20
        lo_, hi_ = -0.05, 0.05
        X = lambda v: l + (v - lo_) / (hi_ - lo_) * (W - l - r_)
        s = [f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="14" y2="{H - 30}" class="zero"/>']
        for v in (-0.04, -0.02, 0.02, 0.04):
            s.append(f'<text x="{X(v):.1f}" y="{H - 10}" text-anchor="middle" class="ax">{pct(v, 0)}</text>')
        s.append(f'<text x="{X(0):.1f}" y="{H - 10}" text-anchor="middle" class="ax">0%</text>')
        if mde and p["p"] >= 0.05:
            s.append(f'<rect x="{X(-mde):.1f}" y="22" width="{X(mde) - X(-mde):.1f}" height="44" class="mde"/>'
)
        y = 44
        s.append(f'<line x1="{X(p["ci_low"]):.1f}" x2="{X(p["ci_high"]):.1f}" y1="{y}" y2="{y}" class="ci"/>'
                 f'<line x1="{X(p["ci_low"]):.1f}" x2="{X(p["ci_low"]):.1f}" y1="{y - 7}" y2="{y + 7}" class="ci"/>'
                 f'<line x1="{X(p["ci_high"]):.1f}" x2="{X(p["ci_high"]):.1f}" y1="{y - 7}" y2="{y + 7}" class="ci"/>'
                 f'<circle cx="{X(p["mean_car"]):.1f}" cy="{y}" r="6" class="pt"/>')
        return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Average two-day reaction of listed competitors '
                f'{e(pct(p["mean_car"], 2))}, 95% interval {e(pct(p["ci_low"], 2))} to {e(pct(p["ci_high"], 2))}, which includes zero.">'
                + "".join(s) + "</svg>")

    year = str(datetime.fromisoformat(str(m.get("results_run_utc", "2026"))[:10]).year) if m.get("results_run_utc") else ""
    status = [("Launch failures", f["n_failures"], f"orbital, {span}"), ("Listed-maker cases", f["n_cases"], f"{len(f['case_firms'])} firms"),
              ("Rival reactions", p["n_firm_events"], f"{n_firms} listed rivals"), ("Independent events", f["n_clusters"], "clusters"),
              ("Prespecified checks", f["n_robust"], "none significant" if f["n_robust_sig"] == 0 else f"{f['n_robust_sig']} significant")]
    status_html = "".join(f'<li><span class="st-k">{e(k)}</span><span class="st-v">{e(str(v))}</span><span class="st-n">{e(n)}</span></li>'
                          for k, v, n in status)
    code_link = (f'<a class="card-go" href="{e(repo)}">View the code</a>' if repo else "")
    maker_line = (f"In all {f['n_cases']} listed cases, the maker's shares fell {pct(abs(f['case_hi']), 1, False)} to {pct(abs(f['case_lo']), 1, False)} "
                  f"more than the market in the two trading days after the failure." if all_fell else
                  f"Across the {f['n_cases']} listed cases, the maker's two-day abnormal return ranged from {pct(f['case_lo'])} to {pct(f['case_hi'])}.")
    rival_line = (f"Listed competitors moved {pct(p['mean_car'], 2)} on average (95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}"
                  + (f", p = {pval(f['pA'])}" if f.get("pA") is not None else "") + f"). That {detect}.")
    body = f"""<a class="skip-link" href="#main">Skip to the article</a>
<div class="topbar"><div class="wrap tb">
  <span><span class="dot" aria-hidden="true"></span>T-Minus Markets · research log</span>
  <span>Results {e(updated)} · {f['n_failures']} failures · {p['n_firm_events']} rival reactions</span>
</div></div>
<header class="brand"><div class="wrap brand-row">
  <a class="logo" href="index.html" aria-label="T-Minus Markets, home"><span class="logo-mark" aria-hidden="true">T&#8722;</span>
    <span class="logo-text"><span class="logo-name">T-Minus Markets</span><span class="logo-tag">What a failed launch costs on the stock market</span></span></a>
  <nav class="cd-nav" aria-label="Sections">
    <a href="#question"><b>T&#8722;4</b> Question</a><a href="#findings"><b>T&#8722;3</b> Findings</a><a href="#method"><b>T&#8722;2</b> Method</a>
    <a href="#meaning"><b>T&#8722;1</b> Meaning</a><a href="#explore"><b>T&#8722;0</b> Explore</a>
  </nav>
</div></header>
{ticker}
<main id="main">
<section class="hero"><div class="wrap hero-grid">
  <div>
    <p class="eyebrow">Space · Finance · Event study</p>
    <h1>When a rocket fails, who loses money?</h1>
    <p class="dek">An event study of {f['n_failures']} orbital launch failures, {e(span)}: the stock of the company that built the rocket, and the stocks of its listed competitors.</p>
    <p class="byline">{e(meta.get('author', 'Nahian Ibnat'))} · Independent research · Updated {e(updated)}</p>
    <p class="cta"><a class="btn" href="site/index.html">Open the interactive report</a><a class="btn ghost" href="case-study.html">Read the working paper</a>{'<a class="dl-link" href="case-study.pdf" download>Download PDF</a>' if pdf_ok else ''}</p>
  </div>
  <aside class="status" aria-label="Sample at a glance"><div class="st-head"><span>Mission data</span><span>from the pipeline</span></div>
    <ul>{status_html}</ul><p class="st-note">Every number on this page is read from the published results. Prices are never published.</p></aside>
</div></section>

<section id="question" class="band"><div class="wrap two">
  <div><p class="eyebrow">T&#8722;4 · The question</p><h2>Contagion or a gain for rivals?</h2></div>
  <div class="lede-text">
    <p>A failed launch destroys a rocket and often a customer's satellite, so the builder should lose value. The open question is its <strong>listed competitors</strong>. If investors read a failure as a sign that spaceflight is risky for everyone, rival stocks fall: <strong>contagion</strong>. If they expect customers to move to a rocket that works, rival stocks rise: <strong>competitive gain</strong>.</p>
    <p class="muted">The same question comes up when a bank fails or a product is recalled. Launch failures are useful because they are sudden, public and easy to date.</p>
  </div>
</div></section>

<section id="findings" class="findings"><div class="wrap">
  <p class="eyebrow">T&#8722;3 · What the data show</p><h2>Two findings</h2>
  <div class="find-grid">
    <article class="panel loss-panel"><p class="panel-kicker">01 · The rocket's maker</p>
      <p class="big">{e(f"{pct(f['case_hi'])} to {pct(f['case_lo'])}" if all_fell else f"{pct(f['case_lo'])} to {pct(f['case_hi'])}")}</p>
      <p>{e(maker_line)}</p>
      <figure>{maker_chart()}<figcaption>Cumulative abnormal return from the day before (0%) to day +10. Shaded: the two-day window. {f['n_cases']} cases from {len(f['case_firms'])} firms, so these are case studies.</figcaption></figure>
    </article>
    <article class="panel"><p class="panel-kicker">02 · Its listed competitors</p>
      <p class="big neutral">{e(pct(p['mean_car'], 2))}</p>
      <p>{e(rival_line)} {f['n_clusters']} independent events, {n_firms} firms.</p>
      <figure>{rival_chart()}<figcaption>Dot: average two-day reaction. Bar: 95% interval. {f"Shaded: average effects up to about {pct(mde, 1, False)} either way could not be reliably detected." if mde and p["p"] >= 0.05 else ""}</figcaption></figure>
      <p class="small">The prespecified standardized test gives p = {e(pval(p['p']))}.{f" On random ordinary days the real average sits at the {ordinal(pl['actual_percentile'])} percentile." if pl.get('actual_percentile') is not None else ""}</p>
    </article>
  </div>
</div></section>

<section id="method" class="band"><div class="wrap">
  <p class="eyebrow">T&#8722;2 · How it works</p><h2>Three steps</h2>
  <ol class="steps">
    <li><span class="step-n">1</span><h3>Find every failure</h3><p>{f['n_failures']} orbital launch failures from GCAT, each dated to the first trading day after the news became public.</p></li>
    <li><span class="step-n">2</span><h3>Predict a normal day</h3><p>A market model, fitted on about a year of earlier returns, predicts each stock's return from its home index.</p></li>
    <li><span class="step-n">3</span><h3>Measure the gap</h3><p>The abnormal return is actual minus predicted, added up over the two trading days after the failure.</p></li>
  </ol>
  <details class="more"><summary>The sample in detail</summary>{sample_svg}
    <ul class="method">
      <li><strong>Listed-maker cases ({f['n_cases']}):</strong> failures whose rocket was built by a listed company.</li>
      <li><strong>Rival-eligible failures ({f['n_rival_failures']}):</strong> failures with at least one listed direct competitor.</li>
      <li><strong>Rival reactions ({p['n_firm_events']}):</strong> one per listed rival per failure.</li>
      <li><strong>Independent events ({f['n_clusters']}):</strong> failures that share a firm within a few trading days count as one event.</li>
      <li><strong>Rival firms ({n_firms}):</strong> {e(", ".join(f["rival_names"]))}.</li>
    </ul>
    <p>The rules were committed to the public repository before the results (record in the working paper, Appendix G); they were not filed with an independent registry. Only derived statistics are published.</p></details>
</div></section>

<section id="meaning" class="meaning"><div class="wrap">
  <p class="eyebrow">T&#8722;1 · What it means</p><h2>What the evidence can and cannot say</h2>
  <div class="mean-grid">
    <div class="mean-card ok"><h3>Shown</h3><p>{"Large two-day losses for the maker in every listed case." if all_fell else "The maker's reaction in each listed case."} No detectable average reaction among the {n_firms} listed competitors.</p></div>
    <div class="mean-card no"><h3>Not shown</h3><p>That rivals lose or gain on average; that the effect is zero; that customers switch rockets; that the pattern holds for private or state-owned firms.</p></div>
    <div class="mean-card why"><h3>Why so uncertain</h3><p>{f"Only {n_firms} listed rivals, and {e(f['top_firm'])} is in all {f['n_clusters']} events." if w and f['top_firm'] else f"Only {n_firms} listed rivals."}{f" Effects below about {pct(mde, 1, False)} either way would usually be missed." if mde and p['p'] >= 0.05 else ""}</p></div>
  </div>
  <details class="more"><summary>Reliability and robustness</summary>
    {f'<p>With this sample, an average effect smaller than about {e(pct(pw["mde80"], 1, False))} either way would usually go undetected (80% power at the 5% level); the chance of detecting a true 1% effect is about {pw["power"][0.01] * 100:.0f}%. "Not detectable" here does not mean "no effect".</p>' if pw and p["p"] >= 0.05 else ''}
    <p><strong>Prespecified checks.</strong> {"None of the" if f["n_robust_sig"] == 0 else str(f["n_robust_sig"]) + " of the"} {f['n_robust']} checks fixed in advance {"detects" if f["n_robust_sig"] == 0 else "detect"} a significant average at the 5% level{f"; the estimates range from {e(pct(f['rob_min'], 2))} to {e(pct(f['rob_max'], 2))}, so the lack of an effect is stable but its direction and size are not" if f['rob_min'] is not None and f['rob_min'] < 0 < f['rob_max'] else ""}.</p>
    {f'<p><strong>Weighting (added after the results).</strong> {e(pct(w["observation_weighted"], 2))} with every reaction equal (prespecified), {e(pct(w["event_weighted"], 2))} with every event equal, {e(pct(w["precision_weighted"], 2))} weighting calm stocks more, {e(pct(w["firm_balanced"], 2))} with every firm equal.</p>' if w else ''}
    <p><strong>Exploratory.</strong>{e(e1_txt) if e1_txt else " No exploratory checks have been run."}</p>
    <p>Possible explanations the data cannot separate: contagion and competitive gain cancelling out, customers unable to switch quickly, or investors treating a failure as news about the failed firm only.</p></details>
</div></section>

<section id="explore" class="band"><div class="wrap">
  <p class="eyebrow">T&#8722;0 · Explore</p><h2>Go deeper</h2>
  <div class="explore-grid">
    <a class="card feature" href="site/index.html"><span class="card-k">Interactive report</span><h3>Run the study yourself</h3>
      <p>Failure Timeline, Expected vs Actual, Event Study Lab and Placebo Simulator, in five countdown stages.</p><span class="card-go">Open the report</span></a>
    <div class="card"><span class="card-k">Working paper</span><h3>The full study</h3>
      <p><em>Rocket Launch Failures and Equity-Market Spillovers.</em> Methods, results, robustness and appendices.{' The same paper as a web page and as a PDF.' if pdf_ok else ''}</p>
      <span class="card-actions"><a class="card-go" href="case-study.html">Read the paper</a>{'<a class="dl-link" href="case-study.pdf" download>Download PDF</a>' if pdf_ok else ''}</span></div>
    <div class="card"><span class="card-k">Code</span><h3>Pipeline and tests</h3>
      <p>Python pipeline from raw launch records to every published number, with an independent verification.</p>{code_link}</div>
  </div>
  {evidence}
</div></section>
</main>
<footer class="site-foot"><div class="wrap foot-grid">
  <div><h3>Author</h3><p>{e(meta.get('author', 'Nahian Ibnat'))}</p></div>
  <div><h3>Sources</h3><p>Launch data: GCAT, J. McDowell, CC-BY. Prices: Yahoo Finance, used only to compute statistics.</p></div>
  <div><h3>Cite</h3><p class="mono">Ibnat, N. ({e(year)}). When a rocket blows up, who loses money, and does anyone win? An event study of orbital launch failures. T-Minus Markets.{(' ' + e(cite_url)) if cite_url else ''}</p></div>
  <div><h3>Note</h3><p>Research, not investment advice.</p></div>
</div></footer>"""
    desc = (f"Event study of {f['n_failures']} orbital launch failures: the rocket's maker loses {pct(f['case_hi'])} to {pct(f['case_lo'])} in two days; "
            f"listed competitors show no detectable reaction ({pct(p['mean_car'], 2)}, 95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}).")
    image = (meta["live_url"].rstrip("/") + "/og.png") if meta.get("live_url") else None
    return _shell("T-Minus Markets: when a rocket blows up, who loses money?", desc, meta.get("live_url"), body, css, meta.get("live_url"), image, body_class="theme-sky")
