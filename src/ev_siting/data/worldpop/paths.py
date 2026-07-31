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
# E-DQ7e: nguồn chính thức là bản **UN-adjusted**. Bản unadjusted GIỮ LẠI trên đĩa (đã
# checksum trong MANIFEST) vì nó là chứng cứ tái lập được của cổng
# `pop_scale_ratio_is_constant` — không có nó thì khẳng định "UNadj là hằng số quốc gia,
# thứ hạng ô bất biến" trở lại thành lời hứa.
POP_TIF = RAW_DIR / "vnm_ppp_2020_UNadj_constrained.tif"
POP_TIF_UNADJUSTED = RAW_DIR / "vnm_ppp_2020_constrained.tif"
# R2024B 2025 (constrained, mặt nạ công trình mới) — nguồn của cột SENSITIVITY
# `pop_2025` (Q6iii): mặt nạ 2020 gán pop=0 cho 60,3% số ô có đường (audit 29/07).
# Repo Kỳ đã tải sẵn -> nhận fallback sang repo anh em để không tải lại 74 MB;
# ghi đè bằng env EVCS_WORLDPOP_2025_TIF (xem `resolve_tif`).
POP_TIF_2025 = RAW_DIR / "vnm_pop_2025_CN_100m_R2024B_v1.tif"
# R2024B 2020 (constrained) — cap CUNG THE HE voi POP_TIF_2025 de so per-cell hop le.
# Do 2026-07-31: 188.094 o/11,33M nguoi chi co o footprint R2024B (khac mo hinh
# settlement, khong phai tang dan) -> KHONG so per-cell cheo the he voi `pop`/`pop_adj`;
# xem schema-contract muc pop_2025.
POP_TIF_2020_R24 = RAW_DIR / "vnm_pop_2020_CN_100m_R2024B_v1.tif"

# --- derived (data/interim/worldpop) ---
INTERIM_DIR = DATA / "interim" / "worldpop"
POP_H3 = INTERIM_DIR / "worldpop_pop_h3.parquet"        # h3_r8 -> pop
POP_H3_2025 = INTERIM_DIR / "worldpop_pop_2025_h3.parquet"  # h3_r8 -> pop (R2024B 2025)
POP_H3_2020_R24 = INTERIM_DIR / "worldpop_pop_2020_r24_h3.parquet"  # h3_r8 -> pop (R2024B 2020)
POP_REPORT = INTERIM_DIR / "worldpop_pop_report.json"   # cổng QA hiệu chuẩn (E-DQ7e)

# demand_h3 đầy đủ (pop + thành phần OSM) — đầu ra tích hợp
DEMAND_DIR = DATA / "interim" / "demand"
DEMAND_H3 = DEMAND_DIR / "demand_h3.parquet"
# E-DQ7a: ô nằm ngoài lãnh thổ VN — tách ra (không xoá) để đối soát
# `input = output + clipped`, nhất quán nguyên tắc "flag dòng, không xoá".
DEMAND_H3_CLIPPED = DEMAND_DIR / "demand_h3_clipped_out.parquet"
DEMAND_REPORT = DEMAND_DIR / "demand_h3_report.json"
# settlement (DEGURBA + đĩa k=1 + cờ đất đai) — sinh SAU demand_h3 bởi `settlement.py`;
# consumer đọc TRỰC TIẾP bảng này, `demand_h3` KHÔNG mang cột settlement.
SETTLEMENT_H3 = DEMAND_DIR / "settlement_h3.parquet"

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

# WorldPop R2024B 2025, constrained. CC-BY 4.0.
WORLDPOP_2025_URL = ("https://data.worldpop.org/GIS/Population/"
                     "Individual_countries/VNM/vnm_pop_2025_CN_100m_R2024B_v1.tif")
WORLDPOP_2020_R24_URL = ("https://data.worldpop.org/GIS/Population/"
                         "Global_2015_2030/R2024B/2020/VNM/v1/100m/constrained/"
                         "vnm_pop_2020_CN_100m_R2024B_v1.tif")

# vintage -> (đường raster, output H3, URL tải)
POP_SOURCES = {
    "2020": (POP_TIF, POP_H3, WORLDPOP_URL),
    "2025": (POP_TIF_2025, POP_H3_2025, WORLDPOP_2025_URL),
    "2020_r24": (POP_TIF_2020_R24, POP_H3_2020_R24, WORLDPOP_2020_R24_URL),
}

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

# --- E-DQ7f: dồn cục dasymetric + tái phân bổ theo built-up (2026-07-29) ---
#: Bảng pop ĐÃ HIỆU CHỈNH VỊ TRÍ: giữ `pop` (UN-anchored, E-DQ7e) + thêm `pop_adj`
#: (đặt lại chỗ theo built-up) + cờ chẩn đoán. Là đầu vào của `build_demand_h3`.
POP_ADJ_H3 = INTERIM_DIR / "worldpop_pop_adj_h3.parquet"
POP_ADJ_REPORT = INTERIM_DIR / "worldpop_pop_adj_report.json"
#: Ngưỡng detector (đặt tay nhưng neo ngoại vi — xem reconcile_dasymetric.py).
POP_MAX_PX_IMPLAUSIBLE = 1000.0        # p99 built-up lõi TP.HCM = 737 < 1000 < flagged p50 1201
POP_TOP3_SHARE_IMPLAUSIBLE = 0.8       # cùng pop > 2000 -> dồn cục
POP_PIXEL_IMPLAUSIBLE_MIN_POP = 2000.0
#: Tỉ số quốc gia WorldPop(UNadj 2020)/VNSDI DANSO(đăng ký 2025) = 97,569/113,626.
#: Dùng để TRUNG HOÀ lệch niên đại trước khi so mức cấp xã (RETOTAL chỉ kích hoạt khi
#: vượt xa mức niên đại giải thích được).
POP_WORLDPOP_OVER_DANSO = 0.859
#: RETOTAL khi WorldPop cấp xã > 1,5× DANSO (= r>1,75 sau trung hoà niên đại). Đo được:
#: 50/139 ô (63% khối lượng bị cờ) rơi vào đây; 16 ô có 1 ô > cả xã (bất khả thi).
POP_RETOTAL_RATIO = 1.5
#: ⚠️ HẰNG SỐ CHẾT — khai báo cho E-DQ7f nhưng `reconcile_dasymetric.py` chỉ import chứ
#: KHÔNG dùng, và docstring cũ ("p99 ô lõi TP.HCM = 737") mô tả **sai đại lượng**: 737 là
#: `pop_per_eff_px` (người/pixel hiệu dụng), không phải người/ha built-up. Đo lại đúng
#: đại lượng (2026-07-30): p99 mật độ built-up của lõi TP.HCM r=12km là **904**, max
#: 1.491; ngưỡng 750 gắn cờ **15.056 ô / 8,97 M người (9,2% toàn quốc)** trong đó có 26 ô
#: lõi TP.HCM/Hà Nội THẬT ⇒ vô dụng làm detector. Giữ lại kèm cảnh báo này để không ai
#: đấu dây nó vào một cổng QA. Xem `reallocate_roadless.py` (E-DQ8b) về lý do built-up
#: chỉ dùng làm **trọng số ô nhận**, không dùng làm detector.
POP_BUILTUP_DENSITY_CEIL = 750.0

# --- E-DQ8b: dời dân ở ô không có lối vào (2026-07-30) ---
#: Bảng pop sau CẢ HAI phép đặt lại chỗ (7f dồn cục + 8b roadless). Giữ nguyên hợp đồng
#: D5 của 7f: `pop` UN-anchored cho phát biểu tuyệt đối, `pop_adj` cho consumer XẾP HẠNG.
POP_ACC_H3 = INTERIM_DIR / "worldpop_pop_acc_h3.parquet"
POP_ACC_REPORT = INTERIM_DIR / "worldpop_pop_acc_report.json"


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
