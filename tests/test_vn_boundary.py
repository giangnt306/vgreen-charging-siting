"""E-DQ7a (Kỳ: E-DQ11) — khoá việc cắt theo ĐA GIÁC lãnh thổ, và cái bẫy đã giấu lỗi.

Bẫy: `VN_BBOX` là hình chữ nhật (8..23,7 N × 102..110 E). Nó trùm Đông Bắc Thái Lan, Nam
Lào, phần lớn Campuchia và Quảng Tây/Vân Nam. Overpass truy vấn theo bbox đó, không ai
cắt lại, và cổng kiểm tra `poi_coords_in_vn` cũ trong `validate.py` cũng chỉ so với
**cùng cái bbox** — nên nó luôn PASS trong khi 20.256/37.362 POI (54,2%) nằm ngoài Việt
Nam. Sản phẩm cuối: 6.881/28.075 candidate (24,5%) ngoài lãnh thổ, riêng T1 fuel 67,5%.

Bài học: cổng hỏi sai câu hỏi thì không bao giờ đỏ. Test dưới đây hỏi bằng đa giác.

Sau hợp nhất 2026-07-30:
  - Nguồn ranh giới lãnh thổ: polygon adm2 OSM rel 49915 trích từ `.pbf` freeze
    (`ev_siting.data.osm.vn_boundary`) — polygon gồm cả lãnh hải.
  - Chính sách artefact FAIL-CLOSED: `POI_POINTS` chỉ chứa dòng trong VN, phần cắt
    tách sang `POI_OUTSIDE_VN` để audit.
  - Test cũ `test_admin_dir_shared_with_admin_join` (bất biến "trạm và POI cắt cùng
    một bản đồ") ĐÃ GỠ có chủ đích: nhãn admin nay lấy từ VNSDI (gói `data/admin/`),
    lãnh thổ cắt theo adm2 PBF — hai bản đồ cho hai việc, không còn `admin_dir` chung.
"""

import numpy as np
import pandas as pd
import pytest

from ev_siting.data.osm.build_osm_h3 import poi_layers
from ev_siting.data.osm.paths import VN_BBOX, VN_BOUNDARY
from ev_siting.data.osm.vn_boundary import classify_cells, points_in_vn

needs_boundary = pytest.mark.skipif(
    not VN_BOUNDARY.exists(),
    reason="thiếu vn_boundary.parquet (chạy `make boundary`)")

# (nhãn, lat, lng, có thuộc VN không) — toạ độ thật, quan sát trong dữ liệu hoặc tra bản đồ
CASES = [
    ("PTT Khon Kaen (TH)", 16.4134, 102.8188, False),  # node/371154605 trong POI cũ
    ("Phnom Penh (KH)", 11.5564, 104.9282, False),
    ("Nam Ninh, Quảng Tây (CN)", 22.8170, 108.3665, False),
    ("Savannakhet (LA)", 16.5560, 104.7530, False),
    ("Hà Nội", 21.0278, 105.8342, True),
    ("Mũi Cà Mau", 8.5900, 104.8400, True),
    ("Phú Quốc", 10.2270, 103.9640, True),
    ("Côn Đảo", 8.6833, 106.6000, True),
    ("Bạch Long Vĩ", 20.1330, 107.7250, True),
]


def _in_bbox(lat, lng):
    s, w, n, e = VN_BBOX
    return s <= lat <= n and w <= lng <= e


@needs_boundary
@pytest.mark.parametrize("label,lat,lng,expected", CASES)
def test_polygon_beats_bbox(label, lat, lng, expected):
    assert bool(points_in_vn([lat], [lng])[0]) is expected, label


@needs_boundary
def test_bbox_alone_would_have_passed_the_foreign_points():
    """Chứng minh vì sao cổng cũ vô dụng: cả 4 điểm nước ngoài đều LỌT bbox."""
    foreign = [(la, lo) for _, la, lo, ok in CASES if not ok]
    assert all(_in_bbox(la, lo) for la, lo in foreign)
    assert not points_in_vn([la for la, _ in foreign], [lo for _, lo in foreign]).any()


@needs_boundary
def test_cells_touching_uses_intersects_not_just_centre():
    """Ô biên giới rộng ~0,85 km²: tâm bên kia biên KHÔNG được làm mất phần đất VN.

    Quy tắc tâm-trong xoá 74.642 dân VN thật; giao lục giác chỉ xoá 6.472 (đo trên
    polygon adm2 — docstring `vn_boundary.py` §2). Vì vậy tập ô "chạm VN"
    (`cell_state != OUTSIDE` của `classify_cells`) phải là TẬP CHA của tập ô tâm-trong.
    """
    import h3

    from ev_siting.data.worldpop.paths import DEMAND_H3

    if not DEMAND_H3.exists():
        pytest.skip("chưa có demand_h3.parquet")
    d = pd.read_parquet(DEMAND_H3, columns=["h3_r8"])
    cells = d["h3_r8"].to_numpy()[:60000]
    ll = np.array([h3.cell_to_latlng(c) for c in cells])
    centre = points_in_vn(ll[:, 0], ll[:, 1])
    # classify_cells giữ nguyên thứ tự input -> mask thẳng hàng với `centre`
    touch = (classify_cells(cells)["cell_state"] != "OUTSIDE").to_numpy()
    assert touch.sum() >= centre.sum()
    assert bool((touch | ~centre).all()), "mọi ô tâm-trong phải nằm trong tập chạm"


@needs_boundary
def test_poi_points_artifact_has_no_foreign_rows():
    """Hàng rào fail-closed: file POI đã ghi ra không được còn dòng ngoài lãnh thổ."""
    from ev_siting.data.osm.paths import POI_POINTS

    if not POI_POINTS.exists():
        pytest.skip("chưa có osm_poi_points.parquet")
    poi = pd.read_parquet(POI_POINTS)
    assert len(poi), "file POI rỗng — nghi cắt quá tay"
    n_out = int((~points_in_vn(poi["lat"], poi["lng"])).sum())
    assert n_out == 0, f"{n_out} POI ngoài đa giác lãnh thổ VN còn sót trong {POI_POINTS.name}"


@needs_boundary
def test_candidate_sites_have_no_foreign_rows():
    """Cổng cuối: đây là chỗ lỗi biến thành khuyến nghị đặt trạm."""
    from ev_siting.features.paths import CANDIDATE_SITES

    if not CANDIDATE_SITES.exists():
        pytest.skip("chưa có candidate_sites.parquet")
    c = pd.read_parquet(CANDIDATE_SITES, columns=["lat", "lng", "tier"])
    out = ~points_in_vn(c["lat"], c["lng"])
    bad = c[out]["tier"].value_counts().to_dict()

    # T1/T2 (POI) và T4 (tổng hợp) do E-DQ7a quản: phải sạch tuyệt đối. Trước khi cắt là
    # 6.881 điểm ngoài lãnh thổ (T1 fuel 4.527, T1 parking 1.449, T2 897, T4 4).
    assert {k: v for k, v in bad.items() if k != "T0"} == {}, f"candidate ngoài VN: {bad}"

    # T0 = trạm EVCS có thật; toạ độ của chúng là địa hạt của E-DQ1 (fix_coords), không
    # phải cắt biên. Đo 2026-07-29 trên lớp vn_admin: đúng 4 trạm ngoài ranh; polygon
    # adm2 (gồm lãnh hải) chỉ rộng hơn ven biển nên 4 vẫn là TRẦN. Chốt con số để nó
    # không âm thầm phình ra.
    assert bad.get("T0", 0) <= 4, f"số trạm T0 ngoài ranh giới tăng: {bad}"


def test_poi_layers_counts_only_in_vn_primary_rows():
    """Hợp đồng đếm sau hợp nhất: lọc lãnh thổ + khử trùng nằm ở `poi_layers`
    (`in_vn & is_poi_primary`), còn `run()` tách artefact fail-closed. Chốt hợp đồng
    để không ai lọc hai nơi rồi lệch nhau.

    (Thay cho test cũ `test_aggregate_counts_only_rows_it_is_given`: `aggregate` của
    bản hợp nhất nhận bảng LỚP đã gộp, không còn nhận điểm thô.)
    """
    cell = "8865b56601fffff"
    poi = pd.DataFrame({
        "h3_r8": [cell] * 4,
        "lat": [21.0] * 4,
        "lng": [105.8] * 4,
        "poi_class": ["FUEL"] * 4,
        "poi_access": ["PUBLIC"] * 4,
        "levels": [None] * 4,
        "in_vn": [True, True, False, True],
        "is_poi_primary": [True, True, True, False],
    })
    out = poi_layers(poi)
    assert int(out["poi_fuel"].iloc[0]) == 2
