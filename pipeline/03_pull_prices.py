"""Step 03: download daily prices for mapped firms and their benchmarks."""
import json
from datetime import datetime, timezone

import pandas as pd

import config as C
from prices import fetch_one, quality_checks, to_returns


def main():
    events = pd.read_csv(C.INTERIM / "firm_events.csv", dtype=str, keep_default_na=False)
    firms = events[["ticker", "exchange"]].drop_duplicates()
    tickers = sorted(firms["ticker"].unique())
    benches = sorted({C.BENCHMARKS[e] for e in firms["exchange"].unique() if e in C.BENCHMARKS})

    frames, log = [], []
    for t in tickers + benches:
        try:
            df = fetch_one(t)
            status = "ok" if not df.empty else "empty"
        except Exception as e:  # keep going; the log records it
            df, status = pd.DataFrame(), f"error: {e}"
        n = len(df)
        first = str(df["date"].min().date()) if n else ""
        last = str(df["date"].max().date()) if n else ""
        log.append({"ticker": t, "status": status, "rows": n, "first_date": first, "last_date": last})
        print(f"{t:<12} {status:<8} rows={n:<6} {first} -> {last}")
        if n:
            frames.append(df)

    C.INTERIM.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(log).to_csv(C.INTERIM / "price_download_log.csv", index=False)
    if not frames:
        raise SystemExit("No prices downloaded. See data/interim/price_download_log.csv")
    prices = pd.concat(frames, ignore_index=True)
    rets = to_returns(prices)
    prices.to_parquet(C.INTERIM / "prices.parquet", index=False)
    rets.to_parquet(C.INTERIM / "returns.parquet", index=False)
    quality_checks(prices, rets).to_csv(C.INTERIM / "price_quality_issues.csv", index=False)
    (C.RAW / "manifest_prices.json").write_text(json.dumps({
        "source": "Yahoo Finance via yfinance",
        "auto_adjust": C.YF_AUTO_ADJUST,
        "returns_from": "Adj Close, simple returns",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tickers": log,
        "licence_note": "Check Yahoo terms before publishing raw prices or returns (audit risk 8).",
    }, indent=2))


if __name__ == "__main__":
    main()
