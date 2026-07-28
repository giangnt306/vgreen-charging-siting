"""Tests cho bộ lọc dirty-coord dùng chung (F4) và baseline covered0 (F5).

Nguyên tắc F4: tập cờ lọc phải khớp TỪ VỰNG CỜ THẬT mà producer sinh ra —
bộ lọc cũ chết 2 tuần vì lọc theo cờ ma (`DUP_COORD`) không ai sinh.
"""

import pandas as pd

from ev_siting.features import build_candidates
from ev_siting.features.build_covered0 import _baseline_mask
from ev_siting.features.build_covered0 import _operational_only_mask
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
    row = {"is_operational": True, "access": "PUBLIC", "is_primary": True, "quality_flags": []}
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
            _station(quality_flags=["COORD_PLACEHOLDER"]),  # placeholder E-DQ1 (h3 null)
        ]
    )
    mask, reasons = _baseline_mask(df)
    assert mask.tolist() == [True, False, False, False, False, False, False]
    assert reasons == {
        "not_operational": 1,
        "access_restricted": 1,
        "access_unknown": 1,
        "cross_source_dup": 1,
        "dirty_coord": 2,
    }


def test_baseline_mask_null_safe():
    # null ở cột bool -> loại (không xác nhận được), không crash / không default ngầm
    df = pd.DataFrame([_station(is_operational=None), _station(is_primary=None)])
    mask, _ = _baseline_mask(df)
    assert not mask.any()


def test_operational_only_sensitivity_excludes_maintenance():
    df = pd.DataFrame([_station(op_status="OPERATIONAL"), _station(op_status="MAINTENANCE")])
    baseline, _ = _baseline_mask(df)
    assert baseline.tolist() == [True, True]
    assert _operational_only_mask(df).tolist() == [True, False]


def test_t0_drops_every_dirty_coordinate_flag(monkeypatch):
    stations = pd.DataFrame(
        [
            {
                "station_id": f"dirty-{flag}", "lat": 21.0, "lng": 105.8,
                "h3_r8": "8828308281fffff", "quality_flags": [flag],
                "operator": "x", "is_operational": True, "access": "PUBLIC", "is_primary": True,
            }
            for flag in DIRTY_COORD_FLAGS
        ]
        + [
            {
                "station_id": "clean", "lat": 21.0, "lng": 105.8,
                "h3_r8": "8828308281fffff", "quality_flags": [],
                "operator": "x", "is_operational": True, "access": "PUBLIC", "is_primary": True,
            }
        ]
    )

    class AllInAoi:
        @staticmethod
        def contains(lat, lng):
            return [True] * len(lat)

    monkeypatch.setattr(build_candidates.pd, "read_parquet", lambda *args, **kwargs: stations)
    out = build_candidates._load_stations(AllInAoi())
    assert out["source_ref"].tolist() == ["clean"]
