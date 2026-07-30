import json

import h3
import numpy as np
import pandas as pd
import pytest

from ev_siting.data.evcs.transform_canonical import explode_connectors
from ev_siting.data.osm import overpass_poi
from ev_siting.features import build_candidates


def test_f9_http_200_remark_is_not_accepted(monkeypatch):
    class Response:
        status_code = 200
        def json(self):
            return {"remark": "runtime error: Query timed out"}
    monkeypatch.setattr(overpass_poi.requests, "post", lambda *args, **kwargs: Response())
    with pytest.raises(RuntimeError, match="incomplete"):
        overpass_poi._post("query", tries=1)


def test_f13_evcs_only_connector_falls_back_to_power_tier():
    # Q5 (B3 30/07): theo Giang — connector evcs-only (khong khop registry) van suy
    # AC/DC tu nguong 25 kW (AC_MAX_W) lam gia tri LIVE; su "chua xac minh" nam o
    # connector_standard='UNKNOWN' (+ STD_UNVERIFIED o station), va E-DQ4 co
    # current_type_asset de phan tang. Khong con expectation UNKNOWN cua F13 cu.
    rows = explode_connectors(json.dumps([{"type": 22000, "totalEvse": 1}]), "s", "C.X", "NA", {})
    assert rows[0]["current_type"] == "AC"
    assert rows[0]["connector_label"] == "AC-22kW"
    assert rows[0]["connector_standard"] == "UNKNOWN"
    rows = explode_connectors(json.dumps([{"type": 120000, "totalEvse": 1}]), "s", "C.X", "NA", {})
    assert rows[0]["current_type"] == "DC"
    assert rows[0]["connector_label"] == "DC-120kW"


def test_f16_gapfill_clips_global_buildable_to_aoi(monkeypatch):
    inside = h3.latlng_to_cell(21.0, 105.8, 8)
    outside = h3.latlng_to_cell(10.0, 106.0, 8)
    # Q6i: n_poi/road_len_mt_m da khai tu (E-DQ7b/c) — demand_h3 mang bo cot lop cua
    # Giang: road_lane_mw_m/road_lane_ar_m + n_<lop POI> cho trip_gen_interim.
    dem = pd.DataFrame({
        "h3_r8": [inside, outside], "pop": [10, 999],
        "road_lane_mw_m": [0.0, 0.0], "road_lane_ar_m": [0.0, 0.0],
        "n_mall": [0, 0], "n_dept_store": [0, 0], "n_supermarket": [0, 0],
        "n_market": [0, 0], "n_apartment_complex": [0, 0],
    })
    monkeypatch.setattr(build_candidates.pd, "read_parquet", lambda *args, **kwargs: dem)
    # F16 kiểm CLIP THEO AOI; bộ cắt biên giới (Q1: osm/vn_boundary.points_in_vn) là
    # control khác và có test riêng trong `test_vn_boundary.py`. Vô hiệu hoá nó ở đây
    # (raising=False: no-op nếu _gapfill không clip biên), nếu không nó cũng đọc
    # parquet và dính luôn monkeypatch `read_parquet` ở trên.
    monkeypatch.setattr(build_candidates, "points_in_vn",
                        lambda lat, lng: np.ones(len(lat), dtype=bool), raising=False)
    class Aoi:
        @staticmethod
        def contains(lat, lng):
            return (lat > 20) & (lat < 22)
    buildable = pd.DataFrame({"h3_r8": [inside, outside], "buildable": [True, True]})
    out = build_candidates._gapfill(Aoi(), buildable, set(), gapfill_q=0)
    assert out["h3_r8"].tolist() == [inside]


def test_f16_qa_gate_fails_invalid_radius_before_handoff(monkeypatch):
    cell = h3.latlng_to_cell(21.0, 105.8, 8)
    monkeypatch.setattr(build_candidates.pd, "read_parquet", lambda *args, **kwargs: pd.DataFrame({"h3_r8": [cell], "pop": [1]}))
    class Aoi:
        @staticmethod
        def in_core(lat, lng):
            return [True] * len(lat)
    cand = pd.DataFrame({"h3_r8": [cell], "lat": [21.0], "lng": [105.8]})
    ok, report = build_candidates._qa_gate(cand, Aoi(), 0.4, p_hint=1, max_candidates=5)
    assert not ok
    assert next(x for x in report["checks"] if x["gate"] == "grid_radius")["status"] == "FAIL"
