"""Tests cho bộ lọc dirty-coord dùng chung (F4) và baseline covered0 (F5).

Nguyên tắc F4: tập cờ lọc phải khớp TỪ VỰNG CỜ THẬT mà producer sinh ra —
bộ lọc cũ chết 2 tuần vì lọc theo cờ ma (`DUP_COORD`) không ai sinh.
"""

import pandas as pd

from ev_siting.features import build_candidates
from ev_siting.features.build_covered0 import _baseline_mask, _operational_only_mask
from ev_siting.features.paths import DIRTY_COORD_FLAGS, has_dirty_coord

#: Từ vựng cờ thật quan sát từ producer + canonical parquet snapshot 2026-07-20
#: (build_master_evcs / transform_canonical / dedup_crosssource + E-DQ1 coord-fix).
PRODUCER_FLAGS = {
    "COORD_INVALID",
    "NO_TS",
    "DUP_TS",
    "NONMONOTONIC",
    "NEG_VALUE",
    "NONNUMERIC",
    "ALL_ZERO",
    "SPARSE",
    "STD_UNVERIFIED",
    "NOT_OPERATIONAL",
    "UNDER_MAINTENANCE",
    "STATUS_UNKNOWN",
    "NON_PUBLIC",
    "ACCESS_UNKNOWN",
    "CROSS_SOURCE_DUP",
    "DUP_COORD_SUSPECT",
    "COORD_ADDR_MISMATCH",
    "COORD_PLACEHOLDER",
}


def test_dirty_flags_exist_in_producer_vocabulary():
    # Cờ ma trong bộ lọc = bộ lọc chết im lặng (bài học F4).
    ghosts = DIRTY_COORD_FLAGS - PRODUCER_FLAGS
    assert not ghosts, f"cờ lọc không producer nào sinh ra: {ghosts}"


def test_has_dirty_coord_each_flag_and_none():
    for flag in DIRTY_COORD_FLAGS:
        assert has_dirty_coord([flag]), flag
    assert not has_dirty_coord(["ALL_ZERO", "SPARSE"])  # cờ chất lượng khác không phải toạ độ
    assert not has_dirty_coord([])
    assert not has_dirty_coord(None)
    assert not has_dirty_coord(float("nan"))


def _station(**kw):
    row = {"is_operational": True, "access": "PUBLIC", "is_primary": True,
           "coord_resolved": True, "quality_flags": []}
    row.update(kw)
    return row


def test_baseline_mask_drops_each_reason():
    df = pd.DataFrame(
        [
            _station(),  # giữ
            _station(is_operational=False),  # OUT_OF_SERVICE
            _station(access="RESTRICTED"),  # tư nhân
            _station(access="UNKNOWN"),  # không xác nhận public
            _station(is_primary=False),  # dup chéo nguồn (E-DQ2)
            _station(quality_flags=["DUP_COORD_SUSPECT"]),  # toạ độ bẩn (F4)
            # placeholder E-DQ1: coord_resolved=False VÀ có cờ -> dính cả hai counter
            _station(coord_resolved=False, quality_flags=["COORD_PLACEHOLDER"]),
        ]
    )
    mask, reasons = _baseline_mask(df)
    assert mask.tolist() == [True, False, False, False, False, False, False]
    assert reasons == {
        "not_operational": 1,
        "access_restricted": 1,
        "access_unknown": 1,
        "cross_source_dup": 1,
        "coord_unresolved": 1,
        "dirty_coord": 2,
    }


def test_baseline_excludes_coord_outside_admin():
    """Hồi quy: `COORD_OUTSIDE_ADMIN` có `coord_resolved=False` nhưng KHÔNG nằm trong
    `DIRTY_COORD_FLAGS` — bản trước chỉ lọc theo cờ nên 9 trạm `h3_r8` NULL lọt vào
    baseline và tạo coverage ảo. Baseline phải gate bằng CẢ `coord_resolved`."""
    df = pd.DataFrame([_station(coord_resolved=False,
                                quality_flags=["COORD_OUTSIDE_ADMIN"])])
    assert not has_dirty_coord(["COORD_OUTSIDE_ADMIN"])  # cờ này không ở tập F4
    mask, reasons = _baseline_mask(df)
    assert not mask.any()
    assert reasons["coord_unresolved"] == 1


def test_baseline_is_subset_of_export_supply_gate():
    """Bất biến hợp đồng: baseline ⊆ tập cung. Cùng 4 vị từ của `export_supply`
    (`is_operational & PUBLIC & is_primary & coord_resolved`) + 1 lớp bảo thủ thêm,
    nên không dòng nào vào được baseline mà đứng ngoài cung."""
    df = pd.DataFrame([
        _station(),
        _station(coord_resolved=False),
        _station(quality_flags=["DUP_COORD_SUSPECT"]),
        _station(access="UNKNOWN"),
    ])
    baseline, _ = _baseline_mask(df)
    supply = (df["is_operational"].fillna(False).astype(bool)
              & df["access"].eq("PUBLIC")
              & df["is_primary"].fillna(False).astype(bool)
              & df["coord_resolved"].fillna(False).astype(bool))
    assert (baseline & ~supply).sum() == 0


def test_baseline_mask_null_safe():
    # null ở cột bool -> loại (không xác nhận được), không crash / không default ngầm
    df = pd.DataFrame([_station(is_operational=None), _station(is_primary=None),
                       _station(coord_resolved=None)])
    mask, _ = _baseline_mask(df)
    assert not mask.any()


def test_operational_only_sensitivity_excludes_maintenance():
    df = pd.DataFrame([_station(op_status="OPERATIONAL"), _station(op_status="MAINTENANCE")])
    baseline, _ = _baseline_mask(df)
    assert baseline.tolist() == [True, True]
    assert _operational_only_mask(df).tolist() == [True, False]


def _t0_station(station_id, coord_resolved, quality_flags):
    return {
        "station_id": station_id, "lat": 21.0, "lng": 105.8,
        "h3_r8": "8828308281fffff" if coord_resolved else None,
        "quality_flags": quality_flags, "operator": "x", "is_operational": True,
        "access": "PUBLIC", "is_primary": True, "coord_resolved": coord_resolved,
        "province_code": "HNO",  # hệ 63 CŨ — T0 mang theo từ trạm neo (C3)
    }


def test_t0_gates_on_coord_resolved(monkeypatch):
    """E-DQ1 (Q3): anchor T0 lọc theo `coord_resolved` — COORD_PLACEHOLDER loại;
    COORD_ADDR_MISMATCH (advisory) và DUP_COORD_SUSPECT đơn lẻ GIỮ, không loại
    incumbent oan (khác baseline covered0: bảo thủ hơn, loại theo DIRTY_COORD_FLAGS)."""
    stations = pd.DataFrame(
        [
            _t0_station("placeholder", False, ["COORD_PLACEHOLDER"]),
            _t0_station("advisory", True, ["COORD_ADDR_MISMATCH"]),
            _t0_station("suspect", True, ["DUP_COORD_SUSPECT"]),
            _t0_station("clean", True, []),
        ]
    )

    class AllInAoi:
        @staticmethod
        def contains(lat, lng):
            return [True] * len(lat)

    monkeypatch.setattr(build_candidates.pd, "read_parquet", lambda *args, **kwargs: stations)
    out = build_candidates._load_stations(AllInAoi())
    assert out["source_ref"].tolist() == ["advisory", "suspect", "clean"]
