import json

import numpy as np
import pandas as pd
import pytest

from ev_siting.data.evcs import fix_coords, transform_canonical
from ev_siting.data.evcs.evcs_enumerate import (
    _load_resume_catalog,
    _load_resume_checkpoint,
    _resume_force_seeds,
    _save_checkpoint_atomic,
)
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


# --- E-DQ1 (Q3/B3 30/07): semantics toa do hop nhat theo fix_coords cua Giang -----
# Thay 2 test resolve_coordinates cu (coord_src='vinfast_official_exact'/'unresolved'):
# nhanh sua-theo-official >=200m cua transform la nhanh chet (0/19.427 kich hoat vi
# official cung backend evcs — audit 29/07), enum coord_src theo Giang:
# {evcs, official, placeholder} (+ 'outside_admin' do E-DQ3 gan sau).


def _coord_frame():
    # 25 tram HNO that quanh Ha Noi -> centroid median dang tin (MIN_PROV_N=20);
    # STACK_MIN tram vat ly KHAC nhau don ve DUNG 1 diem HCM cach tinh >100km —
    # mo hinh do that cua E-DQ1 (35 tram HNO placeholder tai 10.773106,106.694794).
    rows = [
        {
            "station_id": f"good{i}",
            "station_code": f"C.HNO{i:04d}",
            "lat": 21.0 + 0.01 * i,
            "lng": 105.8 + 0.01 * i,
            "h3_r8": None,
            "province_code": "HNO",
            "physical_id": f"pg{i}",
            "quality_flags": [],
            "official_store_id": None,
        }
        for i in range(25)
    ]
    rows += [
        {
            "station_id": f"ph{i}",
            "station_code": f"C.HNO9{i:03d}",
            "lat": 10.773106,
            "lng": 106.694794,
            "h3_r8": None,
            "province_code": "HNO",
            "physical_id": f"pp{i}",
            "quality_flags": [],
            "official_store_id": f"C.HNO9{i:03d}",
        }
        for i in range(fix_coords.STACK_MIN)
    ]
    return pd.DataFrame(rows)


def test_e_dq1_placeholder_stack_is_unresolved_dirty_with_no_fake_point(monkeypatch):
    # Khong co toa do official tot -> coord_src='placeholder', LOAI khoi cung
    # (coord_resolved=False, h3_r8=NULL), GIU toa do goc de dao nguoc/geocode sau —
    # khong bia diem, khong xoa dong (giu dung y F20: unresolved phai dirty).
    monkeypatch.setattr(fix_coords, "_official_placeholder_points", lambda min_stack=fix_coords.STACK_MIN: ({}, set()))
    out = fix_coords.resolve_coords(_coord_frame())
    ph = out[out["station_id"].str.startswith("ph")]
    assert (ph["coord_src"] == "placeholder").all()
    assert (~ph["coord_resolved"]).all()
    assert ph["h3_r8"].isna().all()
    assert ph["quality_flags"].map(lambda fl: "COORD_PLACEHOLDER" in fl).all()
    assert (ph["lat"] == ph["lat_raw"]).all()  # giu nguyen de dao nguoc, khong co diem gia
    good = out[out["station_id"].str.startswith("good")]
    assert (good["coord_src"] == "evcs").all()
    assert good["coord_resolved"].all()
    assert good["h3_r8"].notna().all()


def test_e_dq1_placeholder_snaps_to_good_official_coordinate(monkeypatch):
    # Tier 2 cua cay ground-truth: placeholder NHUNG official co toa do TOT (khong
    # phai diem placeholder, gan centroid tinh) -> snap, coord_src='official',
    # quay lai cung. FLAG khong xoa (nhat quan P6/P8): COORD_PLACEHOLDER van nam
    # trong quality_flags de audit.
    lut = {f"C.HNO9{i:03d}": (21.05, 105.85) for i in range(fix_coords.STACK_MIN)}
    monkeypatch.setattr(fix_coords, "_official_placeholder_points", lambda min_stack=fix_coords.STACK_MIN: (lut, set()))
    out = fix_coords.resolve_coords(_coord_frame())
    ph = out[out["station_id"].str.startswith("ph")]
    assert (ph["coord_src"] == "official").all()
    assert ph["coord_resolved"].all()
    assert (ph["lat"] == 21.05).all()
    assert (ph["lng"] == 105.85).all()
    assert (ph["coord_fix_dist_m"] > 0).all()
    assert ph["h3_r8"].notna().all()
    assert ph["quality_flags"].map(lambda fl: "COORD_PLACEHOLDER" in fl).all()


def _dedup(rows):
    import pandas as pd

    from ev_siting.data.evcs.dedup_crosssource import assign_physical_id

    base = {"match_method": "exact_code", "official_matched": True, "confidence": 0.9,
            "has_timeseries": True, "quality_flags": []}
    df = pd.DataFrame([{**base, **r} for r in rows])
    out = assign_physical_id(df)
    return out, dict(zip(out["station_id"], out["physical_id"]))


def test_dedup_store_id_guard_is_not_a_restatement_of_the_primary_key():
    """Hai dong TRUNG TEN + TRUNG TOA DO phai duoc gop, du store_id khac nhau.

    Day la ca DOI KHANG cua guard `_distinct_store`. Ban 29/07 chan bang dieu kien
    "hai `official_store_id` khac nhau", nhung `exact_code` gan store_id = station_code
    cho 19.605/19.635 dong (99,85%) va station_code la PK unique -> dieu kien do LUON
    dung, tang T2 chet, va 97 cap ten TRUNG KHIT (vd "Vincom Plaza Tra Vinh" x2) bi bo
    sot, ca hai deu `is_primary=True` -> cung bi dem hai lan.
    """
    out, pid = _dedup([
        {"station_id": "s1", "station_code": "C.TVI0003", "lat": 9.9, "lng": 106.3,
         "name": "Vincom Plaza Tra Vinh", "address": "1 Nguyen Thai Hoc, Tra Vinh",
         "official_store_id": "C.TVI0003"},
        {"station_id": "s2", "station_code": "C.TVI0013", "lat": 9.9000072, "lng": 106.3,
         "name": "Vincom Plaza Tra Vinh mat phia truoc", "address": "1 Nguyen Thai Hoc, Tra Vinh",
         "official_store_id": "C.TVI0013"},
    ])
    assert pid["s1"] == pid["s2"], "store_id chi echo lai PK thi khong duoc dung lam trong tai"
    assert out["is_primary"].sum() == 1
    assert out.attrs["n_blocked_by_store"] == 0


def test_dedup_blocks_when_registry_evidence_is_independent_of_the_key():
    """Nguoc lai: store_id KHAC station_code (spatial_fuzzy) = quy chieu doc lap -> chan."""
    out, pid = _dedup([
        {"station_id": "s1", "station_code": "C.A1", "lat": 10.0, "lng": 106.0,
         "name": "Tram A", "address": "12 Le Loi", "official_store_id": "C.STORE9"},
        {"station_id": "s2", "station_code": "C.A2", "lat": 10.0000072, "lng": 106.0,
         "name": "Tram A", "address": "12 Le Loi", "official_store_id": "C.STORE7"},
    ])
    assert pid["s1"] != pid["s2"]
    assert out.attrs["n_blocked_by_store"] == 1


def test_dedup_same_official_store_still_merges():
    """T1 khong doi: >1 dong cung `official_store_id` -> gop khong can nguong."""
    _, pid = _dedup([
        {"station_id": "s3", "station_code": "C.B1", "lat": 11.0, "lng": 107.0,
         "name": "Tram Ben Thanh", "address": "1 Le Loi", "official_store_id": "C.B9"},
        {"station_id": "s4", "station_code": "C.B2", "lat": 11.0, "lng": 107.0,
         "name": "Tram Ben Thanh", "address": "1 Le Loi", "official_store_id": "C.B9",
         "match_method": "spatial_fuzzy", "confidence": 0.5, "has_timeseries": False},
    ])
    assert pid["s3"] == pid["s4"]


def test_dedup_identity_ignores_address_and_respects_serial_tokens():
    """Hai lay do that trong du lieu ma ty le mo tren `name` tho bat sai.

    (a) cung DIA CHI khac CHU: `name` cua evcs nhung ca dia chi nen token_set_ratio dat
        89,9 -> gop nham hai ho khac nhau. Tru phan `address` ra thi con 50.
    (b) khac SO thu tu: "Van Hien 1" / "Van Hien 2" cach nhau vai met la HAI tram that,
        moi ty le mo deu cho >=97.
    """
    _, pid = _dedup([
        {"station_id": "a1", "station_code": "C.AGI11021", "lat": 9.6, "lng": 105.35,
         "name": "Tu nhan Ho Van Nam,To 7, Ap Tan Doi, Xa Vinh Tuy, Tinh An Giang",
         "address": "To 7, Ap Tan Doi, Xa Vinh Tuy, Tinh An Giang",
         "official_store_id": "C.AGI11021"},
        {"station_id": "a2", "station_code": "C.DTH11257", "lat": 9.6000072, "lng": 105.35,
         "name": "Tu nhan Le Thi My Kim,To 7, Ap Tan Doi, Xa Vinh Tuy, Tinh An Giang",
         "address": "To 7, Ap Tan Doi, Xa Vinh Tuy, Tinh An Giang",
         "official_store_id": "C.DTH11257"},
        {"station_id": "b1", "station_code": "C.HCM1288", "lat": 10.8, "lng": 106.7,
         "name": "Tram sac Van Hien 1, 453/27 Le Hong Phong", "address": "453/27 Le Hong Phong",
         "official_store_id": "C.HCM1288"},
        {"station_id": "b2", "station_code": "C.HCM1289", "lat": 10.8000072, "lng": 106.7,
         "name": "Tram sac Van Hien 2, 453/27 Le Hong Phong", "address": "453/27 Le Hong Phong",
         "official_store_id": "C.HCM1289"},
    ])
    assert pid["a1"] != pid["a2"], "dia chi trung khong duoc keo hai chu khac nhau vao mot nhom"
    assert pid["b1"] != pid["b2"], "so thu tu khac nhau = hai tram that"
