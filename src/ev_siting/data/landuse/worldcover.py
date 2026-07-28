#!/usr/bin/env python3
"""worldcover.py — ESA WorldCover 10 m -> tỷ lệ lớp phủ theo ô H3 res 8.

Vì sao cần: OSM land-use ở VN rất thưa — "không có polygon nước" **không** có nghĩa
là đất khô. Dùng raster lớp phủ toàn phủ (ESA WorldCover 10 m, CC-BY 4.0) làm **nền
chính** cho bộ lọc khả thi (P5); OSM chỉ bổ sung military/protected mà raster không có.

Cơ chế (giống worldpop_pop.py — đọc raster theo cửa sổ để giới hạn RAM):
  - Xác định các ô tile 3°x3° phủ AOI, tải từng tile về data/raw/landuse/worldcover/.
  - Đọc theo strip, gán mỗi pixel 10 m về ô H3 res 8 của tâm pixel.
  - Với mỗi ô H3: đếm pixel theo nhóm lớp (built/water/tree/...) -> **tỷ lệ**.

Output: data/interim/landuse/landuse_h3.parquet
  cột: h3_r8, n_px, frac_built, frac_water, frac_wetland, frac_tree, frac_shrub,
       frac_grass, frac_crop, frac_bare, built_up_frac (= frac_built).

Chạy:
    PYTHONPATH=src python -m ev_siting.data.landuse.worldcover --city hanoi
"""
import argparse
import math
import sys
import time

import h3
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

from ev_siting.aoi import add_aoi_args, aoi_from_args

from .paths import (
    H3_RES_R8,
    LANDUSE_H3,
    WC_BASE_URL,
    WC_CLASS_GROUP,
    WC_GROUPS,
    WC_TILE_DEG,
    WC_TILE_DIR,
    WC_VERSION,
    WC_YEAR,
    ensure_dirs,
)

ROW_BLOCK = 1024  # số hàng đọc mỗi cửa sổ (WorldCover ~36000 px/tile)


def _tile_origin(deg, size):
    """Toạ độ góc dưới-trái của ô tile chứa `deg` (bội số của `size`)."""
    return int(math.floor(deg / size) * size)


def _tile_name(lat0, lon0):
    """Tên tile WorldCover, ví dụ N21E105 (góc dưới-trái)."""
    ns = f"{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}"
    ew = f"{'E' if lon0 >= 0 else 'W'}{abs(lon0):03d}"
    return f"{ns}{ew}"


def tiles_for_bbox(bbox):
    """Danh sách (lat0, lon0) các tile 3° phủ bbox=(s, w, n, e)."""
    s, w, n, e = bbox
    out = []
    lat0 = _tile_origin(s, WC_TILE_DEG)
    while lat0 <= n:
        lon0 = _tile_origin(w, WC_TILE_DEG)
        while lon0 <= e:
            out.append((lat0, lon0))
            lon0 += WC_TILE_DEG
        lat0 += WC_TILE_DEG
    return out


def download_tile(lat0, lon0, force=False):
    """Tải 1 tile WorldCover (idempotent). Trả về path .tif, hoặc None nếu tile
    không tồn tại (ô 3° toàn biển → WorldCover không phát hành → HTTP 404)."""
    name = _tile_name(lat0, lon0)
    fn = f"ESA_WorldCover_10m_{WC_YEAR}_{WC_VERSION}_{name}_Map.tif"
    dst = WC_TILE_DIR / fn
    if dst.exists() and dst.stat().st_size > 0 and not force:
        print(f"[wc] đã có {name} ({dst.stat().st_size/1e6:.0f} MB) — bỏ qua tải")
        return dst
    import requests
    url = f"{WC_BASE_URL}/{fn}"
    print(f"[wc] tải {name} <- {url}")
    # 18 tile lớn qua mạng chập chờn -> retry với backoff (reset/timeout là thường gặp).
    tries = 5
    for attempt in range(tries):
        try:
            with requests.get(url, stream=True, timeout=600) as r:
                if r.status_code == 404:
                    print(f"[wc] {name}: 404 (ô toàn biển) — bỏ qua")
                    return None
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                got = 0
                tmp = dst.with_suffix(".tif.part")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
                        got += len(chunk)
                        if total:
                            print(f"\r      {got/1e6:5.0f}/{total/1e6:.0f} MB", end="", file=sys.stderr)
                print("", file=sys.stderr)
                if total and got < total:
                    raise IOError(f"tải thiếu {got}/{total} byte")
                tmp.replace(dst)
            print(f"[wc] xong -> {dst.name} ({dst.stat().st_size/1e6:.0f} MB)")
            return dst
        except (requests.RequestException, IOError) as e:
            wait = 10 * (attempt + 1)
            print(f"\n[wc] ! {name} lỗi tải ({type(e).__name__}); thử lại sau {wait}s "
                  f"({attempt+1}/{tries})", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"[wc] tải {name} thất bại sau {tries} lần")


def _accumulate_tile(tif_path, aoi, counts, stride=1):
    """Đọc 1 tile trong cửa sổ AOI, cộng dồn đếm pixel theo (h3, group) vào `counts`.

    `stride` > 1 → chỉ lấy mỗi `stride` pixel theo mỗi chiều (giảm khối lượng
    gán H3 `stride²` lần). Cần cho national: full VN ~3,3 tỉ pixel đất, gán H3
    từng pixel là bất khả thi; stride=8 (~80 m) vẫn cho ~130 mẫu/ô res 8 → đủ để
    ước lượng tỷ lệ lớp phủ ổn định.
    """
    s, w, n, e = aoi.bbox()
    with rasterio.open(tif_path) as src:
        try:
            win = from_bounds(w, s, e, n, src.transform)
        except Exception:
            return
        win = win.round_offsets().round_lengths()
        # cắt cửa sổ về trong ảnh
        col_off = max(0, int(win.col_off))
        row_off = max(0, int(win.row_off))
        width = min(src.width - col_off, int(win.width))
        height = min(src.height - row_off, int(win.height))
        if width <= 0 or height <= 0:
            return
        t = src.transform
        col_idx = np.arange(col_off, col_off + width, stride)
        lon_row = t.c + t.a * (col_idx + 0.5)
        for r0 in range(row_off, row_off + height, ROW_BLOCK):
            rows = min(ROW_BLOCK, row_off + height - r0)
            arr = src.read(1, window=rasterio.windows.Window(col_off, r0, width, rows))
            arr = arr[::stride, ::stride]                 # downsample block
            row_local = np.arange(0, rows, stride)        # khớp hàng đã lấy mẫu
            valid = arr > 0
            if not valid.any():
                continue
            rr, cc = np.nonzero(valid)
            vals = arr[rr, cc]
            lats = t.f + t.e * ((r0 + row_local[rr]) + 0.5)
            lons = lon_row[cc]
            # chỉ giữ pixel trong AOI, tránh đếm thừa ở góc bbox
            in_aoi = np.asarray(aoi.contains(lats, lons))
            if not in_aoi.any():
                continue
            lats, lons, vals = lats[in_aoi], lons[in_aoi], vals[in_aoi]
            cells = [h3.latlng_to_cell(la, lo, H3_RES_R8) for la, lo in zip(lats, lons)]
            groups = np.array([WC_CLASS_GROUP.get(int(v), "bare") for v in vals])
            df = pd.DataFrame({"h3_r8": cells, "grp": groups})
            grp = df.groupby(["h3_r8", "grp"]).size()
            for (cell, g), cnt in grp.items():
                d = counts.setdefault(cell, {})
                d[g] = d.get(g, 0) + int(cnt)


def build(aoi, force_download=False, stride=1):
    ensure_dirs()
    tiles = tiles_for_bbox(aoi.bbox())
    print(f"[wc] {aoi} -> {len(tiles)} tile (stride={stride}): {[_tile_name(*t) for t in tiles]}")
    counts: dict[str, dict[str, int]] = {}
    for lat0, lon0 in tiles:
        path = download_tile(lat0, lon0, force=force_download)
        if path is None:
            continue                       # ô toàn biển (404) — bỏ qua
        print(f"[wc] gộp {_tile_name(lat0, lon0)} -> H3...")
        _accumulate_tile(path, aoi, counts, stride=stride)
        print(f"      luỹ kế {len(counts)} ô")

    rows = []
    for cell, gc in counts.items():
        n_px = sum(gc.values())
        row = {"h3_r8": cell, "n_px": n_px}
        for g in WC_GROUPS:
            row[f"frac_{g}"] = gc.get(g, 0) / n_px if n_px else 0.0
        rows.append(row)
    df = pd.DataFrame(rows).sort_values("h3_r8").reset_index(drop=True)
    df["built_up_frac"] = df["frac_built"]
    df.to_parquet(LANDUSE_H3, index=False)
    print(f"[wc] -> {LANDUSE_H3}  ({len(df)} ô)")
    if len(df):
        print("  TB tỷ lệ:", {g: round(float(df[f'frac_{g}'].mean()), 3) for g in WC_GROUPS})
    return df


def run(args=None):
    ap = argparse.ArgumentParser(description="ESA WorldCover -> land-cover fractions theo H3")
    add_aoi_args(ap)
    ap.add_argument("--force-download", action="store_true")
    ap.add_argument("--stride", type=int, default=None,
                    help="lấy mẫu mỗi N pixel (mặc định: 1 cho city, 8 cho national)")
    a = ap.parse_args(args)
    aoi = aoi_from_args(a)
    stride = a.stride if a.stride else (8 if getattr(a, "national", False) else 1)
    build(aoi, force_download=a.force_download, stride=stride)


if __name__ == "__main__":
    run()
