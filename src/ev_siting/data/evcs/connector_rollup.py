#!/usr/bin/env python3
"""connector_rollup.py — Suy tầng cấu hình **SỐNG** (LIVE) từ bảng `connectors`.

**Vì sao module này tồn tại.** `stations` từng mang 5 cột LIVE
(`num_connectors`/`max_power_kw`/`total_power_kw`/`current_type`/`connector_types`)
song song với bảng `connectors` — cùng một sự thật ở hai nơi. Hệ quả đã xảy ra thật:
bản sửa **P7** (connector 20–22 kW bị power-tier gán nhầm AC → thực tế **DC CCS2**) được
áp cho `connectors` và cho `stations.current_type`, nhưng **quên** `connector_types`, nên
**1.579 trạm** tự mâu thuẫn trong chính dòng của nó (`current_type='DC'` nhưng
`connector_types=['AC-20kW']`). Đó là lỗi kinh điển của denormalize không có cổng.

**Chốt (31/07):** `connectors` là **nguồn chân lý duy nhất** của tầng LIVE. `stations`
không giữ bản sao; consumer nào cần thì gọi `rollup()` — một công thức, một chỗ sửa.

⚠️ **KHÔNG áp dụng cho tầng TÀI SẢN (ASSET, E-DQ4).** `n_guns_installed`/`site_power_kw`/
`nameplate_power_kw`/`current_type_asset` **không** suy được từ `connectors`: `evse_powers`
là mảng trạng thái SỐNG (EVSE tắt thì rời khỏi mảng), nên Σ`count_total` = **62.924** súng
ĐANG BÁO CÁO trong khi tài sản LẮP ĐẶT là **69.174** (chênh 6.250, đo 2026-07-31). Tầng
ASSET do `resolve_config.py` hợp giải official-first và **ở lại** `stations`.
"""
import pandas as pd

#: cột LIVE mà `rollup()` sinh ra — đúng bộ đã gỡ khỏi `stations` ngày 31/07.
LIVE_COLS = ["current_type", "max_power_kw", "total_power_kw",
             "num_connectors", "connector_types"]


def _roll_current(s: pd.Series):
    """AC/DC/MIXED theo đúng quy ước P7 của `transform_canonical`."""
    has_ac, has_dc = (s == "AC").any(), (s == "DC").any()
    return "MIXED" if has_ac and has_dc else ("AC" if has_ac else "DC" if has_dc else None)


def rollup(connectors: pd.DataFrame) -> pd.DataFrame:
    """`connectors` -> DataFrame index `station_id`, 5 cột LIVE.

    Thuần hàm để test được. Trạm KHÔNG có connector sẽ **không** xuất hiện ở đây —
    dùng `attach()` để nhận `num_connectors = 0` (giá trị LIVE **đúng**, E-DQ4) thay vì NaN.
    """
    g = connectors.groupby("station_id", observed=True)
    out = pd.DataFrame({
        "current_type": g["current_type"].apply(_roll_current),
        "max_power_kw": g["power_kw"].max(),
        # tổng công suất = Σ(công suất mỗi súng × số súng cùng loại)
        "total_power_kw": g.apply(
            lambda x: (x["power_kw"] * x["count_total"]).sum(), include_groups=False),
        "num_connectors": g["count_total"].sum().astype("int64"),
        # danh sách LOẠI phân biệt (không phải một phần tử mỗi súng) -> len <= num_connectors
        "connector_types": g["connector_label"].apply(lambda s: sorted(set(s))),
    })
    return out


def attach(stations: pd.DataFrame, connectors: pd.DataFrame,
           cols=None) -> pd.DataFrame:
    """Gắn cột LIVE vào `stations` theo `station_id` (không sửa `stations` gốc).

    Trạm không có connector: `num_connectors = 0`, `connector_types = []`, phần còn lại
    NULL — đúng ngữ nghĩa "0 súng ĐANG BÁO CÁO" của E-DQ4, **không** phải thiếu dữ liệu.
    """
    cols = list(cols) if cols else LIVE_COLS
    live = rollup(connectors)
    out = stations.merge(live[[c for c in cols if c in live.columns]],
                         left_on="station_id", right_index=True, how="left")
    if "num_connectors" in cols:
        out["num_connectors"] = out["num_connectors"].fillna(0).astype("int64")
    if "connector_types" in cols:
        out["connector_types"] = out["connector_types"].apply(
            lambda v: v if isinstance(v, list) else [])
    return out


def load(cols=None) -> pd.DataFrame:
    """Đọc `canonical/connectors` từ đĩa rồi `rollup()` (tiện cho consumer ngoài package)."""
    from .paths import CONNECTORS_DIR
    need = ["station_id", "power_kw", "current_type", "connector_label", "count_total"]
    live = rollup(pd.read_parquet(CONNECTORS_DIR, columns=need))
    return live[[c for c in (cols or LIVE_COLS) if c in live.columns]]
