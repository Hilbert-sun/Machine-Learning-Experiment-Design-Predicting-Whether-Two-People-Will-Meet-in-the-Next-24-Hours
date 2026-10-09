import gzip
import io
import zipfile

import pytest
from streamlit.testing.v1 import AppTest
from pathlib import Path
from src.dataset_catalog import DatasetAdapter,validate_probe


def spec():
    return {'dataset_id':'test_namespace','name':'fixture','source_url':'https://example.test','citation':'synthetic test fixture',
            'licence':'fixture only','access_status':'public','format':'triplet','temporal_resolution':20,
            'source_verified':True,'licence_verified':True,'scan_coverage_evidence':'none','coverage_supported':False}


def test_parser_namespace_missing_days_and_unknown_negatives(tmp_path):
    path=tmp_path/'events.dat';path.write_text('0 10 30\n20 30 10\n864000 10 50\n-1 10 20\n900000 10 10\n')
    adapter=DatasetAdapter(spec());report=adapter.inspect(path,tmp_path/'out')
    assert report['event_rows']==3 and report['participants']==3 and report['valid_pairs']==2
    assert report['invalid_rows']==1 and report['self_contact_rows']==1
    assert report['eligibility_status']=='exploratory_only'
    assert report['days_without_contact_records']>0
    assert report['usable_days_for_1d_3d_7d']['7']['primary_eligible_snapshots']==0
    assert adapter.inspect(path,tmp_path/'out')==report
    contacts=next((tmp_path/'out').rglob('contacts.parquet'));contacts.write_bytes(b'tampered')
    with pytest.raises(ValueError,match='checksum'):adapter.inspect(path,tmp_path/'out')


def test_zip_and_gzip_probe_and_parsing_and_restricted_acquisition(tmp_path):
    content=b'0 10 30\n20 30 10\n40 10 50\n'
    validate_probe(content,spec());validate_probe(gzip.compress(content),spec())
    path=tmp_path/'events.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('events.dat',content)
    validate_probe(path.read_bytes(),spec())
    assert DatasetAdapter(spec()).inspect(path,tmp_path/'out')['event_rows']==3
    with pytest.raises(ValueError,match='public source'):DatasetAdapter({**spec(),'access_status':'restricted'}).acquire(tmp_path,tmp_path/'out')
    with pytest.raises(ValueError,match='schema'):validate_probe(b'0 1 2 3\n0 1 2 3\n',spec())


def test_catalog_page_loads_empty_without_claiming_eligibility(tmp_path,monkeypatch):
    monkeypatch.setattr('yaml.safe_load',lambda _:{'paths':{n:str(tmp_path/n) for n in ('reports','models','features','processed','raw_copenhagen','raw_sociopatterns')}})
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py')).run().switch_page('pages/9_Dataset_Catalog.py').run()
    assert not app.exception and not app.metric
    next(b for b in app.button if b.label=='Scan Local Datasets').click().run()
    assert not app.exception
    assert app.dataframe[0].value.eligibility_status.eq('not_yet_verified').all()


def test_processed_time_ticks_are_not_invented_as_seconds_or_days(tmp_path):
    path=tmp_path/'processed.txt';path.write_text('15 11 233\n15 11 233\n11 4 232\n')
    s={**spec(),'column_order':['user_a','user_b','timestamp'],'timestamp_unit':'unverified integer tick'}
    r=DatasetAdapter(s).inspect(path,tmp_path/'out')
    assert r['participants']==3 and r['first_timestamp']==232 and r['last_timestamp']==233
    assert r['duplicate_canonical_records']==1
    assert r['span_days'] is None and r['per_day']==[]
    assert r['eligibility_status']=='exploratory_only'
    assert r['usable_days_for_1d_3d_7d']['7']['calendar_complete_snapshots'] is None


def test_social_evolution_requires_verified_timestamp_mapping_and_timezone(tmp_path):
    path=tmp_path/'Proximity.csv';path.write_text('user.id,remote.user.id.if.known,time,prob2\n10,20,2010-01-01 12:00:00,0.9\n')
    s={**spec(),'format':'social_evolution','column_mapping':{'user.id':'user_a','remote.user.id.if.known':'user_b','time':'timestamp'},'timestamp_encoding':'datetime'}
    with pytest.raises(ValueError,match='timezone'):DatasetAdapter(s).inspect(path,tmp_path/'bad')
    r=DatasetAdapter({**s,'timestamp_timezone':'America/New_York'}).inspect(path,tmp_path/'good')
    assert r['event_rows']==1 and r['first_timestamp']==1262365200
    with pytest.raises(ValueError,match='mapping'):DatasetAdapter({**s,'column_mapping':None}).inspect(path,tmp_path/'unverified')


def test_schema_and_unit_policy_changes_invalidate_catalog_cache(tmp_path):
    path=tmp_path/'events.dat';path.write_text('0 10 30\n864000 10 50\n')
    first=DatasetAdapter(spec()).inspect(path,tmp_path/'out')
    second=DatasetAdapter({**spec(),'timestamp_unit':'unverified integer tick'}).inspect(path,tmp_path/'out')
    assert first['span_days'] is not None and second['span_days'] is None
    assert len(list((tmp_path/'out').rglob('dataset_manifest.json')))==2


def test_manual_import_validates_before_publishing_and_never_overwrites_raw(tmp_path):
    adapter=DatasetAdapter({**spec(),'filename':'contacts.dat'})
    directory=tmp_path/'raw';directory.mkdir();(directory/'contacts.dat').write_text('0 1 2\n')
    with pytest.raises(ValueError,match='preserved'):
        adapter.import_file(io.BytesIO(b'0 3 4\n'),'different.dat',directory,tmp_path/'processed')
    assert (directory/'contacts.dat').read_text()=='0 1 2\n'
    with pytest.raises(ValueError,match='schema'):
        adapter.import_file(io.BytesIO(b'0 1 2 3\n'),'bad.dat',tmp_path/'newraw',tmp_path/'processed')
    assert not (tmp_path/'newraw/contacts.dat').exists()
