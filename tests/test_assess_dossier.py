"""Test deliverable v1 — hồ sơ facts (dossier) + benchmark định cỡ (sizing).

Bất biến sản phẩm được kiểm ở đây, không chỉ là code chạy được:
1. KHÔNG bao giờ xuất "Từ chối" (backlog §4.2);
2. KHÔNG rò `score_total` ra hồ sơ (v1 bỏ điểm số — postmortem §10);
3. Nhóm benchmark mỏng KHÔNG được công bố số;
4. Trùng phủ 100% phải nâng mức rà soát (rủi ro doanh thu NPP).
"""

import json
from types import SimpleNamespace

import h3
import numpy as np
import pandas as pd
import pytest

from ev_siting.assess import dossier, engine, kernel, params, sizing

LAT_A, LNG_A = 21.0278, 105.8342
LAT_FAR, LNG_FAR = 20.30, 104.80


@pytest.fixture
def bench():
    return pd.DataFrame(
        {
            "current_type": ["DC", "AC", "DC", "AC"],
            "density_band": ["đô thị", "đô thị", "thưa", "thưa"],
            "port_band": ["4+", "1", "1", "1"],
            "n": [500, 900, 5, 400],  # nhóm DC-thưa n=5 -> dưới ngưỡng
            "util_p25": [0.2, 0.05, np.nan, 0.03],
            "util_p50": [0.35, 0.09, np.nan, 0.10],
            "util_p75": [0.5, 0.2, np.nan, 0.2],
            "reportable": [True, True, False, True],
        }
    )


@pytest.fixture
def meta():
    return {"density_edges_pop": [100.0, 10000.0]}


def test_sizing_suggest_picks_band_and_hides_thin_groups(bench, meta):
    urban = sizing.suggest(50_000.0, bench, meta)
    assert urban["density_band"] == "đô thị"
    got = {r["current_type"]: r for r in urban["observed"]}
    assert got["DC"]["util_p50"] == pytest.approx(0.35) and got["AC"]["util_p50"] == pytest.approx(0.09)

    sparse = sizing.suggest(10.0, bench, meta)
    kinds = {r["current_type"] for r in sparse["observed"]}
    assert "AC" in kinds and "DC" not in kinds, "nhóm mỏng (n=5) không được công bố"


def test_sizing_benchmark_masks_thin_groups():
    assert sizing.MIN_GROUP_N >= 20  # ngưỡng mẫu tối thiểu là hợp đồng, không phải tuỳ hứng


def _ctx(dem, ref, cand_by_cell=None):
    covered0 = pd.DataFrame(
        {
            "station_id": ["st-a"], "lat": [LAT_A], "lng": [LNG_A],
            "h3_r8": [h3.latlng_to_cell(LAT_A, LNG_A, 8)], "num_connectors": [2],
            "current_type": ["AC"], "operator": ["VinFast"],
        }
    )  # fmt: skip
    net = kernel.build_network(covered0)
    occ = pd.DataFrame(
        {"station_id": ["st-a"], "occ_mean_dw": [0.4], "duration_coverage": [0.9], "num_connectors": [2]}
    )
    if cand_by_cell is None:
        cand_by_cell = pd.DataFrame({"penalty_flags": [[]], "tier": ["T1"]}, index=pd.Index(["x"], name="h3_r8"))
    return engine.AssessContext(
        bundle=SimpleNamespace(aoi={"bbox": [8.0, 102.0, 23.7, 110.0]}, covered0=covered0),
        dem=dem, net=net, ref=ref, occ=occ, credit_rule="shapley", mode="live", cand_by_cell=cand_by_cell,
    )  # fmt: skip


@pytest.fixture
def dctx(bench, meta, monkeypatch, tmp_path):
    cov = kernel.point_cells(LAT_A, LNG_A)
    cells = sorted(cov)[:3]
    dem = pd.Series([500.0] * 3, index=pd.Index(cells, name="h3_r8"), name="pop", dtype=float)
    ref = pd.DataFrame(
        {
            "n_marginal_pop": np.linspace(0, 2000, 20), "v_demand_local": np.linspace(0, 2000, 20),
            "v_competition": np.full(20, 1.0), "rho": np.arange(1.0, 21.0),
        }
    )  # fmt: skip
    # demand_h3 thật là 268k dòng — test thay bằng frame tí hon qua paths.DEMAND_H3.
    dem_df = pd.DataFrame({"h3_r8": cells, "pop": 500.0, "road_len_m": 100.0, "n_poi": 1, "n_fuel": 0, "n_parking": 0})
    p = tmp_path / "dem.parquet"
    dem_df.to_parquet(p)
    monkeypatch.setattr(dossier.paths, "DEMAND_H3", p)
    return dossier.DossierContext(actx=_ctx(dem, ref), bench=bench, bench_meta=meta)


def test_dossier_never_rejects_and_hides_score(dctx, tmp_path, monkeypatch):
    monkeypatch.setattr(engine.paths, "LOG_PATH", tmp_path / "log.jsonl")
    for lat, lng in ((LAT_A, LNG_A), (LAT_FAR, LNG_FAR), (0.0, 0.0)):
        d = dossier.make_dossier(lat, lng, dctx, point_id="HS-T")
        assert d["verdict"] in (dossier.VERDICT_OK, dossier.VERDICT_SURVEY)
        assert d["verdict"] != params.TIER_REJECT, "v1 không bao giờ tự Từ chối"
        blob = json.dumps(d, ensure_ascii=False, default=str)
        assert "score_total" not in blob and "score_N" not in blob, "v1 không được rò điểm số"


def test_dossier_full_overlap_raises_review(dctx, tmp_path, monkeypatch):
    """Điểm trùng chỗ trạm cũ: 100% dân trong R đã phủ + có trạm trong 1 km -> R13."""
    monkeypatch.setattr(engine.paths, "LOG_PATH", tmp_path / "log.jsonl")
    d = dossier.make_dossier(LAT_A, LNG_A, dctx, point_id="HS-OVERLAP")
    assert d["operations"]["n_redundancy"] == pytest.approx(1.0)
    assert d["verdict"] == dossier.VERDICT_SURVEY
    assert any(r.startswith("R13") for r in d["reasons"])


def test_dossier_full_overlap_fires_without_station_within_1km(bench, meta, tmp_path, monkeypatch):
    """B8 29/07: R13 từng đòi 'có trạm ≤1 km' nên im ở 3,0% hồ sơ đã trùng phủ 100%.

    Ca này là đúng cái lỗ đó: trạm duy nhất cách ~1,5 km — NGOÀI 1 km, TRONG bán kính
    phục vụ — mà catchment vẫn phủ 100% ⇒ phải nổ R13, không được ra "Đủ điều kiện xem xét".
    """
    from ev_siting.aoi import EARTH_R_KM, haversine_km

    s_lng = LNG_A + np.degrees(1.5 / (EARTH_R_KM * np.cos(np.radians(LAT_A))))
    assert 1.0 < haversine_km(LAT_A, LNG_A, LAT_A, s_lng) < 3.0, "trạm phải ngoài 1 km, trong R"

    covered0 = pd.DataFrame(
        {
            "station_id": ["st-far"], "lat": [LAT_A], "lng": [s_lng],
            "h3_r8": [h3.latlng_to_cell(LAT_A, s_lng, 8)], "num_connectors": [2],
            "current_type": ["AC"], "operator": ["VinFast"],
        }
    )  # fmt: skip
    net = kernel.build_network(covered0)
    cells = sorted(kernel.point_cells(LAT_A, LNG_A) & net.covered_cells)[:3]
    dem = pd.Series([500.0] * 3, index=pd.Index(cells, name="h3_r8"), name="pop", dtype=float)
    ref = pd.DataFrame(
        {
            "n_marginal_pop": np.linspace(0, 2000, 20), "v_demand_local": np.linspace(0, 2000, 20),
            "v_competition": np.full(20, 1.0), "rho": np.arange(1.0, 21.0),
        }
    )  # fmt: skip
    actx = engine.AssessContext(
        bundle=SimpleNamespace(aoi={"bbox": [8.0, 102.0, 23.7, 110.0]}, covered0=covered0),
        dem=dem, net=net, ref=ref,
        occ=pd.DataFrame({"station_id": ["st-far"], "occ_mean_dw": [0.4], "duration_coverage": [0.9],
                          "num_connectors": [2]}),
        credit_rule="shapley", mode="live",
        cand_by_cell=pd.DataFrame({"penalty_flags": [[]], "tier": ["T1"]}, index=pd.Index(["x"], name="h3_r8")),
    )  # fmt: skip
    dem_df = pd.DataFrame({"h3_r8": cells, "pop": 500.0, "road_len_m": 100.0, "n_poi": 1, "n_fuel": 0, "n_parking": 0})
    dpath = tmp_path / "dem.parquet"
    dem_df.to_parquet(dpath)
    monkeypatch.setattr(dossier.paths, "DEMAND_H3", dpath)
    monkeypatch.setattr(engine.paths, "LOG_PATH", tmp_path / "log.jsonl")

    d = dossier.make_dossier(LAT_A, LNG_A, dossier.DossierContext(actx=actx, bench=bench, bench_meta=meta),
                             point_id="HS-FAR")
    assert d["network"]["n_within_1km"] == 0, "kịch bản mất nghĩa nếu trạm lọt vào 1 km"
    assert d["network"]["n_within_r"] >= 1
    assert d["operations"]["n_redundancy"] == pytest.approx(1.0)
    assert d["verdict"] == dossier.VERDICT_SURVEY, "luật cũ (đòi ≤1 km) sẽ ra 'Đủ điều kiện xem xét' ở đây"
    r13 = next(r for r in d["reasons"] if r.startswith("R13"))
    assert "trong bán kính" in r13


def test_dossier_markdown_carries_labels_and_limits(dctx, tmp_path, monkeypatch):
    monkeypatch.setattr(engine.paths, "LOG_PATH", tmp_path / "log.jsonl")
    md = dossier.render_markdown(dossier.make_dossier(LAT_A, LNG_A, dctx, point_id="HS-MD"))
    for must in (
        "HS-MD",
        "Kết luận",
        params.CALIBRATION_LABEL,
        params.DATA_VERSION,
        "không phải dự đoán doanh thu",
        "[mô phỏng]",
        "Định cỡ",
    ):
        assert must in md, f"thiếu trong hồ sơ: {must}"  # fmt: skip
    assert "score_total" not in md


def test_dossier_batch_columns_stable(dctx, tmp_path, monkeypatch):
    monkeypatch.setattr(engine.paths, "LOG_PATH", tmp_path / "log.jsonl")
    pts = pd.DataFrame({"point_id": ["A", "B"], "lat": [LAT_A, LAT_FAR], "lng": [LNG_A, LNG_FAR]})
    tab = dossier.batch(pts, dctx)
    assert list(tab["point_id"]) == ["A", "B"]
    for c in ("verdict", "d_nearest_m", "pop_catchment", "util_dc_similar", "util_ac_similar", "calibration"):
        assert c in tab.columns
    assert not any(c.startswith("score") for c in tab.columns)
