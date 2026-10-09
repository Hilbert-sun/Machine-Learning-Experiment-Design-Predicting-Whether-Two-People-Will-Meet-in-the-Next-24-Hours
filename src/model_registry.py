"""Shared fit/predict contract; model inputs are restricted to historical features."""

from dataclasses import dataclass, field
import hashlib
from importlib.metadata import version as package_version
import json
from pathlib import Path
import platform
import tempfile
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.baselines import ConstantProbability, HistoricalPairFrequency, TimeBasedRule
from src.feature_engineering import FEATURE_NAMES
from src.feature_policy import feature_window_view
from src.temporal_split import TrainingDataError

BASELINES = ("constant", "historical_frequency", "time_rule", "logistic_regression", "random_forest")
MAIN_MODELS = ("xgboost", "lightgbm")


def _numeric(X):
    if not isinstance(X, pd.DataFrame) or set(X.columns) - set(FEATURE_NAMES):
        raise TrainingDataError("模型输入只能包含历史特征白名单，不能包含配对键、目标或未来观测字段。")
    frame = X.apply(pd.to_numeric, errors="raise")
    if np.isinf(frame.to_numpy(dtype=float)).any():
        raise TrainingDataError("模型输入不能包含无穷值。")
    return frame


@dataclass
class RegisteredModel:
    name: str
    estimator: object
    parameters: dict
    seed: int
    feature_columns: list = field(default_factory=list)
    threshold: float = 0.5
    fitted: bool = False
    feature_window_days: int | None = None
    feature_reference: dict = field(default_factory=dict)

    def fit(self, X, y):
        X = feature_window_view(_numeric(X), self.feature_window_days)
        y = np.asarray(y)
        if len(X) != len(y) or len(y) == 0 or not np.isin(y, [0, 1]).all():
            raise TrainingDataError("模型目标必须是与特征一一对应的已知二元标签。")
        self.feature_columns = [name for name in X.columns if X[name].notna().any()]
        self.feature_reference = {name: float(X[name].median()) for name in self.feature_columns}
        if not self.feature_columns and self.name not in BASELINES[:3]:
            raise TrainingDataError("训练集没有可用数值特征。")
        self.estimator.fit(X.loc[:, self.feature_columns], y)
        self.fitted = True
        return self

    def predict_proba(self, X):
        if not self.fitted:
            raise TrainingDataError("模型尚未训练。")
        X = feature_window_view(_numeric(X), self.feature_window_days)
        if set(self.feature_columns) - set(X.columns):
            raise TrainingDataError("预测特征缺少模型训练时的字段。")
        probabilities = np.asarray(self.estimator.predict_proba(X.loc[:, self.feature_columns]), dtype=float)
        if probabilities.shape != (len(X), 2) or not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any() or not np.allclose(probabilities.sum(axis=1), 1):
            raise TrainingDataError("模型返回无效的二元概率。")
        return probabilities

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= self.threshold).astype("int8")


class ModelRegistry:
    @staticmethod
    def names():
        return BASELINES + MAIN_MODELS

    @staticmethod
    def create(name, *, seed=42, parameters=None, feature_window_days=None):
        parameters = dict(parameters or {})
        if "random_state" in parameters or "n_jobs" in parameters:
            raise TrainingDataError("random_state/n_jobs由统一运行配置控制。")
        if name in BASELINES[:3]:
            constructor = {"constant": ConstantProbability, "historical_frequency": HistoricalPairFrequency, "time_rule": TimeBasedRule}[name]
            return RegisteredModel(name, constructor(**parameters), parameters, seed, feature_window_days=feature_window_days)
        defaults = {"random_state": seed}
        if name == "logistic_regression":
            defaults.update(max_iter=1000)
            defaults.update(parameters)
            classifier = LogisticRegression(**defaults)
        elif name == "random_forest":
            defaults.update(n_estimators=200, min_samples_leaf=2, n_jobs=1)
            defaults.update(parameters)
            classifier = RandomForestClassifier(**defaults)
        elif name == "xgboost":
            from xgboost import XGBClassifier
            defaults.update(n_estimators=200, max_depth=4, learning_rate=0.05, n_jobs=1, objective="binary:logistic", eval_metric="logloss")
            defaults.update(parameters)
            classifier = XGBClassifier(**defaults)
        elif name == "lightgbm":
            from lightgbm import LGBMClassifier
            defaults.update(n_estimators=200, learning_rate=0.05, n_jobs=1, objective="binary", verbosity=-1, deterministic=True, force_col_wise=True)
            defaults.update(parameters)
            classifier = LGBMClassifier(**defaults)
        else:
            raise TrainingDataError(f"不支持的模型：{name}")
        steps = [("imputer", SimpleImputer(strategy="median", add_indicator=True).set_output(transform="pandas"))]
        if name == "logistic_regression":
            steps.append(("scaler", StandardScaler()))
        steps.append(("classifier", classifier))
        return RegisteredModel(name, Pipeline(steps), defaults, seed, feature_window_days=feature_window_days)

    @staticmethod
    def save(model, root, *, metadata=None):
        if model.name not in ModelRegistry.names():
            raise TrainingDataError("只能保存已注册的模型。")
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        version = uuid4().hex[:12]
        destination = root / f"{model.name}-{version}"
        with tempfile.TemporaryDirectory(prefix=".model-", dir=root) as temporary:
            folder = Path(temporary)
            path = folder / "model.joblib"
            joblib.dump(model, path, compress=3)
            with path.open("rb") as handle:
                checksum = hashlib.file_digest(handle, "sha256").hexdigest()
            manifest = {"schema_version": 1, "version": version, "model_name": model.name,
                        "feature_columns": model.feature_columns, "threshold": model.threshold, "seed": model.seed,
                        "parameters": model.parameters, "calibration_method": getattr(model, "method", None),
                        "feature_window_days": model.feature_window_days,
                        "sha256": checksum, "python_version": platform.python_version(),
                        "package_versions": {name: package_version(name) for name in ("numpy", "pandas", "scikit-learn", "xgboost", "lightgbm", "joblib")},
                        "metadata": metadata or {}}
            (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False))
            folder.rename(destination)
        return destination

    @staticmethod
    def load(directory):
        # Only load artifacts produced locally by this registry; never uploaded pickles.
        directory = Path(directory)
        manifest = json.loads((directory / "manifest.json").read_text())
        if manifest["schema_version"] != 1 or manifest["model_name"] not in ModelRegistry.names():
            raise TrainingDataError("不支持的模型清单。")
        path = directory / "model.joblib"
        with path.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        if checksum != manifest["sha256"]:
            raise TrainingDataError("模型文件校验失败。")
        if any(package_version(name) != expected for name, expected in manifest["package_versions"].items()):
            raise TrainingDataError("模型依赖版本与保存时不一致，请使用清单记录的环境。")
        model = joblib.load(path)
        if model.name != manifest["model_name"] or model.feature_columns != manifest["feature_columns"] or model.threshold != manifest["threshold"] or model.feature_window_days != manifest.get("feature_window_days"):
            raise TrainingDataError("模型对象与清单不一致。")
        return model

    @staticmethod
    def list_saved(root):
        records = []
        for path in sorted(Path(root).rglob("manifest.json")):
            if any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
            record = json.loads(path.read_text())
            records.append({"path": str(path.parent), "model_name": record["model_name"], "version": record["version"], "threshold": record["threshold"], "calibration_method": record["calibration_method"], "feature_window_days": record.get("feature_window_days")})
        return records
