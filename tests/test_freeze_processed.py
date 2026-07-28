"""Cổng chặn của bundle freeze processed (sprint2).

Lỗi thật đã gặp 28/07: `build_covered0 --national` rồi `build_candidates --city hanoi`
ghi vào CÙNG đường dẫn, để lại `data/processed/` mang baseline toàn quốc cạnh candidate
một thành phố. MCLP đọc vào là mọi phép "phủ thêm" đều sai mà không có gì báo.
"""

import pytest

from ev_siting.features.freeze_processed import _assert_same_aoi

_HANOI = {"name": "hanoi", "radius_km": 25.0, "buffer_km": 5.0, "bbox": [20.8, 105.5, 21.3, 106.1]}
_NATIONAL = {"name": "vietnam", "scope": "national", "bbox": [8.0, 102.0, 23.7, 110.0]}


def test_same_aoi_passes_and_returns_it():
    assert _assert_same_aoi({"aoi": _HANOI}, {"aoi": _HANOI}) == _HANOI


def test_mixed_scope_is_rejected():
    with pytest.raises(SystemExit, match="LẪN SCOPE"):
        _assert_same_aoi({"aoi": _HANOI}, {"aoi": _NATIONAL})


def test_same_name_different_geometry_is_rejected():
    # Đổi bán kính mà giữ nguyên tên vẫn là hai vùng khác nhau; so tên là không đủ.
    wider = {**_HANOI, "radius_km": 40.0}
    with pytest.raises(SystemExit, match="radius_km"):
        _assert_same_aoi({"aoi": _HANOI}, {"aoi": wider})


def test_missing_aoi_block_is_rejected():
    with pytest.raises(SystemExit, match="thiếu khối"):
        _assert_same_aoi({}, {"aoi": _HANOI})
