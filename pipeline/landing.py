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
from sitechrome import FONTS  # noqa: E402  (shared with the report and the paper)

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
    """Homepage (site root). Order: header, title, findings, interpretation, contagion vs competition, sample,
    tool previews, limitations, resources, footer. Every number is read from the exported results."""
    import sitechrome as SC
    f = facts(data)
    p, pl, e1 = f["prim"], f["placebo"], f["e1"]
    m = data["manifest"]
    updated = month(m.get("results_run_utc") or datetime.now(timezone.utc).isoformat())
    span = f"{f['first_year']} to {f['last_year']}" if f["first_year"] else ""
    detectable = p["p"] < 0.05
    all_fell = f["case_hi"] is not None and f["case_hi"] < 0
    pw, w, we1 = f["pw"], f["w"], f.get("w_e1")
    mde = pw["mde80"] if pw else None
    n_firms = f["n_rival_firms"]
    pdf_ok = (root / "paper.pdf").exists()
    repo = meta.get("repo_url")
    cite_url = meta.get("live_url") or ""
    year = str(datetime.fromisoformat(str(m.get("results_run_utc", "2026"))[:10]).year) if m.get("results_run_utc") else ""
    fes_all = data.get("firmEvents") or []
    makers = sorted([r for r in fes_all if r["group"] == "provider_failure" and r["windows"]["primary"]["car"] is not None], key=lambda r: r["day0"])
    rivals = [r for r in fes_all if r["group"] == "rival" and r["windows"]["primary"]["car"] is not None]
    blob = (repo.rstrip("/") + "/blob/master/") if repo else None
    ev = [("Feasibility report (written before results)", "reports/04_feasibility_report.md"), ("Results report", "reports/05_results.md"),
          ("Confounding-news checks", "docs/CONFOUNDING_NEWS.md"), ("Exploratory confounding sensitivity", "reports/06_confounding_sensitivity.md"),
          ("Independent audit and verification", "audit/AUDIT_REPORT.md"), ("Reproduction guide", "README.md")]
    evidence = "".join(f'<li><a href="{e(blob + path)}">{e(lab)}</a></li>' for lab, path in ev) if blob else ""

    # ---------------------------------------------------------------- charts (inline SVG, data-driven)
    def maker_chart():
        if not makers:
            return ""
        W, H, l, r_, t_, b_ = 560, 240, 46, 118, 14, 30
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
        lo = min(-0.05, min(v for _, pts in paths for _, v in pts))
        lo = -0.05 * (int(-lo / 0.05) + 1)
        hi = 0.05
        X = lambda t: l + (t - T0) / (T1 - T0) * (W - l - r_)
        Y = lambda v: t_ + (hi - v) / (hi - lo) * (H - t_ - b_)
        g = [f'<rect x="{X(0):.1f}" y="{t_}" width="{X(1) - X(0):.1f}" height="{H - t_ - b_}" class="win"/>']
        v = hi
        while v >= lo - 1e-9:
            g.append(f'<line x1="{l}" x2="{W - r_}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="{"zero" if abs(v) < 1e-9 else "grid"}"/>'
                     f'<text x="{l - 6}" y="{Y(v) + 4:.1f}" text-anchor="end" class="ax">{pct(v, 0)}</text>')
            v -= 0.05
        for t in (0, 1, 5, 10):
            g.append(f'<text x="{X(t):.1f}" y="{H - 10}" text-anchor="middle" class="ax">{"Day 0" if t == 0 else "+" + str(t)}</text>')
        for r, pts in paths:
            d = " ".join(f'{"M" if i == 0 else "L"}{X(t):.1f},{Y(v):.1f}' for i, (t, v) in enumerate(pts))
            lt, lv = pts[-1]
            g.append(f'<path d="{d}" class="loss-line"/><circle cx="{X(lt):.1f}" cy="{Y(lv):.1f}" r="3" class="loss-dot"/>'
                     f'<text x="{X(lt) + 8:.1f}" y="{Y(lv) + 4:.1f}" class="lab">{e(r["vehicle"])} {e(r["day0"][:4])}</text>')
        desc = "; ".join(f'{r["vehicle"]} {r["day0"][:4]}: {pct(r["windows"]["primary"]["car"])} over days 0 to +1' for r, _ in paths)
        return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Cumulative abnormal return of the rocket maker after each failure. {e(desc)}">'
                + "".join(g) + "</svg>")

    def rival_chart():
        W, H, l, r_ = 560, 118, 24, 24
        lo_, hi_ = -0.05, 0.05
        X = lambda v: l + (v - lo_) / (hi_ - lo_) * (W - l - r_)
        s = []
        if mde and not detectable:
            s.append(f'<rect x="{X(-mde):.1f}" y="18" width="{X(mde) - X(-mde):.1f}" height="54" class="mde"/>')
        s.append(f'<line x1="{X(0):.1f}" x2="{X(0):.1f}" y1="10" y2="{H - 28}" class="zero"/>')
        for v in (-0.04, -0.02, 0, 0.02, 0.04):
            s.append(f'<text x="{X(v):.1f}" y="{H - 8}" text-anchor="middle" class="ax">{pct(v, 0) if v else "0%"}</text>')
        y = 45
        s.append(f'<line x1="{X(p["ci_low"]):.1f}" x2="{X(p["ci_high"]):.1f}" y1="{y}" y2="{y}" class="ci"/>'
                 f'<line x1="{X(p["ci_low"]):.1f}" x2="{X(p["ci_low"]):.1f}" y1="{y - 8}" y2="{y + 8}" class="ci"/>'
                 f'<line x1="{X(p["ci_high"]):.1f}" x2="{X(p["ci_high"]):.1f}" y1="{y - 8}" y2="{y + 8}" class="ci"/>'
                 f'<circle cx="{X(p["mean_car"]):.1f}" cy="{y}" r="6.5" class="pt"/>')
        return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Average two-day reaction of listed competitors '
                f'{e(pct(p["mean_car"], 2))}, 95% interval {e(pct(p["ci_low"], 2))} to {e(pct(p["ci_high"], 2))}, which includes zero.">'
                + "".join(s) + "</svg>")

    def mini_years():
        ys = {}
        for x in data.get("failures") or []:
            y_ = str(x.get("launch_utc", ""))[:4]
            if y_.isdigit():
                ys[int(y_)] = ys.get(int(y_), 0) + 1
        if not ys:
            return ""
        a, b = min(ys), max(ys)
        mx = max(ys.values())
        bw = 240 / (b - a + 1)
        bars = "".join(f'<rect x="{(y_ - a) * bw + 1:.1f}" y="{70 - ys.get(y_, 0) / mx * 64:.1f}" width="{bw - 2:.1f}" height="{ys.get(y_, 0) / mx * 64:.1f}" class="bar"/>'
                       for y_ in range(a, b + 1))
        return f'<svg viewBox="0 0 240 72" class="mini" aria-hidden="true">{bars}</svg>'

    def mini_dots():
        if not rivals:
            return ""
        X = lambda v: 120 + max(-0.1, min(0.1, v)) / 0.1 * 112
        dots = "".join(f'<circle cx="{X(r["windows"]["primary"]["car"]):.1f}" cy="{20 + (i * 37) % 40}" r="3.4" class="{"neg" if r["windows"]["primary"]["car"] < 0 else "pos"}"/>'
                       for i, r in enumerate(rivals))
        return f'<svg viewBox="0 0 240 72" class="mini" aria-hidden="true"><line x1="120" x2="120" y1="4" y2="68" class="zero"/>{dots}</svg>'

    def mini_placebo():
        dist = pl.get("distribution") or []
        if not dist:
            return ""
        lo_, hi_ = min(dist), max(dist)
        nb = 24
        cnt = [0] * nb
        for v in dist:
            cnt[min(nb - 1, int((v - lo_) / (hi_ - lo_ + 1e-12) * nb))] += 1
        mx = max(cnt)
        bw = 240 / nb
        bars = "".join(f'<rect x="{i * bw + 1:.1f}" y="{70 - c / mx * 60:.1f}" width="{bw - 2:.1f}" height="{c / mx * 60:.1f}" class="bar soft"/>' for i, c in enumerate(cnt))
        xa = (pl["actual_mean_car"] - lo_) / (hi_ - lo_ + 1e-12) * 240
        return f'<svg viewBox="0 0 240 72" class="mini" aria-hidden="true">{bars}<line x1="{xa:.1f}" x2="{xa:.1f}" y1="2" y2="70" class="mark"/></svg>'

    def mini_explainer():
        return ('<svg viewBox="0 0 240 72" class="mini" aria-hidden="true"><polyline points="0,40 40,36 80,42 120,34 160,38 200,35 240,37" class="exp"/>'
                '<polyline points="0,40 40,37 80,41 120,33 140,58 160,62 200,60 240,61" class="act"/></svg>')

    # ---------------------------------------------------------------- text pieces
    maker_big = f"{pct(f['case_hi'])} to {pct(f['case_lo'])}" if all_fell else f"{pct(f['case_lo'])} to {pct(f['case_hi'])}"
    pA = f.get("pA")

    import diagnostics as D
    tm = D.timing(fes_all) if fes_all else None
    prov = tm["rival_reactions"]["shares"].get("provisional", 0.0) if tm else None
    body = f"""<a class="skip-link" href="#main">Skip to content</a>
{SC.header("home", "", pdf_ok, repo)}
<main id="main">
<section class="hero" aria-labelledby="title"><div class="wrap hero-in">
  <p class="eyebrow">Space Shock · Research overview</p>
  <h1 id="title">When Rockets Fail, Who Pays the Price?</h1>
  <p class="dek">An empirical investigation of financial contagion and competitive effects following rocket launch failures.</p>
  <p class="q">When an orbital rocket fails, what happens to the stock of the company that built it, and to the stocks of its listed competitors? Investors could treat the failure as bad news for the whole industry (<strong class="c-loss">contagion</strong>) or as a chance for rivals to win customers (<strong class="c-gain">competitive gain</strong>). This study measures which, using {f['n_failures']} orbital launch failures from {e(span)}.</p>
  <p class="cta"><a class="btn" href="site/index.html">Explore the Evidence</a><a class="btn ghost" href="paper.html">Read the Paper</a></p>
  <p class="meta-line">{e(meta.get('author', 'Nahian Ibnat'))} · Paper, not peer reviewed · Results {e(updated)}</p>
</div></section>

<section class="findings" aria-labelledby="h-find"><div class="wrap">
  <h2 id="h-find" class="sec-h">Key findings</h2>
  <div class="kf-grid">
    <div class="kf is-loss"><p class="kf-k">Rocket makers</p><p class="kf-v loss-v">{e(maker_big)}</p><p class="kf-l">Two-day abnormal return in each of the {f['n_cases']} listed-maker cases ({len(f['case_firms'])} firms). Case studies, not an average.</p></div>
    <div class="kf"><p class="kf-k">Listed competitors</p><p class="kf-v">{e(pct(p['mean_car'], 2))}</p><p class="kf-l">Average two-day abnormal return. 95% interval {e(pct(p['ci_low'], 2))} to {e(pct(p['ci_high'], 2))}.</p></div>
    <div class="kf"><p class="kf-k">Statistical test</p><p class="kf-v">p = {e(pval(p['p']))}</p><p class="kf-l">Prespecified standardized test. {"No conclusive evidence of either contagion or competitive gains." if not detectable else "Detectable at the 5% level."}</p></div>
    <div class="kf"><p class="kf-k">Sample</p><p class="kf-v">{f['n_clusters']} <span class="kf-u">independent events</span></p><p class="kf-l">{p['n_firm_events']} reactions of {n_firms} listed competitor firms to {f['n_rival_failures']} failures.</p></div>
  </div>
  <div class="fig-row">
    <figure class="fig-card">{maker_chart()}<figcaption><strong>Rocket makers.</strong> Cumulative abnormal return from the close before the failure (0%) to day +10, one line per case. Shaded: the two-day window.</figcaption></figure>
    <figure class="fig-card">{rival_chart()}<figcaption><strong>Listed competitors.</strong> Dot: average; bar: 95% interval (cluster-robust).{f" Shaded: average effects up to about {pct(mde, 1, False)} either way that this sample could not reliably detect." if mde and not detectable else ""}{f" A second test of the plain average gives p = {pval(pA)}; it measures a different quantity, so the two p-values are not interchangeable." if pA is not None else ""}</figcaption></figure>
  </div>
</div></section>

<section class="tools band dark" aria-labelledby="h-tools"><div class="wrap">
  <h2 id="h-tools" class="sec-h">Explore the evidence</h2>
  <div class="tool-grid">
    <a class="tool-card" href="site/index.html#timeline">{mini_years()}<h3>Failure Timeline</h3><p>Every failure since {f['first_year']}, and which ones enter the study.</p></a>
    <a class="tool-card" href="site/index.html#explainer">{mini_explainer()}<h3>Expected vs Actual</h3><p>How an abnormal return is measured, on a simulated stock.</p></a>
    <a class="tool-card" href="site/index.html#lab">{mini_dots()}<h3>Event Study Lab</h3><p>Re-run the competitor test on a sample you choose.</p></a>
    <a class="tool-card" href="site/index.html#placebo-sim">{mini_placebo()}<h3>Placebo Simulator</h3><p>Compare the real result with random ordinary days.</p></a>
  </div>
</div></section>

<section class="limits" aria-labelledby="h-lim"><div class="wrap narrow">
  <h2 id="h-lim" class="sec-h">What the evidence can and cannot show</h2>
  <ul class="cc">
    <li><strong>Makers lose.</strong> {"In every listed case the maker's shares fell well beyond the market over two days." if all_fell else "Maker reactions differ across the listed cases."} With {f['n_cases']} cases this describes those cases, not every launch company.</li>
    <li><strong>Competitors: imprecise, not zero.</strong> The evidence does not establish a statistically reliable competitive or contagion effect; it does not show that there is no effect either. The interval runs from {e(pct(p['ci_low'], 2))} to {e(pct(p['ci_high'], 2))}.</li>
    {f'<li><strong>Low power.</strong> Average effects below about {e(pct(mde, 1, False))} either way would usually be missed.</li>' if mde else ''}
    <li><strong>Small, concentrated sample.</strong> {n_firms} listed competitors{f"; {e(f['top_firm'])} is in all {f['n_clusters']} independent events" if f.get('top_firm') and f.get('top_firm_clusters') == f['n_clusters'] else ""}.</li>
    {f'<li><strong>Weighting matters.</strong> Weighting every reaction equally gives {e(pct(w["observation_weighted"], 2))}; weighting every firm equally gives {e(pct(w["firm_balanced"], 2))} (a sensitivity analysis, not the prespecified estimate).</li>' if w else ''}
    {f'<li><strong>Event timing.</strong> {prov * 100:.0f}% of competitor reactions are dated from GCAT launch times not separately checked against a company statement, used only where the trading day would not change under a small timing error.</li>' if prov is not None else ''}
  </ul>
  <p class="more-links">Details: <a href="methods.html#quality">data quality and limitations</a> · <a href="paper.html#s7">robustness in the paper</a></p>
</div></section>

<section class="resources band" aria-labelledby="h-res"><div class="wrap">
  <h2 id="h-res" class="sec-h">Research and reproducibility</h2>
  <div class="res-grid">
    <div class="r-card"><h3>Read</h3><ul class="rlist">
      <li><a href="paper.html">Paper (web)</a><span>{e(SC.PAPER_TITLE)}</span></li>
      {'<li><a href="paper.pdf" download>Download PDF</a><span>Same paper, typeset</span></li>' if pdf_ok else ''}</ul></div>
    <div class="r-card"><h3>Understand</h3><ul class="rlist">
      <li><a href="methods.html">Data &amp; Methods</a><span>Sources, definitions, tests, data quality</span></li>
      <li><a href="site/index.html">Explore Data</a><span>Interactive report and four tools</span></li></ul></div>
    <div class="r-card"><h3>Reproduce</h3><ul class="rlist">
      {f'<li><a href="{e(repo)}">Source code</a><span>Python pipeline and tests</span></li>' if repo else ''}
      <li><a href="methods.html#replicate">Replication instructions</a><span>Steps, commands and checks</span></li>
      {f'<li><a href="{e(blob + "audit/VERIFICATION.md")}">Verification report</a><span>Every published statistic recomputed</span></li>' if blob else ''}</ul></div>
  </div>
  {f'<details class="more"><summary>Supporting evidence documents</summary><ul class="ev">{evidence}</ul></details>' if evidence else ''}
</div></section>
</main>
{SC.footer("", meta, pdf_ok, SC.cite(year, meta))}"""
    desc = (f"Event study of {f['n_failures']} orbital launch failures: the rocket's maker loses {pct(f['case_hi'])} to {pct(f['case_lo'])} in two days; "
            f"listed competitors show no detectable reaction ({pct(p['mean_car'], 2)}, 95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}).")
    image = (meta["live_url"].rstrip("/") + "/og.png") if meta.get("live_url") else None
    return _shell("Space Shock: When Rockets Fail, Who Pays the Price?", desc, meta.get("live_url"), body, css, meta.get("live_url"), image, body_class="home")
