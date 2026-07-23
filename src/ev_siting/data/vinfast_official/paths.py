"""Canonical paths cho nguon chinh thuc vinfastauto.com (store locator).

Layout theo quy uoc repo: crawl tho -> data/raw/, chuan hoa -> data/interim/.
"""
from pathlib import Path

# vinfast_official -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA = PROJECT_ROOT / "data"

# --- raw, immutable ---
RAW_DIR = DATA / "raw" / "vinfast_official"
META_JSON = RAW_DIR / "locators_meta.json"        # {generation,count,full,sc}
BULK_JSON = RAW_DIR / "locators_full.json"         # toan bo locators (moi category)
DETAIL_DIR = RAW_DIR / "details"                   # 1 file/<store_id>.json (per-station)

# --- interim, normalized ---
INTERIM_DIR = DATA / "interim" / "vinfast_official"
STATIONS_PARQUET = INTERIM_DIR / "official_stations.parquet"     # registry tram sac oto
CONNECTORS_PARQUET = INTERIM_DIR / "official_connectors.parquet"  # tu detail (evses/connectors)
ADMIN_PARQUET = INTERIM_DIR / "official_admin.parquet"           # province/district/commune per store_id

# --- cross-reference: doi chieu evcs.vn <-> nguon chinh thuc (matcher output) ---
XREF_PARQUET = INTERIM_DIR / "official_xref.parquet"             # 1 dong/station_code evcs
XREF_REPORT = INTERIM_DIR / "official_xref_report.json"         # thong ke match

# --- master evcs (input doi chieu) ---
MASTER_CSV = DATA / "interim" / "stations_master_evcs.csv"


def ensure_dirs():
    for d in (RAW_DIR, DETAIL_DIR, INTERIM_DIR):
        d.mkdir(parents=True, exist_ok=True)
