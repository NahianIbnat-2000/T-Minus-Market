"""Audit diagnostics and repository hygiene."""
from pathlib import Path

import diagnostics as D

ROOT = Path(__file__).resolve().parents[1]


def _fe(tag, tk, firm, cl, car, var=0.0004):
    return {"group": "rival", "launch_tag": tag, "ticker": tk, "firm": firm, "cluster": cl, "day0": f"2020-01-{cl:02d}",
            "vehicle": "V", "windows": {"primary": {"car": car, "var": var, "L": 2}}}


FE = [_fe("A", "X", "Xco", 1, 0.02), _fe("A", "Y", "Yco", 1, 0.00), _fe("B", "X", "Xco", 2, -0.04), _fe("C", "Y", "Yco", 3, 0.05, 0.0016)]


def test_weighting_definitions():
    w = D.weighting(FE)
    assert abs(w["observation_weighted"] - 0.0075) < 1e-12
    assert abs(w["event_weighted"] - (0.01 - 0.04 + 0.05) / 3) < 1e-12           # clusters equal
    assert abs(w["firm_balanced"] - ((0.02 - 0.04) / 2 + (0.0 + 0.05) / 2) / 2) < 1e-12
    assert abs(w["median"] - 0.01) < 1e-12 and w["share_negative"] == 0.25
    assert abs(D.weighting(FE, drop=["C Y"])["observation_weighted"] - (-0.02 / 3)) < 1e-12


def test_power_matches_interval():
    p = D.power({"mean_car": 0.0028, "ci_low": -0.0162, "ci_high": 0.0218, "n_clusters": 22})
    assert 0.0085 < p["se"] < 0.0095 and 0.025 < p["mde80"] < 0.029 and p["power"][0.01] < 0.25


def test_exposure_matrix():
    firms, rows = D.exposure_matrix(FE)
    assert set(firms) == {"Xco", "Yco"} and [r["cluster"] for r in rows] == [1, 2, 3] and rows[0]["counts"] == {"Xco": 1, "Yco": 1}


def test_alpha_beta_file_never_committed():
    assert "data/processed/firm_event_cars.csv" in (ROOT / ".gitignore").read_text().splitlines()
