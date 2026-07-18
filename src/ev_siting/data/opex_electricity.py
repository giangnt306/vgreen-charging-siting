"""OpEx — electricity tariff for EV charging stations (Vietnam).

Biggest OpEx component of a charging station is the electricity it buys from EVN.
Vietnam introduced a *dedicated* retail tariff group for EV charging stations in
2025, so we can source it from public legal documents instead of the company:

  * Cơ cấu (structure, % of average retail price) — Quyết định 14/2025/QĐ-TTg
    (Thủ tướng Chính phủ, ban hành 29/05/2025), mục 3.2 "Giá bán điện cho trạm,
    trụ sạc xe điện". Two voltage groups only (simpler than the industrial tariff):
        - Từ trung áp trở lên (> 1 kV)
        - Hạ áp (<= 1 kV)
    each with 3 time-of-use bands: bình thường / thấp điểm / cao điểm.

  * Giá bán lẻ điện bình quân (base average price the % applies to) — set by EVN,
    published via Quyết định 1279/QĐ-BCT (09/05/2025): 2,204.07 đ/kWh, eff. 10/05/2025.

Why not a raw HTML scraper: EVN publishes the number tables as images, and the
legal % structure lives in decision text — both are (a) low-cardinality and
(b) semi-static (they change only when a new decision is issued). So we encode the
% matrix from the decision (with citation) and treat the base average price as the
single volatile input, refreshable from config / CLI. This is the update path the
problem-analysis doc asks for ("pipeline cần cho phép cập nhật pricing_tiers").

Run:
    python -m ev_siting.data.opex_electricity                 # use default base price
    python -m ev_siting.data.opex_electricity --base-price 2300
Outputs (to data/external/, gitignored — regenerate any time):
    opex_electricity_tariff.csv    tidy table: one row per (voltage_group, tou_band)
    opex_electricity_tariff.json   same data + provenance / source metadata
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Sourced facts (edit only when a new legal decision supersedes these).
# --------------------------------------------------------------------------- #

# Giá bán lẻ điện bình quân — the base the tariff percentages apply to.
# Source: Quyết định 1279/QĐ-BCT (Bộ Công Thương), effective 2025-05-10.
DEFAULT_BASE_AVG_PRICE_VND_KWH: float = 2204.07
BASE_PRICE_SOURCE = "Quyết định 1279/QĐ-BCT (09/05/2025), hiệu lực 10/05/2025"
BASE_PRICE_EFFECTIVE = "2025-05-10"

# Structure: % of the average retail price, per voltage group × time-of-use band.
# Source: Quyết định 14/2025/QĐ-TTg, mục 3.2 (giá bán điện cho trạm/trụ sạc xe điện).
STRUCTURE_SOURCE = "Quyết định 14/2025/QĐ-TTg (29/05/2025), mục 3.2"

# voltage_group -> tou_band -> percent of base average price
TARIFF_STRUCTURE_PCT: dict[str, dict[str, float]] = {
    "tren_1kv": {   # từ trung áp trở lên (> 1 kV)
        "binh_thuong": 118.0,   # normal
        "thap_diem": 71.0,      # off-peak
        "cao_diem": 174.0,      # peak
    },
    "den_1kv": {    # hạ áp (<= 1 kV)
        "binh_thuong": 125.0,
        "thap_diem": 75.0,
        "cao_diem": 195.0,
    },
}

VOLTAGE_GROUP_LABEL = {
    "tren_1kv": "Từ trung áp trở lên (> 1 kV)",
    "den_1kv": "Hạ áp (đến 1 kV)",
}

TOU_BAND_LABEL = {
    "binh_thuong": "Giờ bình thường (normal)",
    "thap_diem": "Giờ thấp điểm (off-peak)",
    "cao_diem": "Giờ cao điểm (peak)",
}

# Time-of-use windows — standard Vietnamese 3-band schedule carried by QĐ 14/2025.
# Used to derive clock-hour weights for a naive blended price; the demand-weighted
# blend (blended_price_vnd_kwh) is what the OpEx term should actually use.
TOU_WINDOWS = {
    "cao_diem": "Thứ 2–Thứ 7: 09:30–11:30 và 17:00–20:00. Chủ nhật: không có giờ cao điểm.",
    "thap_diem": "Tất cả các ngày: 22:00–04:00.",
    "binh_thuong": "Các khung giờ còn lại.",
}
# Clock hours per week in each band (see TOU_WINDOWS): total 168h.
TOU_CLOCK_HOURS_PER_WEEK = {
    "cao_diem": 30.0,       # 5h/day × 6 days (Mon–Sat)
    "thap_diem": 42.0,      # 6h/day × 7 days
    "binh_thuong": 96.0,    # remainder
}

VND_ROUND = 2  # đồng, 2 decimals to match published figures (…,89 / …,94)


@dataclass
class TariffCell:
    voltage_group: str
    tou_band: str
    percent_of_avg: float
    price_vnd_kwh: float

    def as_dict(self) -> dict:
        return {
            "voltage_group": self.voltage_group,
            "voltage_group_label": VOLTAGE_GROUP_LABEL[self.voltage_group],
            "tou_band": self.tou_band,
            "tou_band_label": TOU_BAND_LABEL[self.tou_band],
            "percent_of_avg": self.percent_of_avg,
            "price_vnd_kwh": self.price_vnd_kwh,
        }


@dataclass
class OpexElectricityTariff:
    """Computed EV-charging electricity tariff for a given base average price."""

    base_avg_price_vnd_kwh: float
    cells: list[TariffCell] = field(default_factory=list)

    @classmethod
    def build(cls, base_avg_price: float = DEFAULT_BASE_AVG_PRICE_VND_KWH) -> "OpexElectricityTariff":
        cells: list[TariffCell] = []
        for vg, bands in TARIFF_STRUCTURE_PCT.items():
            for band, pct in bands.items():
                price = round(base_avg_price * pct / 100.0, VND_ROUND)
                cells.append(TariffCell(vg, band, pct, price))
        return cls(base_avg_price_vnd_kwh=base_avg_price, cells=cells)

    def price(self, voltage_group: str, tou_band: str) -> float:
        """Return đ/kWh for a (voltage_group, tou_band) cell."""
        for c in self.cells:
            if c.voltage_group == voltage_group and c.tou_band == tou_band:
                return c.price_vnd_kwh
        raise KeyError(f"No tariff cell for ({voltage_group!r}, {tou_band!r})")

    def blended_price_vnd_kwh(
        self,
        voltage_group: str,
        energy_share: dict[str, float] | None = None,
    ) -> float:
        """Blended đ/kWh for one voltage group.

        `energy_share` = fraction of charged energy (kWh) falling in each TOU band,
        e.g. {"cao_diem": 0.2, "binh_thuong": 0.5, "thap_diem": 0.3}. This is the
        number the OpEx term in the model wants: expected buy price per kWh given how
        charging demand is distributed over the day. Must sum to ~1.

        If `energy_share` is None, falls back to clock-hour weights (naive: assumes a
        flat charging profile across the day — usually optimistic on peak share).
        """
        if energy_share is None:
            total = sum(TOU_CLOCK_HOURS_PER_WEEK.values())
            energy_share = {k: v / total for k, v in TOU_CLOCK_HOURS_PER_WEEK.items()}
        s = sum(energy_share.values())
        if abs(s - 1.0) > 1e-6:
            raise ValueError(f"energy_share must sum to 1.0, got {s:.4f}")
        return round(
            sum(self.price(voltage_group, band) * share for band, share in energy_share.items()),
            VND_ROUND,
        )

    # ----------------------------------------------------------------------- #
    # Serialization
    # ----------------------------------------------------------------------- #

    def metadata(self) -> dict:
        return {
            "dataset": "opex_electricity_tariff",
            "description": "EV charging station retail electricity tariff (Vietnam), đ/kWh.",
            "unit": "VND/kWh",
            "base_avg_price_vnd_kwh": self.base_avg_price_vnd_kwh,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "tariff_structure": STRUCTURE_SOURCE,
                "base_avg_price": BASE_PRICE_SOURCE,
                "base_avg_price_effective": BASE_PRICE_EFFECTIVE,
            },
            "tou_windows": TOU_WINDOWS,
            "notes": (
                "Tariff structure (% of average retail price) is fixed by decision; "
                "only base_avg_price changes when EVN adjusts the average retail price "
                "— re-run with --base-price to refresh. QĐ 14/2025 caps this structure "
                "at 3 years from its implementation date."
            ),
        }

    def to_rows(self) -> list[dict]:
        return [c.as_dict() for c in self.cells]

    def write_csv(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = self.to_rows()
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"metadata": self.metadata(), "tariff": self.to_rows()}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_out_dir() -> Path:
    # repo_root/data/external  (this file: src/ev_siting/data/opex_electricity.py)
    return Path(__file__).resolve().parents[3] / "data" / "external"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--base-price",
        type=float,
        default=DEFAULT_BASE_AVG_PRICE_VND_KWH,
        help=f"Giá bán lẻ điện bình quân (đ/kWh). Default {DEFAULT_BASE_AVG_PRICE_VND_KWH} "
        f"({BASE_PRICE_SOURCE}).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=_default_out_dir(),
        help="Output directory (default: data/external/).",
    )
    args = parser.parse_args(argv)

    tariff = OpexElectricityTariff.build(args.base_price)
    csv_path = args.out_dir / "opex_electricity_tariff.csv"
    json_path = args.out_dir / "opex_electricity_tariff.json"
    tariff.write_csv(csv_path)
    tariff.write_json(json_path)

    print(f"Base average price: {tariff.base_avg_price_vnd_kwh:,.2f} đ/kWh")
    print(f"Wrote {len(tariff.cells)} tariff cells:")
    for c in tariff.cells:
        print(
            f"  {VOLTAGE_GROUP_LABEL[c.voltage_group]:32s} | "
            f"{TOU_BAND_LABEL[c.tou_band]:28s} | "
            f"{c.percent_of_avg:5.0f}% | {c.price_vnd_kwh:>10,.2f} đ/kWh"
        )
    for vg in TARIFF_STRUCTURE_PCT:
        print(
            f"  blended (clock-hour) {VOLTAGE_GROUP_LABEL[vg]:32s} "
            f"≈ {tariff.blended_price_vnd_kwh(vg):,.2f} đ/kWh"
        )
    print(f"\nCSV : {csv_path}")
    print(f"JSON: {json_path}")


if __name__ == "__main__":
    main()
