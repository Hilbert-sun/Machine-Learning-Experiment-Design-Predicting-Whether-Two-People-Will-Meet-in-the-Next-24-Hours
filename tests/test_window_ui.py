from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from src.window_ui import StudySettings, study_key, run_study, predict_case
from src.window_study import fit_window
from src.model_registry import ModelRegistry
from test_window_study import small_inputs

APP = str(Path(__file__).resolve().parents[1]/'app.py')


def test_research_empty_state_missing_source_and_setting_invalidations(tmp_path,monkeypatch):
    config = {'paths':{n:str(tmp_path/n) for n in ('reports','models','features','processed','raw_copenhagen','raw_sociopatterns')}}
    monkeypatch.setattr('yaml.safe_load',lambda _:config)
    app = AppTest.from_file(APP).run().switch_page('pages/8_History_Window_Study.py').run()
    assert not app.exception and not app.metric
    assert any('尚未运行' in m.value for m in app.info)
    next(b for b in app.button if b.label=='Run Study').click().run()
    assert not app.exception and any('缺少本地' in e.value for e in app.error)
    first = study_key(tmp_path,config,StudySettings())
    assert first!=study_key(tmp_path,config,StudySettings(coverage=0.75))
    with pytest.raises(ValueError,match='候选池扩展'):
        run_study(tmp_path,config,StudySettings(candidate_policy='expanded_7d_counts_only'))


def test_future_case_never_reads_labels_and_rejects_preselection_dates(tmp_path,monkeypatch):
    frame,bank = small_inputs()
    train = frame.loc[frame.split.eq('train')]; validation=frame.loc[frame.split.eq('validation')]
    models,_ = fit_window(bank,train,validation,1,{"models":["logistic_regression"],"seed":42,"parameters":{"logistic_regression":{}}})
    feature = tmp_path/'features.parquet';bank.to_parquet(feature,index=False)
    path = ModelRegistry.save(models['logistic_regression'],tmp_path/'models')
    result={'information_deadline':int(validation.timestamp.max()+86400),'feature_paths':{'1':str(feature)},
            'models':{'1':{'logistic_regression':str(path)}},'settings':{'model':'logistic_regression'},'prediction_paths':{'1':str(tmp_path/'FORBIDDEN_TARGETS.parquet')}}
    row = frame.loc[frame.timestamp.gt(result['information_deadline'])].iloc[0]
    actual_read = pd.read_parquet
    def guarded(path,*args,**kwargs):
        assert 'FORBIDDEN' not in str(path)
        return actual_read(path,*args,**kwargs)
    monkeypatch.setattr(pd,'read_parquet',guarded)
    case = predict_case(result,int(row.timestamp),int(row.user_min),int(row.user_max))
    assert 'actual_outcome' not in case and 0<=case['probabilities']['1']<=1
    with pytest.raises(ValueError,match='截止'):
        predict_case(result,result['information_deadline'],1,2)
