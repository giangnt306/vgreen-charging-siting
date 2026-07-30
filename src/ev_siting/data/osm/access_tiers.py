#!/usr/bin/env python3
"""access_tiers.py — E-DQ8a: lối vào đo ở thang LÂN CẬN, không đo trong một ô.

VẤN ĐỀ. `buildable_h3` và E-DQ8 hỏi "ô này có đường không?" bằng cách xét **đúng ô đó**
(`road_access_m <= 0`). Ô res 8 rộng 0,75 km², tâm hai ô kề cách **0,98 km**: một xóm mà
đường vào nằm ở **ô bên cạnh** bị kết luận là "không có đường". Đo được: **4.862/6.350 ô**
(72,1% khối lượng, 894.956 người) của E-DQ8 có đường ngay trong vành 1. Đây **không phải
lỗi dữ liệu** — là lỗi **thang đo**, cùng họ với `poi_coords_in_vn` (E-DQ7a) và
`POP_DENSITY_OUTLIER` (E-DQ7f): một đại lượng không chứa thông tin về câu hỏi được hỏi.

E-DQ7a đã gặp và đã giải đúng bài này ở tầng biên giới — "test là **giao lục giác** ∩
polygon, KHÔNG phải tâm-ô-trong-polygon" — vì ô vắt biên rơi tâm về bên nào cũng được.
Tầng đường chưa được xử lý cùng cách. Module này xử lý.

BẬC LỐI VÀO (thứ tự, không phải nhị phân — cùng nguyên tắc "hai cột, hai nhiệm vụ" của
E-DQ7b):

    DIRECT    có đường lái xe được TRONG ô            -> đặt trụ được
    ADJACENT  không, nhưng vành 1 có (~1,0 km)         -> tới được, KHÔNG đặt trụ được
    NEAR      không, nhưng vành 2 có (~2,0 km)         -> tới được, xa
    ISOLATED  không có đường trong bán kính ~2 vành    -> ứng viên cô lập THẬT

⚠️ ADJACENT **không** đồng nghĩa "xây được". Kiểm ngoại vi bằng 19.015 trạm đang vận
hành: **99,43%** trạm nằm ở ô `DIRECT`, chỉ **15 trạm (0,079%)** ở ô `ADJACENT` — trong
khi ô `ADJACENT` giữ **0,917%** dân số. Tức trạm thật dưới mức dân số ~11×. Bằng chứng
này ĐỦ để nói "ADJACENT là tới được" (có 15 trạm thật ở đó) nhưng **không đủ** để nói
"ADJACENT tương đương DIRECT". Vì vậy:

  - `buildable` loại cứng **chỉ** `ISOLATED` (thay `NO_ROAD_ACCESS` cũ, vốn loại cả 4.862
    ô ADJACENT);
  - dân ở ADJACENT/NEAR **không** được coi là phục vụ được tại chỗ — khối lượng phải
    **dời** sang ô `DIRECT` có built-up cùng xã (E-DQ8b, `reallocate_roadless.py`).

Hai việc đó là hai nửa của cùng một phép sửa: thang đo lối vào (đây) và thang đo khối
lượng dân (8b). Không nửa nào tự đủ.

Hàm ở đây **thuần** (vào DataFrame, ra DataFrame) để test khoá được hành vi mà không cần
raster hay `.pbf` — cùng khuôn `road_semantics.py` / `poi_semantics.py`.
"""
import numpy as np
import pandas as pd

import h3

#: Bậc lối vào, **theo thứ tự tốt dần → xấu dần**. Thứ tự là hợp đồng: consumer so sánh
#: bằng chỉ số (`TIER_ORDER.index`), không so chuỗi.
TIER_ORDER = ["DIRECT", "ADJACENT", "NEAR", "ISOLATED"]

#: Bậc bị loại cứng khỏi `buildable`. CHỈ `ISOLATED` — xem docstring về 15 trạm ADJACENT.
BUILDABLE_EXCLUDED_TIERS = ("ISOLATED",)

#: Bậc được coi là "đặt trụ được" ⇒ hợp lệ làm ô NHẬN khi dời dân (E-DQ8b).
RECEIVER_TIERS = ("DIRECT",)

#: Cột suy ra, thêm vào `demand_h3`.
DERIVED_COLUMNS = ["road_access_nb1_m", "road_access_nb2_m", "access_tier"]


def _ring_sums(cells, acc, k_max=2):
    """Σ access của vành 1..k_max cho từng ô, tra từ dict `acc` (h3 -> mét)."""
    nb = np.zeros((k_max, len(cells)), dtype=float)
    for i, c in enumerate(cells):
        for k in range(1, k_max + 1):
            # grid_disk(k) là đĩa (gồm mọi vành ≤ k) -> trừ chính ô, cộng dồn tự nhiên
            nb[k - 1, i] = sum(acc.get(x, 0.0) for x in h3.grid_disk(c, k) if x != c)
    return nb


def classify(self_access_m, nb1_m, nb2_m):
    """(access trong ô, Σ vành 1, Σ vành 2) -> bậc. **Nơi DUY NHẤT** định nghĩa bậc.

    `derive()` và `tiers_from_lookup()` đều đi qua đây: hai đường tính bậc mà tự viết
    lấy quy tắc là đúng loại lỗi mà `road_tiers_sum_eq_access` (E-DQ7b) phải dựng cổng
    để bắt — ở đây chặn từ gốc bằng cách chỉ có một chỗ để sai.
    """
    return np.select(
        [np.asarray(self_access_m) > 0, np.asarray(nb1_m) > 0, np.asarray(nb2_m) > 0],
        ["DIRECT", "ADJACENT", "NEAR"],
        default="ISOLATED")


def ring_access_sums(cells, access_m, k_max=2):
    """Σ `road_access_m` của các ô trong vành 1 và vành 2 (KHÔNG gồm chính ô).

    Ô ngoài lưới coi như 0 — đúng ngữ nghĩa "OSM không có đường ở đó", và là lý do
    hàm nhận cả lưới một lần thay vì tính từng ô: tổng vành phụ thuộc ô láng giềng nên
    không thể tính đúng trên một tập con. Cần phân bậc một TẬP CON thì dùng
    `tiers_from_lookup()`, nó tra láng giềng trên nguồn đầy đủ.
    """
    return _ring_sums(cells, dict(zip(cells, np.asarray(access_m, dtype=float))), k_max)


def tiers_from_lookup(cells, access_lookup):
    """Bậc lối vào cho `cells`, tra access của **cả ô đó lẫn láng giềng** từ
    `access_lookup` (mapping h3 -> mét, thường là toàn bộ `osm_demand_components_h3`).

    Dùng khi tập cần phân bậc **không** phải toàn lưới — ví dụ ô AOI thành phố không có
    dòng trong `demand_h3`. Trả về mảng bậc, KHÔNG mặc định `ISOLATED`: bậc được **tính**
    từ nguồn đường, nên ô chứa trạm sạc thật mà OSM chưa vẽ đường tới vẫn nhận đúng
    `ADJACENT` thay vì bị loại cứng (đo 30/07: 76 ô như thế chứa 83 trạm đang vận hành —
    50 ADJACENT · 8 NEAR · 18 ISOLATED).
    """
    acc = dict(access_lookup)
    cells = list(cells)
    if not cells:
        return np.array([], dtype=object)
    nb1, nb2 = _ring_sums(cells, acc)
    return classify([acc.get(c, 0.0) for c in cells], nb1, nb2)


def derive(df, access_col="road_access_m"):
    """Thêm `road_access_nb1_m`, `road_access_nb2_m`, `access_tier` vào `df`.

    `df` phải là **toàn lưới** (mọi ô mà pipeline biết tới), có `h3_r8` + `access_col`.
    """
    if "h3_r8" not in df.columns or access_col not in df.columns:
        raise ValueError(f"cần cột h3_r8 + {access_col}")
    cells = df["h3_r8"].tolist()
    nb1, nb2 = ring_access_sums(cells, df[access_col].to_numpy())
    out = df.copy()
    out["road_access_nb1_m"] = nb1
    out["road_access_nb2_m"] = nb2
    out["access_tier"] = classify(out[access_col].to_numpy(), nb1, nb2)
    return out


def tier_rank(tier):
    """Bậc -> số nguyên (0 = DIRECT tốt nhất). Dùng để so sánh/sắp xếp có thứ tự."""
    s = pd.Series(tier).astype(str)
    return s.map({t: i for i, t in enumerate(TIER_ORDER)}).fillna(len(TIER_ORDER)).astype(int)


def summarise(df, pop_col="pop"):
    """Bảng phân bố ô/dân theo bậc — dùng cho report JSON và cổng QA."""
    g = df.groupby("access_tier")
    tot = float(df[pop_col].sum()) or 1.0
    return {t: {"cells": int(len(x)), "pop": float(x[pop_col].sum()),
                "pop_share": float(x[pop_col].sum() / tot)}
            for t, x in g}
