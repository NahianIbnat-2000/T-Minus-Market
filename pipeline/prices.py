"""Step 03 logic: pull daily prices with yfinance and run data checks.

yfinance output is not assumed to be error-free. Every ticker is logged,
adjustment is set explicitly, and suspicious rows are flagged, not fixed.
"""
from __future__ import annotations

import pandas as pd

import config as C


def fetch_one(ticker: str, start: str = C.PRICE_START) -> pd.DataFrame:
    import yfinance as yf  # imported here so tests run without network

    df = yf.Ticker(ticker).history(start=start, auto_adjust=C.YF_AUTO_ADJUST, actions=True)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None).dt.normalize()
    out = pd.DataFrame({
        "date": df["date"], "ticker": ticker,
        "close": df.get("Close"), "adj_close": df.get("Adj Close", df.get("Close")),
        "volume": df.get("Volume"),
        "dividend": df.get("Dividends", 0.0), "split": df.get("Stock Splits", 0.0),
    })
    return out


def to_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Simple returns from adjusted close, per ticker, on the dates the ticker traded."""
    p = prices.sort_values(["ticker", "date"]).copy()
    p["ret"] = p.groupby("ticker")["adj_close"].pct_change(fill_method=None)
    return p[["date", "ticker", "ret", "adj_close", "volume"]]


def quality_checks(prices: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    issues = []
    for t, g in prices.groupby("ticker"):
        bad = g[(g["adj_close"] <= 0) | g["adj_close"].isna()]
        for _, r in bad.iterrows():
            issues.append((t, r["date"], "non_positive_or_missing_price", r["adj_close"]))
        dup = g[g["date"].duplicated()]
        for _, r in dup.iterrows():
            issues.append((t, r["date"], "duplicate_date", None))
        splits = g[g["split"].fillna(0) != 0]
        for _, r in splits.iterrows():
            issues.append((t, r["date"], "split_reported_check_adjustment", r["split"]))
    big = returns[returns["ret"].abs() > 0.5]
    for _, r in big.iterrows():
        issues.append((r["ticker"], r["date"], "abs_return_over_50pct_verify", round(r["ret"], 4)))
    return pd.DataFrame(issues, columns=["ticker", "date", "issue", "value"])
