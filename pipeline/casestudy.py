"""Long-form paper (paper.html): the full write-up of the project, built from site/data/*.json.

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
INK, MUTED, RULE, SIGNAL, GAIN, DEEP = "#0F172A", "#475569", "#D9DEE7", "#E8604C", "#14A38B", "#EEF1F5"


# ----------------------------------------------------------------------------- small SVG helpers
def _svg(w, h, label, inner):
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{e(label)}" '
            f'font-family="DM Mono, ui-monospace, monospace" font-size="11" fill="{INK}"><title>{e(label)}</title>{inner}</svg>')


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
              f'fill="{col if kind != "explore" else "#FFFFFF"}" stroke="{col}" stroke-width="1.4"/>')
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
    return (f'<div class="table-wrap" tabindex="0" role="region" aria-label="Table (scrolls sideways on small screens)"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head)
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
                s += f'<text x="{x + cw / 2:.1f}" y="{y + rh / 2 + 4}" text-anchor="middle" font-size="10" fill="#FFFFFF">{n}</text>'
    for i, f in enumerate(firms):
        s += f'<text x="{m["l"] - 8}" y="{m["t"] + i * rh + rh / 2 + 4}" text-anchor="end" font-size="11">{e(f)}</text>'
    return _svg(W, H, "Which rival firm is present in each independent event, in date order.", s)


def sample_graph(sample, f, p):
    """Nodes and edges of the sample diagram. Units change along the way (launches -> failures -> stock
    reactions -> clusters), so edges carry labels and the layout branches instead of a shrinking funnel."""
    nodes = [
        ("att", "Launch attempts", sample.get("launch_attempts"), "launches", 0, 0),
        ("fail", "Failures", sample.get("failures") or f["n_failures"], "launches", 1, 0),
        ("study", "In the study", sample.get("failures_in_study"), "failures", 2, 0),
        ("maker", "Listed maker", f["n_cases"], "failures; case studies", 3, 0),
        ("rivf", "Listed rivals", f["n_rival_failures"], "failures", 2, 1),
        ("obs", "Rival reactions", p["n_firm_events"], "firm x failure", 3, 1),
        ("clu", "Independent events", f["n_clusters"], "clusters", 4, 1),
        ("firm", "Rival firms", f["n_rival_firms"], "firms", 4, 2),
    ]
    nodes = [n for n in nodes if n[2] is not None]
    have = {n[0] for n in nodes}
    src = "study" if "study" in have else "fail"
    edges = [(a, b, lab) for a, b, lab in [("att", "fail", "score < 0.75"), ("fail", "study", "listed maker or rival"),
             ("study", "maker", "maker listed"), ("study", "rivf", "rival listed"), ("fail", "maker", "maker listed"),
             ("fail", "rivf", "rival listed"), ("rivf", "obs", "one row per rival"), ("obs", "clu", "grouped by date"),
             ("obs", "firm", "unique firms")] if a in have and b in have and not (a == "fail" and b in ("maker", "rivf") and src == "study")]
    return nodes, edges


def fig_sample(nodes, edges):
    if not nodes:
        return ""
    W, H, bw, bh = 720, 250, 128, 58
    xs = lambda c: 8 + c * 146
    ys = lambda r: 12 + r * 80
    pos = {n[0]: (xs(n[4]), ys(n[5])) for n in nodes}
    s = f'<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>'
    for a, b, lab in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        if y1 == y2:
            ax, ay, bx, by = x1 + bw, y1 + bh / 2, x2, y2 + bh / 2
        elif x1 == x2:
            ax, ay, bx, by = x1 + bw / 2, y1 + bh, x2 + bw / 2, y2
        else:
            ax, ay, bx, by = x1 + bw / 2, y1 + bh, x2, y2 + bh / 2
        s += f'<path d="M{ax:.1f},{ay:.1f} L{bx:.1f},{by:.1f}" stroke="{INK}" fill="none" marker-end="url(#arr)"/>'
    for nid, lab, val, unit, c, r in nodes:
        x, y = pos[nid]
        s += f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{"#EEF1F5" if nid in ("maker", "clu") else "#FFFFFF"}" stroke="{INK}"/>'
        s += f'<text x="{x + 8}" y="{y + 22}" font-size="16" font-weight="700">{val:,}</text>'
        s += f'<text x="{x + 8}" y="{y + 37}" font-size="9.5">{e(lab)}</text><text x="{x + 8}" y="{y + 50}" font-size="8.5" fill="{MUTED}">unit: {e(unit)}</text>'
    return _svg(W, H, "Sample construction: launches, failures, rival reactions and independent events, with the unit of each box.", s)


def fig_weights(rows):
    """rows: (label, value, kind) dot chart."""
    rows = [r for r in rows if r[1] is not None]
    if not rows:
        return ""
    W, rh, m = 720, 26, dict(l=260, r=30, t=8, b=28)
    H = m["t"] + m["b"] + rh * len(rows)
    vals = [r[1] for r in rows] + [0]
    tk = _ticks(min(vals), max(vals), 6)
    x = _lin(tk[0], tk[-1], m["l"], W - m["r"])
    s = "".join(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{m["t"]}" y2="{H - m["b"]}" stroke="{RULE}"/>'
                f'<text x="{x(t):.1f}" y="{H - 10}" text-anchor="middle" fill="{MUTED}">{pct(t, 1)}</text>' for t in tk)
    s += f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{m["t"]}" y2="{H - m["b"]}" stroke="{INK}"/>'
    for i, (lab, v, kind) in enumerate(rows):
        cy = m["t"] + rh * i + rh / 2
        if kind == "primary":
            s += f'<rect x="0" y="{cy - rh / 2:.1f}" width="{W}" height="{rh}" fill="{DEEP}"/>'
        s += f'<text x="{m["l"] - 10}" y="{cy + 4:.1f}" text-anchor="end" font-size="10.5">{e(lab)}</text>'
        s += f'<line x1="{x(0):.1f}" x2="{x(v):.1f}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="{MUTED}"/>'
        s += f'<circle cx="{x(v):.1f}" cy="{cy:.1f}" r="4.5" fill="{INK}"/><text x="{x(v) + (8 if v >= 0 else -8):.1f}" y="{cy - 6:.1f}" font-size="10" text-anchor="{"start" if v >= 0 else "end"}">{pct(v, 2)}</text>'
    return _svg(W, H, "The rival average under different weightings.", s)


def fig_timing(tm):
    order = [("high", "Sourced statement, high confidence"), ("low", "Sourced statement, low confidence"),
             ("provisional", "GCAT launch time (unverified)")]
    groups = [("Rival reactions", tm["rival_reactions"]), ("Maker cases", tm["maker_cases"])]
    W, rh, m = 720, 34, dict(l=130, r=20, t=10, b=46)
    H = m["t"] + m["b"] + rh * len(groups)
    shade = {"high": INK, "low": MUTED, "provisional": "#FFFFFF"}
    s = ""
    for i, (lab, g) in enumerate(groups):
        y = m["t"] + i * rh; x0 = m["l"]
        s += f'<text x="{m["l"] - 10}" y="{y + rh / 2 + 4}" text-anchor="end" font-size="11">{e(lab)} (n = {g["n"]})</text>'
        for k, _ in order:
            n = g["counts"].get(k, 0)
            if not n:
                continue
            w = (W - m["l"] - m["r"]) * n / g["n"]
            s += f'<rect x="{x0:.1f}" y="{y + 6}" width="{w:.1f}" height="{rh - 12}" fill="{shade[k]}" stroke="{INK}"/>'
            if w > 26:
                s += f'<text x="{x0 + w / 2:.1f}" y="{y + rh / 2 + 4}" text-anchor="middle" font-size="10" fill="{"#FFFFFF" if k != "provisional" else INK}">{n}</text>'
            x0 += w
    lx = m["l"]
    for k, lab in order:
        s += f'<rect x="{lx}" y="{H - 30}" width="10" height="10" fill="{shade[k]}" stroke="{INK}"/><text x="{lx + 14}" y="{H - 21}" font-size="9.5">{e(lab)}</text>'
        lx += 14 + len(lab) * 5.6 + 18
    return _svg(W, H, "How the disclosure time of each event is sourced.", s)


# ----------------------------------------------------------------------------- page helpers
class _Num:
    def __init__(self):
        self.fig = 0; self.tab = 0; self.eq = 0; self.map = {}


def _figure(num, fid, title, svg, cap):
    if not svg:
        return ""
    num.fig += 1
    num.map[("fig", fid)] = num.fig
    return (f'<figure class="cs-fig" id="fig-{fid}" data-fig="{fid}"><figcaption class="cs-figtitle"><span>Figure {num.fig}.</span> {e(title)}</figcaption>'
            f'{svg}<figcaption class="cs-cap">{cap}</figcaption></figure>')


def _ttable(num, title, head, rows, note="", cls="", key=None):
    num.tab += 1
    key = key or f"t{num.tab}"
    num.map[("tab", key)] = num.tab
    return (f'<div class="cs-table" id="tab-{key}"><p class="tcap"><strong>Table {num.tab}.</strong> {e(title)}</p>' + _table(head, rows, cls)
            + (f'<p class="cs-cap">{note}</p>' if note else "") + "</div>")


def _eq(num, html_body, tex):
    num.eq += 1
    return (f'<div class="eq" id="eq-{num.eq}" data-tex="{e(tex)}" tabindex="0" role="group" aria-label="Equation {num.eq}">'
            f'<span class="eq-body">{html_body}</span><span class="eq-no">({num.eq})</span></div>')


def X(kind, key):
    """Placeholder for a link to a table or figure; replaced by "Table N" / "Figure N" once all are numbered."""
    return f"@@{kind}:{key}@@"


def resolve_xrefs(body: str, num) -> str:
    import re as _re

    def sub(m):
        kind, key = m.group(1), m.group(2)
        n = num.map.get((kind, key))
        if n is None:                              # the item was not drawn for this data; keep the sentence readable
            return "the table below" if kind == "tab" else "the figure below"
        word = "Table" if kind == "tab" else "Figure"
        return f'<a class="xref" href="#{kind if kind == "tab" else "fig"}-{key}">{word} {n}</a>'
    return _re.sub(r"@@(tab|fig):([\w-]+)@@", sub, body)


def sec(n, cap=True):
    return f'<a class="xref" href="#s{n}">{"Section" if cap else "section"} {n}</a>'


def apx(letter):
    return f'<a class="xref" href="#apx-{letter.lower()}">Appendix {letter}</a>'


def eqref(n):
    return f'<a class="xref" href="#eq-{n}">Equation {n}</a>'


# ----------------------------------------------------------------------------- references (APA 7)
# key: (names in a narrative citation, names in a parenthetical citation, year, full APA 7 entry as HTML).
# Every entry was checked against Crossref or the publisher page. Only entries cited in the text are listed.
REFS = {
    "abramov2015": ("Abramov and Kiang", "Abramov &amp; Kiang", "2015",
                    "Abramov, D., &amp; Kiang, C. (2015). <em>Effect of space launch delays and failures on stock market returns of commercial "
                    "payload operators</em> (Paper IAC-15,E6,1,1,x29453) [Conference paper]. 66th International Astronautical Congress, "
                    "Jerusalem, Israel. <a href=\"https://iafastro.directory/iac/archive/browse/IAC-15/E6/1/29453/\">https://iafastro.directory/iac/archive/browse/IAC-15/E6/1/29453/</a>"),
    "aharony1983": ("Aharony and Swary", "Aharony &amp; Swary", "1983",
                    "Aharony, J., &amp; Swary, I. (1983). Contagion effects of bank failures: Evidence from capital markets. "
                    "<em>Journal of Business, 56</em>(3), 305–322. DOI"),
    "blose1996": ("Blose et al.", "Blose et al.", "1996",
                  "Blose, L. E., Bornkamp, R., Brier, M., Brown, K., &amp; Frederick, J. (1996). Catastrophic events, contagion, and stock "
                  "market efficiency: The case of the space shuttle Challenger. <em>Review of Financial Economics, 5</em>(2), 117–129. DOI"),
    "boehmer1991": ("Boehmer et al.", "Boehmer et al.", "1991",
                    "Boehmer, E., Musumeci, J., &amp; Poulsen, A. B. (1991). Event-study methodology under conditions of event-induced "
                    "variance. <em>Journal of Financial Economics, 30</em>(2), 253–272. DOI"),
    "bosch1998": ("Bosch et al.", "Bosch et al.", "1998",
                  "Bosch, J.-C., Eckard, E. W., &amp; Singal, V. (1998). The competitive impact of air crashes: Stock market evidence. "
                  "<em>Journal of Law and Economics, 41</em>(2), 503–519. DOI"),
    "brown1985": ("Brown and Warner", "Brown &amp; Warner", "1985",
                  "Brown, S. J., &amp; Warner, J. B. (1985). Using daily stock returns: The case of event studies. "
                  "<em>Journal of Financial Economics, 14</em>(1), 3–31. DOI"),
    "cameron2008": ("Cameron et al.", "Cameron et al.", "2008",
                    "Cameron, A. C., Gelbach, J. B., &amp; Miller, D. L. (2008). Bootstrap-based improvements for inference with clustered "
                    "errors. <em>Review of Economics and Statistics, 90</em>(3), 414–427. DOI"),
    "campbell1997": ("Campbell et al.", "Campbell et al.", "1997",
                     "Campbell, J. Y., Lo, A. W., &amp; MacKinlay, A. C. (1997). <em>The econometrics of financial markets</em>. "
                     "Princeton University Press."),
    "chance1987": ("Chance and Ferris", "Chance &amp; Ferris", "1987",
                   "Chance, D. M., &amp; Ferris, S. P. (1987). The effect of aviation disasters on the air transport industry: A financial "
                   "market perspective. <em>Journal of Transport Economics and Policy, 21</em>(2), 151–165. DOI"),
    "corrado1989": ("Corrado", "Corrado", "1989",
                    "Corrado, C. J. (1989). A nonparametric test for abnormal security-price performance in event studies. "
                    "<em>Journal of Financial Economics, 23</em>(2), 385–395. DOI"),
    "cross2018": ("Cross and Vesely", "Cross &amp; Vesely", "2018",
                  "Cross, B., &amp; Vesely, W. (2018, September 16–21). <em>Synthesizing a new launch vehicle failure probability based on "
                  "historical flight data</em> [Conference presentation]. Probabilistic Safety Assessment and Management Conference "
                  "(PSAM 14), Los Angeles, CA, United States. <a href=\"https://ntrs.nasa.gov/citations/20180006947\">https://ntrs.nasa.gov/citations/20180006947</a>"),
    "dillow2015": ("Dillow", "Dillow", "2015",
                   "Dillow, C. (2015, July 23). What SpaceX’s launch failure means for the private space industry. <em>Fortune</em>. "
                   "<a href=\"https://fortune.com/2015/07/23/spacex-rocket-failure-industry/\">https://fortune.com/2015/07/23/spacex-rocket-failure-industry/</a>"),
    "do2023": ("Do et al.", "Do et al.", "2023",
               "Do, H. X., Nguyen, N. H., Nguyen, Q. M. P., &amp; Truong, C. (2023). Aerospace competition, investor attention, and stock "
               "return comovement. <em>Journal of Economic Behavior &amp; Organization, 215</em>, 40–59. DOI"),
    "euronews2026": ("“SpaceX Makes Its Nasdaq Debut”", "“SpaceX Makes Its Nasdaq Debut,”", "2026",
                     "SpaceX makes its Nasdaq debut after the largest public offering in history. (2026, June 12). <em>Euronews</em>. "
                     "<a href=\"https://www.euronews.com/business/2026/06/12/spacex-makes-its-nasdaq-debut-after-the-largest-public-offering-in-history\">"
                     "https://www.euronews.com/business/2026/06/12/spacex-makes-its-nasdaq-debut-after-the-largest-public-offering-in-history</a>"),
    "faa2021": ("Federal Aviation Administration", "Federal Aviation Administration", "2021",
                "Federal Aviation Administration. (2021). <em>Part 450 mishap plan: Reporting, response, and investigation requirements</em> "
                "(Advisory Circular 450.173-1). U.S. Department of Transportation. "
                "<a href=\"https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_450.173-1.pdf\">https://www.faa.gov/documentLibrary/media/Advisory_Circular/AC_450.173-1.pdf</a>"),
    "fama1969": ("Fama et al.", "Fama et al.", "1969",
                 "Fama, E. F., Fisher, L., Jensen, M. C., &amp; Roll, R. (1969). The adjustment of stock prices to new information. "
                 "<em>International Economic Review, 10</em>(1), 1–21. DOI"),
    "jarrell1985": ("Jarrell and Peltzman", "Jarrell &amp; Peltzman", "1985",
                    "Jarrell, G., &amp; Peltzman, S. (1985). The impact of product recalls on the wealth of sellers. "
                    "<em>Journal of Political Economy, 93</em>(3), 512–536. DOI"),
    "kaplanski2010": ("Kaplanski and Levy", "Kaplanski &amp; Levy", "2010",
                      "Kaplanski, G., &amp; Levy, H. (2010). Sentiment and stock prices: The case of aviation disasters. "
                      "<em>Journal of Financial Economics, 95</em>(2), 174–201. DOI"),
    "kolari2010": ("Kolari and Pynnönen", "Kolari &amp; Pynnönen", "2010",
                   "Kolari, J. W., &amp; Pynnönen, S. (2010). Event study testing with cross-sectional correlation of abnormal returns. "
                   "<em>Review of Financial Studies, 23</em>(11), 3996–4025. DOI"),
    "lang1992": ("Lang and Stulz", "Lang &amp; Stulz", "1992",
                 "Lang, L. H. P., &amp; Stulz, R. M. (1992). Contagion and competitive intra-industry effects of bankruptcy announcements. "
                 "<em>Journal of Financial Economics, 32</em>(1), 45–60. DOI"),
    "mackinlay1997": ("MacKinlay", "MacKinlay", "1997",
                      "MacKinlay, A. C. (1997). Event studies in economics and finance. <em>Journal of Economic Literature, 35</em>(1), 13–39."),
    "maloney2003": ("Maloney and Mulherin", "Maloney &amp; Mulherin", "2003",
                    "Maloney, M. T., &amp; Mulherin, J. H. (2003). The complexity of price discovery in an efficient market: The stock market "
                    "reaction to the Challenger crash. <em>Journal of Corporate Finance, 9</em>(4), 453–479. DOI"),
    "mcdowell": ("McDowell", "McDowell", "n.d.",
                 "McDowell, J. C. (n.d.). <em>GCAT: General catalog of artificial space objects</em> [Data set]. "
                 "<a href=\"https://planet4589.org/space/gcat/\">https://planet4589.org/space/gcat/</a>"),
    "webb2023": ("Webb", "Webb", "2023",
                 "Webb, M. D. (2023). Reworking wild bootstrap-based inference for clustered errors. "
                 "<em>Canadian Journal of Economics, 56</em>(3), 839–858. DOI"),
    "yahoo": ("Yahoo Finance", "Yahoo Finance", "n.d.",
              "Yahoo Finance. (n.d.). <em>Historical prices</em> [Data set]. <a href=\"https://finance.yahoo.com/\">https://finance.yahoo.com/</a>"),
}
DOIS = {"aharony1983": "10.1086/296203", "blose1996": "10.1016/S1058-3300(96)90010-5", "boehmer1991": "10.1016/0304-405X(91)90032-F",
        "bosch1998": "10.1086/467399", "brown1985": "10.1016/0304-405X(85)90042-X", "cameron2008": "10.1162/rest.90.3.414",
        "chance1987": "10.3828/jtep.1987.21.2.151", "corrado1989": "10.1016/0304-405X(89)90064-0", "do2023": "10.1016/j.jebo.2023.09.005",
        "fama1969": "10.2307/2525569", "jarrell1985": "10.1086/261313", "kaplanski2010": "10.1016/j.jfineco.2009.10.002",
        "kolari2010": "10.1093/rfs/hhq072", "lang1992": "10.1016/0304-405X(92)90024-R", "maloney2003": "10.1016/S0929-1199(02)00055-X",
        "webb2023": "10.1111/caje.12661"}


def _apa(key):
    entry = REFS[key][3]
    if key in DOIS:
        u = "https://doi.org/" + DOIS[key]
        entry = entry.replace("DOI", f'<a href="{u}">{u}</a>')
    return entry


class Cites:
    """In-text citations that link to their entry in the reference list; remembers which works were cited."""

    def __init__(self):
        self.used = set()

    def n(self, key):                               # narrative: Lang and Stulz (1992)
        self.used.add(key)
        names, _, year, _ = REFS[key]
        return f'<a class="cite" href="#ref-{key}">{names} ({year})</a>'

    def p(self, *keys, pre=""):                     # parenthetical: (Lang &amp; Stulz, 1992; MacKinlay, 1997)
        self.used.update(keys)
        parts = [f'<a class="cite" href="#ref-{k}">{REFS[k][1]} {REFS[k][2]}</a>' if REFS[k][1].rstrip("”").endswith(",") else
                 f'<a class="cite" href="#ref-{k}">{REFS[k][1]}, {REFS[k][2]}</a>'
                 for k in sorted(keys, key=lambda k: html.unescape(REFS[k][1]).strip("“”"))]
        return "(" + (pre + " " if pre else "") + "; ".join(parts) + ")"

    def reference_list(self):
        import re as _re
        keys = sorted(self.used, key=lambda k: _re.sub(r"<[^>]+>", "", html.unescape(REFS[k][3])).lower())
        return "".join(f'<p class="ref" id="ref-{k}">{_apa(k)}</p>' for k in keys)


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
    et = D.estimand_tests(fes, p) if riv else None
    tm = D.timing(fes)
    prov_share = tm["rival_reactions"]["shares"].get("provisional", 0.0)
    nodes, edges = sample_graph(sample, f, p)
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
        + (f"the maker's two-day cumulative abnormal return was between {pct(f['case_hi'])} and {pct(f['case_lo'])}, "
           f"each case with a 95% interval excluding zero. " if all_fell and all(c['car_primary_ci'][1] < 0 for c in cases)
           else f"two-day abnormal returns ranged from {pct(f['case_lo'])} to {pct(f['case_hi'])}. ")
        + f"Across {f['n_rival_failures']} failures with listed competitors ({p['n_firm_events']} stock reactions, {f['n_rival_firms']} firms, "
        f"{f['n_clusters']} independent events), the equal-weighted average two-day cumulative abnormal return is {pct(p['mean_car'], 2)} "
        f"(95% cluster-robust interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}"
        + (f"; cluster-robust p = {pval(et['A']['p'])}" if et else "")
        + f"); the prespecified standardized test (Boehmer-Musumeci-Poulsen with a Kolari-Pynnönen adjustment) gives p = {pval(p['p'])}. "
        + ("The evidence therefore establishes neither systematic contagion nor systematic competitive gains among these firms, "
           f"and it does not show the effect is negligible: average effects of about {pct(pw['mde80'], 1, False)} in either direction "
           f"would usually go undetected. " if not detect and pw else "")
        + (f"The sign of the estimate changes with how events and firms are weighted, and every independent event involves "
           f"{f['top_firm']}. " if sign_flips and top_all else "")
        + "The study is a small-sample study of listed firms, not an estimate for the launch industry as a whole.")

    inshort = [
        f"<strong>The rocket's maker:</strong> " + (f"large losses in each of {f['n_cases']} cases ({pct(f['case_hi'])} to {pct(f['case_lo'])} over two days)."
                                                     if all_fell else f"mixed reactions across {f['n_cases']} cases."),
        f"<strong>Listed competitors:</strong> {pct(p['mean_car'], 2)} on average (95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}"
        + (f", p = {pval(et['A']['p'])}" if et else "") + f"; prespecified standardized test p = {pval(p['p'])}): "
        + ("no detectable reaction." if not detect else "a detectable reaction."),
        (f"<strong>Uncertainty:</strong> effects of about {pct(pw['mde80'], 1, False)} either way could go undetected; " if pw else "<strong>Uncertainty:</strong> ")
        + ("the sign depends on weighting." if sign_flips else "see section 7."),
        "<strong>Status:</strong> paper for feedback; rules fixed in git before results, not independently registered.",
    ]

    # ---------------- tables
    funnel_rows = [("Orbital launch attempts", sample.get("launch_attempts")), ("Launch failures", sample.get("failures") or f["n_failures"]),
                   ("Failures in the study", sample.get("failures_in_study")),
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
                ["BMP-KP adjusted t / p (prespecified test; mean standardized CAR = 0)", f'<span class="num">{p["stat"]:.3f} / {pval(p["p"])}</span>'],
                ["Cluster-robust t / p for the mean CAR (matches the interval)", f'<span class="num">{et["A"]["t"]:.3f} / {pval(et["A"]["p"])}</span>' if et else "n/a"],
                [f"Wild cluster bootstrap p for the mean CAR (Webb weights, {et['A']['draws']:,} draws)" if et else "Wild cluster bootstrap p", f'<span class="num">{pval(et["A"]["p_wild"])}</span>' if et else "n/a"],
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
                  e(r["flag"]["verdict"].replace("_", " ")), e(r["flag"].get("reason", "")) + (f' <a href="{e(r["flag"]["source"])}">[source]</a>' if str(r["flag"].get("source") or "").startswith("http") else "")]
                 for r in sorted(flagged, key=lambda r: -abs(r["windows"]["primary"]["car"]))]
    expl_lab = {"H3a": "Competitors: first-flight failures minus other failures", "H3b": "Maker: failures minus successful launches",
                "H3c": "Competitors over one month (T0 to T+20)"}
    expl_rows = [[e(expl_lab.get(x["id"], x["label"])), f'<span class="num">{pct(x.get("estimate"), 2)}</span>',
                  f'<span class="num">{pval(x.get("p_raw"))}</span>', f'<span class="num">{pval(x.get("p_holm"))}</span>'] for x in expl]
    ev_rows = [[e(r["launch_tag"]), e(r["vehicle"]), e(r["day0"]), e(r["ticker"]), str(r["cluster"]),
                "MM" if r["model"] == "market_model" else "MA", e(r.get("disclosure_confidence") or ""), e((r.get("flag") or {}).get("verdict", "").replace("_", " ")),
                f'<span class="num">{pct(r["windows"]["primary"]["car"], 2)}</span>', f'<span class="num">{pct(r["windows"]["primary"]["var"] ** 0.5, 2, False)}</span>']
               for r in sorted(riv, key=lambda r: (r["day0"], r["ticker"]))]
    freeze_rows = []
    pf = root / "docs" / "ANALYSIS_PLAN.md"
    if pf.exists():
        txt = pf.read_text(encoding="utf-8")
        if "## Freeze record" in txt:
            blk = txt.split("## Freeze record", 1)[1].split("\n## ", 1)[0]
            for ln in blk.splitlines():
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if ln.startswith("|") and len(cells) == 3 and cells[1].startswith("`"):
                    freeze_rows.append([e(cells[0].replace("Plan v1.0 with the locked table", "Rules fixed").replace("plan v1.0 frozen", "rules frozen")),
                                        f"<code>{e(cells[1].strip('`'))}</code>", e(cells[2])])
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
             ("Interactive report", "site/index.html", "Five stages and four interactive tools")]
    if blob:
        links += [("Feasibility report", blob + "reports/04_feasibility_report.md", "Sample and minimum detectable effects, before results"),
                  ("Results report", blob + "reports/05_results.md", "All prespecified results"),
                  ("Confounding-news checks", blob + "docs/CONFOUNDING_NEWS.md", "News around the largest reactions, with sources"),
                  ("Independent audit", blob + "audit/AUDIT_REPORT.md", "Verification of every published statistic"),
                  ("Code and pipeline", meta["repo_url"], "Python pipeline, tests and reproduction guide")]
    pdf_row = ("Download PDF", pdf_name, "This paper as a typeset PDF (same text)") if pdf_name else None
    nav = " · ".join(f'<a href="{e(h)}">{e(l)}</a>' for l, h in
                     [("Article", "index.html"), ("Interactive report", "site/index.html")]
                     + ([("Code", meta["repo_url"])] if meta.get("repo_url") else []))
    nav += (f' <span class="screen-only">· <a href="{e(pdf_name)}" download>Download PDF</a></span>' if pdf_name else "")
    contents = ["Introduction", "Institutional background", "Related literature", "Data and sample construction", "Empirical methodology",
                "Main results", "Robustness and sensitivity", "Confounding corporate announcements", "Discussion", "Limitations", "Conclusion"]

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

    import sitechrome as SC
    plan_v = res.get("plan_version") or ""
    C = Cites()
    gap = st.get("cluster_gap", 5)
    min_obs = st.get("min_obs", 100)
    top = e(f["top_firm"]) if f.get("top_firm") else ""
    cases_sig = all_fell and all(c["car_primary_ci"][1] < 0 for c in cases)
    n_prov_r = tm["rival_reactions"]["counts"].get("provisional", 0)
    n_low_r = tm["rival_reactions"]["counts"].get("low", 0)
    n_prov_m = tm["maker_cases"]["counts"].get("provisional", 0)
    toc_items = ("".join(f'<li><a href="#s{i}">{i}. {e(c)}</a></li>' for i, c in enumerate(contents, 1))
                 + '<li><a href="#refs">References</a></li><li><a href="#apx">Appendices</a></li>')

    # ---------------- reusable sentences (kept outside the f-strings so the page builds on Python 3.11)
    maker_sentence = (f"In every one of the {f['n_cases']} listed cases the maker's shares fell over the two trading days after the failure became "
                      f"public, after allowing for the movement of the market, by between {pct(f['case_hi'])} and {pct(f['case_lo'])}"
                      + (", and in each case the 95% interval excludes zero." if cases_sig else ".")
                      if all_fell else f"The {f['n_cases']} listed cases do not move in the same direction, so they are reported one by one.")
    h2_sentence = ("H2 is therefore not rejected at the 5% level by any of these tests." if not detect and (not et or et["A"]["p"] >= 0.05)
                   else "The tests do not all agree; each is reported next to the quantity it measures.")
    precision = (f"How large would an effect have to be for this sample to find it? With a cluster-robust standard error of {pct(pw['se'], 2, False)}, "
                 f"an average effect would need to be about {pct(pw['mde80'], 1, False)} to be detected four times out of five (80% power), and "
                 f"about {pct(pw['mde90'], 1, False)} to be detected nine times out of ten. The chance of detecting a true average effect of 1% is only "
                 f"{pw['power'][0.01]:.2f}. This figure is called the minimum detectable effect: the smallest true effect that a test of this size would "
                 f"usually find. A two-day move of {pct(pw['mde80'], 1, False)} in a firm's value is large in economic terms, so the test can only rule out "
                 f"large effects. The 90% interval ({_ci(*pw['ci90'])}) could support a claim that the effect is negligible only if a two-day effect of "
                 f"about ±{pct(max(abs(pw['ci90'][0]), abs(pw['ci90'][1])), 1, False)} were accepted as negligible, which it is not. The data therefore "
                 "do not show that competitors are unaffected; they show that any average effect is too small, relative to the noise, to be measured "
                 "with this sample." if pw else "")
    offset = (f"The average is close to zero partly because firms with opposite reactions cancel each other out. {e(et['contrib'][-1]['firm'])}'s "
              f"{et['contrib'][-1]['n']} reactions add {pct(et['contrib'][-1]['contribution'], 2)} to the mean, while {e(et['contrib'][0]['firm'])}'s "
              f"{et['contrib'][0]['n']} reactions add {pct(et['contrib'][0]['contribution'], 2)} ({X('tab', 'contrib')}). "
              if et and len(et["contrib"]) > 1 else "")
    firm_view = (f"A firm-level view makes the same point. The mean of the {et['firm']['k']} firm means is {pct(et['firm']['mean'], 2)}, with a 95% "
                 f"interval of {_ci(*et['firm']['ci'], 1)}, but this interval rests on only {et['firm']['k'] - 1} degrees of freedom and is therefore "
                 f"very wide. " if et and et["firm"]["ci"][0] is not None else "")
    weights_sentence = (f"Weighting each firm equally instead of each reaction gives a different answer, and no weighting is better than the others on "
                        f"statistical grounds ({X('tab', 'wt')} and {X('fig', 'weights')}). The every-reaction average is the main estimate only "
                        "because it was chosen before the results were seen." if wt_rows else "")
    e1_sentence = (f"Dropping the {len(e1.get('dropped') or [])} reactions that coincide with contract news changes the average from "
                   f"{pct(p['mean_car'], 2)} to {pct(e1['mean_car'], 2)}"
                   + (f", but the median moves only from {pct(w['median'], 2)} to {pct(w_e1['median'], 2)}. The change therefore comes from "
                      f"removing {nw(n_e1)} large {e1_sign + ' ' if e1_sign else ''}move{'s' if n_e1 != 1 else ''}, not from a shift in the typical "
                      "reaction" if w and w_e1 else "")
                   + f". The standardized test hardly moves (p = {pval(e1['p'])}), because it already gives less weight to the volatile stocks behind "
                   "those moves." if e1 else "")
    flag_intro = (f"{X('tab', 'flag')} lists every competitor reaction with other company news in the window, the verdict, and the source of the news. "
                  if flag_rows else "No competitor reaction had other company news in the window. ")
    placebo_b = (f" A version designed after the results, with one shared random date for all reactions in a cluster (R9b, {r9b['draws']} draws), "
                 f"places the real result at the {ordinal(r9b['actual_percentile'])} percentile (two-sided share {r9b['two_sided_share']:.3f})."
                 if r9b else "")
    concentration = (f"{top} appears in every one of the {f['n_clusters']} independent events. " if top_all else "")
    verify_txt = (f"An independent script (<code>audit/verify_published.py</code>) recomputes the published statistics from the published derived data, "
                  f"without importing any of the project's own code. {verif[0]} of {verif[1]} quantities match within a tolerance of 1e-9 for "
                  "estimates and intervals and 1e-8 for test statistics and p-values." if verif else
                  "An independent script (<code>audit/verify_published.py</code>) recomputes every published statistic from the published derived "
                  "data, without importing any of the project's own code.")
    commit_txt = (f" The published statistics were exported from commit <code>{e(str(man['git']['commit'])[:7])}</code>"
                  + (" (with uncommitted changes in the working tree)" if man["git"].get("uncommitted_changes") else "") + "."
                  if (man.get("git") or {}).get("commit") else "")
    inshort_p = (("The rocket's maker lost a large share of its value in each of the " + str(f["n_cases"]) + f" listed cases ({pct(f['case_hi'])} to "
                  f"{pct(f['case_lo'])} over two days). " if all_fell else f"The rocket's maker reacted differently in the {f['n_cases']} listed cases. ")
                 + f"Listed competitors moved by {pct(p['mean_car'], 2)} on average (95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}"
                 + (f", p = {pval(et['A']['p'])}" if et else "") + f"; prespecified standardized test p = {pval(p['p'])}), "
                 + ("which cannot be told apart from zero. " if not detect else "which is different from zero. ")
                 + (f"Effects of about {pct(pw['mde80'], 1, False)} in either direction could go undetected" if pw else "")
                 + (", and the sign of the estimate depends on how events and firms are weighted. " if sign_flips else ". ")
                 + "The rules were fixed in the public repository before the results, but not filed with an independent registry.")

    lim_paras = [
        f"The first limitation is the small number of listed firms. Only {f['n_rival_firms']} listed firms qualify as competitors, and they "
        f"produce {f['n_clusters']} independent events{f', every one of which involves {top}' if top_all else ''}. Because the same shares appear "
        f"in many events, grouping reactions by event captures only part of the dependence between them, and with {f['n_rival_firms']} firms "
        "grouping by firm is not reliable either. The maker evidence is thinner still: "
        f"{f['n_cases']} cases from {n_case_firms} firm{'s' if n_case_firms != 1 else ''}, which are case studies rather than an average effect.",
        (f"The second limitation is statistical power. Average effects of about {pct(pw.get('mde80', 0), 1, False)} could go undetected, so the "
         "study cannot claim that the effect is zero or negligible. " if pw else "The second limitation is statistical power. ")
        + ("The sign of the estimate depends on how events and firms are weighted" if sign_flips else "The estimate is sensitive to the weighting")
        + (f", and on {nw(n_e1)} large reaction{'s' if n_e1 != 1 else ''} that coincide with contract news" if n_e1 else "")
        + ". The interval (for the equal-weighted mean) and the prespecified test (for the standardized mean) answer slightly different "
        "questions and can disagree.",
        f"The third limitation is timing. {pct(prov_share, 0, False)} of competitor reactions and {n_prov_m} of {tm['maker_cases']['n']} maker "
        "cases use GCAT launch times that were not checked separately against a company statement. These times are used only where day 0 "
        "would not change if the true disclosure came up to 10 minutes earlier or 180 minutes later. "
        + (f"{nw(n_low).capitalize()} failure{'s are' if n_low != 1 else ' is'} dated by a statement with low confidence, which checks R5a "
           "and R5b address. " if n_low else "")
        + "A clock or time-zone error larger than that band would move day 0.",
        "The fourth limitation is the model. A one-factor market model with a home-market index does not remove moves that affect the whole "
        "space sector on the event days"
        + (f" ({nw(n_sector)} flagged case{'s' if n_sector != 1 else ''})" if n_sector else "")
        + ". Firms that were listed but later delisted, such as Orbital Sciences (later Orbital ATK), Astra and Virgin Orbit, are missing from "
        "the main sample because the free price source does not carry them. Yahoo Finance prices and GCAT records are good sources but are "
        "not audited.",
        f"Finally, the results describe historically eligible, publicly traded launch firms with comparable commercial business, not the launch "
        f"industry as a whole, and they say nothing about private, state-owned or diversified aerospace companies. The rules were committed to "
        f"git before the results ({apx('G')}) but were not filed with an independent registry, and git timestamps are set by the author.",
    ]
    limitations = "".join(f"<p>{x}</p>" for x in lim_paras)

    est_eq = _eq(num, "<i>θ</i><sub>obs</sub> = (1/<i>N</i>) Σ<sub><i>i</i></sub> <i>CAR</i><sub><i>i</i></sub>, &nbsp; <i>θ</i><sub>event</sub> = (1/<i>G</i>) Σ<sub><i>g</i></sub> (1/<i>N</i><sub><i>g</i></sub>) Σ<sub><i>i</i>∈<i>g</i></sub> <i>CAR</i><sub><i>i</i></sub>, &nbsp; <i>θ</i><sub>prec</sub> = Σ<sub><i>i</i></sub> <i>CAR</i><sub><i>i</i></sub>/<i>s</i><sub><i>i</i></sub> / Σ<sub><i>i</i></sub> 1/<i>s</i><sub><i>i</i></sub>, &nbsp; <i>θ</i><sub>firm</sub> = (1/<i>K</i>) Σ<sub><i>k</i></sub> (1/<i>N</i><sub><i>k</i></sub>) Σ<sub><i>i</i>∈<i>k</i></sub> <i>CAR</i><sub><i>i</i></sub>",
                 r"\begin{gathered}\theta_{obs} = \frac{1}{N}\sum_i CAR_i,\qquad \theta_{event} = \frac{1}{G}\sum_g \frac{1}{N_g}\sum_{i\in g} CAR_i,\\ \theta_{prec} = \frac{\sum_i CAR_i/s_i}{\sum_i 1/s_i},\qquad \theta_{firm} = \frac{1}{K}\sum_k \frac{1}{N_k}\sum_{i\in k} CAR_i\end{gathered}")
    up = p["mean_car"] >= 0
    rival_econ = (f"In economic terms, the point estimate says that the average competitor's market value {'rose' if up else 'fell'} by about "
                  f"{pct(abs(p['mean_car']), 2, False)} more than the market predicted over the two days after a failure. For a "
                  f"competitor worth one billion dollars, this would be a {'gain' if up else 'loss'} of about {abs(p['mean_car']) * 1000:.1f} million "
                  f"dollars. The interval, however, runs from {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}"
                  + (", so a small loss through contagion and a small gain through competition are both consistent with the data."
                     if p["ci_low"] < 0 < p["ci_high"] else "."))
    maker_econ = (f"In economic terms, investors cut their estimate of the maker's market value by {pct(abs(f['case_hi']), 1, False)} to "
                  f"{pct(abs(f['case_lo']), 1, False)} within two days. Losses of this size are consistent with investors expecting costs well "
                  "beyond the lost rocket, such as delayed launches, lost contracts and a weaker reputation for reliability. " if all_fell else "")
    sections = f"""<section class="abstract-sec"><h2>Abstract</h2><p>{e(abstract)}</p></section>
<div class="kw"><p class="keywords"><em>Keywords:</em> event study; industry spillovers; contagion; competitive effects; launch failures</p>
<p class="keywords"><em>JEL:</em> G14, L13</p></div>

<aside class="inshort screen-only"><h2>In short</h2><p>{inshort_p}</p></aside>

<section id="s1"><h2>1. Introduction</h2>
<p>When a rocket fails, the company that built it loses the rocket, often a customer's satellite, and usually several months of flights while engineers find the cause. In the United States, for example, a licensed launch operator must investigate the root cause of any mishap, report the results to the regulator, and put in place measures that stop it from happening again {C.p("faa2021")}. The effect of the failure on the maker's competitors is much less clear, and it is the main question of this paper.</p>
<p>Economists describe two opposite ways in which bad news at one firm can move the share prices of other firms in the same industry {C.p("lang1992")}. The first is contagion: investors read the failure as news about the whole industry, for example that rockets are riskier than they thought or that rules will become stricter, and they lower their estimate of the value of every firm in it. The second is the competitive effect: investors expect customers to move their satellites to providers whose rockets still work, so the competitors gain. The two channels push share prices in opposite directions, so theory alone cannot say which one is larger. Only data can.</p>
<p>The question matters more now than it did a decade ago, because launch companies have become a larger part of public stock markets. In June 2026 SpaceX began trading on the Nasdaq after raising about $75 billion, the largest initial public offering on record {C.p("euronews2026")}. When more launch firms are listed, more investors hold shares whose value depends on how the market prices launch risk, both the risk of a firm's own rockets and the risk of its competitors' rockets. Whether a failure at one provider moves the shares of the others matters for how investors diversify, for how they value new listings, and for how firms and regulators think about the industry's exposure to a single accident.</p>
<p>Earlier work has answered the same question for other industries. Studies of bankruptcies {C.p("lang1992")}, bank failures {C.p("aharony1983")}, product recalls {C.p("jarrell1985")} and air crashes {C.p("chance1987", "bosch1998")} show that bad news at one firm often moves the share prices of its competitors, and that the direction depends on the industry. For spaceflight, the evidence comes mainly from a single event, the loss of the space shuttle Challenger in 1986 {C.p("blose1996", "maloney2003")}, and from studies of satellite operators, who are the launch firms' customers rather than their competitors {C.p("abramov2015")}. To the author's knowledge, no study has measured how listed launch providers react to the failures of their competitors across many events.</p>
<p>This paper fills that gap with an event study of orbital launch failures from {e(span)}. An event study measures how much a share price moves on and just after a specific piece of news, beyond what the general movement of the market on those days would predict {C.p("mackinlay1997")}. Launch failures suit the method well. They happen at a known time, they are usually broadcast live, and they are not caused by the decisions of the competitors whose shares are studied. The paper makes three contributions. First, it builds a hand-checked list of which listed firms were real competitors of the failed rocket on the day of each failure, using the GCAT launch catalogue {C.p("mcdowell")}. Second, it reports the reaction of the failed rocket's maker as a set of case studies and tests one confirmatory hypothesis for competitors, called H2: the average two-day abnormal return of listed competitors is zero. All rules for this test were fixed in the project's public repository before any result was computed ({apx("G")}). Third, it reports the uncertainty in full: how small an effect the sample could detect, how the estimate changes when events and firms are weighted differently, and which reactions coincide with other company news.</p>
<p>The answer is limited by the sample. Only {f['n_rival_firms']} listed launch firms qualify as direct competitors at the time of a failure, so the study observes {f['n_clusters']} independent competitor events{f", every one of which involves {top}" if top_all else ""}. {"The average reaction of competitors is not distinguishable from zero, but the interval around it is wide enough to contain losses and gains that would matter to investors." if not detect else "The average reaction of competitors is distinguishable from zero."} The contribution is therefore a carefully documented and reproducible estimate with its uncertainty stated in full, not a general claim about the launch industry.</p>
<p>The paper is organized as follows. {sec(2)} describes the launch industry and {sec(3, False)} reviews earlier studies. {sec(4)} and {sec(5, False)} describe the data and the method. {sec(6)}, {sec(7, False)} and {sec(8, False)} report the main results, the robustness checks and the role of other company news. {sec(9)} discusses the findings, {sec(10, False)} sets out the limitations and {sec(11, False)} concludes.</p></section>

<section id="s2"><h2>2. Institutional background</h2>
<p>An orbital launch places a satellite or another payload into orbit around the Earth. A small number of providers sell these launches, and many of them are government agencies, state-owned companies or privately held firms. As a result, only a few launch providers have shares that trade on a stock exchange, and these are the only firms whose market value can be observed every day. Rockets and satellites need long preparation before a launch, so a provider cannot easily turn spare rockets into launches in the near term, and satellite operators must choose from a limited number of providers and rockets {C.p("dillow2015")}. This matters for the competitive effect: even if customers want to leave a provider after a failure, the competitors can take on only a limited amount of new business in the short run.</p>
<p>Launching is risky, and new rockets are riskier than mature ones. A study of launch records from 1980 to 2017 by NASA engineers found that new launch vehicles have had much higher failure probabilities in their early flights than engineering risk models predicted {C.p("cross2018")}. After a failure, the rocket normally stops flying while the cause is found and fixed; in the United States this investigation is a legal requirement for licensed launches {C.p("faa2021")}. For the maker, a failure therefore means the loss of the rocket, possible penalties or free replacement flights for the customer, the delay of its next launches, and damage to its reputation for reliability.</p>
<p>Few launch companies have been publicly traded with launch as a major part of their business. Large aerospace groups that build rockets also make aircraft, defence systems or satellites, so a launch failure is a small part of their value and their share price says little about their launch business. The study therefore counts a firm as a direct competitor only when launch is its only business (a pure-play firm) or a major one ({apx("B")}). The listed launch-focused firms in the sample became public mostly in the last decade, so most of the competitor evidence comes from recent years. SpaceX listed on the Nasdaq in June 2026 {C.p("euronews2026")} and had too little trading history to enter the sample, because the model in {sec(5, False)} needs at least {min_obs} days of returns before an event.</p>
<p>Most orbital launches are shown live online, so a failure usually becomes public at the moment it happens. In some cases a launch first appears to succeed, and the company confirms only later that the satellite did not reach the right orbit. In those cases the event date is set by the first public statement from the company, and the paper records how confident it is about that time ({sec(4, False)}).</p></section>

<section id="s3"><h2>3. Related literature</h2>
<h3>3.1 Event studies</h3>
<p>The event study is the standard tool for measuring how a piece of news changes the value of a firm. The method goes back to {C.n("fama1969")}, who studied how share prices adjust to stock splits. Its logic is simple. If investors use public information quickly, the effect of news on a firm's value shows up in its share price within a short time. The researcher predicts what the firm's return would have been without the news, using the firm's normal relation to the market, and calls the difference between the actual and the predicted return the abnormal return {C.p("mackinlay1997")}. {C.n("brown1985")} show that this approach works well with daily returns and simple models.</p>
<p>Two statistical problems matter for this paper. First, a dramatic event can make returns more volatile than usual, and ordinary tests then find an effect too often even when there is none. {C.n("boehmer1991")} propose a standardized test that allows for this extra volatility. Second, when one event hits several firms on the same day, their abnormal returns are correlated, which also makes ordinary tests too confident. {C.n("kolari2010")} measure the size of this bias and propose the correction used here. {C.n("corrado1989")} offers a test based on ranks rather than averages, which is less sensitive to a few very large returns. Finally, when observations fall into a small number of groups, standard errors that allow for correlation within groups can still be unreliable, and {C.n("cameron2008")} and {C.n("webb2023")} propose bootstrap methods for this case.</p>
<h3>3.2 Contagion and competitive effects</h3>
<p>A large literature asks how news at one firm moves its competitors. {C.n("lang1992")} separate the two channels described in the introduction. They find that bankruptcy announcements lower the value of a portfolio of competitors by about 1% on average, so contagion dominates on average, but that competitors gain in highly concentrated industries with low debt, where the bankrupt firm's customers can move to its rivals. {C.n("aharony1983")} study the failures of large US banks and find that the effect on other banks depends on whether the cause of the failure is specific to the failed bank or could be shared by others. {C.n("jarrell1985")} show that product recalls in the drug and car industries cost the recalling firm more than the direct cost of the recall, and that part of the loss spreads to its competitors.</p>
<h3>3.3 Disasters and investor sentiment</h3>
<p>Accidents are a closer comparison to launch failures, because they are sudden, public and physical. {C.n("chance1987")} study the share prices of airlines after fatal crashes. {C.n("bosch1998")} ask whether rival airlines lose because travellers become afraid of flying in general, or gain because travellers switch to other carriers. {C.n("kaplanski2010")} show that aviation disasters are followed by losses across the whole stock market that are far larger than the economic damage of the crash and that reverse within a few days. This points to investor sentiment, meaning a change in mood rather than in information about firm values, as a possible driver of short-run reactions to disasters.</p>
<h3>3.4 Spaceflight and launch markets</h3>
<p>For spaceflight, most of the evidence comes from one event, the loss of the space shuttle Challenger in January 1986. {C.n("blose1996")} study how the shares of the shuttle's contractors reacted and how quickly the market absorbed the news. {C.n("maloney2003")} show that the contractors' shares fell together on the day of the disaster, and that within the same day the market singled out Morton Thiokol, the firm whose booster seal was later found to have failed, months before the official inquiry reached that conclusion. {C.n("abramov2015")} study launch delays and failures from the point of view of satellite operators, the launch firms' customers. {C.n("do2023")} find that US satellite launch days draw investors' attention away from firm-specific news, so that share prices move more closely with the market on those days.</p>
<h3>3.5 What this paper adds</h3>
<p>This paper differs from these studies in three ways. It studies the failed provider's listed competitors, not its contractors or its customers. It uses many failures rather than one, so that an average reaction can be estimated, even though the number of listed competitors is small. And it applies the corrections for extra volatility and same-day correlation discussed above, together with a full report of the study's statistical power, so that a result of "no detectable effect" can be read correctly: as a statement about what the sample can and cannot detect, not as proof that there is no effect.</p></section>

<section id="s4"><h2>4. Data and sample construction</h2>
<h3>4.1 Launch records</h3>
<p>The list of launches comes from GCAT, the General Catalog of Artificial Space Objects maintained by the astronomer Jonathan McDowell {C.p("mcdowell")}. GCAT records orbital launch attempts with their date, time, rocket, launch site and outcome. Each launch has a success score between 0 and 1, where lower scores mean worse outcomes. This paper treats a launch as a failure when its score is below 0.75. Explosions on the launch pad before lift-off are recorded separately and are not part of the main sample. The sample covers {e(span)} and contains {f['n_failures']} failures.</p>
<h3>4.2 Firms and competitors</h3>
<p>Each failure is linked by hand to its maker, if the maker was a listed company on that date, and to any listed competitors. The link is made point in time, which means that it uses only what was true on the day of the failure: a firm that listed later, or that bought a launch business later, is not counted. A firm is a Tier 1 competitor when four conditions hold on the date of the failure. Its shares are listed on a stock exchange; launch is its only business or a major one; it sells a rocket of the same size class to the same customer market as the failed rocket; and it has flown that rocket in the previous 730 days, which is about two years. A small number of further competitors (Tier 2) are added case by case, each with a documented source. Every row of the firm map used in the test is checked against company filings or exchange notices ({apx("B")}).</p>
<h3>4.3 Share prices</h3>
<p>Daily share prices, adjusted for dividends and stock splits, come from Yahoo Finance {C.p("yahoo")}. A daily return is the percentage change in this adjusted price from one trading day to the next. Each firm's benchmark is the main stock index of its home market, so that the model compares a firm with the market in which it trades. Prices from before a firm's real listing, for example the price of a shell company that it merged with in order to list, are dropped. Raw prices are used only on the author's computer and are not redistributed; the paper and the website publish only derived statistics.</p>
<h3>4.4 Event dates and independent events</h3>
<p>Day 0, written T0, is the first trading session on the stock's own exchange that starts at or after the moment the failure became public. If a rocket fails after the exchange has closed, day 0 is the next trading day. Other days are counted in trading days around day 0: T−1 is the session before it and T+1 the session after it. When two failures less than {gap} trading days apart affect the same firm, their windows overlap and the reactions cannot be separated, so they are grouped into one cluster, which this paper calls an independent event. {X("fig", "sample")} shows how the sample narrows from all launch attempts to the competitor reactions used in the test.</p>
{_figure(num, "sample", "Sample construction", fig_sample(nodes, edges), f"Each box gives a count and its unit, and the unit changes along the way. Failures: GCAT success score below 0.75. In the study: the failure has a listed maker or a listed Tier 1-2 competitor (one failure has both). Competitor reactions: one per listed competitor per failure. Independent events: failures that share a firm within {gap} trading days are grouped. Source: GCAT (McDowell, n.d.) and the project pipeline.")}
<h3>4.5 Event timing verification</h3>
<p>Day 0 depends on when a failure became public relative to the close of the exchange, so the disclosure time of each event was checked. For each event the time is either a sourced company statement, recorded with high or low confidence, or the launch time recorded in GCAT. GCAT times are used only where day 0 would not change if the true disclosure came 10 minutes earlier or up to 180 minutes later; events that fail this check need a sourced time. {pct(prov_share, 0, False)} of competitor reactions ({n_prov_r} of {tm['rival_reactions']['n']}) and {n_prov_m} of {tm['maker_cases']['n']} maker cases rely on GCAT launch times that were not checked separately against a company statement, and {n_low_r} competitor reaction{"s" if n_low_r != 1 else ""} rely on a sourced time with low confidence. Checks R5a and R5b ({sec(7, False)}) test whether these choices matter. {X("tab", "tsrc")} and {X("fig", "timing")} give the breakdown.</p>
{_ttable(num, "Disclosure-time sources", ["Source of the disclosure time", "Competitor reactions", "Competitor failures", "Maker cases"],
         [[lab, str(tm["rival_reactions"]["counts"].get(k, 0)), str(tm["rival_failures"]["counts"].get(k, 0)), str(tm["maker_cases"]["counts"].get(k, 0))]
          for k, lab in (("high", "Company statement, high confidence"), ("low", "Company statement, low confidence"), ("provisional", "GCAT launch time (not separately verified)"))], key="tsrc")}
{_figure(num, "timing", "Event timing verification", fig_timing(tm), f"Share of events by disclosure-time source. Competitor reactions: n = {tm['rival_reactions']['n']}; maker cases: n = {tm['maker_cases']['n']}. Source: data/manual/disclosure_times.csv and GCAT.")}
<h3>4.6 Description of the sample</h3>
<p>{X("fig", "years")} shows how many orbital launch failures happened each year and how many of them enter the study. Most failures do not enter, because neither the maker nor any competitor was a listed launch firm at the time ({apx("E")}). {X("tab", "desc")} describes the competitor reactions firm by firm, and {X("fig", "exposure")} shows which firm is present in each independent event. The cumulative abnormal return (CAR) in these tables is defined in {sec(5, False)}; in short, it is the part of a stock's move over the window that the market does not explain.</p>
{_figure(num, "years", "Orbital launch failures per year", fig_years(fails), f"Outline: all orbital launch failures, {e(span)}. Filled: failures that enter the study.")}
{_ttable(num, "Competitor reactions by firm, CAR " + t("primary"), ["Firm", "Ticker", "Reactions", "Clusters", "Mean", "Median", "Range"], desc_rows, f"Clusters: independent events in which the firm appears; {f['n_clusters']} in total.", key="desc")}
{_figure(num, "exposure", "Which competitor is present in each independent event", fig_exposure(firm_names, exp_rows), "Columns: independent events in date order. Filled: the firm is a competitor in that event; a number means it appears more than once (two close failures).")}
</section>

<section id="s5"><h2>5. Empirical methodology</h2>
<h3>5.1 Normal and abnormal returns</h3>
<p>To measure the effect of a failure, the study first needs an estimate of how each stock would have moved without it. This "normal" return comes from the market model, which describes a stock's daily return as a constant plus a fixed share of the market's return {C.p("mackinlay1997")}. The share is called beta (β): a stock with a beta of 1.5 tends to rise 1.5% when the market rises 1%. The model is estimated by ordinary least squares, the standard method that picks the line that best fits past data, on trading days {-est[0]} to {-est[1]} before day 0. This period, called the estimation window, ends a month before the event so that the event itself cannot affect the estimate. At least {min_obs} daily returns are required. With 30 to 99 returns, the study uses a simpler market-adjusted model, in which the normal return is just the market return (α = 0 and β = 1), and flags the event:</p>
{eqs[0]}
<p>In {eqref(1)}, <i>R</i><sub><i>it</i></sub> is the return of stock <i>i</i> on day <i>t</i>, <i>R</i><sub><i>mt</i></sub> is the return of its market index, and <i>ε</i><sub><i>it</i></sub> is the part of the return that the market does not explain. The abnormal return (AR) on a day is the actual return minus the return the model predicts. The cumulative abnormal return (CAR) over an event window from day τ<sub>1</sub> to day τ<sub>2</sub> is the sum of the daily abnormal returns:</p>
{eqs[1]}
<p>A CAR of −10% over two days means that the stock did 10 percentage points worse than the market would have predicted, which can be read as the market cutting its estimate of the firm's value by about a tenth. Returns are simple percentage changes, and CARs are sums of simple abnormal returns.</p>
<h3>5.2 How precise is each reaction?</h3>
<p>Each CAR contains noise, because even on a quiet day a stock does not move exactly as the model predicts. The variance of each CAR, a measure of how much it would vary by chance, includes both this daily noise and the error from estimating the model itself {C.p("campbell1997")}. In {eqref(3)}, <i>σ̂</i><sub><i>i</i></sub><sup>2</sup> is the variance of the stock's unexplained returns in the estimation window, <i>L</i> is the length of the event window, <i>T</i> the number of estimation days, <i>W</i> the event window and <i>E</i> the estimation window:</p>
{eqs[2]}
<h3>5.3 Testing whether competitors react</h3>
<p>A statistical test asks whether an average reaction is larger than chance alone would produce. Its result is summarized by a p-value: the probability of seeing an average at least this far from zero if the true average were zero. A p-value below 0.05 is the usual threshold for calling an effect statistically significant. The confirmatory test in this paper is the standardized test of {C.n("boehmer1991")}, called the BMP test. It first divides each CAR by its own standard deviation, so that every reaction is measured in units of its own noise, and then tests whether the average of these standardized CARs (SCARs) is zero. Because it uses the spread of the standardized CARs across firms, it remains valid when the failure makes returns more volatile than usual:</p>
{eqs[3]}
<p>One failure can hit several competitors on the same day, and their reactions are then not independent. The BMP statistic is therefore adjusted as proposed by {C.n("kolari2010")} (the BMP-KP test, {eqref(5)}). Correlation is allowed only within a cluster <i>c</i>. For a pair of reactions it is the correlation of their unexplained returns in the estimation window, scaled by the share ℓ<sub><i>ij</i></sub> of event-window days that the two windows have in common. The p-values use a t distribution with <i>G</i> − 1 degrees of freedom, where <i>G</i> is the number of independent events; using the number of events rather than the number of reactions makes the test more cautious:</p>
{eqs[4]}
<p>The equal-weighted average CAR is reported with a cluster-robust interval ({eqref(6)}). A cluster-robust standard error measures the uncertainty of the average while allowing reactions in the same independent event to be correlated. The 95% interval is the range of values that the data cannot rule out at the 5% level. As a further check, the study also reports a wild cluster bootstrap p-value, which re-creates the test many times from the data and is more reliable when there are few clusters {C.p("cameron2008", "webb2023")}:</p>
{eqs[5]}
<h3>5.4 What exactly is being averaged?</h3>
<p>An average depends on how much weight each observation gets, and with few firms and events this choice matters. Let <i>i</i> = 1, …, <i>N</i> index competitor reactions (one per listed competitor per failure), <i>g</i> = 1, …, <i>G</i> independent events, and <i>k</i> = 1, …, <i>K</i> firms, with <i>N</i><sub><i>g</i></sub> and <i>N</i><sub><i>k</i></sub> reactions in event <i>g</i> and firm <i>k</i>, and <i>s</i><sub><i>i</i></sub> = √Var(<i>CAR</i><sub><i>i</i></sub>). Four averages answer four different questions. Statisticians call the quantity that an average is meant to measure the estimand:</p>
{est_eq}
<p><i>θ</i><sub>obs</sub> is the average reaction of a listed competitor to a failure; <i>θ</i><sub>event</sub> treats every independent event equally; <i>θ</i><sub>prec</sub> gives more weight to calm stocks, whose reactions are measured more precisely; and <i>θ</i><sub>firm</sub> treats every firm equally. The confirmatory hypothesis H2 is stated for <i>θ</i><sub>obs</sub>, reported with the cluster-robust interval of {eqref(6)}. The prespecified BMP-KP test asks a slightly different question, whether the average standardized CAR is zero; the two coincide only when all stocks are about equally volatile, and the test is closest in spirit to <i>θ</i><sub>prec</sub>. Both are reported, each next to the quantity it matches. None of the weightings is better on statistical grounds; <i>θ</i><sub>obs</sub> stays the main estimate because it was chosen before the results were seen.</p>
<h3>5.5 Event windows and prespecified checks</h3>
<p>The main window covers day 0 and the next trading day, which is long enough to capture a failure late in the trading day and short enough to keep out most other news. {X("tab", "win")} lists the windows. Nine robustness checks were fixed in advance. Check R1 averages the reactions within each independent event first and then tests the event averages, with both a t-test and a sign test, which counts how many averages are negative. Check R2 is a plain t-test that ignores standardization. Check R3 is a rank test in the spirit of {C.n("corrado1989")}, with a p-value obtained by simulation. Check R4 uses the wider window. Check R5 drops or shifts events whose disclosure time is uncertain. Check R6 drops reactions estimated with the market-adjusted fallback model. Check R7 drops clusters that contain more than one failure. Check R8 leaves out one firm at a time. Check R9 is a placebo test, which repeats the whole calculation on ordinary days with no failure, to see how often an average as large as the real one appears by chance. Analyses designed after the results were seen are called exploratory, are labelled wherever they appear, and never replace H2.</p>
{_ttable(num, "Event windows", ["Window", "Days", "Role"], [["Main", t("primary"), "Confirmatory test (H2)"], ["Wider", t("robust"), "Robustness check"], ["One month", t("descriptive"), "Description only"]], key="win")}
</section>

<section id="s6"><h2>6. Main results</h2>
<h3>6.1 The rocket's maker</h3>
<p>{maker_sentence} {X("tab", "case")} gives the numbers and {X("fig", "paths")} shows how the losses built up over the days after each failure. {maker_econ}With {f['n_cases']} cases from {n_case_firms} firm{"s" if n_case_firms != 1 else ""}, however, these are case studies, not an estimate of an average effect.</p>
{_ttable(num, "The rocket's maker: two-day abnormal returns", ["Rocket", "Failure", "Listed maker", f"CAR {t('primary')}", "95% interval", f"CAR {t('robust')}"], case_rows, "Intervals: CAR ± 1.96 × prediction-error standard deviation.", key="case")}
{_figure(num, "paths", "The rocket's maker: cumulative abnormal return", fig_paths(cases), f"Cumulative abnormal return from T−5 to T+20, set to zero at the close before the failure (T−1), so the value at T+1 is the two-day result in the table. {f['n_cases']} cases, market model, simple returns, home-market index. Source: project pipeline (prices from Yahoo Finance, not published).")}
<h3>6.2 Listed competitors</h3>
<p>{X("tab", "inf")} reports the confirmatory test. The equal-weighted average two-day abnormal return of listed competitors is {pct(p['mean_car'], 2)}, with a 95% interval from {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}{f"; the cluster-robust p-value is {pval(et['A']['p'])} and the wild cluster bootstrap p-value is {pval(et['A']['p_wild'])}" if et else ""}. The prespecified standardized test gives t = {p['stat']:.2f} (p = {pval(p['p'])}). {h2_sentence}</p>
<p>{rival_econ}</p>
{_ttable(num, "Confirmatory test of H2: listed competitors, CAR " + t("primary"), ["Quantity", "Value"], inf_rows, "Minimum detectable effect: two-sided 5% test, from the cluster-robust standard error implied by the interval.", key="inf")}
<p>{precision}</p>
<h3>6.3 Sample concentration, repeated firm exposure, and external validity</h3>
<p>The competitor sample is concentrated. {concentration}The same shares appear in many events, so the {f['n_clusters']} clusters are not {f['n_clusters']} independent draws from the launch industry. Grouping by event handles competitors that react on the same day, but a firm-specific shock that lasts for months, such as a change in how investors value one firm, links that firm's reactions across events. Grouping by firm would address this, but with {f['n_rival_firms']} firms such inference is not reliable.</p>
{_ttable(num, "Contribution of each firm to the competitor average", ["Firm", "Reactions", "Share of reactions", "Contribution to the mean", "Firm mean"],
         [[e(c["firm"]), str(c["n"]), f'{c["share"] * 100:.0f}%', f'<span class="num">{pct(c["contribution"], 2)}</span>',
           f'<span class="num">{pct(next(x["mean"] for x in firms if x["firm"] == c["firm"]), 2)}</span>'] for c in et["contrib"]] if et else [],
         f"Contribution: the firm's summed CARs divided by all {p['n_firm_events']} reactions; contributions add up to the equal-weighted mean ({pct(p['mean_car'], 2)}).", key="contrib") if et else ""}
<p>{offset}{weights_sentence}</p>
{_ttable(num, "The competitor average under alternative weightings", ["Weighting (estimand)", "Estimate", "Note"], wt_rows, "Sensitivity analysis added after the audit; the prespecified estimate is the first row.", key="wt") if wt_rows else ""}
{_figure(num, "weights", "The competitor average under alternative weightings", fig_weights([("Every reaction equal (prespecified)", w.get("observation_weighted"), "primary"), ("Every independent event equal", w.get("event_weighted"), ""), ("Inverse prediction-error SD", w.get("precision_weighted"), ""), ("Every firm equal", w.get("firm_balanced"), ""), ("Median reaction", w.get("median"), "")]) if w else "", f"CAR {t('primary')}, market model, simple returns; {p['n_firm_events']} reactions, {f['n_clusters']} events, {f['n_rival_firms']} firms. Shaded: the prespecified estimand.")}
<p>{firm_view}Leaving one firm out at a time (check R8, {sec(7, False)}) is the more informative check of how much the result depends on a single firm. The results describe these listed firms, not private, state-owned or diversified aerospace companies, and they cannot be extended to the launch industry as a whole.</p></section>

<section id="s7"><h2>7. Robustness and sensitivity</h2>
<p>A robustness check repeats the analysis with a different but reasonable choice, to see whether the conclusion depends on that choice. {"None of the" if f["n_robust_sig"] == 0 else str(f["n_robust_sig"]) + " of the"} {len(robust)} prespecified checks {"finds" if f["n_robust_sig"] == 0 else "find"} a significant average at the 5% level ({X("fig", "forest")} and {X("tab", "rob")}). The conclusion that no effect is detectable is therefore stable. The size of the estimate is not: across the checks the average ranges from {pct(rob_lo, 2)} ({e(_plain_name(f['rob_min_name']))}) to {pct(rob_hi, 2)} ({e(_plain_name(f['rob_max_name']))}).{" Leaving out one firm changes the sign of the average." if r8_flip else ""}</p>
{_figure(num, "forest", "Listed competitors: main test and prespecified checks", fig_forest(forest), f"Dots: average CAR {t('primary')} (except the wider-window check); lines: 95% cluster-robust intervals; tests without an interval are omitted. Full sample: {p['n_firm_events']} reactions, {f['n_clusters']} events. Shaded: the confirmatory estimate.")}
{_ttable(num, "Prespecified robustness checks", ["Check", "Average", "95% interval", "p", "Reactions", "Clusters"], rob_rows, key="rob")}
<p>The placebo test (R9) repeats the calculation on {pl.get("draws")} sets of randomly chosen ordinary trading days. If the real result were unusual, it would sit far in the tails of these placebo averages. It sits at the {ordinal(pl["actual_percentile"])} percentile, with a two-sided share of {pl["two_sided_share"]:.3f}, meaning that about {pl["two_sided_share"] * 100:.0f}% of random sets give an average at least as far from zero ({X("fig", "placebo")}). Because R9 draws a separate date for each reaction, it ignores that competitors hit by one failure move on the same day, so its spread is too narrow. It is a benchmark, not an exact test, and the percentile is not the probability that the effect is real.{placebo_b}</p>
{_figure(num, "placebo", "Real result against random ordinary days (R9)", fig_placebo(pl), f"Average CAR {t('primary')} over {p['n_firm_events']} reactions on random non-event days, {pl.get('draws')} draws (fixed seed), one random day per reaction. Red: averages at least as far out as the real result. Black line: the real failures. A benchmark, not an exact permutation test.")}
</section>

<section id="s8"><h2>8. Confounding corporate announcements and sensitivity of the competitor estimate</h2>
<p>An event study gives the event credit for every unusual return in the window. If a firm announces something else on the same days, such as a new contract or quarterly results, its reaction mixes the two pieces of news. This problem is called confounding, and the event-study model cannot fix it by itself {C.p("mackinlay1997")}. The news around the largest competitor reactions was therefore checked against public sources. {flag_intro}Flagged reactions stay in the confirmatory test, because the rules fixed in advance do not allow events to be removed after the results are seen.</p>
{_ttable(num, "Competitor reactions with other news in the window", ["Firm", "Failure", "CAR", "Verdict", "News"], flag_rows, key="flag") if flag_rows else ""}
<p>The exploratory specifications in {X("tab", "conf")} and {X("fig", "conf")} drop the flagged reactions. {e1_sentence} These exploratory estimates are not more correct than the prespecified one, because the choice of what to drop was made after seeing the data.</p>
{_ttable(num, "Confounding-news sensitivity (exploratory)", ["Specification", "Average", "95% interval", "p", "Median", "Reactions", "Clusters"], conf_rows, key="conf")}
{_figure(num, "conf", "Confounding-news sensitivity", fig_forest(conf_forest), f"Average CAR {t('primary')} with 95% cluster-robust intervals. Shaded: the prespecified estimate ({p['n_firm_events']} reactions). Hollow: exploratory specifications, chosen after results, that drop reactions with other news.")}
</section>

<section id="s9"><h2>9. Discussion</h2>
<p>The evidence supports two statements. First, {"listed makers lose a large share of their value when their rocket fails" if all_fell else "the reactions of listed makers vary"}, in a small set of cases. Second, the average reaction of listed competitors cannot be told apart from zero in this sample. The first finding fits the Challenger evidence, where the market quickly singled out the firm responsible for the failure {C.p("maloney2003")}. The second differs from the clear average contagion that {C.n("lang1992")} find for bankruptcies, although their finding that competitors can gain in concentrated industries shows that the net effect depends on the industry.</p>
<p>Several explanations are consistent with a small net reaction of competitors, and the data cannot separate them. Contagion and competitive gains may both be present and cancel each other out, as the two channels in {sec(1, False)} suggest. Customers may be unable to switch providers quickly, because rockets and satellites need long preparation and the choice of providers is limited {C.p("dillow2015")}, which would weaken the competitive effect in the short run. Or investors may treat a failure mainly as news about the failed firm and its rocket rather than about the industry. A short-lived market-wide mood effect of the kind found after air crashes {C.p("kaplanski2010")} would be removed by the market model, because it moves the benchmark index as well. Separating these explanations would need customer-level data on contracts that moved between providers, launch backlogs, or a much larger sample of listed competitors.</p>
<p>For investors, the results suggest that, in this sample, a launch failure is mainly a risk for the firm whose rocket failed rather than for the listed industry as a whole. The evidence is too weak, however, to treat competitors' shares as unaffected, and the conclusion may change as more launch firms list and the number of independent events grows.</p></section>

<section id="s10"><h2>10. Limitations</h2>
{limitations}</section>

<section id="s11"><h2>11. Conclusion</h2>
<p>{"When an orbital rocket fails, its listed maker loses a large share of its value within two days in every case observed." if all_fell else "The reactions of listed makers vary across the few listed cases."} For listed competitors, the average two-day reaction is {pct(p['mean_car'], 2)}, with an interval from {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}. The data do not establish contagion or competitive gains, and they do not rule out either at magnitudes of a few percent.</p>
<p>The study is useful as a transparent and reproducible starting point. Every number can be recomputed from the published data ({apx("D")}), and the rules were fixed before the results ({apx("G")}). Adding more listed firms, including firms that have since delisted, and adding SpaceX as its price history grows, would sharpen the answer without changing the prespecified test.</p></section>

<section class="refs-sec newpage" id="refs"><h2>References</h2><div class="refs">REFLIST</div></section>

<div class="appendices newpage" id="apx">
<section id="apx-a"><h2>Appendix A. Competitor event list</h2>
<p>{X("tab", "events")} lists every competitor reaction in the confirmatory test, in date order, with the model used, the source of the disclosure time, any news flag, the two-day CAR and its standard deviation.</p>
{_ttable(num, "All competitor reactions, CAR " + t("primary"), ["Failure", "Rocket", "T0", "Ticker", "Cluster", "Model", "Timing", "Flag", "CAR", "SD"], ev_rows, "Model: MM market model, MA market-adjusted fallback. SD: prediction-error standard deviation of the CAR.", "small", key="events")}
</section>
<section id="apx-b"><h2>Appendix B. Firm mapping and competitor criteria</h2>
<p>Competitors are classified point in time from two hand-built files. The firm map (<code>data/manual/firm_map.csv</code>) records, for each firm and period, the listing dates, the ownership of each rocket, how important launch is to the firm, and the source of each fact. The size-and-market table (<code>data/manual/vehicle_segments.csv</code>) records the size class and customer market of each rocket. A Tier 1 competitor must be listed, have launch as a pure-play or major business, sell a rocket of the same size class to the same customer market as the failed rocket, and have flown that rocket in the previous 730 days. Tier 2 competitors are added case by case in <code>data/manual/rival_overrides.csv</code>, each with a source. Diversified aerospace groups are classified as having minor exposure to launch and enter only descriptive tiers, not the test.</p></section>
<section id="apx-c"><h2>Appendix C. Additional exploratory results</h2>
{(f'<p>{X("tab", "expl")} reports comparisons designed after the results were seen. Their p-values are adjusted with the Holm method, which raises each p-value to allow for the fact that several comparisons were made at once.</p>' + _ttable(num, "Exploratory comparisons (Holm-adjusted p-values)", ["Comparison", "Estimate", "p", "p (Holm)"], expl_rows, key="expl")) if expl_rows else "<p>There are no additional exploratory results.</p>"}
</section>
<section id="apx-d"><h2>Appendix D. Statistical verification</h2>
<p>{verify_txt} The CARs themselves need licensed prices and are reproduced by running the pipeline again.</p></section>
<section id="apx-e"><h2>Appendix E. Exclusions</h2>
<p>Most failures do not enter the study because neither the maker nor any competitor was a listed launch firm at the time. {"The reasons are counted below." if why_rows or drop_rows else ""}</p>
{_ttable(num, "Failures not in the study, by reason", ["Reason", "Failures"], why_rows, "A failure can have more than one reason, so the counts can add up to more than the number of excluded failures.", key="why") if why_rows else ""}
{_ttable(num, "Firm-events dropped at the price-coverage step", ["Reason", "Firm-events"], drop_rows, key="drop") if drop_rows else ""}
</section>
<section id="apx-f"><h2>Appendix F. Reproduction guide</h2>
<p>The full analysis can be reproduced with Python 3.11 or later. After installing the required packages with <code>pip install -r requirements.txt</code>, the script <code>pipeline/01_ingest_launches.py</code> downloads GCAT and classifies the launches, and <code>02_map_firms.py</code> applies the firm map. The script <code>03_pull_prices.py</code> downloads prices from Yahoo Finance, which are not redistributed, and <code>04_check_coverage.py</code> writes the feasibility check. The script <code>05_event_study.py</code> runs the prespecified analysis, and <code>06</code> and <code>09</code> run the exploratory checks. Finally, <code>07_export_site_data.py</code> exports the derived statistics, <code>08_build_html.py</code> builds the website and this paper, <code>python audit/verify_published.py</code> checks every published statistic again, and <code>python -m pytest tests</code> runs the test suite.</p></section>
<section id="apx-g"><h2>Appendix G. Freeze record</h2>
<p>The rules of the study (hypothesis, test, windows, sample criteria and checks) were committed to the public repository before the first results were computed. {(X("tab", "freeze") + " lists the commits.") if freeze_rows else "The repository history records the commits."}{commit_txt} Exploratory analyses added later (E1 to E3, R9b and the audit diagnostics) are labelled wherever they appear.</p>
{_ttable(num, "Commit record", ["Item", "Commit", "Time (+06:00)"], freeze_rows, key="freeze") if freeze_rows else ""}
</section>
</div>
"""
    sections = resolve_xrefs(sections, num).replace("REFLIST", C.reference_list())
    body = f"""<a class="skip-link" href="#main">Skip to the paper</a>
{SC.header("paper", "", bool(pdf_name), meta.get("repo_url"))}
<header class="paper-head"><div class="wrap ph-in">
  <nav class="crumbs screen-only" aria-label="Breadcrumb"><ol><li><a href="index.html">Overview</a></li><li aria-current="page">Paper</li></ol></nav>
  <p class="ph-eyebrow">Paper · Space Shock</p>
  <h1>{e(SC.PAPER_TITLE)}</h1>
  <p class="dek">Evidence from publicly listed launch providers: stock market reactions to orbital launch failures, {e(span)}.</p>
  <p class="byline">{e(meta.get("author", "Nahian Ibnat"))} · {e(updated)} · Draft for feedback, not peer reviewed</p>
  <dl class="ph-meta screen-only">
    <div><dt>Status</dt><dd>Paper, not peer reviewed</dd></div>
    <div><dt>Version</dt><dd>Analysis rules v{e(str(plan_v))} · results {e(updated)}</dd></div>
    <div><dt>Sample</dt><dd>{f['n_failures']} failures · {p['n_firm_events']} competitor reactions · {f['n_clusters']} independent events</dd></div>
    <div><dt>Formats</dt><dd>{f'<a class="btn small" href="{e(pdf_name)}" download>Download PDF</a> ' if pdf_name else ''}<a href="methods.html#replicate">Replication</a></dd></div>
  </dl>
</div></header>
<div class="wrap paper-grid">
<aside class="paper-toc screen-only" aria-label="Contents"><nav aria-label="Paper contents"><p class="pt-h">Contents</p><ol>{toc_items}</ol></nav></aside>
<details class="toc-mobile screen-only"><summary>Contents</summary><nav aria-label="Paper contents"><ol>{toc_items}</ol></nav></details>
<main id="main" class="article cs">
{sections}
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

<p class="signoff">{e(meta.get("author", "Nahian Ibnat"))}, {e(updated)}. Cite as: Ibnat, N. ({e(year)}). <em>{e(SC.PAPER_TITLE)}.</em> Space Shock paper.{(" " + e(meta["live_url"]) + "paper.html") if meta.get("live_url") else ""} Research, not investment advice.</p>
</main>
</div>
{SC.footer("", meta, bool(pdf_name), SC.cite(year, meta))}
{SC.TOC_SCRIPT}"""
    desc = (f"Paper: {f['n_failures']} orbital launch failures, {span}. Listed makers lose {pct(f['case_hi'])} to {pct(f['case_lo'])} in two days; "
            f"listed rivals {pct(p['mean_car'], 2)} (95% interval {pct(p['ci_low'], 2)} to {pct(p['ci_high'], 2)}), not detectable with {f['n_clusters']} independent events.")
    url = (meta["live_url"].rstrip("/") + "/paper.html") if meta.get("live_url") else None
    img = (meta["live_url"].rstrip("/") + "/og.png") if meta.get("live_url") else None
    return landing._shell(f"{SC.PAPER_TITLE} (Space Shock paper)", desc, url, body, css, url, img, body_class="paper")
