"""Luật đặt trạm của BO → vị từ khả thi + hàng ràng buộc MILP (chốt 2026-07-29).

Tầng này là **nguồn chân lý duy nhất** cho cả hai hướng sản phẩm; ``mclp`` (sinh) và
``assess`` (chấm) đều gọi vào đây thay vì tự chế biến thể riêng::

    Hướng A — SINH:  cho p  → tập S ⊂ I đề xuất, có chứng chỉ tối ưu
    Hướng B — CHẤM:  cho q  → phán quyết + lý do + giá trị biên Δ(q) [đơn vị: người]

Nguyên tắc giữ đúng: **luật quyết định TÍNH HỢP LỆ, bộ tối ưu quyết định THỨ TỰ ƯU
TIÊN.** Không trộn hai thứ vào một điểm số — ``Δ(q)`` là số người, không phải điểm 0–1.
Nhờ vậy bất biến nối hai hướng viết được thành test::

    ∀ q ∈ solve_mclp(p):  verdict(q) ≠ KHÔNG_PHÊ_DUYỆT

Bộ luật (số hiệu theo thứ tự BO gửi):

===== ==================================================================== ==========
Luật  Nội dung                                                             Dạng toán
===== ==================================================================== ==========
R2    Trạm CHỈ có trụ AC không vào đánh giá, không lên bản đồ              lọc ``S₀``
R4    Quận/Phường/Thị xã/Thị trấn: được mở gần, gate bằng hiệu suất        *tắt* R5/R6
R5    Xã: bán kính 2 km không được có trạm khác                            tiền lọc unary
R6    Xã + cao tải: nới còn 500 m                                          tiền lọc unary
R7    Hiệu suất lân cận <30% ⇒ từ chối; hỗn hợp ⇒ người quyết              **CHƯA CHẠY**
R8    Hai đề xuất trong 2 km ⇒ cả hai "Cân nhắc thêm", chọn một            clique + cặp
R9    5 lớp công suất trụ                                                  phân lớp
===== ==================================================================== ==========

**BẤT BIẾN B0 — trạm đã triển khai là BẤT KHẢ XÂM PHẠM** (chốt 29/07). Mọi luật ở đây
chỉ chấm *đề xuất mới*. Không luật nào, không nghiệm nào được đóng, di dời hay xoá một
trạm đang vận hành; T0 **không phải biến quyết định**. Hệ quả cụ thể:

* **R2 không xoá trạm chỉ-AC khỏi thực tế** — nó chỉ rút chúng khỏi *phần được tính phủ*
  và khỏi bản đồ. 12.987 trạm đó vẫn đứng nguyên, và trở thành **ứng viên NÂNG CẤP**
  (thêm trụ DC tại chỗ, giữ nguyên trạm) — tập điểm rẻ nhất trong bài vì đã có đất và
  đã có đấu nối. Đo 29/07: nâng cấp mua được 86% mức phủ của xây mới ở p = 800.
* **R5/R6 không hồi tố.** 42,17% trạm DC đang nằm trong xã đã vi phạm chính luật này;
  chúng được grandfather. Đúng chữ BO dùng: *"Không phê duyệt"* — chặn phía trước.
* ``assert_existing_untouched`` cưỡng chế bất biến này ở tầng nghiệm, có test hồi quy.

**R7 nằm ngoài mô hình, có chủ ý** (chốt 29/07). Ba đại lượng khác nhau cùng tên
"hiệu suất": ``occ_mean_dw`` (F19) là **số trụ bận đồng thời** (max 59,2 — KHÔNG phải
tỷ lệ, so thẳng với "30%" là lỗi loại đại lượng); ``occ_mean_dw / số_trụ`` là tỷ lệ
chiếm dụng theo thời gian (trạm DC: trung vị **16,9%**, **25,2%** vượt 30%); còn BO
tính theo **kWh** thực/danh định, luôn ≤ tỷ lệ thời gian. Áp ngưỡng 30% lên tỷ lệ
thời gian thì 74,8% trạm DC nằm dưới. Xem
``docs/sprint2/results-rules-encoding.md`` §7 Q1.

Ba con số đo được, đừng suy lại (2026-07-29, R = 3 km, bundle ``sprint2-2026-07-28``):

* R2 loại 12.987/18.902 trạm (69,8%) ⇒ ``covered0`` **0,8672 → 0,7290** ``cov@pop``;
* R5 như BO viết giữ **88,65%** ứng viên; hiểu nhầm thành luật phẳng chỉ còn 61,68%
  (Hà Nội: 51,45% vs 9,42%);
* R8 chỉ **18.760 cặp xung đột** trên 15.241 ứng viên ⇒ encode CHÍNH XÁC được, không
  cần row-generation, không cần big-M.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.neighbors import BallTree

#: Bán kính Trái Đất (m) — CÙNG hằng với ``aoi.haversine_km``, không khai lại số khác.
R_EARTH_M = 6_371_008.8

#: Địa bàn được MIỄN luật khoảng cách (R4). "Thị" gộp Thị xã + Thị trấn — chốt 29/07:
#: Thị trấn không nằm trong điều luật nào, xếp về phía đô thị vì là trung tâm huyện.
URBAN_ADMIN_KINDS = frozenset({"Quận", "Phường", "Thị", "Thành"})


class ExistingStationTouched(AssertionError):
    """Nghiệm định đụng vào trạm đã triển khai — lỗi hợp đồng, không phải cảnh báo."""


def assert_existing_untouched(chosen_ids, existing_ids, *, what="nghiệm MCLP"):
    """Bất biến B0: không nghiệm nào được đóng/di dời/xoá trạm đã triển khai.

    Cưỡng chế ở tầng nghiệm chứ không chỉ ghi trong doc, vì đây là ràng buộc *kinh
    doanh* không đảo ngược được: một trạm bị gỡ khỏi kế hoạch có thể thành một trạm bị
    gỡ khỏi thực địa. Ứng viên **nâng cấp** (thêm trụ DC tại ô đã có trạm AC) KHÔNG vi
    phạm — đó là phép cộng tại chỗ, trạm vẫn còn.
    """
    touched = set(map(str, chosen_ids)) & set(map(str, existing_ids))
    if touched:
        raise ExistingStationTouched(
            f"B0 FAIL: {what} chứa {len(touched)} trạm đã triển khai như biến quyết định "
            f"(vd {sorted(touched)[:5]}) — T0 phải bắt buộc mở, không được chọn/bỏ"
        )


class Verdict(str, Enum):
    """Ba mức của hướng B. ``REJECT`` chỉ phát khi có ĐIỀU LUẬT CỤ THỂ bị vi phạm.

    Khác hẳn "tier Từ chối" bị cấm ở v1: cấm cũ nhắm vào từ chối *do điểm số mô hình*
    — không kiểm toán được, không đảo ngược được. Ở đây mọi từ chối đều kèm tên luật +
    số đo, và đảo ngược ngay khi luật đổi. Vẫn CẤM ``score_total``.
    """

    OK = "Đủ điều kiện xem xét"
    REVIEW = "Cân nhắc thêm"
    REJECT = "Không phê duyệt"


@dataclass(frozen=True)
class RuleSet:
    """Tham số luật — mọi ngưỡng PHƠI RA, không có hằng số chôn trong hàm."""

    #: R5 — xã: bán kính cấm quanh trạm hiện hữu (m).
    d_rural_m: float = 2000.0
    #: R6 — xã + cao tải: ngưỡng nới (m).
    d_rural_highload_m: float = 500.0
    #: R4 — đô thị: không áp luật khoảng cách.
    d_urban_m: float = 0.0
    #: R8 — hai ĐỀ XUẤT không được cách nhau dưới ngưỡng này (m).
    d_mutual_m: float = 2000.0
    #: R6 — "cao tải" = công suất trụ đề xuất ≥ ngưỡng (chốt 29/07: lớp 120/150 + 250/300).
    highload_kw: float = 120.0
    #: R2 — chỉ trạm có ≥1 trụ DC mới được tính là mạng hiện hữu.
    require_dc: bool = True
    #: R8 cứng ở hướng SINH (kế hoạch phải sạch), mềm ở hướng CHẤM (gắn cờ, không từ chối).
    mutual_is_hard: bool = True
    urban_kinds: frozenset[str] = URBAN_ADMIN_KINDS

    def clearance_m(self, is_rural, is_highload) -> np.ndarray:
        """``D₀`` cho từng điểm — vectorised, dùng chung cho tiền lọc lẫn hướng B."""
        is_rural = np.asarray(is_rural, dtype=bool)
        is_highload = np.asarray(is_highload, dtype=bool)
        return np.where(
            is_rural,
            np.where(is_highload, self.d_rural_highload_m, self.d_rural_m),
            self.d_urban_m,
        ).astype(float)


# ───────────────────────── R2 · mạng hiện hữu được tính phủ ──────────────────────


def connector_kind(connectors: pd.DataFrame) -> pd.Series:
    """``station_id`` → ``DC`` | ``AC`` | ``UNK``. DC thắng: một trụ DC là đủ (R2)."""
    return connectors.groupby("station_id")["current_type"].agg(
        lambda x: "DC" if "DC" in set(x) else ("AC" if set(x) <= {"AC"} else "UNK")
    )


def power_band(max_kw) -> pd.Categorical:
    """R9 — 5 lớp công suất. Biên đặt giữa hai lớp liền kề, không cắt giữa một lớp."""
    return pd.cut(
        pd.to_numeric(max_kw, errors="coerce"),
        bins=[0, 19.9, 39.9, 99.9, 199.9, np.inf],
        labels=["AC(<20)", "DC 20/30", "DC 60/80", "DC 120/150", "DC 250/300"],
    )


def apply_r2(stations: pd.DataFrame, connectors: pd.DataFrame, rules=RuleSet()) -> pd.DataFrame:
    """Lọc mạng hiện hữu theo R2, gắn ``conn_kind`` + ``max_conn_kw`` + ``power_band``.

    Trạm thiếu dòng connector rơi về ``current_type`` trên bảng station thay vì bị loại
    ngầm — cùng tinh thần P8 bước 6 (giữ UNKNOWN, không suy diễn).
    """
    out = stations.copy()
    kind = connector_kind(connectors)
    out["conn_kind"] = out["station_id"].map(kind)
    miss = out["conn_kind"].isna()
    if "current_type" in out.columns:
        out.loc[miss, "conn_kind"] = out.loc[miss, "current_type"]
    out["conn_kind"] = out["conn_kind"].fillna("UNK")
    out["max_conn_kw"] = out["station_id"].map(connectors.groupby("station_id")["power_kw"].max())
    out["power_band"] = power_band(out["max_conn_kw"])
    if rules.require_dc:
        out = out[out["conn_kind"] == "DC"]
    return out.reset_index(drop=True)


# ───────────────────────── nhãn địa bàn hành chính (R4/R5) ───────────────────────


@dataclass
class AdminLabeller:
    """Nhãn Xã/Đô thị cho một điểm bất kỳ.

    ⚠ **Đây là proxy đo được, không phải sự thật.** Chuyển nhãn từ trạm gần nhất chỉ
    đúng **72,9%** (LOO, k=1; vote k=3 được 74,2%), trong khi đoán bừa "không phải xã"
    đã được 58,4%. R5/R6 đứng hoàn toàn trên nhãn này, nên ``label()`` luôn trả kèm
    ``source`` để tầng trên biết đang đứng trên đất nào — và ``adm_kind`` truyền tay
    LUÔN thắng nhãn suy diễn.

    Sửa đúng cần một trong hai: ranh giới xã/phường **sau sáp nhập 2025** dạng polygon,
    hoặc trường địa bàn đi kèm mỗi điểm đề xuất (BO có sẵn trong depot). OSM có
    ``admin_level`` nhưng nhiều khả năng còn ranh giới TRƯỚC sáp nhập ⇒ sai nguồn.
    """

    #: Độ chính xác đo được của phép suy nhãn — đi kèm mọi output dùng nhãn suy diễn.
    INFERRED_ACC = 0.729

    lat: np.ndarray
    lng: np.ndarray
    is_rural: np.ndarray
    _tree: BallTree = field(init=False, repr=False)

    def __post_init__(self):
        self.is_rural = np.asarray(self.is_rural, dtype=bool)
        self._tree = BallTree(np.radians(np.c_[self.lat, self.lng]), metric="haversine")

    @classmethod
    def from_stations(cls, stations: pd.DataFrame, admin: pd.DataFrame, rules=RuleSet()):
        """Dựng từ bảng trạm + ``official_admin`` (khoá ``store_id``).

        Loại hành chính suy từ TIỀN TỐ tên đơn vị ("Xã Đông Tảo" → ``Xã``) — đó là quy
        ước đặt tên hành chính VN, không phải heuristic tự chế.
        """
        adm = admin.assign(kind=admin["commune"].str.split().str[0]).set_index("store_id")["kind"]
        key = stations["official_store_id"].where(stations["official_store_id"].notna(), stations["station_code"])
        kind = key.map(adm)
        ok = kind.notna()
        if not ok.any():
            raise ValueError("AdminLabeller: không join được nhãn hành chính nào — sai khoá store_id?")
        s = stations[ok]
        return cls(
            lat=s["lat"].to_numpy(float),
            lng=s["lng"].to_numpy(float),
            is_rural=~kind[ok].isin(rules.urban_kinds).to_numpy(),
        )

    def label(self, lat, lng) -> tuple[np.ndarray, str]:
        """→ (``is_rural``, nhãn nguồn). Luôn dùng k=1: vote k lớn hơn không cứu được."""
        _, idx = self._tree.query(np.radians(np.c_[np.atleast_1d(lat), np.atleast_1d(lng)]), k=1)
        return self.is_rural[idx[:, 0]], f"inferred_nn (acc≈{self.INFERRED_ACC:.3f})"


# ─────────────────── R5/R6 · tiền lọc bậc một (không phải hàng MILP) ─────────────


def clearance_ok(cand_lat, cand_lng, net_lat, net_lng, is_rural, is_highload, rules=RuleSet()):
    """Điểm nào giữ được khoảng cách bắt buộc tới mạng hiện hữu?

    Đây là ràng buộc **bậc một** (chỉ phụ thuộc chính điểm đó) nên nó là *tiền lọc*,
    không sinh hàng MILP nào. Trả về ``(mask, d_nearest_m, D₀_m)`` — hai mảng sau đi
    thẳng vào hồ sơ lý do của hướng B.

    T0 được **grandfather**: hàm chỉ chấm ứng viên MỚI. Đo 29/07: 42,17% trạm DC đang
    nằm trong xã đã vi phạm chính luật này ⇒ R5 là luật cho phê duyệt mới, không phải
    kiểm tra tính hợp lệ của mạng đang vận hành (đúng chữ BO dùng: "Không phê duyệt").
    """
    cand_lat, cand_lng = np.atleast_1d(cand_lat).astype(float), np.atleast_1d(cand_lng).astype(float)
    d0 = rules.clearance_m(np.broadcast_to(is_rural, cand_lat.shape), np.broadcast_to(is_highload, cand_lat.shape))
    if len(net_lat) == 0:
        return np.ones(cand_lat.size, dtype=bool), np.full(cand_lat.size, np.inf), d0
    tree = BallTree(np.radians(np.c_[net_lat, net_lng]), metric="haversine")
    d, _ = tree.query(np.radians(np.c_[cand_lat, cand_lng]), k=1)
    d_m = d[:, 0] * R_EARTH_M
    return d_m >= d0, d_m, d0


# ───────────────────────── R8 · xung đột giữa các ĐỀ XUẤT ───────────────────────


def conflict_rows(lat, lng, d_m: float, n_var: int | None = None) -> tuple[sp.csr_matrix, dict]:
    """Hàng ``Σ x ≤ 1`` cưỡng chế "không hai đề xuất nào cách nhau < ``d_m``".

    Hai họ hàng, cộng lại mới **chính xác**:

    1. **Clique tâm-ứng-viên** bán kính ``d/2``. Bất đẳng thức tam giác cho
       ``i, j ∈ B(c, d/2) ⇒ dist(i,j) ≤ d`` nên ``Σ_{j∈B} x_j ≤ 1`` hợp lệ, và nó
       **mạnh hơn hẳn** các hàng cặp mà nó bao. Nhưng nó **KHÔNG đầy đủ**: cặp có
       ``d/2 < dist < d`` không nằm trong quả cầu nào tâm ứng viên.
    2. **Cặp còn dư** cho đúng những cặp mà (1) bỏ sót.

    Chỉ dùng (1) là encode SAI luật, không phải encode yếu — đây là chỗ dễ sai nhất
    của cả module. Đo 29/07: 8.198 clique + ≤18.760 cặp ≈ 27k hàng, so với 36.294 hàng
    phủ đã có ⇒ chi phí không đáng kể, **không cần row-generation, không cần big-M**.

    Ràng buộc dùng ``≤ d``, luật thật là ``< d``: chênh nhau ở tập đo-không, chọn phía
    bảo thủ (cấm nhiều hơn một chút) thay vì phía nới.
    """
    lat, lng = np.asarray(lat, float), np.asarray(lng, float)
    n = lat.size
    n_var = n if n_var is None else n_var
    if n == 0 or d_m <= 0:
        return sp.csr_matrix((0, n_var), dtype=np.float64), {"n_clique": 0, "n_pair": 0, "n_conflict_pairs": 0}

    X = np.radians(np.c_[lat, lng])
    tree = BallTree(X, metric="haversine")

    # (1) clique — dedupe theo tập, bỏ clique tầm thường (chỉ chứa chính nó)
    balls = tree.query_radius(X, r=(d_m / 2) / R_EARTH_M)
    cliques, covered = {}, set()
    for b in balls:
        if b.size < 2:
            continue
        key = frozenset(b.tolist())
        if key in cliques:
            continue
        cliques[key] = np.sort(b)
        srt = cliques[key]
        for a in range(srt.size):
            for c in range(a + 1, srt.size):
                covered.add((int(srt[a]), int(srt[c])))

    # (2) cặp còn dư — mọi cặp xung đột chưa nằm trong clique nào
    full = tree.query_radius(X, r=d_m / R_EARTH_M)
    residual = []
    for i, nb in enumerate(full):
        for j in nb:
            j = int(j)
            if j <= i:
                continue
            if (i, j) not in covered:
                residual.append((i, j))

    rows, cols = [], []
    for r, members in enumerate(cliques.values()):
        rows.extend([r] * members.size)
        cols.extend(members.tolist())
    off = len(cliques)
    for r, (i, j) in enumerate(residual):
        rows.extend([off + r, off + r])
        cols.extend([i, j])

    n_rows = off + len(residual)
    M = sp.csr_matrix((np.ones(len(rows), dtype=np.float64), (rows, cols)), shape=(n_rows, n_var))
    n_conf = sum(1 for i, nb in enumerate(full) for j in nb if int(j) > i)
    return M, {"n_clique": off, "n_pair": len(residual), "n_conflict_pairs": n_conf}


def violates_mutual(lat, lng, d_m: float) -> np.ndarray:
    """Điểm nào có một điểm KHÁC trong cùng tập cách < ``d_m`` (R8, dạng gắn cờ)."""
    lat, lng = np.asarray(lat, float), np.asarray(lng, float)
    if lat.size < 2:
        return np.zeros(lat.size, dtype=bool)
    X = np.radians(np.c_[lat, lng])
    d, _ = BallTree(X, metric="haversine").query(X, k=2)
    return d[:, 1] * R_EARTH_M < d_m


# ───────────────────────────── hướng B · chấm một điểm ──────────────────────────


def verdict(
    d_nearest_m: float,
    d_required_m: float,
    *,
    is_rural: bool,
    conflicts_with_other_proposal: bool = False,
    rules: RuleSet = RuleSet(),
) -> tuple[Verdict, list[str]]:
    """Phán quyết luật cho MỘT điểm + lý do bằng số đo.

    KHÔNG nhận và KHÔNG trả điểm số: xếp hạng trong nhóm hợp lệ là việc của ``Δ(q)``
    (đơn vị người) ở tầng gọi. Trộn hai thứ lại là đúng cái sai mà hợp đồng v1 cấm.
    """
    reasons: list[str] = []
    v = Verdict.OK

    if is_rural and d_required_m > 0 and d_nearest_m < d_required_m:
        v = Verdict.REJECT
        reasons.append(
            f"R5/R6_MIN_DISTANCE: địa bàn xã, trạm gần nhất {d_nearest_m:.0f} m "
            f"< ngưỡng {d_required_m:.0f} m — không phê duyệt"
        )
    elif not is_rural:
        reasons.append(
            f"R4_URBAN_EXEMPT: địa bàn đô thị — không áp luật khoảng cách "
            f"(trạm gần nhất {d_nearest_m:.0f} m). Gate hiệu suất R7 CHƯA chạy được"
        )

    if conflicts_with_other_proposal:
        reasons.append(
            f"R8_PROPOSAL_OVERLAP: có đề xuất khác trong {rules.d_mutual_m:.0f} m — "
            "làm việc lại với NPP để chọn một điểm"
        )
        if v is Verdict.OK:
            v = Verdict.REVIEW

    reasons.append(
        "R7_NOT_APPLIED: gate hiệu suất lân cận chưa chạy — đơn vị 'hiệu suất' của BO chưa khớp F19 (nợ đã khai)"
    )
    return v, reasons
