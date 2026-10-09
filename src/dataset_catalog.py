"""Evidence-based, dataset-isolated adapters; no inferred negatives from contact-only files."""

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
from urllib.parse import urlparse
import zipfile

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

from src.baseline_audit import sha256
from src.downloader import RemoteFile, download_file, safe_name, save_upload
from src.loader import iter_source_chunks
from src.preprocessing import preprocess_contacts
from src.real_experiment import snapshot_capacity
from src.window_ui import location

DAY = 86400
ADAPTER_VERSION = 3
SCHEMA = pa.schema([('dataset_id',pa.string()),('timestamp',pa.int64()),('user_min',pa.int64()),('user_max',pa.int64())])


def sources(root):
    return json.loads((Path(root)/'configs/dataset_catalog.json').read_text())


def directory_for(root,config,spec):
    if spec['dataset_id']=='copenhagen':return location(root,config,'raw_copenhagen')
    if spec['dataset_id']=='highschool2013':return location(root,config,'raw_sociopatterns')
    return Path(root)/config['paths'].get('raw_catalog',str(Path(config['paths']['processed']).parent/'raw/catalog'))/spec['dataset_id']


def availability(spec):
    return {'dataset_id':spec['dataset_id'],'name':spec['name'],'source_url':spec['source_url'],'citation':spec['citation'],
            'licence':spec.get('licence','not verified'),'access_status':spec['access_status'],'format':spec['format'],
            'temporal_resolution':spec.get('temporal_resolution'),'scan_coverage_evidence':spec['scan_coverage_evidence'],
            'eligibility_status':'restricted_access' if spec['access_status']=='restricted' else 'not_yet_verified',
            'reason':spec.get('access_note','Local file not yet validated.'),'participants':None,'event_rows':None,'valid_pairs':None,
            'first_timestamp':None,'last_timestamp':None,'usable_days_for_1d_3d_7d':None,'file_hash':None}


@contextmanager
def text_stream(path):
    path=Path(path)
    if path.suffix=='.zip':
        with zipfile.ZipFile(path) as archive:
            members=[n for n in archive.namelist() if n.endswith(('.dat','.csv','.txt')) and not Path(n).name.startswith('.')]
            if len(members)!=1:raise ValueError('Expected exactly one contact text member; no archive extraction permitted.')
            with archive.open(members[0]) as raw, io.TextIOWrapper(raw) as handle:yield handle
    elif path.suffix=='.gz':
        with gzip.open(path,'rt') as handle:yield handle
    elif path.suffix=='.bz2':
        import bz2
        with bz2.open(path,'rt') as handle:yield handle
    else:
        with path.open() as handle:yield handle


def edge_chunks(path,spec,*,chunksize=65536,nrows=None):
    fmt=spec['format']
    if fmt in ('copenhagen','highschool'):
        yield from iter_source_chunks(path,'Copenhagen' if fmt=='copenhagen' else 'SocioPatterns',chunksize=chunksize)
        return
    if fmt=='triplet':
        with text_stream(path) as handle:
            for frame in pd.read_csv(handle,sep=r'\s+',header=None,comment='#',chunksize=chunksize,nrows=nrows):
                if frame.shape[1]!=3:raise ValueError('Expected exactly t i j columns; schema mismatch.')
                frame.columns=spec.get('column_order',['timestamp','user_a','user_b']);yield frame
        return
    if fmt=='reality_csv_archive':
        with tarfile.open(path,'r:*') as archive:
            members=[m for m in archive.getmembers() if m.isfile() and Path(m.name).name=='edges.csv']
            if len(members)!=1:raise ValueError('Verified archive must contain one edges.csv.')
            with archive.extractfile(members[0]) as handle:
                for frame in pd.read_csv(handle,comment='#',chunksize=chunksize,nrows=nrows):
                    mapping=spec['column_mapping']
                    if not set(mapping)<=set(frame):raise ValueError('Reality Mining edge header differs from verified source.')
                    yield frame.rename(columns=mapping).loc[:,['timestamp','user_a','user_b']]
        return
    if fmt=='social_evolution':
        with text_stream(path) as handle:
            for frame in pd.read_csv(handle,chunksize=chunksize,nrows=nrows):
                mapping=spec.get('column_mapping')
                if not mapping or not {'timestamp','user_a','user_b'}<=set(mapping.values()):raise ValueError('Social Evolution timestamp/schema mapping has not been verified.')
                if not set(mapping)<=set(frame):raise ValueError('Social Evolution header differs from documented mapping.')
                renamed=frame.rename(columns=mapping)
                if spec.get('timestamp_encoding')=='datetime':
                    parsed=pd.to_datetime(renamed.timestamp,errors='raise')
                    if parsed.dt.tz is None:
                        zone=spec.get('timestamp_timezone')
                        if not zone:raise ValueError('Naive datetime timezone not verified; no assumed UTC.')
                        parsed=parsed.dt.tz_localize(zone,ambiguous='raise',nonexistent='raise')
                    renamed['timestamp']=parsed.dt.tz_convert('UTC').astype('int64')//10**9
                yield renamed.loc[:,['timestamp','user_a','user_b']]
        return
    raise ValueError('No verified parser/schema for this source.')


@dataclass
class DatasetAdapter:
    spec: dict

    def inspect(self,path,output):
        path,output=Path(path),Path(output)
        if path.is_symlink() or not path.is_file():raise ValueError('Require a regular local dataset file.')
        checksum=sha256(path)
        if self.spec.get('expected_sha256') and checksum!=self.spec['expected_sha256']:raise ValueError('Publisher source SHA256 mismatch.')
        spec_hash=hashlib.sha256(json.dumps(self.spec,sort_keys=True).encode()).hexdigest()[:12]
        destination=output/self.spec['dataset_id']/f'v{ADAPTER_VERSION}-{checksum[:20]}-{spec_hash}'
        manifest_path=destination/'dataset_manifest.json'
        if manifest_path.exists():
            result=json.loads(manifest_path.read_text())
            if sha256(destination/'contacts.parquet')!=result['processed_sha256']:raise ValueError('Catalog cache checksum changed.')
            return result
        destination.mkdir(parents=True,exist_ok=True)
        participants,pairs=set(),set()
        daily,day_users=Counter(),{}
        raw_rows,invalid,self_rows,valid_rows=0,0,0,0
        seen_events=set() if self.spec["format"] not in ("copenhagen","highschool") else None
        duplicate_rows=0
        first,last=None,None
        with tempfile.TemporaryDirectory(dir=destination,prefix='.inspect-') as tmp:
            staged=Path(tmp)/'contacts.parquet'
            with pq.ParquetWriter(staged,SCHEMA) as writer:
                for frame in edge_chunks(path,self.spec):
                    raw_rows+=len(frame)
                    numeric=frame[['timestamp','user_a','user_b']].apply(pd.to_numeric,errors='coerce')
                    finite=np.isfinite(numeric).all(axis=1)
                    integer=numeric.eq(numeric.round()).all(axis=1)
                    nonnegative=numeric.ge(0).all(axis=1)
                    good=finite & integer & nonnegative
                    invalid+=int((~good).sum())
                    numeric=numeric.loc[good].astype('int64')
                    self_rows+=int(numeric.user_a.eq(numeric.user_b).sum())
                    numeric=numeric.loc[numeric.user_a.ne(numeric.user_b)]
                    if numeric.empty:continue
                    contacts=pd.DataFrame({'dataset_id':self.spec['dataset_id'],'timestamp':numeric.timestamp,
                                           'user_min':numeric[['user_a','user_b']].min(axis=1),'user_max':numeric[['user_a','user_b']].max(axis=1)})
                    valid_rows+=len(contacts)
                    if seen_events is not None:
                        before=len(seen_events)
                        seen_events.update(contacts[['timestamp','user_min','user_max']].itertuples(index=False,name=None))
                        duplicate_rows+=len(contacts)-(len(seen_events)-before)
                    minimum,maximum=int(contacts.timestamp.min()),int(contacts.timestamp.max())
                    first=minimum if first is None else min(first,minimum);last=maximum if last is None else max(last,maximum)
                    participants.update(contacts.user_min);participants.update(contacts.user_max)
                    pairs.update(contacts[['user_min','user_max']].drop_duplicates().itertuples(index=False,name=None))
                    for day,group in contacts.groupby(contacts.timestamp//DAY):
                        daily[int(day)]+=len(group)
                        day_users.setdefault(int(day),set()).update(group.user_min)
                        day_users[int(day)].update(group.user_max)
                    writer.write_table(pa.Table.from_pandas(contacts,schema=SCHEMA,preserve_index=False))
            if first is None:raise ValueError('No valid canonical contact events.')
            if sha256(path)!=checksum:raise ValueError('Raw source changed during diagnostics.')
            staged.replace(destination/'contacts.parquet')
        origin=first//DAY*DAY
        snapshot_counts={}
        for window in (1,3,7):
            times=[d*DAY+28800 for d in range(first//DAY,last//DAY+1) if d*DAY+28800-window*DAY>=first and d*DAY+28800+DAY<=last]
            n=len(times);a,b=int(n*0.6),int(n*0.8)
            capacity={'train':0,'validation':0,'test':0}
            if 0<a<b<n:
                capacity={'train':sum(t+DAY<times[a] for t in times[:a]),'validation':sum(t+DAY<times[b] for t in times[a:b]),'test':n-b}
            snapshot_counts[str(window)]={'calendar_complete_snapshots':len(times),'primary_eligible_snapshots':None if self.spec.get('coverage_supported') else 0,
                                         'chronological_purged_date_capacity':capacity,'temporal_status':'insufficient_days' if min(capacity.values())<2 else 'date_capacity_only',
                                         'note':'calendar span only; no contact absence is converted into a negative'}
        coverage_checked=False
        coverage_diagnostics=None
        if self.spec['format']=='copenhagen':
            from src.label_builder import build_labels
            from src.pipeline_cache import parquet_frames
            from src.temporal_split import chronological_split
            processed=preprocess_contacts(path,'Copenhagen',output.parent)
            label_artifact=build_labels(processed,output.parent/'labels')
            label_frame=pd.read_parquet(label_artifact.path)
            eligible=label_frame.loc[label_frame.eligible_for_evaluation & label_frame.label_24h.notna()]
            coverage_checked=processed.report['empty_scan_rows']>0 and not eligible.empty
            coverage_diagnostics={'empty_scan_rows':processed.report['empty_scan_rows'],'external_device_rows':processed.report['external_device_rows'],
                                  'recorded_participants':processed.report['participants'],'eligible_rows':len(eligible),'unknown_rows':int(label_frame.label_24h.isna().sum())}
            for window in (1,3,7):
                complete=eligible.loc[eligible.timestamp-window*DAY>=processed.report['source_timestamp_min']-processed.report['time_origin_seconds']]
                snapshot_counts[str(window)]['primary_eligible_snapshots']=int(complete.timestamp.nunique())
            try:chronological_split(eligible)
            except ValueError:coverage_checked=False
        unit_verified=self.spec.get('timestamp_unit','seconds')=='seconds'
        status='eligible_primary_24h' if coverage_checked and unit_verified else 'exploratory_only'
        blockers=[]
        if not coverage_checked:blockers.append('missing verified scan support or insufficient eligible chronological samples; no reliable negative assumption')
        if unit_verified and snapshot_counts['7']['calendar_complete_snapshots']<6:blockers.append('insufficient_days after7d history and strict chronological purge')
        if unit_verified and last-first<8*DAY and not self.spec.get('coverage_supported'):status='insufficient_history'
        if not unit_verified:
            blockers.append('timestamp tick scale not verified; no conversion to seconds/days or24h labels')
            snapshot_counts={str(w):{'calendar_complete_snapshots':None,'primary_eligible_snapshots':0,'note':'timestamp unit unverified'} for w in (1,3,7)}
        result={**availability(self.spec),'adapter_version':ADAPTER_VERSION,'eligibility_status':status,'reason':'; '.join(blockers) or 'Coverage policy supported; still require cohort/class/time checks before training.',
                'file_name':path.name,'file_hash':checksum,'file_bytes':path.stat().st_size,'raw_rows':raw_rows,'event_rows':valid_rows,
                'invalid_rows':invalid,'self_contact_rows':self_rows,'participants':len(participants),'valid_pairs':len(pairs),
                'first_timestamp':first,'last_timestamp':last,'time_unit':self.spec.get('timestamp_unit','seconds'),'time_origin_seconds':origin if unit_verified else None,'span_days':(last-first)/DAY if unit_verified else None,
                'usable_days_for_1d_3d_7d':snapshot_counts,'missing_data_policy':'No recorded contact is not proof of a negative. No inferred labels or model scores.',
                'per_day':[{'study_day':d-first//DAY+1,'event_rows':daily[d],'participants_with_contacts':len(day_users.get(d,set()))} for d in range(first//DAY,last//DAY+1)] if unit_verified else [],
                'days_without_contact_records':sum(daily[d]==0 for d in range(first//DAY,last//DAY+1)) if unit_verified else None,'duplicate_canonical_records':duplicate_rows if seen_events is not None else None,
                'duplicates_policy':'Repeated source measurements retained; valid_pairs is distinct. No deduplication of repeated timestamps across different pairs.',
                'processed_sha256':sha256(destination/'contacts.parquet'),'namespace':self.spec['dataset_id'],'coverage_diagnostics':coverage_diagnostics,
                'preprocessing_note':self.spec.get('preprocessing_note','No unpublished availability assumptions.')}
        manifest_path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return result

    def import_file(self,stream,name,directory,output):
        if self.spec['access_status']=='restricted':raise ValueError('Restricted source; no automated import/acquisition without a documented lawful path.')
        safe_name(name)
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        destination=directory/safe_name(self.spec.get('filename',name))
        with tempfile.TemporaryDirectory(dir=directory,prefix='.import-') as temp:
            staged=save_upload(stream,destination.name,temp)
            if destination.exists():
                if sha256(destination)!=sha256(staged):raise ValueError('Existing raw source is preserved; use a separately versioned source instead of replacing it.')
                return self.inspect(destination,output)
            report=self.inspect(staged,output)
            staged.replace(destination)
        return report

    def acquire(self,directory,output,*,progress=None):
        spec=self.spec
        if spec['access_status']!='public' or not spec.get('source_verified') or not spec.get('download_url') or not spec.get('licence_verified'):
            raise ValueError('Full acquisition requires verified public source, license and download URL; use official manual recovery.')
        remote=RemoteFile(spec['filename'],spec['download_url'],spec.get('file_bytes'))
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        path=directory/remote.name
        # Always validate a bounded schema probe before first full acquisition.
        if not path.is_file():
            with requests.get(remote.download_url,stream=True,timeout=(10,30),headers={'Range':'bytes=0-65535'}) as response:
                response.raise_for_status()
                prefix=next(response.iter_content(chunk_size=65536),b'')
            validate_probe(prefix,spec)
            if progress:progress(0,None)
        result=download_file(remote,directory,progress=progress)
        return self.inspect(result.path,output)


def validate_probe(prefix,spec):
    """Validate a small streamed prefix; never extract archive paths or treat it as full data."""
    if not prefix:raise ValueError('Empty source probe.')
    if spec['format']=='triplet':
        if prefix.startswith(b'PK\x03\x04'):
            import struct,zlib
            method=struct.unpack_from('<H',prefix,8)[0]
            name_len,extra_len=struct.unpack_from('<HH',prefix,26)
            data=prefix[30+name_len+extra_len:]
            if method==8:text=zlib.decompressobj(-15).decompress(data,65536).decode('utf-8')
            elif method==0:text=data.decode('utf-8')
            else:raise ValueError('Unsupported compressed probe method.')
        elif prefix.startswith(b'\x1f\x8b'):
            import zlib
            text=zlib.decompressobj(16+zlib.MAX_WBITS).decompress(prefix).decode('utf-8')
        else:text=prefix.decode('utf-8')
        lines=[line for line in text.splitlines()[:-1] if line.strip() and not line.startswith('#')]
        if not lines or any(len(line.split())!=3 for line in lines[:20]):raise ValueError('Triplet probe schema mismatch.')
        for line in lines[:20]:
            if any(not token.lstrip('-').isdigit() for token in line.split()):raise ValueError('Noninteger triplet schema.')
    elif spec['format']=='reality_csv_archive':
        # Stream through initial tar entries only; stop after the verified edge header.
        try:
            with tarfile.open(fileobj=io.BytesIO(prefix),mode='r|*') as archive:
                for member in archive:
                    if member.isfile() and Path(member.name).name=='edges.csv':
                        header=archive.extractfile(member).read(2048).decode().splitlines()
                        line=next(line for line in header if line and not line.startswith('#'))
                        if not set(spec['column_mapping'])<=set(line.split(',')):raise ValueError('Edge probe header differs.')
                        return
        except (tarfile.TarError,EOFError) as exc:raise ValueError('Bounded archive probe did not expose a verified header; manual schema check needed.') from exc
        raise ValueError('No edge header in bounded archive probe.')
    else:raise ValueError('No safe streaming probe implemented for this source; manual verified import only.')


def scan_catalog(root,config):
    output=location(root,config,'processed')/'catalog'
    manifests=[]
    for spec in sources(root):
        path=directory_for(root,config,spec)/spec['filename']
        if path.is_file():
            try:record=DatasetAdapter(spec).inspect(path,output)
            except (ValueError,OSError,pd.errors.ParserError) as exc:record={**availability(spec),'reason':f'validation failed: {exc}'}
        else:record=availability(spec)
        manifests.append(record)
    return manifests
