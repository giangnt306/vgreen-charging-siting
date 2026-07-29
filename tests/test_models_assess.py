"""Test 3 nghĩa vụ báo cáo của nghiệm MCLP (candidate-sites.md §10).

Dữ liệu synthetic nhỏ dựng tay — đây là hàm thuần trên DataFrame nghiệm, không
đụng bundle frozen. Điều đáng test là CHỮ của hợp đồng: một cờ đơn lẻ không kích
hoạt cảnh báo, is_existing không được tự miễn trừ, và gate λ dùng đúng công thức
shift = 1 − |A∩B| / max(|A|,|B|).
"""

import pandas as pd
import pytest

from ev_siting.models.assess import lambda_sensitivity, penalty_breakdown, survey_warnings
from ev_siting.models.paths import LAMBDA_SENSITIVITY, SENSITIVITY_MAX_SHIFT

_COLS = ["candidate_id", "tier", "penalty_flags", "capex_class", "is_existing"]


def _sol(rows):
    """Dựng DataFrame nghiệm tối thiểu; rows = list các tuple theo _COLS."""
    return pd.DataFrame(rows, columns=_COLS)


# --- survey_warnings (§10-1) -------------------------------------------------


def test_survey_warnings_bat_tier_t4():
    sol = _sol(
        [
            ("c1", "T4", None, "low", False),
            ("c2", "T1", None, "low", False),
        ]
    )
    out = survey_warnings(sol)
    assert list(out["candidate_id"]) == ["c1"]
    assert list(out["survey_reason"]) == ["tier=T4"]


def test_survey_warnings_bat_cap_co_dong_thoi_khong_phu_thuoc_thu_tu():
    # Thứ tự cờ trong list không được ảnh hưởng — cùng một tổ hợp đất.
    sol = _sol(
        [
            ("c1", "T1", ["NOT_BUILT_UP", "NO_ROAD_ACCESS"], "mid", False),
            ("c2", "T1", ["NO_ROAD_ACCESS", "NOT_BUILT_UP", "CROP"], "mid", False),
        ]
    )
    out = survey_warnings(sol)
    assert list(out["candidate_id"]) == ["c1", "c2"]
    # Nhãn in đúng câu chữ hợp đồng, kể cả khi input có thêm cờ khác (superset).
    assert set(out["survey_reason"]) == {"flags=NO_ROAD_ACCESS+NOT_BUILT_UP"}


def test_survey_warnings_khong_bat_co_don_le():
    # Từng cờ riêng chỉ là phạt mềm (F14) — không đủ để bắt khảo sát thực địa.
    sol = _sol(
        [
            ("c1", "T1", ["NO_ROAD_ACCESS"], "low", False),
            ("c2", "T1", ["NOT_BUILT_UP"], "low", False),
            ("c3", "T2", ["CROP", "LOW_BUILTUP"], "low", False),
        ]
    )
    assert survey_warnings(sol).empty


def test_survey_warnings_is_existing_van_vao_danh_sach():
    # Hợp đồng viết "mọi điểm được chọn" — T0 thoả điều kiện không được tự miễn trừ,
    # cột is_existing giữ nguyên để report tự diễn giải.
    sol = _sol([("t0", "T4", ["NO_ROAD_ACCESS", "NOT_BUILT_UP"], "low", True)])
    out = survey_warnings(sol)
    assert len(out) == 1
    assert bool(out["is_existing"].iloc[0]) is True
    # Cả hai điều kiện cùng nổ -> ghép bằng "; ", tier đứng trước.
    assert out["survey_reason"].iloc[0] == "tier=T4; flags=NO_ROAD_ACCESS+NOT_BUILT_UP"


def test_survey_warnings_giu_nguyen_cot_goc():
    sol = _sol([("c1", "T4", None, "high", False)])
    out = survey_warnings(sol)
    assert list(out.columns) == _COLS + ["survey_reason"]


# --- penalty_breakdown (§10-2) -----------------------------------------------


def test_penalty_breakdown_share_cong_bang_1_va_flags_lan_lon():
    # None và [] là cùng nhóm "(none)"; list lệch thứ tự là cùng nhóm tuple đã sort.
    sol = _sol(
        [
            ("c1", "T0", None, "low", True),
            ("c2", "T1", [], "low", False),
            ("c3", "T1", ["NO_ROAD_ACCESS"], "low", False),
            ("c4", "T4", ["NOT_BUILT_UP", "NO_ROAD_ACCESS"], "mid", False),
            ("c5", "T4", ["NO_ROAD_ACCESS", "NOT_BUILT_UP"], "mid", False),
        ]
    )
    out = penalty_breakdown(sol)
    assert list(out.columns) == ["capex_class", "penalty_flags", "n", "share"]
    assert out["share"].sum() == pytest.approx(1.0)
    assert list(out["n"]) == sorted(out["n"], reverse=True)  # sort n giảm dần
    assert list(out.index) == list(range(len(out)))  # đã reset_index

    by_key = {(r.capex_class, r.penalty_flags): r.n for r in out.itertuples()}
    pair = tuple(sorted(["NO_ROAD_ACCESS", "NOT_BUILT_UP"]))
    assert by_key == {
        ("low", "(none)"): 2,
        ("mid", pair): 2,
        ("low", ("NO_ROAD_ACCESS",)): 1,
    }


def test_penalty_breakdown_rong_khong_chia_cho_0():
    out = penalty_breakdown(_sol([]))
    assert out.empty
    assert list(out.columns) == ["capex_class", "penalty_flags", "n", "share"]


# --- lambda_sensitivity (§10-3) ----------------------------------------------

_A10 = [f"c{i:02d}" for i in range(10)]


def test_lambda_sensitivity_thieu_lambda_1_la_valueerror():
    # Thiếu λ=1 thì gate 0-vs-1 không tồn tại — không được im lặng trả "OK".
    with pytest.raises(ValueError, match=r"1\.0"):
        lambda_sensitivity({0.0: _A10, 3.0: _A10})


def test_lambda_sensitivity_giao_7_tren_10_la_stop():
    # Case tay: |A|=|B|=10, giao 7 -> shift = 1 − 7/10 = 0.3 > 0.20 -> STOP.
    b = _A10[:7] + ["x1", "x2", "x3"]
    res = lambda_sensitivity({0.0: _A10, 1.0: b})
    assert res["shift"]["0-1"] == pytest.approx(0.3)
    assert res["verdict"] == "STOP"
    # Message phải nói rõ: DỪNG và báo lại, penalty chi phối hơn demand, soát §4.
    assert "DỪNG" in res["message"]
    assert "penalty" in res["message"] and "demand" in res["message"]
    assert "§4" in res["message"]


def test_lambda_sensitivity_giao_9_tren_10_la_ok_va_missing_3():
    b = _A10[:9] + ["x1"]
    res = lambda_sensitivity({0.0: _A10, 1.0: b})
    assert res["shift"]["0-1"] == pytest.approx(0.1)
    assert res["verdict"] == "OK"
    # 3.0 nằm trong bộ bắt buộc nhưng không được cung cấp -> liệt kê, không nổ lỗi.
    assert res["missing_lambdas"] == [3.0]
    assert res["sizes"] == {0.0: 10, 1.0: 10}


def test_lambda_sensitivity_kich_thuoc_lech_dung_max():
    # A ⊂ B (4 trong 10): min cho 0 (che mất lệch), max cho 1 − 4/10 = 0.6 -> STOP.
    res = lambda_sensitivity({0.0: _A10[:4], 1.0: _A10})
    assert res["shift"]["0-1"] == pytest.approx(0.6)
    assert res["verdict"] == "STOP"


def test_lambda_sensitivity_ca_hai_rong_shift_0():
    res = lambda_sensitivity({0.0: [], 1.0: []})
    assert res["shift"]["0-1"] == 0.0
    assert res["verdict"] == "OK"


def test_lambda_sensitivity_du_bo_ba_lambda_co_cap_ke_nhau():
    b = _A10[:9] + ["x1"]
    c = _A10[:8] + ["y1", "y2"]
    res = lambda_sensitivity({0: _A10, 1: b, 3: c})  # key int vẫn phải hiểu là λ float
    assert set(res["shift"]) == {"0-1", "1-3"}
    assert res["shift"]["1-3"] == pytest.approx(1 - len(set(b) & set(c)) / 10)
    assert res["missing_lambdas"] == []
    assert res["sizes"] == {0.0: 10, 1.0: 10, 3.0: 10}


def test_hang_so_gate_khop_hop_dong():
    # Neo test vào hợp đồng: đổi hằng số mà không sửa doc §10 thì phải thấy đỏ ở đây.
    assert LAMBDA_SENSITIVITY == (0.0, 1.0, 3.0)
    assert SENSITIVITY_MAX_SHIFT == 0.20
