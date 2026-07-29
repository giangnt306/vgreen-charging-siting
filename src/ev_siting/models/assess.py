"""Đánh giá nghiệm MCLP — chỗ ở của các nghĩa vụ báo cáo, tách khỏi solver.

Vì sao là module riêng chứ không nằm trong ``mclp.py``: những thứ dưới đây là
**điều kiện công bố số**, không phải chi tiết của thuật toán tối ưu. Gộp vào solver
thì chúng biến thành tuỳ chọn và sẽ bị bỏ qua đúng lúc cần nhất.

Hợp đồng phải cài (candidate-sites.md §10, chốt 2026-07-28):

1. **Cảnh báo khảo sát thực địa** cho điểm được chọn có ``tier == T4`` hoặc mang
   ĐỒNG THỜI ``NO_ROAD_ACCESS`` + ``NOT_BUILT_UP`` (``paths.SURVEY_WARNING_*``).
2. **Bảng phân rã** số điểm chọn theo ``penalty_flags`` × ``capex_class``, để người
   đọc thấy bao nhiêu khuyến nghị đứng trên đất chưa kiểm chứng.
3. **Sensitivity λ ∈ {0, 1, 3}**: tập chọn lệch > ``SENSITIVITY_MAX_SHIFT`` giữa
   λ=0 và λ=1 ⇒ ``penalty`` chi phối nghiệm hơn cả demand -> chặn công bố.

Cả ba là hàm thuần trên nghiệm đã có (DataFrame cột tối thiểu: ``candidate_id``,
``tier``, ``penalty_flags``, ``capex_class``, ``is_existing``) — không đọc file,
không side-effect, để solver nào (greedy hay MIP) cũng phải đi qua cùng một cửa.
"""

from collections.abc import Iterable, Mapping

import pandas as pd

from ev_siting.models.paths import (
    LAMBDA_SENSITIVITY,
    SENSITIVITY_MAX_SHIFT,
    SURVEY_WARNING_FLAGS,
    SURVEY_WARNING_TIERS,
)

# frozenset không giữ thứ tự, mà reason phải grep-được chéo với câu chữ hợp đồng §10
# ("NO_ROAD_ACCESS ∧ NOT_BUILT_UP") — nên in theo thứ tự của doc, cờ lạ (nếu hợp đồng
# mở rộng sau này) nối sorted phía sau thay vì lặng lẽ biến mất khỏi nhãn.
_CONTRACT_FLAG_ORDER = ("NO_ROAD_ACCESS", "NOT_BUILT_UP")
_FLAGS_LABEL = "+".join(
    [f for f in _CONTRACT_FLAG_ORDER if f in SURVEY_WARNING_FLAGS]
    + sorted(SURVEY_WARNING_FLAGS - set(_CONTRACT_FLAG_ORDER))
)


def _flags_set(value) -> frozenset:
    """Chuẩn hoá một ô ``penalty_flags`` về set cờ.

    None/NaN (sinh ra từ join/parquet round-trip) nghĩa là "không cờ" chứ không phải
    lỗi — một ô null không được làm vỡ cả report. Str đơn lẻ cũng nhận, vì để lọt
    xuống nhánh iterate sẽ thành duyệt từng ký tự: bug câm, không exception nào báo.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return frozenset()
    if isinstance(value, str):
        return frozenset({value}) if value else frozenset()
    return frozenset(str(f) for f in value)


def survey_warnings(solution: pd.DataFrame) -> pd.DataFrame:
    """Các dòng nghiệm PHẢI kèm cảnh báo khảo sát thực địa trước khi trình bày.

    Điều kiện (hợp đồng §10-1): ``tier`` thuộc ``SURVEY_WARNING_TIERS`` HOẶC
    ``penalty_flags`` chứa ĐỒNG THỜI đủ mọi cờ trong ``SURVEY_WARNING_FLAGS`` —
    một cờ đơn lẻ không kích hoạt, vì từng cờ riêng chỉ là phạt mềm (F14).

    ``is_existing=True`` thoả điều kiện VẪN vào danh sách: hợp đồng viết "mọi điểm
    được chọn", và chính 17 trạm T0 đang chạy thật mang cả hai cờ là bằng chứng cờ
    có thể sai — tự miễn trừ ở đây là giấu bằng chứng đó khỏi report. Cột
    ``is_existing`` giữ nguyên để report tự diễn giải.

    Trả về các dòng cảnh báo với đầy đủ cột gốc + ``survey_reason``
    ("tier=T4" / "flags=NO_ROAD_ACCESS+NOT_BUILT_UP" / cả hai, phân cách "; ").
    """
    reasons = []
    for tier, flags in zip(solution["tier"], solution["penalty_flags"]):
        parts = []
        if tier in SURVEY_WARNING_TIERS:
            parts.append(f"tier={tier}")
        if SURVEY_WARNING_FLAGS <= _flags_set(flags):
            parts.append(f"flags={_FLAGS_LABEL}")
        reasons.append("; ".join(parts))
    # Giữ index gốc để dòng cảnh báo truy ngược được về dòng nghiệm tương ứng.
    out = solution.loc[[bool(r) for r in reasons]].copy()
    out["survey_reason"] = [r for r in reasons if r]
    return out


def penalty_breakdown(solution: pd.DataFrame) -> pd.DataFrame:
    """Phân rã điểm chọn theo (``capex_class`` × ``penalty_flags``) — nghĩa vụ §10-2.

    ``penalty_flags`` chuẩn hoá thành tuple đã sort (["B","A"] và ["A","B"] là cùng
    một tổ hợp đất, không được tách nhóm), rỗng/None -> ``"(none)"`` để nhóm "đất
    sạch" hiện rõ trong bảng thay vì thành NaN bị groupby nuốt mất.

    Trả về cột ``n`` và ``share`` (n / tổng số điểm chọn), sort ``n`` giảm dần.
    """
    cols = ["capex_class", "penalty_flags", "n", "share"]
    if solution.empty:
        # Không chia cho 0; bảng rỗng vẫn giữ schema để report ghép không vỡ.
        return pd.DataFrame(columns=cols)
    keys = pd.DataFrame(
        {
            "capex_class": solution["capex_class"].to_numpy(),
            "penalty_flags": [tuple(sorted(_flags_set(v))) or "(none)" for v in solution["penalty_flags"]],
        }
    )
    # sort=False: cột key trộn tuple với str "(none)" — để pandas sort key sẽ nổ
    # TypeError khi so tuple < str; thứ tự cuối cùng do sort theo n quyết định.
    out = keys.groupby(cols[:2], sort=False, dropna=False).size().rename("n").reset_index()
    out["share"] = out["n"] / len(solution)
    return out.sort_values("n", ascending=False, kind="stable").reset_index(drop=True)


def _fmt_lam(lam: float) -> str:
    """0.0 -> "0" vì hợp đồng viết λ ∈ {0, 1, 3}; λ lẻ (0.5) giữ nguyên dạng thập phân."""
    return str(int(lam)) if lam.is_integer() else str(lam)


def _shift(a: set, b: set) -> float:
    """Độ lệch tập chọn = 1 − |A∩B| / max(|A|,|B|).

    Dùng max chứ không min: nghiệm λ này là tập con thật sự của nghiệm λ kia vẫn phải
    tính là lệch (min sẽ cho 0 — che mất việc penalty đã đuổi bớt điểm khỏi nghiệm).
    """
    denom = max(len(a), len(b))
    if denom == 0:
        return 0.0  # cả hai rỗng: không có nghiệm nào để mà lệch
    return 1.0 - len(a & b) / denom


def lambda_sensitivity(selected_by_lambda: Mapping[float, Iterable[str]]) -> dict:
    """Gate sensitivity λ trước khi công bố số — nghĩa vụ §10-3.

    Vì sao λ=0 và λ=1 là bắt buộc (thiếu -> ValueError): cặp này chính là phép đo
    "penalty có đang bẻ nghiệm không" — thiếu một trong hai thì gate không tồn tại,
    và trả kết quả "OK" khi chưa đo được là tự lừa mình. λ=3 thiếu chỉ bị liệt kê
    vào ``missing_lambdas`` (mất độ nhạy phần đuôi, không mất gate).

    Trả về dict: ``shift`` ("0-1" + mọi cặp λ kề nhau có mặt), ``sizes``,
    ``missing_lambdas``, ``verdict`` ("STOP" nếu shift 0-1 > SENSITIVITY_MAX_SHIFT),
    ``message`` tiếng Việt sẵn cho report.
    """
    sets = {float(lam): {str(c) for c in ids} for lam, ids in selected_by_lambda.items()}
    missing_required = sorted({0.0, 1.0} - sets.keys())
    if missing_required:
        raise ValueError(
            f"lambda_sensitivity: thiếu λ bắt buộc {missing_required} — gate công bố so λ=0 vs λ=1, "
            f"hợp đồng §10 yêu cầu chạy đủ λ ∈ {LAMBDA_SENSITIVITY} trên cùng candidate set."
        )
    lams = sorted(sets)
    # "0-1" đứng đầu vì đó là con số gate; các cặp kề nhau còn lại cho thấy nghiệm
    # trôi dần theo λ hay gãy đột ngột ở một khúc.
    shift = {"0-1": _shift(sets[0.0], sets[1.0])}
    for a, b in zip(lams, lams[1:]):
        shift.setdefault(f"{_fmt_lam(a)}-{_fmt_lam(b)}", _shift(sets[a], sets[b]))
    shift01 = shift["0-1"]
    missing = [lam for lam in LAMBDA_SENSITIVITY if lam not in sets]
    if shift01 > SENSITIVITY_MAX_SHIFT:
        verdict = "STOP"
        message = (
            f"DỪNG và báo lại — không công bố số: tập chọn lệch {shift01:.1%} > "
            f"{SENSITIVITY_MAX_SHIFT:.0%} giữa λ=0 và λ=1, tức penalty đang chi phối nghiệm "
            f"hơn cả demand. Soát lại trọng số penalty ở §4 candidate-sites.md trước khi chốt."
        )
    else:
        verdict = "OK"
        message = (
            f"OK — tập chọn lệch {shift01:.1%} ≤ {SENSITIVITY_MAX_SHIFT:.0%} giữa λ=0 và λ=1; "
            f"penalty không chi phối nghiệm, được phép công bố số."
        )
        if missing:
            message += f" Lưu ý: chưa chạy λ = {missing} trong bộ bắt buộc {LAMBDA_SENSITIVITY}."
    return {
        "shift": shift,
        "sizes": {lam: len(sets[lam]) for lam in lams},
        "missing_lambdas": missing,
        "verdict": verdict,
        "message": message,
    }
