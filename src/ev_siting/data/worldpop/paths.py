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
# E-DQ7e: nguồn chính thức là bản **UN-adjusted**. Bản unadjusted GIỮ LẠI trên đĩa (đã
# checksum trong MANIFEST) vì nó là chứng cứ tái lập được của cổng
# `pop_scale_ratio_is_constant` — không có nó thì khẳng định "UNadj là hằng số quốc gia,
# thứ hạng ô bất biến" trở lại thành lời hứa.
POP_TIF = RAW_DIR / "vnm_ppp_2020_UNadj_constrained.tif"
POP_TIF_UNADJUSTED = RAW_DIR / "vnm_ppp_2020_constrained.tif"

# --- derived (data/interim/worldpop) ---
INTERIM_DIR = DATA / "interim" / "worldpop"
POP_H3 = INTERIM_DIR / "worldpop_pop_h3.parquet"        # h3_r8 -> pop
POP_REPORT = INTERIM_DIR / "worldpop_pop_report.json"   # cổng QA hiệu chuẩn (E-DQ7e)

# demand_h3 đầy đủ (pop + thành phần OSM) — đầu ra tích hợp
DEMAND_DIR = DATA / "interim" / "demand"
DEMAND_H3 = DEMAND_DIR / "demand_h3.parquet"
# E-DQ7a: ô nằm ngoài lãnh thổ VN — tách ra (không xoá) để đối soát
# `input = output + clipped`, nhất quán nguyên tắc "flag dòng, không xoá".
DEMAND_H3_CLIPPED = DEMAND_DIR / "demand_h3_clipped_out.parquet"
DEMAND_REPORT = DEMAND_DIR / "demand_h3_report.json"

H3_RES_R8 = 8

# WorldPop Vietnam 2020, constrained (~100m, built-settlement aware), **UN-adjusted**.
# CC-BY 4.0. Xem https://www.worldpop.org/
#
# E-DQ7e (chốt 2026-07-29) — vì sao đổi FILE chứ không nhân hệ số trong code:
# nhân `pop` với 0,979344 cho ra đúng cùng một mảng số, nhưng biến một hằng số ma thuật
# không truy vết được thành thứ mà E-DQ10 checksum được. Hiệu chuẩn phải là **thuộc
# tính của nguồn**, không phải của pipeline.
_WORLDPOP_BASE = ("https://data.worldpop.org/GIS/Population/"
                  "Global_2000_2020_Constrained/2020/BSGM/VNM/")
WORLDPOP_URL = _WORLDPOP_BASE + "vnm_ppp_2020_UNadj_constrained.tif"
WORLDPOP_URL_UNADJUSTED = _WORLDPOP_BASE + "vnm_ppp_2020_constrained.tif"

# --- hằng số hiệu chuẩn E-DQ7e (đo trên chính hai file đã checksum, 2026-07-29) ---
#: Tổng dân số của raster UNadj (Σ pixel > 0). Neo vào **file đã băm sha256**, KHÔNG
#: neo vào một con số UN WPP chép tay: UN WPP (bản duyệt 2019) cho VN 2020 là 97,34 M,
#: còn raster UNadj tổng 97,57 M — lệch 0,24%, tức "UNadj" ≠ "đúng bằng WPP".
POP_TOTAL_EXPECTED = 97_569_444.24
POP_TOTAL_TOL = 1e-4                    # 0,01%
#: Tỉ số UNadj/unadjusted đo trên TỪNG pixel: min = p1 = trung vị = p99 = max.
POP_UNADJ_RATIO = 0.979344
#: Đơn điệu = std của tỉ số phải ~0 (đo được 2,5e-08). Nếu WorldPop đổi cách UNadj ở
#: phiên bản sau, tỉ số hết là hằng số ⇒ khẳng định "thứ hạng bất biến" tan, và mọi kết
#: luận của E-DQ7d dựa trên nó phải đo lại.
POP_UNADJ_RATIO_STD_MAX = 1e-6


def ensure_dirs():
    for d in (RAW_DIR, INTERIM_DIR, DEMAND_DIR):
        d.mkdir(parents=True, exist_ok=True)
