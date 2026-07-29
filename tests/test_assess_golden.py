"""B8 — golden test: đối chiếu kernel với **oracle độc lập**, không phải với chính nó.

Kịch bản chết B của nhóm trước là *sai một fact trước mặt người biết địa bàn*
("cách đó 200 m có 3 trạm rồi kìa"). Mọi fact ở mục 1 của hồ sơ thẩm định đều
đi qua bốn hàm dưới đây, nên mỗi hàm được kiểm bằng một đường tính **khác**:

| Fact | Đường sản xuất | Oracle độc lập ở đây |
|---|---|---|
| `d_nearest_m`, `n_within_1km` | BallTree haversine (sklearn) | vét cạn `aoi.haversine_km` trên toàn bộ trạm |
| `pop_catchment` | `grid_disk` + lọc bán kính | lọc bán kính trực tiếp trên toàn lưới cầu |
| `n_marginal_pop` / `n_redundancy` | hiệu tập ô | đếm tay trên hình học hai đĩa |
| bán kính đổi mét | `EARTH_R_KM` | trạm đặt ở khoảng cách BIẾT TRƯỚC |

Lưới nhân tạo: ô r8 quanh Hà Nội, dân số 100/ô ⇒ mọi tổng là bội số của 100,
đếm tay được.
"""

import h3
import numpy as np
import pandas as pd
import pytest

from ev_siting.aoi import EARTH_R_KM, haversine_km
from ev_siting.assess import kernel, params

LAT, LNG = 21.0000, 105.8000
POP_PER_CELL = 100.0


def _grid(k=12):
    """Lưới cầu nhân tạo: mọi ô trong grid_disk(k), mỗi ô 100 dân."""
    cells = sorted(h3.grid_disk(h3.latlng_to_cell(LAT, LNG, 8), k))
    ll = np.array([h3.cell_to_latlng(c) for c in cells])
    return pd.DataFrame({"h3_r8": cells, "pop": POP_PER_CELL, "lat": ll[:, 0], "lng": ll[:, 1]})


def _offset(lat, lng, north_km=0.0, east_km=0.0):
    """Dời một điểm theo mét — dùng CÙNG bán kính Trái Đất với kernel."""
    dlat = np.degrees(north_km / EARTH_R_KM)
    dlng = np.degrees(east_km / (EARTH_R_KM * np.cos(np.radians(lat))))
    return lat + dlat, lng + dlng


def _network(points):
    st = pd.DataFrame(
        [
            {"station_id": f"st-{i}", "lat": la, "lng": ln, "h3_r8": h3.latlng_to_cell(la, ln, 8), "num_connectors": 2}
            for i, (la, ln) in enumerate(points)
        ]
    )
    return kernel.build_network(st)


# ───────────────────── 1. khoảng cách: BallTree vs vét cạn ─────────────────────


@pytest.mark.parametrize("east_km", [0.15, 0.2, 0.35, 0.999, 1.0, 1.001, 2.5])
def test_d_nearest_matches_bruteforce_haversine(east_km):
    """Sai một mét ở đây là sai câu 'cách đó 200 m' — đối chiếu công thức thẳng."""
    sla, slng = _offset(LAT, LNG, east_km=east_km)
    net = _network([(sla, slng)])
    got = kernel.nearest_info(net, np.array([LAT]), np.array([LNG]))
    want_m = haversine_km(LAT, LNG, sla, slng) * 1000.0
    assert got["d_nearest_m"][0] == pytest.approx(want_m, rel=1e-9)


def test_counts_within_radius_match_bruteforce():
    """`n_within_1km` phải đúng bằng số trạm mà công thức haversine nói là ≤ 1 km."""
    pts = [_offset(LAT, LNG, east_km=d) for d in (0.1, 0.5, 0.95, 1.05, 2.0, 2.9, 3.5)]
    pts += [_offset(LAT, LNG, north_km=d) for d in (0.3, 1.2, 4.0)]
    net = _network(pts)
    got = kernel.nearest_info(net, np.array([LAT]), np.array([LNG]))

    d_km = np.array([haversine_km(LAT, LNG, la, ln) for la, ln in pts])
    assert got["n_within_comp"][0] == int((d_km <= params.COMPETITION_RADIUS_KM).sum()) == 4
    assert len(got["idx_within_r"][0]) == int((d_km <= params.R_SERVICE_KM).sum()) == 8
    assert got["connectors_within_r"][0] == pytest.approx(2.0 * 8)
    assert got["d_nearest_m"][0] == pytest.approx(d_km.min() * 1000.0, rel=1e-9)


def test_empty_network_is_infinite_not_zero():
    """Mạng rỗng phải là 'không có trạm', không phải 'trạm cách 0 m'."""
    net = kernel.build_network(pd.DataFrame(columns=["station_id", "lat", "lng", "h3_r8", "num_connectors"]))
    got = kernel.nearest_info(net, np.array([LAT]), np.array([LNG]))
    assert np.isinf(got["d_nearest_m"][0]) and got["n_within_comp"][0] == 0


# ───────────────── 2. catchment: grid_disk vs lọc bán kính thẳng ────────────────


def test_point_cells_equals_direct_radius_filter():
    """Oracle: ô thuộc catchment ⇔ tâm ô cách điểm ≤ R. Không qua grid_disk."""
    g = _grid()
    cov = kernel.point_cells(LAT, LNG)
    center = h3.cell_to_latlng(h3.latlng_to_cell(LAT, LNG, 8))
    d = haversine_km(center[0], center[1], g["lat"].to_numpy(), g["lng"].to_numpy())
    want = set(g.loc[d <= params.R_SERVICE_KM, "h3_r8"])
    assert set(cov) & set(g["h3_r8"]) == want
    assert len(want) > 30, "lưới thử phải đủ rộng để catchment không chạm biên"


def test_local_pop_is_countable_by_hand():
    g = _grid()
    dem = kernel.demand_series(g[["h3_r8", "pop"]])
    cov = kernel.point_cells(LAT, LNG)
    n_cells = len(set(cov) & set(g["h3_r8"]))
    assert kernel.local_pop(cov, dem) == pytest.approx(n_cells * POP_PER_CELL)


# ───────────────────── 3. giá trị biên: hình học hai đĩa ──────────────────────


def test_marginal_zero_when_station_shares_the_cell():
    """Trạm cùng ô ⇒ cùng tập phủ ⇒ biên = 0, trùng phủ = 100% (bất biến C10)."""
    g = _grid()
    dem = kernel.demand_series(g[["h3_r8", "pop"]])
    net = _network([_offset(LAT, LNG, east_km=0.05)])
    cov = kernel.point_cells(LAT, LNG)
    assert kernel.marginal_pop(cov, net, dem) == 0.0
    assert kernel.local_pop(cov, dem) > 0.0


def test_marginal_is_full_catchment_when_network_is_far():
    """Trạm cách > 2R ⇒ hai đĩa rời nhau ⇒ biên = toàn bộ catchment."""
    g = _grid()
    dem = kernel.demand_series(g[["h3_r8", "pop"]])
    far = _offset(LAT, LNG, east_km=3 * params.R_SERVICE_KM)
    net = _network([far])
    cov = kernel.point_cells(LAT, LNG)
    assert kernel.marginal_pop(cov, net, dem) == pytest.approx(kernel.local_pop(cov, dem))


def test_partial_overlap_marginal_matches_cellwise_oracle():
    """Chồng một phần: biên phải bằng tổng ô nằm trong đĩa điểm mà NGOÀI đĩa trạm."""
    g = _grid()
    dem = kernel.demand_series(g[["h3_r8", "pop"]])
    sla, slng = _offset(LAT, LNG, east_km=params.R_SERVICE_KM)  # tâm cách đúng R
    net = _network([(sla, slng)])
    cov = set(kernel.point_cells(LAT, LNG)) & set(g["h3_r8"])

    # oracle: tính lại phủ của trạm bằng lọc bán kính trên tâm Ô CỦA TRẠM (đúng C10)
    s_center = h3.cell_to_latlng(h3.latlng_to_cell(sla, slng, 8))
    d = haversine_km(s_center[0], s_center[1], g["lat"].to_numpy(), g["lng"].to_numpy())
    s_cov = set(g.loc[d <= params.R_SERVICE_KM, "h3_r8"])

    want = cov - s_cov
    assert kernel.marginal_pop(kernel.point_cells(LAT, LNG), net, dem) == pytest.approx(len(want) * POP_PER_CELL)
    assert 0 < len(want) < len(cov), "cấu hình phải chồng MỘT PHẦN, không rời cũng không trùm"


# ───────────────────────── 4. bất biến không được vi phạm ─────────────────────


def test_purge_removes_station_from_every_fact():
    """Retrodiction purge phải rút trạm khỏi CẢ khoảng cách LẪN tập phủ — không chỉ một."""
    g = _grid()
    dem = kernel.demand_series(g[["h3_r8", "pop"]])
    st = pd.DataFrame(
        [{"station_id": "st-0", "lat": LAT, "lng": LNG, "h3_r8": h3.latlng_to_cell(LAT, LNG, 8), "num_connectors": 2}]
    )
    kept, purged = kernel.build_network(st), kernel.build_network(st, exclude_station_ids=["st-0"])
    cov = kernel.point_cells(LAT, LNG)
    assert purged.n_excluded == 1 and kept.n_excluded == 0
    assert kernel.marginal_pop(cov, kept, dem) == 0.0
    assert kernel.marginal_pop(cov, purged, dem) == pytest.approx(kernel.local_pop(cov, dem))
    assert np.isinf(kernel.nearest_info(purged, np.array([LAT]), np.array([LNG]))["d_nearest_m"][0])
