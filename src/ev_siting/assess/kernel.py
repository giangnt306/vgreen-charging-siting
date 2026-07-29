"""Kernel không gian của assess() — mạng nền N, tập phủ, cầu biên, láng giềng gần.

Bất biến C10 (một hệ quy chiếu phủ duy nhất): tập phủ của MỌI thứ — trạm nền,
điểm được chấm, lớp tham chiếu — đều đi qua ``build_candidates._coverage_cells``
(grid_disk k=⌈R/0,98⌉+1 + lọc haversine tâm-ô ≤ R). Import trực tiếp, không copy:
copy là mầm lệch hệ quy chiếu khi một bên sửa mà bên kia không.

Khoảng cách điểm—trạm dùng toạ độ thật (không snap ô) qua BallTree haversine —
khớp từng hằng số với ``aoi.haversine_km`` (EARTH_R_KM = 6371,0088) để số mét
in ra reason và số km lọc bán kính không bao giờ cãi nhau.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import h3
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from ev_siting.aoi import EARTH_R_KM
from ev_siting.assess import params
from ev_siting.features.build_candidates import _coverage_cells

#: Cột bắt buộc của bảng trạm nền — thiếu cột nào kernel phải nổ sớm, không đoán.
_STATION_COLS = ["station_id", "lat", "lng", "h3_r8", "num_connectors"]


# eq=False: field ``tree`` (BallTree) và ``stations`` (DataFrame) không so sánh
# được bằng ``==`` — context là object dùng một lần theo mode, không phải value.
@dataclass(eq=False)
class NetworkContext:
    """Mạng nền N đã đóng gói: trạm còn lại + tập ô đã phủ + index láng giềng."""

    stations: pd.DataFrame
    covered_cells: frozenset[str]
    mode: str
    r_km: float
    n_excluded: int
    tree: BallTree | None  # None khi mạng rỗng — BallTree không nhận 0 điểm


def build_network(
    covered0: pd.DataFrame,
    exclude_station_ids: Iterable[str] = (),
    r_km: float = params.R_SERVICE_KM,
    mode: str = "live",
) -> NetworkContext:
    """Dựng mạng nền N từ covered0 frozen, trừ đi các trạm bị loại (retrodiction).

    ``n_excluded`` là số trạm khớp THỰC TẾ (pre-reg §2 bắt báo con số này) —
    mã trong danh sách loại mà không có trong covered0 thì không được đếm,
    để lệch map mã lộ ra ở report thay vì im lặng.
    """
    excl = set(exclude_station_ids)
    mask = covered0["station_id"].isin(excl)
    n_excluded = int(covered0.loc[mask, "station_id"].nunique())
    stations = covered0.loc[~mask, _STATION_COLS].reset_index(drop=True)

    # Hợp phủ tính trên ô UNIQUE: nhiều trạm chung một ô r8 chỉ cần một lần
    # grid_disk — kết quả y hệt, chi phí tuyến tính theo số ô chứ không số trạm.
    cells: set[str] = set()
    for cell in stations["h3_r8"].unique():
        cells |= _coverage_cells(cell, r_km)

    if len(stations):
        # BallTree haversine nhận (lat, lng) theo RADIANS; khoảng cách trả về là
        # góc tâm (radians) — đổi km/mét bằng đúng EARTH_R_KM của aoi.
        tree = BallTree(np.radians(stations[["lat", "lng"]].to_numpy(dtype=float)), metric="haversine")
    else:
        tree = None

    return NetworkContext(
        stations=stations,
        covered_cells=frozenset(cells),
        mode=mode,
        r_km=r_km,
        n_excluded=n_excluded,
        tree=tree,
    )


def point_cells(lat: float, lng: float, r_km: float = params.R_SERVICE_KM) -> frozenset[str]:
    """Cov(p) của một điểm — cùng kernel phủ với trạm nền (C10), nên marginal = 0
    là bất biến kiểm được khi điểm trùng ô một trạm hiện hữu."""
    return _coverage_cells(h3.latlng_to_cell(lat, lng, 8), r_km)


def demand_series(demand_df: pd.DataFrame) -> pd.Series:
    """demand_h3 -> Series index h3_r8 -> pop (float) — dạng tra cứu O(1) cho các tổng theo tập ô.

    Index trùng bị chặn cứng (adversarial 28/07): ô lặp làm control sampling lấy một ô
    hai lần "không hoàn lại" và ``.loc`` một ô trả Series — cả hai đều là bug câm.
    """
    s = demand_df.set_index("h3_r8")["pop"].astype(float)
    if not s.index.is_unique:
        dup = s.index[s.index.duplicated()].unique()[:5].tolist()
        raise SystemExit(f"ASSESS FAIL: demand_h3 có {int(s.index.duplicated().sum())} ô h3_r8 trùng, vd {dup}")
    return s


def marginal_pop(cells: frozenset[str], ctx: NetworkContext, dem: pd.Series) -> float:
    """Σ pop các ô của điểm CHƯA thuộc phủ mạng nền — feature I-1: đo giá trị biên,
    không đo "chỗ đông" (chỗ đông mà đã phủ kín thì biên bằng 0)."""
    free = cells - ctx.covered_cells
    if not free:
        return 0.0
    return float(dem[dem.index.isin(free)].sum())


def local_pop(cells: frozenset[str], dem: pd.Series) -> float:
    """Σ pop toàn catchment (v_demand_local) — mẫu số của n_redundancy nên tách hàm riêng."""
    return float(dem[dem.index.isin(cells)].sum())


def nearest_info(
    ctx: NetworkContext,
    lats: np.ndarray,
    lngs: np.ndarray,
    comp_km: float = params.COMPETITION_RADIUS_KM,
    r_km: float = params.R_SERVICE_KM,
) -> dict:
    """Truy vấn láng giềng vector hoá cho một lô điểm — một lần dựng mảng, ba bán kính.

    Trả về dict mảng cùng độ dài với ``lats``:
    - ``d_nearest_m``: mét tới trạm gần nhất (np.inf nếu mạng rỗng — để G2/R10
      tự suy "không có trạm" thay vì phải xử lý ngoại lệ riêng);
    - ``n_within_comp``: số trạm cách ≤ comp_km (v_competition);
    - ``connectors_within_r``: Σ num_connectors trạm cách ≤ r_km (mẫu v_pressure);
    - ``idx_within_r``: list array chỉ số dòng ``ctx.stations`` trong R — engine
      cần danh tính trạm (không chỉ tổng) để join telemetry cho occ_local.
    """
    lats = np.asarray(lats, dtype=float).reshape(-1)
    lngs = np.asarray(lngs, dtype=float).reshape(-1)
    n = len(lats)

    if ctx.tree is None:
        return {
            "d_nearest_m": np.full(n, np.inf),
            "n_within_comp": np.zeros(n, dtype=int),
            "connectors_within_r": np.zeros(n, dtype=float),
            "idx_within_r": [np.empty(0, dtype=int) for _ in range(n)],
        }

    pts = np.radians(np.column_stack([lats, lngs]))
    dist_rad, _ = ctx.tree.query(pts, k=1)
    # Bán kính truy vấn đổi sang radians bằng CÙNG bán kính Trái Đất với
    # aoi.haversine_km — mét trả về đối chiếu được 1-1 với hàm đó (test #4).
    idx_comp = ctx.tree.query_radius(pts, r=comp_km / EARTH_R_KM)
    idx_r = ctx.tree.query_radius(pts, r=r_km / EARTH_R_KM)
    conn = ctx.stations["num_connectors"].to_numpy(dtype=float)

    return {
        "d_nearest_m": dist_rad[:, 0] * EARTH_R_KM * 1000.0,
        "n_within_comp": np.array([len(i) for i in idx_comp], dtype=int),
        "connectors_within_r": np.array([conn[i].sum() for i in idx_r], dtype=float),
        "idx_within_r": list(idx_r),
    }
