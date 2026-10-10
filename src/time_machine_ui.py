"""Independent Time Machine page; future evidence is opened only by Reveal."""

import pandas as pd
import streamlit as st

from src.asof_inference import MODES,NAMESPACES,InferenceError,as_of_candidates
from src.asof_ui import available_models
from src.dataset_catalog import sources
from src.preprocessing import cached_dataset
from src.time_machine import TimeMachineSession,context_key,data_version,make_prediction,reveal_prediction,OUTCOME_REASONS
from src.window_ui import location,source_path


def render_time_machine(root,config):
    session=st.session_state.setdefault('time_machine_session',TimeMachineSession())
    st.caption('Select → Predict → Freeze → Reveal。只预测匿名设备未来24小时接近；历史回放按记录事件时间模拟。')
    datasets=['Copenhagen','SocioPatterns']+[s['name'] for s in sources(root) if s['dataset_id'] not in {'copenhagen','highschool2013'}]
    dataset=st.selectbox('Time Machine Dataset',datasets)
    def unavailable(message):
        session.select('unavailable:'+dataset+':'+message)
        st.info(message)
    if dataset not in NAMESPACES:
        unavailable('该来源尚无可核实的二分类推理模型/观测契约；请查看Dataset Catalog的限制。')
        return
    source=source_path(root,config,dataset)
    if not source.is_file():
        unavailable('缺少本地数据；请先在Data Manager准备合法来源。')
        return
    processed=cached_dataset(source,dataset,location(root,config,'processed'))
    if processed is None:
        unavailable('缺少与当前数据版本匹配的已验证接触/扫描缓存。')
        return
    rows=available_models(root,config,dataset)
    if not rows:
        unavailable('尚无可核实数据集、窗口和标签信息截止时间的保存模型。')
        return
    families=sorted({(r['run_id'],r['model']) for r in rows},key=lambda key:(key[1]!='xgboost',key))
    family=st.selectbox('Time Machine Model',families,format_func=lambda key:f'{key[1]} · {key[0]}')
    choices={r['window']:r for r in rows if (r['run_id'],r['model'])==family}
    windows=st.multiselect('History Windows',[w for w in (1,3,7) if w in choices],default=sorted(choices))
    mode=st.radio('Time Machine Mode',MODES)
    deadline=max(r['deadline'] for r in choices.values())
    day=st.number_input('Prediction Study Day',min_value=1,value=deadline//86400+2,step=1)
    hour=st.number_input('Prediction Hour',min_value=0,max_value=23,value=8,step=1)
    timestamp=(int(day)-1)*86400+int(hour)*3600
    if not windows:
        unavailable('请选择至少一个1/3/7天历史窗口。')
        return
    models={int(w):choices[w] for w in windows}
    st.dataframe(pd.DataFrame([{'history_days':w,'model':r['model'],'label_information_deadline_seconds':r['deadline'],
                               'deadline_study_day':r['deadline']//86400+1} for w,r in models.items()]),hide_index=True)
    if timestamp<=max(r['deadline'] for r in models.values()):
        unavailable('所选时刻不晚于模型训练/验证/阈值标签信息截止时间，不能模拟当时预测。')
        return
    if mode=='prospective_inference':
        st.warning('静态档案没有可信实时UTC时间锚点。Predict将执行T28时钟/近期扫描检查并拒绝冒充实时预测；请使用historical_blind_replay。')
    try:
        keys=as_of_candidates(processed,timestamp,dataset_id=NAMESPACES[dataset])
    except (ValueError,OSError) as exc:
        unavailable(str(exc))
        return
    st.caption(f'仅依据[t-1d,t)接触：{len(keys):,} 个候选；候选未经过未来扫描覆盖率筛选。')
    if keys.empty:
        unavailable('该时点前24小时没有历史接触候选配对。')
        return
    a=st.selectbox('Anonymous Person A',sorted(keys.user_min.unique()))
    b=st.selectbox('Anonymous Person B',sorted(keys.loc[keys.user_min.eq(a),'user_max'].unique()))
    try:
        key=context_key(processed,source,models,timestamp,int(a),int(b),mode)
    except (OSError,ValueError) as exc:
        unavailable(f'数据/模型版本不可用：{exc}')
        return
    if session.select(key):
        st.caption('选择或数据/模型版本已改变，旧预测与揭晓结果已失效。')
    st.caption('数据版本：'+data_version(processed,source)[:16])
    stage_display=st.empty()
    def checked(action):
        # Reject edits during an action instead of attaching results to a different version.
        current=context_key(processed,source,models,timestamp,int(a),int(b),mode)
        if current!=key:
            session.select(current)
            raise InferenceError('data_or_model_version_changed: reselect and predict.')
        value=action()
        current=context_key(processed,source,models,timestamp,int(a),int(b),mode)
        if current!=key:
            session.select(current)
            raise InferenceError('data_or_model_version_changed: reselect and predict.')
        return value
    if st.button('Predict'):
        try:
            with st.spinner('只计算t之前的候选/特征和保存模型概率…'):
                session.predict(key,lambda:checked(lambda:make_prediction(processed,models,timestamp,int(a),int(b),mode=mode)))
        except (ValueError,OSError,KeyError,RuntimeError) as exc:
            st.error(str(exc))
    if st.button('Freeze Prediction',disabled=session.stage!='predicted'):
        try:
            checked(lambda:session.freeze(key))
        except (ValueError,OSError) as exc:
            session.select('invalid_version')
            st.error(str(exc))
    if st.button('Reveal Next24h',disabled=session.stage not in ('frozen','revealed') or mode!='historical_blind_replay'):
        try:
            session.reveal(key,lambda:checked(lambda:reveal_prediction(processed,session.prediction())))
        except (ValueError,OSError,KeyError,RuntimeError) as exc:
            st.error(str(exc))
    stage_display.write('当前阶段：'+session.stage)
    prediction=session.prediction()
    if prediction:
        st.subheader('历史预测（未作为新评估指标）')
        if any(r.get('source_kind')!='real_public_dataset' for r in prediction['models'].values()):
            st.warning('模型来源为合成测试或未核验类别；只展示实际计算结果，不作为真实研究证据。')
        for w,case in prediction['cases'].items():
            st.metric(f'{w}d历史 · 未来24h记录接近概率',f"{case['probability']:.2%}")
        st.dataframe(pd.DataFrame({w:c['historical_features'] for w,c in prediction['cases'].items()}).T,hide_index=False)
        st.caption('历史统计均来自t前；缺失统计保持未知。旧评估指标不能保证扩大候选总体的概率校准。')
        with st.expander('模型版本与标签信息截止时间'):
            st.json({'selection_version':prediction['selection_version'],'models':prediction['models'],
                     'label_information_ends':{w:c['label_information_ends'] for w,c in prediction['cases'].items()}})
        if session.frozen_sha256:
            st.success('预测已冻结：'+session.frozen_sha256)
        else:
            st.info('预测尚未冻结。先Freeze Prediction，再独立Reveal。')
    outcome=session.outcome()
    if outcome:
        st.subheader('Actual Outcome: '+outcome['outcome'])
        st.write(OUTCOME_REASONS.get(outcome['reason'],outcome['reason']))
        if 'coverage' in outcome:st.json({'future_coverage_revealed_only_now':outcome['coverage']})
