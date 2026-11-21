"""Root article page (index.html) and the rendered analysis plan (plan.html), for GitHub Pages.

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
    }


def _shell(title, desc, url, body, css, canonical=None):
    og_url = e(url) if url else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}"><meta name="author" content="Nahian Ibnat">
<meta property="og:type" content="article"><meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">{f'<meta property="og:url" content="{og_url}">' if og_url else ""}
<meta name="twitter:card" content="summary">{f'<link rel="canonical" href="{e(canonical)}">' if canonical else ""}
{FONTS}
<style>
{css}
</style>
</head>
<body>
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
    reading = ("The evidence fits a simple reading: investors treat a failure as bad news for the firm that flew the rocket, "
               "not as news about the industry. " if all_fell and p["p"] >= 0.05 else "")
    abstract = (
        f"When an orbital rocket fails, does the stock market punish only the company that built it, or the whole launch industry? "
        f"Using {f['n_failures']} orbital launch failures from {span}, this study measures abnormal stock returns over the two trading days "
        f"after each failure became public. In the {f['n_cases']} cases where the rocket's maker was listed, {maker} "
        f"after allowing for the market. Listed competitors moved by {pct(p['mean_car'], 2)} on average "
        f"(95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}; p = {pval(p['p'])}), which {detect} with "
        f"{f['n_clusters']} independent events. {reading}Every analysis choice was fixed in a written plan before any stock reaction was measured.")
    paper = root / meta.get("paper_pdf", "paper/none.pdf")
    paper_card = (f'<a class="read-card" href="{e(meta["paper_pdf"])}"><span class="rc-kicker">PDF</span><h3>Working paper</h3>'
                  f'<p>The full write-up: data, method, results, robustness and limits.</p><span class="rc-go">Read the paper</span></a>'
                  if paper.exists() else
                  '<div class="read-card muted-card"><span class="rc-kicker">In preparation</span><h3>Working paper</h3>'
                  '<p>The full write-up is being drafted. The interactive report already contains every result.</p></div>')
    repo = meta.get("repo_url")
    code_card = (f'<a class="read-card" href="{e(repo)}"><span class="rc-kicker">GitHub</span><h3>Code and pipeline</h3>'
                 f'<p>Python pipeline from raw launch records to the published statistics, with tests.</p><span class="rc-go">View the code</span></a>'
                 if repo else
                 '<div class="read-card muted-card"><span class="rc-kicker">On request</span><h3>Code and pipeline</h3>'
                 '<p>A tested Python pipeline from raw launch records to every published number. Available on request.</p></div>')
    changes = len(re.findall(r"^\| \d{4}-\d{2}-\d{2} \|", (root / "docs" / "ANALYSIS_PLAN.md").read_text(encoding="utf-8"), re.M)) \
        if (root / "docs" / "ANALYSIS_PLAN.md").exists() else 0
    tiles = [
        ((f"{pct(f['case_hi'])} to {pct(f['case_lo'])}", f"two-day abnormal return of the rocket's maker: a loss in each of the {f['n_cases']} listed cases", "loss")
         if all_fell else
         (f"{pct(f['case_lo'])} to {pct(f['case_hi'])}", f"range of two-day abnormal returns of the rocket's maker across the {f['n_cases']} listed cases", "neutral")),
        (pct(p["mean_car"], 2), f"average two-day reaction of listed competitors; 95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}, p = {pval(p['p'])}", "gain" if p["mean_car"] > 0 else "loss"),
    ]
    if pl.get("actual_percentile") is not None:
        tiles.append((ordinal(pl["actual_percentile"]), f"percentile of the real competitor result among {pl['draws']} random sets of ordinary trading days", "neutral"))
    tiles_html = "".join(f'<div class="tile {c}"><div class="tile-num">{e(n)}</div><p>{e(t)}</p></div>' for n, t, c in tiles)
    e1_txt = (f" An exploratory check added after the results, which leaves out two days when competitors announced large contracts, gives "
              f"{pct(e1['mean_car'], 2)} (95% interval {pct(e1['ci_low'], 2)} to {pct(e1['ci_high'], 2)}); it is labelled as such everywhere."
              if e1 else "")
    cite_url = meta.get("live_url") or ""
    body = f"""<a class="skip-link" href="#main">Skip to the article</a>
<header class="masthead"><div class="wrap">
  <div class="kicker"><span>T-Minus Markets</span><span>Research article · Event study</span></div>
  <h1>When a rocket blows up, who loses money, and does anyone win?</h1>
  <p class="dek">How stock markets react to orbital launch failures, {e(span)}.</p>
  <p class="byline">{e(meta.get('author', 'Nahian Ibnat'))} · Independent research · Updated {e(updated)} · Analysis plan v{e(str(m.get('plan_version')))}</p>
</div></header>
<main id="main" class="wrap article">
  <section class="tiles" aria-label="Key findings">{tiles_html}</section>

  <section class="abstract"><h2>In short</h2><p>{e(abstract)}</p>
    <p class="cta"><a class="btn" href="site/">Open the interactive report</a> <a class="btn ghost" href="plan.html">Read the analysis plan</a></p></section>

  <section><h2>Why this question</h2>
  <p>Orbital launch is a small industry with a handful of listed firms, and every launch is a public, all-or-nothing test. A failure destroys hardware and a customer's satellite, so the rocket's maker should lose value. The open question is the competitors. If investors read a failure as a reminder that spaceflight is risky for everyone, rival launch stocks fall too: contagion. If they expect customers to switch to a rocket that works, rivals rise: competitive gain. The two stories point in opposite directions, so only data can say which one investors act on.</p>
  <p>The same question appears wherever one firm's bad news may spread to similar firms: bank failures, product recalls, sovereign debt crises. Launch failures are useful because they are sudden, public and easy to date.</p></section>

  <section><h2>What the data say</h2>
  <p>{"For the rocket's maker, the answer is the same in every case: shares fell over the two days after the failure became public, after allowing for the market." if all_fell else "For the rocket's maker, the cases do not all point the same way."} With {f['n_cases']} cases, these are case studies, not an industry average.</p>
  <p>For competitors, the average reaction {e(detect)}: {e(pct(p['mean_car'], 2))} over two days, from {f['n_rival_failures']} failures, {f['n_rival_firms']} companies and {f['n_clusters']} independent events. "Not detectable" is not the same as "no effect", but the interval tells us average reactions much larger than its ends, in either direction, are unlikely. {f['n_robust_same']} of {f['n_robust']} prespecified robustness checks reach the same conclusion.{e(e1_txt)}</p>
  {"<p>Read economically, a launch failure looks like a firm-specific shock. Investors do not seem to rewrite their view of the industry, and there is no sign that competitors are expected to win business quickly.</p>" if reading else ""}</section>

  <section aria-label="Read the work"><h2>Read the work</h2>
  <div class="read-grid">
    <a class="read-card" href="site/"><span class="rc-kicker">Interactive</span><h3>The report</h3>
      <p>Five countdown stages from the question to the checks, with four tools: Failure Timeline, Expected vs Actual, Event Study Lab and Placebo Simulator.</p><span class="rc-go">Open the report</span></a>
    {paper_card}
    <a class="read-card" href="plan.html"><span class="rc-kicker">Preregistered</span><h3>Analysis plan</h3>
      <p>The rules fixed before any stock reaction was measured, and a dated log of {changes} entries since.</p><span class="rc-go">Read the plan</span></a>
    {code_card}
  </div></section>

  <section><h2>How it was done</h2>
  <ul class="method">
    <li><strong>Sample.</strong> Orbital launch failures since 2000 from GCAT (J. McDowell), linked by hand to listed makers and to listed competitors of a similar size selling to the same customers.</li>
    <li><strong>Measure.</strong> Abnormal return: the stock's actual return minus what a market model, fitted on about a year of earlier data, predicts from its home market index.</li>
    <li><strong>Test.</strong> A standardized event-study test (Boehmer, Musumeci and Poulsen) adjusted for failures that hit several competitors at once (Kolari and Pynnönen), with cluster-robust intervals.</li>
    <li><strong>Checks.</strong> Other test statistics, a wider window, timing and sample changes, leaving out one firm at a time, and a placebo using random ordinary days.</li>
    <li><strong>Rules.</strong> The plan was frozen and committed before results; anything added later is labelled exploratory. Only derived statistics are published, never stock prices.</li>
  </ul></section>

  <section class="cite"><h2>Cite</h2>
  <p class="mono">Ibnat, N. ({e(str(datetime.fromisoformat(str(m.get('results_run_utc', '2026'))[:10]).year if m.get('results_run_utc') else ''))}). When a rocket blows up, who loses money, and does anyone win? An event study of orbital launch failures. T-Minus Markets.{(' ' + e(cite_url)) if cite_url else ''}</p></section>
</main>
<footer class="site-foot"><div class="wrap cols">
  <div><h3>Author</h3><p>{e(meta.get('author', 'Nahian Ibnat'))}. Economics, data and finance.{' <a href="' + e(meta['portfolio_url']) + '">Portfolio</a>' if meta.get('portfolio_url') else ''}{' · <a href="' + e(meta['linkedin_url']) + '">LinkedIn</a>' if meta.get('linkedin_url') else ''}</p></div>
  <div><h3>Sources</h3><p>Launch data: GCAT, J. McDowell, CC-BY. Prices: Yahoo Finance, used only to compute statistics.</p></div>
  <div><h3>Note</h3><p>Research, not investment advice.</p></div>
</div></footer>"""
    desc = (f"Event study of {f['n_failures']} orbital launch failures: the rocket's maker loses {pct(f['case_hi'])} to {pct(f['case_lo'])} in two days; "
            f"listed competitors show no detectable reaction ({pct(p['mean_car'], 2)}, p = {pval(p['p'])}).")
    return _shell("T-Minus Markets: when a rocket blows up, who loses money?", desc, meta.get("live_url"), body, css, meta.get("live_url"))


def md_to_html(md: str) -> str:
    """Tiny Markdown subset for the plan: headings, paragraphs, pipe tables, lists, `code`, **bold**, links."""
    def inline(s):
        s = e(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
        s = re.sub(r'(?<!href=")(https?://[^\s<]+)', r'<a href="\1">\1</a>', s)
        return s
    out, para, lines, i = [], [], md.splitlines(), 0
    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>"); para.clear()
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            flush(); i += 1; continue
        h = re.match(r"^(#{1,4})\s+(.*)", ln)
        if h:
            flush(); lvl = len(h.group(1)) + 1; out.append(f"<h{lvl}>{inline(h.group(2))}</h{lvl}>"); i += 1; continue
        if ln.startswith("|"):
            flush(); rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
            out.append("<div class='table-wrap'><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        if re.match(r"^\s*[-*] ", ln):
            flush(); items = []
            while i < len(lines) and re.match(r"^\s*[-*] ", lines[i]):
                items.append(re.sub(r"^\s*[-*] ", "", lines[i])); i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>"); continue
        para.append(ln.strip()); i += 1
    flush()
    return "\n".join(out)


def plan_page(root: Path, meta: dict, css: str) -> str:
    md = (root / "docs" / "ANALYSIS_PLAN.md").read_text(encoding="utf-8")
    body = f"""<header class="masthead"><div class="wrap">
  <div class="kicker"><span><a href="./">T-Minus Markets</a></span><span>Analysis plan</span></div>
  <p class="byline"><a href="./">Back to the article</a> · <a href="site/">Interactive report</a></p>
</div></header>
<main id="main" class="wrap article plan">
{md_to_html(md)}
<p class="byline">This page is generated from docs/ANALYSIS_PLAN.md in the project repository. The change log records every change after the plan was frozen, with the date and whether results had been seen.</p>
</main>"""
    return _shell("T-Minus Markets: analysis plan and change log",
                  "The analysis plan fixed before any stock reaction was measured, with a dated change log.", None, body, css)
