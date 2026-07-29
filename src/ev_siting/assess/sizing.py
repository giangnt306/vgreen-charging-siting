"""Benchmark ĐỊNH CỠ — utilization quan sát theo (loại trụ × mật độ dân × số cổng).

Vì sao module này tồn tại (bằng chứng đo 2026-07-28, xem postmortem §3):

- Proxy cầu (`pop`, `road`, `n_poi`, `demand_a`, `demand_b`, `built_up_frac`) có
  **rho ≈ 0** với utilization thực tế của 1.546 trạm mới (|rho| ≤ 0,043, p > 0,09).
  Tức là: **vị trí ở thang km không giải thích được trạm chạy tốt hay không.**
- Ngược lại, cấu hình trạm thì có: `util ↔ max_power_kw` rho **+0,342**,
  `util ↔ num_connectors` rho **+0,235**, và util median **DC 0,233 vs AC 0,093**.

Nên câu hỏi có tín hiệu không phải *"đặt ở đâu"* mà là *"đặt loại gì ở đây"* — đúng
insight I-5 của Sprint 1 (mạng bão hoà ⇒ chuyển từ siting sang sizing).

Kỷ luật phát biểu: module này chỉ trả **thống kê mô tả trên trạm ĐANG CHẠY THẬT**
(thang phát biểu loại 1 — fact). Nó KHÔNG dự đoán utilization của trạm chưa xây; cấm
đọc con số ở đây thành cam kết hiệu suất (I-4, và đó là cách nhóm trước chết).

Chạy: uv run python -m ev_siting.assess.sizing
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ev_siting.assess import occupancy, params, paths
from ev_siting.features.read_frozen import load_frozen

BENCH_PATH = paths.CACHE_DIR / "sizing_benchmark.parquet"
BENCH_META = paths.CACHE_DIR / "sizing_benchmark.meta.json"

#: Ngưỡng dân số trong ô r8 để phân "đô thị / ven / thưa". Cắt theo tứ phân vị của ô
#: CÓ TRẠM (không phải toàn lưới) — mẫu so sánh phải là chỗ người ta thật sự đặt trạm.
DENSITY_LABELS = ("thưa", "ven", "đô thị")

#: Nhóm có ít hơn ngần này trạm quan sát thì KHÔNG công bố median — mẫu mỏng là cách
#: nhanh nhất để một con số vô nghĩa được trích dẫn như bằng chứng.
MIN_GROUP_N = 20


def _density_band(pop: pd.Series, edges: tuple[float, float]) -> pd.Series:
    lo, hi = edges
    return pd.cut(pop, [-np.inf, lo, hi, np.inf], labels=list(DENSITY_LABELS))


def build_benchmark(scope: str = params.SCOPE, label: str = params.FREEZE_LABEL) -> pd.DataFrame:
    """Bảng utilization quan sát theo nhóm — nền để so một vị trí với 'chỗ tương tự'.

    Utilization = ``occ_mean_dw / num_connectors`` (clip 1,0 như engine), chỉ tính trạm
    có ``duration_coverage ≥ 0,5`` và ``num_connectors > 0``. Đây là CÙNG một định nghĩa
    với ``occ_local`` trong hồ sơ, nên hai con số so được với nhau.
    """
    bundle = load_frozen(scope, label=label)
    occ = occupancy.load_occupancy()
    occ = occ.assign(station_id=occ["station_code"].map(params.station_id_from_code))

    dem = pd.read_parquet(paths.DEMAND_H3)[["h3_r8", "pop"]]
    df = (
        bundle.covered0.merge(occ[["station_id", "occ_mean_dw", "duration_coverage"]], on="station_id")
        .merge(dem, on="h3_r8", how="left")
    )  # fmt: skip
    df = df[(df["duration_coverage"] >= params.OCC_COVERAGE_FLOOR) & (df["num_connectors"] > 0)].copy()
    df["util"] = (df["occ_mean_dw"] / df["num_connectors"]).clip(0.0, 1.0)

    edges = (float(df["pop"].quantile(0.33)), float(df["pop"].quantile(0.67)))
    df["density_band"] = _density_band(df["pop"], edges)
    # Gộp số cổng thành 3 bậc: mẫu ở đuôi quá mỏng để đọc từng giá trị một.
    df["port_band"] = pd.cut(df["num_connectors"], [0, 1, 3, np.inf], labels=("1", "2-3", "4+"))

    g = df.groupby(["current_type", "density_band", "port_band"], observed=True)["util"]
    out = g.agg(n="size", util_p25=lambda s: s.quantile(0.25), util_p50="median", util_p75=lambda s: s.quantile(0.75))
    out = out.reset_index()
    # Nhóm mỏng vẫn giữ dòng (để người đọc thấy nó tồn tại) nhưng bị che số + gắn cờ.
    thin = out["n"] < MIN_GROUP_N
    out.loc[thin, ["util_p25", "util_p50", "util_p75"]] = np.nan
    out["reportable"] = ~thin

    paths.ensure_dirs()
    out.to_parquet(BENCH_PATH, index=False)
    BENCH_META.write_text(
        json.dumps(
            {
                "data_version": params.DATA_VERSION,
                "model_version": params.MODEL_VERSION,
                "n_stations": int(len(df)),
                "density_edges_pop": list(edges),
                "min_group_n": MIN_GROUP_N,
                "definition": "util = clip(occ_mean_dw / num_connectors, 0, 1); coverage >= 0.5; connectors > 0",
                "caveat": "thống kê mô tả trên trạm đang chạy — KHÔNG phải dự đoán hiệu suất trạm chưa xây (I-4)",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return out


def load_benchmark(path: Path = BENCH_PATH) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"SIZING FAIL: chưa build benchmark {path} — chạy `python -m ev_siting.assess.sizing`")
    return pd.read_parquet(path)


def suggest(pop_cell: float, bench: pd.DataFrame, meta: dict | None = None) -> dict:
    """So sánh AC vs DC ở dải mật độ tương ứng — trả FACT, không trả khuyến nghị cứng."""
    meta = meta or json.loads(BENCH_META.read_text(encoding="utf-8"))
    lo, hi = meta["density_edges_pop"]
    band = str(_density_band(pd.Series([pop_cell]), (lo, hi)).iloc[0])
    sub = bench[(bench["density_band"] == band) & bench["reportable"]]
    rows = []
    for ct in ("DC", "AC"):
        s = sub[sub["current_type"] == ct]
        if not len(s):
            continue
        # Trọng số theo n để một nhóm 25 trạm không lấn nhóm 900 trạm.
        w = s["n"].to_numpy()
        rows.append({"current_type": ct, "n": int(w.sum()), "util_p50": float(np.average(s["util_p50"], weights=w))})
    return {"density_band": band, "observed": rows}
