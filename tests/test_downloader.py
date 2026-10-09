import hashlib
from io import BytesIO
from unittest.mock import Mock

import pytest
import requests

from src.downloader import (
    DownloadError, RemoteFile, download_file, fetch_copenhagen_files,
    save_upload, scan_local_files,
)


def response(payload=b"sample", metadata=None):
    result = Mock()
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    result.headers = {"Content-Length": str(len(payload))}
    result.iter_content.return_value = [payload[:2], b"", payload[2:]]
    result.json.return_value = metadata
    return result


def remote(payload=b"sample"):
    return RemoteFile("events.csv", "https://example.org/official-file", len(payload), hashlib.md5(payload).hexdigest())


def test_metadata_uses_returned_filename_url_and_checksum():
    client = Mock()
    client.get.return_value = response(metadata={"files": [{
        "name": "bt_symmetric.csv", "size": 10, "download_url": "https://example.org/from-api",
        "computed_md5": "a" * 32,
    }]})
    files = fetch_copenhagen_files(session=client)
    assert files == [RemoteFile("bt_symmetric.csv", "https://example.org/from-api", 10, "a" * 32)]


def test_streamed_download_skip_and_progress(tmp_path):
    client = Mock()
    reply = response()
    client.get.return_value = reply
    progress = Mock()
    result = download_file(remote(), tmp_path, session=client, progress=progress)
    assert result.path.read_bytes() == b"sample"
    assert not result.skipped
    assert client.get.call_args.kwargs["stream"] is True
    assert client.get.call_args.kwargs["timeout"] == (10, 30)
    assert progress.call_args.args == (6, 6)
    assert download_file(remote(), tmp_path, session=client).skipped
    assert client.get.call_count == 1
    assert not list(tmp_path.glob("*.part"))


@pytest.mark.parametrize("failure", ["md5", "size", "network"])
def test_failed_download_preserves_existing_file_and_cleans_partial(tmp_path, failure):
    existing = tmp_path / "events.csv"
    existing.write_bytes(b"old-data")
    client = Mock()
    reply = response(b"broken")
    if failure == "size":
        reply.iter_content.return_value = [b"truncated"]
    elif failure == "network":
        reply.iter_content.side_effect = requests.ConnectionError("connection dropped")
    client.get.return_value = reply
    with pytest.raises(DownloadError):
        download_file(remote(), tmp_path, session=client, attempts=1)
    assert existing.read_bytes() == b"old-data"
    assert not list(tmp_path.glob("*.part"))


def test_retry_after_timeout(tmp_path, monkeypatch):
    monkeypatch.setattr("src.downloader.time.sleep", lambda _: None)
    client = Mock()
    client.get.side_effect = [requests.Timeout("timed out"), response()]
    assert download_file(remote(), tmp_path, session=client).path.read_bytes() == b"sample"
    assert client.get.call_count == 2


def test_api_failure_reports_manual_recovery():
    client = Mock()
    client.get.side_effect = requests.Timeout("offline")
    with pytest.raises(DownloadError, match="手动下载"):
        fetch_copenhagen_files(session=client, attempts=1)


@pytest.mark.parametrize("name", ["../events.csv", "/tmp/events.csv", "a\\events.csv", ".."])
def test_unsafe_filename_rejected(name):
    with pytest.raises(ValueError):
        RemoteFile(name, "https://example.org/data")


def test_manual_upload_and_local_scan(tmp_path):
    saved = save_upload(BytesIO(b"data"), "events.csv", tmp_path)
    assert saved.read_bytes() == b"data"
    with pytest.raises(FileExistsError):
        save_upload(BytesIO(b"replacement"), "events.csv", tmp_path)
    with pytest.raises(ValueError):
        save_upload(BytesIO(b""), "empty.csv", tmp_path)
    (tmp_path / ".gitkeep").touch()
    (tmp_path / "incomplete.part").write_bytes(b"partial")
    assert scan_local_files(tmp_path) == [{"文件": "events.csv", "字节": 4, "状态": "Downloaded · 待验证"}]
