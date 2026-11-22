# T-Minus Markets: CRSP extension (for a WRDS subscriber)

Thank you for helping. This script uses your own WRDS login to read CRSP data for four delisted
launch firms (Orbital Sciences, Orbital ATK, Astra Space, Virgin Orbit). It computes event-study
statistics on your side. **Only derived statistics are written. No prices, returns, volumes or
model coefficients leave your machine.**

## Run it

**Option A: WRDS Jupyter (easiest)**
1. Go to wrds-jupyter.wharton.upenn.edu and log in.
2. Upload `tminus_crsp_extract.py`.
3. Open a terminal there and run `python tminus_crsp_extract.py`.

**Option B: your own laptop**
```
pip install wrds pandas numpy
python tminus_crsp_extract.py
```
The `wrds` package asks for your username, password and Duo approval. The run takes about a minute.

If the script stops with "Several PERMNOs for ...", it prints the candidates. Choose the right one,
type it into `PERMNO_OVERRIDE` near the top of the file (for example `{"OA": 12345}`), and run again.

## What comes out

| File | Contents |
|---|---|
| `tminus_crsp_firm_events.csv` | One row per launch event (137): CAR and CAR variance for 3 windows, daily abnormal returns from T-5 to T+20, residual volatility, model used, estimation days |
| `tminus_crsp_pairs.csv` | Residual correlations for events within 30 days of each other (needed for the clustered test) |
| `tminus_crsp_run_info.json` | PERMNOs, CRSP tables used, counts, script version, Orbital ATK's company-name history |
| `..._vwretd.csv` (2 files) | The same statistics with the CRSP value-weighted index as the market benchmark |
| `..._oa_atk.csv` (2 files) | Orbital ATK only, using its full history including Alliant Techsystems |

Please open the seven files before sending them, so you can see that nothing raw is inside.

## Why this stays within the licence

Abnormal returns and CARs are statistics computed from CRSP, the same kind of numbers that appear
in published event studies. The raw series (RET, PRC, VOL, SHROUT) are never written to disk by
the script. If your library has a stricter reading, please check with them before sending.
