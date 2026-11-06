import json
import sqlite3
from pathlib import Path


class SQLiteConversationMemory:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_turns_session
                ON conversation_turns (session_id, id)
                """
            )

    def _connect(self):
        return sqlite3.connect(self.database_path, timeout=10)

    def append(self, session_id: str, turn: dict):
        question = turn.get("question")
        answer = turn.get("answer")
        if not isinstance(question, str) or not isinstance(answer, str):
            raise ValueError("Conversation turns require string question and answer.")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_turns (session_id, question, answer)
                VALUES (?, ?, ?)
                """,
                (session_id, question, answer),
            )

    def get_history(self, session_id: str, limit: int | None = None) -> list[dict]:
        sql = (
            "SELECT question, answer FROM conversation_turns "
            "WHERE session_id = ? ORDER BY id DESC"
        )
        parameters: tuple = (session_id,)
        if limit is not None:
            if limit < 0:
                raise ValueError("History limit cannot be negative.")
            sql += " LIMIT ?"
            parameters = (session_id, limit)

        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [
            {"question": question, "answer": answer}
            for question, answer in reversed(rows)
        ]

    def clear(self, session_id: str):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM conversation_turns WHERE session_id = ?",
                (session_id,),
            )

    def __contains__(self, session_id: str):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM conversation_turns WHERE session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone()
        return row is not None

    def __getitem__(self, session_id: str):
        history = self.get_history(session_id)
        if not history:
            raise KeyError(session_id)
        return history
