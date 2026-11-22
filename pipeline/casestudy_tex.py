"""LaTeX version of the paper: paper.html (one source of text) -> paper/paper.tex -> paper.pdf.

- Text: converted from the case-study HTML, so the web page and the PDF never disagree.
  Elements with class "screen-only" (for example the PDF links) are left out.
- Figures: redrawn with matplotlib as vector PDFs (paper/fig-1.pdf ...), Times-style font.
- Typeset: XeLaTeX with Times New Roman 12 pt (TeX Gyre Termes if Times New Roman is not installed);
  pdfLaTeX with the Times package as a fallback. If no LaTeX is installed, the .tex folder is still
  written, ready to upload to Overleaf.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

INK, MUTED, RULE, SIGNAL = "#0F172A", "#475569", "#D9DEE7", "#E8604C"

# ----------------------------------------------------------------------------- LaTeX escaping
_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\u2212": r"\textminus{}", "\u00b7": r"\textperiodcentered{}",
        "\u2013": "--", "\u2014": "---", "\u2192": r"$\rightarrow$", "\u00a0": "~"}


def esc(s: str) -> str:
    return "".join(_ESC.get(ch, ch) for ch in s)


# ----------------------------------------------------------------------------- HTML -> LaTeX
class _Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent, self.kids = tag, dict(attrs), parent, []

    @property
    def cls(self):
        return (self.attrs.get("class") or "").split()


class _Tree(HTMLParser):
    VOID = {"br", "img", "meta", "link", "input", "hr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", {}); self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = _Node(tag, attrs, self.cur); self.cur.kids.append(n)
        if tag not in self.VOID:
            self.cur = n

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, data):
        self.cur.kids.append(data)


def _find(n, pred):
    if isinstance(n, str):
        return None
    if pred(n):
        return n
    for k in n.kids:
        r = _find(k, pred)
        if r is not None:
            return r
    return None


class _Conv:
    def __init__(self, figs, base_url=""):
        self.figs, self.fig_i, self.base = figs, 0, base_url.rstrip("/") + "/" if base_url else ""
        self.anchor = None

    def inline(self, n) -> str:
        if isinstance(n, str):
            return esc(re.sub(r"\s+", " ", n))
        if "screen-only" in n.cls or n.tag in ("svg", "script", "style"):
            return ""
        inner = "".join(self.inline(k) for k in n.kids)
        if n.tag in ("strong", "b"):
            return rf"\textbf{{{inner}}}"
        if n.tag in ("em", "i"):
            return rf"\emph{{{inner}}}"
        if n.tag == "sup":
            return rf"\textsuperscript{{{inner.strip()}}}"
        if n.tag == "code":                              # long file paths may break after / and _
            return r"\texttt{" + inner.replace("/", r"/\allowbreak{}").replace(r"\_", r"\_\allowbreak{}") + "}"
        if n.tag == "span" and "num" in n.cls:
            return inner
        if n.tag == "br":
            return r"\\ "
        if n.tag == "a":
            href = n.attrs.get("href") or ""
            if href.startswith("#") and len(href) > 1:        # in-text citation, table, figure, section or appendix link
                return r"\hyperlink{" + href[1:] + "}{" + inner + "}"
            if not href:
                return inner
            text = "".join(k for k in n.kids if isinstance(k, str)).strip()
            if text == href and re.match(r"https?://", href):  # a printed address (reference list): let it break across lines
                return r"\url{" + href.replace("%", r"\%").replace("#", r"\#") + "}"
            if not re.match(r"https?://", href):
                if not self.base:
                    return inner
                href = self.base + href
            return r"\href{" + href.replace("%", r"\%").replace("#", r"\#") + "}{" + inner + "}"
        return inner

    def block(self, n) -> str:
        if isinstance(n, str):
            t = n.strip()
            return esc(re.sub(r"\s+", " ", t)) + "\n\n" if t else ""
        if "screen-only" in n.cls or n.tag in ("svg", "script", "style", "nav"):
            return ""
        t = n.tag
        anchor = n.attrs.get("id")
        if t in ("section", "div") and ("newpage" in n.cls or (anchor and "cs-table" not in n.cls)):
            # sections, the reference list and the appendices: page break where asked, and a link target on the heading
            pre = "\\clearpage\n" if "newpage" in n.cls else ""
            heads = [k for k in n.kids if not isinstance(k, str) and k.tag in ("h2", "h3")]
            if anchor and heads and t == "section" and "abstract-sec" not in n.cls:
                self.anchor = anchor
            elif anchor:
                pre += r"\hypertarget{" + anchor + "}{}"
            n2 = _Node(n.tag, {k: v for k, v in n.attrs.items() if k != "id"}); n2.kids = n.kids
            n2.attrs["class"] = " ".join(c for c in n.cls if c != "newpage")
            return pre + self.block(n2)
        if t in ("h2", "h3"):
            tgt = (r"\hypertarget{" + self.anchor + "}{}") if self.anchor else ""
            self.anchor = None
            cmd = "section" if t == "h2" else "subsection"
            return "\\" + cmd + "*{" + tgt + self.inline(n).strip() + "}\n"
        if t == "div" and "refs" in n.cls:
            items = [k for k in n.kids if not isinstance(k, str) and k.tag == "p"]
            out = ""
            for k in items:                                  # APA: no numbers, hanging indent of 0.5 inch
                out += ("\\noindent\\hypertarget{" + (k.attrs.get("id") or "") + "}{}\\hangindent=0.5in\\hangafter=1 "
                        + self.inline(k).strip() + "\\par\n")
            return "{\\raggedright\\setlength{\\parskip}{8pt}\n" + out + "}\n\n"
        if t == "p":
            txt = self.inline(n).strip()
            if "signoff" in n.cls:
                return r"\vspace{1.5em}\noindent\rule{\textwidth}{0.4pt}\par\noindent{\small " + txt + "}\n\n"
            return txt + "\n\n" if txt else ""
        if t in ("ul", "ol"):
            env = "itemize" if t == "ul" else "enumerate"
            items = "".join(r"  \item " + "".join(self.inline(k) for k in li.kids).strip() + "\n"
                            for li in n.kids if not isinstance(li, str) and li.tag == "li")
            return rf"\begin{{{env}}}[leftmargin=*,itemsep=2pt,topsep=4pt]" + "\n" + items + rf"\end{{{env}}}" + "\n\n"
        if t == "dl":
            out = ""
            for k in n.kids:
                if isinstance(k, str):
                    continue
                if k.tag == "dt":
                    out += r"\paragraph{" + self.inline(k).strip() + "}"
                elif k.tag == "dd":
                    out += " " + self.inline(k).strip() + "\n\n"
            return out
        if t == "aside" and "inshort" in n.cls:
            body = "".join(self.block(k) for k in n.kids if isinstance(k, str) or k.tag != "h2")
            return ("\\begin{center}\\fcolorbox{black}{boxbg}{\\begin{minipage}{0.94\\textwidth}\\vspace{4pt}"
                    "{\\textbf{\\textsc{In short}}}\\par\\vspace{2pt}" + body + "\\vspace{2pt}\\end{minipage}}\\end{center}\n\n")
        if t == "table":
            return self.table(n, small="small" in n.cls)
        if t == "div" and "eq" in n.cls and n.attrs.get("data-tex"):
            tgt = (r"\hypertarget{" + n.attrs["id"] + "}{}") if n.attrs.get("id") else ""
            return tgt + "\\begin{equation}\n" + n.attrs["data-tex"] + "\n\\end{equation}\n\n"
        if t == "div" and "cs-table" in n.cls:
            inner = "".join(self.block(k) for k in n.kids)
            tgt = (r"\hypertarget{" + n.attrs["id"] + "}{}") if n.attrs.get("id") else ""
            if "xltabular" in inner:                         # long tables may break across pages
                return tgt + inner
            return "\\par\\noindent\\begin{minipage}{\\textwidth}" + tgt + "\n" + inner + "\\end{minipage}\\par\\vspace{4pt}\n\n"
        if t == "p" and "tcap" in n.cls:
            return "\\par\\vspace{6pt}\\noindent{\\small " + self.inline(n).strip() + "}\\par\\nopagebreak\n"
        if t == "section" and "abstract-sec" in n.cls:
            inner = "".join(self.block(k) for k in n.kids if isinstance(k, str) or k.tag != "h2")
            return "\\begin{abstract}\n\\noindent " + inner.strip() + "\n\\end{abstract}\n\n"
        if t == "figure" and "cs-fig" in n.cls:
            caps = [k for k in n.kids if not isinstance(k, str) and k.tag == "figcaption"]
            title = self.inline(caps[0]).strip() if caps else ""
            num = re.match(r"^Figure (\d+)\.", title)
            self.fig_i = int(num.group(1)) if num else self.fig_i + 1
            title = re.sub(r"^Figure \d+\.\s*", "", title)
            cap = self.inline(caps[1]).strip() if len(caps) > 1 else ""
            f = self.figs.get(n.attrs.get("data-fig")) or self.figs.get(self.fig_i)      # by id, else by number
            if not f:
                return ""
            tgt = (r"\hypertarget{" + n.attrs["id"] + "}{}") if n.attrs.get("id") else ""
            return ("\\begin{figure}[htbp]\\centering" + tgt + "\n"
                    f"\\caption*{{\\textbf{{Figure {self.fig_i}.}} {title}}}\n"
                    f"\\includegraphics[width=\\textwidth]{{{f}}}\n"
                    f"\\par\\vspace{{2pt}}{{\\footnotesize {cap}}}\n\\end{{figure}}\n\n")
        return "".join(self.block(k) for k in n.kids)

    def table(self, n, small=False) -> str:
        rows = []
        for tr in _iter(n, "tr"):
            cells = [c for c in tr.kids if not isinstance(c, str) and c.tag in ("th", "td")]
            rows.append(([self.inline(c).strip() for c in cells], any(c.tag == "th" for c in cells)))
        if not rows:
            return ""
        ncol = max(len(r[0]) for r in rows)
        widths = [max(len(re.sub(r"\\[a-z]+\{|\}", "", c)) for c in col) for col in
                  zip(*[r[0] + [""] * (ncol - len(r[0])) for r in rows])]
        spec = "".join("X" if w > 22 else "l" for w in widths)
        if "X" not in spec:                                     # stretch the widest column, not the last one
            k = widths.index(max(widths))
            spec = "".join("X" if i == k else "l" for i in range(ncol))
        size = "\\scriptsize" if small else "\\small"
        long = len(rows) > 18
        env = "xltabular" if long else "tabularx"
        out = "{" + size + "\\setlength{\\tabcolsep}{4pt}\\begin{" + env + "}{\\textwidth}{" + spec + "}\n\\toprule\n"
        for i, (cells, head) in enumerate(rows):
            cells = cells + [""] * (ncol - len(cells))
            line = " & ".join((r"\textbf{" + c + "}") if head else c for c in cells) + r" \\" + "\n"
            out += line
            if head:
                out += "\\midrule\n" + ("\\endhead\n" if long else "")
        return out + "\\bottomrule\n\\end{" + env + "}}\n\\vspace{6pt}\n\n"


def _iter(n, tag):
    for k in n.kids:
        if isinstance(k, str):
            continue
        if k.tag == tag:
            yield k
        else:
            yield from _iter(k, tag)


# ----------------------------------------------------------------------------- figures (matplotlib)
def _style(plt):
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "TeX Gyre Termes", "Liberation Serif", "STIXGeneral", "DejaVu Serif"],
        "font.size": 10, "axes.edgecolor": INK, "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "axes.grid.axis": "y", "grid.color": RULE,
        "grid.linewidth": 0.6, "pdf.fonttype": 42, "svg.fonttype": "none", "axes.unicode_minus": True})


def _pct_axis(ax, which="y", d=0):
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: f"{v * 100:+.{d}f}%".replace("-", "\u2212") if abs(v) > 1e-12 else f"{0:.{d}f}%")
    (ax.yaxis if which == "y" else ax.xaxis).set_major_formatter(fmt)


def _forest(plt, rows, path):
    fig, ax = plt.subplots(figsize=(6.3, 0.27 * len(rows) + 0.7))
    for i, (lab, m, a, b, kind) in enumerate(rows):
        yv = len(rows) - 1 - i
        col = INK if kind != "explore" else MUTED
        if kind == "primary":
            ax.axhspan(yv - 0.5, yv + 0.5, color="#EEF1F5", zorder=0)
        ax.plot([a, b], [yv, yv], color=col, linewidth=1.3)
        ax.plot([m], [yv], "o", markersize=5.5 if kind == "primary" else 4.5,
                markerfacecolor=col if kind != "explore" else "white", markeredgecolor=col)
    ax.axvline(0, color=INK, linewidth=0.8)
    ax.set_yticks(range(len(rows))[::-1], [r[0] for r in rows], fontsize=8.5)
    ax.set_ylim(-0.6, len(rows) - 0.4); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    _pct_axis(ax, "x", 1)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def make_figures(data: dict, outdir: Path) -> dict:
    """Vector figures keyed by the same ids as the web page's <figure data-fig="...">."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from collections import Counter

    import diagnostics as D
    from casestudy import _anchored, _plain_name
    from landing import MONTHS, facts, pct

    _style(plt)
    res, fails, fes, man = data["results"], data["failures"], data["firmEvents"], data["manifest"]
    f = facts(data)
    p = f["prim"]
    figs = {}

    def save(fig, key):
        figs[key] = f"fig-{key}.pdf"; fig.savefig(outdir / figs[key]); plt.close(fig)

    # sample diagram (boxes and arrows; units change along the way)
    from casestudy import sample_graph
    nodes, edges = sample_graph(man.get("sample") or {}, f, p)
    if nodes:
        fig, ax = plt.subplots(figsize=(6.3, 2.9))
        bw, bh, sx, sy = 0.92, 0.66, 1.3, 1.05
        pos = {n[0]: (n[4] * sx, -n[5] * sy) for n in nodes}
        for a_, b_, lab in edges:
            (x1, y1), (x2, y2) = pos[a_], pos[b_]
            if y1 == y2:
                p1, p2 = (x1 + bw, y1 + bh / 2), (x2, y2 + bh / 2)
                tx, ty, ha = (p1[0] + p2[0]) / 2, p1[1] + 0.06, "center"
            elif x1 == x2:
                p1, p2 = (x1 + bw / 2, y1), (x2 + bw / 2, y2 + bh)
                tx, ty, ha = p1[0] + 0.05, (p1[1] + p2[1]) / 2, "left"
            else:
                p1, p2 = (x1 + bw / 2, y1), (x2, y2 + bh / 2)
                tx, ty, ha = (p1[0] + p2[0]) / 2 + 0.05, (p1[1] + p2[1]) / 2, "left"
            ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8))
        for nid, lab, val, unit, c, r in nodes:
            x, y = pos[nid]
            ax.add_patch(plt.Rectangle((x, y), bw, bh, facecolor="#EEF1F5" if nid in ("maker", "clu") else "white", edgecolor=INK, linewidth=0.8))
            ax.text(x + 0.06, y + bh - 0.2, f"{val:,}", fontsize=11, fontweight="bold")
            ax.text(x + 0.06, y + bh - 0.4, lab, fontsize=7)
            ax.text(x + 0.06, y + 0.07, unit, fontsize=5.8, color=MUTED)
        ax.set_xlim(-0.05, max(n[4] for n in nodes) * sx + bw + 0.05); ax.set_ylim(-max(n[5] for n in nodes) * sy - 0.08, bh + 0.25); ax.axis("off")
        fig.tight_layout(); save(fig, "sample")

    # weighting comparison
    w = f.get("w")
    if w:
        rows_w = [("Every reaction equal (prespecified)", w["observation_weighted"]), ("Every independent event equal", w["event_weighted"]),
                  ("Inverse prediction-error SD", w["precision_weighted"]), ("Every firm equal", w["firm_balanced"]), ("Median reaction", w["median"])]
        fig, ax = plt.subplots(figsize=(6.3, 1.9))
        for i, (lab, v) in enumerate(rows_w):
            yv = len(rows_w) - 1 - i
            if i == 0:
                ax.axhspan(yv - 0.5, yv + 0.5, color="#EEF1F5", zorder=0)
            ax.plot([0, v], [yv, yv], color=MUTED, linewidth=0.8); ax.plot([v], [yv], "o", color=INK, markersize=5)
            ax.annotate(pct(v, 2), xy=(v, yv), xytext=(6 if v >= 0 else -6, 4), textcoords="offset points", fontsize=8, ha="left" if v >= 0 else "right")
        ax.axvline(0, color=INK, linewidth=0.8)
        ax.set_yticks(range(len(rows_w))[::-1], [r[0] for r in rows_w], fontsize=8.5)
        ax.set_ylim(-0.6, len(rows_w) - 0.4); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
        lo_, hi_ = min(r[1] for r in rows_w + [("", 0)]), max(r[1] for r in rows_w + [("", 0)])
        ax.set_xlim(lo_ - 0.006, hi_ + 0.006)
        _pct_axis(ax, "x", 1)
        fig.tight_layout(); save(fig, "weights")

    # event timing verification
    tm = D.timing(fes)
    order = [("high", "Sourced statement, high confidence", INK), ("low", "Sourced statement, low confidence", MUTED),
             ("provisional", "GCAT launch time (unverified)", "white")]
    groups = [("Rival reactions", tm["rival_reactions"]), ("Maker cases", tm["maker_cases"])]
    if any(g["n"] for _, g in groups):
        fig, ax = plt.subplots(figsize=(6.3, 1.5))
        for i, (lab, g) in enumerate(groups):
            left = 0.0
            for k, kl, col in order:
                n = g["counts"].get(k, 0)
                if not n or not g["n"]:
                    continue
                wdt = n / g["n"]
                ax.barh(len(groups) - 1 - i, wdt, left=left, color=col, edgecolor=INK, height=0.55, label=kl if i == 0 else None)
                if wdt > 0.05:
                    ax.text(left + wdt / 2, len(groups) - 1 - i, str(n), ha="center", va="center", fontsize=8, color="white" if k != "provisional" else INK)
                left += wdt
        ax.set_yticks(range(len(groups))[::-1], [f"{l} (n = {g['n']})" for l, g in groups], fontsize=8.5)
        ax.set_xlim(0, 1); ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%")); ax.grid(False)
        ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3)
        fig.tight_layout(); save(fig, "timing")

    # failures per year
    yrs = [int(str(x["launch_utc"])[:4]) for x in fails if x.get("launch_utc")]
    if yrs:
        allc = Counter(yrs)
        inc = Counter(int(str(x["launch_utc"])[:4]) for x in fails if x.get("in_rival_test") or x.get("in_provider_case_series"))
        xs = list(range(min(yrs), max(yrs) + 1))
        fig, ax = plt.subplots(figsize=(6.3, 2.4))
        ax.bar(xs, [allc.get(x, 0) for x in xs], width=0.72, facecolor="white", edgecolor=INK, linewidth=0.8, label="All failures")
        ax.bar(xs, [inc.get(x, 0) for x in xs], width=0.72, color=INK, label="Enter the study")
        ax.set_xlim(xs[0] - 0.7, xs[-1] + 0.7); ax.legend(frameon=False, loc="upper left", fontsize=9)
        ax.yaxis.get_major_locator().set_params(integer=True)
        fig.tight_layout(); save(fig, "years")

    # exposure matrix
    firm_names, rows = D.exposure_matrix(fes)
    if rows:
        fig, ax = plt.subplots(figsize=(6.3, 0.32 * len(firm_names) + 0.6))
        for j, r in enumerate(rows):
            for i, fn in enumerate(firm_names):
                n = r["counts"].get(fn, 0)
                yv = len(firm_names) - 1 - i
                ax.add_patch(plt.Rectangle((j + 0.06, yv + 0.12), 0.88, 0.76, facecolor=INK if n else "white", edgecolor=INK if n else RULE, linewidth=0.6))
                if n > 1:
                    ax.text(j + 0.5, yv + 0.5, str(n), ha="center", va="center", color="white", fontsize=7)
        ax.set_xlim(0, len(rows)); ax.set_ylim(0, len(firm_names))
        ax.set_yticks([len(firm_names) - 1 - i + 0.5 for i in range(len(firm_names))], firm_names, fontsize=9)
        ticks = list(range(0, len(rows), 3))
        ax.set_xticks([t + 0.5 for t in ticks], [rows[t]["date"][:4] for t in ticks], fontsize=8)
        ax.grid(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_visible(False)
        ax.tick_params(length=0)
        fig.tight_layout(); save(fig, "exposure")

    # maker paths
    cases = res.get("provider_case_series") or []
    if cases:
        fig, ax = plt.subplots(figsize=(6.3, 3.0))
        shades = ["#E8604C", "#B4361F", "#0F172A", "#F29A8A", "#475569"]
        ends = []
        for i, c in enumerate(cases):
            pth = _anchored(c["path"])
            ax.plot([t for t, _ in pth], [v for _, v in pth], color=shades[i % len(shades)], linewidth=1.3)
            ends.append([pth[-1][1], f'{c["vehicle"]}, {MONTHS[int(str(c["day0"])[5:7]) - 1]} {str(c["day0"])[:4]}: {pct(pth[-1][1])}',
                         shades[i % len(shades)]])
        ax.axhline(0, color=INK, linewidth=0.8); ax.axvline(-0.5, color=INK, linewidth=0.8, linestyle=(0, (3, 3)))
        ax.set_xlim(-6, 20)
        ax.set_xticks([-5, -1, 0, 1, 5, 10, 15, 20], ["T\u22125", "", "T0", "", "T+5", "T+10", "T+15", "T+20"])
        _pct_axis(ax)
        lo, hi = ax.get_ylim(); gap = (hi - lo) * 0.065
        ends.sort()
        for i in range(1, len(ends)):
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + gap)
        for yv, lab, col in ends:
            ax.annotate(lab, xy=(20, yv), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8.5, color=col, annotation_clip=False)
        fig.subplots_adjust(left=0.1, right=0.72, top=0.96, bottom=0.12)
        save(fig, "paths")

    # forest: prespecified only; and the confounding sensitivity
    robust = [r for r in (res.get("robustness") or []) if r.get("p") is not None and r.get("ci_low") is not None]
    main = ("Main test (prespecified)", p["mean_car"], p["ci_low"], p["ci_high"], "primary")
    _forest(plt, [main] + [(_plain_name(r["name"]), r["mean_car"], r["ci_low"], r["ci_high"], "robust") for r in robust], outdir / "fig-forest.pdf")
    figs["forest"] = "fig-forest.pdf"
    short = {"E1": "Exploratory: drop contract days", "E2": "Exploratory: also possible news", "E3": "Exploratory: drop all flagged"}
    conf = [(short[r["id"]], r["mean_car"], r["ci_low"], r["ci_high"], "explore")
            for r in (res.get("exploratory_confounding") or {}).get("results", []) if r.get("id") in short]
    if conf:
        _forest(plt, [main] + conf, outdir / "fig-conf.pdf"); figs["conf"] = "fig-conf.pdf"

    # placebo
    pl = res.get("placebo") or {}
    d = [v for v in (pl.get("distribution") or []) if v is not None]
    if d:
        act = pl["actual_mean_car"]
        fig, ax = plt.subplots(figsize=(6.3, 2.4))
        n, edges, patches = ax.hist(d, bins=30, color=MUTED, alpha=0.5, edgecolor="white", linewidth=0.5)
        for pt, x0, x1 in zip(patches, edges[:-1], edges[1:]):
            if (x0 >= act) if act >= 0 else (x1 <= act):
                pt.set_facecolor(SIGNAL); pt.set_alpha(0.85)
        ax.axvline(act, color=INK, linewidth=1.6)
        right = act > edges[len(edges) * 2 // 3]
        ax.annotate(f"real failures {pct(act, 2)}", xy=(act, ax.get_ylim()[1] * 0.95), xytext=(-5 if right else 5, 0),
                    textcoords="offset points", ha="right" if right else "left", fontsize=9)
        _pct_axis(ax, "x", 1)
        fig.tight_layout(); save(fig, "placebo")
    return figs


# ----------------------------------------------------------------------------- document
PREAMBLE = r"""\documentclass[12pt,a4paper]{article}
\usepackage{iftex}
\ifXeTeX
  \usepackage{fontspec}
  \IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}
\else\ifLuaTeX
  \usepackage{fontspec}
  \IfFontExistsTF{Times New Roman}{\setmainfont{Times New Roman}}{\setmainfont{TeX Gyre Termes}}
\else
  \usepackage[T1]{fontenc}\usepackage[utf8]{inputenc}\usepackage{mathptmx}
\fi\fi
\usepackage{textcomp}
\usepackage[margin=2.5cm]{geometry}
\usepackage{graphicx,booktabs,tabularx,xltabular,enumitem,xcolor,caption,amsmath}
\definecolor{linkblue}{HTML}{1F4E8C}
\IfFileExists{xurl.sty}{\usepackage{xurl}}{}
\usepackage[colorlinks=true,linkcolor=linkblue,urlcolor=linkblue,citecolor=linkblue]{hyperref}\urlstyle{same}
\definecolor{boxbg}{HTML}{F3EEE4}
\captionsetup{labelformat=empty,justification=raggedright,singlelinecheck=false,skip=4pt}
\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}\setlength{\emergencystretch}{3em}
\renewcommand{\arraystretch}{1.25}
\usepackage{titlesec}
\titleformat{\section}{\large\bfseries}{}{0pt}{}
\titleformat{\subsection}{\normalsize\bfseries}{}{0pt}{}
\titlespacing*{\section}{0pt}{14pt}{4pt}
\titlespacing*{\subsection}{0pt}{10pt}{2pt}
\usepackage{fancyhdr}\pagestyle{fancy}\fancyhf{}\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\small\thepage}\fancyhead[R]{\small\textsc{Space Shock}}
"""


def build_tex(html: str, data: dict, meta: dict, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("fig-*.pdf"):                 # figures are regenerated on every build
        old.unlink()
    figs = make_figures(data, outdir)
    tree = _Tree(); tree.feed(html)
    head = _find(tree.root, lambda n: n.tag == "header" and "paper-head" in n.cls)
    main = _find(tree.root, lambda n: n.tag == "main")
    conv = _Conv(figs, meta.get("live_url") or "")
    title = conv.inline(_find(head, lambda n: n.tag == "h1")).strip()
    dek = conv.inline(_find(head, lambda n: n.tag == "p" and "dek" in n.cls)).strip()
    byline = _find(head, lambda n: n.tag == "p" and "byline" in n.cls)
    date = ""
    if byline is not None:
        txt = "".join(k for k in byline.kids if isinstance(k, str))
        m = re.search(r"([A-Z][a-z]{2} \d{4})", txt)
        date = m.group(1) if m else ""
    url = meta.get("live_url") or ""
    body = conv.block(main)
    body = re.sub(r"\n{3,}", "\n\n", body)
    doc = (PREAMBLE + "\\begin{document}\n"
           + "{\\raggedright{\\LARGE\\bfseries " + title + "\\par}\\vspace{6pt}{\\large " + dek + "\\par}\\vspace{8pt}"
           + "{\\normalsize " + esc(meta.get("author", "Nahian Ibnat")) + (" \\textperiodcentered{} " + esc(date) if date else "")
           + "\\par}" + ("{\\small Interactive version: \\url{" + url + "}\\par}" if url else "") + "}\n\\vspace{6pt}\n"
           + body + "\\end{document}\n")
    tex = outdir / "paper.tex"
    tex.write_text(doc, encoding="utf-8")
    return tex


def find_engine() -> list[str] | None:
    for exe, args in (("xelatex", []), ("lualatex", []), ("pdflatex", [])):
        if shutil.which(exe):
            return [shutil.which(exe), *args]
    return None


def compile_pdf(tex: Path, pdf_out: Path) -> bool:
    eng = find_engine()
    if not eng:
        print("Skipped paper.pdf: no LaTeX found. Install MiKTeX (miktex.org) and run step 08 again, "
              "or upload the paper/ folder to Overleaf (compiler: XeLaTeX).")
        return False
    cmd = [*eng, "-interaction=nonstopmode", "-halt-on-error", tex.name]
    try:
        for _ in range(2):                                            # twice, so page layout settles
            r = subprocess.run(cmd, cwd=tex.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
        if r.returncode != 0:
            log = (tex.parent / "paper.log")
            tail = log.read_text(errors="ignore")[-1500:] if log.exists() else r.stdout[-1500:]
            print("Skipped paper.pdf: LaTeX stopped with an error. End of the log:\n" + tail)
            return False
    except (subprocess.SubprocessError, OSError) as err:
        print(f"Skipped paper.pdf: could not run LaTeX ({err}).")
        return False
    shutil.copyfile(tex.with_suffix(".pdf"), pdf_out)
    for ext in (".aux", ".log", ".out"):
        tex.with_suffix(ext).unlink(missing_ok=True)
    return True
