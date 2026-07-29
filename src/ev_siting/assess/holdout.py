"""Cắt holdout ĐỊA LÝ cho v0.2 — niêm phong trước khi EDA (kỷ luật chống rò thiết kế).

Vì sao phải có: v0.2 được thiết kế SAU khi thấy T1 v0 fail. Sàng feature trên đúng tập
GT rồi báo AUC trên chính tập đó là **chọn trên tập test** — công bằng ngưỡng (L1/L2/L3)
không cứu được. Design chỉ được nhìn nửa DESIGN; nửa HOLDOUT mở đúng MỘT lần khi đánh giá.

Vì sao block địa lý chứ không phải random: trạm sạc có tự tương quan không gian — hai trạm
cách 2 km rơi hai bên vạch làm holdout "dễ" giả tạo. Block phải lớn hơn nhiều so với bán
kính phục vụ R = 3 km.

Vì sao H3 res 3 (~59 km cạnh) chứ không phải nhãn tỉnh: CONTEXT.md cấm dùng admin
("TP/tỉnh") làm đơn vị phân tích sau sáp nhập 2025 — tỉnh giờ là vùng đa cực cấp 60 km,
đúng bằng thang res 3, nhưng res 3 tái lập được và không phụ thuộc bảng admin nào.

Phân bổ block là GREEDY tất định (block đông nhất trước, tie-break theo mã ô) — không có
randomness nào để tinh chỉnh, nên không ai (kể cả tôi) chọn được split có lợi.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import h3
import numpy as np
import pandas as pd

from ev_siting.aoi import haversine_km
from ev_siting.assess import paths

#: Cạnh ô ~59 km ≫ R = 3 km ⇒ chỉ trạm sát vạch mới chia sẻ catchment (đo và báo ở meta).
BLOCK_RES = 3
HOLDOUT_FRAC = 0.40
#: Hai lần bán kính phục vụ — trạm holdout gần trạm design hơn mức này là rò biên còn lại.
LEAK_RADIUS_KM = 6.0

SPLIT_PATH = paths.CACHE_DIR / "holdout_split.json"


def assign_blocks(lats, lngs, res: int = BLOCK_RES, holdout_frac: float = HOLDOUT_FRAC) -> dict[str, str]:
    """Gán mỗi block H3 -> 'design' | 'holdout' sao cho ~holdout_frac điểm vào holdout.

    LPT (block đông nhất trước, gán vào bin đang **thiếu tương đối** nhiều nhất), không
    phải "nhồi holdout cho đủ quota". Lý do: nhồi tuần tự đẩy trọn 4 block đô thị lớn về
    một phía, biến split thành **distribution shift** (design nông thôn → holdout đô thị)
    — lúc đó chênh lệch AUC không còn đo overfit nữa mà đo việc hai nửa khác phân bố.
    LPT xen kẽ các block lớn nên cả hai nửa đều có đô thị lẫn vùng thưa.

    Tie-break theo mã ô ⇒ tất định tuyệt đối: không có tham số randomness nào để ai đó
    (kể cả tôi) dò được một split có lợi.
    """
    cells = [h3.latlng_to_cell(float(la), float(lo), res) for la, lo in zip(lats, lngs)]
    counts = Counter(cells)
    quota = {"design": 1.0 - holdout_frac, "holdout": holdout_frac}

    assign: dict[str, str] = {}
    load = {"design": 0.0, "holdout": 0.0}
    for cell in sorted(counts, key=lambda c: (-counts[c], c)):
        # bin nào "đầy" ít nhất so với hạn ngạch của nó thì nhận block tiếp theo
        target = min(load, key=lambda b: (load[b] / quota[b], b))
        assign[cell] = target
        load[target] += counts[cell]
    return assign


def _leak_report(lats, lngs, is_holdout: np.ndarray) -> dict:
    """Đo rò biên còn lại: trạm holdout nằm trong 2R của một trạm design."""
    lat_d, lng_d = np.asarray(lats)[~is_holdout], np.asarray(lngs)[~is_holdout]
    n_near = 0
    for la, lo in zip(np.asarray(lats)[is_holdout], np.asarray(lngs)[is_holdout]):
        if len(lat_d) and np.min(haversine_km(float(la), float(lo), lat_d, lng_d)) < LEAK_RADIUS_KM:
            n_near += 1
    total_h = int(is_holdout.sum())
    return {
        "leak_radius_km": LEAK_RADIUS_KM,
        "n_holdout_within_leak_radius": n_near,
        "share_holdout_leaky": round(n_near / total_h, 4) if total_h else 0.0,
    }


def build_split(gt: pd.DataFrame, out: Path = SPLIT_PATH) -> dict:
    """Cắt split từ GT (cột lat, lng) và NIÊM PHONG ra file.

    File chỉ ghi **mã block H3** (công khai, suy từ lưới) + số đếm — không ghi mã trạm hay
    toạ độ vault. Ai cũng tái tạo được nhãn design/holdout của một điểm bằng
    ``label_points`` mà không cần chạm dữ liệu vault.
    """
    lats = gt["lat"].to_numpy(dtype=float)
    lngs = gt["lng"].to_numpy(dtype=float)
    assign = assign_blocks(lats, lngs)
    labels = label_points(lats, lngs, assign)
    is_h = labels == "holdout"

    doc = {
        "schema": "vgreen.assess-holdout/1",
        "block_res": BLOCK_RES,
        "holdout_frac_target": HOLDOUT_FRAC,
        "n_points": int(len(gt)),
        "n_design": int((~is_h).sum()),
        "n_holdout": int(is_h.sum()),
        "holdout_share_actual": round(float(is_h.mean()), 4),
        "n_blocks": len(assign),
        "n_blocks_holdout": sum(1 for v in assign.values() if v == "holdout"),
        "blocks": assign,
        "leak": _leak_report(lats, lngs, is_h),
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def load_split(path: Path = SPLIT_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"HOLDOUT FAIL: chưa cắt split {path} — chạy `python -m ev_siting.assess.holdout` trước EDA")
    return json.loads(path.read_text(encoding="utf-8"))


def label_points(lats, lngs, assign: dict[str, str], res: int = BLOCK_RES) -> np.ndarray:
    """Nhãn design/holdout cho điểm bất kỳ (GT lẫn control) theo cùng bản đồ block.

    Block chưa từng thấy trong GT (control rơi vào vùng trống) mặc định 'design': nửa
    holdout phải là tập ĐÓNG do GT định nghĩa, không được phình theo control.
    """
    return np.array([assign.get(h3.latlng_to_cell(float(la), float(lo), res), "design") for la, lo in zip(lats, lngs)])


def main():
    from ev_siting.assess.retrodiction import load_ground_truth

    gt, _, sha = load_ground_truth()
    doc = build_split(gt)
    doc["ground_truth_sha256"] = sha
    Path(SPLIT_PATH).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"[holdout] {doc['n_points']} GT -> design {doc['n_design']} / holdout {doc['n_holdout']} "
        f"({doc['holdout_share_actual']:.1%}) qua {doc['n_blocks']} block res{BLOCK_RES} "
        f"({doc['n_blocks_holdout']} block holdout)"
    )
    leak = doc["leak"]
    print(
        f"[holdout] rò biên: {leak['n_holdout_within_leak_radius']}/{doc['n_holdout']} "
        f"({leak['share_holdout_leaky']:.1%}) trạm holdout nằm trong {LEAK_RADIUS_KM:.0f} km của một trạm design"
    )
    print(f"[holdout] NIÊM PHONG -> {SPLIT_PATH}")


if __name__ == "__main__":
    main()
