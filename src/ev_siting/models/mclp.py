"""Maximum coverage location problem — solver + bench bấm giờ (Kỳ).

Vào: bundle model-ready đã đóng băng (``paths.frozen_scope_dir``) — candidate sites +
covered0 của **cùng một AOI** — và lưới cầu ``demand_h3`` (interim, dùng chung mọi scope).
Ra: ``outputs/mclp/``.

Mô hình (Church & ReVelle 1974), biến nhị phân::

    max   Σ_j w_j y_j
    s.t.  y_j ≤ Σ_{i ∈ N_j} x_i      ∀j        (ô j chỉ được tính khi có ≥1 trạm phủ nó)
          Σ_i c_i x_i ≤ B                       (c ≡ 1, B = p ⇒ ràng buộc đếm)
          x, y ∈ {0,1}

Hợp đồng chi phí đã chốt (candidate-sites.md §10, hằng số ở ``models/paths.py``)::

    CapEx_i = base(capex_class_i) × (1 + λ · penalty_i),  λ = 1,0

``penalty`` đi vào **hàm chi phí**, không vào ràng buộc khả thi; T0 (``is_existing``)
có CapEx = 0 và bắt buộc mở. Nghĩa vụ báo cáo + gate sensitivity ở ``assess.py``.
Ở đây ``costs=`` là tham số phơi ra sẵn: khi ``base(capex_class)`` có số thật thì
ràng buộc đếm đổi thành ràng buộc ngân sách mà không phải sửa mô hình. **Chưa có số
thật** ⇒ bench chạy biến thể đếm (``p``), đúng phạm vi B6.

Hai chế độ:

* ``greenfield`` — mọi candidate tự do (đúng chữ đề bài B6: 28.075 × 268.404);
* ``brownfield`` — T0 bắt buộc mở, ô đã phủ bị rút khỏi mục tiêu ⇒ tối ưu **phần
  biên**. Đây là bài thật sự phải giải; nó nhỏ hơn hẳn và ta báo cả hai.

Chạy từ repo root::

    make mclp-bench                     # B6: p ∈ {20,100,800}, cả hai chế độ
    PYTHONPATH=src python -m ev_siting.models.mclp --scope hanoi --p 20
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field

import h3
import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.optimize import LinearConstraint, milp
from sklearn.neighbors import BallTree

from ev_siting.aoi import haversine_km
from ev_siting.data.worldpop.paths import DEMAND_H3

from . import rules as rl
from .paths import (
    DEFAULT_FREEZE_LABEL,
    MCLP_DIR,
    R_SERVICE_KM,
    ensure_dirs,
    frozen_scope_dir,
)

#: Cạnh ô r8 dùng để suy số vành grid_disk — GIỮ ĐÚNG hằng của ``build_candidates``.
_R8_STEP_KM = 0.98
#: Trần thời gian mỗi lần gọi solver (giây). Bench báo gap nếu chạm trần.
DEFAULT_TIME_LIMIT_S = 900.0
#: Ngưỡng gap tương đối coi là "giải được" khi solver chạm trần thời gian.
SOLVED_GAP = 0.01


# ─────────────────────────── phủ: candidate → ô cầu ───────────────────────────


def coverage_matrix(cand_cells, demand_cells, R_km=R_SERVICE_KM):
    """Ma trận phủ thưa ``A[i, j] = 1`` ⇔ tâm ô cầu *j* nằm trong *R_km* quanh candidate *i*.

    Cùng hệ quy chiếu với ``features.build_candidates._coverage_cells`` (C10 — một
    hệ quy chiếu duy nhất cho mọi tầng); ``_assert_same_frame`` kiểm lại trên mẫu
    thay vì tin lời.
    """
    demand_cells = np.asarray(demand_cells)
    dem_ix = {c: j for j, c in enumerate(demand_cells)}
    dll = np.array([h3.cell_to_latlng(c) for c in demand_cells], dtype=float)

    k = int(np.ceil(R_km / _R8_STEP_KM)) + 1
    rows, cols = [], []
    for i, c in enumerate(cand_cells):
        js = [dem_ix[d] for d in h3.grid_disk(c, k) if d in dem_ix]
        if not js:
            continue
        js = np.fromiter(js, dtype=np.int64, count=len(js))
        c_lat, c_lng = h3.cell_to_latlng(c)
        keep = haversine_km(c_lat, c_lng, dll[js, 0], dll[js, 1]) <= R_km
        js = js[keep]
        rows.append(np.full(js.size, i, dtype=np.int64))
        cols.append(js)

    if not rows:
        return sp.csr_matrix((len(cand_cells), len(demand_cells)), dtype=np.int8)
    rows = np.concatenate(rows)
    cols = np.concatenate(cols)
    data = np.ones(rows.size, dtype=np.int8)
    return sp.csr_matrix((data, (rows, cols)), shape=(len(cand_cells), len(demand_cells)))


def _assert_same_frame(cand_cells, demand_cells, A, R_km, n_sample=25, seed=0):
    """Đối chiếu vài dòng của A với ``build_candidates._coverage_cells`` (nguồn gốc)."""
    from ev_siting.features.build_candidates import _coverage_cells

    rng = np.random.default_rng(seed)
    dem_set = set(demand_cells)
    idx = rng.choice(len(cand_cells), size=min(n_sample, len(cand_cells)), replace=False)
    for i in idx:
        want = _coverage_cells(cand_cells[i], R_km) & dem_set
        got = {demand_cells[j] for j in A.indices[A.indptr[i] : A.indptr[i + 1]]}
        if want != got:
            raise AssertionError(f"coverage lệch hệ quy chiếu ở candidate {cand_cells[i]}: {len(want)} vs {len(got)}")


# ───────────────────────────────── bài toán ──────────────────────────────────


@dataclass
class Instance:
    """Một thể hiện MCLP đã rút gọn, sẵn sàng đưa vào solver."""

    scope: str
    mode: str  # greenfield | brownfield
    cand: pd.DataFrame  # candidate TỰ DO (đã bỏ T0 nếu brownfield)
    A: sp.csr_matrix  # (n_cand_free × n_dem_used)
    w: np.ndarray  # trọng số ô cầu còn trong mục tiêu
    total_w: float  # tổng cầu trên TOÀN lưới demand_h3 (mẫu số cov@pop tuyệt đối)
    reach_w: float  # tổng cầu mà tập candidate CÓ THỂ với tới (mẫu số hiệu năng)
    base_w: float  # cầu đã phủ sẵn bởi T0 (brownfield); 0 nếu greenfield
    n_dem_all: int
    build_s: float = 0.0
    meta: dict = field(default_factory=dict)
    #: Hàng ``Σ x ≤ 1`` của R8 (clique + cặp còn dư). ``None`` = chạy biến thể B6 không luật.
    conflict: sp.csr_matrix | None = None
    #: ``candidate_id``/``station_id`` của trạm đã triển khai — bất biến B0 đối chiếu vào đây.
    existing_ids: tuple = ()

    @property
    def n_cand(self):
        return self.A.shape[0]

    @property
    def n_dem(self):
        return self.A.shape[1]


def load_instance(
    scope="vietnam",
    mode="greenfield",
    R_km=R_SERVICE_KM,
    label=DEFAULT_FREEZE_LABEL,
    weight="pop",
    rules=None,
    cand_pool="free",
    assume_highload=False,
    aoi=None,
):
    """Dựng thể hiện từ bundle đóng băng + ``demand_h3``.

    ``rules=None`` ⇒ **đúng biến thể B6** (không luật) — giữ mọi số neo cũ so sánh được.
    Truyền ``RuleSet`` ⇒ áp bộ luật BO:

    * **R2** — ``S₀`` chỉ gồm trạm có ≥1 trụ DC. Trạm chỉ-AC KHÔNG bị xoá (bất biến B0);
      chúng rời phần-được-tính-phủ và có thể vào tập ứng viên qua ``cand_pool``.
    * **R5/R6** — tiền lọc bậc một trên toạ độ THẬT; T0 được grandfather.
    * **R8** — sinh hàng xung đột, gắn vào ``Instance.conflict``.

    ``aoi=(lat, lng, radius_km)`` cắt lát địa bàn: giới hạn **cả** ô cầu **và** ứng viên
    về trong bán kính, và tính lại ``total_w`` trên đúng dân số địa bàn đó — nên
    ``cov@pop`` của một TP là *phủ trong TP / dân TP*, không phải mẫu số quốc gia. Nền
    ``covered0`` vẫn tính từ **toàn bộ** mạng DC (trạm ngay ngoài ranh vẫn phủ vào trong).

    ``cand_pool`` ∈ ``{"free", "upgrade", "both"}``: xây mới / nâng cấp ô đang có trạm
    chỉ-AC / cả hai. ``assume_highload`` mặc định ``False`` = phía bảo thủ: chưa biết
    công suất trụ sẽ lắp thì áp ngưỡng 2 km chứ không tự cho hưởng nới 500 m của R6.

    ⚠ ``rules`` cần bảng ``canonical/stations`` + ``connectors`` **ngoài bundle frozen**
    (bundle không mang thông tin trụ). Cùng quy ước với ``demand_h3``: đọc ngoài bundle
    thì **pin sha256 vào meta** — xem ``meta["rule_inputs"]``.
    """
    t0 = time.perf_counter()
    d = frozen_scope_dir(scope, label)
    if not d.exists():
        raise SystemExit(f"FROZEN FAIL: thiếu bundle {d} — chạy `make freeze-processed LABEL={label}`")

    cand = pd.read_parquet(d / "candidate_sites.parquet")
    dem = pd.read_parquet(DEMAND_H3, columns=["h3_r8", weight])
    dem = dem.drop_duplicates("h3_r8").reset_index(drop=True)
    n_dem_all = len(dem)
    total_w = float(dem[weight].sum())

    dem_cells = dem["h3_r8"].to_numpy()
    w_all = dem[weight].to_numpy(dtype=float)

    if aoi is not None:
        a_lat, a_lng, a_rkm = aoi
        dll = np.array([h3.cell_to_latlng(c) for c in dem_cells], dtype=float)
        in_aoi = haversine_km(a_lat, a_lng, dll[:, 0], dll[:, 1]) <= a_rkm
        dem_cells, w_all = dem_cells[in_aoi], w_all[in_aoi]
        n_dem_all = int(in_aoi.sum())
        total_w = float(w_all.sum())  # mẫu số = dân TP, không phải dân cả nước

    existing = cand[cand["is_existing"]].reset_index(drop=True)
    rule_meta = {}
    if rules is not None:
        net, upgrade, rule_meta = _rule_network(cand, rules)
        t0_cells_all = net["h3_r8"].unique()  # R2: chỉ ô có trạm DC mới tính phủ
    else:
        net, upgrade = existing, existing.iloc[0:0]
        t0_cells_all = existing["h3_r8"].to_numpy()

    base_w = 0.0
    if mode == "brownfield":
        A0 = coverage_matrix(t0_cells_all, dem_cells, R_km)
        covered0 = np.asarray(A0.sum(axis=0)).ravel() > 0
        base_w = float(w_all[covered0].sum())
        _reg_all = np.array([h3.cell_to_parent(c, 5) for c in dem_cells])
        rule_meta["total_by_region"] = dict(pd.Series(w_all).groupby(_reg_all).sum())
        rule_meta["base_by_region"] = dict(pd.Series(w_all * covered0).groupby(_reg_all).sum())
        cand = _cand_pool(cand, upgrade, cand_pool)
        keep = ~covered0  # ô đã phủ là hằng số của mục tiêu -> rút khỏi mô hình
    elif mode == "greenfield":
        cand = _cand_pool(cand, upgrade, cand_pool)
        keep = np.ones(n_dem_all, dtype=bool)
    else:
        raise ValueError(f"mode lạ: {mode}")

    if rules is not None:
        cand, pre = _apply_clearance(cand, net, rules, assume_highload)
        rule_meta.update(pre)

    if aoi is not None:
        a_lat, a_lng, a_rkm = aoi
        keep_c = haversine_km(a_lat, a_lng, cand["lat"].to_numpy(), cand["lng"].to_numpy()) <= a_rkm
        cand = cand[keep_c].reset_index(drop=True)
        rule_meta["aoi"] = {"center": [a_lat, a_lng], "radius_km": a_rkm,
                           "n_cand_in_aoi": int(len(cand)), "n_dem_in_aoi": int(n_dem_all)}

    dem_cells = dem_cells[keep]
    w = w_all[keep]
    A = coverage_matrix(cand["h3_r8"].to_numpy(), dem_cells, R_km)
    _assert_same_frame(cand["h3_r8"].to_numpy(), dem_cells, A, R_km)

    # Ô không candidate nào với tới ⇒ y_j ≡ 0: bỏ đi, nghiệm không đổi.
    reach = np.asarray(A.sum(axis=0)).ravel() > 0
    A = A[:, reach].tocsr()
    w = w[reach]
    dem_cells = dem_cells[reach]  # meta["dem_cells"] phải CÙNG chiều với w/A (sàn ε join theo đây)

    conflict = None
    if rules is not None and rules.d_mutual_m > 0 and rules.mutual_is_hard:
        conflict, cmeta = rl.conflict_rows(
            cand["lat"].to_numpy(), cand["lng"].to_numpy(), rules.d_mutual_m
        )
        rule_meta["R8"] = cmeta

    return Instance(
        scope=scope,
        mode=mode,
        cand=cand,
        A=A,
        w=w,
        total_w=total_w,
        reach_w=base_w + float(w.sum()),
        base_w=base_w,
        n_dem_all=n_dem_all,
        build_s=time.perf_counter() - t0,
        conflict=conflict,
        existing_ids=tuple(existing["candidate_id"].astype(str)) if "candidate_id" in existing else (),
        meta={
            "label": label,
            "R_km": R_km,
            "weight": weight,
            "n_dem_reachable": int(reach.sum()),
            "n_dem_dropped_unreachable": int((~reach).sum()),
            "n_pairs": int(A.nnz),
            "dem_cells": dem_cells,
            "cand_pool": cand_pool,
            "rules": None if rules is None else {
                "d_rural_m": rules.d_rural_m,
                "d_rural_highload_m": rules.d_rural_highload_m,
                "d_mutual_m": rules.d_mutual_m,
                "require_dc": rules.require_dc,
                "assume_highload": assume_highload,
            },
            **rule_meta,
        },
    )


def _rule_network(cand, rules):
    """R2 — tách mạng được-tính-phủ (có DC) khỏi tập nâng cấp (chỉ AC).

    Đọc ``canonical/stations`` + ``connectors`` NGOÀI bundle frozen (bundle không mang
    thông tin trụ) nên pin sha256 vào meta, cùng quy ước ``demand_h3``/``load_ts``.
    """
    from ev_siting.data.evcs.paths import CONNECTORS_DIR, STATIONS_DIR
    from ev_siting.features.paths import has_dirty_coord

    st = pd.read_parquet(
        STATIONS_DIR,
        columns=["station_id", "lat", "lng", "h3_r8", "current_type", "quality_flags",
                 "is_operational", "access", "is_primary"],
    )
    # P8/E-DQ2/F4 — CÙNG bộ lọc `build_candidates._load_stations`, không tự chế biến thể.
    # R1 của BO ("ngày hoạt động không null + blockstatus mở") rơi đúng vào `is_operational`.
    st = st[st["is_operational"] & (st["access"] != "RESTRICTED") & st["is_primary"]]
    st = st[~st["quality_flags"].apply(has_dirty_coord)]
    cn = pd.read_parquet(CONNECTORS_DIR, columns=["station_id", "current_type", "power_kw"])
    st = rl.apply_r2(st, cn, rules)  # giữ trạm có ≥1 trụ DC

    exist_cells = set(cand.loc[cand["is_existing"], "h3_r8"])
    dc_cells = set(st["h3_r8"]) & exist_cells
    # Phủ tính theo Ô (đại diện đủ — đo 29/07: dedup ≤1/ô không mất phủ), nhưng KHOẢNG
    # CÁCH phải đo trên TOẠ ĐỘ THẬT của MỌI trạm DC: đại diện ô bỏ sót các trạm cùng ô,
    # và lệch điểm-thật↔tâm-ô có p50 = 353 m = 17,6% của ngưỡng 2 km.
    net = cand[cand["is_existing"] & cand["h3_r8"].isin(dc_cells)].reset_index(drop=True)
    net.attrs["real_pts"] = st[["lat", "lng"]].reset_index(drop=True)
    # Bất biến B0: trạm chỉ-AC KHÔNG bị xoá — chúng thành ứng viên NÂNG CẤP tại chỗ.
    upgrade = cand[cand["is_existing"] & ~cand["h3_r8"].isin(dc_cells)].reset_index(drop=True)
    upgrade = upgrade.assign(tier="T0U", anchor_type="ac_upgrade", is_existing=False)
    meta = {
        "R2": {
            "n_stations_dc_real": int(len(st)),
            "n_cells_existing": len(exist_cells),
            "n_cells_dc": len(dc_cells),
            "n_cells_ac_only_upgradable": int(len(upgrade)),
            "share_cells_dropped_from_S0": round(1 - len(dc_cells) / max(len(exist_cells), 1), 4),
        }
    }
    return net, upgrade, meta


def _cand_pool(cand, upgrade, pool):
    """``free`` xây mới · ``upgrade`` nâng cấp ô chỉ-AC · ``both`` hợp hai tập."""
    free = cand[~cand["is_existing"]]
    if pool == "free":
        out = free
    elif pool == "upgrade":
        out = upgrade
    elif pool == "both":
        out = pd.concat([free, upgrade], ignore_index=True)
    else:
        raise ValueError(f"cand_pool lạ: {pool}")
    return out.reset_index(drop=True)


def _apply_clearance(cand, net, rules, assume_highload):
    """R5/R6 — tiền lọc bậc một trên toạ độ THẬT. T0 grandfather, chỉ chấm ứng viên mới."""
    from ev_siting.data.evcs.paths import STATIONS_DIR
    from ev_siting.models.paths import PROJECT_ROOT

    adm_path = PROJECT_ROOT / "data" / "interim" / "vinfast_official" / "official_admin.parquet"
    st = pd.read_parquet(
        STATIONS_DIR, columns=["station_code", "official_store_id", "lat", "lng"]
    )
    lab = rl.AdminLabeller.from_stations(st, pd.read_parquet(adm_path), rules)
    is_rural, src = lab.label(cand["lat"].to_numpy(), cand["lng"].to_numpy())

    # Toạ độ THẬT của mọi trạm DC (không phải đại diện ô) — bất biến khoảng cách.
    pts = net.attrs.get("real_pts")
    net_lat, net_lng = (
        (pts["lat"].to_numpy(), pts["lng"].to_numpy())
        if pts is not None
        else (net["lat"].to_numpy(), net["lng"].to_numpy())
    )
    ok, d_near, d_req = rl.clearance_ok(
        cand["lat"].to_numpy(), cand["lng"].to_numpy(),
        net_lat, net_lng,
        is_rural, assume_highload, rules,
    )
    # Bất biến B0 — NÂNG CẤP được miễn R5/R6: trạm đã đứng ở đó, ta chỉ cộng trụ DC tại
    # chỗ chứ không mở vị trí mới. Áp luật "cách trạm hiện hữu ≥ 2 km" lên chính trạm
    # hiện hữu là đọc ngược luật. Chúng vẫn chịu R8 với các đề xuất khác.
    is_upgrade = (cand["tier"] == "T0U").to_numpy() if "tier" in cand else np.zeros(len(cand), bool)
    ok = ok | is_upgrade
    out = cand[ok].reset_index(drop=True)
    out["is_rural"] = is_rural[ok]
    out["d_nearest_net_m"] = d_near[ok]
    out["d_required_m"] = d_req[ok]
    meta = {
        "R5_R6": {
            "admin_label_source": src,
            "n_before": int(len(cand)),
            "n_after": int(len(out)),
            "n_network_pts_real": int(len(net_lat)),
            "share_survive": round(float(ok.mean()), 4),
            "share_rural": round(float(is_rural.mean()), 4),
            "assume_highload": bool(assume_highload),
            "n_upgrade_exempt": int(is_upgrade.sum()),
        }
    }
    return out, meta


# ───────────────────────────────── solver ────────────────────────────────────


def solve_mclp(inst, p, costs=None, budget=None, time_limit=DEFAULT_TIME_LIMIT_S, mip_rel_gap=0.0, eps=None):
    """Giải MCLP bằng HiGHS (qua ``scipy.optimize.milp``).

    ``costs``/``budget`` bỏ trống ⇒ ràng buộc đếm ``Σ x_i ≤ p`` (biến thể B6).
    Truyền ``costs`` (CapEx theo §10) + ``budget`` ⇒ ràng buộc ngân sách; ``p`` khi
    đó chỉ dùng để đặt tên run.
    """
    n, m = inst.n_cand, inst.n_dem
    A = inst.A

    # y_j - Σ_{i∈N_j} x_i ≤ 0  ⇔  [-Aᵀ | I] · [x; y] ≤ 0
    cov = sp.hstack([-A.T.astype(np.float64).tocsr(), sp.identity(m, format="csr", dtype=np.float64)], format="csr")
    if costs is None:
        row = sp.csr_matrix((np.ones(n), (np.zeros(n, dtype=int), np.arange(n))), shape=(1, n + m))
        rhs = float(p)
    else:
        costs = np.asarray(costs, dtype=float)
        row = sp.csr_matrix((costs, (np.zeros(n, dtype=int), np.arange(n))), shape=(1, n + m))
        rhs = float(budget)

    constraints = [
        LinearConstraint(cov, -np.inf, 0.0),
        LinearConstraint(row, -np.inf, rhs),
    ]
    if eps is not None:
        E, rhs_e, emeta = equity_rows(inst, eps)
        if E.shape[0]:
            constraints.append(LinearConstraint(E, rhs_e, np.inf))
    if inst.conflict is not None and inst.conflict.shape[0]:
        # R8 — Σ x ≤ 1 trên từng clique/cặp; chỉ đụng khối x nên pad khối y bằng 0.
        pad = sp.csr_matrix((inst.conflict.shape[0], m), dtype=np.float64)
        constraints.append(
            LinearConstraint(sp.hstack([inst.conflict, pad], format="csr"), -np.inf, 1.0)
        )
    c = np.concatenate([np.zeros(n), -inst.w])  # milp cực TIỂU hoá
    t0 = time.perf_counter()
    res = milp(
        c=c,
        integrality=np.ones(n + m),
        bounds=(0, 1),
        constraints=constraints,
        options={"time_limit": time_limit, "presolve": True, "mip_rel_gap": mip_rel_gap},
    )
    elapsed = time.perf_counter() - t0

    covered = float(-res.fun) if res.x is not None else float("nan")
    bound = float(-res.mip_dual_bound) if res.mip_dual_bound is not None else float("nan")
    chosen = inst.cand.index[np.asarray(res.x[:n]) > 0.5].to_numpy() if res.x is not None else np.array([])
    return {
        "solver": "HiGHS (scipy.optimize.milp)",
        "p": None if p is None else int(p),
        "budget": None if budget is None else float(budget),
        "status": int(res.status),
        "message": str(res.message),
        "solve_s": round(elapsed, 2),
        "n_selected": int(len(chosen)),
        "covered_w": covered,
        "dual_bound_w": bound,
        "mip_gap": None if res.mip_gap is None else float(res.mip_gap),
        "cov_at_w": _cov_ratio(inst, covered),
        "cov_at_w_reach": _cov_ratio(inst, covered, reach=True),
        "cov_at_w_bound": _cov_ratio(inst, bound),
        "hit_time_limit": elapsed >= time_limit * 0.98,
        "n_conflict_rows": 0 if inst.conflict is None else int(inst.conflict.shape[0]),
        "eps": eps,
        "n_equity_rows": 0 if eps is None else int(emeta["n_binding_rows"]),
        "_chosen": chosen,
    }


def equity_rows(inst, eps, region_res=5):
    """Sàn công bằng dạng **ε-constraint chéo vùng** (Chung–Park–Kwon 2018, eq. 6).

    Mỗi vùng *r* phải đạt tỷ lệ phủ tối thiểu ``eps``::

        base_r + Σ_{j ∈ J_r} w_j y_j  ≥  eps · W_r

    Chỉ ``|R|`` hàng, không cần dữ liệu mới, vẫn là MILP — rẻ hơn hẳn phạt-trong-mục-tiêu
    và cho ra **frontier đọc được**: mỗi ``eps`` là một điểm vận hành để lead tự chọn.

    ⚠ **Vùng = ô H3 r5 (~252 km², cỡ một huyện), KHÔNG phải đơn vị hành chính.** Nhãn
    hành chính chuyển từ trạm gần nhất chỉ đúng 66–78% ở mọi cấp (tỉnh 0,775 · huyện
    0,662 · xã 0,729) nên chưa gate được. Đây là proxy hình học tái lập được, đổi sang
    ranh giới thật khi BO cấp — chỉ đổi hàm gán nhãn, máy ε giữ nguyên.

    Cảnh báo Gazmeh 2024: tối ưu equity trên MỘT metric có thể làm TỆ metric khác, và
    thêm trạm có thể làm TĂNG bất bình đẳng đuôi. Phải đo, không được giả định — xem
    cột phân vị trong ``equity_frontier``.
    """
    reg = np.array([h3.cell_to_parent(c, region_res) for c in inst.meta["dem_cells"]])
    base = inst.meta.get("base_by_region", {})
    tot = inst.meta.get("total_by_region", {})
    uniq = sorted(set(reg) | set(tot))
    rows, cols, data, rhs = [], [], [], []
    for r, rg in enumerate(uniq):
        js = np.flatnonzero(reg == rg)
        need = eps * tot.get(rg, 0.0) - base.get(rg, 0.0)
        if need <= 0:  # vùng đã đạt sàn nhờ mạng nền -> hàng thừa, bỏ
            continue
        if js.size == 0 or inst.w[js].sum() < need:
            continue  # KHÔNG khả thi dù chọn hết -> bỏ hàng, ghi lại ở meta
        rows.extend([len(rhs)] * js.size)
        cols.extend((inst.n_cand + js).tolist())
        data.extend(inst.w[js].tolist())
        rhs.append(need)
    M = sp.csr_matrix(
        (data, (rows, cols)), shape=(len(rhs), inst.n_cand + inst.n_dem), dtype=np.float64
    )
    return M, np.array(rhs, dtype=float), {"n_regions": len(uniq), "n_binding_rows": len(rhs)}


def _cov_ratio(inst, covered_w, reach=False):
    """Tỷ lệ cầu được phủ. ``reach=False`` mẫu số = toàn lưới; ``True`` = phần candidate với tới."""
    denom = inst.reach_w if reach else inst.total_w
    if not np.isfinite(covered_w) or denom <= 0:
        return None
    return round((inst.base_w + covered_w) / denom, 6)


def greedy_mclp(inst, p, conflict_d_m=None, latlng=None):
    """Greedy tham lam có lazy-evaluation (CELF).

    Không có R8 ⇒ ràng buộc lực lượng (matroid đều) ⇒ **bảo đảm 1 − 1/e** (Nemhauser–
    Wolsey–Fisher 1978), và Feige 1998 Thm 5.3 nói không thuật toán đa thức nào vượt
    được trần đó trừ khi P = NP.

    Có R8 ⇒ tập khả thi thành **independence system** tổng quát, **bảo đảm 1 − 1/e
    KHÔNG còn đúng**, và gap greedy↔exact 0,00–0,32% đo ở B6 KHÔNG còn áp dụng. Ở chế
    độ đó hàm chỉ trả nghiệm khả thi; số bảo hành phải **đo lại** bằng cách so với MILP,
    xem ``bench(rules=...)``.
    """
    import heapq

    A, w = inst.A, inst.w
    indptr, indices = A.indptr, A.indices
    covered = np.zeros(inst.n_dem, dtype=bool)

    blocked = np.zeros(inst.n_cand, dtype=bool)
    ctree = None
    if conflict_d_m:
        if latlng is None:
            latlng = inst.cand[["lat", "lng"]].to_numpy(float)
        ctree = BallTree(np.radians(latlng), metric="haversine")

    t0 = time.perf_counter()
    heap = []
    for i in range(inst.n_cand):
        g = float(w[indices[indptr[i] : indptr[i + 1]]].sum())
        if g > 0:
            heap.append((-g, i, 0))
    heapq.heapify(heap)

    chosen, total, evals = [], 0.0, inst.n_cand
    for step in range(1, p + 1):
        while heap:
            negg, i, stamp = heapq.heappop(heap)
            if blocked[i]:  # R8 — bị một điểm đã chọn loại khỏi tập khả thi
                continue
            js = indices[indptr[i] : indptr[i + 1]]
            if stamp == step:  # đã tính lại ở vòng này ⇒ đúng là argmax
                gain = -negg
                break
            gain = float(w[js[~covered[js]]].sum())
            evals += 1
            if not heap or gain >= -heap[0][0]:
                break
            heapq.heappush(heap, (-gain, i, step))
        else:
            break
        if gain <= 0:
            break
        covered[js] = True
        chosen.append(i)
        total += gain
        if ctree is not None:
            blocked[ctree.query_radius(np.radians(latlng[i : i + 1]), r=conflict_d_m / rl.R_EARTH_M)[0]] = True

    return {
        "solver": "greedy (CELF, 1−1/e)" if not conflict_d_m else "greedy (CELF, KHÔNG bảo hành — R8)",
        "p": int(p),
        "solve_s": round(time.perf_counter() - t0, 2),
        "n_selected": len(chosen),
        "n_gain_evals": evals,
        "covered_w": total,
        "cov_at_w": _cov_ratio(inst, total),
        "cov_at_w_reach": _cov_ratio(inst, total, reach=True),
        "_chosen": inst.cand.index[chosen].to_numpy(),
    }


# ────────────────────────────────── B6 bench ─────────────────────────────────


def _verdict(r: dict) -> str:
    """Phán quyết B6 cho một lần chạy: chỉ ba khả năng, không có 'gần đúng'."""
    if r["status"] == 0 and (r["mip_gap"] or 0.0) <= 0.0:
        return "OPTIMAL"
    gap = r["mip_gap"]
    if gap is not None and gap <= SOLVED_GAP:
        return f"NEAR_OPTIMAL (gap {gap:.4%} ≤ {SOLVED_GAP:.0%})"
    return "NOT_SOLVED"


def bench(scopes=("vietnam",), modes=("brownfield", "greenfield"), ps=(20, 100, 800), time_limit=DEFAULT_TIME_LIMIT_S):
    """Bấm giờ solver thật — trả lời B6: *giải được hay phải phân rã?*"""
    ensure_dirs()
    runs, out = [], MCLP_DIR / "mclp_bench.json"
    for scope in scopes:
        for mode in modes:
            inst = load_instance(scope=scope, mode=mode)
            print(
                f"\n[bench] {scope}/{mode}: {inst.n_cand} candidate × {inst.n_dem} ô cầu "
                f"({inst.meta['n_pairs']:,} cặp phủ) — dựng {inst.build_s:.1f}s"
                f" · nền T0 cov@pop={inst.base_w / inst.total_w:.4f}"
            )
            for p in ps:
                g = greedy_mclp(inst, p)
                r = solve_mclp(inst, p, time_limit=time_limit)
                r["greedy"] = {k: v for k, v in g.items() if not k.startswith("_")}
                r["greedy_ratio_vs_milp"] = (
                    round(g["covered_w"] / r["covered_w"], 6)
                    if r["covered_w"] and np.isfinite(r["covered_w"])
                    else None
                )
                rec = {
                    "scope": scope,
                    "mode": mode,
                    "n_candidates": inst.n_cand,
                    "n_demand_cells": inst.n_dem,
                    "n_demand_cells_total": inst.n_dem_all,
                    "n_coverage_pairs": inst.meta["n_pairs"],
                    "build_s": round(inst.build_s, 2),
                    "base_cov_at_pop": round(inst.base_w / inst.total_w, 6),
                    "reach_cov_at_pop": round(inst.reach_w / inst.total_w, 6),
                    **{k: v for k, v in r.items() if not k.startswith("_")},
                    # Verdict B6: "giải được" = tối ưu chứng minh được, HOẶC chạm trần
                    # thời gian nhưng gap còn lại đã dưới ngưỡng công bố.
                    "verdict": _verdict(r),
                }
                runs.append(rec)
                print(
                    f"  p={p:<4} MILP {r['solve_s']:>8.1f}s  status={r['status']} "
                    f"gap={r['mip_gap']}  cov@pop={r['cov_at_w']}  |  "
                    f"greedy {g['solve_s']:>6.1f}s cov@pop={g['cov_at_w']} "
                    f"(={r['greedy_ratio_vs_milp']} × MILP)"
                )
                out.write_text(json.dumps({"runs": runs}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[bench] -> {out}")
    return runs


def run(argv=None):
    ap = argparse.ArgumentParser(description="MCLP solver + bench bấm giờ (B6)")
    ap.add_argument("--scope", default="vietnam", help="hanoi | vietnam")
    ap.add_argument("--mode", default="brownfield", choices=("brownfield", "greenfield"))
    ap.add_argument("--p", type=int, default=20)
    ap.add_argument("--label", default=DEFAULT_FREEZE_LABEL)
    ap.add_argument("--time-limit", type=float, default=DEFAULT_TIME_LIMIT_S)
    ap.add_argument("--bench", action="store_true", help="chạy bộ B6: p ∈ {20,100,800} × 2 chế độ")
    a = ap.parse_args(argv)

    if a.bench:
        bench(scopes=(a.scope,), time_limit=a.time_limit)
        return
    inst = load_instance(scope=a.scope, mode=a.mode, label=a.label)
    print(f"[mclp] {inst.n_cand} candidate × {inst.n_dem} ô cầu · dựng {inst.build_s:.1f}s")
    r = solve_mclp(inst, a.p, time_limit=a.time_limit)
    print(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
