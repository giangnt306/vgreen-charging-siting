#!/usr/bin/env python3
"""audit_poi.py — Kiểm kê `osm_poi_points` trong một AOI, trước khi dựng map viewer.

Trả lời **một** câu hỏi: với mỗi `poi_class`, bao nhiêu phần trăm dòng có thể có
polygon, và class nào không đáng đi tìm polygon.

⚠️ **`osm_type == 'way'` KHÔNG có nghĩa là "đã có polygon".**
`overpass_poi.py` query bằng ``out center tags;`` ⇒ raw JSON chỉ giữ **tâm** của
way/relation, không có `geometry` lẫn `nodes`. Hình học phải lấy từ nơi khác —
`data/raw/osm/vietnam-latest.osm.pbf` (cùng snapshot 21/07, đã khai trong MANIFEST;
cùng lý do khiến `poi_timestamps.py` phải đọc pbf). Vì vậy cột way/rel % ở đây là
**CHẶN TRÊN** của polygon coverage:

    coverage thật = (way/rel %) × (tỉ lệ osm_id resolve được thành closed way /
                                   multipolygon hợp lệ trong pbf)

Đo hệ số thứ hai là việc của bước sau; script này cố ý **không** mở pbf (318 MB)
để giữ `--check` chạy trong một nhịp thở.

Dùng:
    uv run python -m ev_siting.viz.audit_poi --city hanoi
    uv run python -m ev_siting.viz.audit_poi --city hanoi --check   # exit 1 nếu vi phạm
"""
from __future__ import annotations

import argparse
import collections
import sys

import pandas as pd

from ev_siting.aoi import add_aoi_args, aoi_from_args
from ev_siting.data.osm.paths import PBF_PATH, POI_POINTS
from ev_siting.data.osm.poi_semantics import CLASSES

#: Ngưỡng way/rel % dưới mức này thì đi tìm polygon không đáng công.
POLYGON_WORTH_PCT = 50.0

#: Lớp có way **tuyến tính** (không đóng) ⇒ way % cao vẫn không dựng được polygon.
#: **RỖNG — đo 07/08 bác bỏ giả thuyết này.** Nghi PARKING_STREET rơi vào đây vì
#: `parking=street_side/lane/on_kerb` chạy dọc lề đường; `--pbf` cho **0/4.159 way mở**
#: trên MỌI lớp, PARKING_STREET `hụt = 0,0`. Nguyên nhân: bộ lọc crawl là
#: `["amenity"="parking"]`, mà `amenity=parking` trong OSM luôn là VÙNG (đỗ ven đường
#: vẽ thành polygon hẹp dọc lề); cái tuyến tính là `parking:lane:*` gắn trên way đường
#: và không lọt vào bộ lọc. Giữ hằng số rỗng thay vì xoá, để lần sau không ai suy lại.
#: ⚠️ PARKING_STREET vẫn bị loại khỏi **siting** — nhưng vì lý do NGỮ NGHĨA (không đặt
#: được trụ, lý lẽ gốc của `poi_semantics`), không phải hình học. Map viewer vẽ được.
LINEAR_CLASSES: set[str] = set()

# --- class MỚI, đã promote vào poi_semantics.CLASSES (07/08) --------------------
# Khai lại tag ở đây vì `osm_poi_points.parquet` **chưa** chứa hai lớp này: nhóm crawl
# `hospital`/`school` mới thêm vào `overpass_poi.CATEGORIES`, `data/raw/osm/poi/` chưa có
# file tương ứng. Cho tới khi crawl lại (hoặc rút từ .pbf), mục 7 là cách DUY NHẤT đo
# được nền của chúng. Xoá khối này sau lần rebuild đầu tiên.
#
# `healthcare=hospital` (193/1.424 VN) chồng gần hết lên `amenity=hospital`
# (275/1.514) ⇒ OR rồi khử trùng theo (osm_type, osm_id), KHÔNG cộng dồn.
CANDIDATE_CLASSES = {
    "HOSPITAL": (("amenity", "hospital"), ("healthcare", "hospital")),
    "SCHOOL": (("amenity", "school"),),
}

# --- SUPERSTORE: ĐÃ CÂN NHẮC VÀ LOẠI (07/08) -----------------------------------
# Ghi lại để không ai đề xuất lại (cùng kiểu ghi chú với `capacity` của parking, C5).
#
# `shop=superstore` KHÔNG tồn tại trong OSM. Bốn ứng viên đều hỏng, đo trên VN:
#   `shop=wholesale`        65n/11w  -> kho vận ("Kho Sagawa Bắc Ninh"), không bán lẻ
#   `shop=department_store` 1.114n/22w -> lẫn văn phòng phẩm + công ty hoá chất
#   `shop=variety_store`    263n/60w -> tạp hoá nhỏ ("shop hồng anh")
#   `shop=convenience`      6.892n/171w -> Circle K; 97,6% node
# Siêu thị lớn VN (Big C/GO!/MM Mega/Lotte) chỉ phân biệt được bằng TÊN, nên đã thử
# lọc brand trong SUPERMARKET+MALL+DEPT_STORE. Đo trên AOI Hà Nội: **79/422 khớp
# (18,7%), chỉ 16 là way/rel => ~3,8% polygon**; trong đó 48/79 là WinMart (siêu thị
# thường) và `metro` khớp nhầm "Vincom Center Metropolis". Bỏ nhiễu thì còn ~15 điểm.
# => Nền dữ liệu không đỡ nổi một class riêng. Cùng lý lẽ E-DQ7g chỉ cho FUEL của
#    Overture đi tiếp: số đếm to không phải là độ phủ tốt.


def _rule(title, width=78):
    print(f"\n{title}\n{'─' * width}")


def _load(aoi):
    """Đọc POI parquet, cắt theo AOI (hình tròn — cùng định nghĩa với cả pipeline)."""
    if not POI_POINTS.exists():
        raise SystemExit(f"thiếu {POI_POINTS} — chạy `make osm` trước")
    df = pd.read_parquet(POI_POINTS)
    inside = aoi.contains(df["lat"].to_numpy(), df["lng"].to_numpy())
    return df, df[inside].copy()


def report_class_by_type(poi):
    """(1) Đếm dòng theo osm_type × poi_class + (2) tỉ lệ way/relation mỗi lớp."""
    _rule("1+2. SỐ DÒNG THEO osm_type × poi_class · tỉ lệ có thể có polygon")
    tab = pd.crosstab(poi["poi_class"], poi["osm_type"])
    for col in ("node", "way", "relation"):
        if col not in tab.columns:
            tab[col] = 0
    tab = tab[["node", "way", "relation"]]
    # giữ thứ tự CLASSES (thứ tự này quyết định tên cột bảng lớp — poi_semantics)
    tab = tab.reindex([c for c in CLASSES if c in tab.index])
    tab["total"] = tab.sum(axis=1)
    tab["poly_ub_%"] = (100 * (tab["way"] + tab["relation"]) / tab["total"]).round(1)
    tab["verdict"] = [_verdict(cls, pct) for cls, pct in zip(tab.index, tab["poly_ub_%"])]

    print(tab.to_string())
    tot = tab[["node", "way", "relation", "total"]].sum()
    print(f"\n{'TOTAL':<16}{tot['node']:>7}{tot['way']:>7}{tot['relation']:>10}"
          f"{tot['total']:>8}"
          f"{100 * (tot['way'] + tot['relation']) / tot['total']:>10.1f}")
    print("\npoly_ub_% = CHẶN TRÊN của polygon coverage, KHÔNG phải giá trị kỳ vọng.")
    print("Raw Overpass dùng `out center tags` ⇒ chưa có hình học nào được lưu.")
    return tab


def _verdict(cls, pct):
    if cls in LINEAR_CLASSES:
        return "KHÔNG (way tuyến tính)"
    if pct < POLYGON_WORTH_PCT:
        return "không đáng"
    return "đáng"


def report_primary(poi):
    """Khử trùng node↔way: nhóm `poi_physical_id` chứa CẢ node lẫn way."""
    _rule("3. KHỬ TRÙNG — poi_physical_id chứa cả node VÀ way/relation")
    g = poi.groupby("poi_physical_id")["osm_type"].agg(
        n="size", kinds=lambda s: frozenset(s))
    mixed = g[g["kinds"].map(lambda k: "node" in k and len(k) > 1)]
    print(f"tổng nhóm poi_physical_id : {len(g):>7}")
    print(f"nhóm >1 thành viên        : {(g['n'] > 1).sum():>7}")
    print(f"nhóm có CẢ node và way/rel: {len(mixed):>7}   ← node bị way nuốt (E-DQ7c)")

    nonprim = poi[~poi["is_poi_primary"]]
    print(f"\nis_poi_primary=False      : {len(nonprim):>7} / {len(poi)} dòng")
    if len(nonprim):
        print("  phân bố theo lớp:")
        for cls, n in nonprim["poi_class"].value_counts().items():
            print(f"    {cls:<16}{n:>5}")
    print("\n⇒ legend PHẢI lọc is_poi_primary=True, nếu không sẽ vẽ chồng node và")
    print("  way của cùng một địa điểm vật lý.")


def report_complex(poi):
    """(4) Phân bố kích thước nhóm `complex_id` (cụm chung cư, gộp 150 m)."""
    _rule("4. PHÂN BỐ KÍCH THƯỚC NHÓM complex_id")
    has = poi[poi["complex_id"].notna()]
    print(f"dòng có complex_id: {len(has)} / {len(poi)}")
    if has.empty:
        print("(không có — complex_id chỉ gán cho APARTMENT)")
        return
    print("phân bố theo lớp:")
    for cls, n in has["poi_class"].value_counts().items():
        print(f"  {cls:<16}{n:>5}")

    sizes = has.groupby("complex_id").size()
    print(f"\nsố cụm: {len(sizes)}   ·   toà/cụm: "
          f"trung vị {sizes.median():.0f}, max {sizes.max()}")
    print("\n kích thước cụm │ số cụm │ số toà")
    print(" ───────────────┼────────┼────────")
    for lo, hi, label in ((1, 1, "1 (đơn lẻ)"), (2, 4, "2–4"),
                          (5, 9, "5–9"), (10, 10**9, "≥10")):
        sel = sizes[(sizes >= lo) & (sizes <= hi)]
        print(f" {label:>14} │ {len(sel):>6} │ {sel.sum():>6}")
    big = sizes[sizes >= 5].sum()
    print(f"\n⇒ {100 * big / sizes.sum():.1f}% số toà nằm trong cụm ≥5 (C6, poi_semantics).")
    print("  Vẽ theo TOÀ sẽ đếm một khu 5–10 lần; map nên gộp hoặc đổi màu theo cụm.")


def report_bounds(df, poi, aoi):
    """(5) Bounds thực tế vs bbox AOI, và vi phạm in_vn. Trả về số vi phạm."""
    _rule("5. BOUNDS vs BBOX AOI · VI PHẠM in_vn")
    s, w, n, e = aoi.bbox()
    print(f"AOI              : {aoi}")
    print(f"bbox AOI         : lat [{s:.5f}, {n:.5f}]  lng [{w:.5f}, {e:.5f}]")
    print(f"bounds POI trong AOI: lat [{poi['lat'].min():.5f}, {poi['lat'].max():.5f}]"
          f"  lng [{poi['lng'].min():.5f}, {poi['lng'].max():.5f}]")
    print(f"\ndòng trong AOI (hình tròn): {len(poi):>7} / {len(df)} toàn quốc")

    in_bbox = ((df["lat"] >= s) & (df["lat"] <= n)
               & (df["lng"] >= w) & (df["lng"] <= e))
    print(f"dòng trong bbox AOI       : {int(in_bbox.sum()):>7}"
          f"   ← bbox là bao trên của hình tròn")
    print(f"chênh bbox − tròn         : {int(in_bbox.sum()) - len(poi):>7}"
          f"   (góc bbox, ĐÃ loại khỏi audit)")

    # `osm_poi_points` là fail-closed (E-DQ7a/E-DQ11): chỉ chứa in_vn=True.
    # Đây là cổng REGRESSION, không phải phép khám phá — kỳ vọng luôn là 0.
    bad_vn = int((~df["in_vn"]).sum())
    print(f"\nin_vn=False (toàn file)   : {bad_vn:>7}   (fail-closed ⇒ phải là 0)")

    null_geom = int(poi[["lat", "lng"]].isna().any(axis=1).sum())
    null_cls = int(poi["poi_class"].isna().sum())
    unknown = sorted(set(poi["poi_class"].dropna()) - set(CLASSES))
    print(f"lat/lng NULL trong AOI    : {null_geom:>7}")
    print(f"poi_class NULL trong AOI  : {null_cls:>7}")
    print(f"poi_class lạ (ngoài CLASSES): {unknown if unknown else 'không'}")

    return bad_vn + null_geom + null_cls + len(unknown)


def _scan_pbf(way_ids, rel_ids, aoi):
    """MỘT lượt quét .pbf làm hai việc (xem docstring module về `out center tags`).

    (a) `way_ids` đã biết (từ POI parquet) -> đóng / mở / không tìm thấy.
        Phân biệt ĐÓNG vs MỞ mới là phép đo thật: way tuyến tính (PARKING_STREET)
        vẫn "resolve được id" nhưng **không** dựng được polygon.
    (b) đếm nền `CANDIDATE_CLASSES` trong AOI — hai class này chưa có trong parquet.

    Không dùng `IdFilter` như `vn_boundary._read_way_geoms`: việc (b) không biết trước
    id nên phải quét toàn file; gộp hai việc vào một lượt rẻ hơn hai lượt có filter.
    """
    import osmium

    print(f"quét {PBF_PATH.name} ({PBF_PATH.stat().st_size / 1e6:.0f} MB) — vài phút…")

    def _cls(tags):
        for cls, pairs in CANDIDATE_CLASSES.items():
            if any(tags.get(k) == v for k, v in pairs):
                return cls
        return None

    class _H(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.closed, self.open = set(), set()
            self.cand = collections.Counter()
            self.cand_ids = collections.defaultdict(set)  # khử trùng hospital OR

        def node(self, n):
            cls = _cls(n.tags)
            if cls and n.location.valid() and aoi.contains(n.location.lat,
                                                           n.location.lon):
                if ("node", n.id) not in self.cand_ids[cls]:
                    self.cand_ids[cls].add(("node", n.id))
                    self.cand[(cls, "node")] += 1

        def way(self, w):
            if w.id in way_ids:
                (self.closed if w.is_closed() else self.open).add(w.id)
            cls = _cls(w.tags)
            if not cls:
                return
            try:
                lat, lng = w.nodes[0].lat, w.nodes[0].lon
            except (IndexError, osmium.InvalidLocationError, RuntimeError):
                return
            if aoi.contains(lat, lng) and ("way", w.id) not in self.cand_ids[cls]:
                self.cand_ids[cls].add(("way", w.id))
                self.cand[(cls, "closed_way" if w.is_closed() else "open_way")] += 1

    h = _H()
    h.apply_file(str(PBF_PATH), locations=True)

    # lượt phụ (rẻ): relation POI -> có phải multipolygon ráp được không
    rel_kind = {}
    for rel in osmium.FileProcessor(str(PBF_PATH), osmium.osm.RELATION):
        if rel.id in rel_ids:
            rel_kind[rel.id] = rel.tags.get("type") or "(không có type)"
    return h.closed, h.open, h.cand, rel_kind


def report_pbf(poi, aoi):
    """(7) Polygon coverage KỲ VỌNG — hệ số thứ hai, đo từ .pbf đã freeze."""
    _rule("6. POLYGON COVERAGE KỲ VỌNG (đo từ .pbf 21/07 đã freeze)")
    if not PBF_PATH.exists():
        print(f"thiếu {PBF_PATH} — bỏ qua"); return

    ways = poi[poi["osm_type"] == "way"]
    rels = poi[poi["osm_type"] == "relation"]
    closed, open_, cand, rel_kind = _scan_pbf(
        set(ways["osm_id"].astype(int)), set(rels["osm_id"].astype(int)), aoi)

    missing = set(ways["osm_id"].astype(int)) - closed - open_
    print(f"\nway POI trong AOI      : {len(ways)}")
    print(f"  đóng (dựng polygon)  : {len(closed)}")
    print(f"  mở   (chỉ ra line)   : {len(open_)}")
    print(f"  KHÔNG thấy id trong pbf: {len(missing)}"
          f"  ({100 * len(missing) / max(len(ways), 1):.1f}%)")
    print("  ↑ lệch Overpass(live 21/07) vs Geofabrik(extract 21/07). Lớn ⇒ hai nguồn"
          "\n    KHÔNG cùng snapshot và giả định của Phase 2 sai.")
    mp = sum(1 for k in rel_kind.values() if k == "multipolygon")
    print(f"\nrelation POI trong AOI : {len(rels)}  ·  type=multipolygon: {mp}"
          f"  ·  không thấy: {len(rels) - len(rel_kind)}")

    ok = closed | {r for r, k in rel_kind.items() if k == "multipolygon"}
    rows = []
    for cls in CLASSES:
        sub = poi[poi["poi_class"] == cls]
        if sub.empty:
            continue
        n_ok = int(sub["osm_id"].astype(int).isin(ok).sum())
        ub = 100 * sub["osm_type"].isin(["way", "relation"]).sum() / len(sub)
        rows.append((cls, len(sub), round(ub, 1), n_ok,
                     round(100 * n_ok / len(sub), 1)))
    out = pd.DataFrame(rows, columns=["poi_class", "total", "poly_ub_%",
                                      "poly_ok", "poly_EXP_%"]).set_index("poi_class")
    out["hụt"] = (out["poly_ub_%"] - out["poly_EXP_%"]).round(1)
    print("\n" + out.to_string())
    print("\npoly_EXP_% = con số dùng được. Cột `hụt` = way tồn tại nhưng KHÔNG đóng")
    print("             (+ id không tìm thấy) — PARKING_STREET phải hụt nhiều nhất.")

    _rule("7. NỀN CLASS ỨNG VIÊN trong AOI (chưa có trong parquet)")
    print(f"{'class':<12}{'node':>7}{'way đóng':>10}{'way mở':>9}{'tổng':>7}{'EXP %':>8}")
    for cls in CANDIDATE_CLASSES:
        n, cw, ow = (cand[(cls, k)] for k in ("node", "closed_way", "open_way"))
        tot = n + cw + ow
        pct = 100 * cw / tot if tot else 0.0
        print(f"{cls:<12}{n:>7}{cw:>10}{ow:>9}{tot:>7}{pct:>7.1f}%")
    print("\nSo trực tiếp với cột poly_EXP_% ở mục 7 để xếp hạng class mới lẫn cũ.")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Kiểm kê osm_poi_points trong AOI (chỉ in stdout, không ghi file).")
    add_aoi_args(ap)
    ap.add_argument("--check", action="store_true",
                    help="exit 1 nếu có vi phạm bất biến (in_vn / NULL / lớp lạ)")
    ap.add_argument("--pbf", action="store_true",
                    help="đo polygon coverage KỲ VỌNG từ .pbf (quét toàn file, vài phút)")
    args = ap.parse_args(argv)

    aoi = aoi_from_args(args)
    df, poi = _load(aoi)
    if poi.empty:
        raise SystemExit(f"không có POI nào trong {aoi}")

    print(f"\n{'═' * 78}\nAUDIT osm_poi_points — {aoi}\nnguồn: {POI_POINTS}\n{'═' * 78}")
    report_class_by_type(poi)
    report_primary(poi)
    report_complex(poi)
    violations = report_bounds(df, poi, aoi)
    if args.pbf:
        report_pbf(poi, aoi)

    _rule("KẾT LUẬN")
    if violations:
        print(f"✗ {violations} vi phạm bất biến — xem mục 5.")
    else:
        print("✓ 0 vi phạm bất biến.")
    if args.check:
        return 1 if violations else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
