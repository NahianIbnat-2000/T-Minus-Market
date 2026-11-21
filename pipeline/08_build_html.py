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

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
SRC = SITE / "src"
STYLES = ["tokens.css", "base.css", "components.css"]
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


def build(site_data: Path = SITE / "data", out: Path = SITE / "index.html") -> Path:
    missing = [f for f in DATA_FILES.values() if not (site_data / f).exists()]
    if missing:
        raise SystemExit(f"Missing {missing} in {site_data}. Run pipeline/07_export_site_data.py first.")
    data = {k: json.loads((site_data / f).read_text(encoding="utf-8")) for k, f in DATA_FILES.items()}
    data_json = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    style = "\n".join((SRC / "styles" / f).read_text(encoding="utf-8") for f in STYLES)
    script = bundle(SRC / "main.js").replace("</script", "<\\/script")
    info = f"built {datetime.now(timezone.utc).isoformat(timespec='seconds')}, plan v{data['manifest'].get('plan_version')}"
    html = (SITE / "template.html").read_text(encoding="utf-8")
    for key, val in (("{{STYLE}}", style), ("{{DATA}}", data_json), ("{{SCRIPT}}", script), ("{{BUILD_INFO}}", info)):
        if key not in html:
            raise ValueError(f"template is missing {key}")
        html = html.replace(key, val)
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    p = build()
    print(f"Wrote {p.relative_to(ROOT)} ({p.stat().st_size / 1024:.0f} kB). Open it in any browser.")
