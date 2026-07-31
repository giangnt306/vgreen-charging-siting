"""Tests cho tầng LIVE suy từ `connectors` (gỡ bản sao khỏi `stations`, 31/07).

Bài học nền: `stations` từng giữ bản sao 5 cột LIVE cạnh bảng `connectors`. Bản sao
KHÔNG có cổng đối soát, nên khi P7 sửa chuẩn cắm 20–22 kW (AC → DC CCS2) ở `connectors`
thì `stations.connector_types` giữ nguyên nhãn AC cũ — 1.579 trạm tự mâu thuẫn trong
chính dòng của nó, không ai báo. Các test dưới đây khoá lại cả hai chiều:
suy đúng (§1–3) và **không cho bản sao quay lại** (§4).
"""

import pandas as pd
import pytest

from ev_siting.data.evcs.connector_rollup import LIVE_COLS, attach, rollup


def _conn(station_id, power_kw, current_type, label, count_total=1):
    return {"station_id": station_id, "power_kw": power_kw,
            "current_type": current_type, "connector_label": label,
            "count_total": count_total}


def test_rollup_scalars():
    cn = pd.DataFrame([
        _conn("s1", 60.0, "DC", "DC-60kW", count_total=2),
        _conn("s1", 11.0, "AC", "AC-11kW", count_total=1),
        _conn("s2", 11.0, "AC", "AC-11kW", count_total=4),
    ])
    out = rollup(cn)
    assert out.loc["s1", "num_connectors"] == 3           # 2 + 1, KHÔNG phải số dòng
    assert out.loc["s1", "max_power_kw"] == 60.0
    assert out.loc["s1", "total_power_kw"] == 60.0 * 2 + 11.0   # Σ(kW × số súng)
    assert out.loc["s1", "current_type"] == "MIXED"       # có cả AC lẫn DC
    assert out.loc["s2", "current_type"] == "AC"
    assert out.loc["s2", "num_connectors"] == 4


def test_connector_types_is_distinct_labels_not_per_gun():
    """`connector_types` là danh sách LOẠI phân biệt ⇒ len ≤ num_connectors.
    Nhầm chỗ này là nguồn gốc của 'lệch 5.140 dòng' khi đối soát sai cách."""
    cn = pd.DataFrame([_conn("s1", 11.0, "AC", "AC-11kW", count_total=7)])
    out = rollup(cn)
    assert out.loc["s1", "connector_types"] == ["AC-11kW"]
    assert len(out.loc["s1", "connector_types"]) < out.loc["s1", "num_connectors"]


def test_attach_station_without_connectors_gets_zero_not_nan():
    """E-DQ4: `num_connectors = 0` là giá trị LIVE **đúng** (0 súng đang báo cáo),
    không phải thiếu dữ liệu ⇒ không được để NaN."""
    st = pd.DataFrame([{"station_id": "s1"}, {"station_id": "ghost"}])
    cn = pd.DataFrame([_conn("s1", 11.0, "AC", "AC-11kW")])
    out = attach(st, cn).set_index("station_id")
    assert out.loc["ghost", "num_connectors"] == 0
    assert out.loc["ghost", "connector_types"] == []
    assert pd.isna(out.loc["ghost", "current_type"])
    assert out.loc["s1", "num_connectors"] == 1


def test_attach_does_not_mutate_input():
    st = pd.DataFrame([{"station_id": "s1"}])
    cn = pd.DataFrame([_conn("s1", 11.0, "AC", "AC-11kW")])
    attach(st, cn)
    assert list(st.columns) == ["station_id"]


# --------------------------------------------------------------------------- #
# §4 — cổng hồi quy trên ARTEFACT THẬT: bản sao không được quay lại            #
# --------------------------------------------------------------------------- #

def _stations():
    from ev_siting.data.evcs.paths import STATIONS_DIR
    if not STATIONS_DIR.exists():
        pytest.skip("chưa có canonical/stations")
    return pd.read_parquet(STATIONS_DIR)


def _connectors():
    from ev_siting.data.evcs.paths import CONNECTORS_DIR
    if not CONNECTORS_DIR.exists():
        pytest.skip("chưa có canonical/connectors")
    return pd.read_parquet(CONNECTORS_DIR)


def test_stations_artifact_has_no_live_copy():
    """Bản sao LIVE ở `stations` = mầm lệch của P7. Cấm quay lại."""
    dup = sorted(set(LIVE_COLS) & set(_stations().columns))
    assert not dup, f"cột LIVE đã quay lại `stations`: {dup} — nguồn chân lý là `connectors`"


def test_asset_layer_stays_on_stations():
    """Đối trọng của test trên: tầng ASSET (E-DQ4) **không** suy được từ `connectors`
    (Σ súng LẮP ĐẶT > Σ count_total), nên nó phải Ở LẠI `stations`."""
    st = _stations()
    for c in ("n_guns_installed", "site_power_kw", "current_type_asset", "config_src"):
        assert c in st.columns, f"mất cột ASSET {c} — không tái tạo được từ connectors"


def test_rollup_reproduces_supply_totals():
    """Σ số súng ĐANG BÁO CÁO suy từ connectors phải khớp Σ count_total."""
    cn = _connectors()
    assert int(rollup(cn)["num_connectors"].sum()) == int(cn["count_total"].sum())
