from pathlib import Path

from streamlit.testing.v1 import AppTest

import requests


APP_PATH = Path(__file__).parents[1] / "streamlit_app.py"


class FakeResponse:
    ok = True
    text = ""

    def __init__(self, payload=None):
        self.payload = payload or {
            "answer": "Grounded response [guide.txt::0].",
            "sources": [],
            "interaction_id": "interaction-1",
        }

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


def test_architecture_queries_reuse_a_persistent_conversation_session(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    app = AppTest.from_file(str(APP_PATH)).run()

    assert "conversation_session_id" in app.session_state
    session_id = app.session_state["conversation_session_id"]
    query_button = next(button for button in app.button if button.label == "Generate review")
    query_button.click().run()

    query_call = next(call for call in calls if call[0].endswith("/api/query"))
    assert query_call[1]["json"]["session_id"] == session_id
    assert app.session_state["conversation_session_id"] == session_id


def test_clearing_conversation_memory_clears_server_and_starts_new_session(
    monkeypatch,
):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({"status": "cleared"})

    monkeypatch.setattr(requests, "post", fake_post)
    app = AppTest.from_file(str(APP_PATH)).run()
    original_session_id = app.session_state["conversation_session_id"]

    clear_button = next(
        button for button in app.button if button.label == "Clear conversation memory"
    )
    clear_button.click().run()

    clear_call = next(
        call for call in calls if call[0].endswith("/api/clear-session")
    )
    assert clear_call[1]["json"] == {"session_id": original_session_id}
    assert app.session_state["conversation_session_id"] != original_session_id


def test_failed_memory_clear_keeps_current_session_and_reports_error(monkeypatch):
    def fail_post(url, **kwargs):
        raise requests.ConnectionError("backend unavailable")

    monkeypatch.setattr(requests, "post", fail_post)
    app = AppTest.from_file(str(APP_PATH)).run()
    session_id = app.session_state["conversation_session_id"]
    clear_button = next(
        button for button in app.button if button.label == "Clear conversation memory"
    )

    clear_button.click().run()

    assert app.session_state["conversation_session_id"] == session_id
    assert any("Could not clear conversation memory" in error.value for error in app.error)


def test_query_displays_backend_provider_error_detail(monkeypatch):
    class FailedResponse:
        ok = False
        text = '{"detail":"Hugging Face Inference API has no available inference credits."}'

        def json(self):
            return {
                "detail": (
                    "Hugging Face Inference API has no available inference credits."
                )
            }

        def raise_for_status(self):
            raise requests.HTTPError("503 Server Error", response=self)

    monkeypatch.setattr(
        requests, "post", lambda url, **kwargs: FailedResponse()
    )
    app = AppTest.from_file(str(APP_PATH)).run()

    query_button = next(button for button in app.button if button.label == "Generate review")
    query_button.click().run()

    assert any(
        "no available inference credits" in error.value.lower()
        for error in app.error
    )


def test_ui_submits_feedback_for_the_displayed_answer(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/api/feedback"):
            return FakeResponse(
                {"status": "recorded", "interaction_id": "interaction-1"}
            )
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    app = AppTest.from_file(str(APP_PATH)).run()

    next(button for button in app.button if button.label == "Generate review").click()
    app.run()
    rating = next(
        widget for widget in app.selectbox if widget.label == "Rate this answer"
    )
    rating.select("5").run()
    comment = next(
        widget for widget in app.text_area if widget.label == "Feedback comment"
    )
    comment.set_value("Clear and useful.").run()
    next(button for button in app.button if button.label == "Send feedback").click()
    app.run()

    feedback_call = next(
        call for call in calls if call[0].endswith("/api/feedback")
    )
    assert feedback_call[1]["json"] == {
        "interaction_id": "interaction-1",
        "rating": 5,
        "comment": "Clear and useful.",
    }
    assert any("Feedback recorded" in item.value for item in app.success)
