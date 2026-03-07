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
                    participant_id TEXT NOT NULL DEFAULT 'global_user',
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

                CREATE TABLE IF NOT EXISTS literacy_state (
                    participant_id TEXT PRIMARY KEY,
                    current_date TEXT NOT NULL,
                    daily_spend REAL NOT NULL,
                    threshold_risk_active INTEGER NOT NULL,
                    stage1_sent INTEGER NOT NULL,
                    stage2_sent INTEGER NOT NULL,
                    notifications_count INTEGER NOT NULL,
                    first_event_date TEXT,
                    warmup_active INTEGER NOT NULL DEFAULT 0,
                    adaptive_daily_safe_limit REAL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS participant_policy (
                    participant_id TEXT PRIMARY KEY,
                    daily_safe_limit REAL NOT NULL,
                    warning_ratio REAL NOT NULL,
                    is_auto INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_spend_history (
                    participant_id TEXT NOT NULL,
                    spend_date TEXT NOT NULL,
                    daily_spend REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (participant_id, spend_date)
                );

                CREATE TABLE IF NOT EXISTS alert_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT NOT NULL,
                    participant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS alert_features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT NOT NULL,
                    participant_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    amount REAL,
                    projected_spend REAL,
                    daily_safe_limit REAL,
                    spend_ratio REAL,
                    txn_anomaly_score REAL,
                    hour_of_day INTEGER,
                    rapid_txn_flag INTEGER NOT NULL,
                    upi_open_flag INTEGER NOT NULL,
                    recent_dismissals_24h INTEGER NOT NULL,
                    risk_score REAL,
                    confidence_score REAL,
                    tone_selected TEXT NOT NULL,
                    frequency_bucket TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "literacy_state", "first_event_date TEXT")
            self._ensure_column(conn, "literacy_state", "warmup_active INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "literacy_state", "adaptive_daily_safe_limit REAL")
            self._ensure_column(conn, "literacy_events", "participant_id TEXT NOT NULL DEFAULT 'global_user'")
            self._ensure_column(conn, "participant_policy", "daily_safe_limit REAL NOT NULL DEFAULT 1200")
            self._ensure_column(conn, "participant_policy", "warning_ratio REAL NOT NULL DEFAULT 0.9")
            self._ensure_column(conn, "participant_policy", "is_auto INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(conn, "participant_policy", "updated_at TEXT NOT NULL DEFAULT ''")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column_def: str) -> None:
        column_name = column_def.split()[0]
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {row["name"] for row in rows}
        if column_name in existing:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

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
        participant_id: str,
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
                    participant_id, event_type, source, amount, app_name, reason, stage, daily_spend, daily_safe_limit, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    participant_id,
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

    def get_literacy_state(self, participant_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT participant_id, current_date, daily_spend, threshold_risk_active,
                       stage1_sent, stage2_sent, notifications_count,
                       first_event_date, warmup_active, adaptive_daily_safe_limit, updated_at
                FROM literacy_state
                WHERE participant_id=?
                """,
                (participant_id,),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            data["threshold_risk_active"] = bool(data["threshold_risk_active"])
            data["stage1_sent"] = bool(data["stage1_sent"])
            data["stage2_sent"] = bool(data["stage2_sent"])
            data["warmup_active"] = bool(data["warmup_active"])
            return data

    def upsert_literacy_state(
        self,
        participant_id: str,
        current_date: str,
        daily_spend: float,
        threshold_risk_active: bool,
        stage1_sent: bool,
        stage2_sent: bool,
        notifications_count: int,
        first_event_date: str | None,
        warmup_active: bool,
        adaptive_daily_safe_limit: float | None,
        updated_at: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO literacy_state (
                    participant_id, current_date, daily_spend, threshold_risk_active,
                    stage1_sent, stage2_sent, notifications_count, first_event_date,
                    warmup_active, adaptive_daily_safe_limit, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(participant_id)
                DO UPDATE SET
                    current_date=excluded.current_date,
                    daily_spend=excluded.daily_spend,
                    threshold_risk_active=excluded.threshold_risk_active,
                    stage1_sent=excluded.stage1_sent,
                    stage2_sent=excluded.stage2_sent,
                    notifications_count=excluded.notifications_count,
                    first_event_date=excluded.first_event_date,
                    warmup_active=excluded.warmup_active,
                    adaptive_daily_safe_limit=excluded.adaptive_daily_safe_limit,
                    updated_at=excluded.updated_at
                """,
                (
                    participant_id,
                    current_date,
                    daily_spend,
                    1 if threshold_risk_active else 0,
                    1 if stage1_sent else 0,
                    1 if stage2_sent else 0,
                    notifications_count,
                    first_event_date,
                    1 if warmup_active else 0,
                    adaptive_daily_safe_limit,
                    updated_at,
                ),
            )

    def reset_literacy_state(self, participant_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                DELETE FROM literacy_state
                WHERE participant_id=?
                """,
                (participant_id,),
            )

    def get_participant_policy(self, participant_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT participant_id, daily_safe_limit, warning_ratio, is_auto, updated_at
                FROM participant_policy
                WHERE participant_id=?
                """,
                (participant_id,),
            ).fetchone()
            return dict(row) if row else None

    def upsert_participant_policy(
        self,
        participant_id: str,
        daily_safe_limit: float,
        warning_ratio: float,
        is_auto: bool,
        updated_at: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO participant_policy (participant_id, daily_safe_limit, warning_ratio, is_auto, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(participant_id)
                DO UPDATE SET
                    daily_safe_limit=excluded.daily_safe_limit,
                    warning_ratio=excluded.warning_ratio,
                    is_auto=excluded.is_auto,
                    updated_at=excluded.updated_at
                """,
                (participant_id, daily_safe_limit, warning_ratio, 1 if is_auto else 0, updated_at),
            )

    def upsert_auto_participant_policy(
        self,
        participant_id: str,
        daily_safe_limit: float,
        warning_ratio: float,
        updated_at: str,
    ) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT is_auto
                FROM participant_policy
                WHERE participant_id=?
                """,
                (participant_id,),
            ).fetchone()
            if row is not None and int(row["is_auto"]) == 0:
                return False

            conn.execute(
                """
                INSERT INTO participant_policy (participant_id, daily_safe_limit, warning_ratio, is_auto, updated_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(participant_id)
                DO UPDATE SET
                    daily_safe_limit=excluded.daily_safe_limit,
                    warning_ratio=excluded.warning_ratio,
                    is_auto=1,
                    updated_at=excluded.updated_at
                """,
                (participant_id, daily_safe_limit, warning_ratio, updated_at),
            )
            return True

    def add_alert_feedback(
        self,
        alert_id: str,
        participant_id: str,
        action: str,
        channel: str,
        title: str,
        message: str,
        timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO alert_feedback (
                    alert_id, participant_id, action, channel, title, message, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (alert_id, participant_id, action, channel, title, message, timestamp),
            )

    def add_alert_features(
        self,
        alert_id: str,
        participant_id: str,
        timestamp: str,
        amount: float,
        projected_spend: float,
        daily_safe_limit: float,
        spend_ratio: float,
        txn_anomaly_score: float,
        hour_of_day: int,
        rapid_txn_flag: bool,
        upi_open_flag: bool,
        recent_dismissals_24h: int,
        risk_score: float,
        confidence_score: float,
        tone_selected: str,
        frequency_bucket: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO alert_features (
                    alert_id, participant_id, timestamp, amount, projected_spend, daily_safe_limit,
                    spend_ratio, txn_anomaly_score, hour_of_day, rapid_txn_flag, upi_open_flag,
                    recent_dismissals_24h, risk_score, confidence_score, tone_selected, frequency_bucket
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert_id,
                    participant_id,
                    timestamp,
                    amount,
                    projected_spend,
                    daily_safe_limit,
                    spend_ratio,
                    txn_anomaly_score,
                    hour_of_day,
                    1 if rapid_txn_flag else 0,
                    1 if upi_open_flag else 0,
                    recent_dismissals_24h,
                    risk_score,
                    confidence_score,
                    tone_selected,
                    frequency_bucket,
                ),
            )

    def upsert_daily_spend(
        self,
        participant_id: str,
        spend_date: str,
        daily_spend: float,
        updated_at: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO daily_spend_history (participant_id, spend_date, daily_spend, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(participant_id, spend_date)
                DO UPDATE SET
                    daily_spend=excluded.daily_spend,
                    updated_at=excluded.updated_at
                """,
                (participant_id, spend_date, daily_spend, updated_at),
            )

    def recent_daily_spends(self, participant_id: str, limit: int = 7) -> list[float]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT daily_spend
                FROM daily_spend_history
                WHERE participant_id=? AND daily_spend > 0
                ORDER BY spend_date DESC
                LIMIT ?
                """,
                (participant_id, limit),
            ).fetchall()
        return [float(row["daily_spend"]) for row in rows]

    def recent_spend_amounts(self, participant_id: str, limit: int = 20) -> list[float]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT amount
                FROM literacy_events
                WHERE participant_id=? AND amount IS NOT NULL AND amount > 0
                ORDER BY id DESC
                LIMIT ?
                """,
                (participant_id, limit),
            ).fetchall()
        return [float(row["amount"]) for row in rows]

    def count_recent_spend_events(self, participant_id: str, since_timestamp: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM literacy_events
                WHERE participant_id=?
                  AND event_type IN ('sms_ingest_event', 'manual_txn_event')
                  AND timestamp >= ?
                """,
                (participant_id, since_timestamp),
            ).fetchone()
        return int(row["cnt"]) if row else 0

    def count_recent_dismissals(self, participant_id: str, since_timestamp: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM alert_feedback
                WHERE participant_id=?
                  AND action='dismissed'
                  AND timestamp >= ?
                """,
                (participant_id, since_timestamp),
            ).fetchone()
        return int(row["cnt"]) if row else 0

    def recent_alert_feature_summary(self, participant_id: str, limit: int = 50) -> dict:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS sample_size,
                    AVG(risk_score) AS avg_risk_score,
                    AVG(confidence_score) AS avg_confidence_score,
                    AVG(spend_ratio) AS avg_spend_ratio,
                    SUM(CASE WHEN frequency_bucket='hard' THEN 1 ELSE 0 END) AS hard_count,
                    SUM(CASE WHEN frequency_bucket='suppressed' THEN 1 ELSE 0 END) AS suppressed_count
                FROM (
                    SELECT risk_score, confidence_score, spend_ratio, frequency_bucket
                    FROM alert_features
                    WHERE participant_id=?
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (participant_id, limit),
            ).fetchone()
        if not row:
            return {
                "sample_size": 0,
                "avg_risk_score": 0.0,
                "avg_confidence_score": 0.0,
                "avg_spend_ratio": 0.0,
                "hard_count": 0,
                "suppressed_count": 0,
            }
        return {
            "sample_size": int(row["sample_size"] or 0),
            "avg_risk_score": float(row["avg_risk_score"] or 0.0),
            "avg_confidence_score": float(row["avg_confidence_score"] or 0.0),
            "avg_spend_ratio": float(row["avg_spend_ratio"] or 0.0),
            "hard_count": int(row["hard_count"] or 0),
            "suppressed_count": int(row["suppressed_count"] or 0),
        }
