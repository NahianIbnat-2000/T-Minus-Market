# Space Shock: UX audit and redesign (22 Nov 2026)

The project was renamed from T-Minus Markets to **Space Shock**. This is a presentation redesign only. No data,
hypotheses, event-study calculations, sample definitions, statistical results or audit history were changed.
The consistency check (56 of 56) and every test pass after the change.

## 1. Audit before the redesign (verified in the build of 22 Nov 2026)

| Area | Problem found | Evidence |
| --- | --- | --- |
| Identity | Three pages, three looks: cream archive report, separate light article theme, paper in archive style. No logo or shared header | `site/template.html`, `article-sky.css`, `casestudy.css` |
| Navigation | Each page had its own link line (byline links on the report and paper, cards on the article). No way to move between pages from a fixed place; no mobile menu | `{{NAV}}` in the template, `nav` string in `casestudy.py` |
| Homepage | Long prose; the central result needed reading 3 paragraphs; the two p-values (0.76 and 0.40) appeared without saying they test different things on first view | old `landing.article()` |
| Homepage | Sample counts in mixed units shown as a list without a picture on the page | old `landing.article()` |
| Report | Section names were countdown labels (T−3 … T+1) that a first-time visitor has to decode | `stageNav.js` |
| Report | Tools looked like the body text (thin ink box), so controls, results and explanations blended together | `components.css` `.tool` |
| Colour | Red for losses and dark blue for gains; blue also used for links and focus, so "blue" meant three things | `tokens.css`, `figures.js`, `lab.js` |
| Paper | Contents list sat in the flow; no sticky navigation on desktop; no version or status block; title differed from the project framing | `casestudy.py` |
| Paper | Scrollable tables on phones could not be reached by keyboard (axe: `scrollable-region-focusable`) | axe at 390 px |
| Report | Same issue for report tables on phones | axe at 390 px |
| Wording | One sentence in the paper used "honest uncertainty" (style rule) | `casestudy.py` |
| Build | The article was written before the PDF, so the PDF link could be missing on a first build (fixed in v27) | `08_build_html.py` |

Not a problem (checked): the Event Study Lab already labels any non-prespecified selection as exploratory and has a reset
button; the Placebo Simulator has a reset; charts already have "show the numbers" tables; the report already has a
no-JavaScript summary.

## 2. Design system

* **Tokens** (`site/src/styles/tokens.css`): light reading surface `#F7F8FA`, white cards, navy `#0B1B2E` for the header, hero and
  analytics surfaces. Coral = negative abnormal return, teal = positive, blue = benchmark, intervals and neutral information.
  Text-safe variants (`--loss-text`, `--gain-text`, `--bench-text`) pass WCAG AA on the reading surface.
* **Type**: Inter for headings and interface, Source Serif 4 for reading text, JetBrains Mono for numbers.
* **Chrome** (`site/src/styles/chrome.css`, `pipeline/sitechrome.py`): one header (logo, name, tagline, navigation with
  `aria-current`, mobile menu without JavaScript), one footer (about, links, sources, citation), buttons, badges
  (Prespecified, Exploratory, Robustness), focus ring, reduced motion.
* **Charts**: the same colour meaning in the homepage SVGs, the report (`figures.js`, `lab.js`) and the paper figures
  (`casestudy.py`, `casestudy_tex.py`).

## 3. What changed, page by page

**Homepage** (`pipeline/landing.py`, `site/src/styles/home.css`), in this order: shared header; title, subtitle, actions;
headline findings (maker range with paths; competitor average with its 95% interval, sample sizes, the undetectable range,
and both tests labelled, with a note that p = 0.40 and p = 0.76 answer different questions); plain-language interpretation
("not finding an effect is not the same as finding no effect"); contagion versus competition; sample and coverage (diagram
plus counts with units); four tool previews drawn from the real data; limitations (power, few firms, weighting table that
shows the sign change, exploratory confounding check, robustness, what an abnormal return is not); paper, data and
reproducibility; footer with citation.

**Interactive report** (`site/template.html`, `site/src/styles/report.css`, `stageNav.js`, `render.js`, `methods.js`,
`main.js`): shared header and footer; navy report hero; sticky section navigation with plain names (1 Question, 2 Failures,
3 Method, 4 Results, 5 Checks, 6 Data & methods); figures as cards; each tool as a dashboard panel (navy title bar, grouped
controls, results below); exploratory state in amber, prespecified state in blue; tables reachable by keyboard.

**Working paper** (`pipeline/casestudy.py`, `site/src/styles/casestudy.css`, `pipeline/casestudy_tex.py`): shared header
and footer; new title *When Rockets Fail: Financial Contagion and Competitive Effects in the Space Industry*; metadata
block (status, rules version, sample, formats with Download PDF); sticky contents on desktop, collapsible "Sections" on
phones and tablets; equations, figures and tables as cards; scrollable tables focusable; print and PDF unchanged in content
(the PDF header now reads Space Shock).

**Other**: preview image `og.png` in the navy identity; README; export metadata `project` field.

## 4. Verification

| Check | Result |
| --- | --- |
| Python tests (`pytest tests`) | 64 passed |
| JavaScript tests (`cd site && npm test`) | 14 passed |
| Site generation (step 08) | report, homepage, paper HTML, paper PDF, og.png all built |
| Consistency of published numbers (`audit/check_consistency.py`) | 56 of 56 |
| axe-core WCAG 2.2 A/AA on all three pages at 1280, 768 and 390 px | 0 violations |
| Horizontal overflow at 768 and 390 px | none |
| Internal links and anchors on all three pages | 0 broken |
| Scientific results | unchanged: every number is still read from `site/data/` |

`audit/verify_published.py` needs the private processed data and runs on the author's machine.

## 5. Remaining issues

* (Resolved in v30) The repository was renamed to `space-shock`; `site/site_meta.json` now points at the new address.
* The report tools do not share one selected event across tools; each keeps its own controls. A shared state would need a
  larger change to the tool code and was left out to avoid risk to the Lab's exact reproduction of the main test.
* The CRSP supplement (plan v1.2) is not yet shown on the site or in the paper.


---

# Second pass (v30, 22 Nov 2026): information architecture

## Audit: verified issues (checked in a real browser at 375, 768, 1280 and 1440 px)

| Issue | Verified how | Fix |
| --- | --- | --- |
| "Data & methods" in the navigation went to a section at the end of the report, not a methods destination | link target `site/index.html#methods` | New page `methods.html`; the report section now points to it |
| Citations, canonical and og:url used the old `/T-Minus-Market/` address | `site_meta.json`, generated pages | `live_url` and `repo_url` now point to `space-shock`; `audit/check_site.py` fails on old URLs |
| Navigation had six items mixing pages, a download and an external link; the mobile menu repeated the same links in a second `<nav>` | page source | Four destinations (Overview, Explore Data, Research Paper, Data & Methods) in one `<nav>`, which becomes a scrollable row on small screens; PDF and code moved to the footer |
| The overview carried method detail (sample diagram, unit definitions, weighting table, robustness text) | page length 5,167 px at 1280 | Five sections; details moved to `methods.html` |
| The competitor estimate was shown in teal (the "gain" colour) in the Event Study Lab although it is not significant | screenshot | The number is coloured only when the test rejects |
| Corrupt or incomplete report data gave a technical message, and the run line kept saying "Loading" | browser test with a broken data block | Data are validated and missing parts named; visitor-facing message with links; `site/tests/data_validate.test.mjs` |
| Paper source links were written even when the source was not a URL (test fixture) | `check_site.py` | Only `http` sources are linked |

## Checked and not a defect

* **Report loading.** Data are embedded in the page, so there is no request that can fail under the Pages base path. The
  loading line is replaced on success; nine charts render; a direct link to `site/index.html#lab` lands on the tool;
  browser back and forward work between pages. The only console message in testing was the font request blocked by the
  test machine's network.
* **Paper Contents / Sections.** Both exist so the table of contents can be a sticky sidebar on desktop and a collapsible
  list on phones. At every width exactly one is displayed; the other has `display: none`, which also removes it from the
  accessibility tree.

## Information architecture

| Destination | File | Purpose |
| --- | --- | --- |
| Overview | `index.html` | Question, hypotheses, four key-finding cards, two charts, tool previews, what the evidence can and cannot show, resources |
| Explore Data | `site/index.html` | The four tools in sections 1 to 5; section 6 points to Data & Methods |
| Research Paper | `case-study.html` (+ PDF) | The full study |
| Data & Methods | `methods.html` | Sources, sample definitions, event timing, firm classification, model and windows, inference (including why p = 0.40 and the mean-test p differ), robustness, data quality, replication |

## Automated checks added

`audit/check_site.py` (run by step 08 and by `tests/test_phase4_single_file.py`): pages exist and have titles; every
relative link and anchor resolves; no root-absolute paths; no old project URL; canonical and og:url use the live address;
navigation has unique destinations and labels, one current page and a single `<nav>`; every inline SVG has an accessible
name or is hidden. A planted broken link, absolute path and old URL are caught (test).

## Old links

`python pipeline/make_redirects.py` writes `redirect/T-Minus-Market/`: pages that forward the old Pages addresses
(overview, report, paper, methods, 404) to `space-shock`, keeping `#anchors`. Publish them in a new repository named
`T-Minus-Market` with GitHub Pages on.

## Results of this pass

Python tests 67 passed; JavaScript tests 16 passed; consistency 56 of 56; site structure check passes; axe-core WCAG 2.2
A/AA: 0 violations on all four pages at 375, 768, 1280 and 1440 px; no page-level horizontal overflow.
`audit/verify_published.py` needs the private data and is run on the author's machine.

## Remaining limitations

* Expected vs Actual uses a simulated stock. Real expected and actual returns need prices that may not be republished.
* Tools keep separate controls; there is no shared event selection across tools.
* Some sample-diagram unit labels run slightly past their box at the smallest sizes.
* The CRSP supplement (plan v1.2) is not shown on the site or in the paper.
