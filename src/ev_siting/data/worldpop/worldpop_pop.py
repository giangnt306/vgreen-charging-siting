#!/usr/bin/env python3
"""worldpop_pop.py — Dân số WorldPop VN 2020 (~100m) -> pop theo ô H3 res 8.

Tải raster GeoTIFF `vnm_ppp_2020_constrained.tif` (Global 2000-2020 Constrained,
built-settlement aware, ~100m, CC-BY) rồi đọc theo **cửa sổ (block)** để RAM bị
giới hạn, gộp dân số từng pixel về ô H3 của tâm pixel.

  pop = tổng số dân (WorldPop = số người/pixel) rơi vào ô H3 res 8.

Chạy:
    PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop
    PYTHONPATH=src python -m ev_siting.data.worldpop.worldpop_pop --force-download
"""
import argparse
import sys

import h3
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

from .paths import H3_RES_R8, POP_H3, POP_TIF, WORLDPOP_URL, ensure_dirs

ROW_BLOCK = 512   # số hàng đọc mỗi cửa sổ (cân bằng RAM/tốc độ)


def download_tif(force=False):
    import requests
    if POP_TIF.exists() and POP_TIF.stat().st_size > 0 and not force:
        print(f"[tif] đã có {POP_TIF.name} ({POP_TIF.stat().st_size/1e6:.0f} MB) — bỏ qua tải")
        return
    print(f"[tif] tải {WORLDPOP_URL} ...")
    with requests.get(WORLDPOP_URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        got = 0
        tmp = POP_TIF.with_suffix(".tif.part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                got += len(chunk)
                if total:
                    print(f"\r      {got/1e6:5.0f}/{total/1e6:.0f} MB", end="", file=sys.stderr)
        print("", file=sys.stderr)
        tmp.replace(POP_TIF)
    print(f"[tif] xong -> {POP_TIF} ({POP_TIF.stat().st_size/1e6:.0f} MB)")


def aggregate_to_h3():
    """Đọc raster theo strip, gộp pop về ô H3 res 8. Trả về DataFrame(h3_r8, pop)."""
    agg = {}          # h3_r8 -> pop tích luỹ
    total_pop = 0.0
    with rasterio.open(POP_TIF) as src:
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


def run(force_download=False):
    ensure_dirs()
    download_tif(force=force_download)
    print("[pop] gộp raster -> H3 res 8...")
    df, total = aggregate_to_h3()
    df.to_parquet(POP_H3, index=False)
    print(f"[pop] -> {POP_H3}  ({len(df)} ô, tổng {total/1e6:.2f}M người)")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-download", action="store_true")
    args = ap.parse_args()
    run(force_download=args.force_download)
