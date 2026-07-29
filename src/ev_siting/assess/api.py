"""B7 — pilot API quanh hồ sơ thẩm định (deliverable v1).

Yêu cầu BO nguyên văn: *"tích hợp qua **API** hoặc bản đồ/dashboard, tuỳ định hướng"* ⇒
API-first, chưa xây UI. Và sau khi T1 fail, phạm vi B7 đổi: pilot phục vụ **hồ sơ facts**,
**không** phải endpoint trả điểm số (backlog, cập nhật 28/07).

Ba cửa, đúng ba cách BO thật sự làm việc:

* ``POST /dossier``          — một điểm, JSON đầy đủ (cho tích hợp phần mềm);
* ``POST /dossier/markdown`` — một điểm, một trang đọc được (dán vào mail/Zalo);
* ``POST /dossier/batch``    — **CSV vào, CSV ra** (workflow Excel-ish; đây là giao diện
  pilot thật, không phải cái để trình diễn).

Bất biến được ép ở tầng này, không chỉ ở tầng dưới:

1. Không response nào được mang ``score``/``tier`` — ``_assert_no_score`` chặn trước khi trả;
2. Mọi response mang ``data_version`` · ``model_version`` · ``calibration`` (bất biến §4.4);
3. Ngữ cảnh dựng **một lần** lúc khởi động — đọc bundle frozen + cache occupancy là việc đắt,
   không được xảy ra mỗi request.

Chạy::

    uv run uvicorn ev_siting.assess.api:app --host 127.0.0.1 --port 8000
    curl -s -X POST localhost:8000/dossier -H 'content-type: application/json' \\
         -d '{"lat":21.0278,"lng":105.8342,"point_id":"HS-0001"}' | jq .verdict
    curl -s -X POST localhost:8000/dossier/batch -H 'content-type: text/csv' \\
         --data-binary @points.csv -o scored.csv
"""

from __future__ import annotations

import io

import pandas as pd
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ev_siting.assess import dossier, params

#: Khoá không bao giờ được xuất hiện trong response (v1 bỏ điểm số + tier "Từ chối").
_FORBIDDEN = ("score", "score_total", "score_n", "score_v", "tier")

app = FastAPI(
    title="Hồ sơ thẩm định vị trí trạm sạc",
    version=dossier.MODEL_VERSION,
    description=(
        "Tổng hợp dữ liệu quanh một vị trí đề xuất — thay việc tra tay 30–60 phút/hồ sơ. "
        "**Không** dự đoán doanh thu, **không** chấm điểm, **không** tự từ chối: máy đưa facts, người quyết."
    ),
)

_CTX: dossier.DossierContext | None = None


def get_context() -> dossier.DossierContext:
    """Ngữ cảnh dùng chung (lazy) — bundle frozen + cache occupancy + benchmark định cỡ."""
    global _CTX
    if _CTX is None:
        _CTX = dossier.build_context()
    return _CTX


class Point(BaseModel):
    lat: float = Field(..., ge=-90, le=90, examples=[21.0278])
    lng: float = Field(..., ge=-180, le=180, examples=[105.8342])
    point_id: str = Field("HS-0001", examples=["HS-0141"])


def _assert_no_score(payload) -> None:
    """Chặn rò điểm số ở tầng biên — kiểm cấu trúc, không kiểm chuỗi con.

    (Chuỗi con sẽ bắt nhầm ``n_score``… và bỏ sót ``{"a": {"score": …}}``.)
    """
    stack = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            bad = [k for k in node if str(k).lower() in _FORBIDDEN]
            if bad:
                raise HTTPException(500, f"vi phạm hợp đồng v1: response mang {bad}")
            stack.extend(node.values())
        elif isinstance(node, (list, tuple)):
            stack.extend(node)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model_version": dossier.MODEL_VERSION,
        "data_version": params.DATA_VERSION,
        "calibration": params.CALIBRATION_LABEL,
        "context_loaded": _CTX is not None,
        "contract": "facts-only — không điểm số, không tự từ chối",
    }


@app.post("/dossier")
def post_dossier(pt: Point) -> dict:
    d = dossier.make_dossier(pt.lat, pt.lng, get_context(), point_id=pt.point_id)
    _assert_no_score(d)
    return d


@app.post("/dossier/markdown", response_class=PlainTextResponse)
def post_dossier_markdown(pt: Point) -> str:
    d = dossier.make_dossier(pt.lat, pt.lng, get_context(), point_id=pt.point_id)
    _assert_no_score(d)
    return dossier.render_markdown(d)


@app.post("/dossier/batch", response_class=PlainTextResponse)
def post_dossier_batch(csv_text: str = Body(..., media_type="text/csv")) -> str:
    """CSV (cột ``lat``,``lng``[,``point_id``]) vào — CSV bảng phẳng ra."""
    try:
        pts = pd.read_csv(io.StringIO(csv_text))
    except Exception as e:
        raise HTTPException(400, f"không đọc được CSV: {e}") from e
    missing = {"lat", "lng"} - set(pts.columns)
    if missing:
        raise HTTPException(400, f"CSV thiếu cột {sorted(missing)}")
    if pts.empty:
        raise HTTPException(400, "CSV rỗng")

    tab = dossier.batch(pts, get_context())
    _assert_no_score(tab.to_dict(orient="records"))
    return tab.to_csv(index=False)
