"""Step 08: build the whole website as ONE self-contained file, site/index.html.

Inlines into site/template.html:
  - the styles      (site/src/styles/*.css)
  - the code        (site/src/**/*.js, starting from src/main.js; each file keeps its own scope)
  - the data        (site/data/*.json, written by step 07: derived statistics only)

The result opens by double-click, works offline (fonts fall back to system fonts) and can be
hosted anywhere as a single file. No npm, no build server.

Usage:  python pipeline/08_build_html.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SRC = SITE / "src"
STYLES = ["tokens.css", "base.css", "components.css", "chrome.css", "report.css"]
DATA_FILES = {"manifest": "manifest.json", "results": "results.json", "firmEvents": "firm_events.json",
              "failures": "failures.json", "rho": "rho.json"}

IMPORT_RE = re.compile(r'^\s*import\s+(?:(\{[^}]*\})|\*\s+as\s+(\w+)|(\w+))?\s*(?:from\s*)?["\']([^"\']+)["\'];?\s*$', re.M)
EXPORT_RE = re.compile(r"^export\s+(async\s+function|function|const|let|class)\s+(\w+)", re.M)


def _mod_name(path: Path) -> str:
    return "__m_" + re.sub(r"\W", "_", str(path.relative_to(SRC)).removesuffix(".js"))


def bundle(entry: Path) -> str:
    """Tiny module bundler for this project's code (named imports, namespace imports, named exports)."""
    order: list[Path] = []
    seen: set[Path] = set()
    parsed: dict[Path, tuple[str, list]] = {}

    def visit(p: Path, stack=()):
        p = p.resolve()
        if p in stack:
            raise ValueError(f"circular import: {' -> '.join(map(str, stack + (p,)))}")
        if p in seen:
            return
        code = p.read_text(encoding="utf-8")
        imports = []
        for m in IMPORT_RE.finditer(code):
            names, star, default, spec = m.groups()
            if spec.endswith(".css"):
                continue
            if not spec.startswith("."):
                raise ValueError(f"{p.name}: external import '{spec}' is not allowed in the single-file build")
            dep = (p.parent / spec).resolve()
            imports.append((names, star, default, dep))
            visit(dep, stack + (p,))
        seen.add(p)
        parsed[p] = (code, imports)
        order.append(p)

    visit(entry)
    out = []
    for p in order:
        code, imports = parsed[p]
        body = IMPORT_RE.sub("", code)
        exports = [m.group(2) for m in EXPORT_RE.finditer(body)]
        body = EXPORT_RE.sub(lambda m: f"{m.group(1)} {m.group(2)}", body)
        if re.search(r"^\s*export\s", body, re.M):
            raise ValueError(f"{p.name}: unsupported export form")
        head = []
        for names, star, default, dep in imports:
            if star:
                head.append(f"const {star} = {_mod_name(dep)};")
            elif names:
                inner = ", ".join(
                    (f"{a.strip()}: {b.strip()}" if b else a.strip())
                    for a, _, b in (n.strip().partition(" as ") for n in names.strip("{} \n").split(",") if n.strip()))
                head.append(f"const {{ {inner} }} = {_mod_name(dep)};")
            elif default:
                raise ValueError(f"{p.name}: default imports are not supported")
        out.append(f"// ---- {p.relative_to(SRC)}\nconst {_mod_name(p)} = (() => {{\n" + "\n".join(head) + "\n"
                   + body.strip() + f"\nreturn {{ {', '.join(exports)} }};\n}})();")
    return '"use strict";\n' + "\n".join(out)


def build_pages(site_data: Path = SITE / "data", root_out: Path = ROOT) -> list[Path]:
    """Root article (index.html), working paper (case-study.html/.pdf) and preview image for GitHub Pages."""
    import landing
    data = {k: json.loads((site_data / f).read_text(encoding="utf-8")) for k, f in DATA_FILES.items()}
    meta = json.loads((SITE / "site_meta.json").read_text(encoding="utf-8"))
    css = "\n".join((SRC / "styles" / f).read_text(encoding="utf-8") for f in STYLES + ["home.css"])
    a = root_out / "index.html"
    (root_out / "plan.html").unlink(missing_ok=True)            # the plan page is no longer published
    (root_out / ".nojekyll").touch()
    out = [a]
    cs_css = "\n".join((SRC / "styles" / f).read_text(encoding="utf-8") for f in STYLES + ["landing.css", "casestudy.css"])
    import casestudy
    import casestudy_tex
    pdf, cs = root_out / "case-study.pdf", root_out / "case-study.html"
    has_tex = casestudy_tex.find_engine() is not None
    html_cs = casestudy.build(data, meta, ROOT, cs_css, pdf.name if (has_tex or pdf.exists()) else None)
    cs.write_text(html_cs, encoding="utf-8")
    out.append(cs)
    try:
        tex = casestudy_tex.build_tex(html_cs, data, meta, root_out / "casestudy")
        out.append(tex)
        if casestudy_tex.compile_pdf(tex, pdf):
            out.append(pdf)
    except ImportError:
        print("Skipped the LaTeX case study: run  pip install matplotlib  first (it draws the figures).")
    # the article is written after the PDF, so its "Download PDF" link reflects this build
    a.write_text(landing.article(data, meta, root_out, css), encoding="utf-8")
    try:                                            # link-preview image; optional
        import og_image
        out.append(og_image.make(landing.facts(data), root_out / "og.png", landing.pct, landing.pval))
    except ImportError:
        print("Skipped og.png (link-preview image): run  pip install matplotlib  to make it.")
    return out


def static_summary(data: dict) -> str:
    """Key results as plain HTML, shown when JavaScript is off (the interactive report needs it)."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import landing as L
    f = L.facts(data)
    p, e = f["prim"], L.e
    rows = "".join(f"<tr><td>{e(c['vehicle'])}, {e(L.day(c['day0']))}</td><td>{e(c['firm'])}</td><td>{e(L.pct(c['car_primary']))}</td></tr>"
                   for c in data["results"].get("provider_case_series") or [])
    return (f"<h2>Key results (static summary)</h2><p>This interactive report needs JavaScript for its charts and tools. "
            f"The full text is in the <a href=\"../case-study.html\">working paper</a> and the <a href=\"../index.html\">article</a>.</p>"
            f"<p>Listed competitors: average two-day abnormal return {e(L.pct(p['mean_car'], 2))} (95% interval {e(L.pct(p['ci_low'], 2))} to "
            f"{e(L.pct(p['ci_high'], 2))}" + (f", p = {e(L.pval(f['pA']))}" if f.get("pA") is not None else "")
            + f"; prespecified standardized test p = {e(L.pval(p['p']))}), from {p['n_failures']} failures, {p['n_firms']} firms and "
            f"{p['n_clusters']} independent events.</p>"
            f"<table><caption>The rocket's maker: two-day abnormal return</caption><thead><tr><th>Failure</th><th>Listed maker</th>"
            f"<th>CAR T0 to T+1</th></tr></thead><tbody>{rows}</tbody></table>")


def build(site_data: Path = SITE / "data", out: Path = SITE / "index.html") -> Path:
    missing = [f for f in DATA_FILES.values() if not (site_data / f).exists()]
    if missing:
        raise SystemExit(f"Missing {missing} in {site_data}. Run pipeline/07_export_site_data.py first.")
    data = {k: json.loads((site_data / f).read_text(encoding="utf-8")) for k, f in DATA_FILES.items()}
    data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    style = "\n".join((SRC / "styles" / f).read_text(encoding="utf-8") for f in STYLES)
    script = bundle(SRC / "main.js").replace("</script", "<\\/script")
    info = f"built {datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    noscript = static_summary(data)
    meta = json.loads((SITE / "site_meta.json").read_text(encoding="utf-8"))
    import sitechrome as SC
    pdf = (ROOT / "case-study.pdf").exists() or bool(shutil.which("xelatex") or shutil.which("pdflatex"))
    header = SC.header("report", "../", pdf, meta.get("repo_url"))
    year = str(data["manifest"].get("results_run_utc", ""))[:4]
    footer = SC.footer("../", meta, pdf, f"Ibnat, N. ({year}). {SC.PAPER_TITLE}. Space Shock working paper.")
    html = (SITE / "template.html").read_text(encoding="utf-8")
    for key, val in (("{{STYLE}}", style), ("{{DATA}}", data_json), ("{{SCRIPT}}", script), ("{{BUILD_INFO}}", info),
                     ("{{NOSCRIPT}}", noscript), ("{{HEADER}}", header), ("{{FOOTER}}", footer), ("{{FONTS}}", SC.FONTS)):
        if key not in html:
            raise ValueError(f"template is missing {key}")
        html = html.replace(key, val)
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    p = build()
    print(f"Wrote {p.relative_to(ROOT)} ({p.stat().st_size / 1024:.0f} kB): the interactive report.")
    for q in build_pages():
        print(f"Wrote {q.relative_to(ROOT)} ({q.stat().st_size / 1024:.0f} kB).")
    try:                                             # article, paper and report must agree with results.json
        spec = importlib.util.spec_from_file_location("consistency", ROOT / "audit" / "check_consistency.py")
        chk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(chk)
        chk.main(ROOT)
    except FileNotFoundError:
        pass
    print("Open index.html (the article) in any browser.")
