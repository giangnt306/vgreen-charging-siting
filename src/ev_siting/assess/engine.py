"""Engine assess() v0 — score, gates, tier, reasons đóng băng theo pre-reg §1–§4.

Kiến trúc hai tầng có chủ ý:

- ``make_context`` gánh TOÀN BỘ I/O nặng (verify bundle, demand 268k ô, telemetry
  F19, dựng lớp tham chiếu) đúng một lần — đây là phần "warm cache" của Done B3;
- ``assess`` sau đó thuần tính toán trên mảng, chấm một điểm dưới 1 giây và cả lô
  T1 không phải chạm đĩa lần nào ngoài dòng log bắt buộc.

Test dựng ``AssessContext`` thủ công từ frame synthetic — vì vậy engine chỉ được
phép đọc context qua thuộc tính đã khai trong dataclass, không lén mở file.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import h3
import numpy as np
import pandas as pd

from ev_siting.aoi import haversine_km
from ev_siting.assess import credit, kernel, occupancy, params, paths, reference
from ev_siting.features.read_frozen import FrozenBundle, load_frozen

#: Cặp cờ kích hoạt R11 khi xuất hiện ĐỒNG THỜI — khớp hợp đồng candidate-sites §10
#: (một cờ đơn lẻ chỉ là phạt mềm F14, không thành nghĩa vụ khảo sát).
_SURVEY_FLAGS = frozenset({"NO_ROAD_ACCESS", "NOT_BUILT_UP"})

#: Thứ tự cột output ĐÓNG BĂNG — downstream (report T1, CLI CSV) đọc theo tên,
#: nhưng giữ thứ tự cố định để diff giữa hai lần chạy đọc được bằng mắt.
_OUT_COLS = [
    "point_id", "lat", "lng", "tier", "score_total", "score_N", "score_V",
    "n_marginal_pop", "n_marginal_pop_solo", "n_marginal_pop_last_in", "n_marginal_pop_shapley",
    "n_redundancy", "v_demand_local", "v_competition", "v_pressure",
    "occ_local", "d_nearest_m", "gates_fired", "reasons",
    "mode", "credit_rule", "data_version", "model_version", "calibration", "vault_tos_restricted",
]  # fmt: skip


@dataclass(eq=False)
class AssessContext:
    """Mọi thứ assess() cần, đã load + verify sẵn — object dùng một lần theo mode."""

    bundle: FrozenBundle  # test được phép thay bằng SimpleNamespace có .aoi["bbox"]
    dem: pd.Series  # h3_r8 -> pop
    net: kernel.NetworkContext
    ref: pd.DataFrame  # 4 phân bố tham chiếu (reference.REF_COLS)
    occ: pd.DataFrame  # per-trạm F19 đã join station_id + num_connectors
    credit_rule: str
    mode: str
    cand_by_cell: pd.DataFrame  # index h3_r8 -> penalty_flags, tier (cho R11)
    demand_sha256: str = ""  # pin provenance demand_h3 (pre-reg §0) — report T1 đọc từ đây


def make_context(
    mode: str = "live",
    exclude_station_ids=(),
    credit_rule: str = params.DEFAULT_CREDIT_RULE,
    scope: str = params.SCOPE,
    label: str = params.FREEZE_LABEL,
    processed_dir: Path | None = None,
) -> AssessContext:
    """Dựng context từ dữ liệu thật: bundle frozen (verify hash) + demand + F19 + reference.

    ``mode="retrodiction"`` mà exclude rỗng bị chặn bằng ValueError: retrodiction
    đúng nghĩa BẮT BUỘC purge cả wave NEW khỏi nền (pre-reg §2) — chạy "retro" trên
    nền còn nguyên trạm mới chính là leakage T1, phải nổ sớm chứ không cho số đẹp giả.
    """
    if mode not in ("live", "retrodiction"):
        raise ValueError(f"mode không hợp lệ: {mode!r} — phải là 'live' hoặc 'retrodiction'")
    if credit_rule not in params.CREDIT_RULES:
        raise ValueError(f"credit_rule không hợp lệ: {credit_rule!r} — phải thuộc {params.CREDIT_RULES}")
    exclude = tuple(exclude_station_ids)
    if mode == "retrodiction" and not exclude:
        raise ValueError("retrodiction bắt buộc có exclude_station_ids (purge wave NEW) — chống chạy nhầm leakage")

    bundle = load_frozen(scope, label=label, processed_dir=processed_dir)
    dem = kernel.demand_series(pd.read_parquet(paths.DEMAND_H3))
    net = kernel.build_network(bundle.covered0, exclude, mode=mode)
    # Adversarial 28/07 (P1): exclude "có phần tử" chưa đủ — phải KHỚP thật. File NEW sai
    # format/sai wave cho n_excluded=0 và T1 sẽ chạy trên nền còn nguyên wave (leakage câm).
    if mode == "retrodiction" and net.n_excluded == 0:
        raise SystemExit(
            "ASSESS FAIL: retrodiction exclude không khớp station_id nào trong covered0 — "
            "kiểm lại file new_supply / quy tắc map mã (params.station_id_from_code)"
        )

    # Telemetry keyed theo station_code (C.AC000067) còn covered0 theo station_id
    # (vn-c-ac000067). Map lower+'.'→'-' KHÔNG đơn ánh trên lý thuyết (mã có cả dấu
    # chấm lẫn gạch) — va chạm nghĩa là hai trạm telemetry trộn vào một id, mọi
    # occ_local sau đó vô nghĩa ⇒ chặn cứng thay vì đoán.
    occ = occupancy.load_occupancy()
    occ = occ.assign(station_id=occ["station_code"].map(params.station_id_from_code))
    dup = occ["station_id"].duplicated(keep=False)
    if dup.any():
        codes = sorted(occ.loc[dup, "station_code"].tolist())[:10]
        raise SystemExit(f"ASSESS FAIL: map station_code->station_id va chạm ({int(dup.sum())} dòng, vd {codes})")
    occ = occ.merge(bundle.covered0[["station_id", "num_connectors"]], on="station_id", how="inner")

    # Tag cache tham chiếu mã hoá context: label + scope + exclude — đổi bundle hay đổi
    # danh sách purge là đổi file cache (hash danh sách đã sort để thứ tự không đổi tag).
    # Tag chỉ là TÊN; ruột còn được reference so vân tay nội dung qua meta sidecar.
    base = f"{label}--{scope}"
    if exclude:
        digest = hashlib.sha256("\n".join(sorted(exclude)).encode("utf-8")).hexdigest()[:8]
        tag = f"{base}--" + ("retro-" if mode == "retrodiction" else "live-") + digest
    else:
        tag = f"{base}--live"
    ref = reference.build_reference(bundle.candidates[["candidate_id", "h3_r8", "lat", "lng"]], net, dem, tag=tag)

    # R11 tra theo ô: candidate frozen đã dedup 1 điểm/ô, nhưng vẫn khử trùng lặp
    # phòng thủ — .loc trên index trùng trả DataFrame và làm gãy render reason.
    cand_by_cell = bundle.candidates.set_index("h3_r8")[["penalty_flags", "tier"]]
    cand_by_cell = cand_by_cell[~cand_by_cell.index.duplicated(keep="first")]

    return AssessContext(
        bundle=bundle, dem=dem, net=net, ref=ref, occ=occ,
        credit_rule=credit_rule, mode=mode, cand_by_cell=cand_by_cell,
        demand_sha256=_sha256_file(paths.DEMAND_H3),
    )  # fmt: skip


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _flags_set(value) -> frozenset:
    """penalty_flags của một ô -> set cờ; None/NaN = không cờ (round-trip parquet),
    str đơn không được để lọt vào iterate — sẽ thành duyệt từng ký tự (bug câm)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return frozenset()
    if isinstance(value, str):
        return frozenset({value}) if value else frozenset()
    return frozenset(str(f) for f in value)


def _reason(code: str, **facts) -> str:
    """Render một reason từ template đóng băng, prefix code để grep/test đối chiếu pre-reg."""
    return f"{code}: {params.REASONS[code].format(**facts)}"


def _jsonable(v):
    # NaN/inf không phải JSON hợp lệ; log là hợp đồng đọc-bằng-máy nên ép về null tường minh.
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if isinstance(v, (np.floating, np.integer)):
        return _jsonable(float(v)) if isinstance(v, np.floating) else int(v)
    return v


def assess(
    points: pd.DataFrame,
    actx: AssessContext,
    plan: bool | None = None,
    log_path: Path | None = None,
    redact_coords_in_log: bool = False,
) -> pd.DataFrame:
    """Chấm một tập điểm (lat, lng[, point_id]) — chấm-1-điểm là trường hợp |P|=1.

    ``plan`` mặc định None = tự suy theo pre-reg §1: |P|>1 là MỘT kế hoạch (chia công
    theo credit_rule của context + G3 trùng-lô). Caller coi các dòng là hồ sơ ĐỘC LẬP
    (T1 §5, batch CSV pilot) phải truyền ``plan=False`` tường minh — Addendum 28/07.

    ``redact_coords_in_log=True`` lược lat/lng khỏi dòng log JSONL — bắt buộc khi lô
    điểm là toạ độ vault (GT T1): log cũng là output, Vault-ToS §0 áp cả ở đó.
    """
    pts = points.reset_index(drop=True).copy()
    if "point_id" not in pts.columns:
        pts["point_id"] = [f"p{i}" for i in range(len(pts))]
    # point_id ép str NGAY từ biên: một pd.Timestamp lọt vào json.dumps giữa vòng ghi log
    # sẽ nổ nửa chừng — mất vết của cả lô (vi phạm bất biến §4.5).
    pts["point_id"] = pts["point_id"].astype(str)
    n = len(pts)
    if plan is None:
        plan = n > 1
    lats = pd.to_numeric(pts["lat"], errors="coerce").to_numpy(dtype=float)
    lngs = pd.to_numeric(pts["lng"], errors="coerce").to_numpy(dtype=float)

    # ---- G1: dữ liệu — toạ độ hợp lệ, trong bbox AOI, có giao với lưới cầu ----
    # bbox bundle theo quy ước aoi.to_dict: [lat_min, lng_min, lat_max, lng_max].
    s, w, no, e = (float(v) for v in actx.bundle.aoi["bbox"])
    ok = (
        ~np.isnan(lats) & ~np.isnan(lngs)
        & (np.abs(lats) <= 90.0) & (np.abs(lngs) <= 180.0)
        & (lats >= s) & (lats <= no) & (lngs >= w) & (lngs <= e)
    )  # fmt: skip
    dem_cells = frozenset(actx.dem.index)
    cells_list: list[frozenset[str] | None] = [None] * n
    for i in np.flatnonzero(ok):
        cov = kernel.point_cells(lats[i], lngs[i], actx.net.r_km)
        if cov & dem_cells:
            cells_list[i] = cov
        else:
            ok[i] = False  # trong bbox nhưng ngoài lưới cầu — vẫn là G1, không phải điểm 0

    # ---- Feature vector hoá cho các điểm qua G1 ----
    nan = np.full(n, np.nan)
    marginal, local, redundancy = nan.copy(), nan.copy(), nan.copy()
    m_solo, m_last, m_shap = nan.copy(), nan.copy(), nan.copy()
    comp, pressure, occ_local, d_nearest, rho = nan.copy(), nan.copy(), nan.copy(), nan.copy(), nan.copy()
    p_dem, p_comp = nan.copy(), nan.copy()

    rule = actx.credit_rule if plan else "solo"  # rule HIỆU LỰC — đóng dấu vào output, không phải rule cấu hình
    ok_idx = np.flatnonzero(ok)
    if len(ok_idx):
        cells_ok = [cells_list[i] for i in ok_idx]
        pop = actx.dem.get  # Series.get: tra O(1) từng ô, không quét 268k index mỗi điểm
        local[ok_idx] = [sum(pop(c, 0.0) for c in cov) for cov in cells_ok]
        # plan=False ≡ rule "solo" (mỗi điểm độc lập vs nền) — dùng CHUNG credit.split_marginal
        # để hai đường không bao giờ lệch nhau về định nghĩa biên. Pre-reg §1: |P|>1 tính đủ
        # CẢ BA rule (người duyệt thấy khoảng kẹp [last_in, shapley, solo]); score dùng `rule`.
        m_solo[ok_idx] = credit.split_marginal(cells_ok, actx.net.covered_cells, actx.dem, "solo")
        if plan and len(ok_idx) > 1:
            m_last[ok_idx] = credit.split_marginal(cells_ok, actx.net.covered_cells, actx.dem, "last_in")
            m_shap[ok_idx] = credit.split_marginal(cells_ok, actx.net.covered_cells, actx.dem, "shapley")
        else:
            m_last[ok_idx] = m_solo[ok_idx]  # |P|=1 / độc lập: ba rule trùng nhau theo định nghĩa
            m_shap[ok_idx] = m_solo[ok_idx]
        marginal = {"solo": m_solo, "last_in": m_last, "shapley": m_shap}[rule].copy()
        # n_redundancy đo "% dân trong catchment đã được N phủ" (§3 #2) — LUÔN từ solo vs nền:
        # trừ phần chia công nội lô vào đây là phát biểu fact sai về mạng (adversarial C7).
        with np.errstate(divide="ignore", invalid="ignore"):
            redundancy[ok_idx] = np.where(local[ok_idx] > 0, 1.0 - m_solo[ok_idx] / local[ok_idx], np.nan)

        info = kernel.nearest_info(actx.net, lats[ok_idx], lngs[ok_idx], r_km=actx.net.r_km)
        d_nearest[ok_idx] = info["d_nearest_m"]
        comp[ok_idx] = info["n_within_comp"].astype(float)
        rho[ok_idx] = local[ok_idx] / (1.0 + info["connectors_within_r"])
        # v_pressure là percentile NGAY TẠI ĐÂY (pre-reg §3 #5) — vào score_V nguyên
        # trạng, tuyệt đối không pctl thêm lần nữa ở tầng score.
        pressure[ok_idx] = reference.pctl(actx.ref["rho"], rho[ok_idx])

        # occ_local (enrichment, KHÔNG vào score): trạm N trong R có telemetry đạt sàn.
        # Trạm 0-cổng bị loại (util không định nghĩa — 46 trạm covered0 như vậy có telemetry);
        # util clip 1.0: snapshot n_cars có thể vượt num_connectors (đo được tới 1,60 — xe xếp
        # hàng/đếm lệch), in "bận 160%" trước mặt BO là tự bắn vào chân (Addendum 28/07).
        occ_ok = actx.occ[
            (actx.occ["duration_coverage"] >= params.OCC_COVERAGE_FLOOR) & (actx.occ["num_connectors"] > 0)
        ]
        util = pd.Series(
            np.clip((occ_ok["occ_mean_dw"] / occ_ok["num_connectors"]).to_numpy(), 0.0, 1.0),
            index=occ_ok["station_id"].to_numpy(),
        )
        sids = actx.net.stations["station_id"].to_numpy()
        for j, i in enumerate(ok_idx):
            near = util.reindex(sids[info["idx_within_r"][j]])
            occ_local[i] = float(near.mean())  # mean bỏ NaN; không trạm đạt sàn ⇒ NaN

        p_dem[ok_idx] = reference.pctl(actx.ref["v_demand_local"], local[ok_idx])
        p_comp[ok_idx] = reference.pctl(actx.ref["v_competition"], comp[ok_idx])

    # ---- Score (§4): N một thành phần, V trung bình 3 thành phần bỏ NaN + renormalize ----
    score_n = reference.pctl(actx.ref["n_marginal_pop"], marginal)
    v_parts = np.vstack([p_dem, 100.0 - p_comp, pressure])
    n_v = np.sum(~np.isnan(v_parts), axis=0)
    with np.errstate(invalid="ignore"):
        score_v = np.where(n_v > 0, np.nansum(v_parts, axis=0) / np.maximum(n_v, 1), np.nan)
    score_total = 0.5 * score_n + 0.5 * score_v  # score_V NaN ⇒ total NaN (không đoán nửa còn lại)

    # ---- G2 trùng hiện hữu + G3 trùng lô (chỉ plan) — chặn TRẦN tier, không chấm lại score ----
    g2 = ok & (d_nearest <= params.NEAR_EXISTING_M)
    g3 = np.zeros(n, dtype=bool)
    d_batch = np.full(n, np.nan)
    if plan:
        # Điểm VÀO SAU bị cờ (thứ tự dòng = thứ tự "nộp hồ sơ" mô phỏng): so với mọi
        # điểm hợp lệ đứng trước, lấy khoảng cách gần nhất làm con số fact của R02.
        for pos in range(1, len(ok_idx)):
            i = ok_idx[pos]
            prev = ok_idx[:pos]
            d_m = haversine_km(lats[i], lngs[i], lats[prev], lngs[prev]) * 1000.0
            d_min = float(np.min(d_m))
            if d_min <= params.BATCH_CONFLICT_M:
                g3[i], d_batch[i] = True, d_min
    capped = g2 | g3

    # ---- Tier (§4): cap chỉ chặn Đồng ý; Từ chối đòi G1 sạch + đủ cả 3 thành phần V ----
    accept = ok & ~capped & (score_total >= params.THRESH_ACCEPT)
    reject = ok & (score_total < params.THRESH_REJECT) & (n_v == 3)
    tier = np.where(accept, params.TIER_ACCEPT, np.where(reject, params.TIER_REJECT, params.TIER_REVIEW))

    # ---- Reasons: render từ template frozen, mỗi reason kèm con số fact ----
    gates_col: list[list[str]] = []
    reasons_col: list[list[str]] = []
    for i in range(n):
        gates: list[str] = []
        rs: list[str] = []
        if not ok[i]:
            gates.append("G1")
            rs.append(_reason("R03_NO_DATA"))
        else:
            if g2[i]:
                gates.append("G2")
                rs.append(_reason("R01_NEAR_EXISTING", d_nearest_m=d_nearest[i], near_m=params.NEAR_EXISTING_M))
            if g3[i]:
                gates.append("G3")
                rs.append(_reason("R02_BATCH_CONFLICT_SIM", d_batch_m=d_batch[i]))
            if score_n[i] < 30.0:
                # Catchment 0 dân ⇒ mẫu redundancy không tồn tại — vẫn phải nói fact
                # (biến thể ALT), không được im lặng nuốt reason (adversarial C5/C21).
                if not np.isnan(redundancy[i]):
                    rs.append(
                        _reason("R04_LOW_MARGINAL", n_redundancy_pct=redundancy[i] * 100.0, r_km=params.R_SERVICE_KM)
                    )
                else:
                    rs.append(_reason("R04_LOW_MARGINAL_ALT", n_marginal_pop=marginal[i], r_km=params.R_SERVICE_KM))
            if score_n[i] >= 60.0:
                rs.append(
                    _reason(
                        "R05_HIGH_MARGINAL",
                        n_marginal_pop=marginal[i], r_km=params.R_SERVICE_KM, pctl_inv=100.0 - score_n[i],
                    )
                )  # fmt: skip
            if p_dem[i] < 30.0:
                rs.append(_reason("R06_LOW_LOCAL_DEMAND", v_demand_local=local[i], r_km=params.R_SERVICE_KM))
            if p_comp[i] >= 90.0:
                rs.append(_reason("R07_HIGH_COMPETITION", v_competition=comp[i], comp_km=params.COMPETITION_RADIUS_KM))
            if pressure[i] >= 60.0:
                rs.append(_reason("R08_PRESSURE_HIGH", pctl_inv=100.0 - pressure[i]))
            if occ_local[i] >= params.OCC_HIGH_BAND:
                rs.append(_reason("R09_OCC_NEARBY_HIGH", occ_local_pct=occ_local[i] * 100.0))
            if comp[i] == 0:
                rs.append(_reason("R10_NO_SUPPLY_1KM", comp_km=params.COMPETITION_RADIUS_KM))
            cell = h3.latlng_to_cell(lats[i], lngs[i], 8)
            if cell in actx.cand_by_cell.index:
                row = actx.cand_by_cell.loc[cell]
                fset = _flags_set(row["penalty_flags"])
                if row["tier"] == "T4" or _SURVEY_FLAGS <= fset:
                    # In cờ theo thứ tự hợp đồng, nối "+"; ô T4 không cờ in "tier=T4"
                    # để reason vẫn mang fact chứ không rỗng.
                    ordered = [f for f in ("NO_ROAD_ACCESS", "NOT_BUILT_UP") if f in fset]
                    ordered += sorted(fset - set(ordered))
                    rs.append(_reason("R11_LAND_SURVEY", flags="+".join(ordered) if ordered else "tier=T4"))
        # Bất biến hợp đồng BO: "Từ chối" KHÔNG BAO GIỜ trắng lý do (adversarial C13) —
        # điểm rơi vào khe không kích hoạt reason nào vẫn phải nghe được con số fact.
        if tier[i] == params.TIER_REJECT and not rs:
            rs.append(_reason("R12_LOW_TOTAL", score_total=score_total[i], thresh=params.THRESH_REJECT))
        gates_col.append(gates)
        reasons_col.append(rs)

    out = pd.DataFrame(
        {
            "point_id": pts["point_id"].to_numpy(),
            "lat": lats, "lng": lngs, "tier": tier,
            "score_total": score_total, "score_N": score_n, "score_V": score_v,
            "n_marginal_pop": marginal,
            "n_marginal_pop_solo": m_solo, "n_marginal_pop_last_in": m_last, "n_marginal_pop_shapley": m_shap,
            "n_redundancy": redundancy,
            "v_demand_local": local, "v_competition": comp, "v_pressure": pressure,
            "occ_local": occ_local, "d_nearest_m": d_nearest,
            "gates_fired": gates_col, "reasons": reasons_col,
            # `rule` là rule HIỆU LỰC (solo khi các điểm độc lập) — nhãn phải nói đúng
            # cách con số được tính, không phải rule cấu hình trong context (C16).
            "mode": actx.mode, "credit_rule": rule,
            "data_version": params.DATA_VERSION, "model_version": params.MODEL_VERSION,
            "calibration": params.CALIBRATION_LABEL, "vault_tos_restricted": True,
        }
    )[_OUT_COLS]  # fmt: skip

    _append_log(out, plan=plan, log_path=log_path, redact_coords=redact_coords_in_log)
    return out


def _append_log(out: pd.DataFrame, plan: bool, log_path: Path | None, redact_coords: bool = False):
    """Append JSONL mỗi điểm một dòng — bất biến backlog §4.5: MỌI lần chấm để lại vết.

    ``redact_coords=True``: lược lat/lng khỏi từng dòng — log là artefact bền trên đĩa,
    lô điểm vault (GT T1) mà ghi toạ độ vào đây là rò Vault-ToS §0 qua cửa sau.
    """
    if log_path is None:
        paths.ensure_dirs()
        log_path = paths.LOG_PATH
    else:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid.uuid4())  # chung cho cả lô — truy ngược "các điểm này chấm cùng nhau"
    assessed_at = datetime.now(timezone.utc).isoformat()
    with open(log_path, "a", encoding="utf-8") as f:
        for row in out.to_dict("records"):
            rec = {"run_id": run_id, "assessed_at": assessed_at, "plan": plan, "coords_redacted": redact_coords}
            rec.update({k: _jsonable(v) for k, v in row.items() if not (redact_coords and k in ("lat", "lng"))})
            # default=str: một giá trị lạ không được phép giết nửa cuối lô log (C14).
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
