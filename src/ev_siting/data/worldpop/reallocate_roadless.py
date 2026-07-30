#!/usr/bin/env python3
"""reallocate_roadless.py — E-DQ8b: dời dân ở ô KHÔNG có lối vào sang ô đặt trụ được.

Chạy **sau** `reconcile_dasymetric.py` (E-DQ7f) và dùng lại đúng bộ máy của nó: phát
hiện ở thang mà lỗi quan sát được → **trọng tài bằng tổng độc lập cấp xã (VNSDI DANSO)**
→ rải lại theo built-up → kế toán khối lượng bằng cổng FAIL được. Khác 7f ở ba chỗ, và
cả ba đều do **đo được**, không do phỏng đoán:

┌─ 1. PHẠM VI: ô roadless, không phải ô dồn cục ─────────────────────────────────────┐
Detector 7f (`max_px > 1.000` ∨ `pop>2.000 & top3>0,8`) là detector **dồn cục** — nó bắt
139 ô. E-DQ8 là **6.350 ô** và giao với 7f chỉ **109 ô**. Hai lỗi khác nhau: 7f = "cả xã
nhồi vào 1 pixel", 8b = "người ở ô mà xe không vào được".

┌─ 2. KHỐI LƯỢNG PHẦN LỚN LÀ THẬT (ngược 7f) ───────────────────────────────────────┐
7f đo được **63%** khối lượng bị cờ là **người ma** (WorldPop cấp xã > 1,5× DANSO) nên
rải lại tại chỗ = rải người ma. Đo lại **cùng phép trọng tài** trên tập E-DQ8 (2026-07-30,
6.350 ô, join xã 96,7%): chỉ **18,5%** (229.224 người · 765 ô · 83 xã) nằm trong xã
`RETOTAL`; **81,5%** (944.229 người · 825 xã) nằm trong xã mà DANSO **xác nhận tổng**.
⇒ Với 8b, mặc định là **REPLACE (bảo toàn khối lượng, chỉ đổi chỗ)**, không phải RETOTAL.

Và một đính chính phải ghi lại vì nó suýt dẫn tới phép sửa sai: giả thuyết "dân ở ô
roadless mà WorldCover không thấy built-up là smear" **không đứng** khi đo phân bố. Ô
built-up = 0 mà **có** đường: p50 = 97, p90 = 558, p99 = **1.779** người. Ô built-up = 0
mà **không** đường: p50 = 70, p90 = 391, p99 = **1.183** — đuôi **nhẹ hơn**. Tức "dân
trên đất không có built-up" là **thuộc tính toàn quốc của cặp WorldPop×WorldCover**
(12.182 ô · 2,50 M người), không phải bệnh riêng của ô roadless; ô roadless chỉ chiếm 24%
của nó. Vì vậy 8b **không** dùng built-up làm detector — built-up chỉ dùng làm **trọng số
ô nhận**. Cùng bài học "đại lượng phải chứa thông tin về lỗi" của E-DQ7a/7f, lần này
tránh được *trước* khi cài đặt.

┌─ 3. Ô NHẬN PHẢI ĐẶT TRỤ ĐƯỢC (sửa hồi quy của 7f) ────────────────────────────────┐
D4 của 7f rải theo built-up **không xét lối vào** ⇒ nó ĐỔ NGƯỜI VÀO Ô ROADLESS: số ô
`pop>0 & road_access=0` đi từ **6.350 (pop) → 6.467 (pop_adj)**. Ở đây trọng số ô nhận là
`built_ha × 1{access_tier == DIRECT}`, nên phép sửa không thể tự sinh thêm lỗi nó đang
sửa (cổng ⑧ canh đúng điều này). Cùng lỗi và cùng cách sửa nên áp lại cho D4 của 7f.

CHÍNH SÁCH KHỐI LƯỢNG (cấp xã, kế toán theo TỔNG — bài học cổng ⑤ của 7f: ô nhận vắt
biên thuộc hai xã nên bảo toàn theo NHÃN ô không giữ được):

    removed = Σ pop_adj của các ô roadless TRONG xã đó
    REPLACE (mặc định)          -> target = removed                (bảo toàn tuyệt đối)
    RETOTAL (wp_xã > 1,5·DANSO) -> target = removed · (0,859·DANSO / wp_xã)   < removed

RETOTAL ở đây **chỉ hạ phần khối lượng đang dời**, KHÔNG viết lại cả xã như 7f — vì 8b
sửa *vị trí của khối lượng roadless*, không sửa *tổng của xã*. Giữ phạm vi hẹp để hai
phép sửa không tranh nhau cùng một khối lượng.

`pop` (UN-anchored, E-DQ7e) **bất biến từng bit**; mọi thay đổi vào `pop_adj` — đúng hợp
đồng D5 của 7f: `pop` cho phát biểu TUYỆT ĐỐI, `pop_adj` cho consumer XẾP HẠNG.

Output:
  data/interim/worldpop/worldpop_pop_acc_h3.parquet  — h3_r8, pop, pop_adj, pop_src,
      access_tier, road_access_m, pop_pixel_implausible, maxa, danso (+ chẩn đoán 7f)
  data/interim/worldpop/worldpop_pop_acc_report.json — cổng QA + thống kê

Chạy:
    PYTHONPATH=src python -m ev_siting.data.worldpop.reallocate_roadless
"""
import json
import sys

import numpy as np
import pandas as pd
from shapely import STRtree, points
from shapely import wkb as shapely_wkb

import h3
from ..landuse.paths import LANDUSE_H3
from ..osm.access_tiers import RECEIVER_TIERS, derive as derive_tiers, summarise
from ..osm.paths import DEMAND_COMPONENTS
from ..vnsdi.paths import COMMUNES_PARQUET
from .paths import (POP_ACC_H3, POP_ACC_REPORT, POP_ADJ_H3,
                    POP_RETOTAL_RATIO, POP_WORLDPOP_OVER_DANSO, ensure_dirs)

#: diện tích ô res 8 (ha) — dùng đổi `built_up_frac` (WorldCover) -> ha built-up.
CELL_AREA_HA = 75.06


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


# --------------------------------------------------------------------------- #
# R1 — lưới hợp nhất + bậc lối vào                                            #
# --------------------------------------------------------------------------- #
def build_grid():
    """Lưới hợp nhất (ô có dân ∪ ô có đường ∪ ô có built-up) + `access_tier`.

    Phải hợp nhất TRƯỚC khi tính vành: tổng vành phụ thuộc ô láng giềng, nên tính trên
    một tập con nào đó sẽ báo "ISOLATED" cho ô mà láng giềng chỉ đơn giản là chưa có
    trong bảng đó. Đây chính là lỗi khiến 80 ô chứa 87 trạm đang vận hành **không tồn
    tại trong bất kỳ bảng lưới nào** (xem báo cáo E-DQ8 §4).
    """
    pop = pd.read_parquet(POP_ADJ_H3)
    comp = pd.read_parquet(DEMAND_COMPONENTS)[["h3_r8", "road_access_m"]]
    lu = pd.read_parquet(LANDUSE_H3)[["h3_r8", "built_up_frac"]]
    lu = lu[lu["built_up_frac"] > 0]
    g = (pd.DataFrame({"h3_r8": pd.unique(pd.concat(
            [pop["h3_r8"], comp["h3_r8"], lu["h3_r8"]], ignore_index=True))})
         .merge(comp, on="h3_r8", how="left")
         .merge(lu, on="h3_r8", how="left"))
    g["road_access_m"] = g["road_access_m"].fillna(0.0)
    g["built_up_frac"] = g["built_up_frac"].fillna(0.0)
    g["built_ha"] = g["built_up_frac"] * CELL_AREA_HA
    g = g.merge(pop, on="h3_r8", how="left")
    for c in ("pop", "pop_adj"):
        g[c] = g[c].fillna(0.0)
    g["pop_src"] = g["pop_src"].fillna("WORLDPOP")
    g["pop_pixel_implausible"] = (g["pop_pixel_implausible"]
                                 .astype(object).where(lambda s: s.notna(), False)
                                 .astype(bool))
    # bậc lối vào tính trên lưới HỢP NHẤT, gồm cả ô ngoài VN: 8.934 km đường rò của
    # Geofabrik (E-DQ7a) là láng giềng có đường THẬT của ô vắt biên. Clip trước khi tính
    # vành = báo ISOLATED giả cho đúng những ô biên — cùng lỗi E-DQ7a đã gỡ.
    return derive_tiers(g)


# --------------------------------------------------------------------------- #
# R3 — gán ô -> xã (tâm ô; 7f gán theo pixel nên hai bảng có thể lệch ở ô vắt   #
#      biên — chấp nhận được: xã chỉ dùng làm RANH GIỚI dời dân, không dùng làm #
#      nhãn hành chính, và cổng ⑤ kế toán theo TỔNG nên không lệ thuộc nhãn)    #
# --------------------------------------------------------------------------- #
def assign_communes(g, com):
    geoms = np.array([shapely_wkb.loads(b) for b in com["geom_wkb"]], dtype=object)
    tree = STRtree(geoms)
    ll = np.array([h3.cell_to_latlng(c) for c in g["h3_r8"]])
    pi, ci = tree.query(points(ll[:, 1], ll[:, 0]), predicate="intersects")
    order = np.argsort(pi, kind="stable")
    pi, ci = pi[order], ci[order]
    first = np.concatenate(([True], pi[1:] != pi[:-1])) if len(pi) else np.array([], bool)
    idx = np.full(len(g), -1)
    idx[pi[first]] = ci[first]
    out = g.copy()
    out["cell_maxa"] = np.where(idx >= 0, com["maxa"].to_numpy()[idx.clip(0)], None)
    out["cell_lat"], out["cell_lon"] = ll[:, 0], ll[:, 1]
    return out


# --------------------------------------------------------------------------- #
# Pipeline                                                                     #
# --------------------------------------------------------------------------- #
def run():
    ensure_dirs()
    for p, hint in ((POP_ADJ_H3, "`make reconcile-pop` (E-DQ7f)"),
                    (DEMAND_COMPONENTS, "`make osm` (E-DQ7b)"),
                    (LANDUSE_H3, "`make landuse-national` (WorldCover)"),
                    (COMMUNES_PARQUET, "`make vnsdi` (E-DQ7f)")):
        if not p.exists():
            raise SystemExit(f"thiếu {p} — chạy {hint} trước")

    print("[8b] dựng lưới hợp nhất + bậc lối vào...")
    g = build_grid()
    print(f"[8b] {len(g):,} ô; theo bậc: "
          + " · ".join(f"{k} {v['cells']:,}" for k, v in summarise(g).items()))

    com = pd.read_parquet(COMMUNES_PARQUET)
    g = assign_communes(g, com)
    # `landuse_h3` phủ theo TILE WorldCover (3°×3°) nên nó kéo vào ~200k ô built-up
    # ngoài lãnh thổ VN (Lào/Campuchia/TQ/biển). Chúng đã làm xong việc của mình (góp
    # đường vào tổng vành ở trên); giữ lại thì vừa thành ô NHẬN bất hợp pháp vừa bơm
    # ISOLATED giả vào báo cáo. Loại đúng phần vô can: không xã, không dân, không đường.
    noise = g["cell_maxa"].isna() & (g["pop_adj"] <= 0) & (g["road_access_m"] <= 0)
    print(f"[8b] loại {int(noise.sum()):,} ô đệm ngoài VN (từ tile WorldCover, "
          f"không xã/dân/đường)")
    g = g[~noise].reset_index(drop=True)
    joined = g["cell_maxa"].notna()
    print(f"[8b] join ô->xã: {joined.mean():.1%} "
          f"({g.loc[~joined, 'pop_adj'].sum():,.0f} người không gán được)")
    print(f"[8b] {len(g):,} ô; theo bậc: "
          + " · ".join(f"{k} {v['cells']:,}" for k, v in summarise(g).items()))

    # tổng WorldPop cấp xã (đo trên `pop` UN-anchored — cùng đại lượng 7f dùng để so
    # với DANSO; dùng pop_adj sẽ tự tham chiếu vào chính phép sửa)
    wp = g[joined].groupby("cell_maxa")["pop"].sum().rename("wp_commune")
    cm = com.set_index("maxa")
    g["danso"] = g["cell_maxa"].map(cm["danso"])
    g["wp_commune"] = g["cell_maxa"].map(wp)

    # R2 — phạm vi: ô CÓ dân nhưng KHÔNG có lối vào trong ô
    scope = (g["pop_adj"] > 0) & (~g["access_tier"].isin(RECEIVER_TIERS))
    before_mass = float(g.loc[scope, "pop_adj"].sum())
    print(f"[8b] phạm vi dời: {int(scope.sum()):,} ô, {before_mass:,.0f} người "
          f"({before_mass / g['pop_adj'].sum():.3%} toàn quốc)")

    # R3 — trọng tài cấp xã: RETOTAL nếu WorldPop > 1,5·DANSO
    ratio = g["wp_commune"] / g["danso"].where(g["danso"] > 0)
    g["commune_retotal"] = (ratio > POP_RETOTAL_RATIO).fillna(False)
    sc = g[scope]
    print(f"[8b] xã RETOTAL {sc.loc[sc.commune_retotal, 'cell_maxa'].nunique()} "
          f"({sc.loc[sc.commune_retotal, 'pop_adj'].sum():,.0f} người) · "
          f"REPLACE {sc.loc[~sc.commune_retotal, 'cell_maxa'].nunique()} "
          f"({sc.loc[~sc.commune_retotal, 'pop_adj'].sum():,.0f} người)")

    # R4/R5 — dời theo từng xã
    g = g.reset_index(drop=True)
    pop_adj = g["pop_adj"].to_numpy(dtype=float).copy()
    src = g["pop_src"].to_numpy(dtype=object).copy()
    tier = g["access_tier"].to_numpy()
    built = g["built_ha"].to_numpy(dtype=float)
    maxa = g["cell_maxa"].to_numpy(dtype=object)
    is_recv_tier = np.isin(tier, RECEIVER_TIERS)
    scope_arr = scope.to_numpy()
    retotal_arr = g["commune_retotal"].to_numpy()

    by_com = {}
    for i, m in enumerate(maxa):
        if m is not None:
            by_com.setdefault(m, []).append(i)

    acc = {"removed": 0.0, "target": 0.0, "retotal_removed": 0.0, "retotal_target": 0.0}
    n_moved = n_unrepaired = 0
    mass_unrepaired = 0.0

    # Ô roadless KHÔNG gán được xã: không có tổng độc lập để trọng tài và không có ranh
    # giới để dời trong ⇒ GIỮ TẠI CHỖ có nhãn. Đây là ô đảo/vắt biên mà polygon VNSDI
    # không phủ (đo 30/07: 224 ô · 41.642 người). Bỏ qua im lặng thì cổng ② bắt được —
    # và nó ĐÃ bắt ở lần chạy đầu. Đầu vào hợp lệ của E-DQ8c, không phải lỗi cần chữa.
    orphan = scope.to_numpy() & pd.isna(maxa)
    if orphan.any():
        src[orphan] = "UNREPAIRED_NO_COMMUNE"
        n_unrepaired += int(orphan.sum())
        mass_unrepaired += float(pop_adj[orphan].sum())
        print(f"[8b] {int(orphan.sum()):,} ô roadless không gán được xã "
              f"({pop_adj[orphan].sum():,.0f} người) -> giữ tại chỗ, nhãn "
              f"UNREPAIRED_NO_COMMUNE")
    for m, idx in by_com.items():
        idx = np.asarray(idx)
        src_idx = idx[scope_arr[idx]]
        if len(src_idx) == 0:
            continue
        removed = float(pop_adj[src_idx].sum())
        if removed <= 0:
            continue
        # Ô NHẬN = built-up **và** đặt trụ được (DIRECT). KHÔNG có nhánh dự phòng "rải
        # vào ô built-up bất kỳ": lần chạy đầu có nhánh đó và cổng ② bắt ngay — nó đổ dân
        # sang một ô roadless KHÁC, tức tự sinh lại đúng lỗi đang sửa (cùng hồi quy mà D4
        # của 7f mắc). Xã không có ô built-up DIRECT nào nghĩa là xã đó **thật sự** không
        # có đất vừa xây được vừa tới được — câu trả lời trung thực là "không phục vụ
        # được" (đầu vào E-DQ8c), không phải dời sang một ô cũng không tới được.
        cand = idx[(built[idx] > 0) & is_recv_tier[idx]]
        if len(cand) == 0:
            n_unrepaired += len(src_idx)
            mass_unrepaired += removed
            src[src_idx] = "UNREPAIRED_NO_ACCESSIBLE_BUILTUP"
            continue
        label = "MOVED_TO_ACCESSIBLE"
        if retotal_arr[src_idx].any():
            r = float(g["wp_commune"].iloc[src_idx[0]] / g["danso"].iloc[src_idx[0]])
            target = removed * min(1.0, POP_WORLDPOP_OVER_DANSO / r)
            acc["retotal_removed"] += removed
            acc["retotal_target"] += target
        else:
            target = removed
        acc["removed"] += removed
        acc["target"] += target
        w = built[cand]
        pop_adj[src_idx] = 0.0
        src[src_idx] = label
        pop_adj[cand] += target * w / w.sum()
        n_moved += len(src_idx)

    g["pop_adj"] = pop_adj
    g["pop_src"] = src
    reduction = acc["removed"] - acc["target"]
    print(f"[8b] đã dời {n_moved:,} ô -> ô DIRECT · {n_unrepaired:,} ô giữ tại chỗ "
          f"({mass_unrepaired:,.0f} người, -> E-DQ8c)")
    print(f"[8b] người ma gỡ bởi RETOTAL: {reduction:,.0f}")

    out_cols = ["h3_r8", "pop", "pop_adj", "pop_src", "access_tier", "road_access_m",
                "road_access_nb1_m", "road_access_nb2_m", "built_ha",
                "pop_pixel_implausible", "cell_maxa", "danso"]
    diag = [c for c in ("n_px", "max_px", "top3_px_share", "n_eff", "pop_per_eff_px",
                        "pop_lat", "pop_lon") if c in g.columns]
    out = g[out_cols + diag].rename(columns={"cell_maxa": "maxa"})
    out = out.sort_values("pop_adj", ascending=False).reset_index(drop=True)

    report = {"cells": int(len(out)), "scope_cells": int(scope.sum()),
              "scope_mass_before": before_mass,
              "cells_moved": n_moved, "cells_unrepaired": n_unrepaired,
              "mass_unrepaired": mass_unrepaired,
              "retotal_reduction": reduction,
              "access_tiers_pop": summarise(g), "checks": []}
    print("\n[8b] cổng QA:")
    ok = qa_gates(report, g, out, acc, before_mass, reduction)
    report["overall"] = "PASS" if ok else "FAIL"
    POP_ACC_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    if not ok:
        print(f"\n[FAIL] -> {POP_ACC_REPORT} (KHÔNG ghi {POP_ACC_H3.name})",
              file=sys.stderr)
        sys.exit(1)
    out.to_parquet(POP_ACC_H3, index=False)
    print(f"\n[PASS] -> {POP_ACC_REPORT}")
    print(f"[8b] -> {POP_ACC_H3}")
    return out


def qa_gates(report, g, out, acc, before_mass, reduction):
    """8 cổng E-DQ8b. Mỗi cổng canh một giả định và FAIL được — không cổng nào đúng
    theo *xây dựng* (bài học `poi_coords_in_vn` của E-DQ7a)."""
    all_ok = True
    canon = pd.read_parquet(POP_ADJ_H3)[["h3_r8", "pop", "pop_adj"]]
    j = canon.merge(out[["h3_r8", "pop", "pop_adj"]], on="h3_r8",
                    suffixes=("_0", "_1"))

    # ① `pop` bất biến từng bit (hợp đồng E-DQ7e/D5 — cột UN-anchored không được đụng)
    dp = float((j["pop_0"] - j["pop_1"]).abs().max())
    all_ok &= _check(report, "pop_bit_invariant", dp < 1e-9,
                     f"max|Δpop| = {dp:.2e}; giữ đủ ô = "
                     f"{set(canon.h3_r8) <= set(out.h3_r8)}")

    # ② KHÔNG còn dân ở ô roadless, TRỪ ô đã ghi nhãn không rải được
    left = g[(g["pop_adj"] > 0) & (~g["access_tier"].isin(RECEIVER_TIERS))]
    unlabelled = int((~left["pop_src"].astype(str)
                      .str.startswith("UNREPAIRED")).sum())
    all_ok &= _check(report, "no_unlabelled_roadless_pop", unlabelled == 0,
                     f"{len(left):,} ô roadless còn dân "
                     f"({left['pop_adj'].sum():,.0f} người), {unlabelled} ô KHÔNG nhãn")

    # ③ RETOTAL chỉ được HẠ (không bịa người) — kế toán theo TỔNG như cổng ④ của 7f
    all_ok &= _check(report, "retotal_only_reduces", reduction >= -1e-6,
                     f"gỡ {reduction:,.0f} người ma "
                     f"(removed {acc['retotal_removed']:,.0f} - "
                     f"target {acc['retotal_target']:,.0f})")

    # ④ bảo toàn TỔNG: Σpop_adj mới = Σ cũ − reduction, chính xác từng người
    before = float(canon["pop_adj"].sum())
    after = float(out["pop_adj"].sum())
    resid = abs(after - (before - reduction))
    all_ok &= _check(report, "global_mass_accounted", resid < 1.0,
                     f"|Σpop_adj − kỳ vọng| = {resid:.3f} người "
                     f"({after:,.0f} vs {before - reduction:,.0f})")

    # ⑤ trôi tổng quốc gia < 1% (7f đã dùng 0,499% — 8b phải cộng dồn vẫn dưới trần)
    drift = abs(after - before) / before
    all_ok &= _check(report, "national_drift_lt_1pct", drift < 0.01,
                     f"trôi {drift:.3%} so pop_adj sau 7f")

    # ⑥ HỒI QUY 7f: phép sửa không được tự sinh ra lỗi nó đang sửa (D4 của 7f đã sinh:
    #    6.350 -> 6.467 ô). Sau 8b, khối lượng roadless phải GIẢM THẬT.
    after_mass = float(left["pop_adj"].sum())
    all_ok &= _check(report, "roadless_mass_strictly_decreases",
                     after_mass < before_mass,
                     f"{before_mass:,.0f} -> {after_mass:,.0f} người "
                     f"({after_mass / before_mass - 1:+.1%})")

    # ⑦ mọi khối lượng NHẬN phải đáp xuống ô DIRECT — đo bằng cách so pop_adj trước/sau
    #    trên chính các ô không-DIRECT. Cổng này FAIL được: nếu ai đó thêm lại nhánh dự
    #    phòng "rải vào built-up bất kỳ", hoặc trọng số ô nhận thôi xét lối vào, nó đỏ
    #    ngay. (Không đo bằng nhãn `pop_src` — nhãn là thứ code TỰ GHI, kiểm bằng nó thì
    #    cổng chỉ xác nhận code đồng ý với chính nó; cùng lỗi `poi_coords_in_vn` E-DQ7a.)
    d = g[["h3_r8", "access_tier"]].merge(
        canon[["h3_r8", "pop_adj"]].rename(columns={"pop_adj": "before"}),
        on="h3_r8", how="left").assign(after=g["pop_adj"].to_numpy())
    d["before"] = d["before"].fillna(0.0)
    gained = d[(d["after"] - d["before"] > 1e-6) & (d["access_tier"] != "DIRECT")]
    all_ok &= _check(report, "all_received_mass_landed_direct", len(gained) == 0,
                     f"{len(gained)} ô không-DIRECT nhận thêm dân "
                     f"({(gained['after'] - gained['before']).sum():,.0f} người)")

    # ⑧ (advisory) tập CUNG bị xê dịch bao nhiêu — 7f đo 14/12.811; nếu 8b chạm nhiều
    #    ô cung thì E-DQ7d phải hiệu chuẩn lại, đó là thông tin Kỳ cần biết.
    moved = j[(j["pop_adj_0"] - j["pop_adj_1"]).abs() > 1e-6]
    _check(report, "supply_ranking_shift", True,
           f"{len(moved):,} ô đổi pop_adj (báo cáo, không chặn)", fatal=False)
    report["cells_pop_adj_changed"] = int(len(moved))
    return all_ok


if __name__ == "__main__":
    run()
