"""Occupancy per-trạm duration-weighted — tái hiện y hệt bronze F19 phía evcs-dataset bằng pandas.

Vì sao file này tồn tại: pre-reg §3.4 khoá cứng "mọi thống kê occupancy phải duration-weighted
theo đúng công thức bronze F19" (``evcs_vn_bronze.liveness``, bản duckdb SQL). Telemetry crawl
có nhịp lấy mẫu không đều — một gap 71h sẽ làm mean-of-samples nói dối, nên F19 CẤM mean đếm
event. Repo này không có duckdb, do đó tái hiện cùng semantics bằng pandas; test đối chiếu số
tính tay từng bước để chốt hai bản không lệch nhau.

Semantics F19 (đối chiếu SQL từng dòng):

- ``TRY_CAST`` ts/n  →  ``to_numeric(errors="coerce")`` rồi drop NaN — dòng rác crawl không
  được làm chết build, cũng không được lọt vào trọng số;
- mỗi trạm sort ts tăng; gap = next_ts − ts; w = clamp(gap, 0, 30′); event CUỐI không có next
  nên không đóng góp trọng số;
- ``occ_mean_dw`` = Σ n·w / Σ w — NaN nếu Σ w = 0 (vd trạm chỉ có 1 event: không đo được gì);
- ``duration_coverage`` = Σ w / (max_ts − min_ts) — phần cửa sổ thực sự được quan sát,
  NaN nếu max == min (không có cửa sổ);
- ``max_gap_ms`` giữ gap THÔ chưa cap — để audit trạm có lỗ hổng quan sát lớn.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.api.types import union_categoricals

from ev_siting.assess import params, paths

#: Chỉ 3 cột này có nghĩa với F19 — usecols để pandas khỏi parse phần còn lại của 460MB.
_COLS = ["station_code", "timestamp", "n_cars_charging"]


def _sha256_file(path: Path) -> str:
    """Hash streaming theo khối — file nguồn 460MB, đọc nguyên khối chỉ để hash là phí RAM."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _concat_parts(parts: list[pd.DataFrame]) -> pd.DataFrame:
    """Nối chunk mà vẫn giữ dtype category.

    ``pd.concat`` rơi về object khi các chunk có tập category khác nhau — với 18,6M dòng
    object-string sẽ phình RAM gấp nhiều lần, nên union category thủ công.
    """
    parts = [p for p in parts if len(p)]
    if not parts:  # toàn dòng rác / file rỗng: trả frame rỗng đúng dtype để aggregate không gãy
        return pd.DataFrame(
            {
                "station_code": pd.Categorical([]),
                "ts": pd.Series([], dtype="int64"),
                "n": pd.Series([], dtype="int32"),
            }
        )
    return pd.DataFrame(
        {
            "station_code": union_categoricals([p["station_code"].array for p in parts]),
            "ts": np.concatenate([p["ts"].to_numpy() for p in parts]),
            "n": np.concatenate([p["n"].to_numpy() for p in parts]),
        }
    )


def _aggregate_f19(df: pd.DataFrame) -> pd.DataFrame:
    """Bản pandas của cặp CTE ``seq`` → ``weighted`` trong bronze ``liveness()`` — giữ nguyên từng phép."""
    # LEAD(ts) OVER (PARTITION BY station_code ORDER BY ts): SQL không định nghĩa thứ tự khi ts
    # trùng nhau — sort stable chọn thứ tự xuất hiện trong file để kết quả tái lập được.
    df = df.sort_values(["station_code", "ts"], kind="stable", ignore_index=True)
    gap = df.groupby("station_code", observed=True)["ts"].shift(-1) - df["ts"]  # NaN ở event cuối mỗi trạm
    # Cap 30' (MAX_HOLD_MS): trạm rớt crawl 71h không được để gap đó thống trị mean.
    w = gap.clip(lower=0, upper=float(params.MAX_HOLD_MS))

    agg = (
        df.assign(w=w, nw=df["n"] * w, gap=gap)
        .groupby("station_code", observed=True)
        .agg(
            weighted_ms=("w", "sum"),  # sum bỏ NaN: trạm 1 event → 0 (event cuối không đóng góp w)
            weighted_n_ms=("nw", "sum"),
            max_gap_ms=("gap", "max"),  # gap THÔ chưa cap — max bỏ NaN, trạm 1 event → NaN
            n_obs=("ts", "size"),
            ts_min=("ts", "min"),
            ts_max=("ts", "max"),
            n_max=("n", "max"),
        )
    )

    # NULLIF(x, 0) của SQL: mẫu 0 → NaN thay vì chia 0 (trạm 1 event / mọi event trùng ts).
    denom_w = agg["weighted_ms"].where(agg["weighted_ms"] > 0)
    span = (agg["ts_max"] - agg["ts_min"]).astype("float64")
    return pd.DataFrame(
        {
            "station_code": agg.index.astype(str).to_numpy(),
            "occ_mean_dw": (agg["weighted_n_ms"] / denom_w).to_numpy(),
            # Khớp bronze từng NULL: trạm 1 event → CTE weighted KHÔNG sinh hàng, LEFT JOIN
            # trả NULL (NaN). Nhưng trạm ≥2 event mà mọi gap = 0 (timestamp trùng) thì hàng
            # weighted TỒN TẠI với 0 → bronze ra 0.0, không phải NULL — nên điều kiện NaN là
            # n_obs==1, không phải weighted_ms==0. Đối chiếu 28/07: 19.218/19.218 bit-exact.
            "duration_observed_s": (agg["weighted_ms"].where(agg["n_obs"] >= 2) / 1000.0).to_numpy(),
            "duration_coverage": (agg["weighted_ms"] / span.where(span > 0)).to_numpy(),
            "max_gap_ms": agg["max_gap_ms"].to_numpy(dtype="float64"),
            "n_obs": agg["n_obs"].to_numpy(dtype="int64"),
            "ever_active": (agg["n_max"] > 0).to_numpy(dtype=bool),
        }
    )


def build_occupancy_cache(
    load_ts_path: Path = paths.LOAD_TS,
    out: Path = paths.OCC_CACHE,
    meta_out: Path = paths.OCC_META,
    chunksize: int = 2_000_000,
) -> pd.DataFrame:
    """Đọc telemetry CSV → thống kê F19 per-trạm → ghi parquet cache + meta JSON, trả DataFrame.

    Đọc theo chunk CHỈ để giới hạn peak RAM lúc parse (file thật 18,6M dòng / 460MB): event
    của một trạm nằm rải nhiều chunk và file không được sort sẵn, nên aggregate per-chunk sẽ
    cắt đứt chuỗi LEAD — bắt buộc concat toàn bộ (dtype gọn) rồi groupby MỘT lần.
    """
    load_ts_path, out, meta_out = Path(load_ts_path), Path(out), Path(meta_out)

    parts: list[pd.DataFrame] = []
    rows_in = 0
    reader = pd.read_csv(
        load_ts_path,
        usecols=_COLS,
        dtype=str,  # all_varchar=true phía duckdb: parse số ở bước TRY_CAST bên dưới, không để pandas đoán
        chunksize=chunksize,
        on_bad_lines="skip",  # ignore_errors=true: dòng lệch cột không được làm chết build
    )
    for chunk in reader:
        rows_in += len(chunk)
        # TRY_CAST: rác ("abc", ô rỗng) → NaN rồi drop — trạm khác không bị vạ lây.
        ts = pd.to_numeric(chunk["timestamp"], errors="coerce")
        n = pd.to_numeric(chunk["n_cars_charging"], errors="coerce")
        # SQL gộp station_code NULL thành một nhóm riêng — nhóm đó không join được với
        # covered0 nên vô nghĩa downstream: drop luôn tại đây.
        ok = ts.notna() & n.notna() & chunk["station_code"].notna()
        parts.append(
            pd.DataFrame(
                {
                    # category + int gọn: giữ 18,6M dòng trong RAM mà không phình object-string.
                    "station_code": chunk.loc[ok, "station_code"].astype("category"),
                    "ts": ts[ok].astype("int64"),
                    "n": n[ok].astype("int32"),
                }
            )
        )

    stats = _aggregate_f19(_concat_parts(parts))

    paths.ensure_dirs()  # dirs mặc định của repo; out tuỳ biến (test) cần parent riêng bên dưới
    out.parent.mkdir(parents=True, exist_ok=True)
    meta_out.parent.mkdir(parents=True, exist_ok=True)
    stats.to_parquet(out, index=False)
    meta = {
        # sha256 nguồn pin vào meta: cache là dẫn xuất — phải chứng minh được build từ file frozen nào.
        "source": str(load_ts_path),
        "source_sha256": _sha256_file(load_ts_path),
        "rows_in": rows_in,
        "n_stations": int(len(stats)),
        "max_hold_ms": params.MAX_HOLD_MS,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stats


def load_occupancy(cache: Path = paths.OCC_CACHE, meta: Path = paths.OCC_META) -> pd.DataFrame:
    """Đọc cache F19 đã build; KHÔNG tự build ngầm — cày 18,6M dòng phải là hành động chủ ý (CLI).

    Meta thiếu cũng coi như chưa build: cache không chứng minh được nguồn thì không được dùng.
    """
    cache, meta = Path(cache), Path(meta)
    if not cache.exists() or not meta.exists():
        raise SystemExit("OCC FAIL: chưa build cache (chạy cli build-occupancy)")
    return pd.read_parquet(cache)
