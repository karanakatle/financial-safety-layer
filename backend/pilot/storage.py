from __future__ import annotations

import sqlite3
from pathlib import Path


class PilotStorage:
    def __init__(self, db_path: str = "data/pilot_research.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS consents (
                    participant_id TEXT PRIMARY KEY,
                    accepted INTEGER NOT NULL,
                    language TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participant_id TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT NOT NULL,
                    language TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS literacy_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    amount REAL,
                    app_name TEXT,
                    reason TEXT,
                    stage INTEGER,
                    daily_spend REAL,
                    daily_safe_limit REAL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS app_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participant_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    language TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
                """
            )

    def upsert_consent(self, participant_id: str, accepted: bool, language: str, timestamp: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO consents (participant_id, accepted, language, timestamp)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(participant_id)
                DO UPDATE SET
                    accepted=excluded.accepted,
                    language=excluded.language,
                    timestamp=excluded.timestamp
                """,
                (participant_id, 1 if accepted else 0, language, timestamp),
            )

    def add_feedback(
        self,
        participant_id: str,
        rating: int,
        comment: str,
        language: str,
        timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback (participant_id, rating, comment, language, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (participant_id, rating, comment, language, timestamp),
            )

    def add_literacy_event(
        self,
        event_type: str,
        source: str,
        timestamp: str,
        amount: float | None = None,
        app_name: str | None = None,
        reason: str | None = None,
        stage: int | None = None,
        daily_spend: float | None = None,
        daily_safe_limit: float | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO literacy_events (
                    event_type, source, amount, app_name, reason, stage, daily_spend, daily_safe_limit, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    source,
                    amount,
                    app_name,
                    reason,
                    stage,
                    daily_spend,
                    daily_safe_limit,
                    timestamp,
                ),
            )

    def summary(self) -> dict:
        with self._connect() as conn:
            consented = conn.execute(
                "SELECT COUNT(*) AS cnt FROM consents WHERE accepted=1"
            ).fetchone()["cnt"]
            total = conn.execute("SELECT COUNT(*) AS cnt FROM consents").fetchone()["cnt"]
            feedback_count = conn.execute("SELECT COUNT(*) AS cnt FROM feedback").fetchone()["cnt"]
            avg_row = conn.execute("SELECT AVG(rating) AS avg_rating FROM feedback").fetchone()
            avg_rating = round(avg_row["avg_rating"], 2) if avg_row["avg_rating"] is not None else None

        return {
            "participants_consented": consented,
            "participants_total": total,
            "feedback_count": feedback_count,
            "average_rating": avg_rating,
        }

    def analytics(self, recent_limit: int = 25) -> dict:
        with self._connect() as conn:
            event_breakdown = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT event_type, COUNT(*) AS count
                    FROM literacy_events
                    GROUP BY event_type
                    ORDER BY count DESC
                    """
                ).fetchall()
            ]
            stage_breakdown = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT stage, COUNT(*) AS count
                    FROM literacy_events
                    WHERE stage IS NOT NULL
                    GROUP BY stage
                    ORDER BY stage
                    """
                ).fetchall()
            ]
            recent_feedback = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT participant_id, rating, comment, language, timestamp
                    FROM feedback
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (recent_limit,),
                ).fetchall()
            ]
            recent_logs = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT participant_id, level, message, language, timestamp
                    FROM app_logs
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (recent_limit,),
                ).fetchall()
            ]

        return {
            "event_breakdown": event_breakdown,
            "stage_breakdown": stage_breakdown,
            "recent_feedback": recent_feedback,
            "recent_app_logs": recent_logs,
        }

    def add_app_log(
        self,
        participant_id: str,
        level: str,
        message: str,
        language: str,
        timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO app_logs (participant_id, level, message, language, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (participant_id, level, message, language, timestamp),
            )
