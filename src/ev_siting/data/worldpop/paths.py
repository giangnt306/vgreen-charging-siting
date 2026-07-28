"""Canonical filesystem paths for the WorldPop population pipeline.

Mirrors ``ev_siting.data.osm.paths`` / ``…evcs.paths``: anchored on PROJECT_ROOT,
immutable download under ``data/raw/worldpop/``, derived artefacts under
``data/interim/worldpop/``.

Run from the repo root::

    PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop
    PYTHONPATH=src python -m ev_siting.data.worldpop.build_demand_h3
"""
from pathlib import Path

# worldpop -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA = PROJECT_ROOT / "data"

# --- raw, immutable download (data/raw/worldpop) ---
RAW_DIR = DATA / "raw" / "worldpop"
POP_TIF = RAW_DIR / "vnm_ppp_2020_constrained.tif"

# --- derived (data/interim/worldpop) ---
INTERIM_DIR = DATA / "interim" / "worldpop"
POP_H3 = INTERIM_DIR / "worldpop_pop_h3.parquet"        # h3_r8 -> pop

# demand_h3 đầy đủ (pop + thành phần OSM) — đầu ra tích hợp
DEMAND_DIR = DATA / "interim" / "demand"
DEMAND_H3 = DEMAND_DIR / "demand_h3.parquet"
# E-DQ7a: ô nằm ngoài lãnh thổ VN — tách ra (không xoá) để đối soát
# `input = output + clipped`, nhất quán nguyên tắc "flag dòng, không xoá".
DEMAND_H3_CLIPPED = DEMAND_DIR / "demand_h3_clipped_out.parquet"
DEMAND_REPORT = DEMAND_DIR / "demand_h3_report.json"

H3_RES_R8 = 8

# WorldPop Vietnam 2020, constrained (~100m, built-settlement aware), UN-unadjusted.
# CC-BY 4.0. Xem https://www.worldpop.org/
WORLDPOP_URL = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/"
    "2020/BSGM/VNM/vnm_ppp_2020_constrained.tif"
)


def ensure_dirs():
    for d in (RAW_DIR, INTERIM_DIR, DEMAND_DIR):
        d.mkdir(parents=True, exist_ok=True)
