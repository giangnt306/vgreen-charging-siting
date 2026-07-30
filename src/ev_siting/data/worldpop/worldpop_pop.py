#!/usr/bin/env python3
"""worldpop_pop.py — Dân số WorldPop VN (~100m) -> pop theo ô H3 res 8.

Tải raster GeoTIFF `vnm_ppp_2020_UNadj_constrained.tif` (Global 2000-2020 Constrained,
built-settlement aware, ~100m, **UN-adjusted**, CC-BY) rồi đọc theo **cửa sổ (block)**
để RAM bị giới hạn, gộp dân số từng pixel về ô H3 của tâm pixel.

  pop = tổng số dân (WorldPop = số người/pixel) rơi vào ô H3 res 8.

**E-DQ7e — hiệu chuẩn tuyệt đối (chốt 2026-07-29).** Bản dùng trước đây là
UN-**unadjusted**: tổng 99,627 M so với 97,569 M của bản UNadj (**+2,11%**), làm sai mọi
phát biểu tuyệt đối (`coverage_pop`, đối chiếu GSO). Đo trên từng pixel, tỉ số
UNadj/unadjusted là **hằng số quốc gia 0,979344** (std **2,5e-08**) ⇒ **thứ hạng ô bất
biến từng bit**, nên đổi nguồn KHÔNG đụng tới MCLP/`demand_weight`. Ba cổng QA ở dưới
canh đúng ba giả định đó, và cả ba đều FAIL được.

⚠️ E-DQ7e **không** sửa việc `pop` bị dồn cục **trong** ô (146 ô / 792.118 dân nằm trên
1–5 pixel) — đó là `E-DQ7f`, một vấn đề khác hẳn: nó **có** xê dịch thứ hạng.

**Hai niên đại (Q6iii).** `--vintage 2020` dựng `pop` UNadj ở trên và đi qua đủ ba cổng
E-DQ7e; `--vintage 2025` dựng thêm `worldpop_pop_2025_h3` (R2024B, mặt nạ công trình
mới) cho cột SENSITIVITY `pop_2025` — trọng tài hạ tầng OSM cho thấy mặt nạ 2020 gán
pop=0 cho **60,3% số ô có đường** (audit 29/07), nên giữ 2025 song song để ĐO độ nhạy
mặt nạ thay vì chọn mù; neo xếp hạng vẫn là `pop`/`pop_adj` 2020. Bản 2025 không có bản
unadjusted đối chứng lẫn tổng đã checksum ⇒ các cổng E-DQ7e không áp được cho nó.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop            # cả hai niên đại
    PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop --vintage 2025
    PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop --force-download
"""
import argparse
import json
import sys

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

from .paths import (H3_RES_R8, POP_H3, POP_REPORT, POP_SOURCES, POP_TIF,
                    POP_TIF_UNADJUSTED, POP_TOTAL_EXPECTED, POP_TOTAL_TOL,
                    POP_UNADJ_RATIO, POP_UNADJ_RATIO_STD_MAX, WORLDPOP_URL,
                    ensure_dirs, resolve_tif)
import h3

ROW_BLOCK = 512   # số hàng đọc mỗi cửa sổ (cân bằng RAM/tốc độ)


def download_tif(vintage="2020", force=False):
    import requests
    tif, _, url = POP_SOURCES[vintage]
    have = resolve_tif(vintage)
    if have.exists() and have.stat().st_size > 0 and not force:
        print(f"[tif] đã có {have} ({have.stat().st_size/1e6:.0f} MB) — bỏ qua tải")
        return
    print(f"[tif] tải {url} ...")
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        got = 0
        tmp = tif.with_suffix(".tif.part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                got += len(chunk)
                if total:
                    print(f"\r      {got/1e6:5.0f}/{total/1e6:.0f} MB", end="", file=sys.stderr)
        print("", file=sys.stderr)
        # tải đứt nửa chừng phải nổ NGAY tại đây, không để raster cụt lọt vào pipeline
        if total and got != total:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"GeoTIFF tải thiếu: got={got:,}, expected={total:,}")
        tmp.replace(tif)
    print(f"[tif] xong -> {tif} ({tif.stat().st_size/1e6:.0f} MB)")


def aggregate_to_h3(tif):
    """Đọc raster theo strip, gộp pop về ô H3 res 8. Trả về DataFrame(h3_r8, pop)."""
    agg = {}          # h3_r8 -> pop tích luỹ
    total_pop = 0.0
    with rasterio.open(tif) as src:
        nodata = src.nodata
        H, W = src.height, src.width
        t = src.transform
        print(f"[pop] raster {W}x{H}, nodata={nodata}, CRS={src.crs}")
        # toạ độ tâm pixel: lon phụ thuộc col, lat phụ thuộc row (raster north-up)
        col_idx = np.arange(W)
        lon_row = t.c + t.a * (col_idx + 0.5)     # 1D theo cột (dùng lại mỗi strip)
        for r0 in range(0, H, ROW_BLOCK):
            rows = min(ROW_BLOCK, H - r0)
            arr = src.read(1, window=Window(0, r0, W, rows))
            mask = np.isfinite(arr) & (arr > 0)
            if nodata is not None:
                mask &= (arr != nodata)
            if not mask.any():
                continue
            rr, cc = np.nonzero(mask)             # chỉ số local trong strip
            vals = arr[rr, cc].astype(np.float64)
            lats = t.f + t.e * ((r0 + rr) + 0.5)  # t.e âm (north-up)
            lons = lon_row[cc]
            cells = [h3.latlng_to_cell(la, lo, H3_RES_R8)
                     for la, lo in zip(lats, lons)]
            grp = pd.Series(vals).groupby(cells).sum()
            for cell, p in grp.items():
                agg[cell] = agg.get(cell, 0.0) + p
            total_pop += vals.sum()
            print(f"\r      hàng {r0+rows}/{H}  ({len(agg)} ô, ~{total_pop/1e6:.1f}M người)",
                  end="", file=sys.stderr)
        print("", file=sys.stderr)
    df = pd.DataFrame(agg.items(), columns=["h3_r8", "pop"])
    df = df.sort_values("pop", ascending=False).reset_index(drop=True)
    return df, total_pop


def _check(report, name, ok, detail="", fatal=True):
    status = "PASS" if ok else ("FAIL" if fatal else "WARN")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name} {('- ' + detail) if detail else ''}")
    return ok or not fatal


def pixel_ratio_vs_unadjusted():
    """Tỉ số UNadj/unadjusted theo TỪNG pixel (E-DQ7e).

    Đây là bằng chứng của khẳng định "hiệu chuẩn UN là một vô hướng quốc gia, thứ hạng ô
    bất biến" — khẳng định mà `E-DQ7d` dựa vào để chạy TRƯỚC `E-DQ7e`. Trả None nếu bản
    unadjusted không còn trên đĩa (cổng chuyển sang WARN thay vì im lặng bỏ qua).
    """
    if not POP_TIF_UNADJUSTED.exists():
        return None
    with rasterio.open(POP_TIF) as a, rasterio.open(POP_TIF_UNADJUSTED) as b:
        if (a.width, a.height) != (b.width, b.height) or a.transform != b.transform:
            return {"grid_mismatch": True}
        lo, hi, n = np.inf, -np.inf, 0
        s = s2 = 0.0
        for r0 in range(0, a.height, ROW_BLOCK):
            rows = min(ROW_BLOCK, a.height - r0)
            w = Window(0, r0, a.width, rows)
            x = a.read(1, window=w).astype(np.float64)
            y = b.read(1, window=w).astype(np.float64)
            # chỉ so trên pixel có dân ở bản unadjusted (mẫu số > 0)
            m = np.isfinite(y) & (y > 0.01) & (y != b.nodata)
            if not m.any():
                continue
            r = x[m] / y[m]
            lo, hi = min(lo, float(r.min())), max(hi, float(r.max()))
            s += float(r.sum())
            s2 += float((r * r).sum())
            n += int(r.size)
        mean = s / max(n, 1)
        var = max(s2 / max(n, 1) - mean * mean, 0.0)
        return {"n_pixels": n, "min": lo, "max": hi, "mean": mean, "std": var ** 0.5}


def qa_gates(report, df, total, prev, ratio):
    """3 cổng của E-DQ7e. Mỗi cổng canh MỘT giả định cụ thể, và FAIL được:

    ① tổng khớp file UNadj đã checksum  -> bắt việc tải nhầm lại bản unadjusted
    ② thứ hạng ô bất biến               -> bắt mọi "hiệu chuẩn" phi tuyến lén lút
    ③ tỉ số theo pixel là hằng số       -> bắt WorldPop đổi cách UNadj ở phiên bản sau
    """
    all_ok = True
    dev = abs(total - POP_TOTAL_EXPECTED) / POP_TOTAL_EXPECTED
    all_ok &= _check(report, "pop_total_matches_unadj", dev <= POP_TOTAL_TOL,
                     f"Σpop {total:,.0f} vs UNadj {POP_TOTAL_EXPECTED:,.0f} "
                     f"(lệch {dev:.2e}, trần {POP_TOTAL_TOL:.0e})")

    # ② so với artefact TRƯỚC khi ghi đè. Ở lần migrate 7e, `prev` là bản dẫn từ raster
    #    unadjusted -> đây chính là phép đo chứng minh "đổi nguồn không đổi thứ hạng".
    if prev is None:
        # KHÔNG báo PASS: cổng không chạy được thì phải nói thế, nếu không nó thành cổng
        # "không bao giờ FAIL" — đúng lỗi mà E-DQ7a/E-DQ7c đã phải sửa.
        all_ok &= _check(report, "pop_rank_invariant", False,
                         "chưa có artefact trước — KHÔNG kiểm được (lần dựng đầu)",
                         fatal=False)
    else:
        same_cells = set(prev["h3_r8"]) == set(df["h3_r8"])
        j = prev.rename(columns={"pop": "pop_prev"}).merge(df, on="h3_r8", how="inner")
        rho = float(j["pop_prev"].corr(j["pop"], method="spearman"))
        # in đủ 9 chữ số: winsorize đỉnh phân vị chỉ kéo rho xuống ~1e-10, làm tròn 6
        # chữ số sẽ hiện "1,000000" ngay trên một dòng FAIL -> đọc log thành mâu thuẫn.
        all_ok &= _check(report, "pop_rank_invariant",
                         same_cells and rho >= 1.0 - 1e-12,
                         f"Spearman(pop cũ, pop mới) = {rho:.9f} (1−ρ = {1.0 - rho:.2e}) "
                         f"trên {len(j):,} ô; "
                         f"tập ô {'trùng khít' if same_cells else 'ĐÃ ĐỔI'} "
                         f"({len(prev):,} -> {len(df):,})")

    # ③ bằng chứng đơn điệu — không có bản unadjusted trên đĩa thì KHÔNG coi là PASS
    if ratio is None:
        all_ok &= _check(report, "pop_scale_ratio_is_constant", False,
                         f"thiếu {POP_TIF_UNADJUSTED.name} — KHÔNG kiểm chứng được "
                         f"tính đơn điệu (E-DQ7d dựa vào nó)", fatal=False)
    elif ratio.get("grid_mismatch"):
        all_ok &= _check(report, "pop_scale_ratio_is_constant", False,
                         "hai raster khác lưới/transform — không so pixel được")
    else:
        all_ok &= _check(report, "pop_scale_ratio_is_constant",
                         ratio["std"] < POP_UNADJ_RATIO_STD_MAX,
                         f"tỉ số {ratio['min']:.6f}–{ratio['max']:.6f} "
                         f"(trung bình {ratio['mean']:.6f}, std {ratio['std']:.1e}, "
                         f"kỳ vọng {POP_UNADJ_RATIO}) trên {ratio['n_pixels']:,} pixel")
    return all_ok


def run(vintage="2020", force_download=False):
    ensure_dirs()
    download_tif(vintage, force=force_download)
    tif = resolve_tif(vintage)
    if vintage != "2020":
        # 2025 (R2024B): không có bản unadjusted đối chứng lẫn tổng đã checksum ⇒ các
        # cổng E-DQ7e không áp được; artefact chỉ nuôi cột sensitivity `pop_2025`.
        out = POP_SOURCES[vintage][1]
        print(f"[pop] {vintage}: gộp {tif.name} -> H3 res 8...")
        df, total = aggregate_to_h3(tif)
        df.to_parquet(out, index=False)
        print(f"[pop] -> {out}  ({len(df)} ô, tổng {total/1e6:.2f}M người)")
        return df
    prev = pd.read_parquet(POP_H3) if POP_H3.exists() else None
    print("[pop] gộp raster -> H3 res 8...")
    df, total = aggregate_to_h3(tif)

    print("[pop] so pixel với bản unadjusted (E-DQ7e)...")
    ratio = pixel_ratio_vs_unadjusted()

    report = {"source_raster": POP_TIF.name, "source_url": WORLDPOP_URL,
              "cells": int(len(df)), "pop_total": float(total),
              "ratio_vs_unadjusted": ratio, "checks": []}
    print("\n[pop] cổng QA (E-DQ7e):")
    ok = qa_gates(report, df, total, prev, ratio)
    report["overall"] = "PASS" if ok else "FAIL"
    POP_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                          encoding="utf-8")

    if not ok:
        print(f"\n[FAIL] -> {POP_REPORT} (KHÔNG ghi đè {POP_H3.name})", file=sys.stderr)
        sys.exit(1)
    df.to_parquet(POP_H3, index=False)
    print(f"\n[PASS] -> {POP_REPORT}")
    print(f"[pop] -> {POP_H3}  ({len(df)} ô, tổng {total/1e6:.2f}M người)")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--vintage", choices=[*POP_SOURCES, "all"], default="all")
    ap.add_argument("--force-download", action="store_true")
    args = ap.parse_args()
    for v in (POP_SOURCES if args.vintage == "all" else [args.vintage]):
        run(vintage=v, force_download=args.force_download)
