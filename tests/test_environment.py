"""Smoke checks for dependency imports, including native model libraries."""

import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "streamlit",
        "pandas",
        "numpy",
        "sklearn",
        "xgboost",
        "lightgbm",
        "plotly",
        "networkx",
        "requests",
        "pyarrow",
        "yaml",
        "pytest",
    ],
)
def test_dependency_import(module_name):
    importlib.import_module(module_name)
