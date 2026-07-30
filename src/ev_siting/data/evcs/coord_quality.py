#!/usr/bin/env python3
"""coord_quality.py — E-DQ1: chấm chất lượng toạ độ bằng NHIỀU tín hiệu độc lập.

VÌ SAO KHÔNG SỬA MÀ CHỈ GẮN CỜ (đo 2026-07-29). Chính sách sửa toạ độ v2 (F20) chỉ thay
toạ độ khi registry official lệch ≥200 m so với raw. Nhưng registry và evcs.vn **cùng một
backend**: 19.427 trạm khớp exact-code có khoảng cách **max 0,3 m** (p99 = 0,0). Nên nhánh
sửa **không thể kích hoạt** — thực đo: `coord_src=evcs_raw` cho 19.427/19.427, 0 sửa.
Không có nguồn độc lập nào để sửa toạ độ ⇒ E-DQ1 là bài toán **gắn cờ**, không phải bài
toán sửa. Module này chỉ gắn cờ; không dòng nào bị xoá, không toạ độ nào bị thay.

NĂM TÍN HIỆU (đo trên 19.427 trạm sạc ô tô, 2026-07-29):

  addr_mismatch          573 (2,95%)  tỉnh suy từ `address`/`name` ≠ tỉnh của toạ độ
  stacked                468 (2,41%)  ≥2 trạm trùng khít lat/lng
  DUP_COORD_SUSPECT      214 (1,10%)  cờ sẵn có từ `dedup_crosssource` (blob dày đặc)
  outside_all_communes    16 (0,08%)  toạ độ không nằm trong xã/phường nào
  outside_all_provinces    4 (0,02%)  toạ độ không nằm trong tỉnh nào — chắc chắn hỏng

NGƯỠNG ≥2 TÍN HIỆU, vì mỗi tín hiệu ĐƠN LẺ đều có dương tính giả thật:
  * `stacked` cặp thường là **hai tầng hầm hợp lệ** — VinFast đăng ký store_id riêng cho
    "Vincom Plaza Xuân Khánh, hầm B2" và "… hầm B3" cách nhau 0,8 m (đo: 2.625 cặp <50 m
    đều khác store_id, 0 cặp trùng).
  * `addr_mismatch` chỉ nói "address và toạ độ BẤT ĐỒNG", không nói cái nào sai —
    vd `C.AC000397` address ghi "Xã Bum Tở, Điện Biên" nhưng Bum Tở thuộc Lai Châu:
    ở đây **address mới là cái sai**, toạ độ đúng.
  * `outside_all_communes` gồm cả khe hở lớp xã ven biển/đảo của OSM.
Các tín hiệu chồng nhau rất ít (DUP_COORD_SUSPECT ∩ addr_mismatch = 79/214/573) nên
dùng một mình cờ cũ sẽ bỏ sót ~494 trạm bất đồng địa chỉ.

Tác động đo được: ≥1 tín hiệu 1.053 (5,42%) · **≥2 tín hiệu 168 (0,86%)** ·
baseline operational+public+primary 19.053 → **18.889**.

GHI VÀO CANONICAL LÀ MỘT BƯỚC CỦA PIPELINE, KHÔNG PHẢI THAO TÁC TAY. Bản đầu ghi ra
`canonical/stations.tmp-coordq` rồi *in ra bảo người dùng tự đổi chỗ*. Hệ quả đo được
29/07: `COORD_LOW_TRUST` có trong `features.paths.DIRTY_COORD_FLAGS` và được cả
`build_candidates._load_stations` lẫn `build_covered0` lọc, nên bảng đã giao mang 171 cờ
trong khi `make canonical` sạch cho **0** — nền `covered0` lệch **55 trạm** (19.210 vs
19.265) mà mọi QA gate vẫn PASS. Nay module tự **swap cả generation** (cùng cách
`transform_canonical._write_partitioned_atomically` làm cho F12) và `make canonical` gọi
nó, nên bảng giao ra luôn là sản phẩm của một đường chạy tái lập được.

Chạy (`make canonical` đã gọi tự động; chạy tay khi cần soi số)::

    python -m ev_siting.data.evcs.coord_quality             # ghi side table + gắn cờ canonical
    python -m ev_siting.data.evcs.coord_quality --dry-run   # chỉ báo số, không ghi
"""

import argparse
import json
import os
import re
import shutil
import unicodedata
import uuid

import numpy as np
import pandas as pd

from .admin_join import STATION_ADMIN
from .paths import INTERIM_DIR, STATIONS_DIR

COORD_QUALITY = INTERIM_DIR / "station_coord_quality.parquet"
COORD_QUALITY_REPORT = INTERIM_DIR / "coord_quality_report.json"
LOW_TRUST_FLAG = "COORD_LOW_TRUST"
MIN_SIGNALS = 2
SIGNALS = ["addr_mismatch", "stacked", "dup_coord_suspect", "outside_all_communes", "outside_all_provinces"]

# Viết tắt hay gặp trong address evcs mà tên tỉnh đầy đủ không bắt được.
PROVINCE_ALIAS = {
    "hcm": "Thành phố Hồ Chí Minh",
    "tphcm": "Thành phố Hồ Chí Minh",
    "tp hcm": "Thành phố Hồ Chí Minh",
    "sai gon": "Thành phố Hồ Chí Minh",
}


def fold(s) -> str:
    """Bỏ dấu + hạ chữ thường + gộp khoảng trắng (so khớp tên tiếng Việt)."""
    s = str(s).replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


def build_province_matcher(province_names):
    """-> hàm text->tên tỉnh. Khớp theo BIÊN TỪ, ưu tiên khớp ở CUỐI chuỗi.

    Biên từ là bắt buộc, không phải tinh chỉnh: khớp chuỗi con cho dương tính giả nặng —
    "An **Khánh, Hoà**i Đức, Hà Nội" bắt nhầm "Khánh Hoà"; "Xuân **Giang**, Sóc Sơn"
    bắt nhầm "An Giang"; "Lạc N**huế**" bắt nhầm "Huế". Ưu tiên vị trí cuối vì tên tỉnh
    theo quy ước nằm ở cuối địa chỉ Việt Nam.
    """
    lut = {fold(re.sub(r"^(Tỉnh|Thành phố)\s+", "", p)): p for p in province_names}
    lut.update(PROVINCE_ALIAS)
    pats = {k: re.compile(rf"(?<![a-z]){re.escape(k)}(?![a-z])") for k in lut if k}

    def match(text):
        best, best_pos = None, -1
        for k, rx in pats.items():
            for m in rx.finditer(text):
                if m.start() > best_pos:
                    best, best_pos = lut[k], m.start()
        return best

    return match


def province_vocabulary(admin: pd.DataFrame) -> list:
    """Danh sách 34 tên tỉnh dùng cho matcher — lấy từ LỚP RANH GIỚI, không phải từ
    giá trị quan sát được trong `admin`.

    Suy từ output join là sai hướng: tỉnh nào tình cờ không có trạm nào (hoặc bị lọc)
    sẽ biến mất khỏi từ vựng, khiến matcher mù với chính tên đó trong address — mà
    `addr_mismatch` lại là tín hiệu quan trọng nhất (576/19.507). Lớp ranh giới là
    nguồn thẩm quyền; chỉ khi không đọc được mới lùi về giá trị quan sát.
    """
    try:
        from .admin_join import load_boundaries

        _, pro = load_boundaries()
        names = [p for p in pro["name"].dropna().unique()]
        if names:
            return names
    except Exception:
        pass
    return list(admin["province_name"].dropna().unique())


def score(stations: pd.DataFrame, admin: pd.DataFrame, provinces=None) -> pd.DataFrame:
    """-> bảng 1 dòng/station_id với 5 tín hiệu + `n_signals` + `coord_low_trust`."""
    a = admin[["station_id", "province_name", "outside_all_provinces", "outside_all_communes"]]
    df = stations.merge(a, on="station_id", how="left", suffixes=("_canon", ""))

    match = build_province_matcher(provinces if provinces is not None else province_vocabulary(admin))
    text = (df["address"].fillna("") + " , " + df["name"].fillna("")).map(fold)
    df["province_from_text"] = [match(t) for t in text]
    comparable = df["province_from_text"].notna() & df["province_name"].notna()
    df["addr_mismatch"] = comparable & (df["province_from_text"] != df["province_name"])

    df["stacked"] = df.groupby(["lat", "lng"])["station_id"].transform("size") > 1
    df["dup_coord_suspect"] = df["quality_flags"].map(
        lambda v: "DUP_COORD_SUSPECT" in (v if isinstance(v, (list, np.ndarray)) else [])
    )
    for c in ("outside_all_provinces", "outside_all_communes"):
        df[c] = df[c].fillna(False).astype(bool)

    df["n_signals"] = df[SIGNALS].sum(axis=1).astype(int)
    df["coord_low_trust"] = df["n_signals"] >= MIN_SIGNALS
    df["addr_comparable"] = comparable
    return df


def apply_flag(stations: pd.DataFrame, scored: pd.DataFrame) -> pd.DataFrame:
    """Thêm `COORD_LOW_TRUST` vào `quality_flags`. KHÔNG xoá dòng, KHÔNG đổi toạ độ."""
    low = set(scored.loc[scored["coord_low_trust"], "station_id"])
    out = stations.copy()

    def add(row):
        fl = list(row["quality_flags"]) if isinstance(row["quality_flags"], (list, np.ndarray)) else []
        if row["station_id"] in low and LOW_TRUST_FLAG not in fl:
            fl.append(LOW_TRUST_FLAG)
        return fl

    out["quality_flags"] = out.apply(add, axis=1)
    return out


def _swap_stations(flagged: pd.DataFrame) -> None:
    """Thay `canonical/stations` bằng bản đã gắn cờ — atomic, có rollback (F12).

    Cùng khuôn với `transform_canonical._write_partitioned_atomically`: dựng off-path,
    đổi chỗ cả thư mục, khôi phục bản cũ nếu bước đổi chỗ hỏng. Không bao giờ `rmtree`
    output đang sống trước khi bản mới hoàn chỉnh.
    """
    parent = STATIONS_DIR.parent
    tmp = parent / f".stations-coordq-{uuid.uuid4().hex}"
    backup = parent / f".stations-prev-{uuid.uuid4().hex}"
    try:
        flagged.to_parquet(tmp, partition_cols=["province_code"], index=False)
        moved_old = False
        if STATIONS_DIR.exists():
            STATIONS_DIR.replace(backup)
            moved_old = True
        try:
            tmp.replace(STATIONS_DIR)
        except Exception:
            if STATIONS_DIR.exists():
                shutil.rmtree(STATIONS_DIR)
            if moved_old and backup.exists():
                backup.replace(STATIONS_DIR)
            raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)


def main(dry_run=False):
    if not STATION_ADMIN.exists():
        raise SystemExit(f"thiếu {STATION_ADMIN} — chạy `admin_join` trước")
    st = pd.read_parquet(STATIONS_DIR)
    admin = pd.read_parquet(STATION_ADMIN)
    scored = score(st, admin)

    rep = {
        "n_stations": int(len(scored)),
        "signals": {s: int(scored[s].sum()) for s in SIGNALS},
        "addr_comparable": int(scored["addr_comparable"].sum()),
        "n_signals_hist": {str(k): int(v) for k, v in scored["n_signals"].value_counts().sort_index().items()},
        "min_signals": MIN_SIGNALS,
        "n_low_trust": int(scored["coord_low_trust"].sum()),
        "policy": (
            "gắn cờ, KHÔNG sửa: registry official cùng backend với evcs (max 0,3 m) "
            "nên không có nguồn độc lập để sửa toạ độ"
        ),
    }
    COORD_QUALITY_REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    print("============== E-DQ1 COORD QUALITY ==============")
    for s in SIGNALS:
        print(f"  {s:22} {rep['signals'][s]:6,}  ({100 * rep['signals'][s] / len(scored):5.2f}%)")
    print(f"  {'so sánh được address':22} {rep['addr_comparable']:6,}")
    print(f"  phân bố số tín hiệu   : {rep['n_signals_hist']}")
    print(f"  >= {MIN_SIGNALS} tín hiệu -> {LOW_TRUST_FLAG}: {rep['n_low_trust']:,}")
    print("=================================================")
    if dry_run:
        print("(dry-run: KHÔNG ghi)")
        return scored

    cols = [
        "station_id",
        "station_code",
        *SIGNALS,
        "n_signals",
        "coord_low_trust",
        "addr_comparable",
        "province_from_text",
    ]
    tmp = COORD_QUALITY.with_suffix(".parquet.tmp")
    scored[cols].to_parquet(tmp, index=False)
    os.replace(tmp, COORD_QUALITY)
    print(f"-> {COORD_QUALITY.name}")

    # Gắn cờ vào canonical: ghi off-path rồi swap generation (F12 — không rmtree live output).
    flagged = apply_flag(st, scored)
    _swap_stations(flagged)
    print(f"-> {STATIONS_DIR}  ({int(scored['coord_low_trust'].sum()):,} cờ {LOW_TRUST_FLAG})")
    return scored


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="E-DQ1: chấm chất lượng toạ độ đa tín hiệu")
    ap.add_argument("--dry-run", action="store_true", help="chỉ báo số, không ghi")
    a = ap.parse_args()
    main(dry_run=a.dry_run)
