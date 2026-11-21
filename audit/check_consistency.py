"""Publication consistency check: the article, paper (HTML and, if built, PDF), report summary and README must
agree with results.json, name the author, and avoid wording the audit ruled out.

Usage:  python audit/check_consistency.py [repo_root]      (step 08 runs it after every build)
Exit code 1 if any check fails.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

BANNED = [r"\bpreregister", r"available on request", r"same conclusion", r"in preparation", r"of market value",
          r"\banalysis plan\b"]


def text_of(path: Path) -> str | None:
    if not path.exists():
        return None
    if path.suffix == ".pdf":
        if not shutil.which("pdftotext"):
            return None
        out = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
        return re.sub(r"\s+", " ", out.replace("−", "−"))
    raw = path.read_text(encoding="utf-8")
    raw = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", raw, flags=re.S)
    raw = re.sub(r'<script type="application/json"[^>]*>.*?</script>', " ", raw, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def noscript_of(path: Path) -> str | None:
    if not path.exists():
        return None
    m = re.search(r"<noscript>(.*?)</noscript>", path.read_text(encoding="utf-8"), flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))) if m else None


def main(root: Path = ROOT) -> int:
    import diagnostics as D
    import landing as L

    data_dir = root / "site" / "data"
    res = json.loads((data_dir / "results.json").read_text())
    fes = json.loads((data_dir / "firm_events.json").read_text())
    p = res["primary"]
    pA = D.estimand_tests(fes, p, draws=99)["A"]["p"]
    must = {
        "mean CAR": L.pct(p["mean_car"], 2), "interval low": L.pct(p["ci_low"], 2), "interval high": L.pct(p["ci_high"], 2),
        "standardized p": f"p = {L.pval(p['p'])}", "mean p": f"p = {L.pval(pA)}",
    }
    counts = {"independent events": f"{p['n_clusters']} independent", "reactions": str(p["n_firm_events"])}
    pages = {
        "article": text_of(root / "index.html"),
        "paper (HTML)": text_of(root / "case-study.html"),
        "paper (PDF)": text_of(root / "case-study.pdf"),
        "report summary": noscript_of(root / "site" / "index.html"),
    }
    fails, rows = [], []
    for page, txt in pages.items():
        if txt is None:
            rows.append((page, "skipped (not built or no pdftotext)", True))
            continue
        for k, v in {**must, **counts}.items():
            if page == "report summary" and k in ("mean p", "reactions"):
                continue
            ok = v in txt
            rows.append((page, f"{k}: {v}", ok))
        ok = "Nahian Ibnat" in txt or page == "report summary"
        rows.append((page, "author named", ok))
        for b in BANNED:
            hit = re.search(b, txt, re.I)
            rows.append((page, f"no '{b}'", not hit))
    readme = (root / "README.md").read_text(encoding="utf-8")
    for b in (r"\bpreregister", r"available on request"):
        rows.append(("README", f"no '{b}'", not re.search(b, readme, re.I)))
    for page, what, ok in rows:
        if not ok:
            fails.append((page, what))
    print(f"Consistency: {sum(ok for _, _, ok in rows)} of {len(rows)} checks pass.")
    for page, what in fails:
        print(f"  FAIL  {page}: {what}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
