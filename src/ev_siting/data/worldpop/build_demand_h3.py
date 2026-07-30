#!/usr/bin/env python3
"""build_demand_h3.py — Ghép pop (WorldPop) + thành phần OSM -> bảng `demand_h3`.

Đầu vào:
  - data/interim/worldpop/worldpop_pop_h3.parquet         (h3_r8, pop)
  - data/interim/worldpop/worldpop_pop_2025_h3.parquet    (h3_r8, pop — R2024B 2025,
                                                           nguồn cột `pop_2025`)
  - data/interim/osm/osm_demand_components_h3.parquet     (h3_r8, n_* POI theo lớp tag
                                                           — E-DQ7c; road_* — E-DQ7b)
  - data/interim/osm/vn_boundary.parquet                  (polygon lãnh thổ — E-DQ7a)

Đầu ra:
  - data/interim/demand/demand_h3.parquet  — **lưới mô hình** (INSIDE + BORDER):
    h3_r8, pop, pop_2025, road_access_m, road_len_m, road_lane_mw_m, road_lane_ar_m,
    road_bridge_m, 10 cột POI theo lớp tag (E-DQ7c), cell_state, frac_in_vn. Cột admin
    (admin_l1_code, province_name, commune_*) enrich sau (E-DQ3); `demand_weight`
    chốt ở Sprint 2.
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

**E-DQ7c — `n_poi`/`n_parking` khai tử.** `n_poi` cộng toà chung cư với trung tâm
thương mại tỉ lệ 1:1 (84,8% số đếm ở top-100 ô là apartments) và `n_parking` gộp đỗ ven
đường với bãi đỗ, đếm cả `access=private`. Nay `demand_h3` mang **10 cột tách rời theo
lớp tag** để E-DQ7d/P1 fit trọng số bằng 18,6M bản ghi occupancy thay vì gán tay. Xem
`osm/poi_semantics.py`.

**E-DQ7b — hai cột đường, hai nhiệm vụ.** `road_access_m` (mọi đường lái xe được, GỒM
`service`+`track`) dùng cho **lối vào** (`buildable_h3`, E-DQ8); `road_len_m` (TRỪ
`service`+`track`) dùng cho **cầu**. `road_len_mt_m` đã khai tử → `road_lane_mw_m`
(lane-mét cao tốc) + `road_lane_ar_m` (lane-mét trunk/primary). Xem
`osm/road_semantics.py`.

**Q6iii — `pop_2025` là cột SENSITIVITY.** Mặt nạ 2020 gán pop=0 cho 60,3% số ô có
đường (audit 29/07, Giang đánh dấu P10); `pop_2025` (R2024B, mặt nạ công trình mới) giữ
SONG SONG để đo độ nhạy mặt nạ raster. Hợp đồng cột theo fillna(0) như mọi cột đo; neo
xếp hạng vẫn là `pop_adj`.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.worldpop.build_demand_h3
"""
import json
import sys

import pandas as pd

from ev_siting.data.osm.paths import DEMAND_COMPONENTS
from ev_siting.data.osm.poi_semantics import DERIVED_COLUMNS as POI_DERIVED
from ev_siting.data.osm.road_semantics import DERIVED_COLUMNS
from ev_siting.data.osm.access_tiers import DERIVED_COLUMNS as TIER_DERIVED
from ev_siting.data.osm.access_tiers import derive as derive_tiers
from ev_siting.data.osm.vn_boundary import classify_cells
from ev_siting.data.provenance.manifest import load_manifest
from .paths import (DEMAND_H3, DEMAND_H3_CLIPPED, DEMAND_REPORT, POP_ACC_H3,
                    POP_ADJ_H3, POP_H3, POP_H3_2025, ensure_dirs)

# `apartment_levels_sum` là Σ số tầng (số ĐO, có thể lẻ khi thiếu tag) -> cột số thực;
# mọi cột POI còn lại là số đếm nguyên. `pop_adj` (E-DQ7f + E-DQ8b) là pop ĐÃ đặt lại chỗ
# — dùng cho consumer XẾP HẠNG; `pop` giữ UN-anchored cho phát biểu tuyệt đối;
# `pop_2025` (Q6iii) là cột sensitivity của mặt nạ raster, KHÔNG dùng để xếp hạng.
#: cột số có SẴN ở đầu vào (pop + thành phần OSM) — được fillna(0) sau outer join.
_JOINED_NUM_COLS = ["pop", "pop_adj", "pop_2025"] + DERIVED_COLUMNS + ["apartment_levels_sum"]
#: cột số của bảng ra = cột join + 2 cột vành do E-DQ8a SUY RA sau (không fillna được
#: vì lúc đó chưa tồn tại — `access_tier` là chuỗi nên không nằm ở đây).
_NUM_COLS = _JOINED_NUM_COLS + [c for c in TIER_DERIVED if c != "access_tier"]
_INT_COLS = [c for c in POI_DERIVED if c != "apartment_levels_sum"]
_FLAG_COLS = ["pop_pixel_implausible"]          # E-DQ7f: cờ ô dồn cục (bool)
_ALL_COLS = (["h3_r8"] + _NUM_COLS + _INT_COLS + _FLAG_COLS
             + ["access_tier", "cell_state", "frac_in_vn"])


def _load_pop():
    """Nạp pop cho demand, theo thang ưu tiên **mới nhất thắng** (không bịa giá trị ở
    bậc nào):

      1. `worldpop_pop_acc_h3` (E-DQ8b) — pop_adj đã qua CẢ hai phép đặt lại chỗ;
      2. `worldpop_pop_adj_h3` (E-DQ7f) — chỉ sửa dồn cục, dân roadless còn nguyên chỗ;
      3. `worldpop_pop_h3`     (E-DQ7e) — pop_adj = pop, cờ = False.
    """
    if POP_ACC_H3.exists():
        p = pd.read_parquet(POP_ACC_H3)[["h3_r8", "pop", "pop_adj",
                                         "pop_pixel_implausible"]]
        print(f"[demand_h3] pop từ {POP_ACC_H3.name} (E-DQ7f + E-DQ8b)")
        return p
    if POP_ADJ_H3.exists():
        p = pd.read_parquet(POP_ADJ_H3)[["h3_r8", "pop", "pop_adj",
                                         "pop_pixel_implausible"]]
        print(f"[demand_h3] ⚠️ chưa có {POP_ACC_H3.name} (E-DQ8b) — pop từ "
              f"{POP_ADJ_H3.name}, dân ô roadless CHƯA được dời")
        return p
    p = pd.read_parquet(POP_H3)[["h3_r8", "pop"]]
    p["pop_adj"] = p["pop"]
    p["pop_pixel_implausible"] = False
    print(f"[demand_h3] ⚠️ chưa có {POP_ADJ_H3.name} (E-DQ7f) — pop_adj=pop, cờ=False")
    return p


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def _totals(df):
    return {"cells": int(len(df)),
            **{c: float(df[c].sum()) for c in _NUM_COLS},
            **{c: int(df[c].sum()) for c in _INT_COLS}}


def qa_gates(report, full, keep, drop):
    """Cổng QA đầu tiên của `demand_h3` — bảng duy nhất chưa từng có validator dù nó
    chính là hàm mục tiêu (xem data-layer/overview.md §7)."""
    all_ok = True
    t_full, t_keep, t_drop = _totals(full), _totals(keep), _totals(drop)

    # ① đối soát: input = output + clipped (nguyên tắc chung của mọi bước E-DQ)
    #    dung sai TƯƠNG ĐỐI: lane-mét toàn quốc ~1e8 nên sai số cộng dồn float vượt 1e-6
    recon = {k: t_full[k] - t_keep[k] - t_drop[k] for k in t_full}
    all_ok &= _check(report, "reconcile_input_eq_output_plus_clipped",
                     all(abs(v) <= 1e-9 * max(1.0, abs(t_full[k]))
                         for k, v in recon.items()),
                     json.dumps({k: round(v, 6) for k, v in recon.items()}))

    # ② khoá chính duy nhất
    dup = int(keep["h3_r8"].duplicated().sum())
    all_ok &= _check(report, "demand_unique_h3", dup == 0, f"{dup} trùng")

    # ③ không âm
    cols = _NUM_COLS + _INT_COLS
    all_ok &= _check(report, "demand_non_negative", bool((keep[cols] >= 0).all().all()))

    # ④ E-DQ7b: mạng sinh cầu ⊆ mạng lối vào; cầu/hầm ⊆ mạng lối vào
    all_ok &= _check(report, "road_len_le_access",
                     bool((keep["road_len_m"] <= keep["road_access_m"] + 1e-6).all()))
    all_ok &= _check(report, "road_bridge_le_access",
                     bool((keep["road_bridge_m"] <= keep["road_access_m"] + 1e-6).all()))

    # ⑤ clip không được ăn vào dân số: ô OUTSIDE phải gần như không có dân
    #    (nếu vượt ngưỡng => polygon sai hoặc dùng nhầm test tâm-ô)
    pop_lost = t_drop["pop"] / max(t_full["pop"], 1)
    all_ok &= _check(report, "clip_pop_loss_negligible", pop_lost < 1e-3,
                     f"{t_drop['pop']:,.0f} dân bị clip ({pop_lost:.4%})")

    # ⑥ lưới giữ lại không còn ô OUTSIDE
    all_ok &= _check(report, "no_outside_cell_in_grid",
                     not (keep["cell_state"] == "OUTSIDE").any())

    # ⑦ E-DQ8a — bậc lối vào phải nhất quán với cột đo: mọi ô `road_access_m > 0` là
    #    DIRECT, và mọi ô ISOLATED phải thật sự không có đường trong cả hai vành. Cổng
    #    này FAIL được (khác `road_mt_le_total` cũ vốn đúng theo xây dựng).
    bad_direct = int(((keep["road_access_m"] > 0)
                      & (keep["access_tier"] != "DIRECT")).sum())
    bad_iso = int(((keep["access_tier"] == "ISOLATED")
                   & ((keep["road_access_nb1_m"] > 0)
                      | (keep["road_access_nb2_m"] > 0))).sum())
    all_ok &= _check(report, "access_tier_consistent",
                     bad_direct == 0 and bad_iso == 0,
                     f"{bad_direct} ô có đường mà không DIRECT · "
                     f"{bad_iso} ô ISOLATED mà vành có đường")

    # ⑧ E-DQ8b — sau khi dời dân, `pop_adj` không được còn đọng ở ô ISOLATED. Ngưỡng
    #    WARN thay vì FAIL vì xã không có ô built-up nào để nhận thì 8b GIỮ TẠI CHỖ có
    #    nhãn (`UNREPAIRED_*`) — đó là đầu vào hợp lệ của E-DQ8c, không phải lỗi.
    iso_pop = float(keep.loc[keep["access_tier"] == "ISOLATED", "pop_adj"].sum())
    share = iso_pop / max(t_keep["pop_adj"], 1.0)
    _check(report, "no_pop_adj_left_isolated", share < 1e-4,
           f"{iso_pop:,.0f} người ({share:.4%}) còn ở ô ISOLATED "
           f"(chưa chạy E-DQ8b nếu ≈ 0,19%)", fatal=False)
    report["stats"]["access_tiers"] = {
        t: {"cells": int(len(x)), "pop": float(x["pop"].sum()),
            "pop_adj": float(x["pop_adj"].sum())}
        for t, x in keep.groupby("access_tier")}
    return all_ok


def run():
    ensure_dirs()
    if not POP_H3.exists():
        raise SystemExit(f"thiếu {POP_H3} — chạy worldpop_pop.py trước")
    if not POP_H3_2025.exists():
        raise SystemExit(f"thiếu {POP_H3_2025} — chạy worldpop_pop.py --vintage 2025 trước")
    if not DEMAND_COMPONENTS.exists():
        raise SystemExit(f"thiếu {DEMAND_COMPONENTS} — chạy osm.build_osm_h3 trước")

    pop = _load_pop()
    osm = pd.read_parquet(DEMAND_COMPONENTS)
    # artefact dựng trước E-DQ7b không có cột lối vào -> chặn (stale), không fill 0 ngầm
    missing = [c for c in DERIVED_COLUMNS if c not in osm.columns]
    if missing:
        raise SystemExit(f"{DEMAND_COMPONENTS.name} thiếu {missing} (bản trước E-DQ7b) "
                         f"— chạy lại `make osm`")
    # E-DQ7c: artefact trước bản vá có `n_poi`/`n_parking` và thiếu cột theo lớp tag
    missing = [c for c in POI_DERIVED if c not in osm.columns]
    if missing:
        raise SystemExit(f"{DEMAND_COMPONENTS.name} thiếu {missing} (bản trước E-DQ7c) "
                         f"— chạy lại `make osm`")
    df = pop.merge(osm, on="h3_r8", how="outer")
    # Q6iii: pop_2025 (R2024B) — outer để giữ cả ô CHỈ có ở mặt nạ 2025 (đúng nhóm ô mà
    # phép đo độ nhạy nhắm tới); ô ngoài VN sẽ bị clip ở bước E-DQ7a như mọi ô khác.
    p25 = pd.read_parquet(POP_H3_2025).rename(columns={"pop": "pop_2025"})
    df = df.merge(p25, on="h3_r8", how="outer")

    for c in _JOINED_NUM_COLS:
        df[c] = df.get(c, 0.0).fillna(0.0)
    for c in _INT_COLS:
        df[c] = df.get(c, 0).fillna(0).astype(int)
    # ô chỉ có ở phía OSM (không dân) -> không phải ô dồn cục
    for c in _FLAG_COLS:
        s = df[c] if c in df.columns else pd.Series(False, index=df.index)
        df[c] = s.where(s.notna(), False).astype(bool)

    # E-DQ8a — bậc lối vào tính ở thang LÂN CẬN. Phải tính TRƯỚC khi clip lãnh thổ: ô
    # bên kia biên vẫn là láng giềng có đường thật, bỏ nó ra sẽ báo ISOLATED giả cho ô
    # vắt biên (cùng cái bẫy "tâm-ô-trong-polygon" mà E-DQ7a đã gỡ).
    print(f"[demand_h3] E-DQ8a: bậc lối vào theo vành 1/2 trên {len(df)} ô...")
    df = derive_tiers(df)

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
        "pop_2025_M": round(keep["pop_2025"].sum() / 1e6, 3),
        **{c: int(keep[c].sum()) for c in _INT_COLS},
        "apartment_levels_sum": int(keep.apartment_levels_sum.sum()),
        "road_access_km": round(keep.road_access_m.sum() / 1e3),
        "road_km": round(keep.road_len_m.sum() / 1e3),
        "lane_mw_km": round(keep.road_lane_mw_m.sum() / 1e3),
        "lane_ar_km": round(keep.road_lane_ar_m.sum() / 1e3),
        "bridge_km": round(keep.road_bridge_m.sum() / 1e3),
    })
    print("  đã clip:", {
        "cells": len(drop), "pop": round(drop["pop"].sum()),
        "road_access_km": round(drop.road_access_m.sum() / 1e3),
    })
    border = keep[keep.cell_state == "BORDER"]
    print(f"  ô vắt biên: {len(border)} (frac_in_vn trung vị "
          f"{border.frac_in_vn.median():.2f}; {int((border.frac_in_vn < 0.5).sum())} ô <0,5 "
          f"chứa {border.loc[border.frac_in_vn < 0.5, 'pop'].sum():,.0f} dân)")
    both = ((keep["pop"] > 0) & (keep.road_access_m > 0)).sum()
    print(f"  ô có cả dân & đường: {both} / {len(keep)}")
    # E-DQ7b: ô chỉ có service/track — GIỮ là "có lối vào", nhưng là tín hiệu mềm
    informal = (keep.road_access_m > 0) & (keep.road_len_m <= 0)
    print(f"  lối vào phi chính thức (chỉ service/track): {int(informal.sum()):,} ô, "
          f"{keep.loc[informal, 'pop'].sum():,.0f} dân "
          f"({int((informal & (keep['pop'] > 0)).sum()):,} ô có dân)")
    # E-DQ8 — tách theo BẬC lối vào (E-DQ8a). Con số "6.350 ô / 1,24M dân" của register
    # là tổng của ba thứ khác nhau: ADJACENT (đường ở ô kề — lỗi THANG ĐO, 72%), NEAR, và
    # ISOLATED (cô lập thật). Chỉ ISOLATED là ứng viên loại cứng.
    roadless = keep["road_access_m"] <= 0
    print(f"  E-DQ8 (pop>0 & không lối vào TRONG ô): "
          f"{int((roadless & (keep['pop'] > 0)).sum()):,} ô, "
          f"{keep.loc[roadless & (keep['pop'] > 0), 'pop'].sum():,.0f} dân — tách theo bậc:")
    for t in ("ADJACENT", "NEAR", "ISOLATED"):
        m = (keep["access_tier"] == t) & (keep["pop"] > 0)
        print(f"    {t:<9} {int(m.sum()):>6,} ô · pop {keep.loc[m, 'pop'].sum():>11,.0f}"
              f" · pop_adj {keep.loc[m, 'pop_adj'].sum():>11,.0f}")
    # Q6iii — phép đo độ nhạy mặt nạ (audit 29/07): cùng một câu hỏi trên hai niên đại
    road_no_pop = (keep.road_access_m > 0) & ~(keep["pop"] > 0)
    road_no_pop25 = (keep.road_access_m > 0) & ~(keep["pop_2025"] > 0)
    print(f"  Q6iii: ô có đường mà pop(2020)=0: {int(road_no_pop.sum()):,} "
          f"({100 * road_no_pop.mean():.1f}%) | với pop_2025: {int(road_no_pop25.sum()):,} "
          f"({100 * road_no_pop25.mean():.1f}%)")

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
