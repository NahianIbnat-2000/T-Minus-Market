"""Redirect pages for the old GitHub Pages address (…/T-Minus-Market/) after the rename to space-shock.

GitHub redirects the renamed repository, but not its old Pages address. Publishing these files in a new repository
called T-Minus-Market (GitHub Pages on, branch main, root) keeps old shared links working.

Usage:  python pipeline/make_redirects.py      -> writes redirect/T-Minus-Market/
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# old path on /T-Minus-Market/ -> new path on /space-shock/
PAGES = {"index.html": "", "site/index.html": "site/index.html", "case-study.html": "paper.html",
         "methods.html": "methods.html", "404.html": ""}


def page(target: str) -> str:
    t = html.escape(target)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Moved · Space Shock</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{t}">
<meta http-equiv="refresh" content="0; url={t}">
<script>location.replace({json.dumps(target)} + location.hash);</script>
</head><body>
<p>This page has moved to <a href="{t}">{t}</a>.</p>
</body></html>
"""


def main(out: Path = ROOT / "redirect" / "T-Minus-Market") -> list[Path]:
    meta = json.loads((ROOT / "site" / "site_meta.json").read_text(encoding="utf-8"))
    base = meta["live_url"].rstrip("/") + "/"
    written = []
    for rel, new in PAGES.items():
        target = base + new
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(page(target), encoding="utf-8")
        written.append(p)
    (out / ".nojekyll").touch()
    (out / "README.md").write_text(f"# T-Minus-Market (moved)\n\nThis project is now Space Shock: {base}\n", encoding="utf-8")
    return written


if __name__ == "__main__":
    for p in main():
        print(f"Wrote {p.relative_to(ROOT)}")
