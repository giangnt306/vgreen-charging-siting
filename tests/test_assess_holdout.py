"""Test cắt holdout địa lý — hợp đồng niêm phong, không data thật."""

import numpy as np
import pandas as pd
import pytest

from ev_siting.assess import holdout


def _cluster(lat, lng, n, spread=0.02, seed=0):
    """Cụm điểm sát nhau (~vài km) — đảm bảo rơi cùng một block res 3."""
    rng = np.random.default_rng(seed)
    return [(lat + d, lng + e) for d, e in rng.uniform(-spread, spread, size=(n, 2))]


@pytest.fixture
def gt():
    pts = (
        _cluster(21.03, 105.83, 60, seed=1)  # cụm lớn 1
        + _cluster(10.78, 106.70, 45, seed=2)  # cụm lớn 2
        + _cluster(16.05, 108.20, 30, seed=3)
        + _cluster(12.24, 109.19, 20, seed=4)
        + _cluster(20.85, 106.68, 10, seed=5)
    )
    return pd.DataFrame(pts, columns=["lat", "lng"])


def test_split_is_deterministic_and_hits_target_share(gt, tmp_path):
    a = holdout.build_split(gt, out=tmp_path / "s1.json")
    b = holdout.build_split(gt, out=tmp_path / "s2.json")
    assert a["blocks"] == b["blocks"]  # không randomness nào để dò split có lợi
    assert 0.25 <= a["holdout_share_actual"] <= 0.55  # LPT không thể chính xác tuyệt đối
    assert a["n_design"] + a["n_holdout"] == len(gt)


def test_lpt_splits_large_blocks_across_both_halves(gt):
    """Hai cụm lớn nhất KHÔNG được rơi cùng một phía — nếu rơi thì split thành
    distribution shift (design nông thôn vs holdout đô thị), không còn đo overfit."""
    assign = holdout.assign_blocks(gt["lat"], gt["lng"])
    labels = holdout.label_points(gt["lat"].to_numpy(), gt["lng"].to_numpy(), assign)
    sizes = pd.Series(labels).value_counts()
    assert set(sizes.index) == {"design", "holdout"}
    # cụm 60 điểm và cụm 45 điểm phải nằm hai bên
    big1 = labels[0]  # thuộc cụm 21.03/105.83
    big2 = labels[60]  # thuộc cụm 10.78/106.70
    assert big1 != big2


def test_unknown_block_defaults_to_design(gt):
    assign = holdout.assign_blocks(gt["lat"], gt["lng"])
    # điểm ở vùng chưa từng có GT (giữa biển Đông) -> design, holdout là tập ĐÓNG do GT định nghĩa
    assert holdout.label_points([15.0], [113.0], assign)[0] == "design"


def test_leak_report_counts_border_stations(tmp_path):
    """Hai điểm cách nhau 1 km nhưng khác block -> phải bị đếm là rò biên, không giấu."""
    doc = holdout.build_split(
        pd.DataFrame(_cluster(21.03, 105.83, 40, seed=7) + _cluster(10.78, 106.70, 30, seed=8),
                     columns=["lat", "lng"]),
        out=tmp_path / "s.json",
    )  # fmt: skip
    leak = doc["leak"]
    assert leak["leak_radius_km"] == holdout.LEAK_RADIUS_KM
    assert 0.0 <= leak["share_holdout_leaky"] <= 1.0
    assert leak["n_holdout_within_leak_radius"] <= doc["n_holdout"]


def test_load_split_missing_fails_loudly(tmp_path):
    with pytest.raises(SystemExit, match="HOLDOUT FAIL"):
        holdout.load_split(tmp_path / "khong-co.json")
