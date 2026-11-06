from app.memory import SQLiteConversationMemory


def test_conversation_history_is_persisted_between_store_instances(tmp_path):
    database_path = tmp_path / "sessions.sqlite3"
    first_store = SQLiteConversationMemory(database_path)
    first_store.append(
        "review-1",
        {"question": "What handles requests?", "answer": "The API [api::0]."},
    )

    restarted_store = SQLiteConversationMemory(database_path)

    assert restarted_store.get_history("review-1") == [
        {"question": "What handles requests?", "answer": "The API [api::0]."}
    ]


def test_session_memory_is_isolated_and_returns_latest_history_in_order(tmp_path):
    store = SQLiteConversationMemory(tmp_path / "sessions.sqlite3")
    store.append("review-1", {"question": "q1", "answer": "a1"})
    store.append("review-2", {"question": "other", "answer": "private"})
    store.append("review-1", {"question": "q2", "answer": "a2"})
    store.append("review-1", {"question": "q3", "answer": "a3"})

    assert store.get_history("review-1", limit=2) == [
        {"question": "q2", "answer": "a2"},
        {"question": "q3", "answer": "a3"},
    ]
    assert store.get_history("review-2") == [
        {"question": "other", "answer": "private"}
    ]


def test_clearing_session_does_not_clear_other_session(tmp_path):
    store = SQLiteConversationMemory(tmp_path / "sessions.sqlite3")
    store.append("review-1", {"question": "q1", "answer": "a1"})
    store.append("review-2", {"question": "q2", "answer": "a2"})

    store.clear("review-1")

    assert store.get_history("review-1") == []
    assert store.get_history("review-2") == [
        {"question": "q2", "answer": "a2"}
    ]
