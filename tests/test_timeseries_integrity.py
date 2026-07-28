"""Regression tests for F2/F3 telemetry preservation."""

import csv

from ev_siting.data.evcs.evcs_scrape import FETCH_JS, reconcile_failed
from ev_siting.data.evcs.split_timeseries import flush


def test_split_merges_discontiguous_blocks_and_new_run_wins(tmp_path):
    # Station A can reappear after B when scrape crashes/resumes. Its first block
    # must survive, and a newer observation of the same timestamp wins deterministically.
    flush("C.A", {100: "1", 200: "2"}, ts_dir=tmp_path)
    stats = flush("C.A", {200: "9", 300: "3"}, ts_dir=tmp_path)

    with (tmp_path / "C.A.csv").open(newline="", encoding="utf-8") as fh:
        assert list(csv.DictReader(fh)) == [
            {"timestamp": "100", "n_cars_charging": "1"},
            {"timestamp": "200", "n_cars_charging": "9"},
            {"timestamp": "300", "n_cars_charging": "3"},
        ]
    assert stats["overlap"] == 1


def test_history_requests_are_socket_isolated_and_cleanup_listener():
    # history_data has no proven correlation id; one socket per sid prevents a
    # late response for A from resolving B's listener after A timed out.
    assert "for (const sid of stationIds) {\n    const socket = io" in FETCH_JS
    assert "socket.off('history_data', done)" in FETCH_JS
    assert "finally {\n      socket.disconnect();" in FETCH_JS


def test_failed_file_drops_codes_that_later_succeed(tmp_path):
    failed = tmp_path / "run.failed"
    failed.write_text("C.A\nC.B\n", encoding="utf-8")
    assert reconcile_failed(str(failed), {"C.A"}) == ["C.B"]
    assert failed.read_text(encoding="utf-8") == "C.B\n"
