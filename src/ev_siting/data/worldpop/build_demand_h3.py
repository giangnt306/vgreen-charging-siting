#!/usr/bin/env python3
"""build_demand_h3.py — Ghép pop (WorldPop) + thành phần OSM -> bảng `demand_h3`.

Đầu vào:
  - data/interim/worldpop/worldpop_pop_h3.parquet         (h3_r8, pop)
  - data/interim/osm/osm_demand_components_h3.parquet     (h3_r8, n_poi, n_parking,
                                                           n_fuel, road_len_m, road_len_mt_m)
  - data/interim/osm/vn_boundary.parquet                  (polygon lãnh thổ — E-DQ7a)

Đầu ra:
  - data/interim/demand/demand_h3.parquet  — **lưới mô hình** (INSIDE + BORDER):
    h3_r8, pop, road_len_m, road_len_mt_m, n_poi, n_parking, n_fuel,
    cell_state, frac_in_vn. Cột admin (admin_l1_code, province_name, commune_*)
    enrich sau (E-DQ3); `demand_weight` chốt ở Sprint 2.
  - data/interim/demand/demand_h3_clipped_out.parquet — ô OUTSIDE (cách ly, để đối soát)
  - data/interim/demand/demand_h3_report.json         — cổng QA + đối soát

Full outer join theo h3_r8: ô có dân nhưng không đường vẫn giữ (và ngược lại).

**E-DQ7a — clip lãnh thổ ở mức Ô.** POI đã clip ở mức điểm tại `build_osm_h3.py`;
`pop` và `road_len` thì chỉ có ở mức ô nên phải phân loại ô. Test là **giao lục giác ∩
polygon**, KHÔNG phải tâm-ô-trong-polygon: ô res 8 có bán kính nội tiếp 0,49 km nên ô
vắt biên rơi tâm về bên nào cũng được — đo thực tế, test theo tâm ô xoá mất 74.642 dân
VN thật, test theo giao lục giác chỉ xoá 6.472 (0,0065%). Ô vắt biên (`BORDER`) được
GIỮ kèm `frac_in_vn` để bước `demand_weight` tự quyết chính sách chia tỉ lệ.

Lưu ý `road_len`: dump Geofabrik **không** cắt đúng biên giới (cắt bằng polygon có đệm)
→ 8.934 km đường nằm ngoài VN, 96% trong vòng 10 km quanh biên. Ghi chú "Geofabrik đã
clip theo quốc gia" ở tài liệu cũ là sai — clip ở đây xử lý cả road, không chỉ POI.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.worldpop.build_demand_h3
"""
import json
import sys

import pandas as pd

from ev_siting.data.osm.paths import DEMAND_COMPONENTS
from ev_siting.data.osm.vn_boundary import classify_cells
from ev_siting.data.provenance.manifest import load_manifest
from .paths import (DEMAND_H3, DEMAND_H3_CLIPPED, DEMAND_REPORT, POP_H3,
                    ensure_dirs)

_NUM_COLS = ["pop", "road_len_m", "road_len_mt_m"]
_INT_COLS = ["n_poi", "n_parking", "n_fuel"]
_ALL_COLS = ["h3_r8"] + _NUM_COLS + _INT_COLS + ["cell_state", "frac_in_vn"]


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def _totals(df):
    return {"cells": int(len(df)), "pop": float(df["pop"].sum()),
            "road_len_m": float(df["road_len_m"].sum()),
            **{c: int(df[c].sum()) for c in _INT_COLS}}


def qa_gates(report, full, keep, drop):
    """Cổng QA đầu tiên của `demand_h3` — bảng duy nhất chưa từng có validator dù nó
    chính là hàm mục tiêu (xem data-layer/overview.md §7)."""
    all_ok = True
    t_full, t_keep, t_drop = _totals(full), _totals(keep), _totals(drop)

    # ① đối soát: input = output + clipped (nguyên tắc chung của mọi bước E-DQ)
    recon = {k: round(t_full[k] - t_keep[k] - t_drop[k], 6) for k in t_full}
    all_ok &= _check(report, "reconcile_input_eq_output_plus_clipped",
                     all(abs(v) < 1e-6 for v in recon.values()), json.dumps(recon))

    # ② khoá chính duy nhất
    dup = int(keep["h3_r8"].duplicated().sum())
    all_ok &= _check(report, "demand_unique_h3", dup == 0, f"{dup} trùng")

    # ③ không âm
    cols = _NUM_COLS + _INT_COLS
    all_ok &= _check(report, "demand_non_negative", bool((keep[cols] >= 0).all().all()))

    # ④ mt_m <= m (trục lớn là tập con của toàn mạng)
    all_ok &= _check(report, "road_mt_le_total",
                     bool((keep["road_len_mt_m"] <= keep["road_len_m"] + 1e-6).all()))

    # ⑤ clip không được ăn vào dân số: ô OUTSIDE phải gần như không có dân
    #    (nếu vượt ngưỡng => polygon sai hoặc dùng nhầm test tâm-ô)
    pop_lost = t_drop["pop"] / max(t_full["pop"], 1)
    all_ok &= _check(report, "clip_pop_loss_negligible", pop_lost < 1e-3,
                     f"{t_drop['pop']:,.0f} dân bị clip ({pop_lost:.4%})")

    # ⑥ lưới giữ lại không còn ô OUTSIDE
    all_ok &= _check(report, "no_outside_cell_in_grid",
                     not (keep["cell_state"] == "OUTSIDE").any())
    return all_ok


def run():
    ensure_dirs()
    if not POP_H3.exists():
        raise SystemExit(f"thiếu {POP_H3} — chạy worldpop_pop.py trước")
    if not DEMAND_COMPONENTS.exists():
        raise SystemExit(f"thiếu {DEMAND_COMPONENTS} — chạy osm.build_osm_h3 trước")

    pop = pd.read_parquet(POP_H3)
    osm = pd.read_parquet(DEMAND_COMPONENTS)
    df = pop.merge(osm, on="h3_r8", how="outer")

    for c in _NUM_COLS:
        df[c] = df.get(c, 0.0).fillna(0.0)
    for c in _INT_COLS:
        df[c] = df.get(c, 0).fillna(0).astype(int)

    print(f"[demand_h3] phân loại {len(df)} ô theo lãnh thổ VN (E-DQ7a)...")
    df = df.merge(classify_cells(df["h3_r8"].tolist()), on="h3_r8", how="left")
    df = df[_ALL_COLS].sort_values("pop", ascending=False).reset_index(drop=True)

    outside = df["cell_state"] == "OUTSIDE"
    keep, drop = df[~outside].reset_index(drop=True), df[outside].reset_index(drop=True)
    keep.to_parquet(DEMAND_H3, index=False)
    drop.to_parquet(DEMAND_H3_CLIPPED, index=False)

    by_state = df["cell_state"].value_counts().to_dict()
    print(f"[demand_h3] -> {DEMAND_H3}  ({len(keep)} ô mô hình)")
    print(f"[demand_h3] -> {DEMAND_H3_CLIPPED}  ({len(drop)} ô ngoài VN, cách ly)")
    print("  theo trạng thái ô:", by_state)
    print("  tổng (lưới giữ lại):", {
        "pop_M": round(keep["pop"].sum() / 1e6, 3),
        "n_poi": int(keep.n_poi.sum()), "n_parking": int(keep.n_parking.sum()),
        "n_fuel": int(keep.n_fuel.sum()),
        "road_km": round(keep.road_len_m.sum() / 1e3),
        "road_mt_km": round(keep.road_len_mt_m.sum() / 1e3),
    })
    print("  đã clip:", {
        "cells": len(drop), "pop": round(drop["pop"].sum()),
        "road_km": round(drop.road_len_m.sum() / 1e3),
    })
    border = keep[keep.cell_state == "BORDER"]
    print(f"  ô vắt biên: {len(border)} (frac_in_vn trung vị "
          f"{border.frac_in_vn.median():.2f}; {int((border.frac_in_vn < 0.5).sum())} ô <0,5 "
          f"chứa {border.loc[border.frac_in_vn < 0.5, 'pop'].sum():,.0f} dân)")
    both = ((keep["pop"] > 0) & (keep.road_len_m > 0)).sum()
    print(f"  ô có cả dân & đường: {both} / {len(keep)}")

    report = {"snapshot_id": (load_manifest() or {}).get("snapshot_id"),
              "checks": [], "stats": {
                  "by_cell_state": by_state,
                  "grid": _totals(keep), "clipped": _totals(drop),
                  "border_cells": int(len(border)),
                  "border_cells_frac_lt_0_5": int((border.frac_in_vn < 0.5).sum()),
              }}
    print("\n[demand_h3] cổng QA:")
    ok = qa_gates(report, df, keep, drop)
    report["overall"] = "PASS" if ok else "FAIL"
    DEMAND_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print(f"\n[{report['overall']}] -> {DEMAND_REPORT}")
    if not ok:
        sys.exit(1)
    return keep


if __name__ == "__main__":
    run()
