"""Tests cho tầng luật đặt trạm của BO (``models/rules.py``, chốt 2026-07-29).

Bất biến được khoá ở đây:

1. **B0** — nghiệm không bao giờ được đụng vào trạm đã triển khai;
2. **R8 encode CHÍNH XÁC** — clique một mình là encode *sai luật*, không phải encode
   yếu: cặp cách nhau giữa ``D/2`` và ``D`` không nằm trong quả cầu nào. Test kiểm cả
   hai chiều (không sót cặp xung đột · không cấm nhầm cặp hợp lệ) trên điểm ngẫu nhiên;
3. **R5/R6/R4** — luật khoảng cách chỉ áp ở xã, có nới cho cao tải, miễn ở đô thị;
4. **R2** — một trụ DC là đủ để trạm được tính vào mạng; thiếu bảng trụ thì KHÔNG loại ngầm;
5. **Nối hai hướng sản phẩm** — mọi điểm bộ sinh chọn phải qua được bộ chấm.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.neighbors import BallTree

from ev_siting.models import rules as rl

HANOI = (21.0278, 105.8342)
DEG_PER_M = 1.0 / 111_320.0


def _line(n, step_m, lat=21.0, lng=105.0):
    """n điểm thẳng hàng, cách đều ``step_m`` — hình học kiểm được bằng tay.

    Chia cho ``cos(lat)``: một độ KINH tuyến ở 21°N chỉ dài 111,32·cos(21°) ≈ 103,9 km,
    quên chỗ này thì mọi khoảng cách trong test lệch 6,6% và test đo nhầm thứ khác.
    """
    return np.full(n, lat), lng + np.arange(n) * step_m * DEG_PER_M / np.cos(np.radians(lat))


def _at(offset_m, lat=21.0, lng=105.0):
    """Một điểm cách (lat, lng) đúng ``offset_m`` về phía đông."""
    return _line(2, offset_m, lat, lng)[0][1:], _line(2, offset_m, lat, lng)[1][1:]


def _pairs_within(lat, lng, d_m):
    X = np.radians(np.c_[lat, lng])
    t = BallTree(X, metric="haversine")
    return {(i, int(j)) for i, nb in enumerate(t.query_radius(X, r=d_m / rl.R_EARTH_M)) for j in nb if int(j) > i}


# ─────────────────────────────── B0 · bất khả xâm phạm ──────────────────────────


def test_b0_rejects_touching_deployed_station():
    with pytest.raises(rl.ExistingStationTouched, match="B0 FAIL"):
        rl.assert_existing_untouched(["c1", "c2"], ["c2", "c9"])


def test_b0_passes_when_solution_only_adds():
    rl.assert_existing_untouched(["c1", "c2"], ["c8", "c9"])  # không ném là đạt


# ──────────────────────────────── R8 · encode chính xác ─────────────────────────


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_r8_rows_are_exact_not_merely_valid(seed):
    """Hai chiều: (a) không cặp xung đột nào lọt lưới; (b) không hàng nào cấm nhầm.

    (a) là chỗ clique-một-mình sai — nó bỏ sót đúng dải ``D/2 < d < D``.
    """
    rng = np.random.default_rng(seed)
    lat = HANOI[0] + rng.normal(0, 0.02, 40)
    lng = HANOI[1] + rng.normal(0, 0.02, 40)
    D = 2000.0
    M, meta = rl.conflict_rows(lat, lng, D)

    conflicting = _pairs_within(lat, lng, D)
    covered = set()
    for r in range(M.shape[0]):
        mem = sorted(int(x) for x in M[r].indices)
        for a in range(len(mem)):
            for b in range(a + 1, len(mem)):
                covered.add((mem[a], mem[b]))

    assert conflicting <= covered, f"lọt lưới {len(conflicting - covered)} cặp xung đột"
    assert covered <= conflicting, f"cấm nhầm {len(covered - conflicting)} cặp hợp lệ"
    assert meta["n_conflict_pairs"] == len(conflicting)


def test_r8_clique_beats_pairwise_row_count():
    """Clique phải NÉN được: 5 điểm sát nhau cho 1 hàng chứ không 10 hàng cặp."""
    lat, lng = _line(5, 100)  # mọi cặp đều < 2 km
    M, meta = rl.conflict_rows(lat, lng, 2000.0)
    assert meta["n_conflict_pairs"] == 10
    assert meta["n_clique"] == 1 and meta["n_pair"] == 0
    assert M.shape[0] == 1 and M[0].nnz == 5


def test_r8_needs_residual_pairs_for_the_middle_band():
    """Hai điểm cách 1,2 km (giữa D/2=1 km và D=2 km) — clique KHÔNG bao nổi."""
    lat, lng = _line(2, 1200)
    M, meta = rl.conflict_rows(lat, lng, 2000.0)
    assert meta["n_conflict_pairs"] == 1
    assert meta["n_clique"] == 0, "quả cầu D/2 không thể chứa cả hai"
    assert meta["n_pair"] == 1, "phải rơi xuống hàng cặp, nếu không là encode SAI luật"


def test_r8_empty_when_rule_off():
    lat, lng = _line(4, 100)
    M, meta = rl.conflict_rows(lat, lng, 0.0)
    assert M.shape[0] == 0 and meta["n_conflict_pairs"] == 0


def test_violates_mutual_flags_both_members():
    lat = np.array([21.0, 21.0, 21.0])
    lng = np.array([105.0, 105.0 + 500 * DEG_PER_M / np.cos(np.radians(21.0)), 105.2])
    assert list(rl.violates_mutual(lat, lng, 2000.0)) == [True, True, False]


# ───────────────────────────── R5/R6/R4 · khoảng cách ───────────────────────────


def test_r5_binds_in_rural_and_r4_exempts_urban():
    net_lat, net_lng = np.array([21.0]), np.array([105.0])
    cl, cg = _at(1500)  # cách trạm 1,5 km về phía đông
    ok_rural, d, req = rl.clearance_ok(cl, cg, net_lat, net_lng, [True], [False])
    assert not ok_rural[0] and req[0] == 2000.0
    assert d[0] == pytest.approx(1500, rel=0.02)

    ok_urban, _, req_u = rl.clearance_ok(cl, cg, net_lat, net_lng, [False], [False])
    assert ok_urban[0] and req_u[0] == 0.0, "R4 — đô thị không áp luật khoảng cách"


def test_r6_relaxes_rural_threshold_for_highload():
    net_lat, net_lng = np.array([21.0]), np.array([105.0])
    cl, cg = _at(800)  # 800 m: thua ngưỡng 2 km, thắng ngưỡng 500 m
    assert not rl.clearance_ok(cl, cg, net_lat, net_lng, [True], [False])[0][0]
    assert rl.clearance_ok(cl, cg, net_lat, net_lng, [True], [True])[0][0]


def test_clearance_on_empty_network_admits_everything():
    cl, cg = _line(3, 100)
    ok, d, _ = rl.clearance_ok(cl, cg, np.array([]), np.array([]), [True], [False])
    assert ok.all() and np.isinf(d).all()


# ──────────────────────────────────── R2 · AC/DC ────────────────────────────────


def _st(ids, current=None):
    return pd.DataFrame({"station_id": ids, "current_type": current or [None] * len(ids)})


def test_r2_one_dc_connector_is_enough():
    conn = pd.DataFrame(
        {
            "station_id": ["a", "a", "b", "b", "c"],
            "current_type": ["AC", "DC", "AC", "AC", "UNKNOWN"],
            "power_kw": [11.0, 60.0, 7.4, 11.0, 11.0],
        }
    )
    kept = rl.apply_r2(_st(["a", "b", "c"]), conn)
    assert set(kept["station_id"]) == {"a"}, "b chỉ-AC phải rời S₀; a có 1 trụ DC là đủ"
    assert kept.loc[0, "max_conn_kw"] == 60.0


def test_r2_missing_connector_rows_fall_back_not_dropped_silently():
    """P8 bước 6 — giữ UNKNOWN, không suy diễn. Trạm thiếu bảng trụ dùng cột station."""
    conn = pd.DataFrame({"station_id": ["a"], "current_type": ["DC"], "power_kw": [60.0]})
    kept = rl.apply_r2(_st(["a", "z"], current=["DC", "DC"]), conn)
    assert set(kept["station_id"]) == {"a", "z"}


def test_r2_can_be_switched_off():
    conn = pd.DataFrame({"station_id": ["b"], "current_type": ["AC"], "power_kw": [11.0]})
    kept = rl.apply_r2(_st(["b"]), conn, rl.RuleSet(require_dc=False))
    assert len(kept) == 1


@pytest.mark.parametrize(
    "kw,band",
    [(11, "AC(<20)"), (30, "DC 20/30"), (60, "DC 60/80"), (120, "DC 120/150"), (250, "DC 250/300")],
)
def test_r9_power_bands_land_on_the_named_class(kw, band):
    assert rl.power_band(pd.Series([kw]))[0] == band


# ──────────────────────────── hướng B · phán quyết ba mức ───────────────────────


def test_verdict_rejects_only_with_a_named_rule():
    v, why = rl.verdict(1200.0, 2000.0, is_rural=True)
    assert v is rl.Verdict.REJECT
    assert any(r.startswith("R5/R6_MIN_DISTANCE") for r in why)
    assert any("1200 m" in r and "2000 m" in r for r in why), "phải nêu SỐ ĐO, không chỉ tên luật"


def test_verdict_urban_passes_and_says_r7_is_missing():
    v, why = rl.verdict(300.0, 0.0, is_rural=False)
    assert v is rl.Verdict.OK
    assert any(r.startswith("R4_URBAN_EXEMPT") for r in why)
    assert any("R7_NOT_APPLIED" in r for r in why), "nợ đã khai phải hiện trong hồ sơ, không im lặng"


def test_verdict_overlap_downgrades_to_review_not_reject():
    v, why = rl.verdict(5000.0, 2000.0, is_rural=True, conflicts_with_other_proposal=True)
    assert v is rl.Verdict.REVIEW, "R8 gắn cờ để làm việc lại với NPP, KHÔNG từ chối"
    assert any(r.startswith("R8_PROPOSAL_OVERLAP") for r in why)


def test_verdict_reject_wins_over_review():
    v, _ = rl.verdict(100.0, 2000.0, is_rural=True, conflicts_with_other_proposal=True)
    assert v is rl.Verdict.REJECT


def test_verdict_never_returns_a_score():
    _, why = rl.verdict(5000.0, 2000.0, is_rural=True)
    joined = " ".join(why).lower()
    assert "score" not in joined and "điểm số" not in joined


# ─────────────────── nối hai hướng: bộ sinh không đề xuất thứ bộ chấm loại ──────


def test_generator_output_always_passes_the_gate():
    """Bất biến hợp đồng: ∀ q ∈ nghiệm, ``verdict(q) ≠ KHÔNG_PHÊ_DUYỆT``.

    Dựng tay một tập ứng viên có cả điểm hợp lệ lẫn điểm vi phạm, chạy tiền lọc rồi
    chấm lại từng điểm sống sót — hai tầng phải nói cùng một câu.
    """
    rng = np.random.default_rng(7)
    lat = 21.0 + rng.normal(0, 0.03, 60)
    lng = 105.0 + rng.normal(0, 0.03, 60)
    net_lat, net_lng = 21.0 + rng.normal(0, 0.03, 8), 105.0 + rng.normal(0, 0.03, 8)
    is_rural = rng.random(60) < 0.6
    rules = rl.RuleSet()

    ok, d_near, d_req = rl.clearance_ok(lat, lng, net_lat, net_lng, is_rural, False, rules)
    assert ok.sum() and (~ok).sum(), "kịch bản phải có cả hai phía, nếu không test rỗng nghĩa"

    for i in np.flatnonzero(ok):
        v, _ = rl.verdict(d_near[i], d_req[i], is_rural=bool(is_rural[i]), rules=rules)
        assert v is not rl.Verdict.REJECT
    for i in np.flatnonzero(~ok):
        v, _ = rl.verdict(d_near[i], d_req[i], is_rural=bool(is_rural[i]), rules=rules)
        assert v is rl.Verdict.REJECT


def test_ruleset_clearance_is_vectorised_and_matches_scalar():
    r = rl.RuleSet()
    got = r.clearance_m([True, True, False], [False, True, True])
    assert list(got) == [2000.0, 500.0, 0.0]
