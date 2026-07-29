"""Lớp tham chiếu (trần percentile) của assess() — pre-reg §2 + hàm percentile §4.

Vì sao trần = 28.075 candidate frozen chứ không phải "mọi ô r8": percentile chỉ có
nghĩa khi so điểm được chấm với QUỸ ĐẤT KHẢ THI thật — so với cả biển/rừng sẽ thổi
phồng mọi điểm. Và feature của lớp tham chiếu phải tính lại DƯỚI CÙNG context N với
điểm được chấm (live vs retrodiction cho hai phân bố khác nhau) — dùng chung một
cache "live" cho retrodiction là leakage hệ quy chiếu, nên cache keyed theo ``tag``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ev_siting.assess import paths
from ev_siting.assess.kernel import NetworkContext, nearest_info
from ev_siting.features.build_candidates import _coverage_cells

#: Cột frozen của bảng tham chiếu — engine đọc đúng 4 cột phân bố này, đổi tên là gãy pctl.
REF_COLS = ["candidate_id", "h3_r8", "lat", "lng", "n_marginal_pop", "v_demand_local", "v_competition", "rho"]


def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _identity(candidates: pd.DataFrame, ctx: NetworkContext, dem: pd.Series) -> dict:
    """Dấu vân tay NỘI DUNG của (candidates, network, demand) — chống cache stale câm.

    Adversarial 28/07: tag tên file không mã hoá bundle/scope/demand — cùng tag mà đổi
    bất kỳ input nào sẽ trả phân bố cũ im lặng. Meta sidecar so vân tay khi đọc lại;
    lệch thì rebuild (in cảnh báo) thay vì tin cache.
    """
    dem_h = hashlib.sha256(pd.util.hash_pandas_object(dem, index=True).to_numpy().tobytes()).hexdigest()[:16]
    return {
        "n_candidates": int(len(candidates)),
        "candidates_sha16": _sha16("\n".join(sorted(map(str, candidates["candidate_id"])))),
        "dem_sha16": dem_h,
        "covered_sha16": _sha16("\n".join(sorted(ctx.covered_cells))) if ctx.covered_cells else "empty",
        "n_stations": int(len(ctx.stations)),
        "r_km": float(ctx.r_km),
        "mode": ctx.mode,
    }


def build_reference(
    candidates: pd.DataFrame,
    ctx: NetworkContext,
    dem: pd.Series,
    cache_dir: Path = paths.REF_DIR,
    tag: str = "live",
) -> pd.DataFrame:
    """Tính 4 phân bố tham chiếu cho toàn bộ candidate frozen dưới context ``ctx``.

    Cache parquet theo ``tag`` (vd "live", "retro-<hash exclude>"): 28k candidate ×
    ~37 ô phủ là vài giây tính — chấp nhận được một lần, không chấp nhận được mỗi lần
    chấm một điểm. Cache có sẵn thì đọc lại nguyên trạng (context đã mã hoá trong tag).
    """
    cache_dir = Path(cache_dir)
    cache = cache_dir / f"ref-{tag}.parquet"
    meta_path = cache_dir / f"ref-{tag}.meta.json"
    ident = _identity(candidates, ctx, dem)
    if cache.exists():
        # Chỉ tin cache khi vân tay nội dung khớp — tag trùng mà input đổi (scope/label/
        # refreeze/demand mới) phải rebuild, không được trả phân bố của bundle cũ.
        try:
            cached_ident = json.loads(meta_path.read_text(encoding="utf-8"))["identity"]
        except (OSError, ValueError, KeyError):
            cached_ident = None
        if cached_ident == ident:
            return pd.read_parquet(cache)
        print(f"[reference] cache {cache.name} lệch vân tay input — rebuild (chống stale)")

    cand = candidates.reset_index(drop=True)

    # Tra pop bằng dict.get thay vì dem.index.isin: isin quét cả ~268k ô MỖI candidate
    # — với 28k candidate là khác biệt giữa vài giây và nhiều phút.
    pop = dem.to_dict()
    covered = ctx.covered_cells

    # Candidate đã dedup 1 ô/điểm nhưng vẫn memo theo ô: hợp đồng không cấm trùng ô,
    # và _coverage_cells (grid_disk + haversine) là phần đắt nhất của vòng lặp.
    cov_cache: dict[str, frozenset[str]] = {}
    local = np.empty(len(cand))
    marginal = np.empty(len(cand))
    for i, cell in enumerate(cand["h3_r8"].to_numpy()):
        cov = cov_cache.get(cell)
        if cov is None:
            cov = cov_cache[cell] = _coverage_cells(cell, ctx.r_km)
        local[i] = sum(pop.get(c, 0.0) for c in cov)
        marginal[i] = sum(pop.get(c, 0.0) for c in cov if c not in covered)

    # Một truy vấn BallTree cho toàn bộ candidate — cùng kernel láng giềng với điểm
    # được chấm (C10), nên percentile so sánh táo-với-táo về cả phủ lẫn khoảng cách.
    info = nearest_info(ctx, cand["lat"].to_numpy(), cand["lng"].to_numpy(), r_km=ctx.r_km)

    out = pd.DataFrame(
        {
            "candidate_id": cand["candidate_id"].to_numpy(),
            "h3_r8": cand["h3_r8"].to_numpy(),
            "lat": cand["lat"].to_numpy(dtype=float),
            "lng": cand["lng"].to_numpy(dtype=float),
            "n_marginal_pop": marginal,
            "v_demand_local": local,
            "v_competition": info["n_within_comp"].astype(float),
            # ρ = cầu địa phương / (1 + cung connector trong R) — pre-reg §3 nói rõ đây là
            # áp lực TƯƠNG ĐỐI để xếp hạng percentile, không phải dự báo utilization (I-4).
            "rho": local / (1.0 + info["connectors_within_r"]),
        }
    )[REF_COLS]

    cache_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache, index=False)
    meta_path.write_text(
        json.dumps({"tag": tag, "identity": ident}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out


def pctl(ref_values, x):
    """Percentile ECDF đóng băng pre-reg §4: (strictly-below + ½·ties) × 100.

    Quy ước ½·ties để một giá trị lặp nhiều lần (vd marginal = 0 hàng loạt) nhận
    percentile ở GIỮA khối ties thay vì 0 hay 100 — không thưởng cũng không phạt
    điểm chỉ vì trùng giá trị phổ biến. NaN trong ref bị loại khỏi phân bố; x NaN
    trả NaN (thiếu dữ liệu lan lên score, không lặng lẽ thành 0). Nhận scalar hoặc
    mảng; ref rỗng (sau khi bỏ NaN) ⇒ NaN toàn phần — không có phân bố thì không có hạng.
    """
    ref = np.asarray(ref_values, dtype=float)
    ref = np.sort(ref[~np.isnan(ref)])
    xs = np.asarray(x, dtype=float)
    scalar = xs.ndim == 0
    xs1 = np.atleast_1d(xs).astype(float)

    out = np.full(xs1.shape, np.nan)
    if len(ref):
        valid = ~np.isnan(xs1)
        # searchsorted hai phía trên ref đã sort: left = số phần tử strictly-below,
        # right − left = số ties — đúng từng chữ định nghĩa ECDF đóng băng.
        below = np.searchsorted(ref, xs1[valid], side="left")
        ties = np.searchsorted(ref, xs1[valid], side="right") - below
        out[valid] = (below + 0.5 * ties) / len(ref) * 100.0
    return float(out[0]) if scalar else out
