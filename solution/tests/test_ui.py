from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.config import Settings
from app.errors import AppError

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_ui_starts_without_model_call_and_mode_rerun_is_safe(monkeypatch):
    calls = []

    def unexpected_call(*args, **kwargs):
        calls.append(args)
        raise AssertionError("A mode change must not call the model")

    monkeypatch.setattr("app.agent.recommend", unexpected_call)
    monkeypatch.setattr("app.config.load_settings", lambda: Settings())
    app = AppTest.from_file(str(APP)).run(timeout=15)
    assert not app.exception
    assert app.title[0].value == "서울컬처픽"
    app.radio[0].set_value("live").run()
    assert not app.exception
    assert calls == []


def test_explicit_snapshot_retry_only(monkeypatch):
    calls = []

    def fail(question, mode, settings, report):
        calls.append(mode)
        raise AppError("seoul_connection", "연결 실패", allow_snapshot=mode == "live")

    monkeypatch.setattr("app.agent.recommend", fail)
    monkeypatch.setattr("app.config.load_settings", lambda: Settings())
    app = AppTest.from_file(str(APP)).run(timeout=15)
    app.radio[0].set_value("live").run()
    app.chat_input[0].set_value("종로 무료 전시").run(timeout=15)
    assert not app.exception
    assert calls == ["live"]
    app.run()
    assert calls == ["live"]
    retry = next(button for button in app.button if button.label == "저장 데이터로 다시 실행")
    retry.click().run(timeout=15)
    assert not app.exception
    assert calls == ["live", "snapshot"]
    assert app.radio[0].value == "snapshot"
