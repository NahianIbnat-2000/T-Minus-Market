"""Shared header, navigation and footer for the three public pages (homepage, report, paper).

`prefix` is the path from the page to the site root ("" for root pages, "../" for site/index.html)."""
from __future__ import annotations

import html

e = html.escape
BRAND = "Space Shock"
TAGLINE = "When rockets fail, who pays the price?"
SUBTITLE = "Financial contagion and competitive effects of rocket launch failures"
PAPER_TITLE = "When Rockets Fail: Financial Contagion and Competitive Effects in the Space Industry"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800'
         '&family=JetBrains+Mono:wght@400;500&family=Source+Serif+4:ital,opsz,wght@0,8..60,400..700;1,8..60,400&display=swap">')

# original mark: a planet with an orbit and a falling stage
LOGO = ('<svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
        '<circle cx="16" cy="16" r="7" fill="none" stroke="#8DB6FF" stroke-width="2.2"/>'
        '<ellipse cx="16" cy="16" rx="14" ry="5.5" fill="none" stroke="#8DB6FF" stroke-width="1.6" transform="rotate(-28 16 16)"/>'
        '<circle cx="27.2" cy="9.4" r="2.4" fill="#FF9480"/></svg>')


def nav_items(prefix: str, pdf: bool, repo: str | None):
    """Primary navigation: four destinations, each with one purpose."""
    return [("home", "Overview", f"{prefix}index.html"), ("report", "Explore Data", f"{prefix}site/index.html"),
            ("paper", "Research Paper", f"{prefix}case-study.html"), ("methods", "Data & Methods", f"{prefix}methods.html")]


def extra_items(prefix: str, pdf: bool, repo: str | None):
    """Secondary links (footer only)."""
    items = []
    if pdf:
        items.append(("pdf", "Download PDF", f"{prefix}case-study.pdf"))
    if repo:
        items.append(("code", "Source code", repo))
    return items


def cite(year: str, meta: dict) -> str:
    url = meta.get("live_url") or ""
    return f"Ibnat, N. ({year}). {PAPER_TITLE}. Space Shock working paper." + (f" {url}" if url else "")


def header(active: str, prefix: str = "", pdf: bool = True, repo: str | None = None) -> str:
    def link(k, label, href):
        cur = ' aria-current="page"' if k == active else ""
        return f'<li><a href="{e(href)}"{cur}>{e(label)}</a></li>'
    items = "".join(link(*i) for i in nav_items(prefix, pdf, repo))
    return (f'<header class="ss-header"><div class="ss-row">'
            f'<a class="ss-logo" href="{e(prefix)}index.html">{LOGO}<span><span class="ss-name">SPACE <b>SHOCK</b></span>'
            f'<span class="ss-sub">{e(SUBTITLE)}</span></span></a>'
            f'<nav class="ss-nav" aria-label="Site"><ul>{items}</ul></nav>'
            f'</div></header>')


def footer(prefix: str = "", meta: dict | None = None, pdf: bool = True, cite: str = "") -> str:
    meta = meta or {}
    repo = meta.get("repo_url")
    links = "".join(f'<li><a href="{e(h)}"{" download" if k == "pdf" else ""}>{e(l)}</a></li>'
                    for k, l, h in nav_items(prefix, pdf, repo) + extra_items(prefix, pdf, repo))
    return (f'<footer class="ss-footer"><div class="ss-fgrid">'
            f'<div><h2>{e(BRAND)}</h2><p>{e(SUBTITLE)}. An event study of orbital launch failures and the stocks of the companies involved.</p>'
            f'<p>By {e(meta.get("author", "Nahian Ibnat"))}</p></div>'
            f'<div><h2>Explore</h2><ul>{links}</ul></div>'
            f'<div><h2>Sources</h2><p>Launch data: GCAT, J. McDowell, CC-BY. Prices: Yahoo Finance, used only to compute statistics; no prices are republished.</p></div>'
            f'<div><h2>Cite</h2><p>{e(cite)}</p></div>'
            f'</div><p class="ss-legal">Independent research, not peer reviewed. Not investment advice.</p></footer>')


# Highlights the current section in a page's table of contents (paper and methods pages). Progressive enhancement:
# without JavaScript the contents still work as plain links.
TOC_SCRIPT = """<script>
(function () {
  var links = Array.prototype.slice.call(document.querySelectorAll(".paper-toc a[href^='#'], .toc-mobile a[href^='#']"));
  if (!links.length) return;
  var ids = [], seen = {};
  links.forEach(function (a) { var id = a.getAttribute("href").slice(1); if (!seen[id]) { seen[id] = 1; ids.push(id); } });
  var secs = ids.map(function (id) { return document.getElementById(id); }).filter(Boolean);
  var current = null, ticking = false;
  function update() {
    ticking = false;
    var line = Math.max(180, window.innerHeight * 0.3), id = secs.length ? secs[0].id : null;
    secs.forEach(function (el) { if (el.getBoundingClientRect().top <= line) id = el.id; });
    if (id === current) return;
    current = id;
    links.forEach(function (a) { if (a.getAttribute("href") === "#" + id) a.setAttribute("aria-current", "location"); else a.removeAttribute("aria-current"); });
  }
  window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  window.addEventListener("hashchange", update);
  window.addEventListener("load", function () { setTimeout(update, 50); });
  update();
})();
</script>"""
