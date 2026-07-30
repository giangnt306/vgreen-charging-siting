"""E-DQ3 — khoá ngữ nghĩa tầng hành chính.

Các test dưới đây khoá đúng những chỗ mà một bản "đơn giản hoá" sẽ làm hỏng trong im
lặng, vì mọi cột vẫn có giá trị và không exception nào được ném:

  1. gán ô bằng **tâm ô** thay vì **giao lục giác** (E-DQ7a đã đo là lệch 11 lần; trên
     lưới hiện tại là 2.926 ô / 475.083 người);
  2. dùng **nhãn** `commune_name` để cộng khối lượng thay vì bảng phân bổ có trọng số
     (40,0% dân số nằm ở ô vắt >= 2 xã);
  3. gán nhãn cho trạm **chưa resolve toạ độ** (biến lỗi đã biết thành một sự thật hành
     chính trông rất thuyết phục);
  4. snap toạ độ ngoài mọi xã **không giới hạn khoảng cách** (dải rỗng đo được là
     0,374 -> 2,100 km).

Test dùng hình học TỔNG HỢP nên chạy được không cần artefact VNSDI, trừ các test có mark
`needs_vnsdi`.
"""
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon, box

import h3

from ev_siting.data.admin import boundaries
from ev_siting.data.admin.boundaries import (_kind, cell_overlaps,
                                             labels_from_overlaps)
from ev_siting.data.admin.enrich_stations import _bare, _norm
from ev_siting.data.admin.paths import ADMIN_SNAP_TOL_M
from ev_siting.data.vnsdi.paths import COMMUNES_PARQUET

CENTER = h3.latlng_to_cell(21.0278, 105.8342, 8)     # Hà Nội


def _frame(rows):
    return pd.DataFrame(rows, columns=["commune_code", "province_name", "admin_l1_code",
                                       "commune_name", "commune_kind", "dientich_km2",
                                       "danso", "geometry"])


@pytest.fixture
def patch_communes(monkeypatch):
    """Thay lớp xã bằng hình học tổng hợp. Cache của `load_communes`/`_tree` PHẢI xoá ở
    cả hai đầu — nếu không, một test dùng lớp giả sẽ đầu độc mọi test sau nó."""
    real = boundaries.load_communes

    def _install(com):
        real.cache_clear()
        boundaries._tree.cache_clear()
        monkeypatch.setattr(boundaries, "load_communes", lambda: com)
        boundaries._tree.cache_clear()
        return com
    yield _install
    monkeypatch.undo()
    real.cache_clear()
    boundaries._tree.cache_clear()


@pytest.fixture
def fake_communes(patch_communes):
    """Hai xã kề nhau chia đôi ô `CENTER` theo kinh tuyến đi qua tâm ô."""
    la, lo = h3.cell_to_latlng(CENTER)
    return patch_communes(_frame([
        ["W001", "Tỉnh Tây", "90", "Xã Phía Tây", "XA", 1.0, 100,
         box(lo - 1.0, la - 1.0, lo, la + 1.0)],
        ["E002", "Tỉnh Đông", "91", "Phường Phía Đông", "PHUONG", 1.0, 200,
         box(lo, la - 1.0, lo + 1.0, la + 1.0)],
    ]))


# --------------------------------------------------------------------------- #
# commune_kind / chuẩn hoá tên                                                 #
# --------------------------------------------------------------------------- #
def test_commune_kind_from_prefix():
    assert _kind("Phường Ba Đình") == "PHUONG"
    assert _kind("Xã Cần Giờ") == "XA"
    assert _kind("Đặc khu Côn Đảo") == "DAC_KHU"
    # cải cách 2025 bỏ `Thị trấn` -> không được lặng lẽ gán vào XA/PHUONG
    assert _kind("Thị trấn Cũ") == "UNKNOWN"


def test_bare_strips_unit_prefix_and_diacritics():
    assert _bare("Phường Ba Đình") == "ba dinh"
    assert _bare("Xã Kỳ Xuân") == "ky xuan"
    assert _norm("Tỉnh Bà Rịa - Vũng Tàu") == "tinh ba ria vung tau"


# --------------------------------------------------------------------------- #
# Ô: lục giác ∩ polygon, KHÔNG phải tâm ô                                      #
# --------------------------------------------------------------------------- #
def test_cell_touching_two_communes_gets_two_rows(fake_communes):
    ov = cell_overlaps([CENTER])
    assert set(ov["commune_code"]) == {"W001", "E002"}, "ô vắt xã phải có 2 dòng phân bổ"


def test_weights_sum_to_one_per_cell(fake_communes):
    ov = cell_overlaps([CENTER])
    assert ov.groupby("h3_r8")["w"].sum().iloc[0] == pytest.approx(1.0)


def test_area_frac_is_raw_share_not_normalised(fake_communes):
    """`area_frac` là tỉ lệ THÔ (dùng làm độ tin của nhãn), `w` mới là trọng số chia."""
    ov = cell_overlaps([CENTER])
    assert ov["area_frac"].sum() == pytest.approx(1.0, abs=1e-6)   # 2 xã phủ kín ô này
    assert (ov["area_frac"] < 0.99).all(), "không xã nào chiếm trọn ô bị chia đôi"


def test_label_is_argmax_not_first_hit(fake_communes):
    ov = cell_overlaps([CENTER])
    lab = labels_from_overlaps(ov).iloc[0]
    winner = ov.sort_values("area_frac", ascending=False).iloc[0]
    assert lab["commune_code"] == winner["commune_code"]
    assert lab["admin_frac"] == pytest.approx(winner["area_frac"])
    assert lab["n_communes"] == 2


def test_cell_outside_every_commune_has_no_row(fake_communes):
    """Không gán bừa: ô ngoài mọi xã VẮNG MẶT (phần dư được công bố ở report)."""
    far = h3.latlng_to_cell(9.0, 107.0, 8)            # giữa Biển Đông
    assert cell_overlaps([far]).empty


def test_hexagon_test_beats_centroid_test(patch_communes):
    """Ô mà TÂM rơi ngoài mọi xã nhưng LỤC GIÁC vẫn chạm — đúng 2.926 ô thật ngoài đời."""
    la, lo = h3.cell_to_latlng(CENTER)
    edge_lo = max(p[1] for p in h3.cell_to_boundary(CENTER))
    strip = Polygon([(edge_lo - 1e-4, la - 1), (edge_lo + 1, la - 1),
                     (edge_lo + 1, la + 1), (edge_lo - 1e-4, la + 1)])
    patch_communes(_frame([["S001", "Tỉnh Rìa", "92", "Xã Rìa", "XA", 1.0, 1, strip]]))
    assert not strip.contains(Point(lo, la)), "tâm ô phải nằm NGOÀI để test có nghĩa"
    assert not cell_overlaps([CENTER]).empty, "giao lục giác phải bắt được ô này"


# --------------------------------------------------------------------------- #
# Điểm: point-in-polygon + dung sai snap                                       #
# --------------------------------------------------------------------------- #
def test_point_inside_gets_label(fake_communes):
    la, lo = h3.cell_to_latlng(CENTER)
    out = boundaries.assign_points([la], [lo - 0.01])
    assert out["commune_code"].iloc[0] == "W001"
    assert out["admin_src"].iloc[0] == "inside"
    assert out["admin_dist_m"].iloc[0] == 0.0


def test_point_just_outside_is_snapped(fake_communes):
    """Bờ biển bị tổng quát hoá ở tỉ lệ 1:1M -> trạm ven biển thật rơi ra vài chục mét."""
    la, lo = h3.cell_to_latlng(CENTER)
    out = boundaries.assign_points([la], [lo + 1.0 + 100 * boundaries.DEG_PER_M])
    assert out["admin_src"].iloc[0] == "nearest"
    assert out["commune_code"].iloc[0] == "E002"
    assert out["admin_dist_m"].iloc[0] == pytest.approx(100.0, rel=0.1)


def test_point_far_outside_is_not_guessed(fake_communes):
    """Quá dung sai thì KHÔNG đoán — đây là tín hiệu lỗi toạ độ, không phải join hụt."""
    la, lo = h3.cell_to_latlng(CENTER)
    out = boundaries.assign_points([la], [lo + 1.0 + 5 * ADMIN_SNAP_TOL_M * boundaries.DEG_PER_M])
    assert out["admin_src"].iloc[0] == "none"
    assert out["commune_code"].iloc[0] is None


def test_nan_coord_yields_no_label(fake_communes):
    out = boundaries.assign_points([np.nan], [np.nan])
    assert out["admin_src"].iloc[0] == "none"
    assert out["commune_code"].iloc[0] is None


# --------------------------------------------------------------------------- #
# Bất biến trên artefact thật (bỏ qua nếu chưa `make vnsdi`)                   #
# --------------------------------------------------------------------------- #
needs_vnsdi = pytest.mark.skipif(not COMMUNES_PARQUET.exists(),
                                 reason="chưa có communes.parquet (`make vnsdi`)")


@needs_vnsdi
def test_commune_layer_is_disjoint_cover():
    """Giả định nền của `assign_points` ('hit đầu tiên = hit duy nhất'): lớp xã không
    chồng lấn. Nếu VNSDI phát hành bản có polygon chồng nhau, test này FAIL chứ không
    để nhãn phụ thuộc thứ tự dòng."""
    com = boundaries.load_communes()
    assert len(com) == com["commune_code"].nunique()
    la = np.array([21.0278, 10.7626, 16.0544, 20.8449, 12.2388])
    lo = np.array([105.8342, 106.6602, 108.2022, 106.6881, 109.1967])
    out = boundaries.assign_points(la, lo)
    assert (out["admin_src"] == "inside").all()
    assert out["admin_l1_code"].notna().all()


@needs_vnsdi
def test_provinces_are_dissolve_of_communes():
    """34 tỉnh = dissolve xã theo `admin_l1_code` -> tổng dân/diện tích khớp theo xây
    dựng (không có cơ hội lệch niên đại giữa hai lớp)."""
    com, prov = boundaries.load_communes(), boundaries.load_provinces()
    assert len(prov) == 34
    assert prov["danso"].sum() == com["danso"].sum()
    assert prov["n_communes"].sum() == len(com)
