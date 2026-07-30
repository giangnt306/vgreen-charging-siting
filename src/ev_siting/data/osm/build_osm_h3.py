#!/usr/bin/env python3
"""build_osm_h3.py — Gộp POI + road network về lưới H3 res 8 (thành phần demand_h3).

Đọc:
  - data/raw/osm/poi/<category>.json   (overpass_poi.py — GIỮ nguyên `tags`)
  - data/interim/osm/osm_roads_h3.parquet  (roads_pbf.py)

Sinh:
  - osm_poi_points.parquet          : 1 dòng/POI **trong lãnh thổ VN** (E-DQ7a,
                                      fail-closed) + `poi_class`/`poi_access`/
                                      `poi_physical_id`/`is_poi_primary`/
                                      `complex_id`/`levels` (E-DQ7c)
  - osm_poi_outside_vn.parquet      : POI bbox-spill bị cắt (TH/LA/KH/CN) — để audit
  - osm_poi_h3.parquet              : **bảng LỚP** POI theo ô (E-DQ7c)
  - osm_demand_components_h3.parquet : theo ô H3 res 8, cột vô hướng SUY RA từ hai
                                      bảng lớp (POI + road)

**E-DQ7b — cột đường suy ra từ bảng LỚP.** `osm_roads_h3.parquet` giữ km/lane-mét theo
từng lớp `highway`; ở đây chỉ gọi `road_semantics.derive()`.

**E-DQ7c — cột POI cũng suy ra từ bảng LỚP.** Trước đây `_COUNT_COL` gộp 5 nhóm crawl
thành 3 vô hướng ngay trong hàm `aggregate`, trong đó `n_poi` = `mall`+`apartments`+
`retail` **tỉ lệ 1:1** — đo được: top-100 ô theo `n_poi` có **84,8%** số đếm là
apartments, tức feature là "mật độ toà chung cư", không phải "điểm sinh cầu". Nay:

  1. phân lớp theo **tag** (`poi_semantics.classify`), không theo nhóm crawl;
  2. **một đối tượng OSM = một lớp** (13 đối tượng từng nằm ở 2 nhóm, 4/5 tổ hợp cùng
     dồn vào `n_poi` ⇒ đếm đôi);
  3. **khử trùng node↔way** về `poi_physical_id` (giữ dòng + cờ `is_poi_primary`, nhất
     quán E-DQ1/E-DQ2 — không xoá);
  4. gộp toà chung cư về **khu** (`complex_id`, 150 m) vì 60,8% toà nằm trong cụm ≥5;
  5. `n_poi` và `n_parking` **khai tử** → 10 cột tách rời để E-DQ7d fit trọng số.

**E-DQ7a — clip lãnh thổ ở mức ĐIỂM, artefact FAIL-CLOSED.** `overpass_poi.py` crawl
bằng `VN_BBOX` thô nên 54,2% POI thu về nằm ở Campuchia/Lào/Thái/TQ. Ở đây gắn cờ
`in_vn` cho TỪNG ĐIỂM và **chỉ đếm điểm `in_vn=True`**; file `POI_POINTS` **chỉ ghi
dòng trong VN** để mọi consumer hạ nguồn sạch theo mà không cần nhớ lọc, phần bị cắt
ghi ra `POI_OUTSIDE_VN` (raw JSON vẫn bất biến, không mất dữ liệu). Khử trùng E-DQ7c
chạy TRƯỚC khi tách nên cặp node↔way vắt biên vẫn được ghép. Xem `vn_boundary.py`.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.build_osm_h3
"""
import json

import pandas as pd

from . import poi_semantics as ps
from .paths import (DEMAND_COMPONENTS, H3_RES_R8, H3_RES_R9, POI_H3,
                    POI_OUTSIDE_VN, POI_POINTS, POI_RAW_DIR, ROADS_H3, ensure_dirs)
from .road_semantics import DERIVED_COLUMNS as ROAD_DERIVED
from .road_semantics import TIER_COLUMNS, derive as derive_roads
from .vn_boundary import points_in_vn
import h3


def _read_raw():
    """Đọc mọi `<category>.json` -> DataFrame thô (giữ `tags` để phân lớp)."""
    rows = []
    for cat_file in sorted(POI_RAW_DIR.glob("*.json")):
        with open(cat_file, encoding="utf-8") as f:
            data = json.load(f)
        for el in data:
            tags = el.get("tags") or {}
            cls = ps.classify(el["category"], tags)
            if cls is None:
                continue
            rows.append({
                "osm_type": el["osm_type"], "osm_id": el["osm_id"],
                "category": el["category"], "poi_class": cls,
                "poi_access": ps.access_of(tags),
                "levels": ps.parse_levels(tags.get("building:levels")),
                "name": el.get("name", ""),
                "lat": el["lat"], "lng": el["lng"],
            })
    return pd.DataFrame(rows)


def _resolve_objects(df):
    """E-DQ7c ②: một đối tượng OSM -> **một** dòng, lớp ưu tiên cao nhất thắng.

    Khoá cũ `(osm_type, osm_id, category)` cố ý cho phép cùng một đối tượng được đếm ở
    hai nhóm crawl. Venue thắng vỏ nhà (`CLASS_PRIORITY`): một toà nhà vừa `shop=mall`
    vừa `building=apartments` là **một** trung tâm thương mại.
    """
    df = df.copy()
    df["_prio"] = df["poi_class"].map(ps.CLASS_PRIORITY)
    n_before = len(df)
    df = (df.sort_values(["osm_type", "osm_id", "_prio"])
            .drop_duplicates(["osm_type", "osm_id"], keep="first")
            .drop(columns="_prio").reset_index(drop=True))
    return df, n_before - len(df)


def _resolve_physical(df):
    """E-DQ7c ③: ghép node ↔ way/relation cùng một địa điểm -> `poi_physical_id`.

    **Chỉ ghép cặp KHÁC kiểu hình học** (node với area) trong bán kính 30 m và cùng lớp.
    Hai node gần nhau / hai polygon liền kề được coi là **hai đối tượng thật** — đó là
    lý do 30 m chứ không phải 100 m: ở 100 m số cặp `parking` nhảy 36→84 và phần tăng
    chủ yếu là bãi đỗ liền kề có thật.

    Bản chính là **area** (way/relation) vì nó mang hình học; node là bản mô tả điểm.
    Giữ mọi dòng, chỉ gắn cờ — nhất quán E-DQ1/E-DQ2.
    """
    df = df.copy().reset_index(drop=True)
    lat, lng = df["lat"].tolist(), df["lng"].tolist()
    is_node = (df["osm_type"] == "node").tolist()
    cls = df["poi_class"].tolist()

    uf = ps._Union(len(df))
    for i, j in ps.neighbour_pairs(lat, lng, ps.DUP_RADIUS_M, same_group=cls):
        if is_node[i] != is_node[j]:          # node ↔ area, không phải cùng kiểu
            uf.union(i, j)

    roots = [uf.find(i) for i in range(len(df))]
    df["_root"] = roots
    # bản chính: area trước node; hoà thì osm_id nhỏ hơn (ổn định giữa các lần chạy)
    df["_rank"] = df["osm_type"].map(lambda t: 1 if t == "node" else 0)
    primary = (df.sort_values(["_root", "_rank", "osm_id"])
                 .drop_duplicates("_root", keep="first").index)
    df["is_poi_primary"] = False
    df.loc[primary, "is_poi_primary"] = True
    df["poi_physical_id"] = (df["_root"].map(
        df.loc[primary].set_index("_root").apply(
            lambda r: f"{r['osm_type']}/{r['osm_id']}", axis=1)))
    return df.drop(columns=["_root", "_rank"])


def _resolve_complexes(df):
    """E-DQ7c ④: gộp toà chung cư về KHU (`complex_id`, đơn liên kết 150 m).

    Chỉ chạy trên bản chính (`is_poi_primary`) để bản trùng node/way không tự tạo cụm.
    Lớp khác `complex_id = None` (mỗi venue là một khu của chính nó).
    """
    df = df.copy()
    df["complex_id"] = pd.NA
    m = (df["poi_class"] == "APARTMENT") & df["is_poi_primary"]
    sub = df[m]
    if sub.empty:
        return df
    groups = ps.single_link_groups(sub["lat"].tolist(), sub["lng"].tolist(),
                                   ps.COMPLEX_RADIUS_M)
    df.loc[m, "complex_id"] = [f"apt{g:06d}" for g in groups]
    return df


def load_poi_points():
    """Raw JSON -> bảng điểm đã phân lớp, khử trùng, gán H3 + `in_vn`."""
    df = _read_raw()
    if df.empty:
        return df, {}
    df, n_obj_dup = _resolve_objects(df)
    df["h3_r8"] = [h3.latlng_to_cell(a, b, H3_RES_R8)
                   for a, b in zip(df["lat"], df["lng"])]
    df["h3_r9"] = [h3.latlng_to_cell(a, b, H3_RES_R9)
                   for a, b in zip(df["lat"], df["lng"])]
    df["in_vn"] = points_in_vn(df["lat"].values, df["lng"].values)   # E-DQ7a
    df = _resolve_physical(df)
    df = _resolve_complexes(df)
    stats = {
        "n_points": int(len(df)),
        "n_object_dup_merged": int(n_obj_dup),
        "n_physical_dup": int((~df["is_poi_primary"]).sum()),
        "n_physical_dup_in_vn": int((~df["is_poi_primary"] & df["in_vn"]).sum()),
    }
    return df, stats


def poi_layers(poi_df):
    """Bảng LỚP POI theo ô H3 (chỉ bản chính, chỉ `in_vn`)."""
    cols = ["h3_r8"] + ps.CLASS_COLUMNS
    keep = poi_df[poi_df["in_vn"] & poi_df["is_poi_primary"]]
    if keep.empty:
        return pd.DataFrame(columns=cols)

    counts = (keep.groupby(["h3_r8", "poi_class"]).size()
              .unstack("poi_class", fill_value=0))
    counts.columns = [ps.n_col(c) for c in counts.columns]
    restricted = (keep[keep["poi_access"] == "RESTRICTED"]
                  .groupby(["h3_r8", "poi_class"]).size()
                  .unstack("poi_class", fill_value=0))
    restricted.columns = [ps.restricted_col(c) for c in restricted.columns]

    apt = keep[keep["poi_class"] == "APARTMENT"]
    levels = apt.groupby("h3_r8")["levels"].agg(
        **{ps.APARTMENT_LEVELS_COL: "sum", ps.APARTMENT_LEVELS_OBS_COL: "count"})

    # KHU chung cư gán theo TRỌNG TÂM khu, không phải theo từng toà: một khu vắt qua 2 ô
    # mà đếm ở cả hai thì lại nhân đôi đúng cái vừa gộp. Σ cột này trên lưới = số khu.
    cen = (apt.groupby("complex_id")[["lat", "lng"]].mean()
           if not apt.empty else pd.DataFrame(columns=["lat", "lng"]))
    if not cen.empty:
        cen["h3_r8"] = [h3.latlng_to_cell(a, b, H3_RES_R8)
                        for a, b in zip(cen["lat"], cen["lng"])]
        complexes = cen.groupby("h3_r8").size().rename(ps.APARTMENT_COMPLEX_COL)
    else:
        complexes = pd.Series(dtype=int, name=ps.APARTMENT_COMPLEX_COL)

    out = (counts.join(restricted, how="outer").join(levels, how="outer")
           .join(complexes, how="outer").reset_index())
    for c in ps.CLASS_COLUMNS:
        if c not in out.columns:
            out[c] = 0
        out[c] = out[c].fillna(0)
        if c != ps.APARTMENT_LEVELS_COL:
            out[c] = out[c].astype(int)
    return out[cols].sort_values("h3_r8").reset_index(drop=True)


def aggregate(poi_h3, roads_df):
    """Hai bảng lớp (POI + road) -> bảng cột vô hướng theo ô."""
    merged = poi_h3.merge(roads_df, on="h3_r8", how="outer")
    merged = ps.derive(merged)          # E-DQ7c: lớp POI  -> cột vô hướng
    merged = derive_roads(merged)       # E-DQ7b: lớp road -> cột vô hướng
    cols = ["h3_r8"] + ps.DERIVED_COLUMNS + ROAD_DERIVED
    return merged[cols].sort_values("h3_r8").reset_index(drop=True)


def run():
    ensure_dirs()
    print("[h3] đọc POI raw + phân lớp + khử trùng (E-DQ7c) + clip lãnh thổ (E-DQ7a)...")
    poi_df, stats = load_poi_points()
    # E-DQ7a — FAIL-CLOSED: file chính CHỈ chứa dòng trong VN; phần bbox-spill tách
    # sang POI_OUTSIDE_VN để audit. Tách SAU khử trùng nên cặp node↔way vắt biên vẫn
    # đã được ghép; cờ `in_vn` giữ lại (toàn True) cho cổng validate.
    outside = poi_df[~poi_df["in_vn"]].reset_index(drop=True) if len(poi_df) else poi_df
    poi_vn = poi_df[poi_df["in_vn"]].reset_index(drop=True) if len(poi_df) else poi_df
    poi_vn.to_parquet(POI_POINTS, index=False)
    outside.to_parquet(POI_OUTSIDE_VN, index=False)
    n_out = len(outside)
    print(f"[h3] {len(poi_df)} POI -> giữ {len(poi_vn)} trong VN -> {POI_POINTS}")
    print(f"[h3] E-DQ7a: cắt {n_out} ngoài VN "
          f"({n_out / max(len(poi_df), 1):.1%}, fail-closed) -> {POI_OUTSIDE_VN}")
    print(f"[h3] E-DQ7c: {stats['n_object_dup_merged']} đối tượng ở >1 nhóm crawl gộp về "
          f"1 lớp · {stats['n_physical_dup']} bản trùng node/way "
          f"({stats['n_physical_dup_in_vn']} trong VN) — giữ dòng, không đếm")
    if len(poi_df):
        by_cls = (poi_df[poi_df["in_vn"]].groupby("poi_class")
                  .agg(diem=("osm_id", "size"), ban_chinh=("is_poi_primary", "sum")))
        print(by_cls.to_string())

    poi_h3 = poi_layers(poi_df)
    poi_h3.to_parquet(POI_H3, index=False)
    print(f"[h3] bảng lớp POI: {len(poi_h3)} ô -> {POI_H3}")

    roads_df = (pd.read_parquet(ROADS_H3) if ROADS_H3.exists()
                else pd.DataFrame(columns=["h3_r8"] + TIER_COLUMNS))
    if not ROADS_H3.exists():
        print(f"[h3] ! chưa có {ROADS_H3.name} — chạy roads_pbf.py trước để có road_len")
    # artefact dựng trước E-DQ7b chỉ có 2 cột vô hướng -> chặn sớm thay vì ra số 0 ngầm
    stale = [c for c in TIER_COLUMNS if c not in roads_df.columns]
    if ROADS_H3.exists() and stale:
        raise SystemExit(f"{ROADS_H3.name} thiếu cột lớp {stale[:3]}… (bản trước E-DQ7b) "
                         f"— chạy lại `python -m ev_siting.data.osm.roads_pbf`")

    comp = aggregate(poi_h3, roads_df)
    comp.to_parquet(DEMAND_COMPONENTS, index=False)
    print(f"[h3] {len(comp)} ô H3 -> {DEMAND_COMPONENTS}")
    print("      tổng:", {
        **{c: int(comp[c].sum()) for c in ps.DERIVED_COLUMNS
           if c != "apartment_levels_sum"},
        "apartment_levels_sum": int(comp.apartment_levels_sum.sum()),
        "road_access_km": round(comp.road_access_m.sum() / 1e3),
        "road_km": round(comp.road_len_m.sum() / 1e3),
        "lane_mw_km": round(comp.road_lane_mw_m.sum() / 1e3),
        "lane_ar_km": round(comp.road_lane_ar_m.sum() / 1e3),
        "bridge_km": round(comp.road_bridge_m.sum() / 1e3),
    })
    return comp


if __name__ == "__main__":
    run()
