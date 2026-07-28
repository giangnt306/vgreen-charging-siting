import json

import h3
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


def test_f13_unknown_connector_never_uses_kw_for_current_type():
    rows = explode_connectors(json.dumps([{"type": 22000, "totalEvse": 1}]), "s", "C.X", "NA", {})
    assert rows[0]["current_type"] == "UNKNOWN"
    assert rows[0]["connector_label"] == "POWER-22kW"


def test_f16_gapfill_clips_global_buildable_to_aoi(monkeypatch):
    inside = h3.latlng_to_cell(21.0, 105.8, 8)
    outside = h3.latlng_to_cell(10.0, 106.0, 8)
    dem = pd.DataFrame({"h3_r8": [inside, outside], "pop": [10, 999], "n_poi": [0, 0], "road_len_mt_m": [0, 0]})
    monkeypatch.setattr(build_candidates.pd, "read_parquet", lambda *args, **kwargs: dem)
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
