import sqlite3
from contextlib import closing
from pathlib import Path


class SQLiteFeedbackStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_interactions (
                    interaction_id TEXT PRIMARY KEY
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS answer_feedback_entries (
                    interaction_id TEXT PRIMARY KEY,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    comment TEXT,
                    FOREIGN KEY (interaction_id)
                        REFERENCES feedback_interactions (interaction_id)
                )
                """
            )

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def record_interaction(self, interaction_id: str):
        if not interaction_id:
            raise ValueError("Interactions require an ID.")

        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO feedback_interactions (interaction_id)
                VALUES (?)
                """,
                (interaction_id,),
            )

    def submit_feedback(
        self,
        interaction_id: str,
        rating: int,
        comment: str | None = None,
    ):
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        if comment is not None and len(comment) > 2000:
            raise ValueError("Feedback comment cannot exceed 2000 characters.")

        with closing(self._connect()) as connection, connection:
            interaction = connection.execute(
                "SELECT 1 FROM feedback_interactions WHERE interaction_id = ?",
                (interaction_id,),
            ).fetchone()
            if interaction is None:
                raise KeyError(interaction_id)
            try:
                connection.execute(
                    """
                    INSERT INTO answer_feedback_entries
                        (interaction_id, rating, comment)
                    VALUES (?, ?, ?)
                    """,
                    (interaction_id, rating, comment),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(
                    "Feedback has already been submitted for this interaction."
                ) from exc

    def get_summary(self) -> dict:
        with closing(self._connect()) as connection, connection:
            total, average = connection.execute(
                "SELECT COUNT(*), AVG(rating) FROM answer_feedback_entries"
            ).fetchone()
            ratings = connection.execute(
                """
                SELECT rating, COUNT(*)
                FROM answer_feedback_entries
                GROUP BY rating
                ORDER BY rating
                """
            ).fetchall()
        return {
            "total_feedback": total,
            "average_rating": round(average, 2) if average is not None else None,
            "ratings": {rating: count for rating, count in ratings},
        }
