"""Tests cho tầng Overture: ánh xạ taxonomy + ghép cặp không gian liên nguồn.

Khoá ba chế độ hỏng **im lặng** — cả ba đều làm số đối chiếu sai mà không ai thấy:
  1. hai nguồn nói khác bảng chữ (lớp lệch giữa `poi_semantics` và `poi_taxonomy`);
  2. ánh xạ tự phình bằng pattern (`%park%` nuốt `car_park`/`theme_park`);
  3. ghép cặp bucket quá nhỏ ⇒ bỏ sót cặp thật ⇒ "chỉ có ở 1 nguồn" bị thổi lên.
"""
import pytest

from ev_siting.data.osm import poi_semantics as ps
from ev_siting.data.overture import compare_osm as cmp
from ev_siting.data.overture import poi_taxonomy as tax


def test_shared_classes_exist_on_both_sides():
    """Điều kiện tiên quyết để so sánh: mọi lớp chung phải có nghĩa ở CẢ HAI nguồn."""
    assert set(tax.SHARED_CLASSES) <= set(ps.CLASSES)
    # PARKING_STREET không có đối ứng bên Overture -> phải nằm ở danh sách miễn trừ,
    # không được lặng lẽ có mặt trong SHARED_CLASSES rồi báo "Overture = 0".
    assert set(tax.NO_OVERTURE_EQUIVALENT) <= set(ps.CLASSES)
    assert not (set(tax.NO_OVERTURE_EQUIVALENT) & set(tax.SHARED_CLASSES))


def test_park_class_exists_on_osm_side():
    """Công viên: lớp được THÊM 07/08 — trước đó tầng POI không hề crawl `leisure=park`."""
    assert "PARK" in ps.CLASSES
    assert ps.classify("park", {}) == "PARK"
    from ev_siting.data.osm.overpass_poi import CATEGORIES
    assert "park" in CATEGORIES


def test_park_class_is_not_wired_into_demand_columns_yet():
    """Trích xuất tách khỏi chính sách (C1): bảng LỚP có `poi_park`, cột SUY RA thì chưa.

    Biến một lớp mới thành covariate cầu là quyết định của E-DQ7d, không phải hệ quả
    phụ của việc thêm nhóm crawl.
    """
    assert ps.n_col("PARK") in ps.CLASS_COLUMNS
    assert "n_park" not in ps.DERIVED_COLUMNS


def test_category_map_does_not_swallow_lookalikes():
    """Ánh xạ là danh sách ĐÓNG — các category 'trông giống' phải rơi ra ngoài."""
    for c in ("amusement_park", "water_park", "rv_park", "dog_park", "playground",
              "mobile_home_park", "beer_garden"):
        assert tax.classify(c) is None, c
    assert tax.classify("park") == "PARK"
    assert tax.classify("national_park") == "PARK"


def test_grocery_store_is_not_supermarket():
    """`grocery_store` = tạp hoá mặt phố, không phải siêu thị có bãi đỗ ô tô.

    Gộp nhầm sẽ tự chế ra 'Overture hơn OSM 20×' ở lớp SUPERMARKET.
    """
    assert tax.classify("grocery_store") == "CONVENIENCE"
    assert tax.classify("convenience_store") == "CONVENIENCE"
    assert tax.classify("supermarket") == "SUPERMARKET"
    assert "CONVENIENCE" not in tax.SHARED_CLASSES


def test_supply_side_categories_are_excluded():
    """Trạm sạc là CUNG — để nó vào covariate cầu là rò rỉ mục tiêu."""
    assert tax.classify("ev_charging_station") is None
    assert "ev_charging_station" in tax.EXCLUDED


def test_unmapped_report_ignores_explicit_exclusions_and_nan():
    cats = ["gas_station"] * 3 + ["amusement_park"] * 2 + ["mystery_market"] * 5 + [None, float("nan")]
    rows = dict(tax.unmapped_report(cats))
    assert rows == {"mystery_market": 5}       # đã ánh xạ / đã loại / NaN đều không kêu


# --- ghép cặp không gian --------------------------------------------------------
def test_cross_pairs_matches_brute_force_at_every_radius():
    """Bucket H3 phải cho kết quả BẰNG brute-force, nếu không 'chỉ có ở 1 nguồn' bị thổi.

    Đây chính là lý do `compare_osm` không dùng `poi_semantics.neighbour_pairs`: hàm đó
    bucket ở res 9 (tâm-tâm 0,37 km) nên chỉ bảo đảm tới ~185 m.
    """
    import random
    random.seed(7)
    a = [(21.0 + random.uniform(-0.02, 0.02), 105.8 + random.uniform(-0.02, 0.02))
         for _ in range(120)]
    b = [(21.0 + random.uniform(-0.02, 0.02), 105.8 + random.uniform(-0.02, 0.02))
         for _ in range(120)]
    la, ga = [p[0] for p in a], [p[1] for p in a]
    lb, gb = [p[0] for p in b], [p[1] for p in b]
    for r in (50.0, 100.0, 200.0, 300.0):
        got = set(cmp._cross_pairs(la, ga, lb, gb, r))
        want = {(i, j) for i in range(len(a)) for j in range(len(b))
                if ps.haversine_m(la[i], ga[i], lb[j], gb[j]) <= r}
        assert got == want, f"lệch brute-force ở {r} m"


def test_cross_pairs_refuses_radius_beyond_its_guarantee():
    """Thà nổ còn hơn trả về số ghép thiếu — bán kính > bảo đảm của res 8 phải raise."""
    with pytest.raises(ValueError):
        list(cmp._cross_pairs([21.0], [105.8], [21.0], [105.8], 900.0))
