"""Test T1 retrodiction — toàn bộ synthetic (tmp_path), KHÔNG data thật, KHÔNG make_context thật.

Mục tiêu: chốt logic sampling (histogram-match, loại trừ, tái lập theo seed), filter ground
truth (NEW-HIGH vs purge cả wave), và số học metric (hit-rate / low-accept / AUC tính tay) —
phần dây chuyền run_t1 chỉ nối các hàm này nên không cần data thật để tin logic.
"""

import hashlib

import h3
import numpy as np
import pandas as pd
import pytest

from ev_siting.assess import cli, params
from ev_siting.assess.retrodiction import (
    compute_metrics,
    load_ground_truth,
    sample_control_a,
    sample_control_b,
)

# ---------------------------------------------------------------- fixtures synthetic


def _fake_demand() -> pd.DataFrame:
    """~200 ô r8 thật quanh Hà Nội với pop đa dạng — cell phải là mã h3 thật vì sampling
    gọi h3.cell_to_latlng; 5 ô đầu pop=0 để kiểm pool loại đúng ô không dân."""
    cells = []
    for i in range(15):
        for j in range(15):
            cells.append(h3.latlng_to_cell(21.0 + 0.01 * i, 105.8 + 0.01 * j, 8))
    cells = list(dict.fromkeys(cells))  # khử trùng lặp giữ thứ tự — mỗi ô một dòng như demand thật
    rng = np.random.default_rng(7)
    pops = rng.integers(1, 5000, size=len(cells)).astype(float)
    pops[:5] = 0.0
    return pd.DataFrame({"h3_r8": cells, "pop": pops})


def _cell_bins(dem: pd.DataFrame) -> pd.Series:
    """Decile pop tính tay y hệt định nghĩa đóng băng (qcut trên TOÀN BỘ ô pop>0) để đối chiếu."""
    pos = dem[dem["pop"] > 0]
    codes = pd.qcut(pos["pop"], 10, labels=False, duplicates="drop")
    return pd.Series(codes.to_numpy(), index=pos["h3_r8"].to_numpy())


# ---------------------------------------------------------------- (1) control A


def test_control_a_matches_gt_histogram_and_exclusions():
    dem = _fake_demand()
    pos_cells = dem.loc[dem["pop"] > 0, "h3_r8"].tolist()
    gt_cells = pos_cells[::5][:40]
    occupied = set(pos_cells[2::7][:10]) - set(gt_cells)

    # Thêm một "ô GT" không có trong lưới cầu — phải bị bỏ và đếm vào meta, không crash.
    df, meta = sample_control_a(dem, gt_cells + ["khong-phai-o"], occupied, n=len(gt_cells))

    assert meta["n_gt_dropped_not_in_dem"] == 1
    assert meta["shortfall"] == {}
    assert len(df) == len(gt_cells)

    # Histogram decile của control phải KHỚP histogram của tập ô GT (định nghĩa §5).
    cell_bin = _cell_bins(dem)
    gt_hist = pd.Series([cell_bin[c] for c in gt_cells]).value_counts().sort_index()
    ctl_hist = pd.Series([cell_bin[c] for c in df["h3_r8"]]).value_counts().sort_index()
    assert gt_hist.equals(ctl_hist)

    # Loại trừ: không lấy ô occupied, không trùng ô GT, chỉ ô pop>0.
    assert not set(df["h3_r8"]) & occupied
    assert not set(df["h3_r8"]) & set(gt_cells)
    pops = dem.set_index("h3_r8")["pop"]
    assert (pops.loc[df["h3_r8"]] > 0).all()

    # Điểm = tâm ô (h3.cell_to_latlng).
    lat0, lng0 = h3.cell_to_latlng(df["h3_r8"].iloc[0])
    assert df["lat"].iloc[0] == lat0 and df["lng"].iloc[0] == lng0


def test_control_a_seed_determinism():
    dem = _fake_demand()
    gt_cells = dem.loc[dem["pop"] > 0, "h3_r8"].tolist()[::6][:30]
    df1, _ = sample_control_a(dem, gt_cells, set(), n=30, seed=params.SEED_CONTROL_A)
    df2, _ = sample_control_a(dem, gt_cells, set(), n=30, seed=params.SEED_CONTROL_A)
    df3, _ = sample_control_a(dem, gt_cells, set(), n=30, seed=params.SEED_CONTROL_A + 1)
    assert df1.equals(df2)  # cùng seed -> y hệt từng dòng
    assert not df1.equals(df3)  # seed khác -> mẫu khác


# ---------------------------------------------------------------- (2) control B


def test_control_b_low_pop_pool_and_determinism():
    dem = _fake_demand()
    pos = dem.loc[dem["pop"] > 0, "pop"]
    thresh = pos.quantile(params.CONTROL_LOW_POP_Q)

    df, meta = sample_control_b(dem, occupied_cells=set(), n=20, seed=params.SEED_CONTROL_B)
    assert len(df) == 20 and meta["shortfall"] == 0
    pops = dem.set_index("h3_r8")["pop"].loc[df["h3_r8"]]
    assert ((pops > 0) & (pops <= thresh)).all()  # mọi ô trong dải "cầu thấp" đóng băng

    df2, _ = sample_control_b(dem, occupied_cells=set(), n=20, seed=params.SEED_CONTROL_B)
    assert df.equals(df2)


def test_control_b_shortfall_recorded():
    dem = _fake_demand()
    pos = dem.loc[dem["pop"] > 0, "pop"]
    pool_size = int((pos <= pos.quantile(params.CONTROL_LOW_POP_Q)).sum())

    df, meta = sample_control_b(dem, occupied_cells=set(), n=10_000)
    assert len(df) == pool_size  # pool cạn: lấy hết, không nới ngưỡng
    assert meta["shortfall"] == 10_000 - pool_size


# ---------------------------------------------------------------- (3) ground truth


def test_load_ground_truth_filters_and_sha(tmp_path):
    df = pd.DataFrame(
        {
            "evcs_code": ["C.AA000001", "C.AA000002", "C.AA000003", "C.AA000004"],
            "lat": [21.0, 21.1, 21.2, 21.3],
            "lng": [105.8, 105.9, 106.0, 106.1],
            "verdict": ["NEW", "NEW", "DRIFT_DUPLICATE", "NEW"],
            "new_confidence": ["HIGH", "AMBIGUOUS", "HIGH", "HIGH"],
        }
    )
    p = tmp_path / "part.parquet"
    df.to_parquet(p, index=False)

    gt, new_all, sha = load_ground_truth(p)
    # GT = NEW & HIGH; DRIFT_DUPLICATE và AMBIGUOUS không đủ chuẩn làm GT.
    assert sorted(gt["evcs_code"]) == ["C.AA000001", "C.AA000004"]
    assert list(gt.columns) == ["evcs_code", "lat", "lng"]
    # Purge cả wave: AMBIGUOUS vào danh sách loại, DRIFT_DUPLICATE ở lại nền.
    assert sorted(new_all) == ["C.AA000001", "C.AA000002", "C.AA000004"]
    assert sha == hashlib.sha256(p.read_bytes()).hexdigest()


def test_load_ground_truth_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit, match="ground truth"):
        load_ground_truth(tmp_path / "khong-ton-tai.parquet")


# ---------------------------------------------------------------- (4) metrics


def _scored(tiers, totals, ns, vs, reasons) -> pd.DataFrame:
    return pd.DataFrame({"tier": tiers, "score_total": totals, "score_N": ns, "score_V": vs, "reasons": reasons})


def test_compute_metrics_hand_values():
    gt = _scored(
        [params.TIER_ACCEPT, params.TIER_REVIEW, params.TIER_REJECT, params.TIER_ACCEPT],
        [80.0, 70.0, 20.0, 90.0],
        [80.0, 70.0, 20.0, 90.0],
        [80.0, np.nan, 20.0, 90.0],
        [["R05_x: a"], ["R05_x: a", "R10_y: b"], [], ["R10_y: b"]],
    )
    a = _scored([params.TIER_REVIEW] * 2, [60.0, 50.0], [10.0, 15.0], [60.0, 50.0], [[], []])
    b = _scored(
        [params.TIER_ACCEPT, params.TIER_REJECT, params.TIER_REVIEW, params.TIER_REJECT],
        [65.0, 10.0, 40.0, 5.0], [65.0, 10.0, 40.0, 5.0], [65.0, 10.0, 40.0, 5.0],
        [[], [], [], []],
    )  # fmt: skip

    m = compute_metrics(gt, a, b)
    assert m["hit_rate"] == pytest.approx(0.75)  # 3/4 GT thuộc {Đồng ý, Cần review}
    assert m["low_accept_share"] == pytest.approx(0.25)  # 1/4 control B được Đồng ý
    # AUC tính tay từng cặp: total 6/8 thắng; N tách hoàn hảo -> 1.0;
    # V: dòng NaN của GT bị loại, còn 3 GT vs 2 A -> 4/6 cặp thắng.
    assert m["auc"] == pytest.approx(0.75)
    assert m["auc_N"] == pytest.approx(1.0)
    assert m["auc_V"] == pytest.approx(2 / 3)
    assert m["auc_n_dropped"]["auc_V"] == {"gt": 1, "control_a": 0}
    assert m["auc_n_dropped"]["auc"] == {"gt": 0, "control_a": 0}
    # Reason đếm theo prefix R.., tier đếm theo nhóm.
    assert m["reason_counts"]["gt"] == {"R05": 2, "R10": 2}
    assert m["tier_counts"]["control_b"][params.TIER_ACCEPT] == 1
    assert m["n"] == {"gt": 4, "control_a": 2, "control_b": 4}


# ---------------------------------------------------------------- (5) CLI


def test_cli_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
