"""Tests cho logic candidate site (P5): coverage-cell, dedup 1/ô, anti-degenerate."""
import h3
import pandas as pd

from ev_siting.features.build_candidates import _coverage_cells, _dedup_one_per_cell


def test_coverage_cells_contains_center():
    center = h3.latlng_to_cell(21.0, 105.8, 8)
    cov = _coverage_cells(center, 3.0)
    assert center in cov
    assert len(cov) > 1                      # R=3km > d -> phủ nhiều ô (không suy biến P4)


def test_coverage_grows_with_radius():
    center = h3.latlng_to_cell(21.0, 105.8, 8)
    small = _coverage_cells(center, 1.5)
    big = _coverage_cells(center, 3.0)
    assert len(big) > len(small)


def test_coverage_degenerate_below_spacing():
    # R < d(0,98km) -> mỗi trạm chỉ phủ ô của nó (P4)
    center = h3.latlng_to_cell(21.0, 105.8, 8)
    cov = _coverage_cells(center, 0.4)
    assert cov == frozenset({center})


def test_dedup_keeps_best_tier_per_cell():
    cell = h3.latlng_to_cell(21.0, 105.8, 8)
    df = pd.DataFrame([
        {"h3_r8": cell, "tier": "T2", "anchor_type": "mall", "lat": 21.0, "lng": 105.8},
        {"h3_r8": cell, "tier": "T0", "anchor_type": "existing_station", "lat": 21.0, "lng": 105.8},
        {"h3_r8": cell, "tier": "T4", "anchor_type": "gapfill_synthetic", "lat": 21.0, "lng": 105.8},
    ])
    out = _dedup_one_per_cell(df)
    assert len(out) == 1
    assert out.iloc[0]["tier"] == "T0"       # tier tốt nhất (rank nhỏ nhất) thắng


def test_dedup_one_row_per_distinct_cell():
    c1 = h3.latlng_to_cell(21.00, 105.80, 8)
    c2 = h3.latlng_to_cell(21.10, 105.90, 8)
    assert c1 != c2
    df = pd.DataFrame([
        {"h3_r8": c1, "tier": "T1", "anchor_type": "fuel", "lat": 21.00, "lng": 105.80},
        {"h3_r8": c1, "tier": "T2", "anchor_type": "mall", "lat": 21.00, "lng": 105.80},
        {"h3_r8": c2, "tier": "T4", "anchor_type": "gapfill_synthetic", "lat": 21.10, "lng": 105.90},
    ])
    out = _dedup_one_per_cell(df)
    assert set(out["h3_r8"]) == {c1, c2}
    assert out["h3_r8"].is_unique
