"""B2 — đối chiếu params.py với pre-reg đã ký (đổi số mà không có Addendum = vi phạm 4 cửa).

Các assert dưới đây lặp lại NGUYÊN VĂN con số trong
evcs-dataset/docs/sprint2/prereg-assess-v0.md (ký 2026-07-28). Nếu một test ở đây đỏ,
câu hỏi đúng KHÔNG phải "sửa test thế nào" mà là "Addendum pre-reg đã viết chưa".
"""

from ev_siting.assess import params
from ev_siting.features.paths import R_BASELINE_KM


def test_versions_and_labels_match_prereg():
    assert params.MODEL_VERSION == "assess-v0.1.0"
    assert params.DATA_VERSION == "sprint2-2026-07-28/vietnam@2026-07-20"
    assert params.CALIBRATION_LABEL == "v0 — chưa calibrate"


def test_geometry_frozen():
    # R = 3,0 phải là CÙNG một object với tầng feature — không khai lại số (một nguồn)
    assert params.R_SERVICE_KM is R_BASELINE_KM or params.R_SERVICE_KM == R_BASELINE_KM == 3.0
    assert params.COMPETITION_RADIUS_KM == 1.0  # GIẢ ĐỊNH — khớp định nghĩa NEW-HIGH >1km
    assert params.NEAR_EXISTING_M == 200.0  # G2 — chờ BO ask #5
    assert params.BATCH_CONFLICT_M == 200.0  # G3 [mô phỏng]


def test_f19_occupancy_frozen():
    assert params.MAX_HOLD_MS == 30 * 60 * 1000  # cap 30' — đúng bronze evcs-dataset
    assert params.OCC_COVERAGE_FLOOR == 0.5
    assert params.OCC_HIGH_BAND == 0.30


def test_tier_thresholds_frozen():
    assert (params.THRESH_ACCEPT, params.THRESH_REJECT) == (60.0, 30.0)  # p60/p30 khởi động
    assert params.DEFAULT_CREDIT_RULE == "shapley"
    assert set(params.CREDIT_RULES) == {"solo", "last_in", "shapley"}


def test_t1_design_frozen():
    assert (params.GT_VERDICT, params.GT_CONFIDENCE) == ("NEW", "HIGH")
    assert params.SEED_CONTROL_A == 20260728
    assert params.SEED_CONTROL_B == 20260729
    assert params.N_CONTROL_B == 1000
    assert params.CONTROL_LOW_POP_Q == 0.30
    assert (params.T1_TARGET_HIT, params.T1_MAX_LOW_ACCEPT, params.T1_TARGET_AUC) == (0.60, 0.10, 0.70)


def test_reason_codes_cover_prereg_list():
    # R01..R11 theo pre-reg §4; R12 (+ biến thể R04_ALT) thêm bởi Addendum 28/07 —
    # bất biến "Từ chối luôn kèm lý do" + R04 khi catchment 0 dân.
    expected = {f"R{i:02d}" for i in range(1, 13)}
    assert {k[:3] for k in params.REASONS} == expected
    assert "R04_LOW_MARGINAL_ALT" in params.REASONS and "R12_LOW_TOTAL" in params.REASONS


def test_station_id_mapping_examples():
    # Quy tắc MỘT chỗ: lower + '.'->'-' + prefix 'vn-'. Đã validate 3.093/3.093 NEW khớp covered0.
    assert params.station_id_from_code("C.AC000067") == "vn-c-ac000067"
    assert params.station_id_from_code("  C.HNO0317 ") == "vn-c-hno0317"
    # Mã có sẵn gạch ngang (AGI67-04) map một chiều — inverse KHÔNG an toàn, cấm suy ngược
    assert params.station_id_from_code("AGI67-04") == "vn-agi67-04"
