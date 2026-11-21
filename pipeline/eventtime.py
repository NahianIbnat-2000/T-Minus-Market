"""Assign event day 0 per security, using real exchange calendars.

Rule (fixed before results):
  - disclosure during an open session  -> day 0 = that session
  - disclosure outside a session        -> day 0 = next session after it
"""
from __future__ import annotations

from functools import lru_cache

import exchange_calendars as xc
import pandas as pd


@lru_cache(maxsize=None)
def get_calendar(code: str):
    return xc.get_calendar(code, start="1998-01-01")


def day_zero(disclosure_utc: pd.Timestamp, exchange: str) -> pd.Timestamp:
    cal = get_calendar(exchange)
    ts = pd.Timestamp(disclosure_utc)
    ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
    ts = ts.floor("min")
    if cal.is_open_on_minute(ts):
        return cal.minute_to_session(ts, direction="none")
    return cal.minute_to_session(ts, direction="next")


def sessions_between(exchange: str, start, end) -> pd.DatetimeIndex:
    return get_calendar(exchange).sessions_in_range(start, end)
