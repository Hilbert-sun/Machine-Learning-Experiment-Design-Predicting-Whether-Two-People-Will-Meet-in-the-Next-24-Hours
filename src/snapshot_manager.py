"""Stable archive snapshots, not atomic acquisition or historical ingestion logs."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

ACTIVE = ContextVar('encounter_snapshot', default=None)
SNAPSHOT_VERSION = 1


class SnapshotChanged(ValueError):
    pass


def cache_root():
    return Path(os.environ.get('ENCOUNTER_CACHE_ROOT', Path(__file__).resolve().parents[1]/'data/processed/t32_cache'))


def file_hash(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class ArchiveSnapshot:
    def __init__(self, paths, identity):
        self.paths = sorted({Path(p).resolve() for p in paths})
        self.identity = identity
        self.pending = []
        self.pending_results = {}
        self.hashes = {str(p): file_hash(p) for p in self.paths}
        self.version = hashlib.sha256(canonical({'files': self.hashes, 'version': SNAPSHOT_VERSION}).encode()).hexdigest()
        self.established_at = datetime.now(timezone.utc).isoformat()
        self.directory = cache_root()/'snapshots'/self.version
        parents = {str(p): i for i, p in enumerate(sorted({p.parent for p in self.paths}))}
        self.mapping = {str(p): self.directory/str(parents[str(p.parent)])/p.name for p in self.paths}
        pointer = self.directory.parent/(self.version+'.json')
        if pointer.is_file():
            try:
                name = json.loads(pointer.read_text())['version_directory']
                if Path(name).name != name or not name.startswith(self.version+'-'):
                    raise ValueError('Invalid snapshot repair pointer')
                self._relocate(self.directory.parent/name)
            except (OSError, ValueError, KeyError, TypeError):
                pass  # An untrusted/incomplete pointer never authorizes bytes; re-pin below.
        self._pin()

    def _relocate(self, directory):
        previous = self.directory
        self.mapping = {name: directory/path.relative_to(previous) for name,path in self.mapping.items()}
        self.directory = directory

    def _pin(self):
        self.directory.parent.mkdir(parents=True, exist_ok=True)
        manifest = self.directory/'COMMITTED.json'
        valid = False
        if manifest.is_file():
            try:
                record = json.loads(manifest.read_text())
                valid = record['files'] == self.hashes and all(file_hash(self.mapping[str(p)]) == self.hashes[str(p)] for p in self.paths)
            except (OSError, ValueError, KeyError):
                valid = False
        if not valid:
            repair = self.directory.exists()
            if repair:
                # Keep the corrupt version for any existing reader; publish a fresh immutable version.
                self._relocate(self.directory.parent/(self.version+'-'+uuid4().hex))
                manifest = self.directory/'COMMITTED.json'
            with tempfile.TemporaryDirectory(dir=self.directory.parent, prefix='.snapshot-') as tmp:
                staged = Path(tmp)
                for p in self.paths:
                    target = staged/self.mapping[str(p)].relative_to(self.directory)
                    target.parent.mkdir(exist_ok=True)
                    with p.open('rb') as source, target.open('wb') as destination:
                        shutil.copyfileobj(source, destination, 1024*1024)
                        destination.flush(); os.fsync(destination.fileno())
                    if file_hash(target) != self.hashes[str(p)]:
                        raise SnapshotChanged('source_snapshot_changed: source bytes changed during pinning.')
                    target.chmod(0o400)
                self.check_live()
                (staged/'COMMITTED.json').write_text(canonical({'files': self.hashes, 'version': SNAPSHOT_VERSION}))
                # A committed content-addressed snapshot is never replaced in-place.
                if self.directory.exists():
                    raise SnapshotChanged('source_snapshot_changed: corrupt or incomplete pinned archive; refuse reuse.')
                try:
                    os.rename(staged, self.directory)
                except FileExistsError:
                    if not manifest.is_file():
                        raise SnapshotChanged('source_snapshot_changed: concurrent incomplete snapshot.')
                # TemporaryDirectory accepts an already-renamed source directory.
            if repair:
                pointer = self.directory.parent/(self.version+'.json')
                with tempfile.NamedTemporaryFile(mode='w',dir=pointer.parent,prefix='.repair-',delete=False) as handle:
                    temporary=Path(handle.name)
                    json.dump({'version_directory':self.directory.name},handle)
                    handle.flush();os.fsync(handle.fileno())
                try:
                    self.check_live()
                    os.replace(temporary,pointer)
                finally:
                    temporary.unlink(missing_ok=True)

    def check_live(self):
        try:
            current = {str(p): file_hash(p) for p in self.paths}
        except OSError as exc:
            raise SnapshotChanged('source_snapshot_changed: source disappeared.') from exc
        if current != self.hashes:
            raise SnapshotChanged('source_snapshot_changed: source content differs from pinned version.')

    def check(self):
        self.check_live()
        if any(file_hash(self.mapping[str(p)]) != self.hashes[str(p)] for p in self.paths):
            raise SnapshotChanged('source_snapshot_changed: private pinned copy was modified.')

    def public_identity(self):
        return {'snapshot_version': SNAPSHOT_VERSION, 'snapshot_id': self.version, 'established_at': self.established_at,
                'identity': self.identity, 'event_time_status': 'recorded_archive_time', 'ingestion_time_status': 'unavailable',
                'guarantee': 'byte-verified stable read-only archive copies; not atomic live acquisition'}


@contextmanager
def snapshot_context(paths, identity):
    paths = [Path(p).resolve() for p in paths]
    active = ACTIVE.get()
    if active is not None:
        if not set(map(str, paths)) <= set(active.hashes):
            raise SnapshotChanged('source_snapshot_changed: unbound dependency in nested calculation.')
        yield active
        return
    snapshot = ArchiveSnapshot(paths, identity)
    token = ACTIVE.set(snapshot)
    try:
        yield snapshot
        snapshot.check()
        for temporary, pointer in snapshot.pending:
            os.replace(temporary, pointer)
    finally:
        for temporary, _ in snapshot.pending:
            temporary.unlink(missing_ok=True)
        ACTIVE.reset(token)


def resolve_path(path):
    original = str(Path(path).resolve())
    snapshot = ACTIVE.get()
    if snapshot is not None and original in snapshot.mapping:
        return snapshot.mapping[original]
    return Path(path)


def read_json(path):
    return json.loads(resolve_path(path).read_text())


def processed_paths(processed):
    return [processed.directory/name for name in ('contacts.parquet', 'observations.parquet') if (processed.directory/name).is_file()]


def model_paths(directory, evidence=None):
    paths = [Path(directory)/name for name in ('manifest.json', 'model.joblib')]
    if evidence is not None:
        paths.append(Path(evidence))
    return paths
