"""Verify data status transitions through the actual Streamlit page."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.downloader import RemoteFile

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def manager(monkeypatch, tmp_path):
    (tmp_path / "raw").mkdir()
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {
        "raw_copenhagen": str(tmp_path / "raw"), "raw_sociopatterns": str(tmp_path / "raw"),
        "processed": str(tmp_path / "processed"),
        "features": str(tmp_path / "features"),
        "models": str(tmp_path / "models"), "reports": str(tmp_path / "reports"),
    }})
    return AppTest.from_file(APP).run().switch_page("pages/1_Data_Manager.py").run()


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception
    return app


def test_ready_requires_valid_primary_file_and_invalidates_when_changed(monkeypatch, tmp_path):
    app = manager(monkeypatch, tmp_path)
    path = tmp_path / "raw" / "bt_symmetric.csv"
    path.write_text("# timestamp,user_a,user_b,rssi\n0,5,-1,0\n300,5,97,-60\n")
    app.run()
    click(app, "验证本地数据")
    assert any("Ready" in message.value for message in app.success)
    path.write_text("timestamp,user_a,user_b,rssi\n0,5,invalid,-60\n")
    app.run()
    assert not any("Ready" in message.value for message in app.success)
    click(app, "验证本地数据")
    assert any("Validation Failed" in message.value for message in app.error)


def test_calls_alone_never_marks_dataset_ready(monkeypatch, tmp_path):
    app = manager(monkeypatch, tmp_path)
    (tmp_path / "raw" / "calls.csv").write_text("timestamp,caller,callee,duration\n0,5,97,-1\n")
    app.run()
    click(app, "验证本地数据")
    assert not app.success
    assert any("缺少主接触文件" in message.value for message in app.warning)


def test_download_action_calls_backend_and_displays_failure(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        from src.downloader import DownloadError
        raise DownloadError("offline: 请手动上传")

    monkeypatch.setattr("src.downloader.download_file", fail)
    app = manager(monkeypatch, tmp_path)
    app.session_state["copenhagen_files"] = [RemoteFile("bt_symmetric.csv", "https://example.org/from-api")]
    app.run()
    app.multiselect[0].select("bt_symmetric.csv").run()
    click(app, "下载所选文件")
    assert any("手动上传" in message.value for message in app.error)


def test_empty_directory_disables_validation(monkeypatch, tmp_path):
    app = manager(monkeypatch, tmp_path)
    assert next(button for button in app.button if button.label == "验证本地数据").disabled
    assert any("Not Downloaded" in message.value for message in app.info)


def test_preprocess_button_writes_cache_and_source_change_removes_processed_status(monkeypatch, tmp_path):
    app = manager(monkeypatch, tmp_path)
    assert next(button for button in app.button if button.label == "运行预处理").disabled
    path = tmp_path / "raw" / "bt_symmetric.csv"
    path.write_text("# timestamp,user_a,user_b,rssi\n0,5,-1,0\n300,5,97,-60\n300,97,5,-60\n")
    app.run()
    assert next(button for button in app.button if button.label == "运行预处理").disabled
    click(app, "验证本地数据")
    click(app, "运行预处理")
    assert any("Processed · 1 条有效接触" in message.value for message in app.success)
    assert len(list((tmp_path / "processed").rglob("contacts.parquet"))) == 1
    click(app, "运行预处理")
    assert len(list((tmp_path / "processed").rglob("contacts.parquet"))) == 1
    path.write_text(path.read_text() + "600,5,222,-70\n")
    app.run()
    assert not any("Processed" in message.value for message in app.success)
    assert next(button for button in app.button if button.label == "运行预处理").disabled


def test_preprocessing_failure_displays_recovery_without_processed_status(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise OSError("output unavailable")

    monkeypatch.setattr("src.preprocessing.preprocess_contacts", fail)
    app = manager(monkeypatch, tmp_path)
    (tmp_path / "raw" / "bt_symmetric.csv").write_text("timestamp,user_a,user_b,rssi\n0,5,97,-65\n")
    app.run()
    click(app, "验证本地数据")
    click(app, "运行预处理")
    assert any("预处理失败" in message.value and "重试" in message.value for message in app.error)
    assert not any("Processed" in message.value for message in app.success)


def test_sociopatterns_processing_explains_unknown_scan_coverage(monkeypatch, tmp_path):
    app = manager(monkeypatch, tmp_path)
    (tmp_path / "raw" / "HighSchool2013_proximity_net.csv").write_text("1385982020 97 5 MP PC\n")
    app.selectbox[0].select("SocioPatterns").run()
    click(app, "验证本地数据")
    click(app, "运行预处理")
    assert any("Processed" in message.value for message in app.success)
    assert any("覆盖率未知" in message.value for message in app.info)


def test_labels_and_features_flow_keeps_unknown_coverage_out_of_main_evaluation(monkeypatch, tmp_path):
    app = manager(monkeypatch, tmp_path)
    (tmp_path / "raw" / "HighSchool2013_proximity_net.csv").write_text("0 5 97 MP PC\n28801 5 97 MP PC\n259200 5 97 MP PC\n")
    app.selectbox[0].select("SocioPatterns").run()
    click(app, "验证本地数据")
    click(app, "运行预处理")
    click(app, "生成24小时标签")
    assert any("正例 1，负例 0，未知 1" in message.value for message in app.success)
    assert any("没有满足覆盖策略" in message.value for message in app.info)
    click(app, "生成历史特征")
    assert any("历史特征缓存：2 行" in message.value for message in app.success)
    assert len(list((tmp_path / "features").glob("*.parquet"))) == 1
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {
        "raw_copenhagen": str(tmp_path / "raw"), "raw_sociopatterns": str(tmp_path / "raw"),
        "processed": str(tmp_path / "processed"), "features": str(tmp_path / "features"),
    }, "features": {"enable_communications": True}})
    app.run()
    assert not any("历史特征缓存" in message.value for message in app.success)
    click(app, "生成历史特征")
    assert any("禁止启用" in message.value for message in app.error)
    app.number_input[0].set_value(0.75).run()
    assert next(button for button in app.button if button.label == "生成历史特征").disabled
