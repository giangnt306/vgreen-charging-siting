#!/usr/bin/env python3
"""admin_join.py — E-DQ3: lấp `admin_l1_code` / `province_name` / `commune_name` /
`commune_kind` cho canonical bằng point-in-polygon.

VÌ SAO KHÔNG DÙNG `official_admin.parquet` (đo 2026-07-29). Registry VinFast có sẵn
province/district/commune cho 23.240 store và phủ 100% trạm ô tô — nhưng nó là địa giới
**TRƯỚC sáp nhập 2025**: 63 tỉnh, 676 huyện, cấp huyện vẫn còn. Dự án chuẩn hoá theo
`vn_admin/valid_from=2025-07-01` (34 tỉnh, 2 cấp, bỏ huyện), và chính `address` của
evcs.vn cũng đã dùng tên mới ("phường Sài Gòn, TP.HCM"). Lấp từ registry = trộn thầm
hai niên đại địa giới → tệ hơn để null. Registry chỉ dùng để **đối chứng**, không làm nguồn.

GHI RA BẢNG PHỤ, KHÔNG NHẬP VÀO CANONICAL. `boundary_source = OSM (ODbL-derived,
VAULT-only)`: nhập thẳng vào `canonical/stations` sẽ biến CẢ BẢNG thành tác phẩm phái
sinh ODbL và siết điều kiện phát hành (liên đới F1 / `_tos_firewall`). Tách sang
`interim/station_admin.parquet` khoá `station_id` thì canonical giữ nguyên tư thế license.

`commune_name` là **nhãn OSM**, không phải mã hành chính pháp lý — dùng để phân nhóm/
đối chứng, đừng dùng làm căn cứ pháp lý.

*Đính chính `_admin_report.json`:* báo cáo đó ghi "OSM đếm 3.930 xã vs official 3.321,
lệch 609". Đo lại 2026-07-29: lớp commune **trộn thể loại** — 3.217 POLYGON + 103
MULTIPOLYGON + 585 MULTILINESTRING + 25 LINESTRING (480 dòng không tên). Lọc còn đa
giác cho **3.320**, khớp official 3.321 (lệch 1). "Lệch 609" phần lớn là artefact của
việc đếm cả feature đường, không phải ranh giới thiếu.

Chạy::

    python -m ev_siting.data.evcs.admin_join            # ghi interim/station_admin.parquet
    python -m ev_siting.data.evcs.admin_join --dry-run  # chỉ báo tỉ lệ khớp
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import DATA, INTERIM_DIR, STATIONS_DIR

# Lớp ranh giới sống ở repo evcs-dataset (nguồn chân lý admin của dự án).
# Ghi đè bằng EVCS_VN_ADMIN_DIR nếu đặt chỗ khác.
VN_ADMIN_DIR = Path(os.environ.get("EVCS_VN_ADMIN_DIR") or DATA / "ref" / "vn_admin" / "valid_from=2025-07-01")
_FALLBACK = Path(__file__).resolve().parents[5] / "evcs-dataset" / "data" / "ref" / "vn_admin" / "valid_from=2025-07-01"

ADMIN_REPORT = INTERIM_DIR / "admin_join_report.json"
# Bảng phụ khoá `station_id` — KHÔNG nhập vào canonical (xem lý do license ở main()).
STATION_ADMIN = INTERIM_DIR / "station_admin.parquet"
# `commune_code` KHONG co trong SIDE_COLS: lop OSM commune khong mang ma (3.320/3.320
# null) -> cot chet, dung phat hanh (dung loi F15 da phe binh).
SIDE_COLS = [
    "station_id",
    "station_code",
    "admin_l1_code",
    "province_name",
    "commune_name",
    "commune_kind",
    "outside_all_provinces",
    "outside_all_communes",
]
# 'Đặc khu' là cấp xã đặc biệt sau sáp nhập — giữ nguyên nhãn, không ép về COMMUNE.
KIND_MAP = {"COMMUNE": "COMMUNE", "WARD": "WARD", "SPECIAL_ZONE": "SPECIAL_ZONE"}


def _admin_dir() -> Path:
    """Cung mot lop ranh gioi voi `ev_siting.vn_boundary` (test khoa) + cung canh bao."""
    for p in (VN_ADMIN_DIR, _FALLBACK):
        if (p / "communes.parquet").exists():
            if p == _FALLBACK:
                print(f"!! CANH BAO: lop ranh gioi NGOAI repo {p} — khong nam trong MANIFEST.", flush=True)
            return p
    raise SystemExit(
        f"không tìm thấy lớp ranh giới. Thử: {VN_ADMIN_DIR} và {_FALLBACK}\n"
        "Đặt EVCS_VN_ADMIN_DIR trỏ tới thư mục chứa communes.parquet/provinces.parquet."
    )


def load_boundaries():
    """-> (communes_df, provinces_df) với cột `geom` là shapely, CHỈ giữ đa giác.

    `communes.parquet` trộn lẫn thể loại: 3.217 POLYGON + 103 MULTIPOLYGON nhưng cũng có
    585 MULTILINESTRING + 25 LINESTRING (đường ranh giới trần, 480 dòng không tên). Lọc
    còn đa giác cho **3.320** — khớp con số official 3.321 (lệch 1). Nói cách khác, cảnh báo
    "OSM đếm 3.930 vs official 3.321, lệch 609" trong `_admin_report.json` phần lớn là
    **artefact của việc đếm cả feature đường**, không phải ranh giới sai.
    """
    import numpy as np
    from shapely import from_wkb, get_type_id

    d = _admin_dir()
    out = []
    for f in ("communes.parquet", "provinces.parquet"):
        df = pd.read_parquet(d / f).reset_index(drop=True)
        df["geom"] = from_wkb([bytes(b) for b in df["geometry"]])
        keep = np.isin(get_type_id(df["geom"].to_numpy()), (3, 6)) & df["name"].notna().to_numpy()
        n_drop = int((~keep).sum())
        if n_drop:
            print(f"    {f}: bỏ {n_drop:,} feature không phải đa giác / không tên", flush=True)
        out.append(df[keep].reset_index(drop=True))
    return out[0], out[1]


def assign_admin(stations: pd.DataFrame, com: pd.DataFrame, pro: pd.DataFrame) -> pd.DataFrame:
    """Point-in-polygon: mỗi trạm -> xã/phường + tỉnh. Trả BẢN SAO có 4 cột admin.

    CẨN THẬN CHIỀU VỊ TỪ: `STRtree.query(g, predicate=p)` tính `p(g_đầu_vào, g_trong_cây)`,
    tức `point.within(polygon)` — KHÔNG phải `polygon.covers(point)`. Đặt nhầm chiều cho
    **0 match trên toàn bộ dataset mà không báo lỗi** (đúng họ lỗi đã sinh ra ghi chú
    "0 match" ở `evcs-dataset/src/evcs/transform/silver.py`). Test hồi quy giữ chiều này.
    """
    from shapely import STRtree, points

    out = stations.copy()
    # points(x=lng, y=lat) — lớp ranh giới lưu đúng trục (đo: bounds x∈[102,110], y∈[8,24]).
    pts = points(out["lng"].to_numpy(dtype=float), out["lat"].to_numpy(dtype=float))

    def _match(poly_df, label):
        tree = STRtree(poly_df["geom"].to_numpy())
        pi, si = tree.query(pts, predicate="within")
        res = np.full(len(out), -1, dtype=np.int64)
        # Ranh giới chồng lấn (OSM adm6 có chỗ đè nhau): giữ khớp ĐẦU TIÊN, đếm phần dư.
        n_multi = 0
        seen = set()
        for p_idx, poly_idx in zip(pi, si):
            if p_idx in seen:
                n_multi += 1
                continue
            seen.add(p_idx)
            res[p_idx] = poly_idx
        print(
            f"    {label}: khớp {int((res >= 0).sum()):,}/{len(out):,} "
            f"({100 * (res >= 0).mean():.2f}%) | đa-khớp bỏ qua: {n_multi:,}",
            flush=True,
        )
        return res, n_multi

    print("[admin] point-in-polygon", flush=True)
    ci, n_multi_c = _match(com, "xã/phường")
    pj, n_multi_p = _match(pro, "tỉnh")

    com_name = com["name"].to_numpy()
    com_kind = com["commune_kind"].to_numpy()
    pro_code = pro["code"].to_numpy()
    pro_name = pro["name"].to_numpy()

    out["commune_name"] = [com_name[i] if i >= 0 else None for i in ci]
    out["commune_kind"] = [KIND_MAP.get(com_kind[i]) if i >= 0 else None for i in ci]
    out["admin_l1_code"] = [pro_code[j] if j >= 0 else None for j in pj]
    out["province_name"] = [pro_name[j] if j >= 0 else None for j in pj]

    # HAI tín hiệu E-DQ1 "miễn phí", KHÔNG gộp làm một vì mức bằng chứng khác hẳn nhau:
    #   outside_all_provinces (đo: 4)  — ngoài mọi tỉnh => toạ độ chắc chắn hỏng.
    #   outside_all_communes  (đo: 16) — yếu hơn: gồm cả khe hở lớp xã ven biển/đảo của OSM.
    # Cờ theo XÃ mới là cờ bắt được cụm placeholder: 7 trạm mã C.HNO* ở (9.0004, 107.0004)
    # nằm LỌT trong polygon TP.HCM (sau sáp nhập 2025 TP.HCM trùm ra tới biển Vũng Tàu),
    # nên cờ theo tỉnh bỏ sót chúng. Toạ độ của chúng tăng đều từng nấc => sinh tự động.
    # Cả hai ĐỘC LẬP với heuristic DUP_COORD_SUSPECT hiện có.
    out["outside_all_communes"] = out["commune_name"].isna()
    out["outside_all_provinces"] = out["province_name"].isna()
    out.attrs["n_multi_commune"] = n_multi_c
    out.attrs["n_multi_province"] = n_multi_p
    return out


def cross_check(out: pd.DataFrame) -> dict:
    """Đối chứng với `official_province` (địa giới CŨ) — chỉ để phát hiện lệch thô.

    Không kỳ vọng khớp tên: 63 tỉnh cũ -> 34 tỉnh mới nên nhiều tên đã biến mất. Ta chỉ
    hỏi: trạm có toạ độ rơi vào ĐÚNG một tỉnh không, và bao nhiêu trạm không rơi vào tỉnh nào.
    """
    n = len(out)
    return {
        "n_stations": int(n),
        "commune_matched": int(out["commune_name"].notna().sum()),
        "province_matched": int(out["admin_l1_code"].notna().sum()),
        "commune_unmatched": int(out["commune_name"].isna().sum()),
        "province_unmatched": int(out["admin_l1_code"].isna().sum()),
        "n_multi_commune": int(out.attrs.get("n_multi_commune", 0)),
        "n_multi_province": int(out.attrs.get("n_multi_province", 0)),
        "commune_kind": {k: int(v) for k, v in out["commune_kind"].value_counts().items()},
        "outside_all_provinces": int(out["outside_all_provinces"].sum()),
        "outside_all_communes": int(out["outside_all_communes"].sum()),
        "in_province_but_commune_gap": int((out["outside_all_communes"] & ~out["outside_all_provinces"]).sum()),
        "n_provinces_hit": int(out["admin_l1_code"].nunique()),
    }


def main(dry_run=False):
    if not STATIONS_DIR.exists():
        raise SystemExit(f"thiếu {STATIONS_DIR} — chạy transform_canonical trước")
    st = pd.read_parquet(STATIONS_DIR)
    print(f"[admin] canonical stations: {len(st):,}", flush=True)
    com, pro = load_boundaries()
    print(f"[admin] ranh giới: {len(com):,} xã/phường, {len(pro):,} tỉnh (2025-07-01)", flush=True)

    out = assign_admin(st, com, pro)
    rep = cross_check(out)
    rep["boundary_dir"] = str(_admin_dir())
    rep["boundary_source"] = "OSM adm6 (ODbL-derived, VAULT-only)"
    rep["caveat"] = (
        "OSM đếm 3.930 xã vs official 3.321 (lệch 609) — commune_name là nhãn OSM, không phải mã hành chính pháp lý"
    )
    ADMIN_REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=============== E-DQ3 ADMIN JOIN ===============")
    for k in (
        "commune_matched",
        "commune_unmatched",
        "province_matched",
        "province_unmatched",
        "n_provinces_hit",
        "n_multi_commune",
    ):
        print(f"  {k:22}: {rep[k]:,}")
    print(f"  commune_kind          : {rep['commune_kind']}")
    print(f"  outside_all_provinces : {rep['outside_all_provinces']:,}  (toa do chac chan hong)")
    print(f"  outside_all_communes  : {rep['outside_all_communes']:,}  "
          f"(trong do {rep['in_province_but_commune_gap']:,} nam trong tinh = khe ho lop xa)")
    print(f"-> {ADMIN_REPORT.name}")
    print("================================================")
    if dry_run:
        print("(dry-run: KHÔNG ghi gì)")
        return out
    # BẢNG PHỤ, không ghi vào canonical: ranh giới là OSM (ODbL, VAULT-only), nhập thẳng
    # vào canonical sẽ biến CẢ BẢNG thành tác phẩm phái sinh ODbL và siết điều kiện phát
    # hành (liên đới F1/_tos_firewall). Tách ra thì canonical giữ nguyên tư thế license,
    # ai cần admin thì join theo `station_id`.
    side = out[SIDE_COLS].copy()
    tmp = STATION_ADMIN.with_suffix(".parquet.tmp")
    side.to_parquet(tmp, index=False)
    os.replace(tmp, STATION_ADMIN)  # atomic (F12)
    print(f"-> {STATION_ADMIN.name}: {len(side):,} dòng, khoá station_id, {len(SIDE_COLS)} cột")
    print("   LICENSE: ODbL-derived (OSM) — KHÔNG phát hành ngoài firewall khi chưa có license")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="E-DQ3: lấp cột hành chính cho canonical (địa giới 2025-07-01)")
    ap.add_argument("--dry-run", action="store_true", help="chỉ báo tỉ lệ khớp, không ghi")
    a = ap.parse_args()
    main(dry_run=a.dry_run)
