"""Pair symmetry, duplicate boundaries, missing observations and cache safety."""

import json
import sqlite3

import pandas as pd
import pytest

from src.loader import SchemaError
from src.preprocessing import cached_dataset, clean_contact_chunk, preprocess_contacts


def bluetooth(tmp_path, rows):
    path = tmp_path / "bt_symmetric.csv"
    path.write_text("# timestamp,user_a,user_b,rssi\n" + rows)
    return path


def test_pair_symmetry_and_defensive_id_filter_do_not_mutate_input():
    frame = pd.DataFrame({"timestamp": [0] * 6, "user_a": [5, 97, 5, 5, -3, 5],
                          "user_b": [97, 5, -1, -2, 97, 5], "rssi": [-65, -65, 0, -80, -65, -60]})
    original = frame.copy(deep=True)
    result = clean_contact_chunk(frame, "Copenhagen")
    pd.testing.assert_series_equal(result.contacts.iloc[0], result.contacts.iloc[1], check_names=False)
    assert result.invalid_id_rows == 3
    assert result.self_contact_rows == 1
    assert result.contacts[["user_min", "user_max"]].values.tolist() == [[5, 97], [5, 97]]
    pd.testing.assert_frame_equal(frame, original)


def test_global_exact_dedup_preserves_other_pairs_and_different_signal(tmp_path):
    path = bluetooth(tmp_path, "0,5,97,-65\n0,5,222,-70\n0,97,5,-65\n0,5,97,-80\n300,5,97,-65\n300,5,5,-60\n")
    result = preprocess_contacts(path, "Copenhagen", tmp_path / "out", chunksize=1)
    contacts = pd.read_parquet(result.directory / "contacts.parquet")
    assert len(contacts) == 4
    assert len(contacts.loc[contacts.timestamp.eq(0)]) == 3
    assert result.report["duplicate_contact_rows"] == 1
    assert result.report["self_contact_rows"] == 1
    assert contacts.user_min.lt(contacts.user_max).all()
    assert contacts.timestamp.tolist() == sorted(contacts.timestamp.tolist())
    assert contacts.class_min.isna().all()
    assert result.report["input_rows"] == sum(result.report[key] for key in (
        "invalid_id_rows", "self_contact_rows", "duplicate_contact_rows", "contact_rows"))


def test_missingness_preserves_empty_external_scans_without_inventing_receiver_scans(tmp_path):
    path = bluetooth(tmp_path, "0,5,-1,0\n0,5,-2,-88\n300,5,97,-60\n172800,5,-1,0\n")
    result = preprocess_contacts(path, "Copenhagen", tmp_path / "out", chunksize=1)
    observations = pd.read_parquet(result.directory / "observations.parquet")
    coverage = pd.read_parquet(result.directory / "coverage.parquet")
    assert observations.user_id.tolist() == [5, 5, 5]
    assert observations.scan_observed.all()
    assert result.report["empty_scan_rows"] == 2
    assert result.report["external_device_rows"] == 1
    reporter = coverage.loc[coverage.user_id.eq(5)].set_index("study_day")
    assert reporter.loc[1, "recorded_bins"] == 2
    assert reporter.loc[1, "scan_coverage"] == pytest.approx(2 / 288)
    assert reporter.loc[2, "recorded_bins"] == 0
    assert reporter.loc[2, "scan_coverage"] == 0
    assert coverage.loc[coverage.user_id.eq(97), "recorded_bins"].eq(0).all()
    contacts = pd.read_parquet(result.directory / "contacts.parquet")
    assert len(contacts) == 1
    assert not any("label" in column for column in contacts.columns)


def test_sociopatterns_classes_follow_canonical_ids_and_coverage_is_unknown(tmp_path):
    path = tmp_path / "HighSchool2013_proximity_net.csv"
    path.write_text("1385982020 97 5 MP PC*\n1385982020 5 97 PC* MP\n1385982040 5 222 PC* 2BIO3\n")
    result = preprocess_contacts(path, "SocioPatterns", tmp_path / "out", chunksize=1)
    contacts = pd.read_parquet(result.directory / "contacts.parquet")
    assert contacts.iloc[0].user_min == 5
    assert contacts.iloc[0].class_min == "PC*" and contacts.iloc[0].class_max == "MP"
    assert contacts.source_timestamp.tolist() == [1385982020, 1385982040]
    assert (contacts.timestamp + result.report["time_origin_seconds"]).equals(contacts.source_timestamp)
    assert contacts.rssi.isna().all()
    assert result.report["duplicate_contact_rows"] == 1
    assert not result.report["scan_coverage_available"]
    coverage = pd.read_parquet(result.directory / "coverage.parquet")
    assert coverage.scan_coverage.isna().all()
    assert coverage.expected_scan_bins.isna().all()
    observations = pd.read_parquet(result.directory / "observations.parquet")
    assert observations.scan_observed.isna().all()
    assert set(observations.user_id) == {5, 97, 222}


def test_cache_reused_and_source_changes_invalidate_it(tmp_path, monkeypatch):
    path = bluetooth(tmp_path, "0,5,97,-65\n")
    output = tmp_path / "out"
    first = preprocess_contacts(path, "Copenhagen", output)
    with monkeypatch.context() as patch:
        patch.setattr("src.preprocessing.iter_source_chunks", lambda *a, **k: pytest.fail("cache reparsed source"))
        second = preprocess_contacts(path, "Copenhagen", output)
    assert not first.cached and second.cached
    assert first.directory == second.directory
    path.write_text(path.read_text() + "300,5,222,-70\n")
    assert cached_dataset(path, "Copenhagen", output) is None
    third = preprocess_contacts(path, "Copenhagen", output)
    assert third.directory != first.directory and third.report["contact_rows"] == 2
    (third.directory / "coverage.parquet").unlink()
    assert cached_dataset(path, "Copenhagen", output) is None


def test_all_empty_scans_produce_valid_empty_contact_artifact(tmp_path):
    path = bluetooth(tmp_path, "0,5,-1,0\n300,5,-2,-80\n")
    result = preprocess_contacts(path, "Copenhagen", tmp_path / "out")
    assert pd.read_parquet(result.directory / "contacts.parquet").empty
    assert len(pd.read_parquet(result.directory / "observations.parquet")) == 2
    assert result.report["rssi_summary"] == {"min": None, "max": None, "mean": None}
    assert json.loads((result.directory / "quality.json").read_text())["contact_rows"] == 0


def test_failure_in_later_chunk_does_not_publish_or_leave_partial_cache(tmp_path):
    path = bluetooth(tmp_path, "0,5,97,-65\n300,5,bad,-70\n")
    output = tmp_path / "out"
    with pytest.raises(SchemaError):
        preprocess_contacts(path, "Copenhagen", output, chunksize=1)
    assert not list(output.rglob("*.json"))
    assert not list(output.rglob("*.parquet"))
    assert not list(output.rglob("*.sqlite"))


def test_communications_cannot_be_mistaken_for_contact_input(tmp_path):
    path = tmp_path / "sms.csv"
    path.write_text("timestamp,sender,recipient\n0,5,97\n")
    with pytest.raises(SchemaError, match="主接触文件"):
        preprocess_contacts(path, "Copenhagen", tmp_path / "out")


def test_source_change_during_processing_aborts_publication(tmp_path):
    path = bluetooth(tmp_path, "0,5,97,-65\n300,5,97,-60\n")
    output = tmp_path / "out"

    def change_source(rows):
        if rows == 1:
            path.write_text(path.read_text() + "600,5,222,-70\n")

    with pytest.raises(RuntimeError, match="源文件在处理期间发生改变"):
        preprocess_contacts(path, "Copenhagen", output, chunksize=1, progress=change_source)
    assert not list(output.rglob("*.parquet"))
    assert not list(output.rglob("*.json"))


def test_storage_failure_preserves_previous_successful_cache(tmp_path, monkeypatch):
    path = bluetooth(tmp_path, "0,5,97,-65\n")
    output = tmp_path / "out"
    first = preprocess_contacts(path, "Copenhagen", output)
    before = {p for p in output.rglob("*") if p.is_file()}
    path.write_text(path.read_text() + "300,5,222,-70\n")

    def fail_export(*args, **kwargs):
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr("src.preprocessing._export", fail_export)
    with pytest.raises(RuntimeError, match="本地预处理存储失败"):
        preprocess_contacts(path, "Copenhagen", output)
    assert {p for p in output.rglob("*") if p.is_file()} == before
    assert (first.directory / "contacts.parquet").is_file()
    assert cached_dataset(path, "Copenhagen", output) is None
