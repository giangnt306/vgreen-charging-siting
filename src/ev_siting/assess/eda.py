"""EDA sàng tín hiệu cho v0.2 — CHỈ chạy trên nửa DESIGN (holdout niêm phong).

Câu hỏi đúng một câu: *trong toàn bộ dữ liệu Giang đang có, tín hiệu nào thật sự tách được
"chỗ operator đã xây" khỏi "ô ngẫu nhiên cùng phân tầng"?* Trả lời bằng AUC đơn biến, không
bằng trực giác — v0 fail chính vì chọn trục theo trực giác (coverage-marginal) rồi mới đo.

Kỷ luật:
- Mọi điểm phải thuộc block ``design`` (assert cứng) — holdout chỉ mở ở lần đánh giá v0.2.
- Nền N là mode retrodiction (purge cả wave NEW) như T1, để feature ở đây so được với T1 v0.
- AUC báo **hai chiều**: <0,5 nghĩa là tín hiệu NGƯỢC dấu, không phải "yếu" — đó chính là
  phát hiện của T1 v0 với trục coverage (auc_N 0,426).

Bảng ra là đầu vào của (a) pre-reg v0.2 và (b) B5 — dòng nào "cần mà data chưa có" thành
yêu cầu gửi Giang, kèm bằng chứng thay vì wish-list.

Chạy: uv run python -m ev_siting.assess.eda
"""

from __future__ import annotations

import json
from pathlib import Path

import h3
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from ev_siting.assess import engine, kernel, params, paths, retrodiction
from ev_siting.assess.holdout import label_points, load_split

OUT_DIR = paths.OUT_DIR / "eda"

#: Cột demand_h3 lấy làm feature — tất cả đều đã có sẵn, chưa cái nào được v0 dùng
#: ngoài `pop`. Đây là phần "nếu thiếu thì EDA moi thêm" của kế hoạch.
DEMAND_COLS = ["pop", "road_len_m", "road_len_mt_m", "n_poi", "n_parking", "n_fuel"]

#: Cột candidate frozen — tính ra để LÀM BẰNG CHỨNG, KHÔNG để dùng làm feature.
#: Đo được 28/07: 763/763 ô GT nằm trong candidate set và 100% mang tier T0
#: (`is_existing=True`); 2.877/2.877 ô trạm NEW đều là anchor T0. Nguyên nhân: candidate
#: set sinh anchor T0 từ TRẠM HIỆN CÓ, và bundle frozen build trên `covered0` CHƯA purge
#: wave NEW ⇒ quỹ đất "biết trước" chỗ operator đã xây. Mọi `cand_*` vì thế là leakage
#: thuần trong bài retrodiction — AUC 0,899 của `cand_in_landbank` là số ma.
CAND_COLS = ["penalty", "built_up_frac", "dist_substation_m"]

#: Prefix feature bị nhiễm leakage — giữ trong bảng kèm cờ, loại khỏi mọi xếp hạng.
LEAKY_PREFIX = "cand_"
LEAK_REASON = "candidate set dùng trạm hiện có làm anchor T0 (763/763 ô GT là T0) — biết trước đáp án"


def enrich(points: pd.DataFrame, actx: engine.AssessContext, dem_df: pd.DataFrame) -> pd.DataFrame:
    """Thêm feature thô quanh mỗi điểm: tại-ô + tổng-catchment + thuộc tính quỹ đất."""
    lats = points["lat"].to_numpy(dtype=float)
    lngs = points["lng"].to_numpy(dtype=float)
    cells = [h3.latlng_to_cell(la, lo, 8) for la, lo in zip(lats, lngs)]

    dem_idx = dem_df.set_index("h3_r8")
    at_cell = dem_idx.reindex(cells)[DEMAND_COLS].reset_index(drop=True)
    at_cell.columns = [f"cell_{c}" for c in DEMAND_COLS]

    # Tổng trong đĩa phục vụ R — cùng kernel phủ với engine (C10, một hệ quy chiếu).
    lookup = {c: dem_idx[col].to_dict() for c, col in zip(DEMAND_COLS, DEMAND_COLS)}
    sums = {f"catch_{c}": np.zeros(len(points)) for c in DEMAND_COLS}
    for i, (la, lo) in enumerate(zip(lats, lngs)):
        cov = kernel.point_cells(la, lo, actx.net.r_km)
        for c in DEMAND_COLS:
            tbl = lookup[c]
            sums[f"catch_{c}"][i] = sum(tbl.get(x, 0.0) or 0.0 for x in cov)

    cand = actx.bundle.candidates.set_index("h3_r8")
    cand = cand[~cand.index.duplicated(keep="first")]
    cand_feat = cand.reindex(cells)[CAND_COLS].reset_index(drop=True)
    cand_feat.columns = [f"cand_{c}" for c in CAND_COLS]
    cand_feat["cand_in_landbank"] = pd.Series(cells).isin(cand.index).astype(float)

    return pd.concat([points.reset_index(drop=True), at_cell, pd.DataFrame(sums), cand_feat], axis=1)


def _derived(df: pd.DataFrame) -> pd.DataFrame:
    """Feature suy diễn — mỗi cái có một giả thuyết đứng sau, không phải rắc gia vị."""
    out = df.copy()
    d = pd.to_numeric(out["d_nearest_m"], errors="coerce")
    # Giả thuyết BAND: operator thích "gần mạng nhưng không sát" (T1 v0: GT median 1,7 km,
    # control cầu-thấp 3,1 km). Khoảng cách thô là ĐƠN ĐIỆU nên AUC của nó không bắt được
    # dạng chuông — mã hoá lại thành độ lệch khỏi dải 1–3 km (càng nhỏ càng "giống chỗ đã xây").
    lo, hi = 1000.0, 3000.0
    out["d_band_fit"] = -np.maximum(0.0, np.maximum(lo - d, d - hi))
    out["log_d_nearest"] = np.log10(d.clip(lower=1.0))
    # Mật độ cung địa phương: đối trọng của v_competition ở thang R chứ không phải 1 km.
    out["supply_density_r"] = pd.to_numeric(out["v_demand_local"], errors="coerce") / (
        1.0 + pd.to_numeric(out["v_pressure"], errors="coerce")
    )
    return out


_SKIP = {
    "point_id", "lat", "lng", "tier", "mode", "credit_rule", "data_version",
    "model_version", "calibration", "vault_tos_restricted", "gates_fired", "reasons",
    "group", "h3_r8",
}  # fmt: skip


def single_var_auc(pos: pd.DataFrame, neg: pd.DataFrame) -> pd.DataFrame:
    """AUC từng feature, GT(1) vs control(0). Báo cả hướng — <0,5 là NGƯỢC dấu, không phải yếu."""
    rows = []
    for col in pos.columns:
        if col in _SKIP or not np.issubdtype(pd.to_numeric(pos[col], errors="coerce").dtype, np.number):
            continue
        p = pd.to_numeric(pos[col], errors="coerce")
        n = pd.to_numeric(neg[col], errors="coerce")
        pv, nv = p[p.notna()], n[n.notna()]
        if len(pv) < 30 or len(nv) < 30 or (pv.nunique() + nv.nunique()) < 3:
            continue
        y = np.concatenate([np.ones(len(pv)), np.zeros(len(nv))])
        auc = float(roc_auc_score(y, np.concatenate([pv.to_numpy(), nv.to_numpy()])))
        leaky = col.startswith(LEAKY_PREFIX)
        rows.append(
            {
                "feature": col,
                "auc": round(auc, 4),
                # |AUC−0,5| là sức tách thật; hướng cho biết dấu phải dùng trong score.
                "strength": round(abs(auc - 0.5), 4),
                "direction": "cao hơn ở GT" if auc >= 0.5 else "THẤP hơn ở GT (ngược dấu)",
                "n_pos": int(len(pv)),
                "n_neg": int(len(nv)),
                "na_pos": int(p.isna().sum()),
                "usable": not leaky,
                "note": LEAK_REASON if leaky else "",
            }
        )
    out = pd.DataFrame(rows)
    # Sắp xếp: feature dùng được trước, trong mỗi nhóm mạnh trước. Feature leaky KHÔNG
    # được đứng đầu bảng — đó đúng là cách một số ma lọt vào pre-reg.
    return out.sort_values(["usable", "strength"], ascending=[False, False]).reset_index(drop=True)


def run(out_dir: Path = OUT_DIR) -> dict:
    split = load_split()
    gt, new_all_codes, gt_sha = retrodiction.load_ground_truth()
    exclude = [params.station_id_from_code(c) for c in new_all_codes]
    actx = engine.make_context(mode="retrodiction", exclude_station_ids=exclude)

    lab = label_points(gt["lat"].to_numpy(), gt["lng"].to_numpy(), split["blocks"])
    gt_d = gt.loc[lab == "design"].reset_index(drop=True)
    assert len(gt_d) == split["n_design"], "số điểm design lệch file niêm phong"

    dem_df = actx.dem.rename("pop").rename_axis("h3_r8").reset_index()
    dem_full = pd.read_parquet(paths.DEMAND_H3)

    # Ô "đã có người" như T1; thêm ràng buộc pool control PHẢI nằm trong block design.
    full = retrodiction._read_new_supply(paths.GROUND_TRUTH_NEW_SUPPLY)
    new_pts = full.loc[full["verdict"] == params.GT_VERDICT, ["lat", "lng"]].dropna()
    occupied = set(actx.bundle.covered0["h3_r8"].astype(str)) | {
        h3.latlng_to_cell(float(a), float(b), 8) for a, b in zip(new_pts["lat"], new_pts["lng"])
    }
    centers = np.array([h3.cell_to_latlng(c) for c in dem_df["h3_r8"]])
    cell_side = label_points(centers[:, 0], centers[:, 1], split["blocks"])
    occupied |= set(dem_df.loc[cell_side != "design", "h3_r8"])  # khoá pool về nửa design

    gt_cells = [h3.latlng_to_cell(float(a), float(b), 8) for a, b in zip(gt_d["lat"], gt_d["lng"])]
    a_pts, a_meta = retrodiction.sample_control_a(dem_df, gt_cells, occupied, n=len(gt_d))
    b_pts, b_meta = retrodiction.sample_control_b(dem_df, occupied, n=min(params.N_CONTROL_B, len(gt_d)))

    log = out_dir / "eda_assess_log.jsonl"  # log riêng: EDA không làm bẩn sổ chấm chính thức
    frames = {}
    for name, pts, redact in (
        ("gt", gt_d.assign(point_id=[f"d-gt-{i}" for i in range(len(gt_d))]), True),
        ("control_a", a_pts.assign(point_id=[f"d-ca-{i}" for i in range(len(a_pts))]), False),
        ("control_b", b_pts.assign(point_id=[f"d-cb-{i}" for i in range(len(b_pts))]), False),
    ):
        scored = engine.assess(
            pts[["point_id", "lat", "lng"]], actx, plan=False, log_path=log, redact_coords_in_log=redact
        )
        frames[name] = _derived(enrich(scored, actx, dem_full)).assign(group=name)

    table = single_var_auc(frames["gt"], frames["control_a"])
    table_b = single_var_auc(frames["gt"], frames["control_b"])
    table = table.merge(
        table_b[["feature", "auc"]].rename(columns={"auc": "auc_vs_control_b"}), on="feature", how="left"
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_dir / "signals.csv", index=False)
    for name, df in frames.items():
        df.drop(columns=["lat", "lng"] if name == "gt" else []).to_parquet(
            out_dir / f"design_{name}.parquet", index=False
        )
    meta = {
        "half": "design",
        "n": {k: int(len(v)) for k, v in frames.items()},
        "holdout_sealed": {"n_holdout": split["n_holdout"], "block_res": split["block_res"]},
        "control_a_meta": a_meta,
        "control_b_meta": b_meta,
        "ground_truth_sha256": gt_sha,
        "demand_h3_sha256": actx.demand_sha256,
        "data_version": params.DATA_VERSION,
        "n_excluded_matched": actx.net.n_excluded,
    }
    (out_dir / "eda_meta.json").write_text(
        json.dumps(retrodiction.json_safe(meta), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"[eda] design half: GT {len(frames['gt'])} vs A {len(frames['control_a'])} / B {len(frames['control_b'])}")
    print(table.head(20).to_string(index=False))
    print(f"[eda] -> {out_dir}/signals.csv")
    return {"table": table, "meta": meta}


if __name__ == "__main__":
    run()
