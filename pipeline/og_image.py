"""Link-preview image (og.png, 1200 x 630) for LinkedIn and other sites. Numbers come from the exported data.

Uses matplotlib's bundled DejaVu fonts so the image is the same on every computer.
"""
from __future__ import annotations

from pathlib import Path

# Space Shock palette on navy: on-navy text, coral for losses, teal for gains, blue accent
PAPER, INK, MUTED, RULE, SIGNAL, SIGNAL_TEXT, GAIN = "#0B1B2E", "#FFFFFF", "#A9B8CA", "#2B4462", "#8DB6FF", "#FF9480", "#5EE0C8"


def make(facts: dict, out: Path, pct, pval) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    W, H, DPI = 1200, 630, 100
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=PAPER)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    sans, serif, mono = "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono"
    L, R = 70, W - 70

    ax.add_patch(Rectangle((0, 0), W, 10, color=SIGNAL))                       # countdown bar
    ax.text(L, 62, "SPACE SHOCK", family=sans, size=17, color=INK, weight="bold", va="center")
    ax.text(R, 62, "PAPER · EVENT STUDY", family=mono, size=13, color=MUTED, va="center", ha="right")
    ax.plot([L, R], [86, 86], color=RULE, lw=1.2)
    ax.text(L, 118, "When rockets fail,\nwho pays the price?", family=sans, weight="bold",
            size=46, color=INK, va="top", linespacing=1.12)

    p = facts["prim"]
    y0 = 400
    ax.plot([L, R], [y0 - 22, y0 - 22], color=RULE, lw=2)
    mid = (L + R) / 2
    ax.plot([mid, mid], [y0 - 22, y0 + 118], color=RULE, lw=1.2)
    all_fell = facts["case_hi"] is not None and facts["case_hi"] < 0
    maker = f"{pct(facts['case_hi'])} to {pct(facts['case_lo'])}" if all_fell else f"{pct(facts['case_lo'])} to {pct(facts['case_hi'])}"
    ax.text(L, y0 + 8, "THE ROCKET'S MAKER", family=mono, size=13, color=MUTED, va="top")
    ax.text(L, y0 + 36, maker, family=sans, weight="bold", size=36, color=SIGNAL_TEXT if all_fell else INK, va="top")
    ax.text(L, y0 + 92, f"two-day abnormal return, {facts['n_cases']} listed cases", family=serif, size=15, color=MUTED, va="top")

    detect = "not detectable" if p["p"] >= 0.05 else "detectable"
    ax.text(mid + 30, y0 + 8, "ITS LISTED COMPETITORS", family=mono, size=13, color=MUTED, va="top")
    ax.text(mid + 30, y0 + 36, pct(p["mean_car"], 2), family=sans, weight="bold", size=36,
            color=INK if p["p"] >= 0.05 else (GAIN if p["mean_car"] > 0 else SIGNAL_TEXT), va="top")
    ax.text(mid + 30, y0 + 92, f"average, {detect} (p = {pval(p['p'])})", family=serif, size=15, color=MUTED, va="top")

    span = f"{facts['first_year']} to {facts['last_year']}" if facts["first_year"] else ""
    ax.plot([L, R], [H - 62, H - 62], color=RULE, lw=1.2)
    ax.text(L, H - 36, f"Nahian Ibnat · {facts['n_failures']} orbital launch failures, {span}", family=mono, size=13, color=INK, va="center")
    ax.text(R, H - 36, "Interactive report and paper", family=mono, size=13, color=MUTED, va="center", ha="right")
    fig.savefig(out, dpi=DPI, facecolor=PAPER)
    plt.close(fig)
    return out
