"""Test chia công n_marginal_pop (``assess/credit.py``) — đối chiếu Shapley brute-force.

Dữ liệu synthetic thuần tập-hợp (tên ô là chuỗi tuỳ ý): công thức chia công không
phụ thuộc hình học H3, chỉ phụ thuộc cấu trúc phủ/chồng lấn, nên test nhỏ là đủ
để pin đúng ngữ nghĩa pre-reg §1 mà không cần đọc data thật.
"""

import itertools

import pandas as pd
import pytest

from ev_siting.assess import params
from ev_siting.assess.credit import split_marginal

# Lô 4 điểm chồng lấn BẤT ĐỐI XỨNG + nền covered che một phần: x đã bị nền phủ
# (pop lớn để lộ bug nếu quên trừ nền), d đã phủ, y không có trong dem (pop 0).
DEM = {"a": 10.0, "b": 20.0, "c": 5.0, "d": 40.0, "e": 8.0, "f": 3.0, "x": 100.0}
COVERED = frozenset({"x", "d"})
POINTS_4 = [
    frozenset({"a", "b", "c", "x"}),
    frozenset({"b", "c", "d"}),
    frozenset({"c", "d", "e", "y"}),
    frozenset({"a", "e", "f"}),
]


def _pop(cells, dem):
    return sum(dem.get(c, 0.0) for c in cells)


def _brute_shapley(cells_per_point, covered, dem):
    """Định nghĩa GỐC của Shapley: trung bình marginal-gain trên TOÀN BỘ hoán vị."""
    n = len(cells_per_point)
    perms = list(itertools.permutations(range(n)))
    totals = [0.0] * n
    for perm in perms:
        seen = set(covered)
        for i in perm:
            totals[i] += _pop(cells_per_point[i] - seen, dem)
            seen |= cells_per_point[i]
    return [t / len(perms) for t in totals]


@pytest.mark.parametrize("n", [2, 3, 4])
def test_shapley_equals_brute_force(n):
    # Công thức đóng phải trùng brute-force ở mọi cỡ lô — đây là chỗ dễ sai nhất
    # nếu ai đó "tối ưu" lại mà quên tiền đề submodular.
    pts = POINTS_4[:n]
    got = split_marginal(pts, COVERED, DEM, rule="shapley")
    assert got == pytest.approx(_brute_shapley(pts, COVERED, DEM))


def test_disjoint_sets_all_rules_equal():
    # Không chồng lấn nội lô ⇒ thứ tự vào không đổi marginal ⇒ ba rule phải trùng nhau.
    pts = [frozenset({"a"}), frozenset({"b", "c"}), frozenset({"f"})]
    results = {rule: split_marginal(pts, COVERED, DEM, rule=rule) for rule in params.CREDIT_RULES}
    assert results["solo"] == results["last_in"] == results["shapley"]
    assert results["solo"] == pytest.approx([10.0, 25.0, 3.0])


def test_shapley_conserves_total_marginal_pop():
    # Tính chất efficiency của Shapley: tổng chia công = đúng tổng giá trị lô tạo ra,
    # không phồng không hụt — solo/last_in cố tình KHÔNG có tính chất này.
    got = split_marginal(POINTS_4, COVERED, DEM, rule="shapley")
    union = frozenset().union(*POINTS_4)
    assert sum(got) == pytest.approx(_pop(union - COVERED, DEM))


def test_last_in_le_shapley_le_solo():
    solo = split_marginal(POINTS_4, COVERED, DEM, rule="solo")
    shap = split_marginal(POINTS_4, COVERED, DEM, rule="shapley")
    last = split_marginal(POINTS_4, COVERED, DEM, rule="last_in")
    for lo, mid, hi in zip(last, shap, solo):
        assert lo <= mid + 1e-9
        assert mid <= hi + 1e-9
    # Case chồng lấn thật sự: ba mức phải tách hẳn ở ít nhất một điểm,
    # nếu không test trên chỉ đang kiểm bộ ba số trùng nhau.
    assert any(lo < mid < hi for lo, mid, hi in zip(last, shap, solo))


def test_single_point_batch_all_rules_equal_solo():
    # |P| = 1: không có ai để chia ⇒ mọi rule phải rơi về solo.
    pts = [POINTS_4[0]]
    expected = [_pop(POINTS_4[0] - COVERED, DEM)]
    for rule in params.CREDIT_RULES:
        assert split_marginal(pts, COVERED, DEM, rule=rule) == pytest.approx(expected)


def test_dem_as_series_matches_dict_and_returns_plain_floats():
    # API nhận cả pd.Series (bảng cầu thật là Series index=ô) — kết quả phải y hệt
    # dict và là float thuần (JSON-serializable cho assess_log, không numpy scalar).
    ser = pd.Series(DEM)
    for rule in params.CREDIT_RULES:
        got = split_marginal(POINTS_4, COVERED, ser, rule=rule)
        assert got == pytest.approx(split_marginal(POINTS_4, COVERED, DEM, rule=rule))
        assert all(type(v) is float for v in got)


def test_unknown_rule_raises_value_error_listing_rules():
    with pytest.raises(ValueError) as exc:
        split_marginal([frozenset({"a"})], COVERED, DEM, rule="banzhaf")
    # Thông điệp phải liệt kê các rule hợp lệ để người gọi tự sửa được ngay.
    for rule in params.CREDIT_RULES:
        assert rule in str(exc.value)
