"""B8 — test cho chính bộ kiểm bẫy: oracle phải BẮT được lệch, không chỉ gật đầu.

Một bộ kiểm luôn báo "0 lỗi" thì vô dụng. Ở đây ta bơm lệch giả vào rồi đòi nó đỏ.
"""

import h3
import numpy as np
import pandas as pd
import pytest

from ev_siting.aoi import haversine_km
from ev_siting.assess import params, spotcheck

LAT, LNG = 21.0000, 105.8000


@pytest.fixture
def world():
    """Một trạm cách 500 m về phía đông; lưới cầu 100 dân/ô."""
    from ev_siting.aoi import EARTH_R_KM

    s_lng = LNG + np.degrees(0.5 / (EARTH_R_KM * np.cos(np.radians(LAT))))
    st = pd.DataFrame([{"lat": LAT, "lng": s_lng, "h3_r8": h3.latlng_to_cell(LAT, s_lng, 8), "num_connectors": 3}])
    cells = sorted(h3.grid_disk(h3.latlng_to_cell(LAT, LNG, 8), 10))
    ll = np.array([h3.cell_to_latlng(c) for c in cells])
    dem = pd.DataFrame({"h3_r8": cells, "pop": 100.0, "lat": ll[:, 0], "lng": ll[:, 1]})
    return st, dem


def test_oracle_reproduces_hand_computed_distance(world):
    st, dem = world
    o = spotcheck._oracle(LAT, LNG, st, dem, params.R_SERVICE_KM)
    want = haversine_km(LAT, LNG, st["lat"].iloc[0], st["lng"].iloc[0]) * 1000.0
    assert o["d_nearest_m"] == pytest.approx(want, rel=1e-9)
    assert o["n_within_1km"] == 1 and o["connectors_within_r"] == 3.0
    assert o["pop_cell"] == pytest.approx(100.0)
    assert o["pop_catchment"] > o["pop_cell"]


def test_oracle_marginal_is_zero_when_station_is_adjacent(world):
    """Trạm cách 500 m ⇒ hai đĩa gần trùng, nhưng KHÔNG trùng: biên phải > 0 và < toàn bộ."""
    st, dem = world
    o = spotcheck._oracle(LAT, LNG, st, dem, params.R_SERVICE_KM)
    assert 0 < o["n_marginal_pop"] < o["pop_catchment"]


def test_compare_is_silent_when_facts_agree(world):
    st, dem = world
    o = spotcheck._oracle(LAT, LNG, st, dem, params.R_SERVICE_KM)
    assert spotcheck._compare(dict(o), o) == []


@pytest.mark.parametrize(
    "key,delta",
    [("d_nearest_m", 1.0), ("n_within_1km", 1), ("pop_catchment", 100.0), ("n_marginal_pop", 100.0)],
)
def test_compare_catches_injected_drift(world, key, delta):
    """Bơm lệch 1 m / 1 trạm / 100 dân — bộ kiểm phải đỏ, nếu không nó vô dụng."""
    st, dem = world
    o = spotcheck._oracle(LAT, LNG, st, dem, params.R_SERVICE_KM)
    fact = dict(o)
    fact[key] = o[key] + delta
    bad = spotcheck._compare(fact, o)
    assert any(b.startswith(key) for b in bad), bad


def test_compare_catches_missing_and_nan(world):
    st, dem = world
    o = spotcheck._oracle(LAT, LNG, st, dem, params.R_SERVICE_KM)
    assert spotcheck._compare({**o, "pop_cell": None}, o)
    assert spotcheck._compare({**o, "pop_cell": np.nan}, o)


def test_trap_list_is_20_points_and_geographically_spread():
    assert len(spotcheck.TRAP_POINTS) == 20
    assert len({p[0] for p in spotcheck.TRAP_POINTS}) == 20, "point_id phải duy nhất"
    assert len({p[2] for p in spotcheck.TRAP_POINTS}) >= 8, "phải trải nhiều tỉnh/TP, không dồn 1 chỗ"
    for _, _, _, lat, lng in spotcheck.TRAP_POINTS:
        assert 8.0 <= lat <= 23.7 and 102.0 <= lng <= 110.0, "toạ độ phải nằm trong bbox Việt Nam"
