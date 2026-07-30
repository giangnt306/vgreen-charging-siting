"""Canonical filesystem paths for the WorldPop population pipeline.

Mirrors ``ev_siting.data.osm.paths`` / ``…evcs.paths``: anchored on PROJECT_ROOT,
immutable download under ``data/raw/worldpop/``, derived artefacts under
``data/interim/worldpop/``.

Run from the repo root::

    PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop
    PYTHONPATH=src python -m ev_siting.data.worldpop.build_demand_h3
"""
import os
from pathlib import Path

# worldpop -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA = PROJECT_ROOT / "data"

# --- raw, immutable download (data/raw/worldpop) ---
RAW_DIR = DATA / "raw" / "worldpop"
POP_TIF = RAW_DIR / "vnm_ppp_2020_constrained.tif"
# R2024B 2025 (constrained, mặt nạ công trình mới). Repo Kỳ đã tải sẵn -> nhận fallback
# sang repo anh em để không tải lại 74 MB; ghi đè bằng EVCS_WORLDPOP_2025_TIF.
POP_TIF_2025 = RAW_DIR / "vnm_pop_2025_CN_100m_R2024B_v1.tif"

# --- derived (data/interim/worldpop) ---
INTERIM_DIR = DATA / "interim" / "worldpop"
POP_H3 = INTERIM_DIR / "worldpop_pop_h3.parquet"             # h3_r8 -> pop (2020)
POP_H3_2025 = INTERIM_DIR / "worldpop_pop_2025_h3.parquet"   # h3_r8 -> pop (2025)

# demand_h3 đầy đủ (pop + thành phần OSM) — đầu ra tích hợp
DEMAND_DIR = DATA / "interim" / "demand"
DEMAND_H3 = DEMAND_DIR / "demand_h3.parquet"

H3_RES_R8 = 8

# WorldPop Vietnam 2020, constrained (~100m, built-settlement aware), UN-unadjusted.
# CC-BY 4.0. Xem https://www.worldpop.org/
WORLDPOP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/"
    "2020/BSGM/VNM/vnm_ppp_2020_constrained.tif"
)

# WorldPop R2024B 2025, constrained. CC-BY 4.0.
WORLDPOP_2025_URL = (
    "https://data.worldpop.org/GIS/Population/Individual_countries/VNM/"
    "vnm_pop_2025_CN_100m_R2024B_v1.tif"
)

# vintage -> (đường raster, output H3, URL tải)
POP_SOURCES = {
    "2020": (POP_TIF, POP_H3, WORLDPOP_URL),
    "2025": (POP_TIF_2025, POP_H3_2025, WORLDPOP_2025_URL),
}


def resolve_tif(vintage: str):
    """Đường raster cho `vintage`, ưu tiên env rồi repo này rồi repo anh em `evcs-dataset`."""
    tif = POP_SOURCES[vintage][0]
    if vintage == "2025":
        env = os.environ.get("EVCS_WORLDPOP_2025_TIF")
        if env:
            return Path(env)
        if not tif.exists():
            sib = PROJECT_ROOT.parent / "evcs-dataset" / "data" / "00_raw" / "worldpop" / tif.name
            if sib.exists():
                return sib
    return tif


def ensure_dirs():
    for d in (RAW_DIR, INTERIM_DIR, DEMAND_DIR):
        d.mkdir(parents=True, exist_ok=True)
