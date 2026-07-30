"""E-DQ3 — port ý định `tests/test_admin_join.py` (Kỳ) sang API admin của Giang (Q4/B3 30/07).

Nguồn admin hợp nhất là VNSDI (`ev_siting.data.admin.*`), `admin_join.py` bị drop. File
này giữ đúng các bất biến "hỏng im lặng" mà bản Kỳ khoá — họ lỗi 0-match đã từng xảy ra
ở `evcs-dataset/src/evcs/transform/silver.py` — nhưng kiểm trên `assign_points`/
`enrich_admin` thay vì `assign_admin`:

  1. hoán trục lng/lat -> mọi điểm rơi ra ngoài, không exception nào được ném;
  2. thiếu lớp ranh giới phải DỪNG to (SystemExit), không im lặng trả admin rỗng;
  3. ranh giới chồng lấn không được fan-out dòng — một trạm đúng một nhãn;
  4. điểm ngoài mọi xã phải bị CỜ (`COORD_BAD`/`COORD_OUTSIDE_ADMIN`, loại khỏi cung),
     không được gán bừa xã gần nhất;
  5. nhãn ⟺ `coord_resolved` — không mặc "sự thật hành chính" lên toạ độ chưa resolve;
  6. lớp thật phải khớp số xã official (~3.321) — bảo vệ đính chính "609 xã lệch".

Bất biến đã có sẵn trong `tests/test_admin.py` (Giang) thì KHÔNG lặp lại ở đây: chiều
vị từ within (`test_point_inside_gets_label` chết ngay nếu đảo chiều — điểm trong sẽ
thành `nearest`), NaN null-safety, dải snap 500 m, lớp xã disjoint, 34 tỉnh dissolve.
Hai test đặc thù lớp OSM của bản Kỳ bỏ theo Q4: lọc LINESTRING (VNSDI chỉ có polygon)
và `SIDE_COLS` license-scope (nhãn VNSDI ghi thẳng canonical, không còn side-table ODbL).
"""
import pandas as pd
import pytest
from shapely.geometry import box

import h3

from ev_siting.data.admin import boundaries, enrich_stations
from ev_siting.data.admin.enrich_stations import enrich_admin
from ev_siting.data.vnsdi.paths import COMMUNES_PARQUET

CENTER = h3.latlng_to_cell(21.0278, 105.8342, 8)     # Hà Nội


def _frame(rows):
    return pd.DataFrame(rows, columns=["commune_code", "province_name", "admin_l1_code",
                                       "commune_name", "commune_kind", "dientich_km2",
                                       "danso", "geometry"])


@pytest.fixture
def patch_communes(monkeypatch):
    """Thay lớp xã bằng hình học tổng hợp — patch CẢ HAI chỗ giữ tham chiếu:
    `boundaries.load_communes` (nuôi `_tree`) và bản đã import vào `enrich_stations`
    (nuôi `build_crosswalk`). Cache xoá ở cả hai đầu như fixture của `test_admin.py`."""
    real = boundaries.load_communes

    def _install(com):
        real.cache_clear()
        boundaries._tree.cache_clear()
        monkeypatch.setattr(boundaries, "load_communes", lambda: com)
        monkeypatch.setattr(enrich_stations, "load_communes", lambda: com)
        boundaries._tree.cache_clear()
        return com
    yield _install
    monkeypatch.undo()
    real.cache_clear()
    boundaries._tree.cache_clear()


@pytest.fixture
def fake_communes(patch_communes):
    """Hai xã kề nhau chia đôi quanh tâm ô `CENTER` theo kinh tuyến (như test_admin.py)."""
    la, lo = h3.cell_to_latlng(CENTER)
    return patch_communes(_frame([
        ["W001", "Tỉnh Tây", "90", "Xã Phía Tây", "XA", 1.0, 100,
         box(lo - 1.0, la - 1.0, lo, la + 1.0)],
        ["E002", "Tỉnh Đông", "91", "Phường Phía Đông", "PHUONG", 1.0, 200,
         box(lo, la - 1.0, lo + 1.0, la + 1.0)],
    ]))


# --------------------------------------------------------------------------- #
# assign_points: trục toạ độ, chồng lấn, fail-loud                             #
# --------------------------------------------------------------------------- #
def test_axis_order_is_lng_lat(fake_communes):
    """`points(x=lng, y=lat)`. Hoán trục -> điểm trong xã rơi ra ngoài mọi ranh giới
    mà KHÔNG có lỗi nào — đúng bẫy 0-match bản Kỳ khoá."""
    la, lo = h3.cell_to_latlng(CENTER)
    swapped = boundaries.assign_points([lo], [la])  # cố ý đảo
    assert swapped["admin_src"].iloc[0] == "none"
    assert swapped["commune_code"].iloc[0] is None


def test_overlapping_boundaries_do_not_fan_out_rows(patch_communes):
    """VNSDI được kiểm là disjoint (`test_commune_layer_is_disjoint_cover`), nhưng
    `assign_points` không được PHỤ THUỘC điều đó: điểm rơi vào 2 polygon phải nhận
    ĐÚNG một nhãn, không nhân bản dòng (bản Kỳ: `n_multi_commune`, không fan-out)."""
    la, lo = h3.cell_to_latlng(CENTER)
    same = box(lo - 1.0, la - 1.0, lo + 1.0, la + 1.0)
    patch_communes(_frame([
        ["C1", "Tỉnh Thử", "90", "Xã A", "XA", 1.0, 1, same],
        ["C2", "Tỉnh Thử", "90", "Xã B", "XA", 1.0, 1, same],
    ]))
    out = boundaries.assign_points([la, la], [lo, lo])
    assert len(out) == 2  # KHÔNG fan-out
    assert out["commune_code"].isin(["C1", "C2"]).all()
    assert out["commune_name"].notna().all()


def test_missing_boundary_layer_fails_loudly(tmp_path, monkeypatch):
    """Thiếu lớp ranh giới phải DỪNG, không được im lặng trả admin rỗng."""
    boundaries.load_communes.cache_clear()
    boundaries._tree.cache_clear()
    monkeypatch.setattr(boundaries, "COMMUNES_PARQUET", tmp_path / "khong-ton-tai.parquet")
    with pytest.raises(SystemExit, match="make vnsdi"):
        boundaries.load_communes()
    boundaries.load_communes.cache_clear()


# --------------------------------------------------------------------------- #
# enrich_admin: ngoài-mọi-xã bị cờ chứ không gán bừa; nhãn ⟺ coord_resolved     #
# --------------------------------------------------------------------------- #
def _stations():
    la, lo = h3.cell_to_latlng(CENTER)
    rows = [
        # (station_id, lat, lng, coord_resolved, quality_flags, address)
        ("s0", la, lo - 0.5, True, [], "1 Duong Thu"),
        # toạ độ placeholder đo thật: chuỗi C.HNO* ở 9.0004/107.0004, ngoài biển Vũng Tàu
        ("s1", 9.000286, 107.000282, True, [], "so 7 pho gia lap"),
        ("s2", la - 0.1, lo - 0.5, False, [], "2 Duong Thu"),
        ("s3", la + 0.1, lo - 0.5, True, ["COORD_ADDR_MISMATCH"], "To 1, Xa Phia Tay"),
    ]
    return pd.DataFrame([
        {"station_id": sid, "station_code": f"C.X{i}", "lat": la_, "lng": lo_,
         "h3_r8": h3.latlng_to_cell(la_, lo_, 8), "province_code": "HNO",
         "name": f"Tram {sid}", "address": addr, "coord_resolved": res,
         "coord_src": "evcs", "quality_flags": fl}
        for i, (sid, la_, lo_, res, fl, addr) in enumerate(rows)
    ])


def test_station_outside_every_commune_is_flagged_not_silently_assigned(fake_communes):
    out = enrich_admin(_stations())
    assert len(out) == 4  # KHÔNG fan-out, KHÔNG xoá dòng
    r = out.set_index("station_id").loc["s1"]
    assert r["admin_verdict"] == "COORD_BAD"
    assert not r["coord_resolved"]          # loại khỏi cung
    assert pd.isna(r["h3_r8"])              # không neo phủ ở vị trí sai
    assert r["coord_src"] == "outside_admin"
    assert "COORD_OUTSIDE_ADMIN" in r["quality_flags"]
    # pandas hạ None -> NaN trong cột object; ý nghĩa vẫn là "không gán bừa"
    assert pd.isna(r["commune_code"])


def test_labels_iff_coord_resolved(fake_communes):
    out = enrich_admin(_stations()).set_index("station_id")
    # điểm trong xã + toạ độ đã resolve -> đủ nhãn
    assert out.loc["s0", "commune_code"] == "W001"
    assert out.loc["s0", "admin_src"] == "inside"
    assert out.loc["s0", "admin_verdict"] == "NOT_FLAGGED"
    # điểm trong xã NHƯNG chưa resolve (E-DQ1) -> KHÔNG nhãn: không mặc một sự thật
    # hành chính lên một lỗi đã biết
    assert pd.isna(out.loc["s2", "commune_code"])
    assert out.loc["s2", "admin_src"] == "unresolved"
    assert out.loc["s2", "admin_verdict"] == "NO_COORD"
    # E-DQ3c: COORD_ADDR_MISMATCH + văn bản địa chỉ xác nhận tên xã -> toạ độ ĐÚNG
    assert out.loc["s3", "admin_verdict"] == "COORD_CONFIRMED"
    assert out.loc["s3", "commune_code"] == "W001"
    # BẤT BIẾN hợp đồng: có nhãn ⟺ coord_resolved (cả hai chiều)
    labelled = out["commune_code"].notna()
    resolved = out["coord_resolved"].fillna(False).astype(bool)
    assert (labelled == resolved).all()


# --------------------------------------------------------------------------- #
# Lớp thật (bỏ qua nếu chưa `make vnsdi`)                                      #
# --------------------------------------------------------------------------- #
needs_vnsdi = pytest.mark.skipif(not COMMUNES_PARQUET.exists(),
                                 reason="chưa có communes.parquet (`make vnsdi`)")


@needs_vnsdi
def test_real_boundary_layer_matches_official_commune_count():
    """Bảo vệ đính chính '609 xã lệch' (artefact đếm cả feature đường ở lớp OSM cũ):
    lớp VNSDI phải ~3.321 xã, đủ tên, kind nằm gọn trong enum cải cách 2025."""
    boundaries.load_communes.cache_clear()
    boundaries._tree.cache_clear()
    com = boundaries.load_communes()
    assert 3300 <= len(com) <= 3340, f"official ~3.321 xã, lớp có {len(com)}"
    assert com["commune_name"].notna().all()
    assert set(com["commune_kind"]) <= {"PHUONG", "XA", "DAC_KHU"}
