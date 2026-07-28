"""Canonical filesystem paths for the EVCS crawl/clean pipeline.

Every step anchors on PROJECT_ROOT derived from this file's location, so the
pipeline runs correctly regardless of the working directory. Directory layout
follows the repo convention (see README.md): immutable crawl output lives under
``data/raw/``, cleaned/derived artefacts under ``data/interim/``.

Run each step as a module from the repo root, e.g.::

    PYTHONPATH=src python -m ev_siting.data.evcs.split_timeseries
"""
from pathlib import Path

# evcs -> data -> ev_siting -> src -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATA = PROJECT_ROOT / "data"

# --- raw, immutable crawl output (data/raw/evcs) ---
RAW_DIR = DATA / "raw" / "evcs"
CATALOG_DIR = RAW_DIR / "catalog"
LOAD_TS = RAW_DIR / "load_ts.csv"
TIMESERIES_RUNS_DIR = RAW_DIR / "timeseries_runs"

# --- cleaned / derived (data/interim) ---
INTERIM_DIR = DATA / "interim"
# Discovery inputs stay raw; merge output is derived and must not mutate raw.
CATALOG_CSV = INTERIM_DIR / "evcs_catalog.csv"
ALL_CODES = INTERIM_DIR / "evcs_all_codes.txt"
TS_DIR = INTERIM_DIR / "evcs_timeseries"
MASTER_CSV = INTERIM_DIR / "stations_master_evcs.csv"
QUALITY_REPORT = INTERIM_DIR / "quality_report.json"

# --- canonical, contract-shaped output (SCHEMA_CONTRACT muc 2/3) ---
# Parquet Hive-partitioned theo province_code la canonical (doc thang vao PostGIS /
# GeoPandas). Mo hinh 2 tang: stations (1 dong/tram) -> connectors (1 dong/nhom cong suat).
CANONICAL_DIR = INTERIM_DIR / "canonical"
STATIONS_DIR = CANONICAL_DIR / "stations"        # dataset partition province_code=*
CONNECTORS_DIR = CANONICAL_DIR / "connectors"    # dataset partition province_code=*
