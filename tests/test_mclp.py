"""Tests cho solver MCLP (B6).

Bất biến được khoá ở đây:
1. Nghiệm MILP = nghiệm vét cạn trên bài tí hon (đúng, không chỉ chạy được);
2. Greedy nằm giữa cận 1−1/e và MILP (dùng làm phương án phân rã khi solver đuối);
3. ``coverage_matrix`` cùng hệ quy chiếu với ``build_candidates._coverage_cells`` (C10);
4. Ràng buộc ≤1 candidate/ô **không** làm mất phủ — lý do cột ``n_existing_in_cell``
   tồn tại thay vì gỡ ràng buộc (đo 2026-07-29: chênh 0 ô / 0 dân toàn quốc).
"""

from itertools import combinations

import h3
import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

from ev_siting.features.build_candidates import _coverage_cells
from ev_siting.models import mclp

HANOI = (21.0278, 105.8342)


def _inst(A_dense, w, base_w=0.0):
    A = sp.csr_matrix(np.asarray(A_dense, dtype=np.int8))
    w = np.asarray(w, dtype=float)
    return mclp.Instance(
        scope="test", mode="greenfield",
        cand=pd.DataFrame({"h3_r8": [f"c{i}" for i in range(A.shape[0])]}),
        A=A, w=w, total_w=float(w.sum()) + base_w, reach_w=float(w.sum()) + base_w,
        base_w=base_w, n_dem_all=A.shape[1],
    )  # fmt: skip


def _brute_force(inst, p):
    """Vét cạn: tổng trọng số lớn nhất trên mọi tập con kích thước ≤ p."""
    A = inst.A.toarray().astype(bool)
    best = 0.0
    for k in range(p + 1):
        for pick in combinations(range(inst.n_cand), k):
            cov = np.zeros(inst.n_dem, dtype=bool)
            for i in pick:
                cov |= A[i]
            best = max(best, float(inst.w[cov].sum()))
    return best


@pytest.fixture
def tiny():
    #      ô:  0  1  2  3  4        trọng số: 10 1 1 1 1
    A = [
        [1, 1, 0, 0, 0],  # c0 — ô đắt tiền + 1 ô rẻ
        [1, 0, 1, 0, 0],  # c1 — chồng c0 ở ô 0
        [0, 0, 1, 1, 1],  # c2 — 3 ô rẻ, không chồng c0
        [0, 0, 0, 0, 1],
    ]  # c3 — bị c2 nuốt trọn
    return _inst(A, [10.0, 1.0, 1.0, 1.0, 1.0])  # fmt: skip


def test_milp_matches_brute_force(tiny):
    for p in (1, 2, 3):
        r = mclp.solve_mclp(tiny, p, time_limit=30)
        assert r["status"] == 0, r["message"]
        assert r["covered_w"] == pytest.approx(_brute_force(tiny, p), abs=1e-6)


def test_milp_respects_cardinality(tiny):
    r = mclp.solve_mclp(tiny, 1, time_limit=30)
    assert r["n_selected"] <= 1
    assert r["covered_w"] == pytest.approx(11.0)  # c0: ô 0 (10) + ô 1 (1)


def test_greedy_between_guarantee_and_optimum(tiny):
    for p in (1, 2, 3):
        opt = _brute_force(tiny, p)
        g = mclp.greedy_mclp(tiny, p)
        assert g["covered_w"] <= opt + 1e-9
        assert g["covered_w"] >= (1 - 1 / np.e) * opt - 1e-9


def test_greedy_stops_when_no_gain_left(tiny):
    g = mclp.greedy_mclp(tiny, p=10)  # chỉ 3 candidate là phủ hết
    assert g["n_selected"] <= 3
    assert g["covered_w"] == pytest.approx(float(tiny.w.sum()))


def test_cov_ratio_counts_brownfield_base():
    inst = _inst([[1, 0], [0, 1]], [1.0, 1.0], base_w=8.0)  # nền 8 + biên 2 = 10
    assert mclp._cov_ratio(inst, 1.0) == pytest.approx(0.9)
    assert mclp._cov_ratio(inst, np.nan) is None


def test_coverage_matrix_same_frame_as_build_candidates():
    """C10 — MCLP và tầng feature phải nhìn cùng một tập ô, không xấp xỉ lại."""
    center = h3.latlng_to_cell(*HANOI, 8)
    demand = sorted(h3.grid_disk(center, 6))
    A = mclp.coverage_matrix([center], np.array(demand), R_km=3.0)
    got = {demand[j] for j in A.indices}
    assert got == _coverage_cells(center, 3.0) & set(demand)
    mclp._assert_same_frame(np.array([center]), np.array(demand), A, 3.0)


def test_dedup_one_per_cell_loses_no_coverage():
    """Ràng buộc ≤1/ô nén số dòng nhưng KHÔNG nén phủ — hai trạm cùng ô phủ y hệt."""
    cell = h3.latlng_to_cell(*HANOI, 8)
    demand = np.array(sorted(h3.grid_disk(cell, 6)))
    many = np.array([cell] * 5)  # 5 trạm thật, cùng một ô
    union_many = np.asarray(mclp.coverage_matrix(many, demand).sum(axis=0)).ravel() > 0
    union_one = np.asarray(mclp.coverage_matrix(many[:1], demand).sum(axis=0)).ravel() > 0
    assert np.array_equal(union_many, union_one)


def test_budget_constraint_replaces_cardinality(tiny):
    """`costs`+`budget` là đường đi của hợp đồng CapEx §10 — cùng mô hình, đổi một hàng."""
    costs = np.array([5.0, 1.0, 1.0, 1.0])  # c0 đắt gấp 5
    r = mclp.solve_mclp(tiny, p=None, costs=costs, budget=2.0, time_limit=30)
    assert r["status"] == 0
    chosen = set(r["_chosen"])
    assert 0 not in chosen, "c0 (giá 5) không thể mua nổi với ngân sách 2"
    assert costs[list(chosen)].sum() <= 2.0 + 1e-9


@pytest.mark.parametrize(
    "status,gap,want",
    [
        (0, 0.0, "OPTIMAL"),
        (1, 0.002, "NEAR_OPTIMAL"),
        (1, 0.08, "NOT_SOLVED"),
        (1, None, "NOT_SOLVED"),
        (0, 0.005, "NEAR_OPTIMAL"),
    ],
)
def test_verdict_is_three_valued_not_vibes(status, gap, want):
    """Phán quyết B6 phải là hàm của (status, gap), không phải cảm nhận khi đọc log."""
    assert mclp._verdict({"status": status, "mip_gap": gap}).startswith(want)
