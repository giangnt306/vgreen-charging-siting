import json

import numpy as np
import pandas as pd
import pytest

from ev_siting.data.evcs.evcs_enumerate import (
    _load_resume_catalog,
    _load_resume_checkpoint,
    _resume_force_seeds,
    _save_checkpoint_atomic,
)
from ev_siting.data.evcs import transform_canonical
from ev_siting.data.vinfast_official.match_official import enrich, match


def test_f7_exact_code_without_coordinates_is_not_verified():
    ev = pd.DataFrame(
        [
            {
                "station_code": "C.TEST1",
                "name": "Tram test",
                "lat": np.nan,
                "lng": np.nan,
                "network": "VinFast",
                "station_type": "VINFAST_CS",
                "evse_powers": "[]",
                "status": "Available",
                "has_timeseries": True,
            }
        ]
    )
    off = pd.DataFrame(
        [
            {
                "store_id": "C.TEST1",
                "name": "Tram test",
                "lat": np.nan,
                "lng": np.nan,
                "charging_status": "ACTIVE",
                "access_type": "Public",
                "status": True,
                "charging_publish": True,
            }
        ]
    )
    out = enrich(match(ev, off), ev).iloc[0]
    assert out["official_matched"]
    assert out["match_method"] == "exact_code_no_coord"
    assert not out["verified"]


def test_f12_checkpoint_write_is_atomic_and_validated(tmp_path):
    ckpt = tmp_path / "catalog.ckpt.json"
    _save_checkpoint_atomic(str(ckpt), [21.0], [105.8], [1.5])
    assert _load_resume_checkpoint(str(ckpt)) == ([21.0], [105.8], [1.5])

    ckpt.write_text(json.dumps({"q_lat": [21.0], "q_lng": [], "q_r": [1.5]}))
    with pytest.raises(SystemExit, match="F12 FAIL"):
        _load_resume_checkpoint(str(ckpt))


def test_f12_resume_rejects_invalid_station_code(tmp_path):
    catalog = tmp_path / "catalog.csv"
    catalog.write_text("code,name\nC.OK,ok\nbad code,broken\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="F12 FAIL"):
        _load_resume_catalog(str(catalog))


def test_f8_resume_reseeds_only_found_station_outside_coverage():
    found = {
        "C.COVERED": {"lat": "21.0", "lng": "105.8"},
        "C.EDGE": {"lat": "21.2", "lng": "106.0"},
    }
    out = _resume_force_seeds(found, (8.0, 23.6, 102.0, 110.0), [21.0], [105.8], [5.0])
    assert out == [(21.2, 106.0, True)]


def test_f7_rejects_xref_from_different_master(tmp_path, monkeypatch):
    master = tmp_path / "master.csv"
    master.write_text("station_code\nC.TEST1\n", encoding="utf-8")
    xref = tmp_path / "official_xref.parquet"
    pd.DataFrame(
        [
            {
                "station_code": "C.TEST1",
                "source_master_sha256": "stale",
                "official_matched": True,
                "confidence": 1.0,
                "verified": True,
            }
        ]
    ).to_parquet(xref)
    monkeypatch.setattr(transform_canonical, "MASTER_CSV", master)
    monkeypatch.setattr(transform_canonical, "XREF_PARQUET", xref)
    with pytest.raises(SystemExit, match="stale"):
        transform_canonical.join_xref(pd.DataFrame({"station_code": ["C.TEST1"]}))


def _write_xref(path, codes, master_sha):
    pd.DataFrame(
        [
            {
                "station_code": c,
                "source_master_sha256": master_sha,
                "official_matched": True,
                "confidence": 1.0,
                "verified": True,
            }
            for c in codes
        ]
    ).to_parquet(path)


def test_f7_gate_accepts_car_only_subset_of_full_master_xref(tmp_path, monkeypatch):
    # Hinh dang THAT: matcher chay tren master DAY DU (co BATTERY_SWAP), con canonical
    # join sau khi da bo BSS. Gate phai la PHU (subset), khong phai BANG — neu khong
    # `make canonical` FAIL 100% o duong mac dinh.
    master = tmp_path / "master.csv"
    master.write_text("station_code\nC.CAR1\nB.BSS1\n", encoding="utf-8")
    xref = tmp_path / "official_xref.parquet"
    monkeypatch.setattr(transform_canonical, "MASTER_CSV", master)
    monkeypatch.setattr(transform_canonical, "XREF_PARQUET", xref)
    sha = transform_canonical._sha256(master)

    _write_xref(xref, ["C.CAR1", "B.BSS1"], sha)  # xref phu ca BSS
    car_only = pd.DataFrame({"station_code": ["C.CAR1"]})  # canonical da bo BSS
    assert transform_canonical.join_xref(car_only)["_has_xref"].all()

    _write_xref(xref, ["B.BSS1"], sha)  # thieu dung ma canonical can
    with pytest.raises(SystemExit, match="thieu 1 station_code"):
        transform_canonical.join_xref(car_only)


def test_f12_canonical_swap_replaces_whole_generation(tmp_path, monkeypatch):
    canonical = tmp_path / "canonical"
    (canonical / "stations").mkdir(parents=True)
    (canonical / "stations" / "old.txt").write_text("old")
    monkeypatch.setattr(transform_canonical, "CANONICAL_DIR", canonical)
    monkeypatch.setattr(transform_canonical, "STATIONS_DIR", canonical / "stations")
    monkeypatch.setattr(transform_canonical, "CONNECTORS_DIR", canonical / "connectors")

    stations = pd.DataFrame({"station_code": ["C.TEST1"], "province_code": ["NA"]})
    connectors = pd.DataFrame({"station_code": ["C.TEST1"], "province_code": ["NA"]})
    transform_canonical._write_partitioned_atomically(stations, connectors)

    assert not (canonical / "stations" / "old.txt").exists()
    assert list((canonical / "stations").rglob("*.parquet"))
    assert list((canonical / "connectors").rglob("*.parquet"))


def test_f20_exact_official_coordinate_replaces_large_raw_drift():
    df = pd.DataFrame(
        [{
            "lat": 21.0, "lng": 105.8, "official_lat": 21.02, "official_lng": 105.82,
            "match_method": "exact_code", "quality_flags": ["COORD_INVALID"],
        }]
    )
    out = transform_canonical.resolve_coordinates(df).iloc[0]
    assert out["coord_src"] == "vinfast_official_exact"
    assert out["coord_resolved"]
    assert out["lat"] == 21.02
    assert "COORD_REPAIRED_OFFICIAL" in out["quality_flags"]
    assert "COORD_INVALID" not in out["quality_flags"]


def test_f20_unresolved_coordinate_is_dirty_and_has_no_fake_point():
    df = pd.DataFrame(
        [{
            "lat": 0.0, "lng": 0.0, "official_lat": np.nan, "official_lng": np.nan,
            "match_method": "none", "quality_flags": [],
        }]
    )
    out = transform_canonical.resolve_coordinates(df).iloc[0]
    assert out["coord_src"] == "unresolved"
    assert not out["coord_resolved"]
    assert "COORD_PLACEHOLDER" in out["quality_flags"]
