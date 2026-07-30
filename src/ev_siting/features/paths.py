"""Paths + hằng số cho tầng feature (demand proxy + candidate sites).

Model-ready artefacts đi vào ``data/processed/`` (SCHEMA_CONTRACT §5). Đây là các
file **bàn giao trực tiếp cho Kỳ** (MCLP), cùng chuẩn parquet + GeoJSON.
"""

from pathlib import Path

# features -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA / "processed"

# --- candidate sites (P5, điểm chạm Giang -> Kỳ) ---
CANDIDATE_SITES = PROCESSED_DIR / "candidate_sites.parquet"
CANDIDATE_GEOJSON = PROCESSED_DIR / "candidate_sites.geojson"

# --- covered0: baseline coverage từ trạm hiện có (active + public) ---
COVERED0_SITES = PROCESSED_DIR / "covered0.parquet"
COVERED0_GEOJSON = PROCESSED_DIR / "covered0.geojson"
COVERED0_OPERATIONAL_SITES = PROCESSED_DIR / "covered0_operational.parquet"
COVERED0_OPERATIONAL_GEOJSON = PROCESSED_DIR / "covered0_operational.geojson"

# --- demand proxy (Sprint 2) ---
DEMAND_WEIGHT = PROCESSED_DIR / "demand_weight.parquet"

# --- tham số chốt (đồng bộ SCHEMA_CONTRACT / known-issues P4) ---
R_BASELINE_KM = 3.0  # bán kính phục vụ MCLP baseline (R/d = 3,07 > 1)

# --- ngưỡng QA gate candidate (P5) ---
COVERAGE_MIN = 0.90  # gate 1: union coverage >= 90% demand lõi AOI
CAND_MIN_MULT = 5  # gate 2: |candidates| >= 5×p
CAND_MAX = 3000  # gate 3: trần kích thước cho MVP city
DEGEN_MIN = 0.90  # gate 4: unique(coverage_set)/|candidates| >= 0,9

# --- gap-fill T4 ---
GAPFILL_TOP_Q = 0.90  # chỉ gap-fill ô demand trong top-decile

# --- cờ toạ độ bẩn (F4) ---
# Loại khỏi baseline covered0 (toạ độ giả -> coverage ảo; COORD_PLACEHOLDER còn mang
# h3_r8 null -> grid_disk crash). Anchor T0 lọc theo `coord_resolved` của E-DQ1, không
# qua tập này. Tập này phải khớp TỪ VỰNG CỜ THẬT mà producer sinh ra (build_master_evcs
# / transform_canonical / dedup_crosssource) — xem known-issues F4; 2 cờ cũ DUP_COORD /
# COORD_ADDR_MISMATCH(pre-E-DQ1) từng là cờ ma khiến bộ lọc chết im lặng.
DIRTY_COORD_FLAGS = frozenset({"COORD_INVALID", "COORD_PLACEHOLDER", "DUP_COORD_SUSPECT"})


def has_dirty_coord(flags):
    """True nếu list `quality_flags` của 1 dòng chứa cờ toạ độ bẩn (None-safe)."""
    if flags is None or (isinstance(flags, float) and flags != flags):
        return False
    return bool(DIRTY_COORD_FLAGS & set(flags))


def ensure_dirs():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
