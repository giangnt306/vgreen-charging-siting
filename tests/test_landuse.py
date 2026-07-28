"""Tests cho tầng land-use (P5): STRtree point-in-zone + phạt mềm vector hoá."""
import numpy as np
from shapely import STRtree
from shapely.geometry import Point, Polygon


def test_strtree_within_predicate_direction():
    """Khoá chiều predicate của shapely: điểm-trong-vùng-cấm dùng `within`,
    KHÔNG phải `contains` (point.contains(poly) luôn False → bug 0 ô bị loại)."""
    poly = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])  # ô vuông quanh (1,1)
    tree = STRtree([poly])
    pts_in = np.array([Point(1, 1)], dtype=object)
    pts_out = np.array([Point(5, 5)], dtype=object)

    # within: point.within(poly) — đúng chiều
    hit = tree.query(pts_in, predicate="within")
    assert hit.shape[1] == 1, "điểm trong polygon phải khớp với predicate 'within'"

    # contains (sai chiều): point.contains(poly) luôn False -> 0 khớp
    wrong = tree.query(pts_in, predicate="contains")
    assert wrong.shape[1] == 0

    # điểm ngoài -> không khớp
    assert tree.query(pts_out, predicate="within").shape[1] == 0


def test_flag_lists_vectorized():
    """`_flag_lists` gán cờ theo mask boolean, nối vào list gốc, khử trùng + sort."""
    from ev_siting.data.landuse.build_buildable_h3 import _flag_lists
    base = [["OSM"], [], ["OSM"]]
    masks = {
        "WATER": np.array([True, False, False]),
        "NOT_BUILT_UP": np.array([True, True, False]),
    }
    out = _flag_lists(masks, base_lists=base)
    assert out[0] == ["NOT_BUILT_UP", "OSM", "WATER"]
    assert out[1] == ["NOT_BUILT_UP"]
    assert out[2] == ["OSM"]


def test_substation_distance_balltree():
    """BallTree haversine trả khoảng cách hợp lý (m); inf khi không có trạm."""
    import pandas as pd

    from ev_siting.data.landuse.build_buildable_h3 import _dist_to_substations_m
    cells = np.array([[21.0, 105.8], [10.77, 106.70]])
    subs = pd.DataFrame({"lat": [21.001], "lng": [105.801]})
    d = _dist_to_substations_m(cells, subs)
    assert d[0] < 200          # ~140 m tới trạm gần
    assert d[1] > 1_000_000    # HCM cách trạm ở HN > 1000 km
    # không có trạm -> inf
    d2 = _dist_to_substations_m(cells, pd.DataFrame(columns=["lat", "lng"]))
    assert np.isinf(d2).all()
