"""Test kernel không gian assess() — golden BẰNG CONSTRUCTION, không tính tay hex.

Chiến thuật: pop được đặt vào ĐÚNG các ô lấy từ chính ``_coverage_cells`` của từng
trạm/điểm, nên kỳ vọng (marginal = 0, marginal = đủ pop, ...) đúng theo định nghĩa
tập hợp chứ không phụ thuộc hình dạng lưới H3 — test sống sót khi đổi resolution.
Khoảng cách đối chiếu qua ``aoi.haversine_km`` (bất biến C10 + một bán kính Trái Đất).
"""

import h3
import numpy as np
import pandas as pd
import pytest

from ev_siting.aoi import EARTH_R_KM, haversine_km
from ev_siting.assess import kernel, params
from ev_siting.features.build_candidates import _coverage_cells

# Trạm A tâm Hà Nội; B cách A ~2 km (trong R, ngoài comp); C cách A >13 km (>2R+buffer).
LAT_A, LNG_A = 21.0278, 105.8342
LAT_C, LNG_C = 21.15, 105.8342
# Điểm F cách mọi trạm >40 km — chắc chắn ngoài 2R nên phủ của F rời hẳn phủ mạng.
LAT_F, LNG_F = 20.75, 105.5

POP_A, POP_C, POP_F = 300.0, 300.0, 500.0


def _lng_offset(lat, lng, km):
    """Dịch đông-tây ~km theo cùng EARTH_R_KM — offset xấp xỉ, test luôn đo lại bằng haversine."""
    return lng + km / (np.pi / 180.0 * EARTH_R_KM * np.cos(np.radians(lat)))


LNG_B = _lng_offset(LAT_A, LNG_A, 2.0)


@pytest.fixture(scope="module")
def covered0():
    df = pd.DataFrame(
        {
            "station_id": ["st-a", "st-b", "st-c"],
            "lat": [LAT_A, LAT_A, LAT_C],
            "lng": [LNG_A, LNG_B, LNG_C],
            "num_connectors": [2, 4, 8],
        }
    )
    df["h3_r8"] = [h3.latlng_to_cell(la, ln, 8) for la, ln in zip(df["lat"], df["lng"])]
    return df


@pytest.fixture(scope="module")
def demand(covered0):
    """Pop đặt vào ô lấy từ chính _coverage_cells: A giữ POP_A, C giữ POP_C (ngoài phủ A/B), F giữ POP_F."""
    cell_a, cell_b, cell_c = covered0["h3_r8"]
    cov_a = _coverage_cells(cell_a, params.R_SERVICE_KM)
    cov_ab = cov_a | _coverage_cells(cell_b, params.R_SERVICE_KM)
    cells_a = sorted(cov_a)[:3]
    # Ô của C phải nằm NGOÀI phủ A∪B để pop này thuộc riêng vùng C — khi exclude C
    # nó quay lại thành biên nguyên vẹn (test #3), không bị A/B "đỡ" mất.
    cells_c = sorted(_coverage_cells(cell_c, params.R_SERVICE_KM) - cov_ab)[:3]
    assert len(cells_c) == 3, "C phải đủ xa để có ô riêng — layout fixture sai"
    cell_f = h3.latlng_to_cell(LAT_F, LNG_F, 8)
    return pd.DataFrame(
        {
            "h3_r8": cells_a + cells_c + [cell_f],
            "pop": [POP_A / 3] * 3 + [POP_C / 3] * 3 + [POP_F],
        }
    )


@pytest.fixture(scope="module")
def ctx(covered0):
    return kernel.build_network(covered0)


@pytest.fixture(scope="module")
def dem(demand):
    return kernel.demand_series(demand)


def test_marginal_zero_at_existing_station(ctx, dem):
    # Điểm trùng toạ độ trạm A ⇒ Cov(p) ≡ Cov(cell A) ⊆ phủ mạng (C10: cùng kernel)
    # ⇒ không còn ô tự do, biên phải bằng 0 tuyệt đối dù local > 0.
    cells = kernel.point_cells(LAT_A, LNG_A)
    assert kernel.marginal_pop(cells, ctx, dem) == 0.0
    assert kernel.local_pop(cells, dem) == pytest.approx(POP_A)


def test_far_point_gets_full_pop(ctx, dem):
    # F cách mọi trạm >2R nên phủ của F rời phủ mạng ⇒ biên = local = đủ POP_F.
    cells = kernel.point_cells(LAT_F, LNG_F)
    assert kernel.marginal_pop(cells, ctx, dem) == pytest.approx(POP_F)
    assert kernel.local_pop(cells, dem) == pytest.approx(POP_F)


def test_exclude_station_restores_marginal(covered0, ctx, dem):
    # Retrodiction: purge C khỏi nền ⇒ pop vùng riêng của C thành biên trở lại.
    cells_c = kernel.point_cells(LAT_C, LNG_C)
    assert kernel.marginal_pop(cells_c, ctx, dem) == 0.0  # mạng đủ: C tự phủ vùng mình
    ctx2 = kernel.build_network(covered0, exclude_station_ids=["st-c", "ghost-id"], mode="retrodiction")
    assert ctx2.n_excluded == 1  # "ghost-id" không có trong covered0 — chỉ đếm khớp thực tế
    assert ctx2.mode == "retrodiction"
    assert kernel.marginal_pop(cells_c, ctx2, dem) == pytest.approx(POP_C)


def test_d_nearest_matches_haversine(ctx):
    # BallTree (radians × EARTH_R_KM) phải khớp aoi.haversine_km từng mét —
    # nếu lệch nghĩa là hai bán kính Trái Đất khác nhau đã lọt vào repo.
    q_lat, q_lng = LAT_A + 0.004, LNG_A - 0.006
    info = kernel.nearest_info(ctx, np.array([q_lat]), np.array([q_lng]))
    expected_m = (
        min(haversine_km(q_lat, q_lng, la, ln) for la, ln in [(LAT_A, LNG_A), (LAT_A, LNG_B), (LAT_C, LNG_C)]) * 1000.0
    )
    assert info["d_nearest_m"][0] == pytest.approx(expected_m, rel=1e-6)


def test_competition_count_at_1km_boundary(ctx):
    # Hai điểm kẹp biên comp=1 km về phía TÂY của A (B nằm đông nên không nhiễu):
    # ~0,9 km ⇒ đếm 1 trạm; ~1,2 km ⇒ 0 trạm. Đo lại offset bằng haversine để
    # test không phụ thuộc xấp xỉ độ-ra-km.
    p_in = (LAT_A, _lng_offset(LAT_A, LNG_A, -0.9))
    p_out = (LAT_A, _lng_offset(LAT_A, LNG_A, -1.2))
    assert 0.85 < haversine_km(*p_in, LAT_A, LNG_A) < 0.95
    assert 1.15 < haversine_km(*p_out, LAT_A, LNG_A) < 1.25
    info = kernel.nearest_info(ctx, np.array([p_in[0], p_out[0]]), np.array([p_in[1], p_out[1]]))
    assert list(info["n_within_comp"]) == [1, 0]


def test_connectors_within_r(ctx):
    # Tại A: A (0 km) + B (~2 km) trong R=3 ⇒ 2+4; C (>13 km) ngoài. Tại C: chỉ C ⇒ 8.
    info = kernel.nearest_info(ctx, np.array([LAT_A, LAT_C]), np.array([LNG_A, LNG_C]))
    assert list(info["connectors_within_r"]) == [6.0, 8.0]
    ids_at_a = set(ctx.stations["station_id"].to_numpy()[info["idx_within_r"][0]])
    assert ids_at_a == {"st-a", "st-b"}


def test_empty_network(covered0, dem):
    # Exclude hết ⇒ mạng rỗng: không được nổ exception — G2/R10 suy từ inf/0,
    # và mọi pop đều là biên (marginal = local).
    ctx0 = kernel.build_network(covered0, exclude_station_ids=list(covered0["station_id"]))
    assert ctx0.tree is None
    assert ctx0.n_excluded == 3
    assert ctx0.covered_cells == frozenset()
    info = kernel.nearest_info(ctx0, np.array([LAT_A]), np.array([LNG_A]))
    assert np.isinf(info["d_nearest_m"][0])
    assert info["n_within_comp"][0] == 0
    assert info["connectors_within_r"][0] == 0.0
    assert len(info["idx_within_r"][0]) == 0
    cells = kernel.point_cells(LAT_A, LNG_A)
    assert kernel.marginal_pop(cells, ctx0, dem) == kernel.local_pop(cells, dem) == pytest.approx(POP_A)
