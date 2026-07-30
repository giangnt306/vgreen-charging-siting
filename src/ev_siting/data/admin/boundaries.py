#!/usr/bin/env python3
"""boundaries.py — E-DQ3: lớp ranh giới hành chính dùng chung (điểm & ô).

Một nguồn (VNSDI cấp xã — xem `paths.py`), **hai phép gán khác nhau về bản chất**:

┌─ ĐIỂM (trạm sạc) → `assign_points` ────────────────────────────────────────────────┐
Toạ độ có lãnh thổ XÁC ĐỊNH: point-in-polygon, không mơ hồ. Đo trên 19.507 trạm
canonical: **0 trạm** rơi vào >1 polygon xã (lớp phủ kín, không chồng lấn). Điểm rơi ra
ngoài mọi xã thì snap về xã gần nhất trong `ADMIN_SNAP_TOL_M` (tổng quát hoá 1:1M), xa
hơn thì **không đoán** — trả `admin_src='none'` để E-DQ3 gắn cờ toạ độ.

┌─ Ô H3 (demand_h3) → `cell_overlaps` ───────────────────────────────────────────────┐
Ô là DIỆN TÍCH, không phải điểm ⇒ hai khác biệt bắt buộc, cả hai đều đo được:

  1. **LỤC GIÁC ∩ POLYGON, không phải TÂM Ô ∈ POLYGON** — đúng bài học E-DQ7a. Đo trên
     lưới hiện tại (255.480 ô): test theo tâm ô bỏ sót **2.926 ô / 475.083 người** mà
     lục giác của chúng CÓ chạm xã. Cùng một ranh giới, hai kết quả khác nhau.
  2. **Nhãn ≠ phân bổ.** **61.649 ô (40,0% dân số, tối đa 6 xã/ô)** vắt qua >1 xã. Một
     cột `commune_name` vô hướng là **NHÃN** (argmax diện tích), KHÔNG phải phép chia
     khối lượng — `groupby(nhãn).sum()` cho rollup cấp tỉnh/xã sẽ sai hàng chục triệu
     người. Vì vậy module trả bảng LONG có trọng số; nhãn chỉ là một cột dẫn xuất.

Trọng số phân bổ `w` được **chuẩn hoá theo ô** (Σw = 1 trên mỗi ô có chạm xã) chứ không
phải tỉ lệ diện tích thô: ô vắt biên giới quốc gia có phần nằm ngoài VN/trên biển, và
khối lượng của phần đó vẫn thuộc về xã đã đo được nó. Chuẩn hoá = **bảo toàn khối lượng
tuyệt đối** (cổng kế toán mới kiểm được), tỉ lệ thô giữ riêng ở `admin_frac` làm tín hiệu
độ tin của NHÃN.

Diện tích tính trong **độ²** (WGS84) chứ không đổi sang mét: mọi phép so ở đây là **tỉ số
trong CÙNG một ô** (đường kính ~0,01°), nên hệ số méo theo vĩ độ triệt tiêu hết. Đổi hệ
toạ độ chỉ thêm phụ thuộc mà không đổi một chữ số nào.
"""
from functools import lru_cache

import numpy as np
import pandas as pd
import shapely
from shapely import STRtree, points, polygons
from shapely import wkb as shapely_wkb

import h3

from ..vnsdi.paths import COMMUNES_PARQUET
from .paths import ADMIN_SNAP_TOL_M

#: 1 độ vĩ ~ 111,32 km — chỉ dùng để đổi ngưỡng snap ra độ (bậc độ lớn, không phải phép
#: đo chính xác: sai số cos(vĩ độ) ở VN <= 8% trên một ngưỡng vốn có dải rỗng 5,6 lần).
DEG_PER_M = 1.0 / 111_320.0

#: Tiền tố loại đơn vị trong `TENXA` -> `commune_kind`. Cải cách 2025 bỏ hẳn `Thị trấn`
#: (đo được: Xã 2.621 · Phường 687 · Đặc khu 13 — không còn loại nào khác).
KIND_PREFIX = {"Phường": "PHUONG", "Xã": "XA", "Đặc khu": "DAC_KHU"}

#: Cột nhãn hành chính (khai báo ở schema-contract) + khoá join thật (`commune_code`).
#: `commune_name`/`province_name` giữ NGUYÊN VĂN chuỗi nguồn (không cắt tiền tố) — không
#: huỷ thông tin; loại đơn vị tách ra `commune_kind` cho ai cần lọc.
LABEL_COLS = ["admin_l1_code", "province_name", "commune_code", "commune_name",
              "commune_kind"]


def _kind(tenxa: str) -> str:
    for pref, kind in KIND_PREFIX.items():
        if str(tenxa).startswith(pref + " "):
            return kind
    return "UNKNOWN"


@lru_cache(maxsize=1)
def load_communes() -> pd.DataFrame:
    """3.321 xã VNSDI + `geometry` (shapely) + `commune_kind`. Cache theo tiến trình."""
    if not COMMUNES_PARQUET.exists():
        raise SystemExit(f"thiếu {COMMUNES_PARQUET} — chạy `make vnsdi` (E-DQ7f) trước")
    df = pd.read_parquet(COMMUNES_PARQUET)
    df = df.rename(columns={"maxa": "commune_code", "tenxa": "commune_name",
                            "matinh": "admin_l1_code", "tentinh": "province_name"})
    df["commune_kind"] = df["commune_name"].map(_kind)
    df["geometry"] = [shapely_wkb.loads(b) for b in df["geom_wkb"]]
    return df[LABEL_COLS + ["dientich_km2", "danso", "geometry"]].reset_index(drop=True)


@lru_cache(maxsize=1)
def _tree():
    com = load_communes()
    return STRtree(com["geometry"].to_numpy()), com


@lru_cache(maxsize=1)
def load_provinces() -> pd.DataFrame:
    """34 tỉnh = **dissolve xã theo `admin_l1_code`** (không đọc lớp tỉnh riêng nào).

    Một lớp ⇒ tỉnh và xã không thể lệch niên đại với nhau, và tổng `danso`/diện tích cấp
    tỉnh đúng bằng tổng các xã theo xây dựng."""
    com = load_communes()
    agg = (com.groupby(["admin_l1_code", "province_name"], as_index=False)
              .agg(n_communes=("commune_code", "size"),
                   dientich_km2=("dientich_km2", "sum"), danso=("danso", "sum")))
    agg["geometry"] = [shapely.union_all(com.loc[com.admin_l1_code == c, "geometry"]
                                         .to_numpy())
                       for c in agg["admin_l1_code"]]
    return agg


# --------------------------------------------------------------------------- #
# ĐIỂM — point-in-polygon (+ snap dung sai cho tổng quát hoá 1:1M)             #
# --------------------------------------------------------------------------- #
def assign_points(lat, lng, snap_tol_m: float = ADMIN_SNAP_TOL_M) -> pd.DataFrame:
    """Gán nhãn hành chính cho mảng toạ độ. Trả DataFrame cùng thứ tự đầu vào:

    `admin_l1_code, province_name, commune_code, commune_name, commune_kind,
     admin_src ∈ {inside, nearest, none}, admin_dist_m`.

    `admin_src` là PROVENANCE, không phải cờ chất lượng — quyết định "toạ độ có sai
    không" là việc của `enrich_stations` (nó có thêm địa chỉ để đối chứng)."""
    tree, com = _tree()
    lat = np.asarray(lat, dtype="float64")
    lng = np.asarray(lng, dtype="float64")
    n = len(lat)
    idx = np.full(n, -1, dtype="int64")
    src = np.array(["none"] * n, dtype=object)
    dist_m = np.full(n, np.nan)

    ok = np.isfinite(lat) & np.isfinite(lng)
    if not ok.any():
        return _label_frame(com, idx, src, dist_m)
    pts = points(np.where(ok, lng, 0.0), np.where(ok, lat, 0.0))

    # (1) trong polygon — lớp phủ kín nên "hit đầu tiên" là hit duy nhất (cổng
    #     `commune_layer_disjoint` của enrich_stations canh đúng giả định này).
    pi, ci = tree.query(pts[ok], predicate="intersects")
    where_ok = np.flatnonzero(ok)
    order = np.argsort(pi, kind="stable")
    pi, ci = pi[order], ci[order]
    if len(pi):
        first = np.concatenate(([True], pi[1:] != pi[:-1]))
        idx[where_ok[pi[first]]] = ci[first]
    inside = idx >= 0
    src[inside] = "inside"
    dist_m[inside] = 0.0

    # (2) ngoài mọi polygon -> snap về xã gần nhất TRONG dung sai (bờ biển bị tổng quát
    #     hoá). Xa hơn: KHÔNG đoán (`none`) — nhất quán "không bịa toạ độ" của E-DQ1.
    miss = np.flatnonzero(ok & ~inside)
    if len(miss):
        nearest = tree.nearest(pts[miss])
        d_deg = shapely.distance(pts[miss], com["geometry"].to_numpy()[nearest])
        d_m = d_deg / DEG_PER_M
        take = d_m <= snap_tol_m
        idx[miss[take]] = nearest[take]
        src[miss[take]] = "nearest"
        dist_m[miss] = d_m
    return _label_frame(com, idx, src, dist_m)


def _label_frame(com, idx, src, dist_m) -> pd.DataFrame:
    out = pd.DataFrame(index=pd.RangeIndex(len(idx)))
    hit = idx >= 0
    for c in LABEL_COLS:
        vals = com[c].to_numpy()[idx.clip(0)]
        out[c] = np.where(hit, vals, None)
    out["admin_src"] = src
    out["admin_dist_m"] = np.round(dist_m, 1)
    return out


# --------------------------------------------------------------------------- #
# Ô H3 — lục giác ∩ polygon, trọng số chuẩn hoá theo ô                         #
# --------------------------------------------------------------------------- #
def cell_overlaps(cells) -> pd.DataFrame:
    """Bảng LONG `h3_r8, commune_code, area_frac, w` cho mọi cặp (ô, xã) có giao.

    - `area_frac` = |lục giác ∩ xã| / |lục giác| — tỉ lệ THÔ (không cộng thành 1 ở ô vắt
      biên giới quốc gia hoặc ô ven biển). Dùng làm ĐỘ TIN của nhãn.
    - `w`         = `area_frac` chuẩn hoá để Σ = 1 trên mỗi ô ⇒ dùng để CHIA KHỐI LƯỢNG
      (cổng kế toán `grid_admin_conservation` kiểm đúng tổng này).

    Ô không chạm xã nào **không có dòng** — kế toán phần dư đó là việc của consumer
    (giống cách `demand_h3_clipped_out` tách phần bị clip thay vì xoá im lặng)."""
    cells = list(cells)
    if not cells:
        return pd.DataFrame(columns=["h3_r8", "commune_code", "area_frac", "w"])
    tree, com = _tree()
    geoms = com["geometry"].to_numpy()

    bnd = [h3.cell_to_boundary(c) for c in cells]
    hexes = polygons([np.array([(lo, la) for la, lo in b]) for b in bnd])
    hex_area = shapely.area(hexes)

    hi, ci = tree.query(hexes, predicate="intersects")
    if not len(hi):
        return pd.DataFrame(columns=["h3_r8", "commune_code", "area_frac", "w"])

    # Đường tắt: xã CHỨA TRỌN lục giác -> area_frac = 1, khỏi dựng hình giao (phần lớn ô
    # nội địa rơi vào đây; chỉ ~2,3 xã/ô ở 61,6k ô vắt xã mới phải tính thật).
    inter_area = np.empty(len(hi))
    covered = shapely.contains_properly(geoms[ci], hexes[hi])
    inter_area[covered] = hex_area[hi[covered]]
    todo = ~covered
    if todo.any():
        inter_area[todo] = shapely.area(
            shapely.intersection(hexes[hi[todo]], geoms[ci[todo]]))

    out = pd.DataFrame({"h3_r8": np.asarray(cells, dtype=object)[hi],
                        "commune_code": com["commune_code"].to_numpy()[ci],
                        "area_frac": inter_area / hex_area[hi]})
    # bỏ giao suy biến (chạm cạnh, diện tích ~0) trước khi chuẩn hoá để không sinh trọng
    # số vô nghĩa; ngưỡng 1e-9 << mọi giao thật (ô nhỏ nhất vẫn ~1e-6 độ²).
    out = out[out["area_frac"] > 1e-9].reset_index(drop=True)
    tot = out.groupby("h3_r8")["area_frac"].transform("sum")
    out["w"] = out["area_frac"] / tot
    return out


def labels_from_overlaps(ov: pd.DataFrame) -> pd.DataFrame:
    """Nhãn 1 dòng/ô = xã chiếm diện tích LỚN NHẤT (argmax), kèm `admin_frac` (tỉ lệ thô
    của xã thắng) và `n_communes` (số xã ô chạm) để consumer biết nhãn "chắc" đến đâu."""
    if ov.empty:
        return pd.DataFrame(columns=["h3_r8", "commune_code", "admin_frac", "n_communes"])
    ov = ov.sort_values(["h3_r8", "area_frac"], ascending=[True, False])
    top = ov.groupby("h3_r8", as_index=False).first()
    n = ov.groupby("h3_r8", as_index=False).size().rename(columns={"size": "n_communes"})
    top = top.merge(n, on="h3_r8")
    return top.rename(columns={"area_frac": "admin_frac"})[
        ["h3_r8", "commune_code", "admin_frac", "n_communes"]]


def attach_labels(df: pd.DataFrame, code_col: str = "commune_code") -> pd.DataFrame:
    """Nối 4 cột nhãn khai báo (+ `province_name`) vào bảng đã có `commune_code`."""
    com = load_communes()[LABEL_COLS]
    return df.merge(com, on=code_col, how="left")
