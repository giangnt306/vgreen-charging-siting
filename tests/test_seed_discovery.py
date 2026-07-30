"""L10 — che do seed co dich tu registry official phai nam TRONG repo va tat dinh.

Loi goc (29/07): `evcs_stations_2026-07-29-new.csv` mang cot `is_new` ma `FIELDS` khong
co, va khong entrypoint nao trong repo sinh duoc no — 298 tram (canonical 19.507 -> 19.805)
bi dong bang vao MANIFEST ma khong tai sinh duoc. Cac test duoi khoa phan TAT DINH cua
quy trinh (chon seed), phan can mang khong test o day.
"""

import pandas as pd
import pytest

from ev_siting.data.evcs.evcs_enumerate import FIELDS, FIELDS_SEED, seed_targets_from_official


def _registry(rows):
    cols = ["store_id", "lat", "lng", "charging_status"]
    return pd.DataFrame(rows, columns=cols)


BASE = [
    ("C.NEW1", 21.0, 105.8, "ACTIVE"),
    ("C.NEW2", 10.8, 106.7, "BUSY"),
    ("C.OLD1", 21.1, 105.9, "ACTIVE"),  # da co trong catalog
    ("C.PIPE", 16.0, 108.0, "UNAVAILABLE"),  # chua mo -> chua the co tren evcs
    ("C.DEAD", 16.1, 108.1, "INACTIVE"),
]


def test_seed_only_live_stores_absent_from_catalog():
    seeds = seed_targets_from_official(_registry(BASE), known_codes={"C.OLD1"})
    assert [s for s, _, _ in seeds] == ["C.NEW1", "C.NEW2"]


def test_seed_is_deterministic_and_sorted():
    """Tat dinh la dieu kien de tai lap: cung (registry, catalog) -> cung tap truy van."""
    reg = _registry(list(reversed(BASE)))
    a = seed_targets_from_official(reg, known_codes=set())
    b = seed_targets_from_official(_registry(BASE), known_codes=set())
    assert a == b == sorted(a)


def test_seed_drops_rows_outside_vietnam_bbox_and_bad_coords():
    reg = _registry(
        [
            ("C.FAR", 40.0, 116.0, "ACTIVE"),  # Bac Kinh
            ("C.NAN", None, 105.0, "ACTIVE"),
            ("C.OKE", 21.0, 105.8, "ACTIVE"),
        ]
    )
    assert [s for s, _, _ in seed_targets_from_official(reg, known_codes=set())] == ["C.OKE"]


def test_seed_ignores_whitespace_in_known_codes():
    seeds = seed_targets_from_official(_registry(BASE), known_codes={" C.NEW1 ", "C.OLD1", ""})
    assert [s for s, _, _ in seeds] == ["C.NEW2"]


def test_seed_output_schema_adds_is_new_without_touching_grid_scan_schema():
    """`is_new` chi ton tai o che do seed — khong doi schema 3 tab quet luoi."""
    assert "is_new" not in FIELDS
    assert FIELDS_SEED == FIELDS + ["is_new"]


def test_empty_registry_yields_no_seed_rather_than_crashing():
    assert seed_targets_from_official(_registry([]), known_codes=set()) == []


@pytest.mark.parametrize("status", ["UNAVAILABLE", "INACTIVE", "OUTOFSERVICE"])
def test_non_live_registry_status_is_not_a_seed(status):
    reg = _registry([("C.X", 21.0, 105.8, status)])
    assert seed_targets_from_official(reg, known_codes=set()) == []
