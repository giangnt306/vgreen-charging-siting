"""Tests cho ev_siting.aoi — hình học vùng nghiên cứu (P5)."""
import h3
import numpy as np

from ev_siting.aoi import AOI, haversine_km, resolve_aoi


def test_haversine_known_distance():
    # Hà Nội -> HCM ~ 1140 km (great-circle)
    d = haversine_km(21.0278, 105.8342, 10.7769, 106.7009)
    assert 1100 < d < 1200


def test_haversine_vectorized():
    lat2 = np.array([21.0278, 10.7769])
    lng2 = np.array([105.8342, 106.7009])
    d = haversine_km(21.0278, 105.8342, lat2, lng2)
    assert d.shape == (2,)
    assert d[0] < 1e-6            # cùng điểm -> 0
    assert 1100 < d[1] < 1200


def test_core_vs_buffer():
    aoi = AOI("t", 21.0, 105.8, radius_km=10.0, buffer_km=5.0)
    assert aoi.outer_radius_km == 15.0
    # điểm cách tâm ~12 km: ngoài lõi nhưng trong buffer
    far = AOI("t", 21.0, 105.8, radius_km=10.0, buffer_km=5.0)
    # dịch ~12km về bắc: 12/111.32 độ vĩ
    lat = 21.0 + 12.0 / 111.32
    assert far.contains(lat, 105.8)
    assert not far.in_core(lat, 105.8)


def test_cells_all_within_outer_radius():
    aoi = AOI("t", 21.0, 105.8, radius_km=8.0, buffer_km=2.0)
    cells = aoi.cells()
    assert len(cells) > 0
    # mọi ô trả về phải có tâm trong bán kính ngoài
    for c in cells:
        lat, lng = h3.cell_to_latlng(c)
        assert aoi.dist_km(lat, lng) <= aoi.outer_radius_km + 1e-9
    # tâm AOI luôn nằm trong tập ô
    assert h3.latlng_to_cell(21.0, 105.8, 8) in set(cells)


def test_cells_unique():
    aoi = AOI("t", 10.7769, 106.7009, radius_km=15.0, buffer_km=5.0)
    cells = aoi.cells()
    assert len(cells) == len(set(cells))


def test_resolve_preset_and_override():
    a = resolve_aoi("hanoi")
    assert a.name == "hanoi" and a.radius_km > 0
    b = resolve_aoi("hanoi", radius_km=5.0, buffer_km=1.0)
    assert b.radius_km == 5.0 and b.buffer_km == 1.0
    # override tâm tự do cho thành phố lạ
    c = resolve_aoi("elsewhere", lat=16.0, lng=108.0, radius_km=10.0)
    assert c.lat == 16.0 and c.lng == 108.0


def test_bbox_encloses_cells():
    aoi = AOI("t", 21.0, 105.8, radius_km=8.0, buffer_km=2.0)
    s, w, n, e = aoi.bbox()
    for c in aoi.cells():
        lat, lng = h3.cell_to_latlng(c)
        assert s - 0.02 <= lat <= n + 0.02
        assert w - 0.02 <= lng <= e + 0.02
