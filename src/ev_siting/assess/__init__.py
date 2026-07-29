"""Máy thẩm định vị trí trạm sạc — assess(P) (Mode A, Sprint 2 B2/B3/B4).

Trả lời "vị trí NPP nộp có nên duyệt không, vì sao" bằng tier + score 2 trục +
reasons có mã. Solver MCLP về sau là *client* của kernel này, không phải ngược lại.

Nguồn chân lý tham số: evcs-dataset/docs/sprint2/prereg-assess-v0.md (ký 2026-07-28),
mirror 1-1 ở `params.py` — đổi giá trị = Addendum pre-reg, không đổi ngầm.

Phân vai với `ev_siting.models.assess` (đừng nhầm): bên đó là nghĩa vụ báo cáo §10
cho *nghiệm MCLP* (survey warnings, phân rã penalty, λ-gate); bên này chấm *điểm nộp vào*.
"""
