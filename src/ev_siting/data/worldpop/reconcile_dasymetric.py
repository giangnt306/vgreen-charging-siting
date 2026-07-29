#!/usr/bin/env python3
"""reconcile_dasymetric.py — E-DQ7f: phát hiện + sửa `pop` bị dồn cục dasymetric.

CHẨN ĐOÁN (đã đo trên artefact UNadj, 2026-07-29). WorldPop *constrained* (BSGM) rải
tổng dân cấp xã chỉ lên pixel mà mặt nạ built-settlement cho là có người. Nơi mặt nạ bỏ
sót (núi đá vôi Đông Bắc/Tây Bắc, đảo), cả xã dồn vào 1–5 pixel: đỉnh 28.731 người trên
MỘT pixel 100 m. Detector mật độ cũ (>48.000/km²) bắt **0/139** ô hỏng và đánh oan 61 ô
lõi TP.HCM CÓ THẬT — giao hai tập = 0.

BƯỚC NGOẶT (đối chiếu VNSDI DANSO — nguồn dân số cấp xã ĐỘC LẬP, xem
`data/vnsdi/`). Tiền đề cũ "792k người là THẬT, chỉ sai chỗ" **SAI với 63% khối lượng**:
50/139 ô nằm trong xã mà WorldPop > 1,5× DANSO; **16 ô có riêng MỘT ô nhiều dân hơn cả
xã** (bất khả thi — chống được cả lệch niên đại). Cụm đảo Hòn Nghệ/Sơn Hải (An Giang):
WorldPop 117k vs DANSO 5,3k (~22×). Tái phân bổ giữ nguyên khối lượng ở đó = rải NGƯỜI
MA. Vì vậy sửa phải TÁCH theo tổng độc lập:

  RETOTAL  (WorldPop_xã > 1,5·DANSO): tổng cấp xã là ma -> hạ về 0,859·DANSO
           (0,859 = tỉ số quốc gia, trung hoà lệch niên đại 2020↔2025) rồi rải lại.
  REPLACE  (còn lại, ô bị cờ): tổng đúng, chỉ sai vị trí -> giữ tổng cấp xã, rải lại.

CẢ HAI đều RẢI LẠI theo **built-up ESA WorldCover 10 m** trong ranh giới xã (không phải
winsorize: cắt ngọn sẽ san phẳng đúng lõi TP.HCM mà không chạm ô hỏng). Vị trí trong ô
vốn ĐÃ đúng (dân cách built-up trung vị 26 m) nên sai sót thật là "ô nào / bao nhiêu",
đúng thứ mà rải-theo-built-up sửa.

NEO KHỐI LƯỢNG. `pop` (UN-anchored, E-DQ7e) GIỮ NGUYÊN từng bit — mọi phát biểu tuyệt
đối vẫn dùng nó, cổng `pop_total_matches_unadj` còn xanh. `pop_adj` là cột ĐÃ ĐẶT LẠI
CHỖ cho consumer XẾP HẠNG (MCLP `demand_weight`, T4 gap-fill). Σ`pop_adj` quốc gia thấp
hơn ~0,3–0,4% (người ma đã gỡ khỏi đảo) — hệ quả CÓ CHỦ Ý, có cổng canh <1%. KHÔNG cân
bằng người ma sang xã thiếu trên phạm vi toàn quốc: việc đó kéo thứ hạng cả lưới theo số
đăng ký 2025 và trộn hiệu chỉnh niên đại (P10) vào một lỗi phân bổ — ngoài phạm vi 7f.

Output:
  data/interim/worldpop/worldpop_pop_adj_h3.parquet — h3_r8, pop, pop_adj, pop_src, cờ,
      + chẩn đoán (n_px, max_px, top3_px_share, n_eff, pop_per_eff_px, pop_lat/lon, maxa)
  data/interim/worldpop/worldpop_pop_adj_report.json — cổng QA + thống kê

Chạy:
    PYTHONPATH=src python -m ev_siting.data.worldpop.reconcile_dasymetric
"""
import json
import sys

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from shapely import STRtree, points
from shapely import wkb as shapely_wkb

import h3
from ..landuse.paths import WC_TILE_DIR
from ..vnsdi.paths import COMMUNES_PARQUET
from .paths import (H3_RES_R8, POP_ADJ_H3, POP_ADJ_REPORT, POP_H3,
                    POP_BUILTUP_DENSITY_CEIL, POP_MAX_PX_IMPLAUSIBLE,
                    POP_PIXEL_IMPLAUSIBLE_MIN_POP, POP_RETOTAL_RATIO, POP_TIF,
                    POP_TOP3_SHARE_IMPLAUSIBLE, POP_WORLDPOP_OVER_DANSO,
                    ensure_dirs)

ROW_BLOCK = 512
WC_BUILT = 50          # lớp "built-up" của ESA WorldCover
WC_STRIDE = 2          # lấy mẫu 20 m cho trọng số built-up (đủ mịn, nhanh gấp 4)


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


# --------------------------------------------------------------------------- #
# D1 — đọc raster -> pixel (giữ lại) + gộp thống kê theo ô                     #
# --------------------------------------------------------------------------- #
def read_pixels():
    """Trả DataFrame pixel có dân: lat, lon, pop, h3_r8. Đây là NƠI DUY NHẤT quan sát
    được bằng chứng dồn cục — vào tới `demand_h3` thì pixel đã mất."""
    lats, lons, vals = [], [], []
    with rasterio.open(POP_TIF) as src:
        nodata, H, W, t = src.nodata, src.height, src.width, src.transform
        lon_row = t.c + t.a * (np.arange(W) + 0.5)
        for r0 in range(0, H, ROW_BLOCK):
            n = min(ROW_BLOCK, H - r0)
            arr = src.read(1, window=Window(0, r0, W, n))
            m = np.isfinite(arr) & (arr > 0)
            if nodata is not None:
                m &= arr != nodata
            if not m.any():
                continue
            rr, cc = np.nonzero(m)
            vals.append(arr[rr, cc].astype(np.float64))
            lats.append(t.f + t.e * ((r0 + rr) + 0.5))
            lons.append(lon_row[cc])
    lat, lon, pop = map(np.concatenate, (lats, lons, vals))
    cells = [h3.latlng_to_cell(a, b, H3_RES_R8) for a, b in zip(lat, lon)]
    return pd.DataFrame({"lat": lat, "lon": lon, "pop": pop, "h3_r8": cells})


def cell_stats(px):
    g = px.groupby("h3_r8")
    st = pd.DataFrame({
        "pop": g["pop"].sum(), "n_px": g["pop"].size(), "max_px": g["pop"].max(),
        "sum_sq": px.assign(p2=px["pop"] ** 2).groupby("h3_r8")["p2"].sum(),
    })
    top3 = (px.sort_values("pop", ascending=False)
              .groupby("h3_r8")["pop"].head(3).groupby(px["h3_r8"]).sum())
    st["top3_px_share"] = top3 / st["pop"]
    st["n_eff"] = st["pop"] ** 2 / st["sum_sq"]
    st["pop_per_eff_px"] = st["sum_sq"] / st["pop"]
    w = px.assign(wlat=px["pop"] * px["lat"], wlon=px["pop"] * px["lon"]).groupby("h3_r8")
    st["pop_lat"] = w["wlat"].sum() / st["pop"]
    st["pop_lon"] = w["wlon"].sum() / st["pop"]
    return st.drop(columns="sum_sq").reset_index()


# --------------------------------------------------------------------------- #
# D1/D3 — gán pixel -> xã, tổng WorldPop cấp xã vs DANSO                       #
# --------------------------------------------------------------------------- #
def assign_communes(px, com):
    geoms = np.array([shapely_wkb.loads(b) for b in com["geom_wkb"]], dtype=object)
    tree = STRtree(geoms)
    pts = points(px["lon"].to_numpy(), px["lat"].to_numpy())
    pi, ci = tree.query(pts, predicate="intersects")
    order = np.argsort(pi, kind="stable")           # ô chồng biên -> giữ match đầu
    pi, ci = pi[order], ci[order]
    first = np.concatenate(([True], pi[1:] != pi[:-1])) if len(pi) else np.array([], bool)
    cidx = np.full(len(px), -1)
    cidx[pi[first]] = ci[first]
    px = px.assign(cidx=cidx)
    px["maxa"] = np.where(cidx >= 0, com["maxa"].to_numpy()[cidx.clip(0)], None)
    return px


# --------------------------------------------------------------------------- #
# D4 — built-up ha/ô trong 1 xã (đọc WorldCover full-res, stride nhẹ)          #
# --------------------------------------------------------------------------- #
def _tile_for(lat, lon):
    la, lo = int(np.floor(lat / 3) * 3), int(np.floor(lon / 3) * 3)
    p = WC_TILE_DIR / f"ESA_WorldCover_10m_2021_v200_N{la:02d}E{lo:03d}_Map.tif"
    return p if p.exists() else None


def builtup_ha_by_cell(poly):
    """Đọc built-up (lớp 50) trong bbox polygon, gán H3 tâm pixel, trả {h3: ha}."""
    s, w, e, n = poly.bounds[1], poly.bounds[0], poly.bounds[2], poly.bounds[3]
    tp = _tile_for((s + n) / 2, (w + e) / 2)
    if tp is None:
        return {}
    from rasterio.windows import from_bounds
    with rasterio.open(tp) as src:
        try:
            win = from_bounds(w, s, e, n, src.transform).round_offsets().round_lengths()
        except Exception:
            return {}
        co, ro = max(0, int(win.col_off)), max(0, int(win.row_off))
        wd = min(src.width - co, int(win.width))
        ht = min(src.height - ro, int(win.height))
        if wd <= 0 or ht <= 0:
            return {}
        arr = src.read(1, window=Window(co, ro, wd, ht))[::WC_STRIDE, ::WC_STRIDE]
        t = src.transform
        lons = t.c + t.a * (np.arange(co, co + wd, WC_STRIDE) + 0.5)
        lats = t.f + t.e * (np.arange(ro, ro + ht, WC_STRIDE) + 0.5)
    m = arr == WC_BUILT
    if not m.any():
        return {}
    LON, LAT = np.meshgrid(lons, lats)
    bl, bo = LAT[m], LON[m]
    ha_per_px = 0.01 * WC_STRIDE * WC_STRIDE          # mỗi mẫu đại diện stride² pixel 10 m
    out = {}
    minx, miny, maxx, maxy = poly.bounds
    for a, o in zip(bl, bo):
        if not (miny <= a <= maxy and minx <= o <= maxx):
            continue
        if not poly.covers(_pt(o, a)):
            continue
        c = h3.latlng_to_cell(a, o, H3_RES_R8)
        out[c] = out.get(c, 0.0) + ha_per_px
    return out


def _pt(x, y):
    from shapely.geometry import Point
    return Point(x, y)


# --------------------------------------------------------------------------- #
# Pipeline                                                                     #
# --------------------------------------------------------------------------- #
def run():
    ensure_dirs()
    if not POP_H3.exists():
        raise SystemExit(f"thiếu {POP_H3} — chạy worldpop_pop.py trước")
    if not COMMUNES_PARQUET.exists():
        raise SystemExit(f"thiếu {COMMUNES_PARQUET} — chạy `make vnsdi` trước (E-DQ7f cần "
                         f"nguồn dân số cấp xã độc lập)")

    print("[7f] đọc raster -> pixel...")
    px = read_pixels()
    st = cell_stats(px)
    print(f"[7f] {len(px):,} pixel, {len(st):,} ô")

    # đối soát với artefact E-DQ7e (pop phải trùng khít từng bit)
    canon = pd.read_parquet(POP_H3)
    j = canon.merge(st[["h3_r8", "pop"]].rename(columns={"pop": "pop_re"}), on="h3_r8")
    max_diff = float((j["pop"] - j["pop_re"]).abs().max())

    com = pd.read_parquet(COMMUNES_PARQUET)
    px = assign_communes(px, com)
    assigned = (px["cidx"] >= 0)
    unassigned_share = float(px.loc[~assigned, "pop"].sum() / px["pop"].sum())

    # tổng WorldPop cấp xã + DANSO
    wp_com = px[assigned].groupby("maxa")["pop"].sum().rename("wp_commune")
    com = com.merge(wp_com, on="maxa", how="left")
    com["wp_commune"] = com["wp_commune"].fillna(0.0)

    # ô -> xã (theo trọng tâm dân số của ô, khớp cách gán pixel)
    cell_com = px[assigned].groupby("h3_r8")["maxa"].agg(
        lambda s: s.value_counts().index[0])
    st = st.merge(cell_com.rename("maxa"), on="h3_r8", how="left")
    cmap = com.set_index("maxa")
    st["danso"] = st["maxa"].map(cmap["danso"])
    st["wp_commune"] = st["maxa"].map(cmap["wp_commune"])

    # D2 — detector cứng (hai điều kiện), cùng khuôn hai-detector E-DQ1
    st["pop_pixel_implausible"] = (
        (st["max_px"] > POP_MAX_PX_IMPLAUSIBLE)
        | ((st["pop"] > POP_PIXEL_IMPLAUSIBLE_MIN_POP)
           & (st["top3_px_share"] > POP_TOP3_SHARE_IMPLAUSIBLE)))
    flagged = st[st["pop_pixel_implausible"]]
    print(f"[7f] POP_PIXEL_IMPLAUSIBLE: {len(flagged)} ô, "
          f"{flagged['pop'].sum():,.0f} người ({flagged['pop'].sum()/st['pop'].sum():.3%})")

    # D3 — phân lớp xã chứa ô bị cờ: RETOTAL nếu WorldPop > 1,5·DANSO
    flagged_maxa = set(flagged["maxa"].dropna())
    com["has_flag"] = com["maxa"].isin(flagged_maxa)
    com["retotal"] = (com["has_flag"] & (com["danso"] > 0)
                      & (com["wp_commune"] > POP_RETOTAL_RATIO * com["danso"]))
    com["affected"] = com["has_flag"]
    n_ret = int(com["retotal"].sum())
    n_rep = int((com["affected"] & ~com["retotal"]).sum())
    print(f"[7f] xã ảnh hưởng: {int(com['affected'].sum())} "
          f"(RETOTAL {n_ret} · REPLACE {n_rep})")

    # D4 — rải lại theo built-up cho từng xã ảnh hưởng
    st["pop_adj"] = st["pop"].astype(float)
    st["pop_src"] = "WORLDPOP"
    aff = com[com["affected"]].reset_index(drop=True)
    new_rows = []          # ô nhận (built-up, trước đó pop=0) chưa có trong bảng
    st_idx = st.set_index("h3_r8")
    unrepaired = 0
    # kế toán khối lượng (độc lập nhãn ô — ô nhận vắt biên thuộc 2 xã nên không thể
    # kiểm bảo toàn theo NHÃN; theo TỔNG thì chính xác): REPLACE cấp lại đúng removed
    # (net 0), chỉ RETOTAL hạ tổng quốc gia đi (removed - target).
    acc = {"retotal_removed": 0.0, "retotal_target": 0.0, "replace_removed": 0.0}
    for _, c in aff.iterrows():
        poly = shapely_wkb.loads(c["geom_wkb"])
        ha = builtup_ha_by_cell(poly)
        maxa = c["maxa"]
        cells_in = st_idx.index[st_idx["maxa"] == maxa].tolist()
        # KHỐI LƯỢNG GỠ RA = tổng pop của đúng những ô sắp bị đưa về 0. REPLACE phải cấp
        # lại ĐÚNG bằng số này (bảo toàn tuyệt đối, không lệ thuộc pixel vắt biên);
        # RETOTAL hạ về 0,859·DANSO (gỡ người ma).
        removed = float(st_idx.loc[cells_in, "pop"].sum())
        target = (POP_WORLDPOP_OVER_DANSO * c["danso"]) if c["retotal"] else removed
        # ô nhận HỢP LỆ: built-up mà (a) là ô của CHÍNH xã này, hoặc (b) ô rỗng chưa ai
        # nhận. Ô populated thuộc xã KHÁC bị loại -> không rò khối lượng sang hàng xóm.
        recv = {cc: h for cc, h in ha.items()
                if (cc not in st_idx.index) or (st_idx.at[cc, "maxa"] == maxa)}
        tot_ha = sum(recv.values())
        if tot_ha <= 0:                       # không có built-up -> không rải được
            for cc in cells_in:
                if st_idx.at[cc, "pop_pixel_implausible"]:
                    st_idx.at[cc, "pop_src"] = "UNREPAIRED_NO_BUILTUP"
                    unrepaired += 1
            continue
        if c["retotal"]:
            acc["retotal_removed"] += removed
            acc["retotal_target"] += target
        else:
            acc["replace_removed"] += removed
        src = "RETOTALED_DANSO" if c["retotal"] else "REDISTRIBUTED"
        for cc in cells_in:                   # về 0 trước, rồi cấp lại theo built-up
            st_idx.at[cc, "pop_adj"] = 0.0
            st_idx.at[cc, "pop_src"] = src
        for cc, h in recv.items():
            share = target * h / tot_ha
            if cc in st_idx.index:
                st_idx.at[cc, "pop_adj"] = share
                st_idx.at[cc, "pop_src"] = src
            else:
                new_rows.append({"h3_r8": cc, "pop": 0.0, "pop_adj": share,
                                 "pop_src": src, "maxa": maxa})
    if new_rows:
        # ô nhận vắt biên hai xã có thể xuất hiện 2 lần (mỗi polygon đọc built-up riêng)
        # -> gộp theo h3, CỘNG pop_adj (ô trải trên cả hai xã, khối lượng mỗi bên đúng).
        add = (pd.DataFrame(new_rows)
               .groupby("h3_r8", as_index=False)
               .agg(pop=("pop", "first"), pop_adj=("pop_adj", "sum"),
                    pop_src=("pop_src", "first"), maxa=("maxa", "first")))
        # ô nhận trùng ô đã có -> CỘNG vào (không drop: giữ bảo toàn khối lượng),
        # phần còn lại là hàng mới.
        hit = add["h3_r8"].isin(st_idx.index)
        for _, rw in add[hit].iterrows():
            st_idx.at[rw["h3_r8"], "pop_adj"] += rw["pop_adj"]
        add = add[~hit]
    st = st_idx.reset_index()
    if new_rows and len(add):
        for col in st.columns:
            if col not in add.columns:
                add[col] = np.nan
        add["pop_pixel_implausible"] = False
        st = pd.concat([st, add[st.columns]], ignore_index=True)
    print(f"[7f] ô nhận mới (built-up, pop=0): {len(new_rows)} · ô hỏng không rải được: {unrepaired}")

    # đóng gói + kiểu
    st["pop_pixel_implausible"] = st["pop_pixel_implausible"].fillna(False).astype(bool)
    diag = ["n_px", "max_px", "top3_px_share", "n_eff", "pop_per_eff_px",
            "pop_lat", "pop_lon"]
    out_cols = (["h3_r8", "pop", "pop_adj", "pop_src", "pop_pixel_implausible",
                 "maxa", "danso"] + diag)
    st = st[out_cols].sort_values("pop", ascending=False).reset_index(drop=True)

    report = {"pixels": len(px), "cells": int(len(st)),
              "flagged_cells": int(len(flagged)),
              "flagged_pop": float(flagged["pop"].sum()),
              "communes_affected": int(com["affected"].sum()),
              "communes_retotal": n_ret, "communes_replace": n_rep,
              "receiver_cells": len(new_rows), "unrepaired_cells": unrepaired,
              "checks": []}
    report["planned_retotal_reduction"] = float(acc["retotal_removed"] - acc["retotal_target"])
    print("\n[7f] cổng QA:")
    ok = qa_gates(report, st, canon, com, max_diff, unassigned_share, acc)
    report["overall"] = "PASS" if ok else "FAIL"
    report["pop_total"] = float(canon["pop"].sum())
    report["pop_adj_total"] = float(st["pop_adj"].sum())
    POP_ADJ_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    if not ok:
        print(f"\n[FAIL] -> {POP_ADJ_REPORT} (KHÔNG ghi {POP_ADJ_H3.name})", file=sys.stderr)
        sys.exit(1)
    st.to_parquet(POP_ADJ_H3, index=False)
    print(f"\n[PASS] -> {POP_ADJ_REPORT}")
    print(f"[7f] -> {POP_ADJ_H3}  (Σpop {report['pop_total']/1e6:.3f}M "
          f"-> Σpop_adj {report['pop_adj_total']/1e6:.3f}M, "
          f"{(report['pop_adj_total']/report['pop_total']-1):+.3%})")
    return st


def qa_gates(report, st, canon, com, max_diff, unassigned_share, acc):
    """6 cổng E-DQ7f — mỗi cổng canh một giả định, và FAIL được."""
    all_ok = True
    pop_total = float(st["pop"].sum())
    pop_adj_total = float(st["pop_adj"].sum())

    # ① `pop` bất biến từng bit so artefact E-DQ7e (không đụng cột UN-anchored)
    same = set(canon["h3_r8"]) <= set(st["h3_r8"])
    all_ok &= _check(report, "pop_bit_invariant", max_diff < 1e-6 and same,
                     f"max|pop_re - pop| = {max_diff:.2e}; giữ đủ ô = {same}")

    # ② mọi ô pixel-bất-khả-thi ĐỀU có cờ (không lọt cổng đo bằng đại lượng vô can)
    unflagged = int(((st["max_px"] > POP_MAX_PX_IMPLAUSIBLE)
                     & ~st["pop_pixel_implausible"]).sum())
    all_ok &= _check(report, "no_unflagged_implausible_pixel", unflagged == 0,
                     f"{unflagged} ô max_px>1000 không cờ")

    # ③ khối lượng bị cờ < 1% (hiện ~0,76%)
    fp = float(st.loc[st["pop_pixel_implausible"], "pop"].sum())
    all_ok &= _check(report, "flagged_mass_share_lt_1pct", fp / pop_total < 0.01,
                     f"{fp:,.0f} người ({fp / pop_total:.3%})")

    # ④ RETOTAL chỉ được HẠ, không bịa người (kế toán theo TỔNG, độc lập nhãn ô)
    red = acc["retotal_removed"] - acc["retotal_target"]
    all_ok &= _check(report, "retotal_reduces_mass", red >= -1e-6,
                     f"gỡ {red:,.0f} người ma (removed {acc['retotal_removed']:,.0f} "
                     f"- target {acc['retotal_target']:,.0f}) — phải ≥ 0")

    # ⑤ bảo toàn TỔNG: Σpop_adj = Σpop − (removed_retotal − target_retotal). REPLACE
    #    net 0, RETOTAL hạ đúng phần người ma. Chính xác từng người, không lệ nhãn ô.
    expect = pop_total - red
    resid = abs(pop_adj_total - expect)
    all_ok &= _check(report, "global_mass_accounted", resid < 1.0,
                     f"|Σpop_adj − kỳ vọng| = {resid:.3f} người "
                     f"(Σpop_adj {pop_adj_total:,.0f} vs {expect:,.0f})")

    # ⑥ trôi tổng quốc gia của pop_adj < 1% (người ma gỡ khỏi đảo là có chủ ý)
    drift = abs(pop_adj_total - pop_total) / pop_total
    all_ok &= _check(report, "pop_adj_national_drift_lt_1pct", drift < 0.01,
                     f"trôi {drift:.3%} (= {red:,.0f} người ma / {pop_total:,.0f})")

    # ⑦ (advisory) độ phủ join pixel->xã
    _check(report, "commune_join_coverage", unassigned_share < 0.01,
           f"pixel không gán được = {unassigned_share:.3%}", fatal=False)
    return all_ok


if __name__ == "__main__":
    run()
