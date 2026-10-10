import os
from pathlib import Path

import pytest

from src.snapshot_manager import SnapshotChanged, file_hash, resolve_path, snapshot_context


def test_pinned_bytes_and_same_size_mtime_source_edit_detected(tmp_path):
    source = tmp_path/'archive'
    source.write_bytes(b'old-data')
    metadata = source.stat()
    with pytest.raises(SnapshotChanged, match='source_snapshot_changed'):
        with snapshot_context([source], {'dataset': 'one'}) as snapshot:
            pinned = resolve_path(source)
            assert pinned != source and pinned.read_bytes() == b'old-data'
            source.write_bytes(b'new-data')
            os.utime(source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            assert pinned.read_bytes() == b'old-data'
    assert snapshot.public_identity()['ingestion_time_status'] == 'unavailable'


def test_changed_while_copying_never_commits(tmp_path, monkeypatch):
    import src.snapshot_manager as module
    source = tmp_path/'source';source.write_bytes(b'first')
    original = module.shutil.copyfileobj
    def changed(src, dest, *args):
        original(src, dest, *args)
        source.write_bytes(b'other')
    monkeypatch.setattr(module.shutil, 'copyfileobj', changed)
    with pytest.raises(SnapshotChanged):
        with snapshot_context([source], {'dataset': 'x'}):
            pytest.fail('Inconsistent snapshot was exposed')
    assert not list((module.cache_root()/'snapshots').glob('*/COMMITTED.json'))


def test_nested_requests_must_use_bound_dependencies_and_copy_integrity(tmp_path):
    source = tmp_path/'source';source.write_bytes(b'data')
    other = tmp_path/'other';other.write_bytes(b'data')
    with snapshot_context([source], {'dataset': 'x'}) as snapshot:
        with snapshot_context([source], {'dataset': 'x'}) as same:
            assert same is snapshot
        with pytest.raises(SnapshotChanged, match='unbound'):
            with snapshot_context([other], {}):
                pass
    with pytest.raises(SnapshotChanged, match='pinned copy'):
        with snapshot_context([source], {}) as snapshot:
            pinned = resolve_path(source)
            pinned.chmod(0o600);pinned.write_bytes(b'fake')


def test_model_related_files_share_pinned_directory(tmp_path):
    folder=tmp_path/'model';folder.mkdir()
    manifest=folder/'manifest.json';manifest.write_text('{}')
    weights=folder/'model.joblib';weights.write_bytes(b'weights')
    with snapshot_context([manifest,weights], {}):
        assert resolve_path(manifest).parent == resolve_path(weights).parent


def test_corrupted_inactive_snapshot_recovers_from_same_verified_source(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'authentic archive')
    with snapshot_context([source],{}) as first:
        old_copy=resolve_path(source)
    old_copy.chmod(0o600);old_copy.write_bytes(b'corrupt cached copy')
    with snapshot_context([source],{}) as repaired:
        assert repaired.version==first.version
        assert resolve_path(source)!=old_copy
        assert resolve_path(source).read_bytes()==source.read_bytes()
        repaired_directory=repaired.directory
    with snapshot_context([source],{}) as reused:
        assert reused.directory==repaired_directory
