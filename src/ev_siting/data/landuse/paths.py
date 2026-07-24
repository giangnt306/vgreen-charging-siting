"""Canonical filesystem paths + ngưỡng cho tầng land-use / khả thi xây dựng (P5).

Cùng quy ước với ``ev_siting.data.osm.paths``: mọi thứ neo vào ``PROJECT_ROOT``
suy từ vị trí file này. Tải/phản hồi thô bất biến ở ``data/raw/landuse/``; sản
phẩm dẫn xuất ở ``data/interim/landuse/``.

Chạy tuần tự:
    PYTHONPATH=src python -m ev_siting.data.landuse.worldcover
    PYTHONPATH=src python -m ev_siting.data.landuse.osm_exclusion
    PYTHONPATH=src python -m ev_siting.data.landuse.build_buildable_h3
    PYTHONPATH=src python -m ev_siting.data.landuse.validate
"""
from pathlib import Path

# landuse -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA = PROJECT_ROOT / "data"

# --- raw, bất biến (data/raw/landuse) ---
RAW_DIR = DATA / "raw" / "landuse"
WC_TILE_DIR = RAW_DIR / "worldcover"        # ESA WorldCover 10m, 1 GeoTIFF/ô 3°x3°
OSM_EXCL_DIR = RAW_DIR / "osm_exclusion"    # phản hồi Overpass thô theo AOI

# --- dẫn xuất (data/interim/landuse) ---
INTERIM_DIR = DATA / "interim" / "landuse"
LANDUSE_H3 = INTERIM_DIR / "landuse_h3.parquet"        # tỷ lệ lớp phủ theo ô H3
EXCLUSION_ZONES = INTERIM_DIR / "exclusion_zones.parquet"  # polygon cấm (WKT)
SUBSTATIONS = INTERIM_DIR / "osm_substations.parquet"   # power=substation (điểm)
BUILDABLE_H3 = INTERIM_DIR / "buildable_h3.parquet"     # <- output chính của tầng này
QUALITY_REPORT = INTERIM_DIR / "landuse_quality_report.json"

# --- nguồn ESA WorldCover v200 (2021), 10 m, CC-BY 4.0 ---
WC_YEAR = 2021
WC_VERSION = "v200"
WC_BASE_URL = ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
               f"{WC_VERSION}/{WC_YEAR}/map")
WC_TILE_DEG = 3          # cạnh 1 ô tile (độ)

H3_RES_R8 = 8

#: Mã lớp phủ WorldCover -> nhóm dùng trong bộ lọc khả thi.
#: 10 cây · 20 bụi · 30 cỏ · 40 cây trồng · 50 xây dựng · 60 đất trống
#: 70 băng tuyết · 80 mặt nước · 90 đất ngập nước · 95 rừng ngập mặn · 100 rêu/địa y
WC_CLASS_GROUP = {
    10: "tree", 20: "shrub", 30: "grass", 40: "crop", 50: "built",
    60: "bare", 70: "bare", 80: "water", 90: "wetland", 95: "wetland",
    100: "bare",
}
WC_GROUPS = ("tree", "shrub", "grass", "crop", "built", "bare", "water", "wetland")

# --- ngưỡng bộ lọc khả thi (P5) ---
#: ô phải có >= 5% pixel "built-up" mới coi là xây được (chốt 24/07, cần hiệu chỉnh
#: lại sau lần chạy đầu trên MVP city — xem docs/candidate-sites.md §Ngưỡng).
BUILT_UP_MIN = 0.05
#: >= 50% pixel là mặt nước -> loại hẳn (hồ/sông/biển).
WATER_MAX = 0.50
#: mặt nước + ngập nước >= 70% -> loại hẳn (đầm/bãi triều).
WATER_WETLAND_MAX = 0.70
#: >= 60% pixel cây trồng -> phạt mềm (đất nông nghiệp, pháp lý/chi phí cao hơn).
CROP_DOMINANT = 0.60
#: 5% <= built < 15% -> phạt mềm (hạ tầng mỏng).
LOW_BUILTUP = 0.15

#: Bộ lọc âm từ OSM: tag -> nhãn cờ loại trừ.
OSM_EXCLUSION_TAGS = {
    'way["landuse"="military"]': "MILITARY",
    'relation["landuse"="military"]': "MILITARY",
    'way["boundary"="protected_area"]': "PROTECTED",
    'relation["boundary"="protected_area"]': "PROTECTED",
    'way["leisure"="nature_reserve"]': "PROTECTED",
    'relation["leisure"="nature_reserve"]': "PROTECTED",
    'way["aeroway"="aerodrome"]': "AIRPORT",
    'relation["aeroway"="aerodrome"]': "AIRPORT",
    'way["natural"="water"]': "WATER_OSM",
    'relation["natural"="water"]': "WATER_OSM",
    'way["landuse"="reservoir"]': "WATER_OSM",
}

#: Trạm biến áp (proxy ràng buộc lưới điện — problem-analysis mục 2 Nhóm 2 #3).
OSM_SUBSTATION_TAGS = ('node["power"="substation"]', 'way["power"="substation"]')


def ensure_dirs():
    """Tạo mọi thư mục output (idempotent)."""
    for d in (WC_TILE_DIR, OSM_EXCL_DIR, INTERIM_DIR):
        d.mkdir(parents=True, exist_ok=True)
