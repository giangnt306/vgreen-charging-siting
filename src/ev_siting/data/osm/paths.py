"""Canonical filesystem paths for the OSM POI + road-network pipeline.

Mirrors the convention in ``ev_siting.data.evcs.paths``: everything anchors on
``PROJECT_ROOT`` derived from this file's location, so the pipeline runs the same
regardless of the working directory. Immutable downloads/responses live under
``data/raw/osm/``; cleaned/derived artefacts under ``data/interim/osm/``.

Run each step as a module from the repo root, e.g.::

    PYTHONPATH=src python -m ev_siting.data.osm.overpass_poi
    PYTHONPATH=src python -m ev_siting.data.osm.roads_pbf
    PYTHONPATH=src python -m ev_siting.data.osm.build_osm_h3
"""
from pathlib import Path

# osm -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA = PROJECT_ROOT / "data"

# --- raw, immutable downloads / API responses (data/raw/osm) ---
RAW_DIR = DATA / "raw" / "osm"
POI_RAW_DIR = RAW_DIR / "poi"                       # 1 GeoJSON/category (phản hồi Overpass thô)
PBF_PATH = RAW_DIR / "vietnam-latest.osm.pbf"       # Geofabrik dump (nguồn road network)

# --- cleaned / derived (data/interim/osm) ---
INTERIM_DIR = DATA / "interim" / "osm"
POI_POINTS = INTERIM_DIR / "osm_poi_points.parquet"     # 1 dòng/POI TRONG VN (đã gán h3)
POI_OUTSIDE_VN = INTERIM_DIR / "osm_poi_outside_vn.parquet"  # POI bbox-spill bị cắt (E-DQ11, để audit)
ROADS_H3 = INTERIM_DIR / "osm_roads_h3.parquet"         # road_len theo ô H3
DEMAND_COMPONENTS = INTERIM_DIR / "osm_demand_components_h3.parquet"  # gộp POI+road theo H3
QUALITY_REPORT = INTERIM_DIR / "osm_quality_report.json"

# --- vùng phủ & lưới ---
# Bounding box Việt Nam (bao gồm cả quần đảo xa bờ): (min_lat, min_lon, max_lat, max_lon)
# CHỈ dùng để CHIA Ô TRUY VẤN Overpass — KHÔNG phải bộ lọc lãnh thổ. Hình chữ nhật này trùm
# Đông Bắc Thái Lan, Nam Lào, phần lớn Campuchia và Quảng Tây/Vân Nam; lọc bằng nó cho lọt
# 54,2% POI ngoại biên (E-DQ11). Cắt lãnh thổ PHẢI dùng `ev_siting.vn_boundary`.
VN_BBOX = (8.0, 102.0, 23.7, 110.0)
H3_RES_R8 = 8
H3_RES_R9 = 9

# Geofabrik luôn 302 sang bản có ngày; theo redirect để lấy dump mới nhất.
GEOFABRIK_URL = "https://download.geofabrik.de/asia/vietnam-latest.osm.pbf"


def ensure_dirs():
    """Tạo mọi thư mục output (idempotent)."""
    for d in (POI_RAW_DIR, INTERIM_DIR):
        d.mkdir(parents=True, exist_ok=True)
