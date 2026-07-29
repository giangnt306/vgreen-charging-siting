"""paths.py — ranh giới + dân số cấp xã VNSDI (Bản đồ nền tỷ lệ nhỏ, MAE).

Layout theo quy ước repo (như ``vinfast_official``/``worldpop``): crawl thô, bất biến
-> ``data/raw/vnsdi/``; chuẩn hoá (reproject + WKB) -> ``data/interim/vnsdi/``.

NGUỒN. ArcGIS Server 11.4 công khai của VNSDI, service ``34DVHC`` (Đơn vị hành chính
34 tỉnh/thành sau sáp nhập 2025), **layer 2 = "Địa phận cấp xã 1000N"** — polygon cấp xã
kèm ``DANSO`` (dân số) và ``DIENTICH`` (diện tích km²). Service yêu cầu **token** +
**Referer** (token nằm trong ``config.aspx`` mà app web nạp lúc chạy, referer-bound và
xoay vòng) → crawler lấy token TƯƠI mỗi lần chạy, KHÔNG hardcode.

⚠️ NIÊN ĐẠI. ``NGAYHIEULUC = 16/6/2025``, ``NGAYXUATBAN = 13/7/2025`` → ``DANSO`` là số
liệu **2025**, mới hơn WorldPop 2020 ~5 năm. Dùng làm KIỂM CHỨNG phân bổ (E-DQ7f), KHÔNG
dùng làm control-total tái phân bổ: neo khối lượng vẫn là tổng WorldPop (giữ cổng
``pop_total_matches_unadj`` của E-DQ7e). Chênh niên đại là hiệu chỉnh mức (P10), không
phải hiệu chuẩn phân bổ.
"""
from pathlib import Path

# vnsdi -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA = PROJECT_ROOT / "data"

# --- endpoint (base url + service; token lấy tươi lúc crawl, không lưu) ---
CONFIG_URL = "https://vnsdi.mae.gov.vn/bandonen/config.aspx"
REFERER = "https://vnsdi.mae.gov.vn/bandonen/"
SERVICE_PATH = "34DVHC/MapServer/2"          # layer 2 = Địa phận cấp xã
OUT_SR = 4326                                # reproject server-side -> WGS84 (khớp WorldPop/H3)
FIELDS = ["MATINH", "MAXA", "TENXA", "TENTINH", "DIENTICH", "DANSO",
          "NGAYHIEULUC", "NGAYXUATBAN"]
#: Số xã kỳ vọng — neo cổng QA (đo returnCountOnly lúc crawl, chốt 2026-07-29).
EXPECTED_COMMUNES = 3321
EXPECTED_PROVINCES = 34

# --- raw, immutable (data/raw/vnsdi) ---
RAW_DIR = DATA / "raw" / "vnsdi"
PAGES_DIR = RAW_DIR / "pages"                 # 1 file/tỉnh: <MATINH>.geojson (as-delivered, SR 4326)
ENDPOINT_JSON = RAW_DIR / "endpoint.json"     # base url + service + field list + count/tỉnh (KHÔNG token)

# --- interim, normalized (data/interim/vnsdi) ---
INTERIM_DIR = DATA / "interim" / "vnsdi"
COMMUNES_PARQUET = INTERIM_DIR / "communes.parquet"      # maxa,...,danso,dientich_km2,geom_wkb
COMMUNES_GEOJSON = INTERIM_DIR / "communes_centroids.geojson"  # tâm xã (QA nhẹ trên map)
COMMUNES_REPORT = INTERIM_DIR / "communes_report.json"  # cổng QA + thống kê


def ensure_dirs():
    for d in (RAW_DIR, PAGES_DIR, INTERIM_DIR):
        d.mkdir(parents=True, exist_ok=True)
