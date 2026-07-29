"""T1 retrodiction — thiết kế ĐÓNG BĂNG pre-reg §5: GT NEW-HIGH vs hai control, chạy MỘT lần as-is.

Vì sao tách ``compute_metrics``/``sample_control_*`` thành hàm thuần: phần đắt (make_context,
chấm 3 lô) và phần logic (sampling, metric) phải kiểm được ĐỘC LẬP bằng frame synthetic —
test không được đụng data thật, còn run_t1 chỉ là dây chuyền nối các hàm đã kiểm.

Kỷ luật chống leakage (pre-reg §2 + §5):
- Nền N của mode retrodiction purge TOÀN BỘ wave NEW (cả AMBIGUOUS) — engine.make_context
  đã chặn cứng retro tay không;
- Control lấy từ ô KHÔNG AI xây trong cửa sổ: loại ô covered0 bản CHƯA exclude ∪ ô mọi
  điểm NEW — dùng nền đã-exclude sẽ để lọt chính chỗ operator vừa chọn làm "đối chứng";
- Vault-ToS §0 TRỌN VẸN — "không mang toạ độ/mã trạm vault": point_id ẩn danh ``gt-<i>``,
  ``gt.parquet`` KHÔNG có cột lat/lng, và lô GT chấm với ``redact_coords_in_log=True``
  (log JSONL cũng là artefact bền — rò qua log là rò). Toạ độ thật chỉ sống trong RAM.

Mọi randomness qua ``numpy.random.default_rng`` seed đóng băng trong params — chạy 2 lần y hệt.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import h3
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ev_siting.assess import engine, params, paths

#: Cột bắt buộc của gold new_supply — thiếu cột nào là sai schema nguồn, nổ sớm thay vì KeyError mù.
_GT_COLS = ["evcs_code", "lat", "lng", "verdict", "new_confidence"]

#: Tier tính "hit" cho GT (pre-reg §5 metric 1): máy không được Từ chối chỗ operator đã thật sự xây.
_HIT_TIERS = frozenset({params.TIER_ACCEPT, params.TIER_REVIEW})


def _sha256_file(path: Path) -> str:
    # Hash streaming theo khối — pin provenance file GT vào report mà không kéo cả file vào RAM.
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _read_new_supply(path: Path) -> pd.DataFrame:
    """Đọc parquet gold new_supply, kiểm schema — đường đọc CHUNG cho GT lẫn danh sách purge."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(
            f"T1 FAIL: không thấy ground truth {path} — repo evcs-dataset phải nằm cạnh repo này, "
            "hoặc override đường dẫn bằng --ground-truth PATH (CLI t1) / --exclude-new-from PATH (CLI score)"
        )
    df = pd.read_parquet(path)
    missing = [c for c in _GT_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"T1 FAIL: {path} thiếu cột {missing} — không phải gold new_supply đúng schema F11")
    return df


def load_ground_truth(path: Path = paths.GROUND_TRUTH_NEW_SUPPLY) -> tuple[pd.DataFrame, list[str], str]:
    """Đọc gold new_supply → (GT NEW-HIGH, danh sách purge cả wave, sha256 pin provenance).

    ``new_all_codes`` gồm MỌI mã ``verdict==NEW`` kể cả AMBIGUOUS: nghi ngờ là trạm mới cũng
    phải rời nền N (pre-reg §2 — purge cả wave), nhưng chỉ NEW-HIGH mới đủ chuẩn làm GT chấm
    điểm (§5). DRIFT_DUPLICATE ở lại nền — đó là trạm cũ trôi toạ độ, không phải cung mới.
    """
    path = Path(path)
    df = _read_new_supply(path)
    is_new = df["verdict"] == params.GT_VERDICT
    gt = (
        df.loc[is_new & (df["new_confidence"] == params.GT_CONFIDENCE), ["evcs_code", "lat", "lng"]]
        .reset_index(drop=True)
    )  # fmt: skip
    new_all_codes = df.loc[is_new, "evcs_code"].astype(str).tolist()
    return gt, new_all_codes, _sha256_file(path)


def _pop_bins(dem_df: pd.DataFrame) -> pd.Series:
    """Ô r8 -> mã decile pop, tính trên TOÀN BỘ ô pop>0 (pre-reg §5 — decile của quỹ ô có dân,
    không phải của riêng pool sau loại trừ: đổi tập tính decile là đổi định nghĩa control)."""
    pos = dem_df.loc[pd.to_numeric(dem_df["pop"], errors="coerce") > 0, ["h3_r8", "pop"]]
    codes = pd.qcut(pos["pop"].astype(float), 10, labels=False, duplicates="drop")
    return pd.Series(codes.to_numpy(), index=pos["h3_r8"].to_numpy())


def sample_control_a(
    dem_df: pd.DataFrame,
    gt_cells: Iterable[str],
    occupied_cells: set[str],
    n: int,
    seed: int = params.SEED_CONTROL_A,
) -> tuple[pd.DataFrame, dict]:
    """Control A — khớp histogram decile-pop của tập ô GT (pre-reg §5, seed 20260728).

    Vì sao khớp histogram thay vì sample uniform: AUC phải đo cấu trúc biên + cạnh tranh,
    không được thắng "miễn phí" chỉ vì GT nằm chỗ đông dân hơn control (caveat §6.3).
    Bin thiếu ô thì lấy hết + ghi thiếu vào meta — không sample có hoàn lại để bù, vì
    lặp điểm làm AUC tự tương quan.
    """
    cell_bin = _pop_bins(dem_df)
    gt_list = list(gt_cells)
    excluded = set(occupied_cells) | set(gt_list)

    # Pop của ô GT tra từ CHÍNH lưới cầu — ô GT ngoài lưới không có decile để khớp, bỏ + ghi meta.
    gt_bins = [cell_bin.get(c) for c in gt_list]
    matched = [b for b in gt_bins if b is not None]
    hist = Counter(matched)
    total = sum(hist.values())
    # Hai lý do rơi khác nhau phải đếm riêng (adversarial C12): "không có trong lưới cầu"
    # ≠ "có trong lưới nhưng pop≤0" — report nói nhầm cái sau thành cái trước là sai fact.
    in_dem = set(dem_df["h3_r8"].astype(str))
    n_not_in_dem = sum(1 for c in gt_list if c not in in_dem)
    meta: dict = {
        "seed": int(seed),
        "n_requested": int(n),
        "n_gt_dropped_not_in_dem": int(n_not_in_dem),
        "n_gt_dropped_pop_nonpositive": int(len(gt_list) - len(matched) - n_not_in_dem),
        # qcut duplicates="drop": ties dày có thể sập số bin < 10 — "decile" chỉ đúng nghĩa
        # khi con số này = 10, report phải nhìn thấy nó (adversarial P4/P7).
        "n_effective_bins": int(cell_bin.nunique()),
        "shortfall": {},
    }
    if total == 0 or n <= 0:
        meta["n_sampled"] = 0
        return pd.DataFrame({"lat": [], "lng": [], "h3_r8": []}), meta

    # Phân bổ n theo tỷ lệ histogram GT, làm tròn largest-remainder (tie-break theo mã bin
    # cho tái lập); n == tổng histogram (trường hợp chuẩn §5) thì alloc == histogram y nguyên.
    bins_sorted = sorted(hist)
    raw = {b: hist[b] * n / total for b in bins_sorted}
    alloc = {b: int(np.floor(raw[b])) for b in bins_sorted}
    rem = int(n - sum(alloc.values()))
    for b in sorted(bins_sorted, key=lambda b: (-(raw[b] - alloc[b]), b))[:rem]:
        alloc[b] += 1

    pool = cell_bin[~cell_bin.index.isin(excluded)]
    rng = np.random.default_rng(seed)
    chosen: list[str] = []
    for b in bins_sorted:  # duyệt bin theo thứ tự cố định — thứ tự gọi rng là một phần của tái lập
        cand = np.array(sorted(pool.index[pool == b].tolist()))  # sort để độc lập thứ tự dòng dem_df
        k = alloc[b]
        if len(cand) < k:
            meta["shortfall"][int(b)] = int(k - len(cand))
            chosen.extend(cand.tolist())
        else:
            chosen.extend(rng.choice(cand, size=k, replace=False).tolist())

    # Điểm control = TÂM ô (artefact lưới r8 — caveat §6.5 đã khai trước), GT giữ toạ độ thật.
    latlng = [h3.cell_to_latlng(c) for c in chosen]
    df = pd.DataFrame({"lat": [p[0] for p in latlng], "lng": [p[1] for p in latlng], "h3_r8": chosen}).reset_index(
        drop=True
    )
    meta["n_sampled"] = int(len(df))
    return df, meta


def sample_control_b(
    dem_df: pd.DataFrame,
    occupied_cells: set[str],
    n: int = params.N_CONTROL_B,
    seed: int = params.SEED_CONTROL_B,
    q: float = params.CONTROL_LOW_POP_Q,
) -> tuple[pd.DataFrame, dict]:
    """Control B — ô cầu thấp 0 < pop ≤ p30(pop>0), uniform (pre-reg §5, seed 20260729).

    Đây là phép đo specificity: máy tốt phải DÁM không Đồng ý ở chỗ vắng — quantile tính
    trên toàn tập pop>0 (trước loại trừ) để ngưỡng "thấp" không dịch theo mạng trạm.
    """
    pop = pd.to_numeric(dem_df["pop"], errors="coerce")
    pos = dem_df.loc[pop > 0]
    thresh = float(pos["pop"].astype(float).quantile(q))
    low = pos.loc[pos["pop"].astype(float) <= thresh, "h3_r8"]
    cells = np.array(sorted(low[~low.isin(set(occupied_cells))].tolist()))

    rng = np.random.default_rng(seed)
    meta: dict = {"seed": int(seed), "n_requested": int(n), "pop_threshold": thresh, "shortfall": 0}
    if len(cells) < n:
        chosen = cells.tolist()  # pool cạn: lấy hết + khai thiếu — không nới ngưỡng để đủ số
        meta["shortfall"] = int(n - len(cells))
    else:
        chosen = rng.choice(cells, size=int(n), replace=False).tolist()

    latlng = [h3.cell_to_latlng(c) for c in chosen]
    df = pd.DataFrame({"lat": [p[0] for p in latlng], "lng": [p[1] for p in latlng], "h3_r8": chosen}).reset_index(
        drop=True
    )
    meta["n_sampled"] = int(len(df))
    return df, meta


def _auc_one(gt_scores, a_scores) -> tuple[float | None, dict]:
    """AUC GT(nhãn 1) vs control A(nhãn 0) trên một cột score; NaN bị loại và ĐẾM —
    số dòng rơi phải lộ ra report, không được lặng lẽ thu nhỏ mẫu (I-2)."""
    g = np.asarray(gt_scores, dtype=float)
    a = np.asarray(a_scores, dtype=float)
    gv, av = g[~np.isnan(g)], a[~np.isnan(a)]
    dropped = {"gt": int(len(g) - len(gv)), "control_a": int(len(a) - len(av))}
    if len(gv) == 0 or len(av) == 0:  # một phía rỗng thì AUC không định nghĩa — None, không đoán 0.5
        return None, dropped
    y = np.concatenate([np.ones(len(gv)), np.zeros(len(av))])
    return float(roc_auc_score(y, np.concatenate([gv, av]))), dropped


def _reason_prefix_counts(scored: pd.DataFrame) -> dict:
    """Đếm reason theo prefix mã R01..R11 (3 ký tự đầu) — phân bố reason là metric phụ §5,
    chỉ cần tần suất mã, không cần con số fact đi kèm từng dòng."""
    c: Counter[str] = Counter()
    for rs in scored["reasons"]:
        for r in rs:
            c[str(r)[:3]] += 1
    return dict(sorted(c.items()))


def compute_metrics(gt_scored: pd.DataFrame, a_scored: pd.DataFrame, b_scored: pd.DataFrame) -> dict:
    """Toàn bộ metric T1 (§5) từ 3 frame đã chấm — hàm THUẦN, không I/O, test bằng frame giả.

    Metric chính: hit_rate (GT không bị Từ chối), low_accept_share (B không được Đồng ý),
    AUC score_total GT vs A. Metric phụ: AUC từng trục, phân bố tier + reason từng nhóm.
    """
    hit_rate = float(gt_scored["tier"].isin(_HIT_TIERS).mean()) if len(gt_scored) else float("nan")
    low_accept = float((b_scored["tier"] == params.TIER_ACCEPT).mean()) if len(b_scored) else float("nan")

    auc, d_total = _auc_one(gt_scored["score_total"], a_scored["score_total"])
    auc_n, d_n = _auc_one(gt_scored["score_N"], a_scored["score_N"])
    auc_v, d_v = _auc_one(gt_scored["score_V"], a_scored["score_V"])

    groups = {"gt": gt_scored, "control_a": a_scored, "control_b": b_scored}
    return {
        "hit_rate": hit_rate,
        "low_accept_share": low_accept,
        "auc": auc,
        "auc_N": auc_n,
        "auc_V": auc_v,
        "auc_n_dropped": {"auc": d_total, "auc_N": d_n, "auc_V": d_v},
        "tier_counts": {g: {str(k): int(v) for k, v in df["tier"].value_counts().items()} for g, df in groups.items()},
        "reason_counts": {g: _reason_prefix_counts(df) for g, df in groups.items()},
        "n": {g: int(len(df)) for g, df in groups.items()},
    }


def json_safe(obj):
    """NaN/numpy scalar -> JSON hợp lệ đệ quy — report là hợp đồng đọc-bằng-máy, NaN phải thành null."""
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        f = float(obj)
        return f if np.isfinite(f) else None
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def _target_check(value, target: float, op: str) -> dict:
    """Cờ đạt/không so target STATE §5 — báo as-is; metric không tính được (None/NaN) là KHÔNG đạt,
    không phải "tạm coi như đạt"."""
    defined = value is not None and np.isfinite(value)
    ok = bool(defined and (value >= target if op == ">=" else value <= target))
    return {"value": value, "target": target, "op": op, "passed": ok}


def _fmt(x) -> str:
    return "NA" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.3f}"


def run_t1(
    scope: str = params.SCOPE,
    label: str = params.FREEZE_LABEL,
    ground_truth_path: Path | None = None,
    out_dir: Path = paths.T1_DIR,
) -> dict:
    """Chạy trọn T1 retrodiction theo pre-reg §5 và ghi kết quả + provenance vào ``out_dir``.

    Chấm ``plan=False``: mỗi hồ sơ NPP là một quyết định độc lập vs nền (G3 không áp trong T1).
    point_id ẩn danh ``gt-<i>`` — mã trạm vault không được rời khỏi hàm này (Vault-ToS §0).
    """
    gt_path = Path(ground_truth_path) if ground_truth_path is not None else paths.GROUND_TRUTH_NEW_SUPPLY
    gt, new_all_codes, gt_sha = load_ground_truth(gt_path)
    exclude = [params.station_id_from_code(c) for c in new_all_codes]
    actx = engine.make_context(mode="retrodiction", exclude_station_ids=exclude, scope=scope, label=label)

    # Ô "đã có người": covered0 bản CHƯA exclude ∪ ô của MỌI điểm NEW (cả AMBIGUOUS) —
    # control phải là chỗ KHÔNG AI xây trong cửa sổ; lấy nền retro (đã purge) sẽ cho phép
    # control rơi đúng ô operator vừa chọn, làm AUC tự đánh lừa.
    full = _read_new_supply(gt_path)
    new_pts = full.loc[full["verdict"] == params.GT_VERDICT, ["lat", "lng"]].dropna()
    new_cells = {h3.latlng_to_cell(float(la), float(lo), 8) for la, lo in zip(new_pts["lat"], new_pts["lng"])}
    occupied = set(actx.bundle.covered0["h3_r8"].astype(str)) | new_cells

    # dem_df tái tạo từ context (Series h3_r8 -> pop) — không đọc demand parquet lần hai.
    dem_df = actx.dem.rename("pop").rename_axis("h3_r8").reset_index()
    gt_cells = [
        h3.latlng_to_cell(float(la), float(lo), 8)
        for la, lo in zip(gt["lat"], gt["lng"])
        if np.isfinite(float(la)) and np.isfinite(float(lo))
    ]

    a_pts, a_meta = sample_control_a(dem_df, gt_cells, occupied, n=len(gt))
    b_pts, b_meta = sample_control_b(dem_df, occupied)

    gt_in = pd.DataFrame(
        {
            "point_id": [f"gt-{i}" for i in range(len(gt))],
            "lat": gt["lat"].to_numpy(dtype=float),
            "lng": gt["lng"].to_numpy(dtype=float),
        }
    )
    a_in = a_pts.assign(point_id=[f"ca-{i}" for i in range(len(a_pts))])[["point_id", "lat", "lng"]]
    b_in = b_pts.assign(point_id=[f"cb-{i}" for i in range(len(b_pts))])[["point_id", "lat", "lng"]]

    # GT là toạ độ vault: log JSONL lược lat/lng (Vault-ToS §0 áp cả lên log — C1/C15).
    # Control là tâm ô lưới cầu công khai, giữ toạ độ bình thường.
    gt_scored = engine.assess(gt_in, actx, plan=False, redact_coords_in_log=True)
    a_scored = engine.assess(a_in, actx, plan=False)
    b_scored = engine.assess(b_in, actx, plan=False)

    metrics = compute_metrics(gt_scored, a_scored, b_scored)
    results = json_safe(
        {
            "metrics": metrics,
            "targets": {
                "hit_rate": _target_check(metrics["hit_rate"], params.T1_TARGET_HIT, ">="),
                "low_accept_share": _target_check(metrics["low_accept_share"], params.T1_MAX_LOW_ACCEPT, "<="),
                "auc": _target_check(metrics["auc"], params.T1_TARGET_AUC, ">="),
            },
            "provenance": {
                "ground_truth_path": str(gt_path),
                "ground_truth_sha256": gt_sha,
                "n_gt": len(gt),
                "n_control_a": len(a_scored),
                "n_control_b": len(b_scored),
                "n_new_all_codes": len(new_all_codes),
                # Số trạm khớp THỰC TẾ trong covered0 — pre-reg §2 bắt báo để lệch map mã lộ ra.
                "n_excluded_matched": actx.net.n_excluded,
                "seeds": {"control_a": params.SEED_CONTROL_A, "control_b": params.SEED_CONTROL_B},
                "control_a_meta": a_meta,
                "control_b_meta": b_meta,
                # Pin sha256 demand_h3 (pre-reg §0 — input ngoài bundle phải có vân tay trong report).
                "demand_h3_sha256": actx.demand_sha256,
                "data_version": params.DATA_VERSION,
                "model_version": params.MODEL_VERSION,
                "calibration": params.CALIBRATION_LABEL,
                "vault_tos_restricted": True,
            },
        }
    )

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Vault-ToS §0 áp NGUYÊN VĂN lên artefact: gt.parquet không mang mã trạm ĐÃ ĐÀNH,
    # cũng không mang lat/lng — toạ độ chính xác join 1-1 ngược về part.parquet vault
    # là tái định danh trọn vẹn (adversarial C1/C15). Feature/score/tier giữ đủ.
    gt_scored.drop(columns=["lat", "lng"]).to_parquet(out_dir / "gt.parquet", index=False)
    a_scored.to_parquet(out_dir / "control_a.parquet", index=False)
    b_scored.to_parquet(out_dir / "control_b.parquet", index=False)
    (out_dir / "t1_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    m = results["metrics"]
    print(
        f"T1 [{params.DATA_VERSION}] hit_rate={_fmt(m['hit_rate'])} "
        f"low_accept={_fmt(m['low_accept_share'])} auc={_fmt(m['auc'])} "
        f"(auc_N={_fmt(m['auc_N'])}, auc_V={_fmt(m['auc_V'])}) | "
        f"n GT/A/B = {m['n']['gt']}/{m['n']['control_a']}/{m['n']['control_b']} | "
        f"excluded khớp = {results['provenance']['n_excluded_matched']}/{len(new_all_codes)}"
    )
    return results
