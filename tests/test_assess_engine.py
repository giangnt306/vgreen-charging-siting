"""Test engine assess() — golden bằng construction trên lưới synthetic, không data thật.

Chiến thuật như test kernel: pop đặt vào ĐÚNG ô lấy từ ``kernel.point_cells`` của
từng vị trí, ref tự dựng 20 dòng phân bố biết trước ⇒ mọi percentile/score kỳ vọng
tính được bằng tay theo định nghĩa ECDF đóng băng (pre-reg §4), không phụ thuộc
hình dạng lưới H3. Context dựng THỦ CÔNG (không make_context) — engine chỉ được
đọc context qua thuộc tính dataclass nên test cũng là hợp đồng interface.
"""

import json
from types import SimpleNamespace

import h3
import numpy as np
import pandas as pd
import pytest

from ev_siting.aoi import haversine_km
from ev_siting.assess import credit, engine, kernel, params

# A: trạm nền duy nhất (Hà Nội). F/L/M: ba vùng cô lập >40 km khỏi A và khỏi nhau.
LAT_A, LNG_A = 21.0278, 105.8342
LAT_F, LNG_F = 20.75, 105.5
LAT_L, LNG_L = 22.5, 106.5
LAT_M, LNG_M = 20.3, 104.8

POP_A_CELL, POP_F_CELL = 400.0, 400.0
POP_L, POP_M = 5.0, 10.5  # M = 10.5 nằm GIỮA rho ref 1..20 ⇒ v_pressure = 50 đúng công thức

BBOX = [8.0, 102.0, 23.7, 110.0]  # [lat_min, lng_min, lat_max, lng_max] — quy ước aoi.to_dict


def _lng_offset(lat, lng, km):
    """Dịch đông-tây ~km; khoảng cách thật luôn được đo lại bằng haversine trong test."""
    return lng + km / (np.pi / 180.0 * 6371.0088 * np.cos(np.radians(lat)))


LNG_NEAR = _lng_offset(LAT_A, LNG_A, 0.1)  # điểm sát trạm A ~100 m (< NEAR_EXISTING_M)
LNG_F2 = _lng_offset(LAT_F, LNG_F, 0.1)  # điểm thứ hai của lô plan, ~100 m sau F


@pytest.fixture(scope="module")
def covered0():
    df = pd.DataFrame({"station_id": ["st-a"], "lat": [LAT_A], "lng": [LNG_A], "num_connectors": [2]})
    df["h3_r8"] = [h3.latlng_to_cell(LAT_A, LNG_A, 8)]
    return df


@pytest.fixture(scope="module")
def net(covered0):
    return kernel.build_network(covered0)


@pytest.fixture(scope="module")
def dem():
    """Pop đặt vào giao cov(A) ∩ cov(P_near) để local của CẢ HAI điểm quanh A = 1200 chính xác."""
    cov_a = kernel.point_cells(LAT_A, LNG_A)
    cov_near = kernel.point_cells(LAT_A, LNG_NEAR)
    cells_a = sorted(cov_a & cov_near)[:3]
    cells_f = sorted(kernel.point_cells(LAT_F, LNG_F))[:5]
    cell_l = h3.latlng_to_cell(LAT_L, LNG_L, 8)
    cell_m = h3.latlng_to_cell(LAT_M, LNG_M, 8)
    return pd.Series(
        [POP_A_CELL] * 3 + [POP_F_CELL] * 5 + [POP_L, POP_M],
        index=pd.Index(cells_a + cells_f + [cell_l, cell_m], name="h3_r8"),
        name="pop",
        dtype=float,
    )


@pytest.fixture(scope="module")
def ref_main():
    """Phân bố tham chiếu "khó": marginal/local 100..2000 ⇒ điểm nhỏ rơi p0, rho 1..20."""
    return pd.DataFrame(
        {
            "n_marginal_pop": np.linspace(100.0, 2000.0, 20),
            "v_demand_local": np.linspace(100.0, 2000.0, 20),
            "v_competition": np.full(20, 5.0),
            "rho": np.arange(1.0, 21.0),
        }
    )


@pytest.fixture(scope="module")
def ref_easy():
    """Phân bố "dễ": mọi ref = 0/nhỏ ⇒ điểm quanh A đạt score cao — dùng ép kịch bản G2 cap."""
    return pd.DataFrame(
        {
            "n_marginal_pop": np.zeros(20),
            "v_demand_local": np.full(20, 10.0),
            "v_competition": np.full(20, 5.0),
            "rho": np.zeros(20),
        }
    )


def make_actx(net, dem, ref, occ=None, cand_by_cell=None):
    if occ is None:
        # Trạm A có telemetry đạt sàn: utilization = 0,8/2 = 0,4 ≥ OCC_HIGH_BAND ⇒ test R09.
        occ = pd.DataFrame(
            {"station_id": ["st-a"], "occ_mean_dw": [0.8], "duration_coverage": [0.9], "num_connectors": [2]}
        )
    if cand_by_cell is None:
        cand_by_cell = pd.DataFrame(
            {"penalty_flags": [["NO_ROAD_ACCESS", "NOT_BUILT_UP"]], "tier": ["T4"]},
            index=pd.Index([h3.latlng_to_cell(LAT_L, LNG_L, 8)], name="h3_r8"),
        )
    return engine.AssessContext(
        bundle=SimpleNamespace(aoi={"bbox": BBOX}),
        dem=dem,
        net=net,
        ref=ref,
        occ=occ,
        credit_rule="shapley",
        mode="live",
        cand_by_cell=cand_by_cell,
    )


def _pts(*latlngs):
    return pd.DataFrame(latlngs, columns=["lat", "lng"])


def _has(reasons, code):
    return any(r.startswith(code) for r in reasons)


def test_g1_bad_points_review_r03(net, dem, ref_main, tmp_path):
    # 3 kiểu G1: ngoài bbox, toạ độ NaN, trong bbox nhưng ngoài lưới cầu — tất cả
    # phải là Cần review + R03 + score NaN, KHÔNG BAO GIỜ Từ chối (pre-reg §4 G1).
    actx = make_actx(net, dem, ref_main)
    out = engine.assess(_pts((0.0, 0.0), (np.nan, 105.8), (95.0, 105.8), (9.0, 103.0)), actx,
                        log_path=tmp_path / "log.jsonl")  # fmt: skip
    assert list(out["tier"]) == [params.TIER_REVIEW] * 4
    for _, row in out.iterrows():
        assert row["gates_fired"] == ["G1"]
        assert _has(row["reasons"], "R03")
        for col in ("score_total", "score_N", "score_V", "n_marginal_pop", "v_demand_local", "occ_local"):
            assert np.isnan(row[col])


def test_g2_caps_high_score_near_station(net, dem, ref_easy, tmp_path):
    # Điểm ~100 m cạnh trạm A với ref "dễ" đạt score_total ≥ 60 — nhưng G2 phải chặn
    # trần xuống Cần review (kịch bản chết B: "cách 200 m có trạm rồi").
    d_m = haversine_km(LAT_A, LNG_NEAR, LAT_A, LNG_A) * 1000.0
    assert 50 < d_m < params.NEAR_EXISTING_M
    actx = make_actx(net, dem, ref_easy)
    out = engine.assess(_pts((LAT_A, LNG_NEAR)), actx, log_path=tmp_path / "log.jsonl")
    row = out.iloc[0]
    assert row["score_total"] >= params.THRESH_ACCEPT  # điểm cao thật — cap mới có ý nghĩa
    assert row["tier"] == params.TIER_REVIEW
    assert "G2" in row["gates_fired"]
    assert _has(row["reasons"], "R01")
    # occ enrichment đi kèm: trạm A đạt sàn, utilization 0,4 ⇒ R09 nhưng KHÔNG đổi score.
    assert row["occ_local"] == pytest.approx(0.4)
    assert _has(row["reasons"], "R09")


def test_score_n_ranks_uncovered_above_covered(net, dem, ref_main, tmp_path):
    # F phủ 2000 pop chưa ai phủ; điểm tại A phủ vùng đã kín (marginal 0) —
    # trục N phải xếp F trên hẳn, bất kể "chỗ đông" (I-1).
    actx = make_actx(net, dem, ref_main)
    out = engine.assess(_pts((LAT_F, LNG_F), (LAT_A, LNG_A)), actx, log_path=tmp_path / "log.jsonl")
    f, a = out.iloc[0], out.iloc[1]
    assert f["n_marginal_pop"] == pytest.approx(5 * POP_F_CELL)
    assert a["n_marginal_pop"] == pytest.approx(0.0)
    assert f["score_N"] > a["score_N"]
    assert f["score_N"] == pytest.approx(97.5)  # ECDF: 19 strictly-below + ½·1 tie trên 20
    assert a["score_N"] == pytest.approx(0.0)


def test_pressure_is_percentile_once(net, dem, ref_main, tmp_path):
    # M: rho = 10,5 nằm giữa ref 1..20 ⇒ v_pressure = 50 ĐÚNG một lần pctl; nếu engine
    # pctl thêm lần nữa thì 50 (trên phân bố 1..20) thành 100 và score_V lệch hẳn.
    actx = make_actx(net, dem, ref_main)
    out = engine.assess(_pts((LAT_M, LNG_M)), actx, log_path=tmp_path / "log.jsonl")
    row = out.iloc[0]
    assert row["v_pressure"] == pytest.approx(50.0)
    # score_V = mean(pctl(local)=0, 100−pctl(comp)=100, v_pressure=50) — 50 vào nguyên trạng.
    assert row["score_V"] == pytest.approx((0.0 + 100.0 + 50.0) / 3.0)


def test_renormalize_when_pressure_and_occ_nan(net, dem, ref_main, tmp_path):
    # ref.rho toàn NaN ⇒ v_pressure NaN ⇒ score_V renormalize trên 2 thành phần còn lại;
    # M không có trạm nào trong R ⇒ occ_local NaN — và occ vốn không được vào score.
    ref_nan = ref_main.assign(rho=np.nan)
    actx = make_actx(net, dem, ref_nan)
    out = engine.assess(_pts((LAT_M, LNG_M)), actx, log_path=tmp_path / "log.jsonl")
    row = out.iloc[0]
    assert np.isnan(row["v_pressure"])
    assert np.isnan(row["occ_local"])
    assert row["score_V"] == pytest.approx((0.0 + 100.0) / 2.0)


def test_plan_batch_conflict_and_shapley_split(net, dem, ref_main, tmp_path):
    # Lô 2 điểm cách ~100 m: điểm VÀO SAU bị G3/R02; marginal chia theo Shapley —
    # đối chiếu TRỰC TIẾP credit.split_marginal (ô chồng lấn k=2 ⇒ mỗi điểm pop/2).
    d_m = haversine_km(LAT_F, LNG_F, LAT_F, LNG_F2) * 1000.0
    assert 50 < d_m < params.BATCH_CONFLICT_M
    actx = make_actx(net, dem, ref_main)
    out = engine.assess(_pts((LAT_F, LNG_F), (LAT_F, LNG_F2)), actx, plan=True, log_path=tmp_path / "log.jsonl")

    cells = [kernel.point_cells(LAT_F, LNG_F), kernel.point_cells(LAT_F, LNG_F2)]
    expected = credit.split_marginal(cells, net.covered_cells, dem, "shapley")
    assert list(out["n_marginal_pop"]) == pytest.approx(expected)
    # Tổng bảo toàn (submodular): hai điểm chia nhau đúng 2000 pop biên, không đếm đôi.
    assert sum(expected) == pytest.approx(5 * POP_F_CELL)
    assert min(expected) > 0

    first, second = out.iloc[0], out.iloc[1]
    assert "G3" not in first["gates_fired"] and not _has(first["reasons"], "R02")
    assert "G3" in second["gates_fired"] and _has(second["reasons"], "R02")
    assert second["tier"] != params.TIER_ACCEPT  # cap trần


def test_version_labels_on_every_row(net, dem, ref_main, tmp_path):
    actx = make_actx(net, dem, ref_main)
    out = engine.assess(_pts((LAT_F, LNG_F), (0.0, 0.0), (LAT_A, LNG_A)), actx, log_path=tmp_path / "log.jsonl")
    assert list(out.columns) == engine._OUT_COLS  # thứ tự cột đóng băng
    assert (out["data_version"] == params.DATA_VERSION).all()
    assert (out["model_version"] == params.MODEL_VERSION).all()
    assert (out["calibration"] == params.CALIBRATION_LABEL).all()
    assert out["vault_tos_restricted"].all()
    assert (out["mode"] == "live").all()
    assert (out["credit_rule"] == "shapley").all()


def test_log_jsonl_one_line_per_point(net, dem, ref_main, tmp_path):
    actx = make_actx(net, dem, ref_main)
    log = tmp_path / "assess_log.jsonl"
    engine.assess(_pts((LAT_F, LNG_F), (LAT_M, LNG_M), (0.0, 0.0)), actx, log_path=log)
    engine.assess(_pts((LAT_L, LNG_L), (LAT_A, LNG_A)), actx, log_path=log)  # append, không ghi đè
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 5
    for rec in lines:
        for key in ("run_id", "assessed_at", "point_id", "tier", "score_total", "mode",
                    "data_version", "model_version", "calibration"):  # fmt: skip
            assert key in rec
    assert len({r["run_id"] for r in lines[:3]}) == 1  # cùng lần gọi = cùng run_id
    assert lines[0]["run_id"] != lines[3]["run_id"]  # hai lần gọi khác run_id


def test_reject_needs_low_score_and_full_v(net, dem, ref_main, tmp_path):
    # L: score_total ~20 < 30 với đủ 3 thành phần V ⇒ Từ chối; CÙNG điểm đó nhưng
    # thiếu v_pressure (ref.rho NaN) ⇒ chỉ được Cần review dù điểm vẫn thấp (pre-reg §4).
    actx = make_actx(net, dem, ref_main)
    out = engine.assess(_pts((LAT_L, LNG_L)), actx, log_path=tmp_path / "log.jsonl")
    row = out.iloc[0]
    assert row["score_total"] < params.THRESH_REJECT
    assert row["tier"] == params.TIER_REJECT
    assert _has(row["reasons"], "R11")  # ô L nằm trong cand_by_cell với cờ khảo sát + T4
    assert _has(row["reasons"], "R10")  # không trạm nào trong 1 km

    actx_nan = make_actx(net, dem, ref_main.assign(rho=np.nan))
    out2 = engine.assess(_pts((LAT_L, LNG_L)), actx_nan, log_path=tmp_path / "log.jsonl")
    row2 = out2.iloc[0]
    assert row2["score_total"] < params.THRESH_REJECT
    assert row2["tier"] == params.TIER_REVIEW


# ---------------------------------------------------------------------------- #
# Regression cho vòng adversarial 28/07 (Addendum pre-reg) — C13/C16/C18/C7/C6/C1
# ---------------------------------------------------------------------------- #


def test_credit_rule_stamp_is_effective_rule(net, dem, ref_main, tmp_path):
    # C16: nhãn phải nói đúng cách số được tính — 1 điểm (auto plan=False) chấm solo
    # thì đóng dấu "solo", dù context cấu hình shapley.
    actx = make_actx(net, dem, ref_main)
    one = engine.assess(_pts((LAT_L, LNG_L)), actx, log_path=tmp_path / "log.jsonl")
    assert (one["credit_rule"] == "solo").all()
    two = engine.assess(_pts((LAT_F, LNG_F), (LAT_F, LNG_F2)), actx, plan=True, log_path=tmp_path / "log.jsonl")
    assert (two["credit_rule"] == "shapley").all()


def test_auto_plan_default_multi_point_fires_g3(net, dem, ref_main, tmp_path):
    # C18/Addendum: |P|>1 không truyền plan ⇒ tự vào plan mode (pre-reg §1) — điểm
    # vào sau cách ~100 m phải dính G3, không cần người gọi nhớ bật cờ.
    actx = make_actx(net, dem, ref_main)
    out = engine.assess(_pts((LAT_F, LNG_F), (LAT_F, LNG_F2)), actx, log_path=tmp_path / "log.jsonl")
    assert "G3" in out.iloc[1]["gates_fired"] and _has(out.iloc[1]["reasons"], "R02")


def test_three_credit_columns_and_redundancy_from_solo(net, dem, ref_main, tmp_path):
    # C6/C17: |P|>1 xuất đủ 3 biến thể marginal; C7: n_redundancy đo vs NỀN (solo),
    # không bị phần chia công nội lô làm sai fact — 2 điểm trùng chỗ F (N không phủ F):
    # solo = full pop, shapley = một nửa, redundancy phải = 0 (N chưa phủ gì ở F).
    actx = make_actx(net, dem, ref_main)
    out = engine.assess(_pts((LAT_F, LNG_F), (LAT_F, LNG_F)), actx, plan=True, log_path=tmp_path / "log.jsonl")
    r = out.iloc[0]
    assert r["n_marginal_pop_solo"] == pytest.approx(2000.0)  # 5 ô × 400
    assert r["n_marginal_pop_shapley"] == pytest.approx(1000.0)
    assert r["n_marginal_pop_last_in"] == pytest.approx(0.0)
    assert r["n_marginal_pop"] == pytest.approx(1000.0)  # score dùng rule context (shapley)
    assert r["n_redundancy"] == pytest.approx(0.0)  # từ solo vs nền, KHÔNG phải 1 − 1000/2000


def test_redact_coords_in_log_keeps_output_intact(net, dem, ref_main, tmp_path):
    # C1/C15: lô toạ độ vault — log JSONL không được mang lat/lng, nhưng DataFrame
    # trả về (RAM) vẫn đủ toạ độ cho caller tính toán.
    actx = make_actx(net, dem, ref_main)
    log = tmp_path / "log.jsonl"
    out = engine.assess(_pts((LAT_L, LNG_L)), actx, log_path=log, redact_coords_in_log=True)
    assert np.isfinite(out.iloc[0]["lat"]) and np.isfinite(out.iloc[0]["lng"])
    rec = json.loads(log.read_text().strip().splitlines()[0])
    assert "lat" not in rec and "lng" not in rec
    assert rec["coords_redacted"] is True


def test_reject_never_without_reason_r12(net, dem, tmp_path):
    # C13: dựng ref sao cho điểm giữa (cách A ~500 m) rơi đúng khe "Từ chối mà không
    # reason nào khác kích hoạt" — R12 phải xuất hiện với con số fact.
    lng_mid = _lng_offset(LAT_A, LNG_A, 0.5)
    ref = pd.DataFrame(
        {
            "n_marginal_pop": [-1.0] * 7 + [1.0] * 13,  # pctl(0) = 35 ⇒ không R04/R05
            "v_demand_local": [1000.0] * 7 + [2000.0] * 13,  # pctl(1200) = 35 ⇒ không R06
            "v_competition": [0.0] * 17 + [2.0] * 3,  # pctl(1) = 85 < 90 ⇒ không R07
            "rho": [1.0] * 2 + [10_000.0] * 18,  # pctl(400) = 10 < 60 ⇒ không R08
        }
    )
    occ_cold = pd.DataFrame(
        {"station_id": ["st-a"], "occ_mean_dw": [0.8], "duration_coverage": [0.1], "num_connectors": [2]}
    )  # dưới sàn coverage ⇒ occ_local NaN ⇒ không R09
    actx = make_actx(net, dem, ref, occ=occ_cold)
    out = engine.assess(_pts((LAT_A, lng_mid)), actx, log_path=tmp_path / "log.jsonl")
    row = out.iloc[0]
    assert row["tier"] == params.TIER_REJECT
    assert row["reasons"], "Từ chối trắng lý do — vi phạm hợp đồng BO"
    assert _has(row["reasons"], "R12")


def test_occ_utilization_clipped_and_zero_connector_excluded(net, dem, ref_main, tmp_path):
    # C10/P3/P6: trạm occ > connectors bị clip 1.0 (không in "bận 160%"); trạm 0 cổng
    # bị loại khỏi pool occ_local thay vì sinh inf.
    occ = pd.DataFrame(
        {
            "station_id": ["st-a", "st-zero"],
            "occ_mean_dw": [3.2, 5.0],
            "duration_coverage": [0.9, 0.9],
            "num_connectors": [2, 0],
        }
    )
    actx = make_actx(net, dem, ref_main, occ=occ)
    out = engine.assess(_pts((LAT_A, _lng_offset(LAT_A, LNG_A, 0.5))), actx, log_path=tmp_path / "log.jsonl")
    assert out.iloc[0]["occ_local"] == pytest.approx(1.0)  # clip(3.2/2)=1.0; st-zero bị loại
