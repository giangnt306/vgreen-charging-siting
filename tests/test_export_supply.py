"""Khoá ngữ nghĩa của `export_supply` — hai CSV "cung sạch" phải LÀ canonical, không phải bản diễn giải lại.

Bối cảnh: `clean_supply.csv`/`excluded.csv` từng là **ảnh chụp không có producer** và đã
âm thầm lệch 16 dòng so với canonical sau `E-DQ3`. Các test dưới đây khoá đúng những chỗ
làm sai lệch đó có thể quay lại:

  * công thức cung KHÔNG được nới/thắt lặng lẽ (4 điều kiện, mỗi cái phải loại được);
  * mỗi dòng bị loại có **đúng một** lý do, theo thứ tự ưu tiên cố định;
  * `E-DQ1` (placeholder) và `E-DQ3` (ngoài đơn vị hành chính) tuy cùng làm
    `coord_resolved=False` nhưng phải ra **hai** lý do khác nhau — nếu gộp thì lần sau
    không ai biết 16 dòng đó biến đi đâu;
  * và các cổng QA phải **CÓ THỂ FAIL** (5 test cuối chứng minh từng cổng fail được).
"""
import pandas as pd
import pytest

from ev_siting.data.evcs.export_supply import (EXCLUDED_COLS, REASON_LABELS, SUPPLY_COLS,
                                               build, exclusion_reason, report, supply_mask)

CELL = "8830e1c4a9fffff"


def _stations(rows):
    """Khung `stations` tối thiểu — mặc định là một trạm THUỘC tập cung."""
    base = dict(name="Tram T", operator="VinFast", province_code="HNO", h3_r8=CELL,
                lat=21.03, lng=105.85, lat_raw=21.03, lng_raw=105.85,
                current_type="AC", max_power_kw=11.0, num_connectors=1,
                connector_types=["AC-11kW"], vehicle_class="CAR",
                op_status="OPERATIONAL", access="PUBLIC", is_operational=True,
                is_primary=True, coord_resolved=True, quality_flags=[])
    out = []
    for i, r in enumerate(rows):
        rec = dict(base)
        rec.update(r)
        rec.setdefault("station_code", f"C.T{i:04d}")
        rec.setdefault("station_id", f"vn-c-t{i:04d}")
        out.append(rec)
    return pd.DataFrame(out)


# --- công thức cung: cả 4 điều kiện đều phải loại được ------------------------------

@pytest.mark.parametrize("field,value", [
    ("is_operational", False),
    ("access", "UNKNOWN"),
    ("access", "RESTRICTED"),
    ("is_primary", False),
    ("coord_resolved", False),
])
def test_each_condition_drops_a_station(field, value):
    df = _stations([{}, {field: value}])
    assert supply_mask(df).tolist() == [True, False]


def test_supply_row_survives_all_four_conditions():
    assert supply_mask(_stations([{}])).all()


# --- lý do loại: đúng một, theo thứ tự ưu tiên -------------------------------------

def test_every_excluded_row_gets_exactly_one_reason():
    df = _stations([
        {},                                        # cung
        {"is_primary": False},
        {"access": "UNKNOWN"},
        {"is_operational": False, "op_status": "OUT_OF_SERVICE"},
        {"coord_resolved": False, "h3_r8": None},
        {"access": "RESTRICTED"},
    ])
    reason = exclusion_reason(df)
    assert reason.isna().tolist() == [True, False, False, False, False, False]
    assert reason.dropna().tolist() == ["CROSS_SOURCE_DUP", "ACCESS_UNKNOWN",
                                        "OUT_OF_SERVICE", "COORD_PLACEHOLDER", "RESTRICTED"]


def test_reason_precedence_dup_wins_over_the_rest():
    """Một dòng phạm 4 điều kiện vẫn chỉ ghi lý do đầu tiên — nếu không, tổng bị đếm 4 lần."""
    df = _stations([{"is_primary": False, "access": "UNKNOWN",
                     "is_operational": False, "coord_resolved": False}])
    assert exclusion_reason(df).tolist() == ["CROSS_SOURCE_DUP"]


def test_edq1_and_edq3_are_different_reasons():
    """Cùng `coord_resolved=False` nhưng khác nguyên nhân → khác lý do (16 dòng của E-DQ3)."""
    df = _stations([
        {"coord_resolved": False, "quality_flags": ["COORD_PLACEHOLDER"]},
        {"coord_resolved": False, "quality_flags": ["COORD_OUTSIDE_ADMIN"]},
    ])
    assert exclusion_reason(df).tolist() == ["COORD_PLACEHOLDER", "COORD_OUTSIDE_ADMIN"]


def test_missing_quality_flags_falls_back_to_placeholder():
    df = _stations([{"coord_resolved": False, "quality_flags": None}])
    assert exclusion_reason(df).tolist() == ["COORD_PLACEHOLDER"]


# --- hình dạng file xuất ra --------------------------------------------------------

def test_build_shapes_and_column_order():
    supply, excluded = build(_stations([{}, {"is_primary": False}]))
    assert list(supply.columns) == SUPPLY_COLS
    assert list(excluded.columns) == EXCLUDED_COLS
    assert len(supply) == 1 and len(excluded) == 1


def test_connector_types_is_literal_eval_able():
    """Bản 28/07 ghi `['A' 'B']` (str của ndarray) — thiếu dấu phẩy, parse không được."""
    import ast
    supply, _ = build(_stations([{"connector_types": ["DC-30kW", "AC-3.5kW"]}]))
    got = supply.loc[0, "connector_types"]
    assert got == "['DC-30kW', 'AC-3.5kW']"
    assert ast.literal_eval(got) == ["DC-30kW", "AC-3.5kW"]


def test_excluded_is_sorted_by_reason_priority():
    df = _stations([{"access": "RESTRICTED"}, {"is_primary": False}])
    _, excluded = build(df)
    assert excluded["reason"].tolist() == [REASON_LABELS["CROSS_SOURCE_DUP"],
                                          REASON_LABELS["RESTRICTED"]]


# --- các cổng QA phải CÓ THỂ FAIL --------------------------------------------------

def test_all_gates_pass_on_clean_input():
    df = _stations([{}, {"is_primary": False}])
    supply, excluded = build(df)
    rep = report(df, supply, excluded)
    assert rep["all_gates_pass"], rep["gates"]
    assert rep["n_input"] == rep["n_supply"] + rep["n_excluded"]


def test_gate_reconciles_input_fails_when_a_row_is_dropped():
    df = _stations([{}, {}, {"is_primary": False}])
    supply, excluded = build(df)
    rep = report(df, supply.iloc[:1], excluded)          # "quên" 1 dòng cung
    assert rep["gates"]["reconciles_input"] is False
    assert rep["all_gates_pass"] is False


def test_gate_every_excluded_has_reason_fails_on_blank_reason():
    df = _stations([{}, {"is_primary": False}])
    supply, excluded = build(df)
    excluded.loc[0, "reason"] = None
    assert report(df, supply, excluded)["gates"]["every_excluded_has_reason"] is False


def test_gate_reasons_are_known_fails_on_ad_hoc_label():
    df = _stations([{}, {"is_primary": False}])
    supply, excluded = build(df)
    excluded.loc[0, "reason"] = "LY DO TU BIA"
    assert report(df, supply, excluded)["gates"]["reasons_are_known"] is False


def test_gate_pk_unique_fails_on_duplicate_station_id():
    df = _stations([{}, {}])
    supply, excluded = build(df)
    supply.loc[1, "station_id"] = supply.loc[0, "station_id"]
    assert report(df, supply, excluded)["gates"]["pk_unique"] is False


def test_gate_sets_are_disjoint_fails_when_a_row_is_in_both_files():
    df = _stations([{}, {"is_primary": False}])
    supply, excluded = build(df)
    excluded.loc[0, "station_id"] = supply.loc[0, "station_id"]
    assert report(df, supply, excluded)["gates"]["sets_are_disjoint"] is False


def test_gate_supply_has_geometry_fails_on_null_h3():
    df = _stations([{}])
    supply, excluded = build(df)
    supply.loc[0, "h3_r8"] = None
    assert report(df, supply, excluded)["gates"]["supply_has_geometry"] is False
