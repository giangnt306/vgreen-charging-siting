#!/usr/bin/env python3
"""build_candidates.py — Sinh tập candidate site cho MCLP (P5, điểm chạm Giang→Kỳ).

Mô hình lai (xem docs/candidate-sites.md):
  - Candidate = **một điểm thực** (POI anchor / trạm hiện có), giữ toạ độ thật để
    explainability ("tại sao đặt ở đây").
  - Nhưng **tối đa 1 candidate / ô H3 res 8**: với R=3 km, R/d=3,07 nên hai điểm
    trong cùng ô phủ gần như y hệt tập ô demand -> nếu giữ nhiều sẽ gây MCLP bị
    *tie degenerate* (biến thể ẩn của P4). Coverage tính theo `h3_r8` của candidate.

Phân tầng anchor (ưu tiên khi gộp về 1/ô):
  T0 trạm hiện có (brownfield, is_existing=True)         <- canonical/stations
  T1 amenity=parking / amenity=fuel                       <- osm_poi_points (parking/fuel)
  T2 mall / retail / apartments (dwell dài, có bãi đỗ)    <- osm_poi_points (mall/retail/apartments)
  T4 gap-fill tổng hợp: ô demand cao, buildable, chưa có anchor -> centroid (SYNTHETIC)
  (T3 rest_area/nút giao QL cần road-class từ .pbf — để roadmap, xem docs)

Lọc: chỉ giữ anchor rơi vào ô `buildable=True` (buildable_h3, P5) và trong AOI;
loại anchor mang cờ toạ độ bẩn (DUP_COORD/COORD_ADDR_MISMATCH — §7 #1).

Output: data/processed/candidate_sites.parquet (+ .geojson cho Kỳ)
Chạy:
    PYTHONPATH=src python -m ev_siting.features.build_candidates --city hanoi
"""
import argparse
import json

import numpy as np
import pandas as pd

import h3

from ev_siting.aoi import add_aoi_args, aoi_from_args
from ev_siting.data.evcs.paths import STATIONS_DIR
from ev_siting.data.landuse.paths import BUILDABLE_H3
from ev_siting.data.osm.paths import POI_POINTS
from ev_siting.data.worldpop.paths import DEMAND_H3
from .paths import (CANDIDATE_GEOJSON, CANDIDATE_SITES, CAND_MAX, CAND_MIN_MULT,
                    COVERAGE_MIN, DEGEN_MIN, GAPFILL_TOP_Q, R_BASELINE_KM,
                    ensure_dirs)

# tier -> (anchor_type từ POI category), theo thứ tự ưu tiên tăng dần rank (0=tốt nhất)
_POI_TIER = {
    "parking": ("T1", "parking"),
    "fuel": ("T1", "fuel"),
    "mall": ("T2", "mall"),
    "retail": ("T2", "retail"),
    "apartments": ("T2", "apartments"),
}
_TIER_RANK = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4}

# cờ toạ độ bẩn -> loại anchor T0 (§7 #1)
_DIRTY_COORD_FLAGS = {"DUP_COORD", "COORD_ADDR_MISMATCH"}


def _in_aoi(aoi, df):
    """Mask boolean vector hoá: dòng nào có (lat,lng) trong AOI."""
    return np.asarray(aoi.contains(df["lat"].to_numpy(), df["lng"].to_numpy()))


def _load_stations(aoi):
    """T0: trạm hiện có trong AOI (is_existing=True).

    P8 — chỉ nhận trạm **đang vận hành & công khai** làm anchor brownfield: T0 là
    incumbent bị ràng buộc **bắt buộc mở** (CapEx=0) nên không được ép mở trạm đã
    ngừng (`is_operational=False`) hay trạm tư nhân (`access=RESTRICTED`). Giữ
    UNKNOWN (không loại ngầm — §8 bước 6)."""
    cols = ["station_id", "lat", "lng", "h3_r8", "quality_flags", "operator",
            "is_operational", "access", "is_primary"]
    df = pd.read_parquet(STATIONS_DIR, columns=cols)
    df = df[_in_aoi(aoi, df)].copy()
    # P8: loại trạm đã ngừng vận hành / tư nhân khỏi anchor T0
    df = df[df["is_operational"] & (df["access"] != "RESTRICTED")]
    # E-DQ2: chỉ lấy dòng CHÍNH (is_primary) — bản trùng chéo nguồn cùng 1 tram vật
    # lý không được thành 2 incumbent "bắt buộc mở" (CapEx=0) / phủ trùng 2 lần.
    df = df[df["is_primary"]]
    # loại toạ độ bẩn
    def _dirty(fl):
        return bool(_DIRTY_COORD_FLAGS & set(fl)) if fl is not None else False
    df = df[~df["quality_flags"].apply(_dirty)]
    df["tier"] = "T0"
    df["anchor_type"] = "existing_station"
    df["source_ref"] = df["station_id"]
    df["is_existing"] = True
    return df[["lat", "lng", "h3_r8", "tier", "anchor_type", "source_ref", "is_existing"]]


def _load_poi(aoi):
    """T1/T2: POI anchor trong AOI."""
    df = pd.read_parquet(POI_POINTS, columns=["osm_type", "osm_id", "category", "lat", "lng", "h3_r8"])
    df = df[df["category"].isin(_POI_TIER)].copy()
    df = df[_in_aoi(aoi, df)].copy()
    df["tier"] = df["category"].map(lambda c: _POI_TIER[c][0])
    df["anchor_type"] = df["category"].map(lambda c: _POI_TIER[c][1])
    df["source_ref"] = df["osm_type"].astype(str) + "/" + df["osm_id"].astype(str)
    df["is_existing"] = False
    return df[["lat", "lng", "h3_r8", "tier", "anchor_type", "source_ref", "is_existing"]]


def _gapfill(aoi, buildable, occupied_cells, gapfill_q=GAPFILL_TOP_Q):
    """T4: ô demand cao, buildable, chưa có anchor -> centroid (SYNTHETIC)."""
    empty = pd.DataFrame(columns=["lat", "lng", "h3_r8", "tier", "anchor_type",
                                  "source_ref", "is_existing"])
    dem = pd.read_parquet(DEMAND_H3)[["h3_r8", "pop", "n_poi", "road_len_mt_m"]]
    b = buildable[buildable["buildable"]][["h3_r8"]]
    cand = b.merge(dem, on="h3_r8", how="left").fillna(0.0)
    cand = cand[~cand["h3_r8"].isin(occupied_cells)]
    if cand.empty:
        return empty
    # CLIP VỀ AOI (như anchor T0/T1/T2): `buildable_h3` có thể là bảng QUỐC GIA
    # (lookup dùng chung cho mọi city — xem E-DQ9). Nếu không clip, city run sẽ hút
    # cell toàn quốc và quantile tính trên phân bố quốc gia -> T4 nổ (size_ceiling).
    # NationalAOI.contains == toàn bbox VN nên với --national đây là no-op.
    latlng = cand["h3_r8"].map(lambda c: h3.cell_to_latlng(c))
    cand["lat"] = latlng.map(lambda x: x[0])
    cand["lng"] = latlng.map(lambda x: x[1])
    cand = cand[_in_aoi(aoi, cand)].copy()
    if cand.empty:
        return empty
    # điểm demand thô để chọn ô đáng gap-fill (pop chủ đạo + đường trục + POI).
    # Quantile tính SAU khi clip -> ngưỡng thích ứng theo demand nội vùng AOI.
    score = cand["pop"] + 50 * cand["n_poi"] + 0.05 * cand["road_len_mt_m"]
    thr = score.quantile(gapfill_q)
    pick = cand[score >= thr].copy()
    pick["tier"] = "T4"
    pick["anchor_type"] = "gapfill_synthetic"
    pick["source_ref"] = "synthetic:" + pick["h3_r8"]
    pick["is_existing"] = False
    return pick[["lat", "lng", "h3_r8", "tier", "anchor_type", "source_ref", "is_existing"]]


def _dedup_one_per_cell(df):
    """Gộp về <=1 candidate/ô H3: giữ anchor tier tốt nhất (rank nhỏ nhất)."""
    df = df.copy()
    df["rank"] = df["tier"].map(_TIER_RANK)
    df = df.sort_values(["h3_r8", "rank"]).drop_duplicates("h3_r8", keep="first")
    return df.drop(columns="rank").reset_index(drop=True)


def _coverage_cells(center_cell, R_km):
    """Tập ô H3 có tâm nằm trong bán kính R_km quanh `center_cell`."""
    k = int(np.ceil(R_km / 0.98)) + 1
    disk = list(h3.grid_disk(center_cell, k))
    c_lat, c_lng = h3.cell_to_latlng(center_cell)
    from ev_siting.aoi import haversine_km
    ll = np.array([h3.cell_to_latlng(c) for c in disk])
    keep = haversine_km(c_lat, c_lng, ll[:, 0], ll[:, 1]) <= R_km
    return frozenset(c for c, ok in zip(disk, keep) if ok)


def _qa_gate(cand, aoi, R_km, p_hint, max_candidates=CAND_MAX):
    """5 cổng chặn P5. Trả về (all_ok, report_dict)."""
    dem = pd.read_parquet(DEMAND_H3)[["h3_r8", "pop"]].copy()
    # demand trong lõi AOI (đo coverage ở lõi, không tính buffer) — vector hoá
    dll = np.array([h3.cell_to_latlng(c) for c in dem["h3_r8"]])
    in_core = np.asarray(aoi.in_core(dll[:, 0], dll[:, 1]))
    dem_core = dem[in_core].set_index("h3_r8")["pop"]
    total_demand = float(dem_core.sum())

    checks, all_ok = [], True

    # coverage_cells theo từng candidate (cache)
    cov_sets = {r.h3_r8: _coverage_cells(r.h3_r8, R_km) for r in cand.itertuples()}

    # Gate 1: upper-bound coverage — union toàn bộ candidate
    covered = set().union(*cov_sets.values()) if cov_sets else set()
    cov_pop = float(dem_core[dem_core.index.isin(covered)].sum())
    ub = cov_pop / total_demand if total_demand else 0.0
    ok = ub >= COVERAGE_MIN
    all_ok &= ok
    checks.append({"gate": "upper_bound_coverage", "status": "PASS" if ok else "FAIL",
                   "value": round(ub, 4), "threshold": COVERAGE_MIN,
                   "detail": "union coverage của mọi candidate trên demand lõi AOI"})

    # Gate 2: tỷ lệ tự do |candidates| >= mult × p
    need = CAND_MIN_MULT * p_hint
    ok = len(cand) >= need
    all_ok &= ok
    checks.append({"gate": "freedom_ratio", "status": "PASS" if ok else "FAIL",
                   "value": len(cand), "threshold": need,
                   "detail": f"|candidates| >= {CAND_MIN_MULT}×p (p_hint={p_hint})"})

    # Gate 3: trần kích thước
    ok = len(cand) <= max_candidates
    all_ok &= ok
    checks.append({"gate": "size_ceiling", "status": "PASS" if ok else "FAIL",
                   "value": len(cand), "threshold": max_candidates,
                   "detail": "giữ MCLP giải được trong thời gian hợp lý"})

    # Gate 4: anti-degenerate — tỷ lệ tập-phủ DUY NHẤT / candidate (biến thể ẩn P4)
    uniq = len(set(cov_sets.values()))
    ratio = uniq / len(cand) if len(cand) else 0.0
    ok = ratio >= DEGEN_MIN
    all_ok &= ok
    checks.append({"gate": "anti_degenerate", "status": "PASS" if ok else "FAIL",
                   "value": round(ratio, 4), "threshold": DEGEN_MIN,
                   "detail": "unique(coverage_set)/|candidates| — thấp = nghiệm suy biến (P4)"})

    # gate lưới↔bán kính (P4) — nhắc lại ở đây cho khép kín
    ok = R_km > 0.98
    all_ok &= ok
    checks.append({"gate": "grid_radius", "status": "PASS" if ok else "FAIL",
                   "value": R_km, "threshold": 0.98,
                   "detail": "R > d(res8) — nếu không MCLP suy biến thành sort top-p (P4)"})

    return all_ok, {"R_km": R_km, "p_hint": p_hint, "n_candidates": len(cand),
                    "total_demand_core": round(total_demand), "checks": checks}


def build(aoi, R_km=R_BASELINE_KM, p_hint=20, strict=True,
          max_candidates=CAND_MAX, gapfill_q=GAPFILL_TOP_Q):
    ensure_dirs()
    print(f"[cand] {aoi}  R={R_km}km  p_hint={p_hint}  max={max_candidates}  gapfill_q={gapfill_q}")
    if not BUILDABLE_H3.exists():
        raise SystemExit(f"thiếu {BUILDABLE_H3} — chạy landuse.build_buildable_h3 trước")
    buildable = pd.read_parquet(BUILDABLE_H3)
    ok_cells = set(buildable.loc[buildable["buildable"], "h3_r8"])

    t0 = _load_stations(aoi)
    poi = _load_poi(aoi)
    print(f"[cand] anchor thô: T0={len(t0)} trạm · T1/T2={len(poi)} POI")

    real = pd.concat([t0, poi], ignore_index=True)
    # giữ anchor trong ô buildable (T0 trạm hiện có luôn giữ — brownfield, đã có điện)
    real = real[(real["tier"] == "T0") | (real["h3_r8"].isin(ok_cells))].copy()

    # gộp về <=1/ô trước, để gap-fill biết ô nào đã có anchor
    real = _dedup_one_per_cell(real)
    occupied = set(real["h3_r8"])

    gap = _gapfill(aoi, buildable, occupied, gapfill_q=gapfill_q)
    print(f"[cand] gap-fill T4: {len(gap)} ô demand cao chưa có anchor")

    cand = pd.concat([real, gap], ignore_index=True)
    cand = _dedup_one_per_cell(cand)

    # enrich cột bàn giao từ buildable_h3 (penalty, dist_substation, capex proxy)
    bcols = ["h3_r8", "penalty", "dist_substation_m", "built_up_frac"]
    cand = cand.merge(buildable[bcols], on="h3_r8", how="left")
    # T0 sát biên AOI có tâm ô ngoài lưới buildable -> không được chấm land-use.
    # Trạm hiện có đã có điện/mặt bằng -> penalty land-use = 0 (không phạt thêm).
    existing_na = cand["is_existing"] & cand["penalty"].isna()
    cand.loc[existing_na, "penalty"] = 0.0
    cand["province_code"] = None  # enrich khi có admin (§8 bước 8)
    cand["capex_class"] = np.where(
        cand["is_existing"], "low",
        np.where(cand["tier"] == "T4", "high",
                 np.where(cand["penalty"].fillna(0) >= 0.5, "high", "mid")))
    cand["exclusion_flags"] = [[] for _ in range(len(cand))]
    cand.insert(0, "candidate_id",
                [f"cand-{aoi.name}-{i:05d}" for i in range(len(cand))])

    # --- QA gate ---
    all_ok, report = _qa_gate(cand, aoi, R_km, p_hint, max_candidates=max_candidates)
    print(f"\n[cand] QA gate ({'PASS' if all_ok else 'FAIL'}):")
    for c in report["checks"]:
        print(f"  [{c['status']}] {c['gate']}: {c['value']} (ngưỡng {c['threshold']})")

    out_cols = ["candidate_id", "lat", "lng", "h3_r8", "province_code", "tier",
                "anchor_type", "source_ref", "is_existing", "built_up_frac",
                "dist_substation_m", "penalty", "capex_class", "exclusion_flags"]
    out = cand[out_cols]
    out.to_parquet(CANDIDATE_SITES, index=False)
    _write_geojson(out, report)
    with open(str(CANDIDATE_SITES).replace(".parquet", "_qa.json"), "w") as f:
        json.dump({"aoi": aoi.to_dict(), **report,
                   "overall": "PASS" if all_ok else "FAIL"}, f, ensure_ascii=False, indent=2)

    print(f"\n[cand] -> {CANDIDATE_SITES}  ({len(out)} candidate)")
    print("  theo tier:", out["tier"].value_counts().to_dict())
    print("  theo capex:", out["capex_class"].value_counts().to_dict())
    if not all_ok and strict:
        raise SystemExit("[cand] QA gate FAIL — xem *_qa.json (đừng bàn giao Kỳ khi FAIL)")
    return out


def _write_geojson(cand, report):
    """GeoJSON điểm candidate cho Kỳ (cùng chuẩn với demand proxy)."""
    feats = []
    for r in cand.itertuples():
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(r.lng, 6), round(r.lat, 6)]},
            "properties": {
                "candidate_id": r.candidate_id, "h3_r8": r.h3_r8, "tier": r.tier,
                "anchor_type": r.anchor_type, "is_existing": bool(r.is_existing),
                "capex_class": r.capex_class,
                "penalty": None if pd.isna(r.penalty) else round(float(r.penalty), 3),
            },
        })
    fc = {"type": "FeatureCollection",
          "properties": {"generated_for": "MCLP candidate sites (P5)", "qa": report},
          "features": feats}
    with open(CANDIDATE_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"[cand] -> {CANDIDATE_GEOJSON}  ({len(feats)} điểm)")


def run(args=None):
    ap = argparse.ArgumentParser(description="Sinh candidate sites cho MCLP (P5)")
    add_aoi_args(ap)  # gồm --radius-km = bán kính LÕI AOI (đo coverage) + --national
    ap.add_argument("--serve-radius-km", type=float, default=R_BASELINE_KM,
                    help=f"bán kính phục vụ R của MCLP để QA (mặc định {R_BASELINE_KM})")
    ap.add_argument("--p-hint", type=int, default=None,
                    help="số trạm dự kiến MCLP chọn (mặc định 20 city / 800 national)")
    ap.add_argument("--max-candidates", type=int, default=None,
                    help=f"trần kích thước gate (mặc định {CAND_MAX} city / 80000 national)")
    ap.add_argument("--gapfill-q", type=float, default=None,
                    help=f"quantile demand cho gap-fill T4 (mặc định {GAPFILL_TOP_Q} city / 0.98 national)")
    ap.add_argument("--no-strict", action="store_true",
                    help="không exit != 0 khi QA FAIL (chỉ cảnh báo)")
    a = ap.parse_args(args)
    national = getattr(a, "national", False)
    # defaults theo scope: national có nhiều anchor hơn -> nới trần + gap-fill chọn lọc hơn
    p_hint = a.p_hint if a.p_hint is not None else (800 if national else 20)
    max_cand = a.max_candidates if a.max_candidates is not None else (80000 if national else CAND_MAX)
    gapfill_q = a.gapfill_q if a.gapfill_q is not None else (0.98 if national else GAPFILL_TOP_Q)
    build(aoi_from_args(a), R_km=a.serve_radius_km, p_hint=p_hint,
          strict=not a.no_strict, max_candidates=max_cand, gapfill_q=gapfill_q)


if __name__ == "__main__":
    run()
