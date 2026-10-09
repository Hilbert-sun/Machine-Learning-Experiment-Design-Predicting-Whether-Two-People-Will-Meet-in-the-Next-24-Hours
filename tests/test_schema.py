import gzip

import pandas as pd
import pytest

from src.loader import SchemaError, iter_source_chunks, validate_file


def test_copenhagen_header_sentinels_duplicates_and_nonconsecutive_ids_preserved(tmp_path):
    path = tmp_path / "bt_symmetric.csv"
    path.write_text("# timestamp,user_a,user_b,rssi\n0,5,-1,0\n0,5,-2,-88\n300,5,97,-65\n300,5,97,-65\n")
    report = validate_file(path, "Copenhagen", chunksize=2)
    assert report.rows == 4
    assert report.empty_scans == report.external_scans == 1
    assert report.timestamp_min == 0 and report.timestamp_max == 300
    assert report.time_basis == "relative_seconds"
    assert report.rssi_min == -88 and report.rssi_max == 0
    frame = pd.concat(iter_source_chunks(path, "Copenhagen", chunksize=1))
    assert frame.user_a.tolist() == [5, 5, 5, 5]
    assert frame.user_b.tolist() == [-1, -2, 97, 97]
    assert frame.duplicated().sum() == 1


@pytest.mark.parametrize("name,header,row", [
    ("calls.csv", "timestamp,caller,callee,duration", "184,300,512,-1"),
    ("sms.csv", "timestamp,sender,recipient", "18,370,512"),
])
def test_real_communication_aliases_and_missed_calls(tmp_path, name, header, row):
    path = tmp_path / name
    path.write_text(header + "\n" + row + "\n")
    frame = next(iter_source_chunks(path, "Copenhagen"))
    assert "user_a" in frame and "user_b" in frame
    assert frame.user_b.iloc[0] == 512
    if name == "calls.csv":
        assert frame.duration.iloc[0] == -1


def test_sociopatterns_gzip_and_mixed_whitespace(tmp_path):
    path = tmp_path / "HighSchool2013_proximity_net.csv.gz"
    with gzip.open(path, "wt") as handle:
        handle.write("1385982020  454 640 MP MP\n1385982040\t1\t939\t2BIO3\t2BIO3\n")
    report = validate_file(path, "SocioPatterns", chunksize=1)
    assert report.rows == 2
    assert report.timestamp_min == 1385982020
    assert report.time_basis == "unix_seconds"
    assert report.preview[1]["class_a"] == "2BIO3"


@pytest.mark.parametrize("header,row", [
    ("timestamp,user_a,user_b,unexpected", "0,1,2,3"),
    ("timestamp,user_a,user_b,rssi", "missing,1,2,-70"),
    ("timestamp,user_a,user_b,rssi", "-1,1,2,-70"),
    ("timestamp,user_a,user_b,rssi", "0,1.5,2,-70"),
    ("timestamp,user_a,user_b,rssi", "0,-1,2,-70"),
    ("timestamp,user_a,user_b,rssi", "0,1,-3,-70"),
    ("timestamp,user_a,user_b,rssi", "0,1,2,inf"),
    ("timestamp,user_a,user_b,rssi", "0,1,2"),
    ("timestamp,user_a,user_b,rssi", "0,1,2,-70,unexpected"),
    ("timestamp,user_a,user_b,rssi", "0,1,9223372036854775808,-70"),
])
def test_bad_schema_or_values_fail_without_silent_repair(tmp_path, header, row):
    path = tmp_path / "bt_symmetric.csv"
    path.write_text(header + "\n" + row + "\n")
    with pytest.raises(SchemaError):
        validate_file(path, "Copenhagen")


@pytest.mark.parametrize("row", ["0,1,2,MP,PC", "0 1 2 MP", "0 1 2 MP PC extra", "0 1 -1 MP PC"])
def test_sociopatterns_rejects_comma_wrong_arity_and_invalid_ids(tmp_path, row):
    path = tmp_path / "HighSchool2013_proximity_net.csv"
    path.write_text(row + "\n")
    with pytest.raises(SchemaError):
        validate_file(path, "SocioPatterns")


@pytest.mark.parametrize("content", ["", "timestamp,user_a,user_b,rssi\n"])
def test_empty_files_fail(tmp_path, content):
    path = tmp_path / "bt.csv"
    path.write_text(content)
    with pytest.raises(SchemaError):
        validate_file(path, "Copenhagen")


def test_error_in_later_chunk_is_not_missed(tmp_path):
    path = tmp_path / "sms.csv"
    path.write_text("timestamp,sender,recipient\n0,5,97\n1,5,97\n2,5,bad\n")
    with pytest.raises(SchemaError, match="数据行 3"):
        validate_file(path, "Copenhagen", chunksize=2)


def test_corrupt_gzip_reports_validation_error(tmp_path):
    path = tmp_path / "HighSchool2013_proximity_net.csv.gz"
    path.write_bytes(b"not a gzip")
    with pytest.raises(SchemaError, match="无法解析"):
        validate_file(path, "SocioPatterns")


@pytest.mark.parametrize("row", ["1,5,97,-70,extra", "1,5,97"])
def test_later_row_with_wrong_field_count_fails_across_chunks(tmp_path, row):
    path = tmp_path / "bt_symmetric.csv"
    path.write_text("timestamp,user_a,user_b,rssi\n0,5,97,-65\n" + row + "\n")
    with pytest.raises(SchemaError):
        validate_file(path, "Copenhagen", chunksize=1)
