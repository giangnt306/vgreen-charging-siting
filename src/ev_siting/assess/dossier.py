"""Hồ sơ thẩm định vị trí — deliverable v1, thay cho "máy chấm điểm" v0.

Vì sao đổi (postmortem + review lead 2026-07-28):

- BO mô tả nỗi đau là *"người đánh giá phải tự tổng hợp 30–60 phút/hồ sơ"*. Đó là xin
  **báo cáo tự động**, không xin một con số 67/100 — và một con số không kiểm được chính
  là cách nhóm trước chết (kịch bản A: hứa số tuyệt đối).
- T1 đã chứng minh score v0 không phân biệt được (AUC 0,452), và trần của toàn bộ dữ liệu
  mở là 0,698 — không đủ biên để bán một điểm số. Nhưng **facts thì luôn đúng**: chúng
  thuộc thang phát biểu loại 1, sai là bug data, tìm được và sửa được.

Nên v1 **không xuất `score_total`, không có tier "Từ chối"**. Chỉ hai kết luận:
``Đủ điều kiện xem xét`` / ``Cần khảo sát`` — và mọi kết luận đều kèm con số.

Phần có tín hiệu thật được giữ lại và đưa lên: **định cỡ** (`sizing.py`). Đo được
2026-07-28: proxy cầu ↔ utilization rho **+0,375 với DC** nhưng **−0,031 với AC**
(Simpson's paradox — gộp lại chỉ còn +0,064). Nghĩa là câu hỏi *"đặt loại trụ nào ở đây"*
có bằng chứng, còn câu hỏi *"chỗ này tốt hay xấu"* thì chưa.

Chạy: uv run python -m ev_siting.assess.cli dossier --in points.csv --out-dir outputs/assess/dossier
"""

from __future__ import annotations

from dataclasses import dataclass

import h3
import numpy as np
import pandas as pd

from ev_siting.assess import engine, kernel, params, paths, sizing

MODEL_VERSION = "assess-v1.0.0-dossier"

VERDICT_OK = "Đủ điều kiện xem xét"
VERDICT_SURVEY = "Cần khảo sát"

#: Cờ buộc chuyển sang "Cần khảo sát". KHÔNG có cờ nào dẫn tới "Từ chối" — bất biến
#: backlog §4.2: không bao giờ tự từ chối, thiếu dữ liệu chỉ làm tăng mức rà soát.
_SURVEY_GATES = ("G1", "G2", "G3")

#: Trùng phủ hoàn toàn: 100% dân trong bán kính phục vụ ĐÃ được mạng hiện hữu phủ, và có
#: trạm trong CHÍNH bán kính đó. Đây là fact (không phải điểm số) và là đúng ca cần người
#: xem kỹ — rủi ro ăn vào doanh thu trạm NPP đã đầu tư gần đó (yêu cầu BO "bảo đảm quyền
#: lợi NPP").
#:
#: Điều kiện thứ hai từng là "có trạm ≤1 km". B8 đo 29/07 trên 600 candidate ngẫu nhiên:
#: 363 điểm (60,5%) trùng phủ 100%, nhưng 35 trong số đó không có trạm nào ≤1 km ⇒ R13 im
#: — dù **33/35 vẫn có trạm trong bán kính phục vụ** (trung vị 4 trạm/điểm). Kết quả:
#: 18/600 = **3,0%** hồ sơ ra "Đủ điều kiện xem xét" ở đúng ca cạnh tranh nội bộ. Nới sang
#: bán kính phục vụ đóng lỗ đó và đi theo chiều bảo thủ (thêm rà soát, không thêm từ chối
#: — bất biến §4.2).
FULL_OVERLAP_REDUNDANCY = 1.0


@dataclass
class DossierContext:
    actx: engine.AssessContext
    bench: pd.DataFrame
    bench_meta: dict


def build_context(mode: str = "live", **kw) -> DossierContext:
    import json

    actx = engine.make_context(mode=mode, **kw)
    return DossierContext(
        actx=actx,
        bench=sizing.load_benchmark(),
        bench_meta=json.loads(sizing.BENCH_META.read_text(encoding="utf-8")),
    )


def _network_facts(lat: float, lng: float, actx: engine.AssessContext) -> dict:
    """Đếm mạng hiện hữu quanh điểm — phần người duyệt đang phải tự tra tay."""
    st = actx.net.stations
    info = kernel.nearest_info(actx.net, np.array([lat]), np.array([lng]), r_km=actx.net.r_km)
    idx = info["idx_within_r"][0]
    # NetworkContext.stations chỉ giữ cột kernel cần; loại trụ/đơn vị vận hành lấy từ
    # bundle frozen theo station_id — không nhồi thêm cột vào kernel chỉ để in báo cáo.
    sids = st["station_id"].to_numpy()[idx] if len(idx) else np.array([], dtype=object)
    near = actx.bundle.covered0.set_index("station_id").reindex(sids)
    d1 = float(info["d_nearest_m"][0])
    return {
        "d_nearest_m": d1 if np.isfinite(d1) else None,
        "n_within_1km": int(info["n_within_comp"][0]),
        "n_within_r": int(len(near)),
        "connectors_within_r": int(info["connectors_within_r"][0]),
        "n_dc_within_r": int((near["current_type"] == "DC").sum()) if len(near) else 0,
        "operators_within_r": sorted(near["operator"].dropna().unique().tolist()) if len(near) else [],
    }


def _demand_facts(lat: float, lng: float, actx: engine.AssessContext) -> dict:
    cov = kernel.point_cells(lat, lng, actx.net.r_km)
    cell = h3.latlng_to_cell(lat, lng, 8)
    dem_full = pd.read_parquet(paths.DEMAND_H3).set_index("h3_r8")
    row = dem_full.reindex([cell]).iloc[0]
    inside = dem_full.index.isin(cov)
    return {
        "h3_r8": cell,
        "pop_catchment": float(dem_full.loc[inside, "pop"].sum()),
        "pop_cell": float(row.get("pop", np.nan)),
        "road_len_m_cell": float(row.get("road_len_m", np.nan)),
        "n_poi_cell": int(row["n_poi"]) if pd.notna(row.get("n_poi")) else None,
        "n_fuel_cell": int(row["n_fuel"]) if pd.notna(row.get("n_fuel")) else None,
        "n_parking_cell": int(row["n_parking"]) if pd.notna(row.get("n_parking")) else None,
        "in_demand_grid": bool(cell in dem_full.index),
    }


def make_dossier(lat: float, lng: float, dctx: DossierContext, point_id: str = "HS-0001") -> dict:
    """Một hồ sơ = facts + kết luận 2 mức. Không có score, không có 'Từ chối'."""
    scored = engine.assess(pd.DataFrame([{"point_id": point_id, "lat": lat, "lng": lng}]), dctx.actx, plan=False).iloc[
        0
    ]

    net = _network_facts(lat, lng, dctx.actx)
    dem = _demand_facts(lat, lng, dctx.actx)
    size = sizing.suggest(dem["pop_cell"] if pd.notna(dem["pop_cell"]) else 0.0, dctx.bench, dctx.bench_meta)

    gates = list(scored["gates_fired"])
    verdict = VERDICT_SURVEY if any(g in _SURVEY_GATES for g in gates) else VERDICT_OK
    # R12 là reason của score_total — v1 không có điểm số nên cũng không có reason của nó.
    reasons = [r for r in scored["reasons"] if not r.startswith("R12")]
    # Cờ khảo sát đất (R11) đẩy sang "Cần khảo sát" — hợp đồng candidate-sites §10.
    if any(r.startswith("R11") for r in reasons):
        verdict = VERDICT_SURVEY

    red = scored["n_redundancy"]
    if pd.notna(red) and red >= FULL_OVERLAP_REDUNDANCY and net["n_within_r"] >= 1:
        verdict = VERDICT_SURVEY
        reasons.append(
            f"R13_FULL_OVERLAP: 100% dân trong {dctx.actx.net.r_km:.0f} km đã được mạng hiện hữu phủ "
            f"({net['n_within_r']} trạm trong bán kính, {net['n_within_1km']} trong 1 km, "
            f"gần nhất {net['d_nearest_m']:.0f} m) — "
            "kiểm tra tác động doanh thu lên trạm hiện có trước khi duyệt"
        )

    return {
        "point_id": point_id,
        "lat": lat,
        "lng": lng,
        "verdict": verdict,
        "reasons": reasons,
        "gates_fired": gates,
        "network": net,
        "demand": dem,
        "operations": {
            "occ_local": None if pd.isna(scored["occ_local"]) else float(scored["occ_local"]),
            "n_marginal_pop": None if pd.isna(scored["n_marginal_pop"]) else float(scored["n_marginal_pop"]),
            "n_redundancy": None if pd.isna(scored["n_redundancy"]) else float(scored["n_redundancy"]),
        },
        "sizing": size,
        "meta": {
            "data_version": params.DATA_VERSION,
            "model_version": MODEL_VERSION,
            "calibration": params.CALIBRATION_LABEL,
            "r_service_km": dctx.actx.net.r_km,
            "vault_tos_restricted": True,
        },
    }


def _fmt(x, unit="", nd=0):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{x:,.{nd}f}{unit}"


def render_markdown(d: dict) -> str:
    """Một trang cho người đọc — mọi dòng là fact kiểm được, không có điểm số."""
    n, dm, op, sz, m = d["network"], d["demand"], d["operations"], d["sizing"], d["meta"]
    obs = {r["current_type"]: r for r in sz["observed"]}
    L = [
        f"# HỒ SƠ THẨM ĐỊNH VỊ TRÍ — {d['point_id']}",
        "",
        f"**Toạ độ:** {d['lat']:.5f}, {d['lng']:.5f} · ô H3 r8 `{dm['h3_r8']}`",
        f"**Kết luận:** **{d['verdict']}**",
        "",
        "## 1. Mạng hiện hữu quanh điểm",
        f"- Trạm gần nhất: **{_fmt(n['d_nearest_m'], ' m')}**",
        f"- Trong 1 km: **{n['n_within_1km']}** trạm · trong {m['r_service_km']:.0f} km: "
        f"**{n['n_within_r']}** trạm / **{n['connectors_within_r']}** cổng (DC: {n['n_dc_within_r']})",
        f"- Đơn vị vận hành trong bán kính: {', '.join(n['operators_within_r']) or '—'}",
        "",
        "## 2. Cầu quanh điểm (proxy — chưa calibrate)",
        f"- Dân số trong {m['r_service_km']:.0f} km: **{_fmt(dm['pop_catchment'])}** người"
        f" · tại ô: {_fmt(dm['pop_cell'])}",
        f"- Đường trong ô: {_fmt(dm['road_len_m_cell'], ' m')} · POI: {dm['n_poi_cell'] if dm['n_poi_cell'] is not None else '—'}"
        f" · cây xăng: {dm['n_fuel_cell'] if dm['n_fuel_cell'] is not None else '—'}"
        f" · bãi đỗ: {dm['n_parking_cell'] if dm['n_parking_cell'] is not None else '—'}",
        f"- Dân chưa được mạng hiện hữu phủ trong bán kính: **{_fmt(op['n_marginal_pop'])}**"
        + (f" ({op['n_redundancy'] * 100:.0f}% đã được phủ)" if op["n_redundancy"] is not None else ""),
        "",
        "## 3. Vận hành trạm lân cận (duration-weighted, cap 30′)",
        (
            f"- Utilization trung bình trạm quanh đây: **{op['occ_local'] * 100:.0f}%**"
            if op["occ_local"] is not None
            else "- Không trạm nào quanh đây có telemetry đạt sàn tin cậy → **chưa đo được**"
        ),
        "",
        "## 4. Định cỡ — so với trạm đang chạy thật ở dải mật độ tương tự",
        f"- Dải mật độ của ô này: **{sz['density_band']}**",
    ]
    for ct in ("DC", "AC"):
        r = obs.get(ct)
        L.append(
            f"- **{ct}**: utilization trung vị **{r['util_p50'] * 100:.0f}%** (n={r['n']:,} trạm)"
            if r
            else f"- **{ct}**: mẫu quá mỏng ở dải này — không công bố"
        )
    if "DC" in obs and "AC" in obs and obs["AC"]["util_p50"] > 0:
        L.append(f"- Chênh lệch DC/AC ở dải này: **{obs['DC']['util_p50'] / obs['AC']['util_p50']:.1f}×**")
    L += [
        "",
        "## 5. Lý do & cảnh báo",
        *([f"- {r}" for r in d["reasons"]] or ["- (không có cờ nào)"]),
        "",
        "## 6. Giới hạn phải đọc kèm",
        "- Đây là **tổng hợp dữ liệu**, không phải dự đoán doanh thu hay số phiên/ngày.",
        "- Cầu là **proxy** (pop/POI/đường), chưa calibrate với cầu EV đo được.",
        "- Utilization ở mục 3–4 là **quan sát trên trạm đang chạy**, không phải cam kết cho trạm mới.",
        f"- Cạnh tranh: toàn bộ mạng nền trong dữ liệu là {', '.join(n['operators_within_r']) or 'VinFast'}"
        " — chưa có dữ liệu đối thủ.",
        "- Gate trùng pipeline đang **[mô phỏng]**: chưa có sổ trạm đã duyệt/đang xây.",
        "",
        f"*{m['model_version']} · {m['data_version']} · {m['calibration']} · nội bộ (vault-ToS)*",
    ]
    return "\n".join(L)


def batch(points: pd.DataFrame, dctx: DossierContext) -> pd.DataFrame:
    """Bảng phẳng cho workflow Excel-ish của BO (batch CSV là giao diện pilot thật)."""
    rows = []
    for i, r in points.reset_index(drop=True).iterrows():
        pid = str(r["point_id"]) if "point_id" in points.columns else f"HS-{i:04d}"
        d = make_dossier(float(r["lat"]), float(r["lng"]), dctx, point_id=pid)
        obs = {x["current_type"]: x for x in d["sizing"]["observed"]}
        rows.append(
            {
                "point_id": pid, "lat": d["lat"], "lng": d["lng"], "verdict": d["verdict"],
                "d_nearest_m": d["network"]["d_nearest_m"],
                "n_within_1km": d["network"]["n_within_1km"],
                "n_within_r": d["network"]["n_within_r"],
                "connectors_within_r": d["network"]["connectors_within_r"],
                "pop_catchment": d["demand"]["pop_catchment"],
                "pop_uncovered": d["operations"]["n_marginal_pop"],
                "occ_local": d["operations"]["occ_local"],
                "density_band": d["sizing"]["density_band"],
                "util_dc_similar": obs.get("DC", {}).get("util_p50"),
                "util_ac_similar": obs.get("AC", {}).get("util_p50"),
                "reasons": " | ".join(d["reasons"]),
                "data_version": params.DATA_VERSION, "model_version": MODEL_VERSION,
                "calibration": params.CALIBRATION_LABEL,
            }
        )  # fmt: skip
    return pd.DataFrame(rows)
