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


# --- pull registry MOI HON ban da dong bang ---
# Registry la nguon SONG: `generation` tang moi lan VinFast cap nhat. De khong de len ban
# da freeze (gen 16, snapshot 2026-07-20), moi pull moi ghi vao `snapshot=<ngay>/`. Dot
# 29/07 dung gen 179 lam seed cho `evcs_enumerate --seed-from-official`, nhung ban gen 179
# do lai KHONG nam trong MANIFEST -> dau vao cua 298 tram moi khong dong bang duoc (L10).
SNAPSHOT_GLOB = "snapshot=*"


def registry_versions():
    """-> [(generation, raw_dir, stations_parquet)] tang dan theo `generation`.

    Gom ban goc (RAW_DIR/INTERIM_DIR) va moi `snapshot=<ngay>/`. Ban thieu meta hoac
    thieu parquet bi bo qua — chi tra ve version dung duoc.
    """
    import json

    out = []
    pairs = [(RAW_DIR, STATIONS_PARQUET)]
    pairs += [(d, INTERIM_DIR / d.name / "official_stations.parquet")
              for d in sorted(RAW_DIR.glob(SNAPSHOT_GLOB)) if d.is_dir()]
    for raw_dir, parquet in pairs:
        meta = raw_dir / "locators_meta.json"
        if not (meta.exists() and parquet.exists()):
            continue
        try:
            gen = int(json.loads(meta.read_text(encoding="utf-8")).get("generation"))
        except (OSError, ValueError, TypeError):
            continue
        out.append((gen, raw_dir, parquet))
    out.sort(key=lambda t: t[0])
    return out


def latest_registry():
    """-> (generation, raw_dir, stations_parquet) ban registry MOI NHAT co du file."""
    vs = registry_versions()
    if not vs:
        raise SystemExit(
            f"khong tim thay registry official nao. Chay `make official` roi "
            f"`python -m ev_siting.data.vinfast_official.fetch_locators parse` (thu: {RAW_DIR})"
        )
    return vs[-1]


def ensure_dirs():
    for d in (RAW_DIR, DETAIL_DIR, INTERIM_DIR):
        d.mkdir(parents=True, exist_ok=True)
