import pytest

from app.feedback import SQLiteFeedbackStore


def test_feedback_is_persisted_and_summary_is_aggregated(tmp_path):
    database_path = tmp_path / "feedback.sqlite3"
    store = SQLiteFeedbackStore(database_path)
    store.record_interaction("interaction-1")
    store.submit_feedback("interaction-1", rating=5, comment="Helpful")

    restarted_store = SQLiteFeedbackStore(database_path)

    assert restarted_store.get_summary() == {
        "total_feedback": 1,
        "average_rating": 5.0,
        "ratings": {5: 1},
    }


def test_feedback_requires_a_known_interaction_and_allows_only_one_rating(tmp_path):
    store = SQLiteFeedbackStore(tmp_path / "feedback.sqlite3")

    with pytest.raises(KeyError):
        store.submit_feedback("unknown", rating=4)

    store.record_interaction("interaction-1")
    store.submit_feedback("interaction-1", rating=4)

    with pytest.raises(ValueError, match="already been submitted"):
        store.submit_feedback("interaction-1", rating=2)


def test_empty_feedback_summary_has_no_average(tmp_path):
    store = SQLiteFeedbackStore(tmp_path / "feedback.sqlite3")

    assert store.get_summary() == {
        "total_feedback": 0,
        "average_rating": None,
        "ratings": {},
    }
