#!/usr/bin/env python3
"""settlement.py — biến `pop` thô thành **vùng tập trung dân cư** + gắn cờ ô vô lý.

HAI VẤN ĐỀ CÒN LẠI CỦA LỚP CẦU (Kỳ nêu 2026-07-29), mà việc cắt biên giới và đổi niên đại
KHÔNG chạm tới:

**(1) Mật độ đỉnh vô lý.** WorldPop 2020 BSGM dồn hàng nghìn người vào một pixel giữa rừng
hoặc giữa biển. Bằng chứng đối chiếu ESA WorldCover 10m (đo 29/07):

    ô 10,036N 104,558E : 80,2% MẶT NƯỚC, 1,9% đã xây -> pop 2020 = 29.337 (2025: 67)
    ô 22,744N 104,686E : 86,2% TÁN CÂY,  1,3% đã xây -> pop 2020 = 14.392 (2025: 269)
    ô 19,524N 104,307E : 93,8% TÁN CÂY,  0,6% đã xây -> pop 2020 =  6.453 (2025: 158)

Tổng: bản 2020 đặt **224 nghìn người lên các ô >80% mặt nước** (một ô 29.337 người); bản
2025 đặt 63 nghìn nhưng rải trên 2.475 ô, ô lớn nhất chỉ 1.170 — tức là vệt tràn ven biển
bình thường của lưới 100 m, không phải cục. Mật độ trên **đất đã xây**: 2020 có p99 =
137.636 và max = 1.837.609 người/km²; 2025 là 55.813 và 182.582.

**(2) Không thấy được "khu tập trung dân cư".** `demand_h3` chỉ có số người từng ô rời rạc.
MCLP cần biết ô nào thuộc một **vùng đô thị liền mạch** — một ô 30k người đơn độc giữa
biển và một ô 30k người trong lõi Hà Nội là hai thứ hoàn toàn khác nhau cho bài toán đặt
trạm, nhưng cột `pop` không phân biệt được.

CÁCH XỬ LÝ — hai lớp, đều **cộng thêm, không sửa `pop`**:

* `pop_k1` — tổng dân trên đĩa H3 bán kính 1 (7 ô, ~5,9 km²). Cục dị thường 1-ô bị pha
  loãng 7 lần, còn vùng đô thị thật thì gần như không đổi vì hàng xóm cũng đông. Đây là
  đại lượng nên dùng cho MCLP: R = 3 km vốn đã lớn hơn ô res 8 (d = 0,98 km), nên độ phân
  giải 1-ô là **giả**.

* `settlement_class` — phân loại theo **Degree of Urbanisation (DEGURBA)**, chuẩn được
  Uỷ ban Thống kê LHQ thông qua 2020, áp lên lưới H3 với kề cạnh `grid_disk(k=1)`:
      URBAN_CENTRE  : cụm liền mạch mật độ ≥1.500 ng/km², tổng cụm ≥50.000 người
      URBAN_CLUSTER : cụm liền mạch mật độ  ≥300 ng/km², tổng cụm  ≥5.000 người
      RURAL         : còn lại
  Kèm `cluster_id` / `cluster_pop` / `cluster_n_cells` để **nhìn thấy** cụm 1-ô giả mạo:
  một "đô thị" có `cluster_n_cells = 1` là dấu hiệu artefact, không phải thành phố.

* Cờ `pop_unsupported` — bằng chứng đất đai **mâu thuẫn** với dân số được gán. Chính sách
  giống E-DQ1: **gắn cờ, không sửa**. Việc SỬA (đặt lại chỗ theo trọng tài VNSDI) nằm ở
  `reconcile_dasymetric`/`reallocate_roadless` (E-DQ7f/8b) và chỉ chạm `pop_adj`; lớp này
  chạy trên `pop`/`pop_2025` thô (Q6iii — giữ nguyên số đã đo) và chỉ gắn cờ chẩn đoán.

Chạy (sau `build_demand_h3` và `landuse.worldcover`; thứ tự do Makefile giữ:
`demand -> settlement`. Module này KHÔNG tự gọi lại `build_demand_h3` — `demand_h3`
không mang cột settlement, consumer đọc thẳng `settlement_h3.parquet`)::

    PYTHONPATH=src python -m ev_siting.data.worldpop.settlement
    PYTHONPATH=src python -m ev_siting.data.worldpop.settlement --dry-run
"""

import argparse
import os

import h3
import numpy as np
import pandas as pd

from .paths import DEMAND_H3, SETTLEMENT_H3, ensure_dirs

# --- ngưỡng DEGURBA (UN Statistical Commission 2020), giữ nguyên số gốc ---
DENS_URBAN_CENTRE = 1500.0
DENS_URBAN_CLUSTER = 300.0
MIN_POP_CENTRE = 50_000
MIN_POP_CLUSTER = 5_000

# --- ngưỡng "đất đai không đỡ nổi dân số này" ---
WATER_FRAC = 0.80  # WorldCover thấy chủ yếu là nước
WATER_MIN_POP = 100.0  # ...mà vẫn có ngần này người
BUILT_FRAC = 0.02  # WorldCover gần như không thấy công trình
BUILT_MIN_POP = 500.0

VINTAGES = {"pop": "", "pop_2025": "_2025"}


def cell_areas(cells) -> np.ndarray:
    """Diện tích km² từng ô. H3 res 8 KHÔNG đều (0,79–0,87 km² ở vĩ độ VN) nên không
    được dùng hằng số — sai số 10% ở đuôi phân bố mật độ."""
    return np.array([h3.cell_area(c, "km^2") for c in cells], dtype=float)


def neighbourhood_sum(cells, values, k=1) -> np.ndarray:
    """Tổng `values` trên đĩa H3 bán kính `k` quanh mỗi ô (kể cả chính nó).

    Ô ngoài lưới coi như 0 — đúng nghĩa "không có dân được ghi nhận ở đó", và sau khi cắt
    biên giới thì hàng xóm thiếu chủ yếu là nước ngoài/biển.
    """
    pos = {c: i for i, c in enumerate(cells)}
    v = np.asarray(values, dtype=float)
    v = np.nan_to_num(v, nan=0.0)
    out = np.zeros(len(cells), dtype=float)
    for i, c in enumerate(cells):
        s = 0.0
        for nb in h3.grid_disk(c, k):
            j = pos.get(nb)
            if j is not None:
                s += v[j]
        out[i] = s
    return out


def connected_clusters(cells, mask) -> np.ndarray:
    """Gán nhãn cụm liền mạch cho các ô `mask=True` (kề cạnh = `grid_disk(k=1)`).

    Union-find; -1 cho ô không thuộc mask. Nhãn được đánh lại theo thứ tự dân số giảm dần
    ở `classify` để `cluster_id=0` luôn là cụm lớn nhất.
    """
    idx = {c: i for i, c in enumerate(cells) if mask[i]}
    parent = list(range(len(cells)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c, i in idx.items():
        for nb in h3.grid_disk(c, 1):
            j = idx.get(nb)
            if j is not None and j > i:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri

    lab = np.full(len(cells), -1, dtype=np.int64)
    for i in idx.values():
        lab[i] = find(i)
    return lab


def _cluster_stats(cells, pop, dens, dens_thr, min_pop):
    """-> (mask thuộc cụm đạt chuẩn, nhãn, tổng dân cụm, số ô cụm)."""
    seed = np.nan_to_num(dens, nan=0.0) >= dens_thr
    lab = connected_clusters(cells, seed)
    p = np.nan_to_num(np.asarray(pop, dtype=float), nan=0.0)
    tot = pd.Series(p).groupby(lab).sum()
    cnt = pd.Series(p).groupby(lab).size()
    keep = {k for k in tot.index if k >= 0 and tot[k] >= min_pop}
    ok = np.array([x in keep for x in lab])
    return ok, lab, tot, cnt


def classify(cells, pop) -> pd.DataFrame:
    """DEGURBA trên lưới H3 -> class + cụm. `pop` NaN xử như 0 (không phủ = không dân ghi nhận)."""
    cells = list(cells)
    area = cell_areas(cells)
    p = np.nan_to_num(np.asarray(pop, dtype=float), nan=0.0)
    dens = p / area

    centre_ok, centre_lab, c_tot, c_cnt = _cluster_stats(cells, p, dens, DENS_URBAN_CENTRE, MIN_POP_CENTRE)
    clus_ok, clus_lab, u_tot, u_cnt = _cluster_stats(cells, p, dens, DENS_URBAN_CLUSTER, MIN_POP_CLUSTER)

    cls = np.where(centre_ok, "URBAN_CENTRE", np.where(clus_ok, "URBAN_CLUSTER", "RURAL"))
    # Cụm ở ngưỡng 300 ng/km² gộp NGUYÊN đồng bằng thành một khối (đo: cụm lớn nhất = 26,6M
    # người / 10.365 ô) nên không dùng để chỉ ra "khu tập trung" được. Cụm ở ngưỡng LÕI
    # (1.500 ng/km²) mới tách ra từng đô thị — đây mới là thứ MCLP cần nhìn.
    c_lab = np.where(centre_ok, centre_lab, -1)
    c_order = {k: i for i, k in enumerate(c_tot[c_tot.index >= 0].sort_values(ascending=False).index)}
    centre_id = np.array([c_order.get(x, -1) if x >= 0 else -1 for x in c_lab], dtype=np.int64)
    # Cụm báo cáo = cụm ĐÔ THỊ (ngưỡng 300) vì nó chứa cả lõi lẫn vành đai; lõi chỉ đổi nhãn.
    lab = np.where(clus_ok, clus_lab, -1)
    order = {k: i for i, k in enumerate(u_tot[u_tot.index >= 0].sort_values(ascending=False).index)}
    cid = np.array([order.get(x, -1) if x >= 0 else -1 for x in lab], dtype=np.int64)

    return pd.DataFrame(
        {
            "h3_r8": cells,
            "area_km2": area,
            "dens_ppkm2": dens,
            "settlement_class": cls,
            "cluster_id": cid,
            "cluster_pop": [float(u_tot.get(x, 0.0)) if x >= 0 else 0.0 for x in lab],
            "cluster_n_cells": [int(u_cnt.get(x, 0)) if x >= 0 else 0 for x in lab],
            "centre_id": centre_id,
            "centre_pop": [float(c_tot.get(x, 0.0)) if x >= 0 else 0.0 for x in c_lab],
            "centre_n_cells": [int(c_cnt.get(x, 0)) if x >= 0 else 0 for x in c_lab],
        }
    )


def land_support(pop, landuse: pd.DataFrame) -> pd.DataFrame:
    """Cờ 'đất đai không đỡ nổi dân số này'. Trả 2 cờ + cờ gộp `pop_unsupported`.

    KHÔNG suy ra "pop sai": WorldCover cũng có sai số, và ô ven biển trộn nước/đất là bình
    thường. Cờ nói **hai nguồn độc lập bất đồng** — đủ để không tin ô đó, chưa đủ để sửa.
    """
    p = np.nan_to_num(np.asarray(pop, dtype=float), nan=0.0)
    water = landuse["frac_water"].fillna(0.0).to_numpy()
    built = landuse["built_up_frac"].fillna(0.0).to_numpy()
    on_water = (water > WATER_FRAC) & (p > WATER_MIN_POP)
    no_built = (built < BUILT_FRAC) & (p > BUILT_MIN_POP)
    return pd.DataFrame({"pop_on_water": on_water, "pop_no_built": no_built, "pop_unsupported": on_water | no_built})


def build(demand: pd.DataFrame, landuse: pd.DataFrame | None = None) -> pd.DataFrame:
    """-> settlement_h3: mọi cột phân loại cho CẢ HAI niên đại."""
    cells = demand["h3_r8"].tolist()
    out = pd.DataFrame({"h3_r8": cells})
    for col, suf in VINTAGES.items():
        if col not in demand.columns:
            continue
        c = classify(cells, demand[col])
        out[f"pop_k1{suf}"] = neighbourhood_sum(cells, demand[col], k=1)
        for name in (
            "dens_ppkm2",
            "settlement_class",
            "cluster_id",
            "cluster_pop",
            "cluster_n_cells",
            "centre_id",
            "centre_pop",
            "centre_n_cells",
        ):
            out[f"{name}{suf}"] = c[name].to_numpy()
        if "area_km2" not in out.columns:
            out["area_km2"] = c["area_km2"].to_numpy()
        if landuse is not None:
            lsup = land_support(demand[col], landuse)
            for name in lsup.columns:
                out[f"{name}{suf}"] = lsup[name].to_numpy()
    return out


def _report(out: pd.DataFrame, demand: pd.DataFrame):
    for col, suf in VINTAGES.items():
        if f"settlement_class{suf}" not in out.columns:
            continue
        p = demand[col].fillna(0.0)
        cls = out[f"settlement_class{suf}"]
        print(f"\n  === {col} ===")
        for k in ("URBAN_CENTRE", "URBAN_CLUSTER", "RURAL"):
            m = cls == k
            print(
                f"    {k:14} {int(m.sum()):7,} ô ({100 * m.mean():5.1f}%)  "
                f"{p[m].sum() / 1e6:6.2f}M người ({100 * p[m].sum() / p.sum():5.1f}%)"
            )
        cid = out[f"cluster_id{suf}"]
        n1 = ((cid >= 0) & (out[f"cluster_n_cells{suf}"] == 1)).sum()
        print(f"    số cụm đô thị: {int(cid.max()) + 1:,} | cụm CHỈ 1 Ô (nghi artefact): {int(n1):,}")
        oid = out[f"centre_id{suf}"]
        o1 = ((oid >= 0) & (out[f"centre_n_cells{suf}"] == 1)).sum()
        print(f"    số LÕI đô thị: {int(oid.max()) + 1:,} | lõi CHỈ 1 Ô (nghi artefact): {int(o1):,}")
        if f"pop_unsupported{suf}" in out.columns:
            u = out[f"pop_unsupported{suf}"]
            print(
                f"    pop_unsupported: {int(u.sum()):,} ô giữ {p[u].sum() / 1e3:,.0f} nghìn người "
                f"({100 * p[u].sum() / p.sum():.2f}%) — trên nước {int(out[f'pop_on_water{suf}'].sum()):,}, "
                f"không thấy công trình {int(out[f'pop_no_built{suf}'].sum()):,}"
            )


def main(dry_run=False):
    ensure_dirs()
    if not DEMAND_H3.exists():
        raise SystemExit(f"thiếu {DEMAND_H3} — chạy build_demand_h3 trước")
    demand = pd.read_parquet(DEMAND_H3)

    from ev_siting.data.landuse.paths import LANDUSE_H3

    landuse = None
    if LANDUSE_H3.exists():
        lu = pd.read_parquet(LANDUSE_H3)[["h3_r8", "frac_water", "built_up_frac"]]
        landuse = demand[["h3_r8"]].merge(lu, on="h3_r8", how="left")
    else:
        print(f"[settlement] ! chưa có {LANDUSE_H3.name} — bỏ qua cờ pop_unsupported")

    print(f"[settlement] {len(demand):,} ô — DEGURBA + đĩa k=1 ...")
    out = build(demand, landuse)
    _report(out, demand)
    if dry_run:
        print("\n(dry-run: KHÔNG ghi)")
        return out

    tmp = SETTLEMENT_H3.with_suffix(".parquet.tmp")
    out.to_parquet(tmp, index=False)
    os.replace(tmp, SETTLEMENT_H3)
    print(f"\n-> {SETTLEMENT_H3}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Phân loại vùng tập trung dân cư (DEGURBA) + cờ pop vô lý")
    ap.add_argument("--dry-run", action="store_true", help="chỉ báo số, không ghi")
    a = ap.parse_args()
    main(dry_run=a.dry_run)
