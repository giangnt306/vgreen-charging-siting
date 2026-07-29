"""Paths cho máy thẩm định assess() — cùng quy ước neo PROJECT_ROOT các package khác.

Vào: bundle frozen (qua ``features.read_frozen``) + ``demand_h3`` + telemetry frozen
``data/raw/evcs/load_ts.csv``. Cache dẫn xuất (rebuild được, có build-meta ghi sha256
nguồn) ở ``data/interim/assess/``; kết quả chấm + log ở ``outputs/assess/`` (gitignored).
"""

from pathlib import Path

# assess -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA = PROJECT_ROOT / "data"

# --- input ngoài bundle (pin sha256 vào build-meta / report khi dùng) ---
DEMAND_H3 = DATA / "interim" / "demand" / "demand_h3.parquet"
LOAD_TS = DATA / "raw" / "evcs" / "load_ts.csv"  # frozen E-DQ10 (trong MANIFEST)

#: Ground truth T1 — gold new_supply phía evcs-dataset (vault-ToS, chỉ nội bộ).
#: Đường dẫn sibling-repo là default của môi trường dev; override bằng --ground-truth.
GROUND_TRUTH_NEW_SUPPLY = (
    PROJECT_ROOT.parent
    / "evcs-dataset"
    / "data"
    / "30_gold"
    / "evcs_new_supply"
    / "country=VN"
    / "snapshot_date=2026-07-20"
    / "part.parquet"
)

# --- cache dẫn xuất (data/interim/assess) ---
CACHE_DIR = DATA / "interim" / "assess"
OCC_CACHE = CACHE_DIR / "occupancy_f19.parquet"  # per-station duration-weighted (F19)
OCC_META = CACHE_DIR / "occupancy_f19.meta.json"  # sha256 nguồn + số dòng + thời điểm build
REF_DIR = CACHE_DIR / "reference"  # phân bố lớp tham chiếu theo context

# --- output chấm điểm (outputs/ gitignored — artefact tái lập được) ---
OUT_DIR = PROJECT_ROOT / "outputs" / "assess"
LOG_PATH = OUT_DIR / "assess_log.jsonl"  # log MỌI lần chấm (bất biến §4.5)
T1_DIR = OUT_DIR / "t1"  # kết quả retrodiction


def ensure_dirs():
    for d in (CACHE_DIR, REF_DIR, OUT_DIR, T1_DIR):
        d.mkdir(parents=True, exist_ok=True)
