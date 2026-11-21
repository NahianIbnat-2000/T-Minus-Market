"""Phase 4: the single-file builder (step 08) produces a correct, self-contained index.html."""
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import config as C
from test_phase3_parity import make_world

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "pipeline"
NODE = shutil.which("node")


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, PIPE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("p4")
    make_world(root)
    mp = pytest.MonkeyPatch()
    for attr, sub in [("INTERIM", "interim"), ("PROCESSED", "processed"), ("REPORTS", "reports"), ("MANUAL", "manual")]:
        mp.setattr(C, attr, root / sub)
    (root / "reports").mkdir()
    mp.setattr(sys, "argv", ["05", "--quick"])
    _load("s5", "05_event_study.py").main()
    _load("s7", "07_export_site_data.py").main(site_data=root / "site_data")
    out = _load("s8", "08_build_html.py").build(site_data=root / "site_data", out=root / "index.html")
    yield root, out.read_text(encoding="utf-8")
    mp.undo()


def test_placeholders_filled_and_no_module_syntax_left(built):
    _, html = built
    for key in ("{{STYLE}}", "{{DATA}}", "{{SCRIPT}}", "{{BUILD_INFO}}"):
        assert key not in html
    script = html.split("<script>")[1].split("</script>")[0]
    assert not re.search(r"^\s*(import|export)\s", script, re.M)
    for mod in ["format", "stats_eventstudy", "components_figures", "sections_render", "sections_methods", "main"]:
        assert f"const __m_{mod} = " in script


def test_data_is_embedded_and_identical(built):
    root, html = built
    blob = html.split('id="site-data">')[1].split("</script>")[0].replace("<\\/", "</")
    data = json.loads(blob)
    assert data["results"] == json.loads((root / "site_data" / "results.json").read_text())
    assert len(data["firmEvents"]) == len(json.loads((root / "site_data" / "firm_events.json").read_text()))


def test_no_external_scripts(built):
    _, html = built
    assert "<script src" not in html and "d3" not in html.split("<script>")[1][:2000].lower()


@pytest.mark.skipif(NODE is None, reason="Node.js not installed")
def test_inline_script_parses(built, tmp_path):
    _, html = built
    js = html.split("<script>")[1].split("</script>")[0]
    (tmp_path / "s.js").write_text(js, encoding="utf-8")
    subprocess.run([NODE, "-e", "new Function(require('fs').readFileSync(process.argv[1],'utf8'))", str(tmp_path / "s.js")],
                   check=True)


def test_article_and_plan_pages(built, tmp_path):
    root, _ = built
    s8 = _load("s8b", "08_build_html.py")
    a, p = s8.build_pages(site_data=root / "site_data", root_out=tmp_path)[:2]
    art, plan = a.read_text(encoding="utf-8"), p.read_text(encoding="utf-8")
    assert (tmp_path / ".nojekyll").exists()
    assert 'href="site/index.html"' in art and 'href="plan.html"' in art and "<script" not in art
    assert 'property="og:title"' in art and "Nahian Ibnat" in art
    res = json.loads((root / "site_data" / "results.json").read_text())
    import landing
    assert landing.pct(res["primary"]["mean_car"], 2) in art           # number comes from results.json
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<style>.*?</style>", "", art, flags=re.S))
    assert not re.search(r"\bNone\b(?! of)|\bnan\b", text)         # "None of the 12 checks" is prose
    assert "<table>" in plan and "Change log" in plan


def test_preview_image(built, tmp_path):
    pytest.importorskip("matplotlib")
    root, _ = built
    out = _load("s8c", "08_build_html.py").build_pages(site_data=root / "site_data", root_out=tmp_path)
    png = tmp_path / "og.png"
    assert png in out and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_case_study_page(built, tmp_path):
    root, _ = built
    outs = _load("s8d", "08_build_html.py").build_pages(site_data=root / "site_data", root_out=tmp_path)
    cs = (tmp_path / "case-study.html").read_text(encoding="utf-8")
    assert tmp_path / "case-study.html" in outs
    for heading in ["Abstract", "1. Introduction", "2. Institutional background", "3. Related literature", "4. Data and sample construction",
                    "5. Empirical methodology", "6. Main results", "7. Robustness and sensitivity", "8. Confounding news",
                    "9. Discussion", "10. Limitations", "11. Conclusion", "References", "Appendix A", "Appendix F"]:
        assert heading in cs
    import landing
    res = json.loads((root / "site_data" / "results.json").read_text())
    assert landing.pct(res["primary"]["mean_car"], 2) in cs                 # numbers come from results.json
    assert cs.count("<svg") >= 3 and "<script" not in cs
    text = re.sub(r"<[^>]+>", " ", re.sub(r"<(style|svg)[^>]*>.*?</\1>", "", cs, flags=re.S))
    assert not re.search(r"\b(nan)\b|[{}]", text)
    assert "Preregistered" not in cs and "same conclusion" not in cs                   # audit wording fixes stay fixed
    art = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Preregistered" not in art and "on request" not in art and "same conclusion" not in art
    assert 'href="case-study.html"' in art


def test_case_study_latex(built, tmp_path):
    pytest.importorskip("matplotlib")
    root, _ = built
    _load("s8e", "08_build_html.py").build_pages(site_data=root / "site_data", root_out=tmp_path)
    tex = (tmp_path / "casestudy" / "case-study.tex").read_text(encoding="utf-8")
    assert r"\documentclass[12pt,a4paper]{article}" in tex and "Times New Roman" in tex
    assert "Economics and Data Science" not in tex and "claude.ai" not in tex
    assert "case-study.pdf" not in tex                     # the PDF does not link to itself
    figs = sorted(p.name for p in (tmp_path / "casestudy").glob("fig-*.pdf"))
    assert "fig-years.pdf" in figs and "fig-forest.pdf" in figs     # always drawn; others depend on the data
    assert all(f"{{{f}}}" in tex for f in figs)                     # every drawn figure is used
    if shutil.which("xelatex") or shutil.which("pdflatex"):
        assert (tmp_path / "case-study.pdf").read_bytes()[:5] == b"%PDF-"
