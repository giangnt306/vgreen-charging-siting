"""E-DQ8a — khoá ngữ nghĩa bậc lối vào.

Các test dưới đây khoá đúng những chỗ mà bản cũ (`road_access_m <= 0`) sai, để phép sửa
không âm thầm quay lại: ô có đường ở vành 1 KHÔNG được coi là không có lối vào, và tổng
vành phải phụ thuộc láng giềng (nên không tính được trên tập con).
"""
import pandas as pd
import pytest

import h3
from ev_siting.data.osm.access_tiers import (BUILDABLE_EXCLUDED_TIERS,
                                             RECEIVER_TIERS, TIER_ORDER, derive,
                                             ring_access_sums, tier_rank,
                                             tiers_from_lookup)

CENTER = h3.latlng_to_cell(21.0278, 105.8342, 8)     # Hà Nội


def _frame(access_by_cell):
    return pd.DataFrame({"h3_r8": list(access_by_cell),
                         "road_access_m": list(access_by_cell.values())})


def test_direct_when_cell_has_road():
    out = derive(_frame({CENTER: 1200.0}))
    assert out["access_tier"].iloc[0] == "DIRECT"


def test_adjacent_when_only_neighbour_has_road():
    """Chính ca mà bộ lọc cũ đánh sai: 4.862 ô / 894.956 người."""
    nb = [c for c in h3.grid_disk(CENTER, 1) if c != CENTER][0]
    out = derive(_frame({CENTER: 0.0, nb: 800.0})).set_index("h3_r8")
    assert out.at[CENTER, "access_tier"] == "ADJACENT"
    assert out.at[CENTER, "road_access_nb1_m"] == pytest.approx(800.0)
    assert out.at[nb, "access_tier"] == "DIRECT"


def test_near_when_only_ring2_has_road():
    ring2 = [c for c in h3.grid_disk(CENTER, 2) if h3.grid_distance(CENTER, c) == 2][0]
    out = derive(_frame({CENTER: 0.0, ring2: 500.0})).set_index("h3_r8")
    assert out.at[CENTER, "access_tier"] == "NEAR"
    assert out.at[CENTER, "road_access_nb1_m"] == 0.0
    assert out.at[CENTER, "road_access_nb2_m"] == pytest.approx(500.0)


def test_isolated_only_when_nothing_within_two_rings():
    far = h3.grid_ring(CENTER, 4)[0]
    out = derive(_frame({CENTER: 0.0, far: 900.0})).set_index("h3_r8")
    assert out.at[CENTER, "access_tier"] == "ISOLATED"


def test_cells_outside_grid_count_as_zero_access():
    """Ô không có trong bảng = OSM không có đường ở đó, KHÔNG phải thiếu dữ liệu để suy
    diễn. Đây là hợp đồng làm cho `ring_access_sums` chỉ đúng khi nhận TOÀN lưới."""
    nb = [c for c in h3.grid_disk(CENTER, 1) if c != CENTER][0]
    full = derive(_frame({CENTER: 0.0, nb: 800.0})).set_index("h3_r8")
    subset = derive(_frame({CENTER: 0.0})).set_index("h3_r8")
    assert full.at[CENTER, "access_tier"] == "ADJACENT"
    assert subset.at[CENTER, "access_tier"] == "ISOLATED"      # cùng ô, tập con -> khác


def test_ring_sums_exclude_self():
    nb = [c for c in h3.grid_disk(CENTER, 1) if c != CENTER][0]
    nb1, nb2 = ring_access_sums([CENTER, nb], [1000.0, 7.0])
    assert nb1[0] == pytest.approx(7.0)          # không cộng 1000 của chính ô
    assert nb2[0] == pytest.approx(7.0)          # đĩa 2 ⊇ đĩa 1, vẫn trừ chính ô


def test_tiers_from_lookup_classifies_a_subset_without_defaulting_isolated():
    """Ca ô "mồ côi": ô có trạm sạc thật, KHÔNG có dòng trong `demand_h3`, nhưng ô kề có
    đường. Mặc định ISOLATED sẽ loại cứng nó; tính từ bảng đường phải ra ADJACENT.
    (Đo 30/07: 76 ô như thế chứa 83 trạm đang vận hành.)"""
    nb = [c for c in h3.grid_disk(CENTER, 1) if c != CENTER][0]
    lut = {nb: 640.0}                      # CENTER hoàn toàn vắng mặt trong lookup
    assert list(tiers_from_lookup([CENTER], lut)) == ["ADJACENT"]


def test_tiers_from_lookup_agrees_with_derive_on_the_full_grid():
    """Hai đường tính bậc phải cho cùng kết quả — nếu lệch thì `classify` đã bị nhân bản."""
    ring = h3.grid_disk(CENTER, 2)
    acc = {c: (500.0 if i % 5 == 0 else 0.0) for i, c in enumerate(ring)}
    full = derive(_frame(acc)).set_index("h3_r8")["access_tier"]
    sub = tiers_from_lookup(list(ring), acc)
    assert list(sub) == [full[c] for c in ring]


def test_tiers_from_lookup_handles_empty_input():
    assert len(tiers_from_lookup([], {})) == 0


def test_tier_rank_is_ordered_and_contracts_hold():
    assert list(tier_rank(TIER_ORDER)) == [0, 1, 2, 3]
    # hợp đồng với build_buildable_h3 / reallocate_roadless
    assert BUILDABLE_EXCLUDED_TIERS == ("ISOLATED",)
    assert RECEIVER_TIERS == ("DIRECT",)
    assert set(BUILDABLE_EXCLUDED_TIERS) | set(RECEIVER_TIERS) <= set(TIER_ORDER)


def test_derive_rejects_missing_columns():
    with pytest.raises(ValueError):
        derive(pd.DataFrame({"h3_r8": [CENTER]}))
