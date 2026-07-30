#!/usr/bin/env python3
"""enrich_grid.py — E-DQ3 (phía LƯỚI): nhãn hành chính cho `demand_h3` + `demand_commune`.

Phía trạm (`enrich_stations.py`) là một phép join tất định vì ĐIỂM có lãnh thổ xác định.
Phía lưới thì không, và bỏ qua khác biệt đó là cách tạo ra một bảng rollup sai hàng chục
triệu người mà mọi cột đều "có giá trị".

┌─ ĐO ĐƯỢC (255.480 ô của lưới hiện tại) ───────────────────────────────────────────┐
    tâm ô ∈ polygon xã            252.372 ô (98,78%)
    lục giác ∩ polygon xã         255.298 ô  ⇒ tâm ô BỎ SÓT **2.926 ô / 475.083 người**
    ô chạm >= 2 xã (tối đa 6)      61.649 ô  ⇒ **40,0% dân số** không thuộc trọn một xã

Hai hệ quả, và chúng là hai QUYẾT ĐỊNH khác nhau:

  1. **Test = lục giác ∩ polygon, KHÔNG phải tâm ô ∈ polygon.** Đúng bài học E-DQ7a
     (ở đó, test theo tâm ô xoá nhầm 74.642 dân — lệch 11 lần). Cổng ③ `hex_beats_centroid`
     đo LẠI cả hai cách mỗi lần chạy: nếu ai đó "đơn giản hoá" về tâm ô thì cổng FAIL,
     chứ không phải mất 475k người trong im lặng.

  2. **NHÃN ≠ PHÂN BỔ.** `demand_h3.commune_name` là **nhãn** (xã chiếm diện tích lớn
     nhất) — dùng để lọc/hiển thị. Nó **KHÔNG** được dùng để cộng khối lượng: với 40%
     dân số ở ô vắt xã, `groupby(commune_name).sum()` gán trọn dân của một ô cho một xã.
     Phân bổ đi qua bảng LONG `cell_commune` (trọng số diện tích, Σw = 1 mỗi ô) và ra
     `demand_commune`. `admin_frac` (tỉ lệ thô của xã thắng) đi kèm nhãn để consumer biết
     nhãn "chắc" tới đâu — cùng tinh thần `frac_in_vn` của E-DQ7a, không nén một đại
     lượng liên tục vào một cờ nhị phân.

Ô không chạm xã nào (**182 ô**, ~2.900 người — đảo/vắt biên/ngoài khơi) **không bị xoá**
và không bị gán bừa: chúng vắng mặt trong `cell_commune`, và phần dư được **công bố** ở
report (`residual_*`) đúng nguyên tắc `input = output + quarantined` của mọi bước E-DQ.
Đây cũng chính là nhóm mà **E-DQ8c** phải ra chính sách `demand_servable`.

⚠️ `demand_commune.danso` là dân số **đăng ký 2025 của VNSDI**, để cạnh `pop`/`pop_adj`
(WorldPop 2020, UN-anchored) làm ĐỐI CHỨNG — KHÔNG phải để thay. Chênh +16,5% toàn quốc
là khe niên đại P9/P10, không phải sai số phân bổ (xem `vnsdi/paths.py`).

Output:
  data/interim/admin/cell_commune.parquet    — h3_r8, commune_code, area_frac, w
  data/interim/admin/demand_commune.parquet  — rollup cấp xã (+ nhãn tỉnh, danso, cung)
  data/interim/admin/grid_admin_report.json  — cổng QA + đối soát
  data/interim/demand/demand_h3.parquet      — thêm 4 cột nhãn + commune_code/admin_frac

Chạy (sau `make demand`):
    PYTHONPATH=src python -m ev_siting.data.admin.enrich_grid
"""
import json
import sys

import numpy as np
import pandas as pd
from shapely import STRtree, points

import h3

from ..evcs.paths import STATIONS_DIR
from ..worldpop.paths import DEMAND_H3
from .boundaries import (LABEL_COLS, assign_points, cell_overlaps,
                         labels_from_overlaps, load_communes)
from .paths import (ADMIN_SOURCE, ADMIN_VINTAGE, CELL_COMMUNE, DEMAND_COMMUNE,
                    EXPECTED_PROVINCES, GRID_ADMIN_REPORT, PROJECT_ROOT, ensure_dirs)

#: Xã KHÔNG có đất trong lưới -> được phép vắng mặt ở cổng ⑥. `20333` = Đặc khu Hoàng Sa
#: (350 km², `danso = 0`) — cùng allowlist mà `vnsdi/fetch_communes.py` đã dùng.
NO_LAND_COMMUNES = {"20333"}

#: Cột nhãn E-DQ3 ghi thêm vào `demand_h3` (`commune_code` là khoá join thật).
GRID_ADMIN_COLS = list(LABEL_COLS) + ["admin_frac", "n_communes"]

#: Cột khối lượng được phân bổ theo trọng số diện tích. POI là số ĐẾM nguyên, sau khi
#: chia tỉ lệ thành số thực — đúng bản chất "phần của ô thuộc xã này", và là điều kiện
#: để cổng kế toán ① kiểm được tổng.
_SKIP = {"h3_r8", "access_tier", "cell_state", "pop_pixel_implausible", "frac_in_vn"}


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def _centroid_match(cells) -> int:
    """Số ô mà TÂM ô rơi vào một polygon xã — chỉ để cổng ③ so với phép giao lục giác."""
    com = load_communes()
    tree = STRtree(com["geometry"].to_numpy())
    ll = np.array([h3.cell_to_latlng(c) for c in cells])
    hit, _ = tree.query(points(ll[:, 1], ll[:, 0]), predicate="intersects")
    return int(len(np.unique(hit)))


def _supply_by_commune() -> pd.DataFrame:
    """Đếm trạm CUNG theo xã (gán độc lập bằng chính `assign_points`, không phụ thuộc
    canonical đã enrich hay chưa -> chạy được ở mọi thứ tự pipeline)."""
    cols = ["lat", "lng", "coord_resolved", "is_operational", "access", "is_primary"]
    try:
        st = pd.read_parquet(STATIONS_DIR, columns=cols)
    except Exception:
        return pd.DataFrame(columns=["commune_code", "n_supply"])
    sup = st[st["coord_resolved"].fillna(False) & st["is_operational"].fillna(False)
             & st["access"].eq("PUBLIC") & st["is_primary"].fillna(False)]
    if sup.empty:
        return pd.DataFrame(columns=["commune_code", "n_supply"])
    lab = assign_points(sup["lat"].to_numpy(), sup["lng"].to_numpy())
    return (lab.loc[lab["commune_code"].notna()]
            .groupby("commune_code", as_index=False).size()
            .rename(columns={"size": "n_supply"}))


def rollup(grid: pd.DataFrame, ov: pd.DataFrame) -> pd.DataFrame:
    """`demand_commune` — phân bổ khối lượng ô theo trọng số diện tích rồi cộng theo xã."""
    mass_cols = [c for c in grid.columns
                 if c not in _SKIP and pd.api.types.is_numeric_dtype(grid[c])]
    j = ov.merge(grid[["h3_r8"] + mass_cols], on="h3_r8", how="left")
    for c in mass_cols:
        j[c] = j[c].fillna(0.0) * j["w"]
    agg = j.groupby("commune_code", as_index=False)[mass_cols].sum()
    agg["n_cells"] = j.groupby("commune_code")["h3_r8"].nunique().to_numpy()
    agg["cell_area_equiv"] = j.groupby("commune_code")["w"].sum().to_numpy()

    com = load_communes()[LABEL_COLS + ["dientich_km2", "danso"]]
    out = com.merge(agg, on="commune_code", how="left")
    for c in mass_cols + ["n_cells", "cell_area_equiv"]:
        out[c] = out[c].fillna(0.0)
    out["n_cells"] = out["n_cells"].astype("int64")
    out = out.merge(_supply_by_commune(), on="commune_code", how="left")
    out["n_supply"] = out["n_supply"].fillna(0).astype("int64")
    return out.sort_values("pop_adj", ascending=False).reset_index(drop=True)


def qa_gates(report, grid, ov, labels, dc):
    """7 cổng — đóng E-DQ3 phía lưới THẬT, không chỉ 'demand_h3 có thêm 4 cột'."""
    all_ok = True
    mass_cols = [c for c in grid.columns
                 if c not in _SKIP and pd.api.types.is_numeric_dtype(grid[c])]
    joined = grid["h3_r8"].isin(set(ov["h3_r8"]))

    # ① KẾ TOÁN: tổng phân bổ == tổng của các ô CÓ chạm xã (dung sai tương đối — tổng
    #    lane-mét ~1e8 nên sai số cộng dồn float vượt 1e-6 tuyệt đối).
    lhs = {c: float(dc[c].sum()) for c in mass_cols}
    rhs = {c: float(grid.loc[joined, c].sum()) for c in mass_cols}
    diff = {c: lhs[c] - rhs[c] for c in mass_cols}
    all_ok &= _check(report, "grid_admin_conservation",
                     all(abs(v) <= 1e-9 * max(1.0, abs(rhs[c])) for c, v in diff.items()),
                     json.dumps({c: round(v, 6) for c, v in diff.items()}))

    # ② phần dư (ô không chạm xã nào) phải nhỏ — và được CÔNG BỐ, không nuốt im lặng.
    res_pop = float(grid.loc[~joined, "pop_adj"].sum())
    share = res_pop / max(float(grid["pop_adj"].sum()), 1.0)
    all_ok &= _check(report, "grid_admin_join_rate", share < 5e-3,
                     f"{int((~joined).sum()):,} ô ngoài mọi xã giữ {res_pop:,.0f} người "
                     f"({share:.4%}) -> E-DQ8c")

    # ③ lục giác PHẢI bắt được nhiều ô hơn tâm ô (chống 'đơn giản hoá' về tâm ô — đúng
    #    lỗi mà E-DQ7a đã đo là lệch 11 lần). Đo lại cả hai mỗi lần chạy.
    n_cent = _centroid_match(grid["h3_r8"].tolist())
    n_hex = int(joined.sum())
    gained = n_hex - n_cent
    all_ok &= _check(report, "hex_beats_centroid", gained > 0,
                     f"lục giác {n_hex:,} vs tâm ô {n_cent:,} (+{gained:,} ô)")
    report["stats"]["cells_centroid_match"] = n_cent
    report["stats"]["cells_hex_match"] = n_hex

    # ④ trọng số phân bổ cộng đúng 1 trên mỗi ô (điều kiện cần của cổng ①).
    wsum = ov.groupby("h3_r8")["w"].sum()
    all_ok &= _check(report, "weights_sum_to_one",
                     bool(np.allclose(wsum.to_numpy(), 1.0, atol=1e-9)),
                     f"lệch tối đa {float((wsum - 1).abs().max()):.2e}")

    # ⑤ nhãn PHẢI là xã chiếm diện tích LỚN NHẤT trong ô. FAIL được nếu phép sắp xếp/
    #    argmax hỏng (vd đổi `sort_values` mà quên `ascending=False`).
    mx = ov.groupby("h3_r8", as_index=False)["area_frac"].max().rename(
        columns={"area_frac": "max_frac"})
    chk = labels.merge(mx, on="h3_r8", how="left")
    bad = int((chk["admin_frac"] < chk["max_frac"] - 1e-12).sum())
    all_ok &= _check(report, "label_is_argmax", bad == 0, f"{bad} ô nhãn không phải argmax")

    # ⑥ mọi xã CÓ ĐẤT phải chạm >= 1 ô (lưới không được bỏ trắng một xã nào — nếu không,
    #    `coverage_pop` cấp xã sẽ thiếu mẫu số mà không ai biết).
    miss = set(dc.loc[dc["n_cells"] == 0, "commune_code"]) - NO_LAND_COMMUNES
    all_ok &= _check(report, "communes_covered", not miss,
                     f"{len(miss)} xã không có ô nào: {sorted(miss)[:5]}")

    # ⑦ một niên đại duy nhất (34 tỉnh VNSDI) — cùng cổng với phía trạm.
    n_prov = int(dc["admin_l1_code"].nunique())
    all_ok &= _check(report, "admin_vintage_single", n_prov == EXPECTED_PROVINCES,
                     f"{n_prov} tỉnh (kỳ vọng {EXPECTED_PROVINCES})")
    return all_ok


def run():
    ensure_dirs()
    if not DEMAND_H3.exists():
        raise SystemExit(f"thiếu {DEMAND_H3} — chạy `make demand` trước")
    grid = pd.read_parquet(DEMAND_H3)
    grid = grid.drop(columns=[c for c in GRID_ADMIN_COLS if c in grid.columns])

    print(f"[E-DQ3] giao lục giác ∩ ranh giới xã trên {len(grid):,} ô...")
    ov = cell_overlaps(grid["h3_r8"].tolist())
    ov.to_parquet(CELL_COMMUNE, index=False)
    labels = labels_from_overlaps(ov)
    print(f"[E-DQ3] {len(ov):,} cặp (ô, xã) · {labels['h3_r8'].nunique():,} ô có nhãn · "
          f"{int((labels['n_communes'] >= 2).sum()):,} ô vắt >= 2 xã")

    com = load_communes()[LABEL_COLS]
    lab = labels.merge(com, on="commune_code", how="left")
    out = grid.merge(lab[["h3_r8"] + GRID_ADMIN_COLS], on="h3_r8", how="left")
    out["n_communes"] = out["n_communes"].fillna(0).astype("int64")
    out.to_parquet(DEMAND_H3, index=False)

    dc = rollup(grid, ov)
    dc.to_parquet(DEMAND_COMMUNE, index=False)

    rel = lambda p: p.relative_to(PROJECT_ROOT)
    print(f"[E-DQ3] -> {rel(DEMAND_H3)} (+{len(GRID_ADMIN_COLS)} cột nhãn)")
    print(f"[E-DQ3] -> {rel(CELL_COMMUNE)} (bảng phân bổ)")
    print(f"[E-DQ3] -> {rel(DEMAND_COMMUNE)} ({len(dc):,} xã / "
          f"{dc['admin_l1_code'].nunique()} tỉnh)")
    top = dc.head(5)[["province_name", "commune_name", "pop_adj", "danso", "n_supply"]]
    print("  5 xã đông nhất (pop_adj phân bổ vs DANSO 2025 vs số trạm cung):")
    for r in top.itertuples():
        print(f"    {r.province_name:<22} {r.commune_name:<24} "
              f"{r.pop_adj:>10,.0f} {r.danso:>10,.0f} {r.n_supply:>5}")

    report = {"admin_vintage": ADMIN_VINTAGE, "admin_source": ADMIN_SOURCE,
              "checks": [], "stats": {
                  "cells": int(len(grid)), "pairs": int(len(ov)),
                  "cells_multi_commune": int((labels["n_communes"] >= 2).sum()),
                  "pop_adj_multi_commune": float(
                      grid.loc[grid["h3_r8"].isin(
                          set(labels.loc[labels["n_communes"] >= 2, "h3_r8"])),
                          "pop_adj"].sum()),
                  "communes": int(len(dc)),
                  "provinces": int(dc["admin_l1_code"].nunique()),
              }}
    print("\n[E-DQ3] cổng QA:")
    ok = qa_gates(report, grid, ov, labels, dc)
    report["overall"] = "PASS" if ok else "FAIL"
    GRID_ADMIN_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
    print(f"\n[{report['overall']}] -> {rel(GRID_ADMIN_REPORT)}")
    if not ok:
        sys.exit(1)
    return out, dc


if __name__ == "__main__":
    run()
