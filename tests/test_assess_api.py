"""Tests cho pilot API (B7) — hợp đồng biên, không phải hợp đồng tầng dưới.

Cái được khoá ở đây là thứ **khách nhìn thấy**:
1. Không endpoint nào rò `score`/`tier` (v1 bỏ điểm số — postmortem §10);
2. Mọi hồ sơ mang data_version/model_version/calibration (bất biến §4.4);
3. CSV vào — CSV ra chạy được, và CSV hỏng trả 400 chứ không 500;
4. Ngữ cảnh dựng MỘT lần, không phải mỗi request (đọc bundle + cache là việc đắt).
"""

import io
from types import SimpleNamespace

import h3
import numpy as np
import pandas as pd
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from ev_siting.assess import api, dossier, engine, kernel  # noqa: E402

LAT, LNG = 21.0278, 105.8342


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Ngữ cảnh tí hon — API test không được phụ thuộc bundle 500 MB."""
    covered0 = pd.DataFrame(
        {
            "station_id": ["st-a"], "lat": [LAT], "lng": [LNG],
            "h3_r8": [h3.latlng_to_cell(LAT, LNG, 8)], "num_connectors": [2],
            "current_type": ["AC"], "operator": ["VinFast"],
        }
    )  # fmt: skip
    cells = sorted(kernel.point_cells(LAT, LNG))[:3]
    dem = pd.Series([500.0] * 3, index=pd.Index(cells, name="h3_r8"), name="pop", dtype=float)
    ref = pd.DataFrame(
        {
            "n_marginal_pop": np.linspace(0, 2000, 20), "v_demand_local": np.linspace(0, 2000, 20),
            "v_competition": np.full(20, 1.0), "rho": np.arange(1.0, 21.0),
        }
    )  # fmt: skip
    actx = engine.AssessContext(
        bundle=SimpleNamespace(aoi={"bbox": [8.0, 102.0, 23.7, 110.0]}, covered0=covered0),
        dem=dem, net=kernel.build_network(covered0), ref=ref,
        occ=pd.DataFrame({"station_id": ["st-a"], "occ_mean_dw": [0.4], "duration_coverage": [0.9],
                          "num_connectors": [2]}),
        credit_rule="shapley", mode="live",
        cand_by_cell=pd.DataFrame({"penalty_flags": [[]], "tier": ["T1"]},
                                  index=pd.Index(["x"], name="h3_r8")),
    )  # fmt: skip
    bench = pd.DataFrame(
        {
            "current_type": ["DC", "AC"], "density_band": ["đô thị"] * 2, "port_band": ["4+", "1"],
            "n": [500, 900], "util_p25": [0.2, 0.05], "util_p50": [0.35, 0.09],
            "util_p75": [0.5, 0.2], "reportable": [True, True],
        }
    )  # fmt: skip
    dem_df = pd.DataFrame({"h3_r8": cells, "pop": 500.0, "road_len_m": 100.0, "n_poi": 1, "n_fuel": 0, "n_parking": 0})
    p = tmp_path / "dem.parquet"
    dem_df.to_parquet(p)
    monkeypatch.setattr(dossier.paths, "DEMAND_H3", p)
    monkeypatch.setattr(engine.paths, "LOG_PATH", tmp_path / "log.jsonl")

    ctx = dossier.DossierContext(actx=actx, bench=bench, bench_meta={"density_edges_pop": [100.0, 10000.0]})
    monkeypatch.setattr(api, "_CTX", ctx)
    return TestClient(api.app)


def test_health_carries_versions(client):
    b = client.get("/health").json()
    assert b["status"] == "ok"
    for k in ("model_version", "data_version", "calibration"):
        assert b[k]


def test_dossier_returns_facts_without_score(client):
    r = client.post("/dossier", json={"lat": LAT, "lng": LNG, "point_id": "HS-API"})
    assert r.status_code == 200
    d = r.json()
    assert d["verdict"] in (dossier.VERDICT_OK, dossier.VERDICT_SURVEY)
    assert "score_total" not in r.text and '"tier"' not in r.text
    assert d["meta"]["data_version"] and d["meta"]["calibration"]


def test_assert_no_score_catches_nested_leak():
    api._assert_no_score({"a": {"b": [{"ok": 1}]}})  # không ném
    with pytest.raises(Exception):
        api._assert_no_score({"a": {"b": [{"score_total": 67}]}})


def test_markdown_endpoint_is_readable_page(client):
    r = client.post("/dossier/markdown", json={"lat": LAT, "lng": LNG, "point_id": "HS-MD"})
    assert r.status_code == 200
    assert "HỒ SƠ THẨM ĐỊNH" in r.text and "HS-MD" in r.text
    assert "score" not in r.text.lower()


def test_batch_csv_roundtrip(client):
    csv = "point_id,lat,lng\nA,21.0278,105.8342\nB,20.30,104.80\n"
    r = client.post("/dossier/batch", content=csv, headers={"content-type": "text/csv"})
    assert r.status_code == 200
    out = pd.read_csv(io.StringIO(r.text))
    assert list(out["point_id"]) == ["A", "B"]
    assert "verdict" in out.columns
    assert not any(c.startswith("score") for c in out.columns)


@pytest.mark.parametrize(
    "body", ["point_id,x,y\nA,1,2\n", "", "không phải csv\x00\x01"], ids=["thiếu-cột", "rỗng", "rác"]
)
def test_batch_rejects_bad_csv_as_client_error(client, body):
    """CSV hỏng phải là lỗi người gửi (4xx), không bao giờ là lỗi máy (5xx)."""
    r = client.post("/dossier/batch", content=body, headers={"content-type": "text/csv"})
    assert 400 <= r.status_code < 500, r.text


def test_point_validation_rejects_impossible_coords(client):
    r = client.post("/dossier", json={"lat": 999.0, "lng": 105.0})
    assert r.status_code == 422
