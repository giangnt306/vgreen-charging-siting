"""paths.py — E-DQ3: đường dẫn + hằng số của tầng hành chính.

NGUỒN CHÂN LÝ = **VNSDI cấp xã** (`data/interim/vnsdi/communes.parquet`, `make vnsdi`),
KHÔNG phải 40 polygon `admin_level=4` của OSM. Lý do đã đo, không phải sở thích:

  | | VNSDI 34DVHC layer 2        | OSM adm4 (`vn_boundary`)              |
  |-|-----------------------------|---------------------------------------|
  | | 3.321 xã / 34 tỉnh          | 40 polygon tỉnh                       |
  | | MỘT niên đại (16/6/2025)    | **TRỘN** hai niên đại: `Tỉnh Lào Cai` |
  | |                             | **và** `Tỉnh Lào Cai cũ` (tương tự    |
  | |                             | Quảng Trị / An Giang)                 |
  | | `MAXA` unique (0 trùng)     | không có khoá                         |
  | | kèm `DANSO`/`DIENTICH`      | —                                     |

Dùng OSM adm4 = gán nhãn bằng một bảng ranh giới **chồng lấn** — đúng cái mà E-DQ7a đã
cảnh báo khi bàn giao artefact (xem `osm/vn_boundary.py`, mục Limitation). Tỉnh ở đây là
**dissolve các xã theo `MATINH`** ⇒ một lớp, một niên đại, nhất quán theo xây dựng, và
mở khoá luôn phần hiệu chuẩn cấp tỉnh mà E-DQ7e phải hoãn.

⚠️ VNSDI chỉ cấp **ranh giới + nhãn**. `DANSO` (113,6 M, đăng ký 2025) lệch **+16,5%** so
với WorldPop UNadj (97,57 M, 2020); lấy nó làm dân số là âm thầm neo lại toàn bộ hàm mục
tiêu qua khe niên đại P9/P10. Hai thứ giữ tách bạch — xem `vnsdi/paths.py`.
"""
from pathlib import Path

# admin -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA = PROJECT_ROOT / "data"

INTERIM_DIR = DATA / "interim" / "admin"

#: Bảng phân bổ ô -> xã (long, có trọng số diện tích) — cơ sở của mọi rollup hành chính.
CELL_COMMUNE = INTERIM_DIR / "cell_commune.parquet"
#: Rollup cấp xã của `demand_h3` (đúng thứ overview.md §"demand_commune" chờ).
DEMAND_COMMUNE = INTERIM_DIR / "demand_commune.parquet"
#: Bảng quy đổi `province_code` (hệ 63 tỉnh cũ, prefix mã evcs) -> `admin_l1_code` (34).
PROVINCE_CROSSWALK = INTERIM_DIR / "province_crosswalk.csv"

STATION_ADMIN_REPORT = INTERIM_DIR / "station_admin_report.json"
STATION_ADMIN_FLAGGED = INTERIM_DIR / "station_admin_flagged.csv"
GRID_ADMIN_REPORT = INTERIM_DIR / "grid_admin_report.json"

# --- niên đại (phải ghi vào MỌI report — bài học "ghi rõ neo vào đâu" của E-DQ7e) ---
#: `NGAYHIEULUC` của lớp VNSDI 34DVHC. Nhãn hành chính KHÔNG có nghĩa nếu thiếu mốc này:
#: cùng một toạ độ trả `Tỉnh Bắc Ninh` (sau 1/7/2025) hay `Tỉnh Bắc Giang` (trước) đều
#: "đúng" — khác niên đại thôi.
ADMIN_VINTAGE = "2025-06-16"
ADMIN_SOURCE = "VNSDI 34DVHC layer 2 (Địa phận cấp xã 1000N)"
EXPECTED_PROVINCES = 34

# --- tham số (mọi ngưỡng đều neo vào một phép đo, ghi ở chỗ dùng) ---
#: Bán kính snap về xã gần nhất khi điểm rơi NGOÀI mọi polygon. Lớp VNSDI là bản đồ nền
#: **tỷ lệ nhỏ (1:1.000.000)** nên đường bờ biển/bờ sông bị tổng quát hoá — trạm ven biển
#: thật vẫn rơi ra ngoài vài chục mét. Đo trên 27 trạm không khớp (2026-07-30): 11 trạm
#: nằm trong **0,374 km** và xã gần nhất KHỚP địa chỉ (Lào Cai→Lào Cai, Cần Giờ→Cần Giờ,
#: Kỳ Xuân→Kỳ Xuân, Rạch Giá→Rạch Giá, Mũi Né→Mũi Né, Vũng Tàu→Vũng Tàu); trạm kế tiếp
#: cách **2,100 km** và địa chỉ ghi Hưng Yên trong khi xã gần nhất ở Quảng Ninh. Ngưỡng
#: 500 m nằm giữa một dải RỖNG rộng 5,6 lần — không phải số chọn tay.
ADMIN_SNAP_TOL_M = 500.0

#: Crosswalk `province_code` -> `admin_l1_code` suy từ dữ liệu (KHÔNG hardcode bảng sáp
#: nhập 63->34: bảng chép tay không kiểm chứng được và sai một dòng thì im lặng). Chỉ tin
#: khi đủ cỡ mẫu VÀ đủ thuần. Đo được: 63/65 mã có độ thuần >= 0,9379; hai mã trượt là
#: `NA` (0,26 — province_code rỗng) và `AC` (0,32 — họ mã `C.AC…`, không phải tỉnh) ⇒
#: ngưỡng 0,90 tách đúng "mã tỉnh thật" khỏi "mã không phải tỉnh".
CROSSWALK_MIN_N = 20
CROSSWALK_MIN_PURITY = 0.90


def ensure_dirs():
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
