"""B8 — danh sách bẫy: chấm 20 địa điểm ai cũng biết, rồi **kiểm lại từng fact**.

Kịch bản chết B (STATE §2): *sai một fact trước mặt người biết địa bàn* — "cách đó
200 m có 3 trạm rồi kìa". Không phòng được bằng cách đọc lại code; phòng bằng cách
tính lại mọi con số sẽ in ra hồ sơ bằng **đường khác**, rồi so.

Oracle ở đây **không dùng** BallTree, **không dùng** ``grid_disk``, **không dùng**
tập phủ đã cache — chỉ haversine thẳng trên bảng trạm và lưới cầu:

===========================  ==========================================
Fact trong hồ sơ             Oracle
===========================  ==========================================
``d_nearest_m``              ``min`` haversine tới toàn bộ trạm covered0
``n_within_1km`` / ``_r``    đếm haversine ≤ 1 km / ≤ R
``connectors_within_r``      Σ ``num_connectors`` các trạm ≤ R
``pop_cell``                 tra ``demand_h3`` tại ô của điểm
``pop_catchment``            Σ pop các ô có tâm ≤ R quanh **tâm ô** của điểm
``n_marginal_pop``           như trên, trừ ô nằm ≤ R quanh tâm ô của bất kỳ trạm nào
===========================  ==========================================

**Giới hạn phải nói thẳng:** cái này chứng minh được *máy tự nhất quán và khớp
nguồn* — nó **không** chứng minh được *nguồn khớp thực địa*. Nửa sau phải do người
thuộc địa bàn xác nhận trên chính bảng này (cột ``ghi_chú_người_kiểm`` để trống sẵn),
và toạ độ mốc dưới đây là **xấp xỉ** — trước buổi demo phải để người biết địa bàn
chốt lại toạ độ, không lấy nguyên.

Chạy::

    make spotcheck
"""

from __future__ import annotations

import h3
import numpy as np
import pandas as pd

from ev_siting.aoi import haversine_km
from ev_siting.assess import dossier, params, paths

#: Sai số cho phép khi so hai đường tính (mét / người). Không phải "ngưỡng chấp nhận
#: lỗi" — là dung sai số học của float; lệch thật luôn lớn hơn nhiều bậc.
TOL_M = 1e-6
TOL_POP = 1e-6

#: Toạ độ **xấp xỉ** của mốc ai cũng biết — dùng để kiểm nhất quán, KHÔNG phải
#: nguồn địa lý. Người thuộc địa bàn chốt lại trước demo (xem docstring).
TRAP_POINTS = [
    ("BAY-01", "Hồ Hoàn Kiếm", "Hà Nội", 21.0287, 105.8524),
    ("BAY-02", "Vincom Bà Triệu", "Hà Nội", 21.0122, 105.8490),
    ("BAY-03", "Times City", "Hà Nội", 20.9944, 105.8683),
    ("BAY-04", "Sân bay Nội Bài", "Hà Nội", 21.2212, 105.8072),
    ("BAY-05", "Royal City", "Hà Nội", 21.0022, 105.8156),
    ("BAY-06", "Landmark 81", "TP.HCM", 10.7951, 106.7218),
    ("BAY-07", "Vincom Đồng Khởi", "TP.HCM", 10.7778, 106.7017),
    ("BAY-08", "Sân bay Tân Sơn Nhất", "TP.HCM", 10.8188, 106.6520),
    ("BAY-09", "Bến xe Miền Đông mới", "TP.HCM", 10.8814, 106.8137),
    ("BAY-10", "Khu đô thị Phú Mỹ Hưng (Q7)", "TP.HCM", 10.7297, 106.7020),
    ("BAY-11", "Vincom Ngô Quyền", "Đà Nẵng", 16.0629, 108.2308),
    ("BAY-12", "Bà Nà Hills", "Đà Nẵng", 15.9955, 107.9967),
    ("BAY-13", "Vincom Lê Thánh Tông", "Hải Phòng", 20.8600, 106.6880),
    ("BAY-14", "Vincom Xuân Khánh", "Cần Thơ", 10.0295, 105.7690),
    ("BAY-15", "Vinpearl Nha Trang", "Khánh Hoà", 12.2166, 109.2440),
    ("BAY-16", "Kinh thành Huế", "Huế", 16.4637, 107.5909),
    ("BAY-17", "Bãi Cháy", "Quảng Ninh", 20.9530, 107.0790),
    ("BAY-18", "Bãi Sau Vũng Tàu", "Bà Rịa – Vũng Tàu", 10.3460, 107.0843),
    ("BAY-19", "Dương Đông, Phú Quốc", "Kiên Giang", 10.2170, 103.9670),
    ("BAY-20", "Thị trấn Sa Pa", "Lào Cai", 22.3364, 103.8438),
]


def _oracle(lat: float, lng: float, st: pd.DataFrame, dem: pd.DataFrame, r_km: float) -> dict:
    """Tính lại mọi fact mạng + cầu bằng haversine thẳng — không BallTree, không grid_disk."""
    d_km = haversine_km(lat, lng, st["lat"].to_numpy(), st["lng"].to_numpy())
    in_r = d_km <= r_km

    cell = h3.latlng_to_cell(lat, lng, 8)
    c_lat, c_lng = h3.cell_to_latlng(cell)
    dl, dn = dem["lat"].to_numpy(), dem["lng"].to_numpy()
    in_catch = haversine_km(c_lat, c_lng, dl, dn) <= r_km

    # Ô nào đã nằm trong bán kính phục vụ của MỘT trạm bất kỳ (theo tâm ô của trạm).
    scells = st["h3_r8"].drop_duplicates().to_numpy()
    sll = np.array([h3.cell_to_latlng(c) for c in scells])
    catch_idx = np.flatnonzero(in_catch)
    covered = np.zeros(len(catch_idx), dtype=bool)
    for s_lat, s_lng in sll:  # ~12,8k trạm × ~40 ô catchment — rẻ hơn ma trận đầy đủ
        if haversine_km(s_lat, s_lng, c_lat, c_lng) > 2 * r_km:
            continue  # không thể chạm catchment
        covered |= haversine_km(s_lat, s_lng, dl[catch_idx], dn[catch_idx]) <= r_km

    pop = dem["pop"].to_numpy(dtype=float)
    row = dem.loc[dem["h3_r8"] == cell, "pop"]
    return {
        "d_nearest_m": float(d_km.min() * 1000.0) if len(d_km) else np.inf,
        "n_within_1km": int((d_km <= params.COMPETITION_RADIUS_KM).sum()),
        "n_within_r": int(in_r.sum()),
        "connectors_within_r": float(st.loc[in_r, "num_connectors"].sum()),
        "pop_cell": float(row.iloc[0]) if len(row) else np.nan,
        "pop_catchment": float(pop[catch_idx].sum()),
        "n_marginal_pop": float(pop[catch_idx][~covered].sum()),
    }


def _compare(fact: dict, oracle: dict) -> list[str]:
    """Danh sách lệch — rỗng nghĩa là 0 lỗi fact."""
    bad = []
    for k, tol in (
        ("d_nearest_m", TOL_M),
        ("n_within_1km", 0),
        ("n_within_r", 0),
        ("connectors_within_r", 0),
        ("pop_cell", TOL_POP),
        ("pop_catchment", TOL_POP),
        ("n_marginal_pop", TOL_POP),
    ):
        a, b = fact.get(k), oracle.get(k)
        if a is None and b is None:
            continue
        if a is None or b is None or (pd.isna(a) != pd.isna(b)):
            bad.append(f"{k}: máy={a} oracle={b}")
        elif pd.notna(a) and abs(float(a) - float(b)) > tol:
            bad.append(f"{k}: máy={a:,.3f} oracle={b:,.3f}")
    return bad


def run(points=TRAP_POINTS, scope: str = params.SCOPE, label: str = params.FREEZE_LABEL) -> pd.DataFrame:
    dctx = dossier.build_context(scope=scope, label=label)
    st = dctx.actx.bundle.covered0[["lat", "lng", "h3_r8", "num_connectors"]]
    dem = pd.read_parquet(paths.DEMAND_H3, columns=["h3_r8", "pop"])
    ll = np.array([h3.cell_to_latlng(c) for c in dem["h3_r8"]])
    dem = dem.assign(lat=ll[:, 0], lng=ll[:, 1])
    r_km = dctx.actx.net.r_km

    rows = []
    for pid, name, prov, lat, lng in points:
        d = dossier.make_dossier(lat, lng, dctx, point_id=pid)
        fact = {**d["network"], **d["demand"], **d["operations"]}
        bad = _compare(fact, _oracle(lat, lng, st, dem, r_km))
        rows.append(
            {
                "point_id": pid, "địa_điểm": name, "tỉnh_tp": prov, "lat": lat, "lng": lng,
                "kết_luận": d["verdict"],
                "trạm_gần_nhất_m": None if fact["d_nearest_m"] is None else round(fact["d_nearest_m"]),
                "trạm_trong_1km": fact["n_within_1km"],
                "trạm_trong_R": fact["n_within_r"],
                "cổng_trong_R": int(fact["connectors_within_r"]),
                "dân_trong_R": round(fact["pop_catchment"]),
                "dân_chưa_phủ": None if fact["n_marginal_pop"] is None else round(fact["n_marginal_pop"]),
                "lỗi_fact": " ; ".join(bad),
                "ghi_chú_người_kiểm": "",
            }
        )  # fmt: skip
    return pd.DataFrame(rows)


def render_markdown(tab: pd.DataFrame, r_km: float = params.R_SERVICE_KM) -> str:
    n_bad = int((tab["lỗi_fact"] != "").sum())
    head = [
        "# B8 — Bảng bẫy 20 hồ sơ (T0 · độ đúng fact)",
        "",
        f"**{len(tab)} điểm · {n_bad} điểm có lệch giữa máy và oracle độc lập.**",
        "",
        f"Oracle tính lại bằng haversine thẳng (không BallTree, không `grid_disk`). R = {r_km:.0f} km.",
        "",
        "> ⚠ Bảng này chứng minh **máy khớp nguồn dữ liệu**. Nó KHÔNG chứng minh **nguồn khớp",
        "> thực địa** — cột `ghi_chú_người_kiểm` để người thuộc địa bàn điền. Toạ độ mốc là",
        "> **xấp xỉ**, phải được chốt lại trước demo.",
        "",
    ]
    cols = [
        "point_id", "địa_điểm", "tỉnh_tp", "kết_luận", "trạm_gần_nhất_m",
        "trạm_trong_1km", "trạm_trong_R", "cổng_trong_R", "dân_trong_R", "dân_chưa_phủ", "lỗi_fact",
    ]  # fmt: skip
    body = [
        "| " + " | ".join(cols) + " |",
        "|" + "|".join(["---"] * len(cols)) + "|",
        *(
            "| " + " | ".join("—" if pd.isna(r[c]) else f"{r[c]:,}" if isinstance(r[c], (int, float)) else str(r[c])
                              for c in cols) + " |"
            for _, r in tab.iterrows()
        ),
    ]  # fmt: skip
    return "\n".join(head + body) + "\n"
