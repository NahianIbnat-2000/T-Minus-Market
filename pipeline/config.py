"""Central settings for the Space Shock (formerly T-Minus Markets) pipeline.

Every number that shapes the sample or the tests lives here, so it is set
once, before any abnormal return is computed. Change it here, never inside
a script.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
MANUAL = ROOT / "data" / "manual"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"

# ---------------------------------------------------------------- sources
GCAT_LAUNCH_URL = "https://planet4589.org/space/gcat/tsv/launch/launch.tsv"
GCAT_LOCAL_FILE = RAW / "launch.tsv"
GCAT_CITATION = "data from GCAT (J. McDowell, planet4589.org/space/gcat), CC-BY"

# ---------------------------------------------------------------- sample
START_DATE = "2000-01-01"
# GCAT LaunchCode first letter: O = orbital, D = deep space (also orbital-class)
ORBITAL_CATEGORIES = {"O", "D"}
# McDowell: "a score of less than 0.75" is a failure.
FAILURE_THRESHOLD = 0.75
# Second letter E = pad explosion, no launch. Kept as a separate set, never pooled.
GROUND_ANOMALY_LETTERS = {"E"}

# ---------------------------------------------------------------- prices
PRICE_START = "1998-06-01"  # enough history for a 250-day window before 2000
YF_AUTO_ADJUST = False      # keep both Close and Adj Close; returns use Adj Close
# Benchmark index per exchange (edit if a better local index is justified)
BENCHMARKS = {
    "XNYS": "^GSPC",
    "XNAS": "^GSPC",
    "XMIL": "FTSEMIB.MI",
    "XPAR": "^FCHI",
    "XETR": "^GDAXI",
    "XTKS": "^N225",
    "XLON": "^FTSE",
}

# ---------------------------------------------------------------- event study (fixed before results)
EST_WINDOW = (-250, -30)        # trading days relative to day 0
EST_MIN_OBS = 100               # fewer -> market-adjusted fallback, flagged
EVENT_WINDOWS = {"primary": (0, 1), "robust": (-1, 3), "descriptive": (0, 20)}
PRIMARY_WINDOW = "primary"
RETURN_TYPE = "simple"          # simple returns for AR and CAR, Python and JS

# ---------------------------------------------------------------- rivals
# A vehicle family counts as "active" on a date if it launched within this many
# days before that date (measured from GCAT, so only pre-event information).
ACTIVE_LOOKBACK_DAYS = 730

# ---------------------------------------------------------------- clusters and gate
CLUSTER_GAP_TRADING_DAYS = 5    # failures sharing a firm within this gap = one cluster
MDE_Z = 2.8                     # 1.96 + 0.84: 5% two-sided, 80% power
GATE_MAX_PROVIDER_MDE = 0.05    # provider test must detect a CAR[0,+1] of 5% or less
GATE_MIN_PROVIDER_CLUSTERS = 10 # and have at least this many independent provider failures
GATE_MIN_RIVAL_EVENTS = 8       # independent failures with >= 1 covered Tier 1 rival

# Timing robustness: day 0 counts as robust if it is the same for disclosure anywhere
# from TIMING_EARLY_MIN before to TIMING_LATE_MIN after the recorded time.
TIMING_EARLY_MIN = 10
TIMING_LATE_MIN = 180

RANDOM_SEED = 20261121
