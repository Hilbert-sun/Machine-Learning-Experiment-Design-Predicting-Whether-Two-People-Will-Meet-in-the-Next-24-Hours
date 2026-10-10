"""T29 Select→Predict→Freeze→Reveal state, using T28 inference without evaluation queues."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from src.asof_inference import InferenceError, NAMESPACES, predict_as_of, reveal_outcome
from src.pipeline_cache import file_signatures


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, np.generic):
        return _clean(value.item())
    if isinstance(value,float) and not math.isfinite(value):
        return None  # Missing historical measurements remain unknown in frozen JSON.
    return value


def _encode(value):
    return json.dumps(_clean(value),sort_keys=True,ensure_ascii=False,allow_nan=False)


def data_version(processed, source):
    """Opaque snapshot metadata only, never a future observation/label query.

    Filesystem signatures detect ordinary version replacement/edit. Atomic
    ingestion/snapshot and adversarial same-metadata edits are separate work.
    """
    paths=[Path(source),processed.directory/'contacts.parquet',processed.directory/'observations.parquet']
    present=[p for p in paths if p.is_file()]
    record={'directory':str(processed.directory.resolve()),'report':processed.report,
            'files':file_signatures(present),'missing':[str(p) for p in paths if not p.is_file()]}
    return hashlib.sha256(_encode(record).encode()).hexdigest()


def context_key(processed, source, models, timestamp, a, b, mode):
    dependencies=[]
    for row in models.values():
        dependencies.extend([Path(row['directory'])/'manifest.json',Path(row['directory'])/'model.joblib',Path(row['evidence_path'])])
    record={'data_version':data_version(processed,source),'models':models,'model_versions':file_signatures(sorted(set(dependencies))),
            'timestamp':int(timestamp),'pair':sorted((int(a),int(b))),'mode':mode}
    return hashlib.sha256(_encode(record).encode()).hexdigest()


@dataclass
class TimeMachineSession:
    key: str | None = None
    stage: str = 'select'
    prediction_json: str | None = None
    frozen_json: str | None = None
    frozen_sha256: str | None = None
    outcome_json: str | None = None

    def select(self,key):
        if self.key != key:
            self.key=key
            self.stage='select'
            self.prediction_json=self.frozen_json=self.frozen_sha256=self.outcome_json=None
            return True
        return False

    def _current(self,key):
        if key != self.key:
            raise InferenceError('selection_changed: reselect and predict before freezing/revealing.')

    def predict(self,key,producer):
        self._current(key)
        self.stage='select'
        self.prediction_json=self.frozen_json=self.frozen_sha256=self.outcome_json=None
        payload=producer()
        self._current(key)
        if not isinstance(payload,dict):
            raise InferenceError('Prediction payload must be a structured record.')
        self.prediction_json=_encode({**payload,'selection_version':key})
        self.stage='predicted'
        return json.loads(self.prediction_json)

    def freeze(self,key):
        self._current(key)
        if self.stage not in ('predicted','frozen','revealed') or self.prediction_json is None:
            raise InferenceError('prediction_required: generate a prediction before Freeze.')
        if self.frozen_json is None:
            self.frozen_json=self.prediction_json
            self.frozen_sha256=hashlib.sha256(self.frozen_json.encode()).hexdigest()
            self.stage='frozen'
        return self.frozen_sha256

    def reveal(self,key,reader):
        self._current(key)
        if self.stage not in ('frozen','revealed') or self.frozen_json is None:
            raise InferenceError('freeze_required: Predict and Freeze must precede Reveal.')
        if hashlib.sha256(self.frozen_json.encode()).hexdigest()!=self.frozen_sha256:
            raise InferenceError('Frozen prediction integrity check failed.')
        if self.outcome_json is None:
            outcome=reader()
            self._current(key)
            self.outcome_json=_encode(outcome)
            self.stage='revealed'
        return json.loads(self.outcome_json)

    def prediction(self):
        content=self.frozen_json or self.prediction_json
        return json.loads(content) if content else None

    def outcome(self):
        return json.loads(self.outcome_json) if self.outcome_json else None


def make_prediction(processed,models,timestamp,a,b,*,mode='historical_blind_replay',clock_anchor=None,now_utc=None):
    """All probabilities/history come directly from T28; no outcome read here."""
    if not models:
        raise InferenceError('Choose at least one historical window.')
    cases={}
    for window,row in sorted(models.items()):
        expected=NAMESPACES.get(processed.report['dataset'])
        if row['window']!=window or row['dataset_id']!=expected:
            raise InferenceError('Selected model dataset/window mismatch.')
        cases[window]=predict_as_of(processed,row['directory'],timestamp,a,b,dataset_id=expected,history_window_days=window,
                                    mode=mode,evidence_path=row['evidence_path'],clock_anchor=clock_anchor,now_utc=now_utc)
    versions={}
    for w,row in models.items():
        manifest=json.loads((Path(row['directory'])/'manifest.json').read_text())
        record=json.loads(Path(row['evidence_path']).read_text())
        versions[w]={'name':row['model'],'run_id':row['run_id'],'artifact_version':manifest['version'],
                     'artifact_sha256':manifest['sha256'],'source_kind':record.get('source_kind','unverified')}
    return {'dataset_id':expected,'timestamp':int(timestamp),'pair':sorted((int(a),int(b))),
            'mode':mode,'models':versions,'cases':cases}


def reveal_prediction(processed,prediction):
    if prediction['mode']!='historical_blind_replay':
        raise InferenceError('Reveal is an explicit historical backtest, not prospective inference.')
    a,b=prediction['pair']
    return reveal_outcome(processed,prediction['timestamp'],a,b,backtest=True)


OUTCOME_REASONS={
    'observed_positive_evidence':'未来24小时内存在实际记录的设备接近事件。',
    'adequately_observed_no_contact':'未来窗口完整，两端扫描覆盖达到标准，未记录接触。扫描覆盖仍是代理证据。',
    'future_window_incomplete':'数据未覆盖完整未来24小时；未见记录不能证明未接触。',
    'scan_coverage_unknown':'缺少可核实的扫描可用性，无法可靠判定负例。',
    'scan_evidence_missing':'扫描证据文件不可用，不能把缺记录判成未接触。',
    'low_scan_coverage':'至少一端未来扫描覆盖不足；未见接触结果保留Unknown。',
}
