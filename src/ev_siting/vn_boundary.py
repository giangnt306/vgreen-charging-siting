#!/usr/bin/env python3
"""vn_boundary.py — cắt mọi lớp dẫn xuất theo **đa giác lãnh thổ VN**, không phải bbox.

VÌ SAO CÓ FILE NÀY (đo 2026-07-29, E-DQ11). `VN_BBOX = (8.0, 102.0, 23.7, 110.0)` trong
`data/osm/paths.py` là **hình chữ nhật**: nó trùm Đông Bắc Thái Lan, Nam Lào, phần lớn
Campuchia và một mảng Quảng Tây/Vân Nam. `overpass_poi.py` truy vấn theo bbox đó rồi ghi
thẳng ra raw, **không có bước cắt đa giác nào**. Kết quả đo trên `osm_poi_points.parquet`:

    20.256 / 37.362 POI (54,2%) nằm NGOÀI lãnh thổ VN
      parking 65,4% · apartments 58,9% · fuel 53,4% · retail 41,0% · mall 18,9%
    ví dụ: `node/371154605` "ป.ต.ท." (PTT) tại 16,4134N 102,8188E — Khon Kaen, Thái Lan

Lỗi lan tới sản phẩm cuối: `candidate_sites.parquet` có **6.881/28.075 (24,5%) điểm ngoài
VN**, riêng tầng T1 (ưu tiên cao nhất) là 5.976/8.688 — fuel 67,5%, parking 73,2%. Đường
KHÔNG dính (1,5%) vì PBF Geofabrik đã cắt sẵn theo biên giới; **chỉ lớp POI hở**.

Kiểm tra cũ không bắt được vì nó cũng chỉ so với bbox: `validate.py` có check tên
`poi_coords_in_vn` nhưng thân hàm là `poi.lat.between(...)` — luôn PASS. Bài học đúng
họ với F4: **cổng kiểm tra hỏi sai câu hỏi thì không bao giờ đỏ**.

Dùng::

    from ev_siting.vn_boundary import mask_points_in_vn, mask_cells_touching_vn
    keep = mask_points_in_vn(df["lat"], df["lng"])          # điểm: within
    keep = mask_cells_touching_vn(df["h3_r8"])              # ô H3: tâm-trong HOẶC chạm biên
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Cùng biến môi trường với `data/evcs/admin_join.py` — hai module PHẢI trỏ cùng một lớp
# ranh giới, nếu không thì trạm và POI bị cắt theo hai bản đồ khác nhau. Test khoá điều này.
VN_ADMIN_DIR = Path(
    os.environ.get("EVCS_VN_ADMIN_DIR") or PROJECT_ROOT / "data" / "ref" / "vn_admin" / "valid_from=2025-07-01"
)
_FALLBACK = PROJECT_ROOT.parent / "evcs-dataset" / "data" / "ref" / "vn_admin" / "valid_from=2025-07-01"

_CACHE = {}


def admin_dir() -> Path:
    """-> thu muc lop ranh gioi. Uu tien ban TRONG repo (co trong MANIFEST).

    `_FALLBACK` sang repo anh em van duoc giu de khong chan may da cau hinh cu, nhung
    phai KEU TO: ban do o do khong nam trong snapshot dong bang, nen doi no la doi
    im lang moi con so cat bien (POI, luoi demand, diem T4, cong QA) ma
    `make verify-snapshot` van bao PASS.
    """
    if (VN_ADMIN_DIR / "provinces.parquet").exists():
        return VN_ADMIN_DIR
    if (_FALLBACK / "provinces.parquet").exists():
        print(
            f"!! CANH BAO: dung lop ranh gioi NGOAI repo {_FALLBACK} — no KHONG nam trong\n"
            f"   MANIFEST nen moi phep cat bien deu khong tai lap duoc. Chep vao {VN_ADMIN_DIR}\n"
            "   roi chay `make freeze`.",
            flush=True,
        )
        return _FALLBACK
    raise SystemExit(
        f"không tìm thấy lớp ranh giới. Thử: {VN_ADMIN_DIR} và {_FALLBACK}\n"
        "Đặt EVCS_VN_ADMIN_DIR trỏ tới thư mục chứa provinces.parquet."
    )


def load_provinces():
    """-> ndarray đa giác tỉnh (shapely). CHỈ giữ (MULTI)POLYGON có tên.

    `provinces.parquet` cũng lẫn feature đường ranh giới trần như `communes.parquet`;
    giữ nguyên chúng sẽ làm `within` trả 0 match mà không báo lỗi.
    """
    from shapely import from_wkb, get_type_id

    if "pro" in _CACHE:
        return _CACHE["pro"]
    df = pd.read_parquet(admin_dir() / "provinces.parquet").reset_index(drop=True)
    geom = from_wkb([bytes(b) for b in df["geometry"]])
    keep = np.isin(get_type_id(geom), (3, 6)) & df["name"].notna().to_numpy()
    _CACHE["pro"] = np.asarray(geom, dtype=object)[keep]
    return _CACHE["pro"]


def _tree():
    from shapely import STRtree

    if "tree" not in _CACHE:
        _CACHE["tree"] = STRtree(load_provinces())
    return _CACHE["tree"]


def mask_points_in_vn(lat, lng) -> np.ndarray:
    """-> bool[n]: điểm nằm TRONG lãnh thổ VN.

    CHIỀU VỊ TỪ: `STRtree.query(g, predicate=p)` tính `p(g_đầu_vào, g_trong_cây)`, tức
    `point.within(polygon)`. Đặt nhầm thành "covers" cho 0 match mà im lặng (đã dính một
    lần ở `admin_join`); test hồi quy khoá chiều này.
    """
    from shapely import points

    lat = np.asarray(lat, dtype=float)
    lng = np.asarray(lng, dtype=float)
    if len(lat) == 0:
        return np.zeros(0, dtype=bool)
    pi, _ = _tree().query(points(lng, lat), predicate="within")
    out = np.zeros(len(lat), dtype=bool)
    out[np.unique(pi)] = True
    return out


def mask_cells_touching_vn(cells) -> np.ndarray:
    """-> bool[n]: ô H3 có phần nào thuộc VN (tâm-trong HOẶC đa giác ô cắt biên giới).

    Dùng `intersects` chứ không chỉ `within(tâm)` vì ô biên giới rộng ~0,85 km²: một ô có
    tâm bên Campuchia vẫn có thể chứa dân/đường phía VN. Đo: quy tắc tâm-trong đơn thuần
    bỏ 0,075M người và 11.259 km đường ở vành biên. Tính tâm trước (rẻ), chỉ dựng đa giác
    cho phần trượt (~6% số ô).
    """
    import h3
    from shapely import polygons

    cells = list(cells)
    if not cells:
        return np.zeros(0, dtype=bool)
    ll = np.array([h3.cell_to_latlng(c) for c in cells])
    out = mask_points_in_vn(ll[:, 0], ll[:, 1])

    idx = np.nonzero(~out)[0]
    if len(idx):
        rings = [np.array([(lo, la) for la, lo in h3.cell_to_boundary(cells[i])]) for i in idx]
        rings = [np.vstack([r, r[:1]]) for r in rings]
        polys = polygons(rings)
        pi, _ = _tree().query(polys, predicate="intersects")
        out[idx[np.unique(pi)]] = True
    return out
