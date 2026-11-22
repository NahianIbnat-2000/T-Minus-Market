"""Shared header, navigation and footer for the three public pages (homepage, report, paper).

`prefix` is the path from the page to the site root ("" for root pages, "../" for site/index.html)."""
from __future__ import annotations

import html

e = html.escape
BRAND = "Space Shock"
TAGLINE = "When rockets fail, who pays the price?"
SUBTITLE = "Financial contagion and competition in the space industry"
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
    items = [("home", "Home", f"{prefix}index.html"), ("report", "Interactive report", f"{prefix}site/index.html"),
             ("paper", "Working paper", f"{prefix}case-study.html"), ("methods", "Data & methods", f"{prefix}site/index.html#methods")]
    if repo:
        items.append(("code", "Code", repo))
    if pdf:
        items.append(("pdf", "Download PDF", f"{prefix}case-study.pdf"))
    return items


def header(active: str, prefix: str = "", pdf: bool = True, repo: str | None = None) -> str:
    def link(k, label, href):
        cur = ' aria-current="page"' if k == active else ""
        dl = ' download class="ss-dl"' if k == "pdf" else ""
        return f'<li><a href="{e(href)}"{cur}{dl}>{e(label)}</a></li>'
    items = "".join(link(*i) for i in nav_items(prefix, pdf, repo))
    return (f'<header class="ss-header"><div class="ss-row">'
            f'<a class="ss-logo" href="{e(prefix)}index.html">{LOGO}<span><span class="ss-name">SPACE <b>SHOCK</b></span>'
            f'<span class="ss-sub">{e(SUBTITLE)}</span></span></a>'
            f'<nav class="ss-nav" aria-label="Site"><ul>{items}</ul></nav>'
            f'<details class="ss-menu"><summary aria-label="Open site menu">Menu</summary><nav aria-label="Site (menu)"><ul>{items}</ul></nav></details>'
            f'</div></header>')


def footer(prefix: str = "", meta: dict | None = None, pdf: bool = True, cite: str = "") -> str:
    meta = meta or {}
    repo = meta.get("repo_url")
    links = "".join(f'<li><a href="{e(h)}"{" download" if k == "pdf" else ""}>{e(l)}</a></li>' for k, l, h in nav_items(prefix, pdf, repo))
    return (f'<footer class="ss-footer"><div class="ss-fgrid">'
            f'<div><h2>{e(BRAND)}</h2><p>{e(SUBTITLE)}. An event study of orbital launch failures and the stocks of the companies involved.</p>'
            f'<p>By {e(meta.get("author", "Nahian Ibnat"))}</p></div>'
            f'<div><h2>Explore</h2><ul>{links}</ul></div>'
            f'<div><h2>Sources</h2><p>Launch data: GCAT, J. McDowell, CC-BY. Prices: Yahoo Finance, used only to compute statistics; no prices are republished.</p></div>'
            f'<div><h2>Cite</h2><p>{e(cite)}</p></div>'
            f'</div><p class="ss-legal">Independent research, not peer reviewed. Not investment advice.</p></footer>')
