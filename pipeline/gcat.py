"""Helpers for reading GCAT launch lists.

Field meanings follow the GCAT documentation:
  https://planet4589.org/space/gcat/web/launch/lcols.html
  https://www.planet4589.org/space/gcat/web/intro/success.html
"""
from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

import pandas as pd

_CODE_RE = re.compile(r"^([A-Z])([A-Z])(\d{2})?$")


def parse_launch_code(code) -> dict:
    """Split a GCAT LaunchCode such as 'OS', 'OF', 'OS85', 'OF40', 'OE'.

    Returns category letter, result letter and a success score in [0, 1]
    (None when the result is unknown or the code is not a launch).
    """
    out = {"category": None, "result": None, "score": None, "code_ok": False}
    if not isinstance(code, str):
        return out
    m = _CODE_RE.match(code.strip())
    if not m:
        return out
    cat, res, digits = m.groups()
    out.update(category=cat, result=res, code_ok=True)
    if digits is not None:
        out["score"] = int(digits) / 100.0
    elif res == "S":
        out["score"] = 1.0
    elif res == "F":
        out["score"] = 0.0
    return out


def jd_to_utc(jd) -> pd.Timestamp | None:
    """Julian Date (UTC) to a timezone-aware UTC timestamp."""
    try:
        jd = float(jd)
    except (TypeError, ValueError):
        return None
    return pd.Timestamp(jd - 2440587.5, unit="D", tz="UTC").round("s")


_VAGUE_RE = re.compile(r"^(\d{4})\s+([A-Za-z]{3})\s+(\d{1,2})(?:\s+(\d{2})(\d{2})(?::(\d{2}))?)?")
_MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def vague_date_to_utc(text) -> pd.Timestamp | None:
    """Parse a GCAT vague date such as '2014 Oct 28 2222:38' (UTC).

    Returns None when the time of day is missing or marked uncertain ('?'),
    so the caller can fall back to Launch_JD.
    """
    if not isinstance(text, str) or "?" in text:
        return None
    m = _VAGUE_RE.match(text.strip())
    if not m or m.group(4) is None:
        return None
    y, mon, d, hh, mm, ss = m.groups()
    if mon.title() not in _MONTHS:
        return None
    return pd.Timestamp(int(y), _MONTHS[mon.title()], int(d), int(hh), int(mm), int(ss or 0), tz="UTC")


def read_launch_tsv(path: Path) -> pd.DataFrame:
    """Read a GCAT TSV. The header line starts with '#'; other '#' lines are comments."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    header = None
    body = []
    for line in lines:
        if line.startswith("#"):
            if header is None:
                header = line.lstrip("#").strip("\n")
            continue
        if line.strip():
            body.append(line)
    if header is None:
        raise ValueError(f"No '#' header line found in {path}")
    text = header + "\n" + "\n".join(body)
    df = pd.read_csv(StringIO(text), sep="\t", dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    # The docs use both 'LaunchCode' and 'Launch_Code'; normalise.
    if "Launch_Code" in df.columns and "LaunchCode" not in df.columns:
        df = df.rename(columns={"Launch_Code": "LaunchCode"})
    for col in df.columns:
        df[col] = df[col].str.strip()
    return df


REQUIRED_COLUMNS = ["Launch_Tag", "Launch_JD", "Launch_Date", "LV_Type", "LaunchCode"]


def validate_schema(df: pd.DataFrame) -> list[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]
