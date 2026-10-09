"""Verify data status transitions through the actual Streamlit page."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.downloader import RemoteFile

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def manager(monkeypatch, tmp_path):
    (tmp_path / "raw").mkdir()
    monkeypatch.setattr("yaml.safe_load", lambda _: {"paths": {
        "raw_copenhagen": str(tmp_path / "raw"), "raw_sociopatterns": str(tmp_path / "raw"),
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
