#!/usr/bin/env python3
"""build_poi.py — Overture raw → `overture_poi_points` / `overture_poi_h3`.

Bốn việc, thứ tự **không đổi được**, đúng khuôn `osm/build_osm_h3.py` để hai nguồn đối
chiếu được theo từng bước chứ không chỉ ở con số cuối:

  1. **Phân lớp** theo `poi_taxonomy.CATEGORY_MAP` (bảng chữ chung với OSM) + kiểm kê
     category chưa ánh xạ.
  2. **Khử trùng** trong nội bộ Overture → `poi_physical_id` / `is_poi_primary`. Overture
     có khử trùng liên nguồn rồi (Meta ∪ Microsoft ∪ OSM → một GERS id), nhưng nó khử
     theo *bản ghi*, không theo *địa điểm vật lý*: một cây xăng vẫn có thể có 2 GERS id
     cách nhau 20 m. Dùng CÙNG ngưỡng `DUP_RADIUS_M=30 m` với OSM, thêm điều kiện tên
     tương thích — nếu chỉ dùng khoảng cách thì 2 sạp liền kề trong một chợ bị gộp làm 1.
  3. **Clip lãnh thổ FAIL-CLOSED** (E-DQ7a): `VN_BBOX` chứa trọn Phnom Penh / Viêng Chăn
     / Nam Ninh / Hải Nam. `POI_POINTS` **chỉ ghi dòng trong VN**; phần cắt ra
     `POI_OUTSIDE_VN` để audit. Khử trùng chạy TRƯỚC khi cắt (cặp vắt biên vẫn ghép).
  4. **Gộp về H3 res 8** → bảng LỚP `n_<class>`, cùng dạng `osm_poi_h3.parquet`.

**Không lọc `confidence` và `operating_status` theo mặc định.** Cả hai là *chính sách*,
không phải *trích xuất* (C1/E-DQ7c). Báo cáo ghi phân phối của chúng và `--min-confidence`
/ `--drop-closed` tồn tại để thử, nhưng mặc định giữ nguyên: lọc ngầm cái không biết là
đúng lỗi P8 đã sửa cho `evcs`.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.overture.build_poi
    PYTHONPATH=src python -m ev_siting.data.overture.build_poi --dump   # chỉ in, không ghi
"""
import argparse
import json
import re
import sys

import h3
import pandas as pd

from ..osm import poi_semantics as ps
from ..osm.paths import H3_RES_R8, H3_RES_R9
from ..osm.vn_boundary import points_in_vn
from . import poi_taxonomy as tax
from .paths import BUILD_REPORT, POI_H3, POI_OUTSIDE_VN, POI_POINTS, RELEASE, ensure_dirs, places_raw

_NORM_RE = re.compile(r"[^a-z0-9]+")


def _norm_name(s):
    """Chuẩn hoá tên để so khớp thô (bỏ dấu câu/khoảng trắng, hạ chữ)."""
    if not isinstance(s, str):
        return ""
    return _NORM_RE.sub("", s.lower())


def _name_compatible(a, b):
    """Hai tên có thể là CÙNG một chỗ không? (một bên rỗng ⇒ coi là tương thích)."""
    if not a or not b:
        return True
    return a == b or a in b or b in a


def load_raw(release=RELEASE):
    src = places_raw(release)
    if not src.exists():
        raise SystemExit(f"thiếu {src} — chạy `make overture-fetch` trước")
    return pd.read_parquet(src)


#: `sources` luôn có một mục giả tên `Overture` = **ngày build release**, không phải
#: ngày dữ liệu được sửa. Lấy nó làm `updated_at` sẽ cho mọi place cùng một ngày rất
#: mới ⇒ báo cáo độ tươi đẹp giả. Loại khỏi cả `updated_at` lẫn `src_dataset`.
_PSEUDO_SOURCE = "overture"


def _updated_at(df):
    """`sources[].update_time` của **nguồn cấp dữ liệu thật** → timestamp mới nhất (UTC).

    ⚠️ Đo 07/08 trên release 2026-07-22.0: với `dataset='meta'` (99% place ở VN) cột này
    có **đúng 1 giá trị duy nhất** cho mọi dòng (`2026-07-02`) — nó là ngày Meta *giao
    lô dữ liệu*, KHÔNG phải ngày từng địa điểm được sửa. Chỉ `Foursquare`/`Microsoft`
    (vài trăm dòng) có giá trị thật sự biến thiên. Vì vậy `compare_osm` **không** so độ
    tươi mức đối tượng giữa hai nguồn — xem `n_unique_update_time_by_dataset` trong báo
    cáo build để thấy điều này bằng số, không phải bằng lời.
    """
    def _mx(v, ds):
        # `v`/`ds` là numpy array (list-of-list trong parquet) -> `ds or []` sẽ raise
        # "truth value of an array is ambiguous"; phải so None tường minh.
        if v is None or len(v) == 0:
            return None
        ds = ds if ds is not None else []
        vals = [t for t, d in zip(v, ds) if t and str(d).lower() != _PSEUDO_SOURCE]
        return max(vals) if vals else None
    return pd.to_datetime([_mx(v, d) for v, d in zip(df["src_update_times"], df["src_datasets"])],
                          format="ISO8601", utc=True, errors="coerce")


def _primary_dataset(df):
    """Nguồn cấp dữ liệu thật (`meta` / `Microsoft` / `OpenStreetMap` / …)."""
    def _first(v):
        if v is None or len(v) == 0:
            return None
        real = [d for d in v if d and str(d).lower() != _PSEUDO_SOURCE]
        return real[0] if real else None
    return df["src_datasets"].map(_first)


def _update_time_variety(df):
    """Số giá trị `update_time` PHÂN BIỆT của mỗi dataset — cổng chống "độ tươi giả"."""
    rows = []
    for ds_list, ut_list in zip(df["src_datasets"], df["src_update_times"]):
        if ds_list is None:
            continue
        for d, t in zip(ds_list, ut_list if ut_list is not None else []):
            if d and str(d).lower() != _PSEUDO_SOURCE:
                rows.append((str(d), t))
    if not rows:
        return {}
    x = pd.DataFrame(rows, columns=["ds", "ut"])
    g = x.groupby("ds")["ut"]
    return {k: {"n": int(n), "n_distinct_update_time": int(u)}
            for k, n, u in zip(g.size().index, g.size(), g.nunique())}


def _dedupe(df):
    """Khử trùng nội bộ → `poi_physical_id` + `is_poi_primary` (giữ mọi dòng).

    Đơn liên kết trong `DUP_RADIUS_M`, **cùng lớp** và **tên tương thích**. Bản chính là
    dòng `confidence` cao nhất; hoà thì `id` nhỏ hơn (ổn định giữa các lần chạy).
    """
    df = df.reset_index(drop=True).copy()
    lat, lng = df["lat"].tolist(), df["lng"].tolist()
    cls = df["poi_class"].tolist()
    nm = df["_nname"].tolist()

    uf = ps._Union(len(df))
    for i, j in ps.neighbour_pairs(lat, lng, ps.DUP_RADIUS_M, same_group=cls):
        if _name_compatible(nm[i], nm[j]):
            uf.union(i, j)

    df["_root"] = [uf.find(i) for i in range(len(df))]
    df["_rank"] = -df["confidence"].fillna(0.0)
    primary = (df.sort_values(["_root", "_rank", "id"])
                 .drop_duplicates("_root", keep="first").index)
    df["is_poi_primary"] = False
    df.loc[primary, "is_poi_primary"] = True
    df["poi_physical_id"] = df["_root"].map(df.loc[primary].set_index("_root")["id"])
    return df.drop(columns=["_root", "_rank"])


def build(release=RELEASE, min_confidence=0.0, drop_closed=False):
    """Raw → (points_in_vn, points_outside_vn, h3_table, report)."""
    raw = load_raw(release)
    rep = {"release": release, "n_raw_bbox": int(len(raw))}

    raw["poi_class"] = raw["category"].map(tax.classify)
    rep["unmapped_related_categories"] = [
        {"category": c, "n": n} for c, n in tax.unmapped_report(raw["category"].tolist())]

    df = raw[raw["poi_class"].notna()].copy()
    rep["n_classified"] = int(len(df))

    # phân phối 2 cột CHÍNH SÁCH — báo cáo, không lọc (xem docstring)
    rep["operating_status"] = {str(k): int(v) for k, v in
                               df["operating_status"].fillna("NULL").value_counts().items()}
    rep["confidence_quantiles"] = {q: round(float(df["confidence"].quantile(q)), 4)
                                   for q in (0.05, 0.25, 0.5, 0.75, 0.95)}
    if min_confidence > 0:
        df = df[df["confidence"].fillna(0) >= min_confidence]
        rep["n_after_min_confidence"] = int(len(df))
    if drop_closed:
        df = df[df["operating_status"].fillna("open") != "closed"]
        rep["n_after_drop_closed"] = int(len(df))

    df["updated_at"] = _updated_at(df)
    df["src_dataset"] = _primary_dataset(df)
    rep["n_unique_update_time_by_dataset"] = _update_time_variety(df)
    df["_nname"] = df["name"].map(_norm_name)

    df = _dedupe(df)
    rep["n_dup_collapsed"] = int((~df["is_poi_primary"]).sum())

    df["in_vn"] = points_in_vn(df["lat"].values, df["lng"].values)
    rep["n_in_vn"] = int(df["in_vn"].sum())
    rep["n_outside_vn"] = int((~df["in_vn"]).sum())
    rep["pct_outside_vn"] = round(100 * rep["n_outside_vn"] / max(len(df), 1), 1)

    df["h3_r8"] = [h3.latlng_to_cell(a, b, H3_RES_R8) for a, b in zip(df["lat"], df["lng"])]
    df["h3_r9"] = [h3.latlng_to_cell(a, b, H3_RES_R9) for a, b in zip(df["lat"], df["lng"])]

    cols = ["id", "poi_class", "category", "name", "lat", "lng", "h3_r8", "h3_r9",
            "confidence", "operating_status", "address", "src_dataset", "updated_at",
            "in_vn", "is_poi_primary", "poi_physical_id"]
    inside = df[df["in_vn"]][cols].reset_index(drop=True)
    outside = df[~df["in_vn"]][cols].reset_index(drop=True)

    prim = inside[inside["is_poi_primary"]]
    rep["by_class"] = {c: int(n) for c, n in prim["poi_class"].value_counts().items()}
    rep["by_dataset"] = {str(k): int(v) for k, v in
                         prim["src_dataset"].fillna("NULL").value_counts().items()}

    h3tab = (prim.groupby(["h3_r8", "poi_class"]).size().unstack(fill_value=0)
                 .reindex(columns=tax.CLASSES, fill_value=0)
                 .rename(columns=lambda c: f"n_{c.lower()}").reset_index())
    rep["n_cells"] = int(len(h3tab))
    return inside, outside, h3tab, rep


def run(release=RELEASE, dump=False, **kw):
    ensure_dirs()
    inside, outside, h3tab, rep = build(release, **kw)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    if dump:
        return rep
    inside.to_parquet(POI_POINTS, index=False)
    outside.to_parquet(POI_OUTSIDE_VN, index=False)
    h3tab.to_parquet(POI_H3, index=False)
    BUILD_REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2))
    print(f"[build] {POI_POINTS} ({len(inside):,}) · {POI_H3} ({len(h3tab):,} ô)")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--release", default=RELEASE)
    ap.add_argument("--dump", action="store_true", help="chỉ in báo cáo, không ghi file")
    ap.add_argument("--min-confidence", type=float, default=0.0)
    ap.add_argument("--drop-closed", action="store_true")
    a = ap.parse_args(argv)
    run(a.release, dump=a.dump, min_confidence=a.min_confidence, drop_closed=a.drop_closed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
