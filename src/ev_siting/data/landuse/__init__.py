"""Land-use / khả thi xây dựng — bộ lọc candidate site (P5).

Trả lời câu hỏi **"ô H3 nào được phép đặt trạm"** cho MCLP. Gồm 2 bộ lọc:

  - **âm (loại cứng):** mặt nước / núi-rừng / đất cấm (quân sự, khu bảo tồn,
    sân bay) / không có đường tiếp cận → không bao giờ là candidate.
  - **phạt mềm (giữ + hạ điểm):** đất nông nghiệp, hạ tầng mỏng, xa trạm biến áp.

Nguồn công khai:
  - **ESA WorldCover 10 m v200 (2021)** — raster lớp phủ (nền chính, CC-BY 4.0).
  - **OSM** — military / protected_area / aerodrome / water polygon + substation.
  - `demand_h3.road_len_m` — proxy đường tiếp cận (đã có sẵn).

Output: `data/interim/landuse/buildable_h3.parquet` — cột `buildable` + thành phần
lớp phủ + cờ, join theo `h3_r8`. Tiêu thụ bởi `features/build_candidates.py`.
"""
