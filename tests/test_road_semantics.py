"""Tests cho ngữ nghĩa `road_len` (E-DQ7b): layout bảng lớp + suy dẫn cột."""
import pandas as pd

from ev_siting.data.osm import road_semantics as rs


def test_accumulator_layout_matches_column_names():
    """Khoá lỗi LỆCH NHÃN CỘT — chế độ lỗi im lặng đã xảy ra một lần trong lúc dựng.

    `roads_pbf.RoadHandler` gom vào list phẳng rồi ghi ra frame với `TIER_COLUMNS`
    làm tên cột. Nếu hai bên khác thứ tự, số vẫn "hợp lệ" (không âm, cộng ra tổng
    đúng) nhưng gán sai lớp — `road_access_m` khi đó ra 205.936 km thay vì 730.718 km.
    """
    from ev_siting.data.osm.roads_pbf import _BRIDGE_SLOT, _N_SLOTS, _TIER_IDX

    assert _N_SLOTS == len(rs.TIER_COLUMNS)
    assert _BRIDGE_SLOT == len(rs.TIER_COLUMNS) - 1
    for tier, base in _TIER_IDX.items():
        assert rs.TIER_COLUMNS[base] == rs.m_col(tier)
        assert rs.TIER_COLUMNS[base + 1] == rs.lane_col(tier)
        assert rs.TIER_COLUMNS[base + 2] == rs.lane_obs_col(tier)


def test_derive_access_vs_demand_split():
    """R2 — `road_access_m` GỒM service/track, `road_len_m` thì không.

    Ô chỉ có đường mòn: có lối vào (buildable giữ) nhưng không sinh cầu.
    """
    row = {c: 0.0 for c in rs.TIER_COLUMNS}
    row[rs.m_col("TRACK")] = 500.0
    row[rs.m_col("SERVICE")] = 300.0
    row[rs.m_col("LOCAL")] = 200.0
    out = rs.derive(pd.DataFrame([row])).iloc[0]

    assert out["road_access_m"] == 1000.0      # gồm cả track + service
    assert out["road_len_m"] == 200.0          # chỉ mạng sinh cầu
    assert out["road_len_m"] <= out["road_access_m"]


def test_derive_major_split_motorway_vs_arterial():
    """R4 — `road_len_mt_m` (gộp) bị khai tử; cao tốc và trục đô thị tách hẳn."""
    row = {c: 0.0 for c in rs.TIER_COLUMNS}
    row[rs.lane_col("MOTORWAY")] = 4000.0
    row[rs.lane_col("TRUNK")] = 1000.0
    row[rs.lane_col("PRIMARY")] = 500.0
    out = rs.derive(pd.DataFrame([row])).iloc[0]

    assert out["road_lane_mw_m"] == 4000.0
    assert out["road_lane_ar_m"] == 1500.0
    assert "road_len_mt_m" not in out.index, "cột gộp cũ phải biến mất, không đổi nghĩa ngầm"


def test_lanes_default_and_parsing():
    """R3 — lane-mét: dùng tag khi có, mặc định theo lớp/chiều khi thiếu."""
    assert rs.lanes_for("MOTORWAY", "4", True) == (4.0, True)
    assert rs.lanes_for("TRUNK", "2;3", False) == (2.0, True)      # `2;3` -> lấy 2
    assert rs.lanes_for("PRIMARY", "50", False) == (2.0, False)    # ngoài dải -> mặc định
    assert rs.lanes_for("LOCAL", None, True) == (1.0, False)       # một chiều -> 1 làn
    assert rs.lanes_for("LOCAL", None, False) == (2.0, False)      # hai chiều -> 2 làn
    assert rs.lanes_for("TRACK", None, False) == (1.0, False)      # đường mòn -> 1 làn


def test_oneway_recognition():
    """`oneway=-1` (chiều ngược) cũng là một chiều — bỏ sót sẽ tính thừa 1 làn."""
    assert rs.is_oneway("yes") and rs.is_oneway("-1") and rs.is_oneway("TRUE")
    assert not rs.is_oneway("no") and not rs.is_oneway(None) and not rs.is_oneway("")


def test_derive_tolerates_missing_tier_columns():
    """Bảng thiếu cột lớp (ô không có đường sau outer-join) -> 0, không KeyError."""
    out = rs.derive(pd.DataFrame({"h3_r8": ["8a1", "8a2"]}))
    assert list(out["road_access_m"]) == [0.0, 0.0]
    assert set(rs.DERIVED_COLUMNS).issubset(out.columns)
