"""E-DQ4 — khoá ngữ nghĩa CẤU HÌNH: tầng TÀI SẢN vs tầng TRẠNG THÁI SỐNG.

Các test dưới đây khoá đúng những chỗ mà bản cũ sai, để phép sửa không âm thầm quay lại:

  * `num_connectors` là "số súng ĐANG BÁO CÁO", KHÔNG phải "số súng lắp đặt"
    (`build_master_evcs.py:33` ghi sai là "số súng THẬT") → 0 không có nghĩa là
    trạm không có súng.
  * cả evcs LẪN registry đều là chặn DƯỚI → phải HỢP `max()`, không được ghi đè.
  * `total_power_kw` = Σ nameplate từng súng ≠ công suất ĐIỂM sạc: hai hồng trên một
    tủ 180 kW cấp 180 kW, không phải 360 (bậc D).
  * `current_type` suy từ mảng sống sai khi cả một loại dòng điện bị tắt (bậc C).
  * và quan trọng nhất: **các cổng QA phải CÓ THỂ FAIL** — trước E-DQ4 thì
    `INCOMPLETE_CONFIG` chỉ tồn tại dưới dạng comment và `validate.py` không kiểm
    một trường cấu hình nào.
"""
import pandas as pd
import pytest

from ev_siting.data.evcs.resolve_config import (CONFIG_COLS, FLAG_CABINET, FLAG_CT_FIXED,
                                                FLAG_LOWER_BOUND, FLAG_TRUNCATED,
                                                FLAG_UNKNOWN, SRC_EVCS, SRC_OFFICIAL,
                                                SRC_TELEMETRY, SRC_UNKNOWN,
                                                config_report, resolve_config)

CELL = "8830e1c4a9fffff"


def _stations(rows):
    """Khung `stations` tối thiểu (đúng các cột resolve_config/config_report cần)."""
    base = dict(province_code="HNO", station_type="VINFAST_CS", h3_r8=CELL,
                num_connectors=0, max_power_kw=None, total_power_kw=None,
                current_type=None, op_status="OPERATIONAL", access="PUBLIC",
                is_operational=True, is_primary=True, coord_resolved=True,
                quality_flags=[])
    out = []
    for i, r in enumerate(rows):
        rec = dict(base)
        rec.update(r)
        rec.setdefault("station_code", f"C.T{i:04d}")
        rec.setdefault("station_id", f"vn-c-t{i:04d}")
        rec["quality_flags"] = list(rec["quality_flags"])
        out.append(rec)
    return pd.DataFrame(out)


_OFF_COLS = ["off_guns", "off_max_kw", "off_nameplate_kw", "off_site_kw",
             "off_shared", "off_cur"]


def _official(rows):
    """Tầng TÀI SẢN dạng `load_official_config()` trả về (index = store_id).

    `[]` = chưa có registry (đúng nhánh mà `load_official_config` trả khi thiếu file)."""
    if not rows:
        return pd.DataFrame(columns=_OFF_COLS)
    return pd.DataFrame(rows).set_index("store_id")


def _off(store_id, guns, kw, site_kw=None, cur="DC", shared=False):
    return dict(store_id=store_id, off_guns=guns, off_max_kw=kw,
                off_nameplate_kw=kw * guns,
                off_site_kw=kw * guns if site_kw is None else site_kw,
                off_cur=cur, off_shared=shared)


def _flags(out, i=0):
    return set(out["quality_flags"].iloc[i])


# --------------------------------------------------------------------------------------
# bậc A — mảng sống rỗng ≠ trạm không có súng
# --------------------------------------------------------------------------------------

def test_zero_reporting_guns_is_not_zero_installed():
    """Chính ca mà register gọi là `num_connectors=0`: mảng tắt hết, không phải 0 súng."""
    st = _stations([{"station_code": "C.X0001", "num_connectors": 0}])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.X0001", 4, 60.0)]))
    assert out["config_src"].iloc[0] == SRC_OFFICIAL
    assert out["n_guns_installed"].iloc[0] == 4
    assert out["num_connectors"].iloc[0] == 0          # tầng LIVE giữ nguyên, không ghi đè
    assert out["max_power_kw"].iloc[0] is None or pd.isna(out["max_power_kw"].iloc[0])
    assert out["max_power_kw_asset"].iloc[0] == 60.0


def test_no_source_stays_explicitly_unknown_not_zero():
    """257 trạm dư: không nguồn nào điền được → NULL + cờ, KHÔNG điền ngầm số 0/median."""
    st = _stations([{"station_code": "C.X0002", "num_connectors": 0}])
    out = resolve_config(st, pd.Series(dtype="float64"), _official([]))
    assert out["config_src"].iloc[0] == SRC_UNKNOWN
    assert pd.isna(out["n_guns_installed"].iloc[0])
    assert pd.isna(out["site_power_kw"].iloc[0])
    assert out["current_type_asset"].iloc[0] is None
    assert FLAG_UNKNOWN in _flags(out)
    assert not bool(out["config_resolved"].iloc[0])


def test_imputation_never_leaks_into_installed():
    """`n_guns_imputed` chỉ để phân tích độ nhạy — không bao giờ là giá trị mặc định."""
    st = _stations([{"station_code": "C.OK", "num_connectors": 6},
                    {"station_code": "C.NA", "num_connectors": 0}])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.OK", 6, 60.0)])).set_index("station_code")
    assert pd.isna(out.at["C.NA", "n_guns_installed"])
    assert out.at["C.NA", "n_guns_imputed"] == 6          # có gợi ý, nhưng ở cột RIÊNG
    assert out.at["C.NA", "config_src"] == SRC_UNKNOWN


# --------------------------------------------------------------------------------------
# bậc B — truncation: cả hai nguồn là chặn DƯỚI ⇒ hợp max(), không ghi đè
# --------------------------------------------------------------------------------------

def test_truncation_is_flagged_and_unioned():
    """1.568 trạm đọc thiếu; 0 trạm đọc thừa — bất đối xứng một chiều."""
    st = _stations([{"station_code": "C.X0003", "num_connectors": 2}])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.X0003", 8, 60.0)]))
    assert out["n_guns_installed"].iloc[0] == 8
    assert FLAG_TRUNCATED in _flags(out)


def test_union_keeps_the_larger_source_when_evcs_leads():
    """Nếu evcs > registry thì registry mới là bản cũ → `max()`, KHÔNG official-first thô."""
    st = _stations([{"station_code": "C.X0004", "num_connectors": 10}])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.X0004", 4, 60.0)]))
    assert out["n_guns_installed"].iloc[0] == 10
    assert FLAG_TRUNCATED not in _flags(out)


def test_telemetry_is_a_witness_but_only_a_lower_bound():
    """132 mâu thuẫn vật lý: không thể sạc 3 xe cùng lúc trên 0 súng."""
    st = _stations([{"station_code": "C.X0005", "num_connectors": 0}])
    out = resolve_config(st, pd.Series({"C.X0005": 3.0}), _official([]))
    assert out["config_src"].iloc[0] == SRC_TELEMETRY
    assert out["n_guns_installed"].iloc[0] == 3
    # chặn dưới thì KHÔNG được coi là đã đo: resolved=False + cờ tường minh
    assert not bool(out["config_resolved"].iloc[0])
    assert FLAG_LOWER_BOUND in _flags(out)


def test_installed_never_below_observed_max():
    st = _stations([{"station_code": "C.X0006", "num_connectors": 2}])
    out = resolve_config(st, pd.Series({"C.X0006": 5.0}),
                         _official([_off("C.X0006", 4, 60.0)]))
    assert out["n_guns_installed"].iloc[0] == 5


# --------------------------------------------------------------------------------------
# bậc C — current_type suy từ mảng sống sai khi cả một loại dòng điện bị tắt
# --------------------------------------------------------------------------------------

def test_current_type_dc_that_is_really_mixed():
    """521 trạm ghi DC nhưng là MIXED: chính các súng AC là những súng bị thiếu."""
    st = _stations([{"station_code": "C.X0007", "num_connectors": 2, "current_type": "DC"}])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.X0007", 6, 60.0, cur="MIXED")]))
    assert out["current_type"].iloc[0] == "DC"              # LIVE giữ nguyên
    assert out["current_type_asset"].iloc[0] == "MIXED"     # ASSET đúng
    assert FLAG_CT_FIXED in _flags(out)


def test_current_type_asset_falls_back_to_live_without_registry():
    st = _stations([{"station_code": "C.X0008", "num_connectors": 2, "current_type": "AC"}])
    out = resolve_config(st, pd.Series(dtype="float64"), _official([]))
    assert out["config_src"].iloc[0] == SRC_EVCS
    assert out["current_type_asset"].iloc[0] == "AC"
    assert FLAG_CT_FIXED not in _flags(out)


# --------------------------------------------------------------------------------------
# bậc D — công suất ĐIỂM sạc ≠ Σ nameplate từng súng
# --------------------------------------------------------------------------------------

def test_shared_cabinet_site_power_is_not_the_sum_of_guns():
    """Một tủ 180 kW hai hồng cấp 180 kW, không phải 360 (phóng đại 1,82x toàn quốc)."""
    st = _stations([{"station_code": "C.X0009", "num_connectors": 2, "total_power_kw": 360.0}])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.X0009", 2, 180.0, site_kw=180.0, shared=True)]))
    assert out["nameplate_power_kw"].iloc[0] == 360.0
    assert out["site_power_kw"].iloc[0] == 180.0
    assert FLAG_CABINET in _flags(out)


def test_site_power_equals_nameplate_when_no_cabinet_is_shared():
    st = _stations([{"station_code": "C.X0010", "num_connectors": 2}])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.X0010", 2, 60.0, site_kw=120.0)]))
    assert out["site_power_kw"].iloc[0] == out["nameplate_power_kw"].iloc[0] == 120.0
    assert FLAG_CABINET not in _flags(out)


# --------------------------------------------------------------------------------------
# các cổng QA PHẢI CÓ THỂ FAIL (khuôn E-DQ7c/E-DQ7e: cổng không bao giờ FAIL = không có cổng)
# --------------------------------------------------------------------------------------

def _resolved_frame():
    st = _stations([{"station_code": "C.G0001", "num_connectors": 4,
                     "total_power_kw": 240.0, "current_type": "DC"}])
    return resolve_config(st, pd.Series({"C.G0001": 3.0}),
                          _official([_off("C.G0001", 4, 60.0)]))


def test_all_gates_pass_on_a_clean_frame():
    out = _resolved_frame()
    rep = config_report(out, pd.Series({"C.G0001": 3.0}))
    assert rep["all_gates_pass"], rep["gates"]
    assert set(CONFIG_COLS) <= set(out.columns)


def test_gate_guns_ge_observed_max_can_fail():
    """Neo NGOẠI VI — cổng duy nhất bắt được truncation mà không cần nguồn thứ hai."""
    out = _resolved_frame()
    rep = config_report(out, pd.Series({"C.G0001": 9.0}))   # 9 xe cùng lúc trên 4 súng
    assert not rep["gates"]["guns_ge_observed_max"]
    assert not rep["all_gates_pass"]


def test_gate_no_silent_zero_can_fail():
    out = _resolved_frame()
    out.loc[0, "n_guns_installed"] = 0                     # đang vận hành mà 0 súng
    rep = config_report(out, pd.Series({"C.G0001": 0.0}))
    assert not rep["gates"]["no_silent_zero"]


def test_gate_site_power_le_nameplate_can_fail():
    out = _resolved_frame()
    out.loc[0, "site_power_kw"] = out.loc[0, "nameplate_power_kw"] * 2
    rep = config_report(out, pd.Series({"C.G0001": 3.0}))
    assert not rep["gates"]["site_power_le_nameplate"]


def test_gate_unknown_is_explicit_can_fail():
    """Điền ngầm cho dòng UNKNOWN (đúng thứ E-DQ4 cấm) phải làm cổng FAIL."""
    st = _stations([{"station_code": "C.G0002", "num_connectors": 0}])
    out = resolve_config(st, pd.Series(dtype="float64"), _official([]))
    out.loc[0, "n_guns_installed"] = 2                     # điền ngầm
    rep = config_report(out, pd.Series(dtype="float64"))
    assert not rep["gates"]["unknown_is_explicit"]


def test_gate_reporting_le_installed_can_fail():
    out = _resolved_frame()
    out.loc[0, "n_guns_installed"] = 1                     # < num_connectors = 4
    rep = config_report(out, pd.Series({"C.G0001": 0.0}))
    assert not rep["gates"]["reporting_le_installed"]


def test_gate_resolved_rate_can_fail():
    """Ngưỡng đo trên tập CUNG, không trên toàn bảng."""
    st = _stations([{"station_code": f"C.R{i:04d}", "num_connectors": 0} for i in range(4)])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.R0000", 2, 60.0)]))
    rep = config_report(out, pd.Series(dtype="float64"))
    assert rep["supply"]["resolved_rate"] == pytest.approx(0.25)
    assert not rep["gates"]["config_resolved_rate"]


def test_report_publishes_the_excluded_denominator():
    """Chính sách E-DQ8c: dư KHÔNG được đọng thành mẫu số im lặng — phải công bố."""
    st = _stations([{"station_code": "C.D0001", "num_connectors": 4},
                    {"station_code": "C.D0002", "num_connectors": 0}])
    out = resolve_config(st, pd.Series(dtype="float64"),
                         _official([_off("C.D0001", 4, 60.0)]))
    rep = config_report(out, pd.Series(dtype="float64"))
    assert rep["n_unknown"] == 1
    assert rep["supply"]["n_unresolved"] == 1
    assert rep["supply"]["guns_installed"] == 4          # chỉ cộng phần đã resolve
    assert rep["gates"]["row_reconciliation"]
