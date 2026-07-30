"""Khoá lớp `settlement`: vùng tập trung dân cư (DEGURBA) + cờ pop vô lý.

Hai thứ `demand_h3` KHÔNG nói được nếu chỉ có cột `pop` thô, và đều đã cắn vào sản phẩm:

* Một ô 29.337 người giữa **80,2% mặt nước** (10,036N 104,558E — bản 2025 nói 67 người)
  trông y hệt một ô 29.337 người trong lõi TP.HCM. Bản 2020 có **18 "đô thị" chỉ gồm ĐÚNG
  1 Ô** rải rác rừng núi phía Bắc, mỗi ô 5.000–14.685 người trong khi bản 2025 nói 85–1.372.
  Bản 2025 có **0** cụm 1-ô.
* 250 điểm candidate T4 từng được sinh ra từ những ô đó — bộ lọc `buildable` chỉ chặn
  757/4.365, phần lớn ô rừng núi vẫn "buildable".
"""

import numpy as np
import pandas as pd
import pytest

from ev_siting.data.worldpop.settlement import (
    DENS_URBAN_CENTRE,
    MIN_POP_CENTRE,
    classify,
    connected_clusters,
    land_support,
    neighbourhood_sum,
)


def _ring(centre="8865b56601fffff", k=1):
    import h3

    return list(h3.grid_disk(centre, k))


def test_neighbourhood_sum_dilutes_a_single_cell_spike():
    """Lý do tồn tại của `pop_k1`: cục 1-ô bị pha loãng, vùng đô thị thật thì không.

    R của MCLP là 3 km còn ô res 8 chỉ d = 0,98 km ⇒ độ phân giải 1-ô là **giả**.
    """
    cells = _ring()
    spike = np.zeros(len(cells))
    spike[0] = 30_000.0  # cục artefact, hàng xóm trống trơn
    real = np.full(len(cells), 30_000.0 / 7)  # cùng tổng dân, nhưng trải đều
    s_spike = neighbourhood_sum(cells, spike)[0]
    s_real = neighbourhood_sum(cells, real)[0]
    assert s_spike == pytest.approx(s_real)
    # tại ô trung tâm hai bên bằng nhau — nhưng giá trị THÔ thì lệch 7 lần
    assert spike[0] / real[0] == pytest.approx(7.0)


def test_neighbourhood_sum_treats_missing_neighbours_as_zero():
    cells = ["8865b56601fffff"]  # không có hàng xóm nào trong lưới
    assert neighbourhood_sum(cells, [5.0])[0] == pytest.approx(5.0)


def test_nan_pop_is_not_counted_as_population():
    """NaN = nguồn không phủ ô (E-DQ8). Nó KHÔNG được thành 0 rồi cộng, cũng không lan NaN."""
    cells = _ring()
    vals = [np.nan] * len(cells)
    vals[0] = 100.0
    out = neighbourhood_sum(cells, vals)
    assert np.isfinite(out).all() and out[0] == pytest.approx(100.0)


def test_connected_clusters_separates_disjoint_blobs():
    import h3

    a = "8865b56601fffff"
    b = h3.latlng_to_cell(21.0, 105.8, 8)  # cách xa hàng trăm km
    cells = _ring(a) + _ring(b)
    mask = np.ones(len(cells), dtype=bool)
    lab = connected_clusters(cells, mask)
    assert len(set(lab)) == 2, "hai blob rời nhau phải là hai cụm"


def test_isolated_spike_is_visible_as_one_cell_cluster():
    """Cụm `n_cells == 1` là dấu hiệu artefact — phải NHÌN THẤY được, không bị chôn."""
    cells = _ring()
    pop = np.zeros(len(cells))
    pop[0] = 30_000.0
    out = classify(cells, pop)
    row = out.iloc[0]
    assert row["cluster_n_cells"] == 1
    assert row["dens_ppkm2"] > DENS_URBAN_CENTRE
    # 30k < 50k nên KHÔNG được lên hạng URBAN_CENTRE chỉ vì mật độ cao
    assert row["settlement_class"] == "URBAN_CLUSTER"


def test_contiguous_dense_area_becomes_urban_centre():
    cells = _ring(k=2)  # 19 ô
    area_km2 = 0.85
    pop = np.full(len(cells), max(MIN_POP_CENTRE / len(cells), DENS_URBAN_CENTRE * area_km2) + 1)
    out = classify(cells, pop)
    assert (out["settlement_class"] == "URBAN_CENTRE").all()
    assert out["cluster_n_cells"].iloc[0] == len(cells)


def test_cluster_id_zero_is_the_largest_cluster():
    import h3

    a, b = "8865b56601fffff", h3.latlng_to_cell(21.0, 105.8, 8)
    cells = _ring(a, k=2) + _ring(b, k=1)
    pop = np.array([9000.0] * 19 + [9000.0] * 7)
    out = classify(cells, pop).set_index("h3_r8")
    assert out.loc[a, "cluster_id"] == 0
    assert out.loc[a, "cluster_pop"] > out.loc[b, "cluster_pop"]


def test_land_support_flags_water_and_bare_ground():
    """Hai ca thật quan sát trên bản 2020 (đo 2026-07-29)."""
    lu = pd.DataFrame(
        {
            "frac_water": [0.802, 0.000, 0.000, 0.900],
            "built_up_frac": [0.019, 0.013, 0.900, 0.010],
        }
    )
    pop = [29336.8, 14391.7, 50000.0, 10.0]
    f = land_support(pop, lu)
    assert f.loc[0, "pop_on_water"] and f.loc[0, "pop_unsupported"]  # 80% nước, 29k người
    assert f.loc[1, "pop_no_built"] and f.loc[1, "pop_unsupported"]  # rừng, 14k người
    assert not f.loc[2, "pop_unsupported"], "ô đô thị thật (90% đã xây) không được gắn cờ"
    assert not f.loc[3, "pop_unsupported"], "10 người trên hồ là bình thường, không phải artefact"


def test_flag_never_mutates_pop():
    """Chính sách giống E-DQ1: gắn cờ, KHÔNG sửa. Không có nguồn thẩm quyền để phân bổ lại."""
    lu = pd.DataFrame({"frac_water": [0.9], "built_up_frac": [0.0]})
    pop = pd.Series([9999.0])
    land_support(pop, lu)
    assert pop.iloc[0] == 9999.0


def test_gapfill_excludes_unsupported_cells():
    """Cổng cuối: artefact dân số không được biến thành điểm ĐỀ XUẤT XÂY."""
    from ev_siting.data.worldpop.paths import SETTLEMENT_H3
    from ev_siting.features.paths import CANDIDATE_SITES

    if not (SETTLEMENT_H3.exists() and CANDIDATE_SITES.exists()):
        pytest.skip("chưa có artefact")
    d = pd.read_parquet(SETTLEMENT_H3, columns=["h3_r8", "pop_unsupported"])
    bad = set(d.loc[d["pop_unsupported"].fillna(False), "h3_r8"])
    c = pd.read_parquet(CANDIDATE_SITES, columns=["h3_r8", "tier"])
    leak = c[(c["tier"] == "T4") & c["h3_r8"].isin(bad)]
    assert len(leak) == 0, f"{len(leak)} điểm T4 sinh từ ô pop_unsupported (trước khi vá: 250)"
