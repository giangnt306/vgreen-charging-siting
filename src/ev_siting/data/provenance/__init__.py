"""Provenance & snapshot freeze cho tầng cung/cầu (E-DQ10).

Đóng băng tập input thô về một **snapshot bất biến** có checksum + xuất
``data/raw/MANIFEST.json`` (lineage version-hoá trong git dù blob bị .gitignore).
Đây là **bước 0** của chuỗi làm sạch E-DQ: mọi dedup/sửa toạ độ/audit cầu phía sau
đều giả định input bên dưới **không đổi** — freeze là thứ biến giả định đó thành
sự thật kiểm chứng được (đối soát `input = output + quarantined + merged`).

Vận hành hoá **P9** (khoá mốc thời điểm): P9 *quyết* ngày freeze (cung chính thức
`2026-07-20`, telemetry occupancy `07/2026`); E-DQ10 làm nó **có checksum & tái lập**.

    PYTHONPATH=src python -m ev_siting.data.provenance.freeze_snapshot          # đóng băng + ghi manifest
    PYTHONPATH=src python -m ev_siting.data.provenance.freeze_snapshot --verify # đối chiếu (nhanh)
    PYTHONPATH=src python -m ev_siting.data.provenance.freeze_snapshot --verify --hashes  # đối chiếu content
"""
