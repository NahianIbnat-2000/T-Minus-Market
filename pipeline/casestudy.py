"""Long-form case study (case-study.html): the full write-up of the project, built from site/data/*.json.

Static HTML with inline SVG figures (no JavaScript), styled for screen and for A4 printing, so the same
file becomes the companion PDF (step 08 prints it with a headless browser when one is available).
Every number comes from the exported data. Sentences that interpret a result are conditional on it.
"""
from __future__ import annotations

import html
from collections import Counter
from datetime import datetime
from pathlib import Path

from landing import MONTHS, day, facts, month, ordinal, pct, pval

e = html.escape
INK, MUTED, RULE, SIGNAL, GAIN, DEEP = "#1C1C1C", "#5E574C", "#C9C1B3", "#D9452B", "#1F4E8C", "#EBE4D6"


# ----------------------------------------------------------------------------- small SVG helpers
def _svg(w, h, label, inner):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{e(label)}" '
            f'font-family="DM Mono, ui-monospace, monospace" font-size="11" fill="{INK}">{inner}</svg>')


def _lin(d0, d1, r0, r1):
    return lambda v: r0 + (v - d0) * (r1 - r0) / (d1 - d0 or 1)


def _ticks(lo, hi, n=5):
    import math
    span = hi - lo or 1
    step = 10 ** math.floor(math.log10(span / n))
    for m in (1, 2, 2.5, 5, 10):
        if span / (step * m) <= n:
            step *= m
            break
    t, out = math.floor(lo / step + 1e-9) * step, []
    while True:
        out.append(round(t, 10))
        if t >= hi - step * 1e-9:
            break
        t += step
    return out


def fig_years(fails):
    yrs = [int(str(f["launch_utc"])[:4]) for f in fails if f.get("launch_utc")]
    if not yrs:
        return ""
    y0, y1 = min(yrs), max(yrs)
    allc = Counter(yrs)
    inc = Counter(int(str(f["launch_utc"])[:4]) for f in fails if f.get("in_rival_test") or f.get("in_provider_case_series"))
    W, H, m = 720, 230, dict(l=36, r=10, t=12, b=28)
    top = max(allc.values())
    tk = _ticks(0, top, 5)
    x = _lin(y0, y1 + 1, m["l"], W - m["r"]); y = _lin(0, tk[-1], H - m["b"], m["t"])
    bw = (x(y0 + 1) - x(y0)) * 0.72
    s = "".join(f'<line x1="{m["l"]}" x2="{W - m["r"]}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{RULE}"/>'
                f'<text x="{m["l"] - 6}" y="{y(t) + 4:.1f}" text-anchor="end" fill="{MUTED}">{t:g}</text>' for t in tk)
    for yr in range(y0, y1 + 1):
        a, b = allc.get(yr, 0), inc.get(yr, 0)
        xx = x(yr) + (x(yr + 1) - x(yr) - bw) / 2
        if a:
            s += f'<rect x="{xx:.1f}" y="{y(a):.1f}" width="{bw:.1f}" height="{y(0) - y(a):.1f}" fill="none" stroke="{INK}"/>'
        if b:
            s += f'<rect x="{xx:.1f}" y="{y(b):.1f}" width="{bw:.1f}" height="{y(0) - y(b):.1f}" fill="{INK}"/>'
        if yr % 5 == 0:
            s += f'<text x="{x(yr) + (x(yr + 1) - x(yr)) / 2:.1f}" y="{H - 8}" text-anchor="middle" fill="{MUTED}">{yr}</text>'
    s += f'<line x1="{m["l"]}" x2="{W - m["r"]}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{INK}"/>'
    return _svg(W, H, "Orbital launch failures per year; filled part enters the study.", s)


def _anchored(path):
    ar = {p["t"]: p["ar"] for p in path}
    lo, hi = min(ar), max(ar)
    out, back = [(-1, 0.0)], 0.0
    for t in range(-2, lo - 2, -1):
        a = ar.get(t + 1)
        if a is None:
            break
        back += a; out.insert(0, (t, -back))
    c = 0.0
    for t in range(0, hi + 1):
        a = ar.get(t)
        if a is None:
            break
        c += a; out.append((t, c))
    return out


def fig_paths(cases):
    if not cases:
        return ""
    series = [(f'{c["vehicle"]}, {MONTHS[int(str(c["day0"])[5:7]) - 1]} {str(c["day0"])[:4]}', _anchored(c["path"])) for c in cases]
    vals = [v for _, p in series for _, v in p]
    lo, hi = min(vals + [0]), max(vals + [0])
    W, H, m = 720, 300, dict(l=46, r=175, t=14, b=30)
    tk = _ticks(lo, hi, 6)
    x = _lin(-6, 20, m["l"], W - m["r"]); y = _lin(tk[0], tk[-1], H - m["b"], m["t"])
    s = "".join(f'<line x1="{m["l"]}" x2="{W - m["r"]}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{RULE}"/>'
                f'<text x="{m["l"] - 6}" y="{y(t) + 4:.1f}" text-anchor="end" fill="{MUTED}">{pct(t, 0)}</text>' for t in tk)
    s += f'<line x1="{x(-0.5):.1f}" x2="{x(-0.5):.1f}" y1="{m["t"]}" y2="{H - m["b"]}" stroke="{INK}" stroke-dasharray="3 3"/>'
    s += f'<line x1="{m["l"]}" x2="{W - m["r"]}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{INK}"/>'
    for t in (-5, -1, 0, 1, 5, 10, 15, 20):
        lab = "T0" if t == 0 else (f"T+{t}" if t > 0 else f"T−{-t}")
        s += f'<text x="{x(t):.1f}" y="{H - 10}" text-anchor="middle" fill="{MUTED}">{lab}</text>'
    ends = []
    for i, (lab, p) in enumerate(series):
        d = " ".join(f'{"M" if j == 0 else "L"}{x(t):.1f},{y(v):.1f}' for j, (t, v) in enumerate(p))
        s += f'<path d="{d}" fill="none" stroke="{SIGNAL}" stroke-width="1.6" stroke-opacity="{0.55 + 0.45 * (i % 2)}"/>'
        ends.append([y(p[-1][1]), f"{lab}: {pct(p[-1][1])}"])
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 14)
    for yy, lab in ends:
        s += f'<text x="{W - m["r"] + 6}" y="{yy + 4:.1f}" font-size="10.5">{e(lab)}</text>'
    return _svg(W, H, "Cumulative abnormal return of the rocket's maker around each failure, zero at the close before the failure.", s)


def fig_forest(rows):
    """rows: (label, mean, lo, hi, kind) with kind in {'primary','robust','explore'}"""
    rows = [r for r in rows if r[1] is not None and r[2] is not None]
    if not rows:
        return ""
    W, m, rh = 720, dict(l=300, r=20, t=10, b=30), 22
    H = m["t"] + m["b"] + rh * len(rows)
    lo, hi = min(r[2] for r in rows + [("", 0, 0, 0, "")]), max(r[3] for r in rows + [("", 0, 0, 0, "")])
    tk = _ticks(lo, hi, 6)
    x = _lin(tk[0], tk[-1], m["l"], W - m["r"])
    s = "".join(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{m["t"]}" y2="{H - m["b"]}" stroke="{RULE}"/>'
                f'<text x="{x(t):.1f}" y="{H - 10}" text-anchor="middle" fill="{MUTED}">{pct(t, 1)}</text>' for t in tk)
    s += f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{m["t"]}" y2="{H - m["b"]}" stroke="{INK}"/>'
    for i, (lab, mu, a, b, kind) in enumerate(rows):
        cy = m["t"] + rh * i + rh / 2
        col = INK if kind != "explore" else MUTED
        if kind == "primary":
            s += f'<rect x="0" y="{cy - rh / 2:.1f}" width="{W}" height="{rh}" fill="{DEEP}"/>'
        s += f'<text x="{m["l"] - 10}" y="{cy + 4:.1f}" text-anchor="end" fill="{col}" font-size="10.5">{e(lab)}</text>'
        s += f'<line x1="{x(a):.1f}" x2="{x(b):.1f}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="{col}" stroke-width="1.6"/>'
        s += (f'<circle cx="{x(mu):.1f}" cy="{cy:.1f}" r="{4.5 if kind == "primary" else 3.5}" '
              f'fill="{col if kind != "explore" else "#F3EEE4"}" stroke="{col}" stroke-width="1.4"/>')
    return _svg(W, H, "Average competitor reaction with 95% intervals: main test, prespecified checks and exploratory checks.", s)


def fig_placebo(pl):
    d = [v for v in (pl.get("distribution") or []) if v is not None]
    if not d:
        return ""
    act = pl["actual_mean_car"]
    lo, hi = min(d + [act]), max(d + [act])
    tk = _ticks(lo, hi, 6)
    nb = 30
    w = (tk[-1] - tk[0]) / nb
    counts = [0] * nb
    for v in d:
        counts[min(nb - 1, max(0, int((v - tk[0]) / w)))] += 1
    W, H, m = 720, 220, dict(l=36, r=34, t=22, b=28)
    yt = _ticks(0, max(counts), 4)
    x = _lin(tk[0], tk[-1], m["l"], W - m["r"]); y = _lin(0, yt[-1], H - m["b"], m["t"])
    s = "".join(f'<line x1="{m["l"]}" x2="{W - m["r"]}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{RULE}"/>'
                f'<text x="{m["l"] - 6}" y="{y(t) + 4:.1f}" text-anchor="end" fill="{MUTED}">{t:g}</text>' for t in yt)
    for i, c in enumerate(counts):
        if c:
            x0 = tk[0] + i * w
            beyond = (x0 >= act) if act >= 0 else (x0 + w <= act)
            s += (f'<rect x="{x(x0) + 0.5:.1f}" y="{y(c):.1f}" width="{x(x0 + w) - x(x0) - 1:.1f}" height="{y(0) - y(c):.1f}" '
                  f'fill="{SIGNAL if beyond else MUTED}" fill-opacity="{0.85 if beyond else 0.45}"/>')
    s += "".join(f'<text x="{x(t):.1f}" y="{H - 8}" text-anchor="middle" fill="{MUTED}">{pct(t, 1)}</text>' for t in tk)
    s += (f'<line x1="{x(act):.1f}" x2="{x(act):.1f}" y1="{m["t"] - 6}" y2="{H - m["b"]}" stroke="{INK}" stroke-width="2"/>'
          + (f'<text x="{x(act) - 6:.1f}" y="{m["t"] + 4}" text-anchor="end">real failures {pct(act, 2)}</text>' if x(act) > W * 0.7
             else f'<text x="{x(act) + 6:.1f}" y="{m["t"] + 4}">real failures {pct(act, 2)}</text>'))
    return _svg(W, H, "Distribution of placebo averages from random ordinary days, with the real result marked.", s)


# ----------------------------------------------------------------------------- text helpers
def _ci(a, b, d=2):
    return f"{pct(a, d)} to {pct(b, d)}"


def _fig(n, title, svg, cap):
    return (f'<figure class="cs-fig"><figcaption class="cs-figtitle"><span>Figure {n}.</span> {e(title)}</figcaption>'
            f'{svg}<figcaption class="cs-cap">{cap}</figcaption></figure>') if svg else ""


def _table(head, rows, cls=""):
    return (f'<div class="table-wrap"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head)
            + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
            + "</tbody></table></div>")


def _plain_name(n):
    rep = {"R1 portfolio t-test": "Portfolio t-test (one average per independent event)",
           "R1 portfolio sign test": "Sign test (share of events with a positive average)",
           "R2 plain t": "Plain t-test, no volatility weighting",
           "R3 rank (simulated p)": "Rank test (simulated p-value)",
           "R4 window [-1,+3]": "Wider window, T−1 to T+3",
           "R5a drop low-confidence timing": "Drop failures with uncertain timing",
           "R5b low-confidence day 0 + 1 session": "Uncertain timing moved one session later",
           "R6 drop fallback-model events": "Drop firms with a short price history",
           "R7 drop multi-failure clusters": "Drop clusters with several failures"}
    if n in rep:
        return rep[n]
    if n.startswith("R8 without "):
        return f"Leave out {n[len('R8 without '):]}"
    return n


# ----------------------------------------------------------------------------- extra figures
def fig_funnel(stages):
    """stages: list of (label, value); horizontal bars on a log-free linear scale, labelled."""
    stages = [(l, v) for l, v in stages if v is not None]
    if not stages:
        return ""
    W, rh, m = 720, 34, dict(l=300, r=70, t=8, b=8)
    H = m["t"] + m["b"] + rh * len(stages)
    top = max(v for _, v in stages)
    s = ""
    for i, (lab, v) in enumerate(stages):
        y = m["t"] + i * rh
        w = max(2.0, (W - m["l"] - m["r"]) * (v / top) ** 0.5)     # square-root scale so small stages stay visible
        s += f'<text x="{m["l"] - 10}" y="{y + rh / 2 + 4:.1f}" text-anchor="end" font-size="11">{e(lab)}</text>'
        s += f'<rect x="{m["l"]}" y="{y + 6}" width="{w:.1f}" height="{rh - 12}" fill="{INK if i else "none"}" stroke="{INK}"/>'
        s += f'<text x="{m["l"] + w + 8:.1f}" y="{y + rh / 2 + 4:.1f}" font-size="12" font-weight="700">{v:,}</text>'
    return _svg(W, H, "Sample construction from all launch attempts to independent rival events.", s)


def fig_exposure(firms, rows):
    if not rows:
        return ""
    W, m = 720, dict(l=150, r=10, t=30, b=8)
    cw = (W - m["l"] - m["r"]) / len(rows)
    rh = 26
    H = m["t"] + m["b"] + rh * len(firms)
    s = ""
    for j, r in enumerate(rows):
        x = m["l"] + j * cw
        if j % 3 == 0:
            s += f'<text x="{x + cw / 2:.1f}" y="{m["t"] - 8}" text-anchor="middle" font-size="9" fill="{MUTED}">{r["date"][:4]}</text>'
        for i, f in enumerate(firms):
            n = r["counts"].get(f, 0)
            y = m["t"] + i * rh
            s += (f'<rect x="{x + 1:.1f}" y="{y + 3}" width="{cw - 2:.1f}" height="{rh - 6}" fill="{INK if n else "none"}" '
                  f'stroke="{RULE if not n else INK}"/>')
            if n > 1:
                s += f'<text x="{x + cw / 2:.1f}" y="{y + rh / 2 + 4}" text-anchor="middle" font-size="10" fill="#F3EEE4">{n}</text>'
    for i, f in enumerate(firms):
        s += f'<text x="{m["l"] - 8}" y="{m["t"] + i * rh + rh / 2 + 4}" text-anchor="end" font-size="11">{e(f)}</text>'
    return _svg(W, H, "Which rival firm is present in each independent event, in date order.", s)


# ----------------------------------------------------------------------------- page helpers
class _Num:
    def __init__(self):
        self.fig = 0; self.tab = 0; self.eq = 0


def _figure(num, fid, title, svg, cap):
    if not svg:
        return ""
    num.fig += 1
    return (f'<figure class="cs-fig" data-fig="{fid}"><figcaption class="cs-figtitle"><span>Figure {num.fig}.</span> {e(title)}</figcaption>'
            f'{svg}<figcaption class="cs-cap">{cap}</figcaption></figure>')


def _ttable(num, title, head, rows, note="", cls=""):
    num.tab += 1
    return (f'<div class="cs-table"><p class="tcap"><strong>Table {num.tab}.</strong> {e(title)}</p>' + _table(head, rows, cls)
            + (f'<p class="cs-cap">{note}</p>' if note else "") + "</div>")


def _eq(num, html_body, tex):
    num.eq += 1
    return f'<div class="eq" data-tex="{e(tex)}"><span class="eq-body">{html_body}</span><span class="eq-no">({num.eq})</span></div>'


WHY = {"no_firm_map_match": "maker not a listed company",
       "provider_not_listed_or_not_owner_on_date": "maker not listed, or not the owner, on that date",
       "no_segment_for_vehicle": "rocket not in the size-and-market table"}


# ----------------------------------------------------------------------------- page
def build(data: dict, meta: dict, root: Path, css: str, pdf_name: str | None) -> str:
    import json as _json

    import diagnostics as D
    import landing

    f = facts(data)
    res, man, fails, fes = data["results"], data["manifest"], data["failures"], data["firmEvents"]
    p, pl, e1 = f["prim"], f["placebo"], f["e1"]
    cases = res.get("provider_case_series") or []
    robust = [r for r in (res.get("robustness") or []) if r.get("p") is not None]
    conf = [r for r in (res.get("exploratory_confounding") or {}).get("results", []) if r.get("id") in ("E1", "E2", "E3")]
    expl = res.get("exploratory") or []
    r9b = (res.get("exploratory_audit") or {}).get("placebo_shared")
    st = res.get("settings") or {}
    win = man["windows"]
    est = st.get("estimation_window", [-250, -30])
    span = f"{f['first_year']} to {f['last_year']}"
    all_fell = f["case_hi"] is not None and f["case_hi"] < 0
    detect = p["p"] < 0.05
    w, pw, firms = f["w"] or {}, f["pw"] or {}, f["firms"]
    w_e1 = f["w_e1"]
    updated = month(man.get("results_run_utc") or datetime.utcnow().isoformat())
    year = str(man.get("results_run_utc", ""))[:4]
    riv = [r for r in fes if r["group"] == "rival"]
    n_case_firms = len({c["ticker"] for c in cases})
    sample = man.get("sample") or {}
    num = _Num()
    t = lambda k: (lambda wd: ("T0" if wd[0] == 0 else f"T−{-wd[0]}") + " to " + f"T+{wd[1]}")(win[k])
    note_t = (p.get("note") or "")
    t_unadj = next((float(x.split("=")[1]) for x in note_t.split(";") if "unadjusted" in x), None)
    adj = next((float(x.split("=")[1]) for x in note_t.split(";") if "adjustment factor" in x), None)
    sign_flips = bool(w) and min(w["observation_weighted"], w["event_weighted"], w["precision_weighted"], w["firm_balanced"]) < 0 \
        < max(w["observation_weighted"], w["event_weighted"], w["precision_weighted"], w["firm_balanced"])
    rob_lo, rob_hi = f["rob_min"], f["rob_max"]
    r8 = [r for r in robust if r["name"].startswith("R8")]
    r8_flip = any((r["mean_car"] < 0) != (p["mean_car"] < 0) for r in r8)
    e1_drop = [x for x in riv if e1 and f"{x['launch_tag']} {x['ticker']}" in set(e1.get("dropped") or [])]
    n_e1 = len(e1_drop)
    e1_sign = ("positive" if all(x["windows"]["primary"]["car"] > 0 for x in e1_drop) else
               "negative" if all(x["windows"]["primary"]["car"] < 0 for x in e1_drop) else "")
    n_sector = sum(1 for x in riv if (x.get("flag") or {}).get("verdict") == "sector_move")
    n_low = len({x["launch_tag"] for x in riv if x.get("disclosure_confidence") == "low"})
    words = ["no", "one", "two", "three", "four", "five", "six"]
    nw = lambda n: words[n] if n < len(words) else str(n)
    top_all = f["top_firm_clusters"] == f["n_clusters"]
    blob = (meta["repo_url"].rstrip("/") + "/blob/master/") if meta.get("repo_url") else None
    verif = None
    vp = root / "audit" / "verification.json"
    if vp.exists():
        try:
            ch = _json.loads(vp.read_text())["checks"]
            verif = (sum(1 for c in ch if c["ok"]), len(ch))
        except (ValueError, KeyError):
            verif = None

    # ---------------- abstract (data-driven, conditional wording)
    abstract = (
        f"This paper asks how equity markets react when an orbital launch fails, both for the company that built the rocket and for "
        f"its publicly listed competitors. Using {f['n_failures']} orbital launch failures from {span} (GCAT) and a market-model event "
        f"study with a prespecified test, it finds that in the {f['n_cases']} failures with a listed maker ({n_case_firms} firms) "
        + (f"the maker lost between {pct(abs(f['case_hi']), 1, False)} and {pct(abs(f['case_lo']), 1, False)} of market value over two "
           f"trading days, each case with a 95% interval excluding zero. " if all_fell and all(c['car_primary_ci'][1] < 0 for c in cases)
           else f"two-day abnormal returns ranged from {pct(f['case_lo'])} to {pct(f['case_hi'])}. ")
        + f"Across {f['n_rival_failures']} failures with listed competitors ({p['n_firm_events']} stock reactions, {f['n_rival_firms']} firms, "
        f"{f['n_clusters']} independent events), the average two-day cumulative abnormal return is {pct(p['mean_car'], 2)} (95% "
        f"cluster-robust interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}; Boehmer-Musumeci-Poulsen test with Kolari-Pynnönen "
        f"adjustment, p = {pval(p['p'])}). "
        + ("The evidence therefore establishes neither systematic contagion nor systematic competitive gains among these firms, "
           f"and it does not show the effect is negligible: average effects of about {pct(pw['mde80'], 1, False)} in either direction "
           f"would usually go undetected. " if not detect and pw else "")
        + (f"The sign of the estimate changes with how events and firms are weighted, and every independent event involves "
           f"{f['top_firm']}. " if sign_flips and top_all else "")
        + "The study is a small-sample case study of listed firms, not an estimate for the launch industry as a whole.")

    inshort = [
        f"<strong>The rocket's maker:</strong> " + (f"large losses in each of {f['n_cases']} cases ({pct(f['case_hi'])} to {pct(f['case_lo'])} over two days)."
                                                     if all_fell else f"mixed reactions across {f['n_cases']} cases."),
        f"<strong>Listed competitors:</strong> {pct(p['mean_car'], 2)} on average (95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}; p = {pval(p['p'])}): "
        + ("no detectable reaction." if not detect else "a detectable reaction."),
        (f"<strong>Uncertainty:</strong> effects of about {pct(pw['mde80'], 1, False)} either way could go undetected; " if pw else "<strong>Uncertainty:</strong> ")
        + ("the sign depends on weighting." if sign_flips else "see section 7."),
        "<strong>Status:</strong> working paper for feedback; plan prespecified in git, not independently registered.",
    ]

    # ---------------- tables
    funnel_rows = [("Orbital launch attempts", sample.get("launch_attempts")), ("Launch failures", sample.get("failures") or f["n_failures"]),
                   ("Failures with a listed firm involved", sample.get("failures_with_any_listed_firm")),
                   ("Failures with listed competitors", f["n_rival_failures"]), ("Competitor stock reactions", p["n_firm_events"]),
                   ("Independent competitor events", f["n_clusters"]), ("Listed competitor firms", f["n_rival_firms"])]
    desc_rows = [[e(x["firm"]), e(x["ticker"]), str(x["n"]), str(x["clusters"]), f'<span class="num">{pct(x["mean"], 2)}</span>',
                  f'<span class="num">{pct(x["median"], 2)}</span>', f'<span class="num">{pct(x["min"], 1)} to {pct(x["max"], 1)}</span>'] for x in firms]
    if w:
        desc_rows.append(["<strong>All</strong>", "", str(w["n"]), str(f["n_clusters"]), f'<span class="num">{pct(w["observation_weighted"], 2)}</span>',
                          f'<span class="num">{pct(w["median"], 2)}</span>',
                          f'<span class="num">{pct(min(x["min"] for x in firms), 1)} to {pct(max(x["max"] for x in firms), 1)}</span>'])
    case_rows = [[e(c["vehicle"]), e(day(c["day0"])), e(f'{c["firm"]} ({c["ticker"]})'),
                  f'<span class="num">{pct(c["car_primary"])}</span>', f'<span class="num">{_ci(*c["car_primary_ci"], 1)}</span>',
                  f'<span class="num">{pct(c.get("car_robust"))}</span>'] for c in cases]
    inf_rows = [["Mean CAR, equal weight per reaction", f'<span class="num">{pct(p["mean_car"], 2)}</span>'],
                ["95% cluster-robust interval (t, G−1 df)", f'<span class="num">{_ci(p["ci_low"], p["ci_high"])}</span>'],
                ["Mean standardized CAR (BMP)", f'<span class="num">{w.get("mean_standardized", float("nan")):.3f}</span>' if w else "n/a"],
                ["BMP t, unadjusted", f'<span class="num">{t_unadj:.3f}</span>' if t_unadj is not None else "n/a"],
                ["Kolari-Pynnönen adjustment factor", f'<span class="num">{adj:.3f}</span>' if adj is not None else "n/a"],
                ["Adjusted t / p (two-sided)", f'<span class="num">{p["stat"]:.3f} / {pval(p["p"])}</span>'],
                ["Mean within-cluster correlation", f'<span class="num">{p.get("mean_within_cluster_corr", 0):.3f}</span>'],
                ["Reactions / failures / firms / clusters", f'{p["n_firm_events"]} / {p["n_failures"]} / {p["n_firms"]} / {p["n_clusters"]}']]
    if pw:
        inf_rows += [["Minimum detectable effect (80% / 90% power)", f'<span class="num">{pct(pw["mde80"], 1, False)} / {pct(pw["mde90"], 1, False)}</span>'],
                     ["Power against a true ±1% / ±2% / ±3% mean", f'<span class="num">{pw["power"][0.01]:.2f} / {pw["power"][0.02]:.2f} / {pw["power"][0.03]:.2f}</span>'],
                     ["90% interval (for an equivalence reading)", f'<span class="num">{_ci(*pw["ci90"])}</span>']]
    wt_rows = [[a, f'<span class="num">{pct(w[k], 2)}</span>', b] for a, k, b in (
        ("Every reaction equal (prespecified estimand)", "observation_weighted", "the main estimate"),
        ("Every independent event equal", "event_weighted", "same as the R1 portfolio average"),
        ("Inverse prediction-error SD", "precision_weighted", "closest to the BMP statistic"),
        ("Every firm equal", "firm_balanced", "each firm's mean, then averaged"),
        ("Median reaction", "median", "not driven by a few large moves"))] if w else []
    rob_rows = [[e(_plain_name(r["name"])), f'<span class="num">{pct(r["mean_car"], 2)}</span>',
                 f'<span class="num">{_ci(r["ci_low"], r["ci_high"]) if r.get("ci_low") is not None else "test only"}</span>',
                 f'<span class="num">{pval(r["p"])}</span>', str(r.get("n_firm_events") or ""), str(r.get("n_clusters") or "")] for r in robust]
    conf_lab = {"E1": "Drop the contract-news days", "E2": "Also drop possible same-day news", "E3": "Drop every flagged day"}
    conf_rows = [["Main test (prespecified)", f'<span class="num">{pct(p["mean_car"], 2)}</span>', f'<span class="num">{_ci(p["ci_low"], p["ci_high"])}</span>',
                  f'<span class="num">{pval(p["p"])}</span>', f'<span class="num">{pct(w["median"], 2)}</span>' if w else "", str(p["n_firm_events"]), str(p["n_clusters"])]]
    for r in conf:
        wd = D.weighting(fes, drop=r.get("dropped") or [])
        conf_rows.append([e(conf_lab.get(r["id"], r["id"])) + " (exploratory)", f'<span class="num">{pct(r["mean_car"], 2)}</span>',
                          f'<span class="num">{_ci(r["ci_low"], r["ci_high"])}</span>', f'<span class="num">{pval(r["p"])}</span>',
                          f'<span class="num">{pct(wd["median"], 2)}</span>', str(r["n_firm_events"]), str(r["n_clusters"])])
    flagged = [r for r in riv if r.get("flag")]
    flag_rows = [[e(f'{r["firm"]}'), e(f'{r["vehicle"]}, {day(r["day0"])}'), f'<span class="num">{pct(r["windows"]["primary"]["car"], 2)}</span>',
                  e(r["flag"]["verdict"].replace("_", " ")), e(r["flag"].get("reason", "")) + (f' <a href="{e(r["flag"]["source"])}">[source]</a>' if r["flag"].get("source") else "")]
                 for r in sorted(flagged, key=lambda r: -abs(r["windows"]["primary"]["car"]))]
    expl_lab = {"H3a": "Competitors: first-flight failures minus other failures", "H3b": "Maker: failures minus successful launches",
                "H3c": "Competitors over one month (T0 to T+20)"}
    expl_rows = [[e(expl_lab.get(x["id"], x["label"])), f'<span class="num">{pct(x.get("estimate"), 2)}</span>',
                  f'<span class="num">{pval(x.get("p_raw"))}</span>', f'<span class="num">{pval(x.get("p_holm"))}</span>'] for x in expl]
    ev_rows = [[e(r["launch_tag"]), e(r["vehicle"]), e(r["day0"]), e(r["ticker"]), str(r["cluster"]),
                "MM" if r["model"] == "market_model" else "MA", e(r.get("disclosure_confidence") or ""), e((r.get("flag") or {}).get("verdict", "").replace("_", " ")),
                f'<span class="num">{pct(r["windows"]["primary"]["car"], 2)}</span>', f'<span class="num">{pct(r["windows"]["primary"]["var"] ** 0.5, 2, False)}</span>']
               for r in sorted(riv, key=lambda r: (r["day0"], r["ticker"]))]
    why = Counter()
    for x in fails:
        if not (x.get("in_rival_test") or x.get("in_provider_case_series")):
            for code in str(x.get("why_not_in_sample") or "no listed maker or listed competitor").split(";"):
                why[WHY.get(code.strip(), code.strip().replace("_", " "))] += 1
    why_rows = [[e(k), str(v)] for k, v in why.most_common()]
    drop_rows = [[e(k.replace("_", " ")), str(v)] for k, v in (sample.get("failure_firm_events_dropped") or {}).items()]

    # ---------------- figures
    firm_names, exp_rows = D.exposure_matrix(fes)
    forest = [("Main test (prespecified)", p["mean_car"], p["ci_low"], p["ci_high"], "primary")]
    forest += [(_plain_name(r["name"]), r["mean_car"], r.get("ci_low"), r.get("ci_high"), "robust") for r in robust]
    conf_forest = [("Main test (prespecified)", p["mean_car"], p["ci_low"], p["ci_high"], "primary")]
    short = {"E1": "Exploratory: drop contract days", "E2": "Exploratory: also possible news", "E3": "Exploratory: drop all flagged"}
    conf_forest += [(short.get(r["id"], r["id"]), r["mean_car"], r["ci_low"], r["ci_high"], "explore") for r in conf]

    links = [("The article (one-page summary)", "index.html", "Key numbers and links"),
             ("Interactive report", "site/index.html", "Five stages and four interactive tools"),
             ("Analysis plan and change log", "plan.html", "Rules fixed before results, and every later change")]
    if blob:
        links += [("Feasibility report", blob + "reports/04_feasibility_report.md", "Sample and minimum detectable effects, before results"),
                  ("Results report", blob + "reports/05_results.md", "All prespecified results"),
                  ("Confounding-news checks", blob + "docs/CONFOUNDING_NEWS.md", "News around the largest reactions, with sources"),
                  ("Independent audit", blob + "audit/AUDIT_REPORT.md", "Verification of every published statistic"),
                  ("Code and pipeline", meta["repo_url"], "Python pipeline, tests and reproduction guide")]
    pdf_row = ("This paper as PDF", pdf_name, "Typeset version (LaTeX)") if pdf_name else None
    nav = " · ".join(f'<a href="{e(h)}">{e(l)}</a>' for l, h in
                     [("Article", "index.html"), ("Interactive report", "site/index.html"), ("Analysis plan", "plan.html")]
                     + ([("Code", meta["repo_url"])] if meta.get("repo_url") else []))
    nav += (f' <span class="screen-only">· <a href="{e(pdf_name)}">PDF</a></span>' if pdf_name else "")
    contents = ["Introduction", "Institutional background", "Related literature", "Data and sample construction", "Empirical methodology",
                "Main results", "Robustness and sensitivity", "Confounding news", "Discussion", "Limitations", "Conclusion"]

    eqs = [
        _eq(num, "<i>R</i><sub><i>it</i></sub> = <i>α</i><sub><i>i</i></sub> + <i>β</i><sub><i>i</i></sub> <i>R</i><sub><i>mt</i></sub> + <i>ε</i><sub><i>it</i></sub>",
            r"R_{it} = \alpha_i + \beta_i R_{mt} + \varepsilon_{it}"),
        _eq(num, "<i>AR</i><sub><i>it</i></sub> = <i>R</i><sub><i>it</i></sub> − (<i>α̂</i><sub><i>i</i></sub> + <i>β̂</i><sub><i>i</i></sub> <i>R</i><sub><i>mt</i></sub>), &nbsp; <i>CAR</i><sub><i>i</i></sub>(<i>τ</i><sub>1</sub>, <i>τ</i><sub>2</sub>) = Σ<sub><i>t</i>=<i>τ</i><sub>1</sub></sub><sup><i>τ</i><sub>2</sub></sup> <i>AR</i><sub><i>it</i></sub>",
            r"AR_{it} = R_{it} - (\hat\alpha_i + \hat\beta_i R_{mt}), \qquad CAR_i(\tau_1,\tau_2) = \sum_{t=\tau_1}^{\tau_2} AR_{it}"),
        _eq(num, "Var(<i>CAR</i><sub><i>i</i></sub>) = <i>σ̂</i><sub><i>i</i></sub><sup>2</sup> [ <i>L</i> + <i>L</i><sup>2</sup>/<i>T</i> + (Σ<sub><i>t</i>∈<i>W</i></sub>(<i>R</i><sub><i>mt</i></sub> − <i>R̄</i><sub><i>m</i></sub>))<sup>2</sup> / Σ<sub><i>t</i>∈<i>E</i></sub>(<i>R</i><sub><i>mt</i></sub> − <i>R̄</i><sub><i>m</i></sub>)<sup>2</sup> ]",
            r"\mathrm{Var}(CAR_i) = \hat\sigma_i^2\left[L + \frac{L^2}{T} + \frac{\left(\sum_{t\in W}(R_{mt}-\bar R_m)\right)^2}{\sum_{t\in E}(R_{mt}-\bar R_m)^2}\right]"),
        _eq(num, "<i>SCAR</i><sub><i>i</i></sub> = <i>CAR</i><sub><i>i</i></sub> / √Var(<i>CAR</i><sub><i>i</i></sub>), &nbsp; <i>t</i><sub>BMP</sub> = √<i>N</i> · <span class=\"ov\">SCAR</span> / <i>s</i><sub>SCAR</sub>",
            r"SCAR_i = \frac{CAR_i}{\sqrt{\mathrm{Var}(CAR_i)}}, \qquad t_{BMP} = \frac{\sqrt{N}\,\overline{SCAR}}{s_{SCAR}}"),
        _eq(num, "<i>t</i><sub>KP</sub> = <i>t</i><sub>BMP</sub> √[(1 − <i>r̄</i>) / (1 + (<i>N</i> − 1) <i>r̄</i>)], &nbsp; <i>r̄</i> = Σ<sub><i>i</i>≠<i>j</i>, <i>c</i>(<i>i</i>)=<i>c</i>(<i>j</i>)</sub> <i>ρ</i><sub><i>ij</i></sub> / (<i>N</i>(<i>N</i> − 1)), &nbsp; <i>ρ</i><sub><i>ij</i></sub> = corr(<i>ε</i><sub><i>i</i></sub>, <i>ε</i><sub><i>j</i></sub>) · ℓ<sub><i>ij</i></sub> / <i>L</i>",
            r"t_{KP} = t_{BMP}\sqrt{\frac{1-\bar r}{1+(N-1)\bar r}}, \quad \bar r = \frac{\sum_{i\neq j,\,c(i)=c(j)} \rho_{ij}}{N(N-1)}, \quad \rho_{ij} = \mathrm{corr}(\varepsilon_i,\varepsilon_j)\,\frac{\ell_{ij}}{L}"),
        _eq(num, "<i>SE</i><sub>CR</sub> = (1/<i>N</i>) √[ <i>G</i>/(<i>G</i> − 1) · Σ<sub><i>g</i></sub> (Σ<sub><i>i</i>∈<i>g</i></sub> (<i>CAR</i><sub><i>i</i></sub> − <span class=\"ov\">CAR</span>))<sup>2</sup> ], &nbsp; interval: <span class=\"ov\">CAR</span> ± <i>t</i><sub><i>G</i>−1, 0.975</sub> <i>SE</i><sub>CR</sub>",
            r"SE_{CR} = \frac{1}{N}\sqrt{\frac{G}{G-1}\sum_g\Big(\sum_{i\in g}(CAR_i-\overline{CAR})\Big)^2}, \qquad \overline{CAR} \pm t_{G-1,\,0.975}\,SE_{CR}"),
    ]

    body = f"""<header class="masthead cs-head"><div class="wrap">
  <div class="kicker"><span><a href="index.html">T-Minus Markets</a></span><span>Working paper</span></div>
  <h1>Rocket Launch Failures and Equity-Market Spillovers: Evidence from Publicly Listed Launch Providers</h1>
  <p class="dek">A T-Minus Markets case study of stock market reactions to orbital launch failures, {e(span)}.</p>
  <p class="byline">{e(meta.get("author", "Nahian Ibnat"))} · {e(updated)} · Draft for feedback, not peer reviewed · {nav}</p>
</div></header>
<main id="main" class="wrap article cs">
<section class="abstract-sec"><h2>Abstract</h2><p>{e(abstract)}</p>
<p class="keywords"><strong>Keywords:</strong> event study; industry spillovers; contagion; competitive effects; launch failures. <strong>JEL:</strong> G14, L13.</p></section>

<aside class="inshort screen-only"><h2>In short</h2><ul>{"".join(f"<li>{b}</li>" for b in inshort)}</ul></aside>
<nav class="toc screen-only" aria-label="Contents"><h2>Contents</h2><ol>{"".join(f'<li><a href="#s{i}">{e(c)}</a></li>' for i, c in enumerate(contents, 1))}<li><a href="#apx">Appendices</a></li></ol></nav>

<section id="s1"><h2>1. Introduction</h2>
<p>When a rocket fails, the company that built it loses hardware, often a customer's satellite, and usually months of flights while the cause is investigated. Its competitors face a less obvious outcome. Investors may read the failure as a reminder that spaceflight is risky for every provider, which lowers rivals' values (contagion), or they may expect customers to move to providers whose rockets work, which raises them (competitive gain). The two channels push in opposite directions, so the net reaction of rivals is an empirical question.</p>
<p>This paper measures both reactions with a short-window event study. Launch failures suit the method: they are sudden, public, precisely timed, and unrelated to the rivals' own decisions. The confirmatory hypothesis (H2) is that the average two-day abnormal return of listed rivals is zero. All rules were fixed in a written plan committed to the project repository before any abnormal return was computed.</p>
<p>The answer is limited by the sample. Only {f['n_rival_firms']} listed launch firms qualify as direct rivals at the time of a failure, so the study observes {f['n_clusters']} independent rival events{f", every one of which involves {e(f['top_firm'])}" if top_all else ""}. {"The average reaction is not distinguishable from zero, but the interval is wide enough to contain economically meaningful losses and gains." if not detect else "The average reaction is distinguishable from zero."} The contribution is therefore a carefully documented, reproducible estimate with honest uncertainty, rather than a general claim about the launch industry.</p>
<p>Section 2 describes the industry; section 3 relates the study to earlier work; sections 4 and 5 describe data and methods; sections 6 to 8 report results, robustness and confounding news; sections 9 to 11 discuss, list limitations and conclude.</p></section>

<section id="s2"><h2>2. Institutional background</h2>
<p><strong>A concentrated market.</strong> Orbital launch is supplied by a small number of providers, many of them state agencies, state-owned firms or privately held companies. Launch contracts are usually signed years ahead, and a satellite is designed for a particular rocket, so customers cannot switch providers quickly. This limits how much business a rival can win in the days after a failure.</p>
<p><strong>Reliability.</strong> New rockets fail more often than mature ones, and a failure normally grounds the vehicle until an investigation is complete. For the maker, the loss includes the hardware, possible penalties or re-flights, delay of other launches and reputation.</p>
<p><strong>Ownership and listing.</strong> Few launch companies have been publicly traded with launch as a major business. Large aerospace groups that build rockets are diversified, so a launch failure is a small part of their value; the plan therefore counts them only when launch is a major part of the business. The listed pure-play or launch-heavy firms in the sample listed only in the last decade, so the sample of listed rival events starts late. SpaceX listed in June 2026 and has too little price history to enter.</p>
<p><strong>Disclosure.</strong> Most launches are broadcast live, so a failure becomes public at launch time. Where a failure is confirmed later, the first public company statement dates the event.</p></section>

<section id="s3"><h2>3. Related literature</h2>
<p><strong>Event-study method.</strong> The design follows MacKinlay (1997) and Brown and Warner (1985) for daily returns. The standardized test of Boehmer, Musumeci and Poulsen (1991) allows the event to raise return variance, and Kolari and Pynnönen (2010) show that cross-sectional correlation among event-day abnormal returns biases standard tests, and propose the adjustment used here. Corrado (1989) supplies a rank-based alternative.</p>
<p><strong>Contagion and competitive effects.</strong> Lang and Stulz (1992) find that bankruptcy announcements lower the value of a portfolio of competitors by about 1% on average, so contagion dominates in that setting. Bosch, Eckard and Singal (1998) study rival airlines after air crashes, testing whether customers switch carriers or fly less.</p>
<p><strong>Disasters and investor sentiment.</strong> Kaplanski and Levy (2010) report market-wide losses after aviation disasters that reverse within days, consistent with sentiment rather than fundamentals. For spaceflight, Blose et al. (1996) and Maloney and Mulherin (2003) study the Challenger disaster: NASA contractors fell together on the day, and within days the market singled out the firm whose component failed.</p>
<p><strong>Launch markets.</strong> Abramov and Kiang (2015) study how launch delays and failures affect satellite operators, the launch customers. Do et al. (2023) show that US satellite launch days draw investor attention away from firm-specific news. This paper studies a different group, the failed provider's listed competitors, over a multi-year sample.</p></section>

<section id="s4"><h2>4. Data and sample construction</h2>
<p><strong>Launch records.</strong> Every orbital launch attempt comes from GCAT (McDowell). A launch is a failure when its GCAT success score is below 0.75; pad explosions before launch are kept separately. Launch times come from GCAT's launch date field; where the company confirmed a failure later, the documented disclosure time is used and its confidence is recorded.</p>
<p><strong>Firms.</strong> Each failure is linked by hand, point in time, to its maker if listed and to listed rivals. A Tier 1 rival is listed, has launch as a pure-play or major business, sells a rocket of the same size class to the same customer market, and has flown that rocket in the previous 730 days. Firm-map rows used in tests are verified against filings or exchange notices.</p>
<p><strong>Prices.</strong> Daily adjusted closes from Yahoo Finance, used locally only; benchmarks are each firm's home market index. Prices from before a firm's real listing (a pre-merger shell) are dropped. Only derived statistics are published.</p>
<p><strong>Event dates and clusters.</strong> Day 0 (T0) is the first trading session at or after the failure became public, on the stock's own exchange calendar. Failures less than {st.get("cluster_gap", 5)} trading days apart that share a firm form one cluster.</p>
{_figure(num, "funnel", "Sample construction", fig_funnel(funnel_rows), "Bar length on a square-root scale. Counts come from the pipeline's interim files and exported data.")}
{_figure(num, "years", "Orbital launch failures per year", fig_years(fails), f"Outline: all orbital launch failures, {e(span)}. Filled: failures that enter the study.")}
{_ttable(num, "Rival reactions by firm, CAR " + t("primary"), ["Firm", "Ticker", "Reactions", "Clusters", "Mean", "Median", "Range"], desc_rows, f"Clusters: independent events in which the firm appears; {f['n_clusters']} in total.")}
{_figure(num, "exposure", "Which rival is present in each independent event", fig_exposure(firm_names, exp_rows), "Columns: independent events in date order. Filled: the firm is a rival in that event; a number means it appears more than once (two close failures).")}
</section>

<section id="s5"><h2>5. Empirical methodology</h2>
<p>For each stock and failure a market model is estimated by ordinary least squares on trading days {-est[0]} to {-est[1]} before day 0 (at least {st.get("min_obs", 100)} returns; with 30 to 99 returns a market-adjusted model with α = 0 and β = 1 is used and flagged):</p>
{eqs[0]}
<p>Abnormal returns and cumulative abnormal returns over an event window [τ<sub>1</sub>, τ<sub>2</sub>] are</p>
{eqs[1]}
<p>Returns are simple, and CARs are sums of simple abnormal returns. The variance of each CAR includes the prediction error of the estimated model (Campbell, Lo and MacKinlay, 1997), where <i>L</i> is the window length, <i>T</i> the number of estimation days, <i>W</i> the event window and <i>E</i> the estimation window:</p>
{eqs[2]}
<p>The confirmatory test is the standardized test of Boehmer, Musumeci and Poulsen (1991), which uses the cross-sectional spread of standardized CARs and so allows the failure to raise variance:</p>
{eqs[3]}
<p>Because one failure can hit several rivals, the statistic is adjusted as in Kolari and Pynnönen (2010). Correlation is non-zero only within a cluster <i>c</i>; for a pair it is the correlation of estimation-window residuals, scaled by the share of event-window days ℓ<sub><i>ij</i></sub> the two windows have in common. p-values use a t distribution with <i>G</i> − 1 degrees of freedom, where <i>G</i> is the number of independent clusters:</p>
{eqs[4]}
<p>The reported 95% interval is a separate, cluster-robust interval around the equal-weighted mean CAR. The test and the interval therefore concern slightly different quantities: the test weights each reaction by its precision, the interval does not.</p>
{eqs[5]}
{_ttable(num, "Event windows", ["Window", "Days", "Role"], [["Main", t("primary"), "Confirmatory test (H2)"], ["Wider", t("robust"), "Robustness check"], ["One month", t("descriptive"), "Description only"]])}
<p><strong>Prespecified checks.</strong> R1 one average per cluster (t-test and sign test); R2 plain t-test; R3 rank test with simulated p-value; R4 the wider window; R5 timing (drop or shift uncertain disclosure times); R6 drop market-adjusted fallbacks; R7 drop clusters with several failures; R8 leave one firm out; R9 a placebo on random non-event days. <strong>Exploratory analyses</strong>, designed after results were seen, are labelled wherever they appear and never replace H2.</p></section>

<section id="s6"><h2>6. Main results</h2>
<h3>6.1 The rocket's maker</h3>
<p>{"In every listed case the maker's shares fell over the two days after the failure became public, after allowing for the market, and each 95% interval excludes zero." if all_fell and all(c["car_primary_ci"][1] < 0 for c in cases) else "The listed cases are reported individually below."} With {f['n_cases']} cases from {n_case_firms} firm{"s" if n_case_firms != 1 else ""}, these are case studies, not an estimate of an average effect.</p>
{_ttable(num, "The rocket's maker: two-day abnormal returns", ["Rocket", "Failure", "Listed maker", f"CAR {t('primary')}", "95% interval", f"CAR {t('robust')}"], case_rows, "Intervals: CAR ± 1.96 × prediction-error standard deviation.")}
{_figure(num, "paths", "The rocket's maker: cumulative abnormal return", fig_paths(cases), "Each line is one case, set to zero at the close before the failure (T−1), so the value at T+1 is the two-day result in the table.")}
<h3>6.2 Listed competitors</h3>
<p>Table {num.tab + 1} reports the confirmatory test. The average two-day abnormal return of listed rivals is <strong>{pct(p['mean_car'], 2)}</strong> (95% interval {_ci(p['ci_low'], p['ci_high'])}); the adjusted BMP statistic is {p['stat']:.2f} (p = {pval(p['p'])}). {"H2 is not rejected at the 5% level." if not detect else "H2 is rejected at the 5% level."}</p>
{_ttable(num, "Confirmatory test of H2: listed competitors, CAR " + t("primary"), ["Quantity", "Value"], inf_rows, "Minimum detectable effect: two-sided 5% test, from the cluster-robust standard error implied by the interval.")}
<p><strong>Precision.</strong> {f"With a cluster-robust standard error of {pct(pw['se'], 2, False)}, an average effect would need to be about {pct(pw['mde80'], 1, False)} to be detected with 80% probability; the probability of detecting a true 1% effect is {pw['power'][0.01]:.2f}. The 90% interval ({_ci(*pw['ci90'])}) would support an equivalence claim only for a margin of about ±{pct(max(abs(pw['ci90'][0]), abs(pw['ci90'][1])), 1, False)}, which is not economically negligible for a two-day return. The data therefore do not show that rivals are unaffected." if pw else ""}</p>
{_ttable(num, "How the rival average depends on weighting", ["Weighting", "Estimate", "Note"], wt_rows, "Descriptive, added after the audit; not new tests.") if wt_rows else ""}
<p>{f"The sign of the average depends on weighting: equal weight per reaction gives {pct(w['observation_weighted'], 2)}, equal weight per firm gives {pct(w['firm_balanced'], 2)}, because {e(firms[-1]['firm'])}'s {firms[-1]['n']} reactions average {pct(firms[-1]['mean'], 2)}." if sign_flips and firms else ""} With {f['n_rival_firms']} firms, asymptotic inference clustered by firm is not reliable, so firm-level dependence is examined by leaving each firm out (R8) rather than by clustering on firms.</p></section>

<section id="s7"><h2>7. Robustness and sensitivity</h2>
<p>{"None of the" if f["n_robust_sig"] == 0 else str(f["n_robust_sig"]) + " of the"} {len(robust)} prespecified checks {"detects" if f["n_robust_sig"] == 0 else "detect"} a significant average at the 5% level. Non-rejection is stable; the estimate is not: across checks the average ranges from {pct(rob_lo, 2)} ({e(_plain_name(f['rob_min_name']))}) to {pct(rob_hi, 2)} ({e(_plain_name(f['rob_max_name']))}).{" Leaving one firm out changes the sign." if r8_flip else ""}</p>
{_figure(num, "forest", "Listed competitors: main test and prespecified checks", fig_forest(forest), "Dots: average two-day abnormal return; lines: 95% intervals. Shaded: the confirmatory test.")}
{_ttable(num, "Prespecified robustness checks", ["Check", "Average", "95% interval", "p", "Reactions", "Clusters"], rob_rows)}
<p><strong>Placebo.</strong> R9 repeats the calculation on {pl.get("draws")} sets of random ordinary trading days. The real result sits at the {ordinal(pl["actual_percentile"])} percentile (two-sided share {pl["two_sided_share"]:.3f}). Because R9 draws a separate date for each reaction, it ignores that rivals hit by one failure move on the same day, so its spread is too narrow; it is a benchmark, not an exact permutation test, and the percentile is not a probability that the effect is real.{f" An exploratory version with one shared date per cluster (R9b, {r9b['draws']} draws) places the real result at the {ordinal(r9b['actual_percentile'])} percentile (two-sided share {r9b['two_sided_share']:.3f})." if r9b else " A corrected version with one shared date per cluster (R9b) is specified as exploratory and is run by step 09."}</p>
{_figure(num, "placebo", "Real result against random ordinary days (R9)", fig_placebo(pl), f"Histogram of {pl.get('draws')} placebo averages (fixed seed). Red: averages at least as far out as the real result. Black line: the real failures.")}
</section>

<section id="s8"><h2>8. Confounding news</h2>
<p>An event study attributes every unusual return in the window to the event. If a firm announces something else on the same days, its reaction mixes the two. The news around the largest rival reactions was therefore checked against public sources. Flagged reactions stay in the confirmatory test, because the plan does not allow removing events after results are seen.</p>
{_ttable(num, "Rival reactions with other news in the window", ["Firm", "Failure", "CAR", "Verdict", "News"], flag_rows) if flag_rows else ""}
<p>The exploratory specifications below drop the flagged reactions. Dropping the {len(e1.get('dropped') or []) if e1 else 0} contract-news days changes the average from {pct(p['mean_car'], 2)} to {pct(e1['mean_car'], 2) if e1 else 'n/a'}{f", but the median moves only from {pct(w['median'], 2)} to {pct(w_e1['median'], 2)}: the change comes from removing {nw(n_e1)} large {e1_sign + " " if e1_sign else ""}move{"s" if n_e1 != 1 else ""}, not from a shift in the typical reaction" if w and w_e1 else ""}. The standardized test barely moves (p = {pval(e1['p']) if e1 else 'n/a'}), because it gives less weight to the volatile stocks behind those moves. The exploratory estimates are not more correct than the prespecified one: the choice of what to drop was made after seeing the data.</p>
{_ttable(num, "Confounding-news sensitivity (exploratory)", ["Specification", "Average", "95% interval", "p", "Median", "Reactions", "Clusters"], conf_rows)}
{_figure(num, "conf", "Confounding-news sensitivity", fig_forest(conf_forest), "Shaded: the confirmatory test. Hollow: exploratory specifications that drop flagged reactions.")}
</section>

<section id="s9"><h2>9. Discussion</h2>
<p>The evidence supports two statements. First, {"listed makers lose substantial value when their rocket fails" if all_fell else "maker reactions vary"}, in a small set of cases. Second, the average reaction of listed rivals cannot be distinguished from zero in this sample.</p>
<p>Several mechanisms are consistent with a small net rival reaction: contagion and competitive gain may both be present and offset each other; customers may be unable to switch quickly because contracts and satellites are tied to particular rockets; or investors may treat failures mainly as news about the failed firm. None of these mechanisms is identified here. Distinguishing them would require customer-level data on contract moves, launch backlogs, or a much larger sample of listed rivals. The results also say nothing about private, state-owned or diversified aerospace firms.</p></section>

<section id="s10"><h2>10. Limitations</h2>
<ul>
<li><strong>Few listed firms.</strong> {f['n_rival_firms']} rival firms and {f['n_clusters']} independent events{f"; {e(f['top_firm'])} appears in all of them" if top_all else ""}. Repeated exposure of the same stock means clustering by event captures only part of the dependence.</li>
<li><strong>Power.</strong> Average effects of about {pct(pw.get('mde80', 0), 1, False)} could go undetected; no equivalence claim is possible.</li>
<li><strong>Weighting and outliers.</strong> {"The sign of the estimate depends on weighting" if sign_flips else "The estimate is sensitive to weighting"}{f" and on {nw(n_e1)} large reaction{'s' if n_e1 != 1 else ''} with contract news" if n_e1 else ""}.</li>
<li><strong>Two estimands.</strong> The interval (equal-weighted mean) and the test (standardized mean) concern different quantities and can disagree.</li>
<li><strong>Timing.</strong> A few failures are dated by later company statements{f"; {nw(n_low)} of these {'is' if n_low == 1 else 'are'} uncertain" if n_low else ""}. R5 checks cover them.</li>
<li><strong>Model dependence.</strong> A one-factor market model with a home index; sector-wide moves on event days are not absorbed{f" ({nw(n_sector)} flagged case{'s' if n_sector != 1 else ''})" if n_sector else ""}.</li>
<li><strong>Survivorship.</strong> Listed launch firms that later delisted (Orbital Sciences/Orbital ATK, Astra, Virgin Orbit) are missing because the free price source does not carry them.</li>
<li><strong>External validity.</strong> The population is historically eligible, publicly traded launch-service competitors with comparable commercial exposure, not the launch industry.</li>
<li><strong>Data quality.</strong> Yahoo adjusted prices and GCAT records are good but not audited sources; price-quality issues are logged in the pipeline.</li>
<li><strong>Prespecification.</strong> The plan was committed to git before results but not filed with an independent registry; git timestamps are set by the author.</li>
</ul></section>

<section id="s11"><h2>11. Conclusion</h2>
<p>{"When an orbital rocket fails, its listed maker loses a large share of its value within two days in every case observed." if all_fell else "Maker reactions vary across the few listed cases."} For listed competitors, the average two-day reaction is {pct(p['mean_car'], 2)}, with an interval from {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}. The data do not establish contagion or competitive gains, and they do not rule out either at magnitudes of a few percent. The study is useful as a transparent, reproducible baseline: every number can be recomputed from the published data, and adding more listed firms, including delisted ones and SpaceX as its price history grows, would sharpen the answer without changing the prespecified test.</p></section>

<section class="refs-sec"><h2>References</h2><ol class="refs">
<li id="r1">Abramov, D. and Kiang, C. (2015). Effect of space launch delays and failures on stock market returns of commercial payload operators. International Astronautical Congress, IAC-15,E6,1,1,x29453.</li>
<li id="r2">Blose, L. E., Bornkamp, R., Brier, M., Brown, K. and Frederick, J. (1996). Catastrophic events, contagion, and stock market efficiency: the case of the space shuttle Challenger. <em>Review of Financial Economics</em> 5(2), 117-129.</li>
<li id="r3">Boehmer, E., Musumeci, J. and Poulsen, A. B. (1991). Event-study methodology under conditions of event-induced variance. <em>Journal of Financial Economics</em> 30(2), 253-272.</li>
<li id="r4">Bosch, J.-C., Eckard, E. W. and Singal, V. (1998). The competitive impact of air crashes: stock market evidence. <em>Journal of Law and Economics</em> 41(2), 503-519.</li>
<li id="r5">Brown, S. J. and Warner, J. B. (1985). Using daily stock returns: the case of event studies. <em>Journal of Financial Economics</em> 14(1), 3-31.</li>
<li id="r6">Campbell, J. Y., Lo, A. W. and MacKinlay, A. C. (1997). <em>The Econometrics of Financial Markets</em>. Princeton University Press.</li>
<li id="r7">Corrado, C. J. (1989). A nonparametric test for abnormal security-price performance in event studies. <em>Journal of Financial Economics</em> 23(2), 385-395.</li>
<li id="r8">Do, H. X., Nguyen, N. H., Nguyen, Q. M. P. and Truong, C. (2023). Aerospace competition, investor attention, and stock return comovement. <em>Journal of Economic Behavior &amp; Organization</em> 215, 40-59.</li>
<li id="r9">Kaplanski, G. and Levy, H. (2010). Sentiment and stock prices: the case of aviation disasters. <em>Journal of Financial Economics</em> 95(2), 174-201.</li>
<li id="r10">Kolari, J. W. and Pynnönen, S. (2010). Event study testing with cross-sectional correlation of abnormal returns. <em>Review of Financial Studies</em> 23(11), 3996-4025.</li>
<li id="r11">Lang, L. H. P. and Stulz, R. M. (1992). Contagion and competitive intra-industry effects of bankruptcy announcements. <em>Journal of Financial Economics</em> 32(1), 45-60.</li>
<li id="r12">MacKinlay, A. C. (1997). Event studies in economics and finance. <em>Journal of Economic Literature</em> 35(1), 13-39.</li>
<li id="r13">Maloney, M. T. and Mulherin, J. H. (2003). The complexity of price discovery in an efficient market: the stock market reaction to the Challenger crash. <em>Journal of Corporate Finance</em> 9(4), 453-479.</li>
<li id="r14">McDowell, J. C. GCAT: General Catalog of Artificial Space Objects. planet4589.org/space/gcat.</li>
</ol></section>

<section id="apx"><h2>Appendix A. Rival event list</h2>
{_ttable(num, "All rival reactions, CAR " + t("primary"), ["Failure", "Rocket", "T0", "Ticker", "Cluster", "Model", "Timing", "Flag", "CAR", "SD"], ev_rows, "Model: MM market model, MA market-adjusted fallback. SD: prediction-error standard deviation of the CAR.", "small")}
</section>
<section><h2>Appendix B. Firm mapping and rival criteria</h2>
<p>Rivals are classified point in time from the hand-built firm map (<code>data/manual/firm_map.csv</code>) and the size-and-market table (<code>data/manual/vehicle_segments.csv</code>): listing dates, ownership, exposure and sources are recorded per row. Tier 1 requires the same size class and customer market, launch as a pure-play or major business, and a flight in the prior 730 days. Diversified aerospace groups are classified as minor exposure and enter only descriptive tiers.</p></section>
<section><h2>Appendix C. Additional exploratory results</h2>
{_ttable(num, "Exploratory comparisons (Holm-adjusted p-values)", ["Comparison", "Estimate", "p", "p (Holm)"], expl_rows) if expl_rows else "<p>None.</p>"}
</section>
<section><h2>Appendix D. Statistical verification</h2>
<p>{f"An independent script (<code>audit/verify_published.py</code>) recomputes the published statistics from the published derived data without importing the pipeline; {verif[0]} of {verif[1]} quantities reproduce within tolerance (1e-9 for estimates and intervals, 1e-8 for t and p)." if verif else "An independent script (<code>audit/verify_published.py</code>) recomputes every published statistic from the published derived data without importing the pipeline."} The CARs themselves need licensed prices and are reproduced by re-running the pipeline.</p></section>
<section><h2>Appendix E. Exclusions</h2>
{_ttable(num, "Failures not in the study, by reason", ["Reason", "Failures"], why_rows, "A failure can have more than one reason, so the counts can add up to more than the number of excluded failures.") if why_rows else ""}
{_ttable(num, "Firm-events dropped at the price-coverage step", ["Reason", "Firm-events"], drop_rows) if drop_rows else ""}
</section>
<section><h2>Appendix F. Reproduction guide</h2>
<ol>
<li>Install Python 3.11+ and <code>pip install -r requirements.txt</code>.</li>
<li><code>python pipeline/01_ingest_launches.py</code> downloads GCAT and classifies launches; <code>02_map_firms.py</code> applies the firm map.</li>
<li><code>03_pull_prices.py</code> downloads prices (Yahoo Finance; not redistributed); <code>04_check_coverage.py</code> writes the feasibility gate.</li>
<li><code>05_event_study.py</code> runs the prespecified analysis; <code>06</code> and <code>09</code> run the exploratory checks.</li>
<li><code>07_export_site_data.py</code> exports derived statistics; <code>08_build_html.py</code> builds the site and this paper; <code>python audit/verify_published.py</code> re-checks every statistic.</li>
<li><code>python -m pytest tests</code> runs the test suite.</li>
</ol></section>

<section class="screen-only"><h2>Plain-language FAQ</h2>
<dl class="faq">
<dt>What is an abnormal return?</dt><dd>The part of a stock's move the market cannot explain: the actual return minus what the market model predicted for that day.</dd>
<dt>Does "not detectable" mean competitors are unaffected?</dt><dd>No. It means the average is too small, relative to the noise in this sample, to tell apart from zero. Effects of a few percent either way remain possible.</dd>
<dt>Why are the average and the test sometimes different?</dt><dd>The test weights calm stocks more than volatile ones; the simple average weights every reaction equally.</dd>
<dt>Can I trade on this?</dt><dd>No. This is research on past reactions with a small sample, not investment advice.</dd>
</dl></section>

<section><h2>Where to find the charts, data and code</h2>
{_table(["Resource", "What it is"], [[f'<a href="{e(h)}">{e(l)}</a>', e(wh)] for l, h, wh in links]
        + ([[f'<a class="screen-only" href="{e(pdf_row[1])}">{e(pdf_row[0])}</a>', f'<span class="screen-only">{e(pdf_row[2])}</span>']] if pdf_row else []))}</section>

<p class="signoff">{e(meta.get("author", "Nahian Ibnat"))}, {e(updated)}. Cite as: Ibnat, N. ({e(year)}). <em>Rocket Launch Failures and Equity-Market Spillovers: Evidence from Publicly Listed Launch Providers.</em> T-Minus Markets working paper.{(" " + e(meta["live_url"]) + "case-study.html") if meta.get("live_url") else ""} Research, not investment advice.{' <a href="' + e(meta["portfolio_url"]) + '">Portfolio</a>' if meta.get("portfolio_url") else ""}{' · <a href="' + e(meta["linkedin_url"]) + '">LinkedIn</a>' if meta.get("linkedin_url") else ""}</p>
</main>"""
    desc = (f"Working paper: {f['n_failures']} orbital launch failures, {span}. Listed makers lose {pct(f['case_hi'])} to {pct(f['case_lo'])} in two days; "
            f"listed rivals {pct(p['mean_car'], 2)} (95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}), not detectable with {f['n_clusters']} independent events.")
    url = (meta["live_url"].rstrip("/") + "/case-study.html") if meta.get("live_url") else None
    img = (meta["live_url"].rstrip("/") + "/og.png") if meta.get("live_url") else None
    return landing._shell("Rocket Launch Failures and Equity-Market Spillovers (T-Minus Markets working paper)", desc, url, body, css, url, img)
