"""Chia công ``n_marginal_pop`` cho kế hoạch nhiều điểm (pre-reg §1).

Hàm phủ là submodular (mỗi ô cầu chỉ được đếm một lần) nên Shapley value có công
thức đóng: ô c chưa bị nền N phủ, được ``k_c`` điểm trong lô phủ ⇒ mỗi điểm nhận
``pop_c / k_c`` — không cần duyệt n! hoán vị. ``solo``/``last_in`` là hai biên
lạc-quan/khắc-nghiệt kẹp quanh Shapley; |P|>1 tính đủ cả ba để người duyệt thấy
khoảng dao động thay vì một con số giả-chắc-chắn (pre-reg §1).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

import pandas as pd

from ev_siting.assess import params


def split_marginal(
    cells_per_point: Sequence[frozenset[str]],
    covered: frozenset[str],
    dem: Mapping[str, float] | pd.Series,
    rule: str,
) -> list[float]:
    """Chia tổng pop biên (ngoài nền ``covered``) cho từng điểm trong lô theo ``rule``.

    Ô không có trong ``dem`` tính pop 0 — ngoài lưới cầu không phải lỗi ở tầng này
    (G1 xử lý riêng ở tầng gate). Trả list float thuần, cùng thứ tự ``cells_per_point``.
    """
    if rule not in params.CREDIT_RULES:
        raise ValueError(f"credit_rule không hợp lệ: {rule!r} — phải thuộc {params.CREDIT_RULES}")

    # Mapping lẫn pd.Series đều có .get(key, default) — một đường đọc pop chung để
    # caller không phải copy bảng cầu (~268k ô) sang dict chỉ để chia công.
    pop = dem.get

    if rule == "solo":
        # Mỗi điểm chấm một mình vs N: bỏ qua chồng lấn nội lô ⇒ biên trên (lạc quan).
        return [float(sum(pop(c, 0.0) for c in cells - covered)) for cells in cells_per_point]

    if rule == "last_in":
        # Điểm i coi như vào SAU CÙNG: mọi điểm khác đã nhập vào nền ⇒ biên dưới (khắc nghiệt).
        out: list[float] = []
        for i, cells in enumerate(cells_per_point):
            others: set[str] = set(covered)
            for j, other in enumerate(cells_per_point):
                if j != i:
                    others |= other
            out.append(float(sum(pop(c, 0.0) for c in cells - others)))
        return out

    # shapley — công thức đóng: trong một hoán vị ngẫu nhiên, ô c được ghi công cho
    # điểm phủ nó ĐỨNG ĐẦU trong k_c điểm; xác suất mỗi điểm đứng đầu là 1/k_c,
    # nên kỳ vọng đóng góp của c cho mỗi điểm phủ đúng bằng pop_c/k_c.
    counts: Counter[str] = Counter()
    for cells in cells_per_point:
        counts.update(cells - covered)
    return [float(sum(pop(c, 0.0) / counts[c] for c in cells - covered)) for cells in cells_per_point]
