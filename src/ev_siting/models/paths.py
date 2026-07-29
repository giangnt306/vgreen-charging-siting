"""Paths + hằng số hợp đồng cho tầng tối ưu (MCLP + assess).

Cùng quy ước với ``ev_siting.features.paths`` và các ``…data.*.paths``: mọi thứ neo
vào ``PROJECT_ROOT`` suy từ vị trí file này, nên chạy ở thư mục nào cũng đúng.

**Vào — đọc bundle đã đóng băng, không đọc thẳng ``data/processed/*.parquet``.**
``build_candidates`` / ``build_covered0`` ghi vào *cùng một đường dẫn* cho mọi AOI,
nên thư mục phẳng có thể đang lẫn scope (national candidate cạnh city covered0).
``features.freeze_processed`` đã chặn đúng lỗi đó rồi mới đóng băng, vì vậy input
hợp lệ của MCLP là ``data/processed/<label>/<scope>/`` — xem ``frozen_scope_dir``.

**Ra — ``outputs/`` (đã gitignore).** Nghiệm MCLP tái lập được từ (label bundle,
λ, p, ngân sách), nên nó là artefact dẫn xuất chứ không phải dữ liệu nguồn.

Chạy từ repo root::

    PYTHONPATH=src python -m ev_siting.models.mclp --label sprint2-2026-07-28
"""

from pathlib import Path

from ev_siting.features.paths import (
    CANDIDATE_SITES,
    COVERED0_OPERATIONAL_SITES,
    COVERED0_SITES,
    PROCESSED_DIR,
    R_BASELINE_KM,
)

# models -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# --- ra: artefact dẫn xuất, tái lập được (outputs/ đã nằm trong .gitignore) ---
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
MCLP_DIR = OUTPUTS_DIR / "mclp"
SOLUTION_SITES = MCLP_DIR / "mclp_solution.parquet"  # 1 dòng / điểm được chọn
SOLUTION_GEOJSON = MCLP_DIR / "mclp_solution.geojson"
RUN_REPORT = MCLP_DIR / "mclp_run.json"  # tham số + nghiệm + gate
SENSITIVITY_REPORT = MCLP_DIR / "lambda_sensitivity.json"

# --- vào: bundle model-ready đã đóng băng ---
#: Nhãn bundle mặc định (khớp `make freeze-processed LABEL=...`).
DEFAULT_FREEZE_LABEL = "sprint2-2026-07-28"
#: Tên file trong bundle — trùng basename bản phẳng ở `data/processed/`.
#: CHỈ liệt kê thứ `freeze_processed._REQUIRED` thực sự đóng băng. `demand_weight`
#: chưa có mặt (`build_demand_proxy` còn là stub) — thêm vào cả hai nơi cùng lúc.
BUNDLE_FILES = {
    "candidates": CANDIDATE_SITES.name,
    "covered0": COVERED0_SITES.name,
    "covered0_operational": COVERED0_OPERATIONAL_SITES.name,
}


def frozen_scope_dir(scope: str, label: str = DEFAULT_FREEZE_LABEL) -> Path:
    """Thư mục bundle của một scope (``hanoi`` / ``vietnam``) trong một lần freeze."""
    return PROCESSED_DIR / label / scope


# --- hợp đồng tiêu thụ `penalty` (candidate-sites.md §10, chốt 2026-07-28) ---
#: Bán kính phục vụ baseline; giữ MỘT nguồn với tầng feature, không khai lại số.
R_SERVICE_KM = R_BASELINE_KM
#: CapEx_i = base(capex_class_i) × (1 + λ·penalty_i).
LAMBDA_PENALTY = 1.0
#: Sensitivity bắt buộc trước khi công bố số.
LAMBDA_SENSITIVITY = (0.0, 1.0, 3.0)
#: Tập chọn lệch > 20% giữa λ=0 và λ=1 ⇒ penalty chi phối nghiệm hơn demand -> soát lại.
SENSITIVITY_MAX_SHIFT = 0.20
#: T0 = trạm đang vận hành: incumbent bắt buộc mở, KHÔNG áp công thức CapEx trên.
T0_CAPEX = 0.0
# `penalty` chỉ vào hàm chi phí, KHÔNG vào ràng buộc khả thi: hard-filter ở tầng model
# là tái lập đúng lỗi F14 (17 trạm T0 đang chạy thật nằm trong ô gắn ĐỒNG THỜI cả hai cờ
# dưới ⇒ cờ sai ở đó). Đây là quy tắc cho người viết solver, không phải cờ bật/tắt.
#: Điểm được chọn thoả một trong hai điều kiện này phải kèm cảnh báo khảo sát thực địa.
SURVEY_WARNING_TIERS = frozenset({"T4"})
SURVEY_WARNING_FLAGS = frozenset({"NO_ROAD_ACCESS", "NOT_BUILT_UP"})  # cần ĐỒNG THỜI cả hai


def ensure_dirs():
    MCLP_DIR.mkdir(parents=True, exist_ok=True)
