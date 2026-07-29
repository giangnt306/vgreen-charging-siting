"""Tests cho logic candidate site (P5): coverage-cell, dedup 1/ô, anti-degenerate."""
import h3
import pandas as pd

import ev_siting.features.build_candidates as bc
from ev_siting.aoi import resolve_aoi
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


def _fake_stations(cells, lat, lng):
    """Trạm T0 giả — nhiều trạm dồn vào một ô, đúng hình dạng thật (max 12 trạm/ô)."""
    return pd.DataFrame(
        [
            {"lat": lat, "lng": lng, "h3_r8": c, "tier": "T0", "anchor_type": "existing_station",
             "source_ref": f"st-{c}-{i}", "is_existing": True}
            for c, n in cells.items() for i in range(n)
        ]
    )  # fmt: skip


def test_n_existing_in_cell_counted_before_dedup(tmp_path, monkeypatch):
    """Ràng buộc ≤1/ô xoá 32% dòng T0; cột này là thứ duy nhất giữ lại sức chứa tại-ô.

    Đếm PHẢI lấy trước dedup — nếu ai đó dời xuống sau, mọi ô sẽ thành 1 và test đỏ.
    """
    lat, lng = 21.0278, 105.8342
    c1 = h3.latlng_to_cell(lat, lng, 8)
    c2 = h3.latlng_to_cell(lat + 0.02, lng + 0.02, 8)
    assert c1 != c2
    counts = {c1: 5, c2: 1}

    cells = sorted(set(h3.grid_disk(c1, 4)) | set(h3.grid_disk(c2, 4)))
    buildable = pd.DataFrame({"h3_r8": cells, "buildable": True, "penalty": 0.0,
                              "penalty_flags": [[] for _ in cells], "dist_substation_m": 100.0,
                              "built_up_frac": 0.5})  # fmt: skip
    demand = pd.DataFrame({"h3_r8": cells, "pop": 1000.0, "n_poi": 0, "road_len_mt_m": 0.0})
    bpath, dpath = tmp_path / "b.parquet", tmp_path / "d.parquet"
    buildable.to_parquet(bpath)
    demand.to_parquet(dpath)

    monkeypatch.setattr(bc, "BUILDABLE_H3", bpath)
    monkeypatch.setattr(bc, "DEMAND_H3", dpath)
    monkeypatch.setattr(bc, "CANDIDATE_SITES", tmp_path / "cand.parquet")
    monkeypatch.setattr(bc, "CANDIDATE_GEOJSON", tmp_path / "cand.geojson")
    monkeypatch.setattr(bc, "_load_stations", lambda aoi: _fake_stations(counts, lat, lng))
    monkeypatch.setattr(bc, "_load_poi", lambda aoi: _fake_stations({}, lat, lng))

    out = bc.build(resolve_aoi(lat=lat, lng=lng, radius_km=8.0), p_hint=1, strict=False, gapfill_q=1.0)

    got = out.set_index("h3_r8")["n_existing_in_cell"]
    assert got[c1] == 5, "đếm sau dedup sẽ ra 1 — số trạm/ô bị mất im lặng"
    assert got[c2] == 1
    assert (out.loc[out["tier"] != "T0", "n_existing_in_cell"] == 0).all()
    assert out["h3_r8"].is_unique, "ràng buộc ≤1 candidate/ô vẫn phải giữ (chống tie-degenerate P4)"
