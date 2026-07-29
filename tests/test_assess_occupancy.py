"""Test occupancy F19 (bản pandas) đối chiếu số tính tay từng bước với công thức bronze.

Toàn bộ CSV synthetic dựng trong tmp_path — tuyệt đối không đụng data thật (460MB):
mục tiêu là chốt semantics (cap 30', event cuối bỏ, TRY_CAST, chunk-boundary), không phải I/O.
"""

import hashlib
import json
import math
from datetime import datetime

import pandas as pd
import pytest

from ev_siting.assess import params
from ev_siting.assess.occupancy import build_occupancy_cache, load_occupancy

HEADER = "station_code,timestamp,n_cars_charging"

#: Trạm A tính tay: gaps 600s / 3600s (cap 1800s) / 600s; event cuối (4800000) không có next.
ROWS_A = [("A", 0, 2), ("A", 600_000, 0), ("A", 4_200_000, 1), ("A", 4_800_000, 3)]


def _write_csv(path, rows):
    lines = [HEADER] + [",".join(str(v) for v in r) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build(tmp_dir, rows, **kwargs):
    csv = tmp_dir / "load_ts.csv"
    _write_csv(csv, rows)
    return build_occupancy_cache(
        load_ts_path=csv,
        out=tmp_dir / "occ.parquet",
        meta_out=tmp_dir / "occ.meta.json",
        **kwargs,
    )


def test_hand_computed_station_a(tmp_path):
    df = _build(tmp_path, ROWS_A)
    r = df.set_index("station_code").loc["A"]
    # occ = (2·600 + 0·1800 + 1·600) / (600 + 1800 + 600) — trọng số duration, KHÔNG phải mean event
    assert r["occ_mean_dw"] == pytest.approx(0.6)
    assert r["duration_observed_s"] == pytest.approx(3000.0)
    assert r["duration_coverage"] == pytest.approx(3000 / 4800)
    assert r["max_gap_ms"] == 3_600_000  # gap THÔ chưa cap — khác với w đã cap 1800s
    assert r["n_obs"] == 4
    assert bool(r["ever_active"]) is True


def test_single_event_station_nan(tmp_path):
    df = _build(tmp_path, [("S", 1_000, 2)])
    r = df.iloc[0]
    assert math.isnan(r["occ_mean_dw"])  # Σw = 0 → NULLIF → NaN, không phải 0
    assert math.isnan(r["duration_coverage"])  # max_ts == min_ts: không có cửa sổ
    # Bronze: 1 event → CTE weighted không có hàng → LEFT JOIN NULL. Đối chiếu 28/07
    # với liveness.parquet gốc: NaN, không phải 0.0 (sửa sau lần cross-check đầu).
    assert math.isnan(r["duration_observed_s"])
    assert math.isnan(r["max_gap_ms"])
    assert r["n_obs"] == 1
    assert bool(r["ever_active"]) is True


def test_duplicate_ts_station_zero_not_nan(tmp_path):
    # ≥2 event nhưng mọi gap = 0 (timestamp trùng): hàng weighted TỒN TẠI với Σw=0
    # → bronze ra duration_observed_s = 0.0 (không phải NULL); occ vẫn NaN qua NULLIF.
    df = _build(tmp_path, [("D", 5_000, 1), ("D", 5_000, 3)])
    r = df.iloc[0]
    assert r["duration_observed_s"] == 0.0
    assert math.isnan(r["occ_mean_dw"])
    assert math.isnan(r["duration_coverage"])  # span = 0 → NULLIF
    assert r["n_obs"] == 2


def test_garbage_rows_dropped(tmp_path):
    rows = [
        ("B", 0, 1),
        ("B", "abc", 1),  # ts rác → TRY_CAST NULL
        ("B", 300_000, ""),  # n rỗng
        ("B", 600_000, 1),
        ("B", "", "x"),  # rác cả hai cột
    ]
    df = _build(tmp_path, rows)
    r = df.iloc[0]
    assert len(df) == 1
    assert r["n_obs"] == 2  # chỉ 2 event hợp lệ sống sót, giống WHERE ts/n IS NOT NULL
    assert r["occ_mean_dw"] == pytest.approx(1.0)  # (1·600s) / 600s — rác không lọt vào trọng số
    meta = json.loads((tmp_path / "occ.meta.json").read_text(encoding="utf-8"))
    assert meta["rows_in"] == 5  # đếm dòng vào TRƯỚC khi drop — audit tỉ lệ rác được


def test_unsorted_input_same_result(tmp_path):
    shuffled = [ROWS_A[2], ROWS_A[0], ROWS_A[3], ROWS_A[1]]
    df = _build(tmp_path, shuffled)
    r = df.iloc[0]
    assert r["occ_mean_dw"] == pytest.approx(0.6)  # LEAD phải theo ts, không theo thứ tự file
    assert r["max_gap_ms"] == 3_600_000


def test_gap_exactly_30min_not_capped(tmp_path):
    # Biên của clamp: gap = MAX_HOLD_MS đúng bằng cap phải GIỮ NGUYÊN, không bị cắt oan.
    df = _build(tmp_path, [("C", 0, 1), ("C", 1_800_000, 0)])
    r = df.iloc[0]
    assert r["occ_mean_dw"] == pytest.approx(1.0)
    assert r["duration_observed_s"] == pytest.approx(1800.0)
    assert r["duration_coverage"] == pytest.approx(1.0)
    assert r["max_gap_ms"] == 1_800_000


def test_ever_active_false_when_all_zero(tmp_path):
    df = _build(tmp_path, [("D", 0, 0), ("D", 60_000, 0)])
    r = df.iloc[0]
    assert bool(r["ever_active"]) is False
    assert r["occ_mean_dw"] == pytest.approx(0.0)  # có quan sát nhưng không bao giờ bận


def test_small_chunksize_equals_single_read(tmp_path):
    # X = trạm A nhưng event nằm vắt qua 3 chunk (chunksize=3) + xen kẽ trạm Y, file không sort:
    # nếu code aggregate per-chunk thì chuỗi LEAD bị cắt và số sẽ lệch.
    rows = [
        ("X", 4_200_000, 1),
        ("Y", 0, 0),
        ("X", 0, 2),
        ("Y", 600_000, 3),
        ("X", 600_000, 0),
        ("X", 4_800_000, 3),
        ("Y", 1_200_000, 0),
    ]
    d_one, d_chunk = tmp_path / "one", tmp_path / "chunked"
    d_one.mkdir()
    d_chunk.mkdir()
    df_one = _build(d_one, rows)
    df_chunk = _build(d_chunk, rows, chunksize=3)
    pd.testing.assert_frame_equal(
        df_one.sort_values("station_code", ignore_index=True),
        df_chunk.sort_values("station_code", ignore_index=True),
    )
    by_code = df_chunk.set_index("station_code")
    assert by_code.loc["X", "occ_mean_dw"] == pytest.approx(0.6)
    assert by_code.loc["Y", "occ_mean_dw"] == pytest.approx(1.5)  # (0·600s + 3·600s) / 1200s


def test_meta_contents(tmp_path):
    _build(tmp_path, ROWS_A)
    csv = tmp_path / "load_ts.csv"
    meta = json.loads((tmp_path / "occ.meta.json").read_text(encoding="utf-8"))
    assert meta["source"] == str(csv)
    assert meta["source_sha256"] == hashlib.sha256(csv.read_bytes()).hexdigest()
    assert meta["rows_in"] == len(ROWS_A)
    assert meta["n_stations"] == 1
    assert meta["max_hold_ms"] == params.MAX_HOLD_MS == 1_800_000
    datetime.fromisoformat(meta["built_at"])  # ISO hợp lệ — parse được là đạt


def test_load_occupancy_roundtrip_and_missing(tmp_path):
    with pytest.raises(SystemExit, match="OCC FAIL"):
        load_occupancy(cache=tmp_path / "missing.parquet", meta=tmp_path / "missing.json")
    df = _build(tmp_path, ROWS_A)
    # Cache có nhưng meta bị xoá → vẫn fail: cache không chứng minh được nguồn thì không dùng.
    (tmp_path / "occ.meta.json").rename(tmp_path / "occ.meta.json.bak")
    with pytest.raises(SystemExit, match="OCC FAIL"):
        load_occupancy(cache=tmp_path / "occ.parquet", meta=tmp_path / "occ.meta.json")
    (tmp_path / "occ.meta.json.bak").rename(tmp_path / "occ.meta.json")
    loaded = load_occupancy(cache=tmp_path / "occ.parquet", meta=tmp_path / "occ.meta.json")
    pd.testing.assert_frame_equal(loaded, df)
