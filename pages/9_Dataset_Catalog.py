from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.dataset_catalog import sources,availability,directory_for,DatasetAdapter,scan_catalog
from src.window_ui import location

st.title("数据目录 · Dataset Catalog")
root=Path(__file__).resolve().parents[1]
config=yaml.safe_load((root/'configs/default.yaml').read_text())
registry=sources(root)
st.caption("各数据集匿名ID严格隔离。文件可读不代表可训练；无扫描覆盖证据时不把未观测接触当负例。")
records=st.session_state.get('catalog_records') or [availability(s) for s in registry]
st.dataframe(pd.DataFrame([{k:r.get(k) for k in ['name','access_status','eligibility_status','participants','event_rows','valid_pairs','reason']} for r in records]),hide_index=True)
spec=st.selectbox("Dataset Source",registry,format_func=lambda s:s['name'])
st.markdown(f"[官方/来源页面]({spec['source_url']})")
st.write("引用：",spec['citation'])
st.write("许可：",spec['licence'])
st.write("观测证据：",spec['scan_coverage_evidence'])
st.caption("下载/手动导入目录："+str(directory_for(root,config,spec)))
if st.button("Scan Local Datasets"):
    with st.spinner("校验字段、时间、匿名ID、源哈希及可用历史…"):
        st.session_state['catalog_records']=scan_catalog(root,config)
    st.rerun()
if st.button("Download Verified Source"):
    bar=st.progress(0.0,text="先验证小片段字段和许可")
    try:
        record=DatasetAdapter(spec).acquire(directory_for(root,config,spec),location(root,config,'processed')/'catalog',progress=lambda n,total:bar.progress(min(n/total,1.0) if total else 0.0,text=f"下载{n:,}字节"))
        st.json(record)
    except (ValueError,OSError,RuntimeError) as exc:st.error(str(exc))
    st.caption("现有Copenhagen/High School下载请使用Data Manager；此按钮仅处理有已核验公开下载路径的新适配器。")
upload=st.file_uploader("手动导入合法获取的接触文件",type=['csv','dat','txt','gz','bz2','zip'])
if upload is not None and st.button("Validate Imported File"):
    try:st.json(DatasetAdapter(spec).import_file(upload,upload.name,directory_for(root,config,spec),location(root,config,'processed')/'catalog'))
    except (ValueError,OSError,RuntimeError) as exc:st.error(str(exc))
for record in records:
    if record['dataset_id']==spec['dataset_id']:
        st.json(record)
        if record.get('per_day'):st.dataframe(pd.DataFrame(record['per_day']),hide_index=True)
