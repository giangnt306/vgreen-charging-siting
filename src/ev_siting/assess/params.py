"""Tham số ĐÓNG BĂNG của assess() v0 — mirror 1-1 pre-reg (B2).

Nguồn chân lý: ``evcs-dataset/docs/sprint2/prereg-assess-v0.md`` (ký 2026-07-28).
Test ``tests/test_assess_params.py`` đối chiếu từng giá trị với doc; đổi bất kỳ số nào
ở đây mà không có Addendum trong pre-reg = vi phạm kỷ luật 4 cửa.

Các giá trị đánh dấu GIẢ ĐỊNH là số khởi động chưa có xác nhận BO (ask-list) —
in nhãn ra output, không giấu trong config (I-2).
"""

from ev_siting.features.paths import R_BASELINE_KM

# --- danh tính phiên bản (in trên MỌI dòng output — bất biến backlog §4.4) ---
MODEL_VERSION = "assess-v0.1.0"
CALIBRATION_LABEL = "v0 — chưa calibrate"
FREEZE_LABEL = "sprint2-2026-07-28"
SCOPE = "vietnam"
SNAPSHOT_ID = "2026-07-20"
DATA_VERSION = f"{FREEZE_LABEL}/{SCOPE}@{SNAPSHOT_ID}"

# --- hình học / bán kính ---
R_SERVICE_KM = R_BASELINE_KM  # 3,0 km — MỘT nguồn với tầng feature, không khai lại số
COMPETITION_RADIUS_KM = 1.0  # GIẢ ĐỊNH — khớp định nghĩa NEW-HIGH (>1 km = chắc chắn thiếu)
NEAR_EXISTING_M = 200.0  # G2 — GIẢ ĐỊNH, chờ BO trả lời ask #5 (bảo hộ khoảng cách)
BATCH_CONFLICT_M = 200.0  # G3 [mô phỏng] — sổ pipeline thật chưa tồn tại

# --- occupancy F19 (đúng từng ký tự bronze phía evcs-dataset) ---
MAX_HOLD_MS = 30 * 60 * 1000  # cap một gap ở 30' — không cho gap 71h thống trị mean
OCC_COVERAGE_FLOOR = 0.5  # trạm duration_coverage < 0,5 không vào occ_local
OCC_HIGH_BAND = 0.30  # GIẢ ĐỊNH — ngưỡng reason R09 (enrichment, không vào score)

# --- score & tier (p60/p30 khởi động — chưa calibrate) ---
THRESH_ACCEPT = 60.0
THRESH_REJECT = 30.0
TIER_ACCEPT = "Đồng ý"
TIER_REVIEW = "Cần review"
TIER_REJECT = "Từ chối"

# --- chia công kế hoạch nhiều điểm ---
CREDIT_RULES = ("solo", "last_in", "shapley")
DEFAULT_CREDIT_RULE = "shapley"  # Shapley hàm phủ có công thức đóng: ô chia đều cho k điểm phủ

#: Reason codes v0 — mỗi reason khi in PHẢI kèm con số fact (thang phát biểu loại 1).
REASONS = {
    "R01_NEAR_EXISTING": "Cách trạm hiện hữu gần nhất {d_nearest_m:.0f} m (≤ {near_m:.0f} m)",
    "R02_BATCH_CONFLICT_SIM": "[mô phỏng] Trùng lô: điểm khác trong lô cách {d_batch_m:.0f} m",
    "R03_NO_DATA": "Ngoài lưới cầu / toạ độ không hợp lệ — không đủ dữ liệu để chấm",
    "R04_LOW_MARGINAL": "Giá trị biên thấp: {n_redundancy_pct:.0f}% dân trong {r_km:.0f} km đã được phủ",
    "R05_HIGH_MARGINAL": "+{n_marginal_pop:,.0f} dân chưa phủ trong {r_km:.0f} km (top {pctl_inv:.0f}% quỹ đất)",
    "R06_LOW_LOCAL_DEMAND": "Cầu quanh điểm thấp: {v_demand_local:,.0f} dân trong {r_km:.0f} km (dưới p30 quỹ đất)",
    "R07_HIGH_COMPETITION": "{v_competition:.0f} trạm trong {comp_km:.1f} km (≥ p90 quỹ đất)",
    "R08_PRESSURE_HIGH": "Áp lực cầu/cung thuộc top {pctl_inv:.0f}% quỹ đất (percentile, không phải dự báo)",
    "R09_OCC_NEARBY_HIGH": "Trạm quanh đây bận {occ_local_pct:.0f}% thời gian quan sát (duration-weighted)",
    "R10_NO_SUPPLY_1KM": "Không có trạm nào trong {comp_km:.1f} km — vùng trống cung",
    "R11_LAND_SURVEY": "Ô đất mang cờ khảo sát ({flags}) — bắt buộc khảo sát thực địa trước khi chốt",
    # Addendum 28/07 (sau adversarial-verify, trước khi chấm GT): hai reason bổ sung để
    # (a) R04 vẫn nói được fact khi catchment 0 dân (mẫu redundancy không tồn tại) và
    # (b) bất biến "Từ chối luôn kèm ≥1 lý do" không thể vỡ (hợp đồng BO "kèm lý do").
    "R04_LOW_MARGINAL_ALT": "Giá trị biên thấp: +{n_marginal_pop:,.0f} dân chưa phủ trong {r_km:.0f} km (catchment không có dân để tính %)",
    "R12_LOW_TOTAL": "score_total {score_total:.0f} < {thresh:.0f} — dưới ngưỡng p30 của quỹ đất khả thi trên tổng hai trục",
}

# --- T1 retrodiction (chốt ở pre-reg §5) ---
GT_VERDICT = "NEW"
GT_CONFIDENCE = "HIGH"  # 1.271 trạm sau F11 (đính chính: 1.544 là số pre-F11)
SEED_CONTROL_A = 20260728  # control cùng phân tầng decile-pop, n = |GT|
SEED_CONTROL_B = 20260729  # control cầu thấp
N_CONTROL_B = 1000
CONTROL_LOW_POP_Q = 0.30  # "cầu thấp" = 0 < pop ≤ p30 của tập ô pop>0
T1_TARGET_HIT = 0.60  # %GT vào {Đồng ý, Cần review}
T1_MAX_LOW_ACCEPT = 0.10  # %control cầu-thấp được Đồng ý
T1_TARGET_AUC = 0.70  # AUC score_total GT vs control A — báo as-is


def station_id_from_code(code: str) -> str:
    """Mã evcs (`C.AC000067`) -> station_id canonical (`vn-c-ac000067`).

    Cùng quy tắc transform_canonical dùng khi sinh covered0; giữ ở MỘT chỗ để
    exclusion T1 và join occupancy không tự chế biến thể riêng.
    """
    return "vn-" + code.strip().lower().replace(".", "-")
