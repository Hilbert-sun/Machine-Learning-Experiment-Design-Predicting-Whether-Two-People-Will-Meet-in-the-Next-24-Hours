"""Research page jobs: reuse frozen evidence or run new validation-only configurations."""

from dataclasses import asdict, dataclass
import hashlib
import html
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.metrics import precision_recall_curve

from src.baseline_audit import immutable_json, sha256
from src.calibration import calibrate_model, reliability_points
from src.evaluate import binary_metrics, choose_threshold
from src.label_builder import build_labels
from src.model_registry import ModelRegistry
from src.pipeline_cache import file_signatures
from src.preprocessing import preprocess_contacts
from src.temporal_split import chronological_split, validation_partition
from src.window_cohort import KEYS, DAY, build_comparison_cohort
from src.window_features import build_window_features
from src.window_study import PROTOCOL, fit_window, model_input, verify_exported_metrics


@dataclass(frozen=True)
class StudySettings:
    dataset: str = "Copenhagen"
    candidate_policy: str = "shared_1d"
    coverage: float = 0.5
    windows: tuple = (1, 3, 7)
    model: str = "xgboost"
    seed: int = 42
    calibrate: bool = False


def location(root, config, name):
    return Path(root)/config["paths"][name]


def source_path(root, config, dataset):
    if dataset=="Copenhagen":return location(root,config,"raw_copenhagen")/"bt_symmetric.csv"
    if dataset=="SocioPatterns":return location(root,config,"raw_sociopatterns")/"HighSchool2013_proximity_net.csv.gz"
    from src.dataset_catalog import sources,directory_for
    spec=next((s for s in sources(root) if dataset in (s['dataset_id'],s['name'])),None)
    if spec is None:raise ValueError('Unknown dataset namespace.')
    return directory_for(root,config,spec)/spec['filename']


def study_key(root, config, settings):
    paths = [source_path(root, config, settings.dataset),Path(root)/"configs/dataset_catalog.json"]
    for name in ("reports", "models", "features", "processed"):
        base = location(root, config, name)
        if base.exists():
            # Metadata/mtime changes invalidate displayed results without reading labels.
            paths += [p for p in base.rglob("*") if p.is_file() and p.suffix in {".json", ".joblib", ".parquet"}]
    signatures = file_signatures(sorted(set(p for p in paths if p.is_file())))
    return hashlib.sha256(json.dumps({"settings":asdict(settings),"files":signatures},sort_keys=True).encode()).hexdigest()


def run_study(root, config, settings, *, progress=None):
    root = Path(root)
    if settings.candidate_policy != "shared_1d":
        raise ValueError("7d候选池扩展仅报告覆盖范围；不能作为纯窗口效应主比较。")
    if not settings.windows or not set(settings.windows) <= {1,3,7} or settings.model not in PROTOCOL["models"]:
        raise ValueError("请选择1/3/7d窗口及已支持模型。")
    source = source_path(root,config,settings.dataset)
    if not source.is_file():
        raise ValueError("缺少本地接触主文件；请先在Data Manager或Dataset Catalog准备合法数据。")
    if settings.dataset != "Copenhagen":
        raise ValueError("该来源缺少可靠扫描覆盖证据，不能为未观测事件生成确定负例。")
    reports = location(root,config,"reports")/"window_study"
    frozen_path = reports/"T22_ROBUSTNESS.json"
    frozen_settings = settings.coverage==0.5 and settings.seed==42 and not settings.calibrate
    if frozen_path.is_file() and frozen_settings:
        if progress: progress(0.1,"验证冻结研究结果")
        from src.window_verify import verify_study
        # The original study uses the repository paths; custom paths use the new job branch.
        if reports.resolve() == (root/"reports/window_study").resolve():
            verify_study(root)
            robust = json.loads(frozen_path.read_text())
            directory = reports/robust["run_id"]
            records = [json.loads((directory/f"{stage}_RESULTS.json").read_text()) for stage in ("T21","T22")]
            paths = {int(w):p for record in records for w,p in record["model_artifacts"].items()}
            predictions = {int(w):str(directory/p["filename"]) for record in records for w,p in record["predictions_local_ignored"].items()}
            receipt = json.loads((root/"data/features/window_study/T20_FEATURES.json").read_text())
            cohort = json.loads((root/"data/processed/window_study/T19_COHORT_MANIFEST.json").read_text())
            result = {"run_id":robust["run_id"],"scope":"frozen_test","settings":asdict(settings),"source_kind":"real_public_dataset",
                      "metrics":[r for r in robust["main_metrics"] if r["model"]==settings.model and r["window_days"] in settings.windows],
                      "cohort":cohort,"prediction_paths":{str(w):predictions[w] for w in settings.windows},
                      "feature_paths":{str(w):str(root/receipt[str(w)]["path"]) for w in settings.windows},
                      "models":{str(w):{settings.model:str(root/paths[w][settings.model])} for w in settings.windows},
                      "information_deadline":int(cohort["support"]["sets"]["validation"]["prediction_times"][-1]+DAY),
                      "calibration_method":None,"calibration_reason":PROTOCOL["calibration_reason"],
                      "paired_uncertainty":robust["paired_uncertainty"],"candidate_expansion":robust["candidate_pool_expansion_counts_only"]}
            if progress: progress(1.0,"冻结结果和模型验签完成")
            return result
    if progress: progress(0.05,"构建独立配置；新配置只评估validation，保护已报告测试集")
    version = hashlib.sha256(json.dumps({"settings":asdict(settings),"source_sha256":sha256(source),"job_version":1},sort_keys=True).encode()).hexdigest()[:16]
    directory = reports/"ui_jobs"/version
    result_path = directory/"result.json"
    if result_path.is_file():
        result = json.loads(result_path.read_text())
        for path, expected in result["artifact_hashes"].items():
            if sha256(path) != expected: raise ValueError("研究缓存文件已改变；不能显示旧配置结果。")
        if progress: progress(1.0,"复用同配置的真实作业缓存")
        return result
    processed = preprocess_contacts(source,"Copenhagen",location(root,config,"processed"))
    labels = build_labels(processed,location(root,config,"processed")/"window_ui_labels",min_scan_coverage=settings.coverage)
    cohort_artifact, audit = build_comparison_cohort(processed,labels,location(root,config,"processed")/"window_ui"/version)
    if audit["support"]["status"] != "ready": raise ValueError("insufficient_days：共同样本无法形成可靠时间切分。")
    cohort = pd.read_parquet(cohort_artifact.path)
    split = chronological_split(cohort)
    calibration, tuning = None, split.validation
    if settings.calibrate:
        try: calibration,tuning = validation_partition(split.validation)
        except ValueError as exc: raise ValueError(f"无可用独立校准段：{exc}") from exc
        if tuning.timestamp.nunique()<2 or min(calibration.label_24h.value_counts().reindex([0,1],fill_value=0))<20:
            raise ValueError("校准独立日期/类别不足；请关闭Calibrate，不能放宽时间隔离。")
    immutable_json(directory/"protocol.json",{"settings":asdict(settings),"scope":"validation_only","cohort_label_hash":audit["label_hash"],"parameters":PROTOCOL["parameters"][settings.model]})
    metrics,predictions,models,features = [],{},{},{}
    for i,days in enumerate(settings.windows):
        if progress: progress(0.15+0.7*i/len(settings.windows),f"计算{days}d特征并训练{settings.model}")
        bank = build_window_features(processed,cohort_artifact,location(root,config,"features")/"window_ui"/version,history_window_days=days,min_scan_coverage=settings.coverage)
        frame = pd.read_parquet(bank.path)
        protocol = {**PROTOCOL,"models":[settings.model],"seed":settings.seed}
        fitted,_ = fit_window(frame,split.train,tuning,days,protocol)
        model = fitted[settings.model]
        if calibration is not None:
            model = calibrate_model(model,model_input(frame,calibration,days),calibration.label_24h)
            model.threshold = choose_threshold(tuning.label_24h,model.predict_proba(model_input(frame,tuning,days))[:,1])
        probability = model.predict_proba(model_input(frame,tuning,days))[:,1]
        metrics.append({"window_days":days,"model":settings.model,**binary_metrics(tuning.label_24h,probability,threshold=model.threshold)})
        exported = tuning.copy().reset_index(drop=True).assign(**{f"p_{settings.model}":probability,f"threshold_{settings.model}":model.threshold})
        path = directory/f"predictions_{days}d.parquet"; exported.to_parquet(path,index=False)
        predictions[str(days)] = str(path)
        features[str(days)] = str(bank.path)
        models[str(days)] = {settings.model:str(ModelRegistry.save(model,location(root,config,"models")/".window_study/ui"/version/f"{days}d",metadata={"scope":"validation_only","settings":asdict(settings)}))}
    result = {"run_id":version,"scope":"validation_only","settings":asdict(settings),"source_kind":"real_public_dataset",
              "metrics":metrics,"cohort":audit,"prediction_paths":predictions,"feature_paths":features,"models":models,
              "information_deadline":int(split.validation.timestamp.max()+DAY),"calibration_method":"sigmoid" if settings.calibrate else None,
              "calibration_reason":"requested independent calibration" if settings.calibrate else "not requested"}
    dependencies = list(predictions.values())+list(features.values())+[str(source)]
    for window in models.values():
        for path in window.values(): dependencies += [str(Path(path)/n) for n in ("manifest.json","model.joblib")]
    result["artifact_hashes"] = {p:sha256(p) for p in dependencies}
    immutable_json(result_path,result)
    if progress: progress(1.0,"实际validation作业已保存，测试集未参与选择")
    return result


def study_figures(result):
    figures = {}
    table = pd.DataFrame(result["metrics"]).sort_values("window_days")
    for metric in ("pr_auc_average_precision","roc_auc","brier_score","log_loss"):
        figures[metric] = go.Figure(go.Scatter(x=table.window_days,y=table[metric],mode="lines+markers"))
        figures[metric].update_layout(title=f"{metric} · {result['scope']}",xaxis_title="History days")
    pr,calibration,daily,delta = go.Figure(),go.Figure(),go.Figure(),go.Figure()
    per_window = {}
    name = result["settings"]["model"]
    for window,path in result["prediction_paths"].items():
        frame = pd.read_parquet(path)
        p = frame[f"p_{name}"]
        precision,recall,_ = precision_recall_curve(frame.label_24h,p)
        pr.add_scatter(x=recall,y=precision,name=f"{window}d")
        points = reliability_points(frame.label_24h,p)
        calibration.add_scatter(x=[r['mean_probability'] for r in points],y=[r['observed_fraction'] for r in points],mode="lines+markers",name=f"{window}d")
        day_rows = [{"day":int(t//DAY+1),"ap":binary_metrics(g.label_24h,g[f'p_{name}'])["pr_auc_average_precision"]} for t,g in frame.groupby("timestamp")]
        per_window[window] = day_rows
        daily.add_scatter(x=[r['day'] for r in day_rows],y=[r['ap'] for r in day_rows],mode="lines+markers",name=f"{window}d")
    calibration.add_scatter(x=[0,1],y=[0,1],name="ideal",mode="lines")
    pr.update_layout(title="PR curves",xaxis_title="Recall",yaxis_title="Precision")
    calibration.update_layout(title="Reliability · "+str(result["calibration_method"] or "raw probabilities"))
    daily.update_layout(title="AP by prediction Study Day")
    if "1" in per_window and "7" in per_window:
        a,b = per_window['1'],per_window['7']
        delta.add_scatter(x=[r['day'] for r in a],y=[y['ap']-x['ap'] if x['ap'] is not None and y['ap'] is not None else None for x,y in zip(a,b)],mode="lines+markers")
        delta.add_hline(y=0,line_dash="dash")
        delta.update_layout(title="Paired7d−1d AP by day; descriptive")
        figures['paired_delta'] = delta
    figures.update(pr=pr,calibration=calibration,per_day=daily)
    return figures


def export_study(result):
    csv = pd.DataFrame(result["metrics"]).to_csv(index=False).encode('utf-8-sig')
    public = {k:result[k] for k in ("run_id","scope","settings","source_kind","metrics","calibration_method","calibration_reason","cohort")}
    fragments = ["<!doctype html><html><meta charset='utf-8'><body><h1>History Window Study</h1>","<pre>"+html.escape(json.dumps(public,ensure_ascii=False,indent=2))+"</pre>"]
    for i,figure in enumerate(study_figures(result).values()): fragments.append(figure.to_html(full_html=False,include_plotlyjs=True if i==0 else False))
    fragments.append("</body></html>")
    return csv,json.dumps(public,ensure_ascii=False,indent=2).encode(),''.join(fragments).encode()


def case_keys(result):
    first = next(iter(result["feature_paths"].values()))
    # Never read target or future coverage for future-mode selection/prediction.
    return pd.read_parquet(first,columns=KEYS)


def predict_case(result,t,a,b,*,backtest=False):
    a,b = sorted((int(a),int(b)))
    if a==b or int(t)<=result["information_deadline"]:
        raise ValueError("预测时点必须晚于模型选择信息截止时刻，且匿名ID不同。")
    key = pd.DataFrame([{"dataset_id":"copenhagen","timestamp":int(t),"user_min":a,"user_max":b}])
    name = result["settings"]["model"]
    response = {"probabilities":{},"historical_features":{}}
    for window,path in result["feature_paths"].items():
        bank = pd.read_parquet(path)
        selected = key.merge(bank,on=KEYS,validate="one_to_one")
        if len(selected)!=1: raise ValueError("该配对/时点不在共同历史候选集中。")
        X = model_input(bank,key,int(window))
        model = ModelRegistry.load(result['models'][window][name])
        response['probabilities'][window] = float(model.predict_proba(X)[0,1])
        response['historical_features'][window] = X.iloc[0].to_dict()
    if backtest:
        frame = pd.read_parquet(next(iter(result['prediction_paths'].values())),columns=KEYS+['label_24h'])
        target = key.merge(frame,on=KEYS)
        response['actual_outcome'] = None if target.empty else int(target.label_24h.iloc[0])
    return response
