"""Tests cho ngữ nghĩa POI (E-DQ7c): phân lớp, khử trùng, gộp khu, suy dẫn cột."""
import pandas as pd

from ev_siting.data.osm import poi_semantics as ps


def test_class_columns_have_no_name_collision_with_derived():
    """Khoá lỗi bảng LỚP ghi đè cột SUY RA.

    Nếu `poi_*` (lớp) trùng tên `n_*` (suy ra) thì `derive()` đọc và ghi cùng một cột:
    số vẫn "hợp lệ" nhưng cổng `poi_layer_sum_eq_points` mất khả năng bắt lệch nhãn —
    đúng chế độ lỗi im lặng mà cổng ② của E-DQ7b đã bắt được ở tầng đường.
    """
    assert not (set(ps.CLASS_COLUMNS) & set(ps.DERIVED_COLUMNS))
    assert all(c.startswith("poi_") for c in ps.CLASS_COLUMNS)
    assert all(c.startswith(("n_", "apartment_")) for c in ps.DERIVED_COLUMNS)


def test_retired_columns_are_gone():
    """`n_poi`/`n_parking` KHAI TỬ — đổi tên để consumer cũ gãy to, không đổi nghĩa ngầm."""
    assert "n_poi" not in ps.DERIVED_COLUMNS
    assert "n_parking" not in ps.DERIVED_COLUMNS


def test_classify_splits_units_inside_a_crawl_group():
    """Lẫn đơn vị nằm BÊN TRONG nhóm crawl, không chỉ giữa các nhóm."""
    assert ps.classify("retail", {"shop": "supermarket"}) == "SUPERMARKET"
    assert ps.classify("retail", {"amenity": "marketplace"}) == "MARKET"
    assert ps.classify("mall", {"shop": "mall"}) == "MALL"
    assert ps.classify("mall", {"shop": "department_store"}) == "DEPT_STORE"
    assert ps.classify("parking", {"parking": "multi-storey"}) == "PARKING_OFF"
    assert ps.classify("parking", {"parking": "street_side"}) == "PARKING_STREET"
    assert ps.classify("parking", {}) == "PARKING_OFF"          # 70% không có tag `parking`


def test_every_class_has_a_crawl_group():
    """**Cổng chống E-DQ7g.** Một lớp có trong `CLASSES` mà không có nhóm crawl nào sinh
    ra nó thì mọi cổng QA vẫn lặp qua nó và luôn đo 0 — "lớp THIẾU" trông y hệt "lớp
    THƯA". Đó chính là thứ đã giấu `PARK` nhiều tuần. Khoá cả hai chiều.
    """
    from ev_siting.data.osm.overpass_poi import CATEGORIES
    produced = {ps.classify(cat, tags)
                for cat in CATEGORIES
                for tags in ({}, {"shop": "mall"}, {"shop": "department_store"},
                             {"shop": "supermarket"}, {"amenity": "marketplace"},
                             {"parking": "street_side"})} - {None}
    assert produced == set(ps.CLASSES), (
        f"lớp không có nhóm crawl: {set(ps.CLASSES) - produced}; "
        f"lớp crawl ra mà không khai: {produced - set(ps.CLASSES)}")


def test_hospital_and_school_classes(tmp_path):
    """HOSPITAL/SCHOOL thêm 07/08 — ba chỗ phải đồng bộ, đúng tiền lệ PARK."""
    from ev_siting.data.osm.overpass_poi import CATEGORIES
    for cls, cat in (("HOSPITAL", "hospital"), ("SCHOOL", "school")):
        assert cls in ps.CLASSES
        assert cat in CATEGORIES
        assert ps.classify(cat, {}) == cls
        assert ps.n_col(cls) in ps.CLASS_COLUMNS

    # `healthcare=hospital` KHÔNG bao trọn `amenity=hospital` -> phải OR cả hai.
    assert len(CATEGORIES["hospital"]) == 2

    # C1 — trích xuất tách khỏi chính sách: bảng LỚP có cột, cột SUY RA thì CHƯA.
    # Biến thành covariate cầu là quyết định của E-DQ7d, không phải hệ quả phụ.
    assert "n_hospital" not in ps.DERIVED_COLUMNS
    assert "n_school" not in ps.DERIVED_COLUMNS


def test_superstore_stays_out():
    """SUPERSTORE đã cân nhắc và loại (đo: ~3,8% polygon, 48/79 khớp là WinMart)."""
    assert "SUPERSTORE" not in ps.CLASSES


def test_access_keeps_unknown_and_customers():
    """P8 — không loại ngầm cái KHÔNG BIẾT; bãi đỗ khách của TTTM là chỗ sạc công cộng."""
    assert ps.access_of({}) == "UNKNOWN"
    assert ps.access_of({"access": "customers"}) == "PUBLIC"
    assert ps.access_of({"access": "private"}) == "RESTRICTED"


def test_derive_subtracts_restricted_only_for_parking():
    """Chính sách trừ `access=RESTRICTED` chỉ áp cho parking (lớp duy nhất có tag này)."""
    row = {c: 0 for c in ps.CLASS_COLUMNS}
    row[ps.n_col("PARKING_OFF")] = 10
    row[ps.restricted_col("PARKING_OFF")] = 3
    row[ps.n_col("FUEL")] = 5
    row[ps.restricted_col("FUEL")] = 2          # có tag nhưng KHÔNG bị trừ
    out = ps.derive(pd.DataFrame([row])).iloc[0]

    assert out["n_parking_off"] == 7
    assert out["n_fuel"] == 5


def test_single_link_groups_merges_towers_not_neighbourhoods():
    """C6 — các toà cách nhau <150 m gộp về MỘT khu; khu cách xa thì không gộp.

    Đây là số quyết định: 5.157 toà chung cư trên toàn quốc gộp về **1.370 khu**. Nếu
    hàm này hỏng, một khu đô thị lại thành 5–10 "điểm sinh cầu" trong khi một trung tâm
    thương mại chỉ tính 1.
    """
    # 3 toà trong một khu (cách nhau ~100 m) + 1 toà cách 2 km
    lat = [21.0000, 21.0009, 21.0018, 21.0200]
    lng = [105.8000, 105.8000, 105.8000, 105.8000]
    groups = ps.single_link_groups(lat, lng, ps.COMPLEX_RADIUS_M)

    assert groups[0] == groups[1] == groups[2]
    assert groups[3] != groups[0]
    assert len(set(groups)) == 2


def test_neighbour_pairs_respects_group_labels():
    """Khử trùng vật lý chỉ ghép trong CÙNG lớp — cây xăng và bãi đỗ cùng góc phố là
    hai đối tượng thật, không phải bản trùng."""
    lat, lng = [21.0, 21.00005], [105.8, 105.8]      # ~5,5 m
    same_class = list(ps.neighbour_pairs(lat, lng, ps.DUP_RADIUS_M,
                                         same_group=["FUEL", "FUEL"]))
    diff_class = list(ps.neighbour_pairs(lat, lng, ps.DUP_RADIUS_M,
                                         same_group=["FUEL", "PARKING_OFF"]))
    assert same_class == [(0, 1)]
    assert diff_class == []


def test_trip_gen_interim_counts_complexes_not_buildings():
    """Điểm sinh cầu tạm thời: chung cư đếm theo KHU, đỗ ven đường không tính."""
    df = pd.DataFrame([{"n_mall": 1, "n_dept_store": 0, "n_supermarket": 0,
                        "n_market": 0, "n_apartment": 40, "n_apartment_complex": 2,
                        "n_parking_street": 9}])
    assert float(ps.trip_gen_interim(df).iloc[0]) == 3.0     # 1 mall + 2 khu
