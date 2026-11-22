"""Structural checks of the built website (run after step 08; step 08 runs it too).

Checks, for the four public pages:
  * the page exists and has a non-empty <title>;
  * every relative link resolves to a file in the build, and every #anchor exists on the target page
    (for the interactive report, anchors are taken from the template and the report source, because the report is
    rendered by JavaScript);
  * no root-absolute links ("/x"), which break under the GitHub Pages project path;
  * no outdated project URL (the old /T-Minus-Market/ address or the old repository) in generated pages;
  * canonical and og:url point at the configured live address;
  * the site navigation has no duplicate destinations or labels, and marks exactly one page as current;
  * every inline SVG either has an accessible name (role="img" with aria-label) or is hidden from assistive technology.

Usage: python audit/check_site.py   (exit code 1 on any failure)
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "site/index.html", "case-study.html", "methods.html"]
OUTDATED = [r"github\.io/T-Minus-Market", r"github\.com/NahianIbnat-2000/T-Minus-Market\b"]


def _ids(text: str) -> set[str]:
    return set(re.findall(r'\bid="([^"]+)"', text))


def _report_ids(root: Path) -> set[str]:
    ids = _ids((root / "site" / "template.html").read_text(encoding="utf-8")) if (root / "site" / "template.html").exists() else set()
    for js in (root / "site" / "src").rglob("*.js") if (root / "site" / "src").exists() else []:
        src = js.read_text(encoding="utf-8")
        ids |= set(re.findall(r'\bid="([A-Za-z][\w+-]*)"', src))
        ids |= set(re.findall(r'\bid: "([A-Za-z][\w+-]*)"', src))           # STAGES entries
    return ids


def check(root: Path = ROOT) -> list[tuple[str, str, bool]]:
    rows = []
    meta_path = root / "site" / "site_meta.json"
    if not meta_path.exists():
        meta_path = ROOT / "site" / "site_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    live = (meta.get("live_url") or "").rstrip("/") + "/"
    texts = {p: (root / p).read_text(encoding="utf-8") for p in PAGES if (root / p).exists()}
    for p in PAGES:
        rows.append((p, "page exists", p in texts))
    report_ids = _report_ids(root) | _ids(texts.get("site/index.html", ""))
    for page, txt in texts.items():
        body = re.sub(r"<script\b[^>]*>.*?</script>", " ", txt, flags=re.S)
        m = re.search(r"<title>(.*?)</title>", txt, flags=re.S)
        rows.append((page, "has a title", bool(m and m.group(1).strip())))
        base = (root / page).parent
        for href in re.findall(r'href="([^"]+)"', body):
            href = html.unescape(href)
            if re.match(r"^(https?:|mailto:|data:)", href):
                continue
            if href.startswith("/"):
                rows.append((page, f"root-absolute link {href}", False))
                continue
            path, _, frag = href.partition("#")
            target = (base / path).resolve() if path else (root / page).resolve()
            ok = target.exists()
            if ok and frag:
                rel = target.relative_to(root.resolve()).as_posix() if target.is_relative_to(root.resolve()) else ""
                ids = report_ids if rel == "site/index.html" else _ids(texts.get(rel, target.read_text(encoding="utf-8", errors="ignore")
                                                                                      if target.suffix == ".html" else ""))
                ok = frag in ids
            if not ok:
                rows.append((page, f"broken link {href}", False))
        for pat in OUTDATED:
            rows.append((page, f"no outdated URL /{pat}/", not re.search(pat, body)))
        for tag in ("canonical", "og:url"):
            mm = re.search(r'<link rel="canonical" href="([^"]+)"' if tag == "canonical" else r'property="og:url" content="([^"]+)"', txt)
            if mm:
                rows.append((page, f"{tag} uses the live address", mm.group(1).startswith(live)))
        cite = re.search(r"<h2>Cite</h2><p>(.*?)</p>", txt, flags=re.S)
        if cite:
            rows.append((page, "citation names the paper and the live address", "Space Shock working paper" in cite.group(1) and live in cite.group(1)))
        expected_nav = ["Overview", "Explore Data", "Research Paper", "Data &amp; Methods"]
        nav = re.search(r'<nav class="ss-nav"[^>]*>(.*?)</nav>', txt, flags=re.S)
        if nav:
            got = re.findall(r">([^<]+)</a>", nav.group(1))
            rows.append((page, "navigation is Overview | Explore Data | Research Paper | Data & Methods", got == expected_nav))
            dest = dict(zip(got, re.findall(r'href="([^"]+)"', nav.group(1))))
            pre = "../" if page.startswith("site/") else ""
            want = {"Overview": pre + "index.html", "Explore Data": pre + "site/index.html", "Research Paper": pre + "case-study.html",
                    "Data &amp; Methods": pre + "methods.html"}
            rows.append((page, "navigation destinations are the four pages", dest == want))
        if nav:
            links = re.findall(r'<a href="([^"]+)"([^>]*)>([^<]+)</a>', nav.group(1))
            hrefs, labels = [h for h, _, _ in links], [l for _, _, l in links]
            rows.append((page, "navigation destinations are unique", len(set(hrefs)) == len(hrefs)))
            rows.append((page, "navigation labels are unique", len(set(labels)) == len(labels)))
            rows.append((page, "exactly one current page in navigation", sum('aria-current="page"' in a for _, a, _ in links) == 1))
            rows.append((page, "one site navigation", len(re.findall(r'<nav class="ss-nav"', txt)) == 1))
        for svg in re.findall(r"<svg\b[^>]*>", body):
            named = 'role="img"' in svg and "aria-label=" in svg
            hidden = 'aria-hidden="true"' in svg
            if not (named or hidden):
                rows.append((page, f"SVG without accessible name: {svg[:60]}", False))
    return rows


def main(root: Path = ROOT) -> int:
    rows = check(root)
    fails = [r for r in rows if not r[2]]
    print(f"Site structure: {len(rows) - len(fails)} of {len(rows)} checks pass.")
    for page, what, _ in fails:
        print(f"  FAIL  {page}: {what}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
