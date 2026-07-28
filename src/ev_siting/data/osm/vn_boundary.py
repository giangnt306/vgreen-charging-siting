#!/usr/bin/env python3
"""vn_boundary.py — E-DQ7a: ranh giới VN trích từ chính `.pbf` ĐÃ FREEZE.

CHẨN ĐOÁN. `overpass_poi.py` query bằng `VN_BBOX = (8,102,23.7,110)` — hộp này chứa
trọn Phnom Penh, Viêng Chăn, Nam Ninh/Sùng Tả (Quảng Tây), Hải Nam → **54,2% POI crawl
về không nằm trong lãnh thổ VN**. `osm/validate.py` lại kiểm "POI trong `VN_BBOX`",
tức đúng cái hộp sinh ra lỗi → cổng QA PASS suốt trong khi 20.256/37.362 POI là POI
nước ngoài. Lỗi này đầu độc `demand_h3` — hàm mục tiêu của MCLP.

BA NGUỒN RÒ RỈ KHÁC NHAU VỀ HÌNH HỌC (đo trên snapshot 2026-07-20) → không thể dùng
chung một chính sách:

  POI (Overpass) : ~99% khối lượng rò rỉ nằm SÂU trong nước bạn (artefact bbox).
  road (.pbf)    : 8.934 km ngoài VN nhưng **96% nằm trong 10 km quanh biên** —
                   Geofabrik cắt bằng polygon CÓ ĐỆM, không cắt đúng biên giới.
                   (Ghi chú "Geofabrik đã clip theo quốc gia" ở doc cũ là SAI.)
  pop (WorldPop) : 100% nằm trong ~2 km quanh biên — hiệu ứng mép raster, KHÔNG có
                   dân nước ngoài lọt vào.

HAI QUYẾT ĐỊNH THIẾT KẾ (đều đã đo, không phải suy đoán):

  1. **Clip POI ở mức ĐIỂM, phân loại lưới ở mức Ô.** Clip POI theo ô sẽ (a) giữ POI
     nước ngoài nằm trong ô có tâm rơi vào VN và (b) xoá POI VN nằm trong ô có tâm rơi
     ra ngoài. Chỉ điểm mới có lãnh thổ xác định.

  2. **Test ô = LỤC GIÁC ∩ POLYGON, không phải TÂM Ô ∈ POLYGON.** Ô res 8 có bán kính
     nội tiếp 0,49 km nên ô vắt qua biên có tâm rơi về bên nào cũng được. Đo thực tế:
     test theo tâm ô xoá mất **74.642 dân VN thật**; test theo giao lục giác chỉ xoá
     **6.472** (0,0065% dân số quốc gia). Cùng một ranh giới, khác nhau 11 lần.

  Ô vắt biên KHÔNG bị xoá mà giữ kèm `frac_in_vn` (tỉ lệ diện tích thuộc VN) để bước
  `demand_weight` tự quyết chính sách chia tỉ lệ — 1.391 ô biên có `frac_in_vn < 0,5`
  và chứa 69.527 dân, quá lớn để xử lý ngầm bằng một cờ nhị phân.

VÌ SAO TỰ RÁP RING THAY VÌ `FileProcessor.with_areas()`. Đã thử: bộ ráp area của
osmium trả về **rỗng** cho relation 49915 — 15/614 way outer bị Geofabrik cắt ở mép
extract nên ring không khép, assembler bỏ qua **im lặng**. `linemerge` + `polygonize`
chịu được khuyết đó. Chính vì chế độ lỗi là "im lặng" nên module này BẮT BUỘC có cổng
QA neo điểm (③) — nếu không, một lần OSM đổi cấu trúc relation là cả pipeline lặng lẽ
chạy với polygon rỗng và clip sạch mọi thứ.

NGUỒN: relation `admin_level=2` id 49915 lấy từ `data/raw/osm/vietnam-latest.osm.pbf`
đã freeze (E-DQ10, `snapshot_id=2026-07-20`) → **không thêm nguồn thô mới**, không đụng
MANIFEST, tái lập được. KHÔNG re-crawl Overpass bằng bộ lọc `(poly:…)`: polygon 614 way
làm query cực nặng, và re-crawl là phá snapshot đã đóng băng — clip là bước DẪN XUẤT
trên raw bất biến.

Module cũng ráp luôn polygon `admin_level=4` (tỉnh) trong cùng một lượt đọc `.pbf` —
đúng artefact **E-DQ3** cần để spatial-join admin (một lượt đọc, hai issue).

Output:
  data/interim/osm/vn_boundary.parquet    : level, osm_rel_id, name, area_km2, geom_wkb
  data/interim/osm/vn_boundary.geojson    : bản xem/QA trên map
  data/interim/osm/vn_boundary_report.json: cổng QA + thống kê

Chạy:
    PYTHONPATH=src python -m ev_siting.data.osm.vn_boundary            # dựng
    PYTHONPATH=src python -m ev_siting.data.osm.vn_boundary --verify   # chỉ chạy lại cổng QA
"""
import argparse
import json
import math
import sys
import time
from functools import lru_cache

import numpy as np
import osmium
import osmium.filter
import pandas as pd
from shapely import STRtree
from shapely import wkb as shapely_wkb
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, polygonize, transform, unary_union

import h3

from ev_siting.data.provenance.manifest import load_manifest
from .paths import (PBF_PATH, VN_ADM2_REL_ID, VN_BOUNDARY, VN_BOUNDARY_GEOJSON,
                    VN_BOUNDARY_REPORT, ensure_dirs)

#: tỉnh được coi là "phía VN" nếu >= ngần này diện tích nằm trong polygon quốc gia
#: (relation adm4 của TQ/Campuchia/Lào cũng có trong extract nhưng ray ra ngoài).
PROV_IN_VN_MIN = 0.5

#: Dải diện tích chấp nhận được (km²). Polygon `admin_level=2` của OSM bao gồm **lãnh
#: hải**, nên KHÔNG gate quanh 331.212 km² (diện tích đất liền) — đo được ~507.000 km².
AREA_KM2_RANGE = (450_000, 560_000)

#: Neo QA ③ — điểm PHẢI nằm trong / PHẢI nằm ngoài polygon. Các điểm "ngoài" đều nằm
#: TRONG `VN_BBOX`, tức chúng test đúng lỗ hổng mà E-DQ7a nói tới.
ANCHORS_IN = {
    "Hà Nội": (21.0278, 105.8342),
    "TP.HCM": (10.7769, 106.7009),
    "Đà Nẵng": (16.0544, 108.2022),
    "Mũi Cà Mau": (8.6000, 104.8500),
    "Phú Quốc": (10.2200, 103.9600),
    "Móng Cái": (21.5300, 107.9600),
}
ANCHORS_OUT = {
    "Phnom Penh (KH)": (11.5560, 104.9280),
    "Viêng Chăn (LA)": (17.9750, 102.6300),
    "Nam Ninh (CN)": (22.8170, 108.3670),
    "Ubon Ratchathani (TH)": (15.2400, 104.8500),
    "Savannakhet (LA)": (16.5500, 104.7500),
}

#: trạng thái ô lưới so với lãnh thổ VN.
CELL_STATES = ("INSIDE", "BORDER", "OUTSIDE")


# --------------------------------------------------------------------------- #
# hình học                                                                     #
# --------------------------------------------------------------------------- #
def area_km2(geom, lat0_deg: float = 16.0) -> float:
    """Diện tích (km²) qua phép chiếu trụ đồng diện tích quanh vĩ tuyến chuẩn VN."""
    r, lat0 = 6371.0088, math.radians(lat0_deg)

    def _proj(x, y):
        return (r * np.radians(x) * math.cos(lat0),
                r * np.sin(np.radians(y)) / math.cos(lat0))

    return transform(_proj, geom).area


def _assemble(way_ids, geoms):
    """Ráp polygon từ các way biên: linemerge -> polygonize (chịu được way khuyết).

    Trả về ``(geom | None, n_dùng, n_khuyết)``.
    """
    lines = [geoms[i] for i in way_ids if i in geoms]
    missing = len(way_ids) - len(lines)
    if not lines:
        return None, 0, missing
    polys = list(polygonize(linemerge(unary_union(lines))))
    if not polys:
        return None, len(lines), missing
    geom = unary_union(polys)
    if not geom.is_valid:
        geom = geom.buffer(0)
    return geom, len(lines), missing


def _read_relations(pbf):
    """Lượt 1: relation adm2 (VN) + mọi relation adm4 -> tập way outer của mỗi cái."""
    adm2, adm4 = None, {}
    for rel in osmium.FileProcessor(pbf, osmium.osm.RELATION):
        if rel.tags.get("type") != "boundary":
            continue
        level = rel.tags.get("admin_level")
        if level not in ("2", "4"):
            continue
        ways = {m.ref for m in rel.members if m.type == "w" and m.role in ("outer", "")}
        rec = {"osm_rel_id": rel.id, "name": rel.tags.get("name", ""), "ways": ways}
        if level == "2" and rel.id == VN_ADM2_REL_ID:
            adm2 = rec
        elif level == "4":
            adm4[rel.id] = rec
    return adm2, adm4


def _read_way_geoms(pbf, way_ids):
    """Lượt 2: hình học các way cần dùng (cần cache toạ độ node -> đọc cả NODE)."""
    fp = (osmium.FileProcessor(pbf, osmium.osm.NODE | osmium.osm.WAY)
          .with_locations()
          .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
          .with_filter(osmium.filter.IdFilter(sorted(way_ids))))
    geoms = {}
    for way in fp:
        coords = [(n.lon, n.lat) for n in way.nodes if n.location.valid()]
        if len(coords) >= 2:
            geoms[way.id] = LineString(coords)
    return geoms


# --------------------------------------------------------------------------- #
# cổng QA                                                                      #
# --------------------------------------------------------------------------- #
def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def qa_gates(report, vn, stats):
    """5 cổng đóng E-DQ7a thật, không chỉ "có file polygon"."""
    all_ok = True

    # ① polygon hợp lệ & không rỗng (bắt chế độ lỗi "assembler trả rỗng im lặng")
    ok = (vn is not None and not vn.is_empty and vn.is_valid
          and vn.geom_type in ("Polygon", "MultiPolygon"))
    all_ok &= _check(report, "boundary_valid", ok,
                     "rỗng/không hợp lệ" if not ok else vn.geom_type)
    if not ok:
        return False

    # ② diện tích trong dải (bắt ring khép sai -> polygon phình/teo)
    a = area_km2(vn)
    lo, hi = AREA_KM2_RANGE
    all_ok &= _check(report, "boundary_area_km2", lo <= a <= hi,
                     f"{a:,.0f} km² (dải {lo:,}–{hi:,}; adm2 gồm cả lãnh hải)")

    # ③ phần đất liền phải chiếm áp đảo (chống ráp nhầm ring đảo thành thân chính)
    parts = list(vn.geoms) if vn.geom_type == "MultiPolygon" else [vn]
    share = max(p.area for p in parts) / vn.area
    all_ok &= _check(report, "boundary_mainland_share", share >= 0.9,
                     f"{share:.3f} ({len(parts)} phần)")

    # ④ neo điểm — cổng QUAN TRỌNG NHẤT: mọi điểm "ngoài" đều nằm TRONG VN_BBOX
    bad = [n for n, (la, lo_) in ANCHORS_IN.items() if not vn.contains(Point(lo_, la))]
    bad += [f"{n}(!)" for n, (la, lo_) in ANCHORS_OUT.items() if vn.contains(Point(lo_, la))]
    all_ok &= _check(report, "boundary_anchor_points", not bad,
                     f"{len(ANCHORS_IN)} trong + {len(ANCHORS_OUT)} ngoài"
                     + (f"; SAI: {bad}" if bad else ""))

    # ⑤ độ phủ way biên (Geofabrik cắt vài way ở mép -> WARN, không chặn)
    used, miss = stats["adm2_ways_used"], stats["adm2_ways_missing"]
    frac = miss / max(used + miss, 1)
    all_ok &= _check(report, "boundary_ways_resolved", frac <= 0.05,
                     f"{miss}/{used + miss} way khuyết ({frac:.1%})", fatal=False)

    # bổ sung (E-DQ3): số tỉnh ráp được — thông tin, không chặn E-DQ7a
    all_ok &= _check(report, "provinces_assembled", stats["n_provinces"] >= 30,
                     f"{stats['n_provinces']} polygon adm4 phía VN", fatal=False)
    return all_ok


# --------------------------------------------------------------------------- #
# dựng                                                                         #
# --------------------------------------------------------------------------- #
def build(pbf=PBF_PATH):
    ensure_dirs()
    if not pbf.exists():
        raise SystemExit(f"thiếu {pbf} — chạy roads_pbf.py (tải Geofabrik) trước")
    t0 = time.time()

    print(f"[bnd] lượt 1: đọc relation ranh giới từ {pbf.name}...")
    adm2, adm4 = _read_relations(pbf)
    if adm2 is None:
        raise SystemExit(f"không thấy relation admin_level=2 id={VN_ADM2_REL_ID} trong {pbf.name}")
    need = set(adm2["ways"]).union(*[r["ways"] for r in adm4.values()]) if adm4 else set(adm2["ways"])
    print(f"[bnd]   adm2 '{adm2['name']}' {len(adm2['ways'])} way · adm4 {len(adm4)} relation "
          f"· cần {len(need)} way")

    print("[bnd] lượt 2: đọc hình học way (cache toạ độ node)...")
    geoms = _read_way_geoms(pbf, need)
    print(f"[bnd]   {len(geoms)}/{len(need)} way có hình học  ({time.time() - t0:.0f}s)")

    vn, used2, miss2 = _assemble(adm2["ways"], geoms)
    if vn is None:
        raise SystemExit("không ráp được ring nào cho ranh giới quốc gia")
    rows = [{"level": 2, "osm_rel_id": adm2["osm_rel_id"], "name": adm2["name"] or "Việt Nam",
             "area_km2": round(area_km2(vn), 1), "frac_in_vn": 1.0,
             "n_ways_used": used2, "n_ways_missing": miss2,
             "geom_wkb": vn.wkb}]

    n_prov_fail = 0
    for rec in adm4.values():
        geom, used, miss = _assemble(rec["ways"], geoms)
        if geom is None or geom.is_empty or geom.area <= 0:
            n_prov_fail += 1
            continue
        frac = geom.intersection(vn).area / geom.area
        if frac < PROV_IN_VN_MIN:      # tỉnh của TQ/KH/LA trong extract
            continue
        rows.append({"level": 4, "osm_rel_id": rec["osm_rel_id"], "name": rec["name"],
                     "area_km2": round(area_km2(geom), 1), "frac_in_vn": round(frac, 4),
                     "n_ways_used": used, "n_ways_missing": miss,
                     "geom_wkb": geom.wkb})

    df = pd.DataFrame(rows).sort_values(["level", "area_km2"], ascending=[True, False])
    df.to_parquet(VN_BOUNDARY, index=False)
    print(f"[bnd] -> {VN_BOUNDARY}  ({len(df)} polygon: 1 adm2 + {len(df) - 1} adm4)")

    _write_geojson(df)

    stats = {
        "snapshot_id": (load_manifest() or {}).get("snapshot_id"),
        "pbf": pbf.name,
        "adm2_rel_id": VN_ADM2_REL_ID,
        "adm2_area_km2": round(area_km2(vn), 1),
        "adm2_parts": len(vn.geoms) if vn.geom_type == "MultiPolygon" else 1,
        "adm2_ways_used": used2,
        "adm2_ways_missing": miss2,
        "n_provinces": int((df.level == 4).sum()),
        "n_provinces_failed_assembly": n_prov_fail,
        "elapsed_s": round(time.time() - t0, 1),
    }
    report = {"checks": [], "stats": stats}
    print("\n[bnd] cổng QA:")
    ok = qa_gates(report, vn, stats)
    report["overall"] = "PASS" if ok else "FAIL"
    VN_BOUNDARY_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    print(f"\n[{report['overall']}] -> {VN_BOUNDARY_REPORT}")
    return df, ok


def _write_geojson(df):
    feats = []
    for r in df.itertuples():
        feats.append({
            "type": "Feature",
            "properties": {"level": int(r.level), "osm_rel_id": int(r.osm_rel_id),
                           "name": r.name, "area_km2": float(r.area_km2)},
            "geometry": shapely_wkb.loads(r.geom_wkb).__geo_interface__,
        })
    VN_BOUNDARY_GEOJSON.write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
        encoding="utf-8")
    print(f"[bnd] -> {VN_BOUNDARY_GEOJSON}")


# --------------------------------------------------------------------------- #
# API cho các bước hạ nguồn                                                    #
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def load_vn_polygon():
    """Polygon lãnh thổ VN (adm2). Cache vì mọi consumer đều dùng lại."""
    if not VN_BOUNDARY.exists():
        raise SystemExit(
            f"thiếu {VN_BOUNDARY} — chạy `make boundary` trước "
            "(E-DQ7a: không clip biên giới thì 54% POI là POI nước ngoài)")
    df = pd.read_parquet(VN_BOUNDARY)
    geoms = [shapely_wkb.loads(b) for b in df.loc[df.level == 2, "geom_wkb"]]
    if not geoms:
        raise SystemExit(f"{VN_BOUNDARY} không có polygon adm2 — dựng lại `make boundary`")
    return unary_union(geoms)


@lru_cache(maxsize=1)
def load_provinces():
    """[(name, osm_rel_id, geom)] cấp tỉnh — artefact dùng lại cho **E-DQ3**."""
    df = pd.read_parquet(VN_BOUNDARY)
    p = df[df.level == 4]
    return [(r.name, int(r.osm_rel_id), shapely_wkb.loads(r.geom_wkb)) for r in p.itertuples()]


def points_in_vn(lat, lng):
    """Mảng bool: điểm có nằm trong lãnh thổ VN không (mức ĐIỂM — xem docstring §1)."""
    lat, lng = np.asarray(lat, dtype=float), np.asarray(lng, dtype=float)
    mask = np.zeros(len(lat), dtype=bool)
    if not len(lat):
        return mask
    pts = np.array([Point(x, y) for x, y in zip(lng, lat)], dtype=object)
    # shapely áp predicate theo chiều input.predicate(tree) -> "within" (point.within(vn));
    # dùng "contains" sẽ luôn False. Cùng bẫy đã ghi ở landuse/osm_exclusion.py.
    idx, _ = STRtree([load_vn_polygon()]).query(pts, predicate="within")
    mask[idx] = True
    return mask


def classify_cells(cells):
    """Phân loại ô H3 theo LỤC GIÁC ∩ polygon (không phải tâm ô — xem docstring §2).

    Trả về DataFrame ``h3_r8, cell_state ∈ {INSIDE,BORDER,OUTSIDE}, frac_in_vn``.
    """
    cells = list(cells)
    if not cells:
        return pd.DataFrame(columns=["h3_r8", "cell_state", "frac_in_vn"])
    vn = load_vn_polygon()
    hexes = np.array([Polygon([(lo, la) for la, lo in h3.cell_to_boundary(c)])
                      for c in cells], dtype=object)
    tree = STRtree(hexes)
    # chiều ngược với points_in_vn: ở đây tree chứa các ô, geometry truy vấn là VN
    # -> trả về chỉ số ô thoả vn.intersects(hex) / vn.contains_properly(hex).
    inter = np.zeros(len(hexes), dtype=bool)
    inter[np.unique(tree.query(vn, predicate="intersects"))] = True
    full = np.zeros(len(hexes), dtype=bool)
    full[np.unique(tree.query(vn, predicate="contains_properly"))] = True

    state = np.where(~inter, "OUTSIDE", np.where(full, "INSIDE", "BORDER"))
    frac = full.astype(float)
    for i in np.flatnonzero(state == "BORDER"):
        frac[i] = hexes[i].intersection(vn).area / hexes[i].area
    return pd.DataFrame({"h3_r8": cells, "cell_state": state, "frac_in_vn": frac})


def verify():
    """Chạy lại cổng QA trên artefact đã có (không đọc lại `.pbf`)."""
    if not VN_BOUNDARY.exists():
        raise SystemExit(f"thiếu {VN_BOUNDARY} — chạy `make boundary`")
    df = pd.read_parquet(VN_BOUNDARY)
    vn = load_vn_polygon()
    a2 = df[df.level == 2].iloc[0]
    stats = {"adm2_ways_used": int(a2.n_ways_used), "adm2_ways_missing": int(a2.n_ways_missing),
             "n_provinces": int((df.level == 4).sum())}
    report = {"checks": [], "stats": stats}
    print("[bnd] verify cổng QA:")
    ok = qa_gates(report, vn, stats)
    print(f"\n[{'PASS' if ok else 'FAIL'}]")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="E-DQ7a — ranh giới VN từ .pbf đã freeze")
    ap.add_argument("--verify", action="store_true",
                    help="chỉ chạy lại cổng QA trên artefact đã dựng")
    a = ap.parse_args()
    ok = verify() if a.verify else build()[1]
    sys.exit(0 if ok else 1)
