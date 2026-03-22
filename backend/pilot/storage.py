from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class PilotStorage:
    def __init__(self, db_path: str = "data/pilot_research.db") -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 5000")
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
                    signal_type TEXT NOT NULL DEFAULT 'expense',
                    signal_confidence TEXT NOT NULL DEFAULT 'confirmed',
                    category TEXT,
                    amount REAL,
                    app_name TEXT,
                    note TEXT,
                    reason TEXT,
                    stage INTEGER,
                    daily_spend REAL,
                    daily_safe_limit REAL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS app_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    participant_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    event_type TEXT,
                    source_app TEXT,
                    target_app TEXT,
                    correlation_id TEXT,
                    classification TEXT,
                    setup_state TEXT,
                    suppression_reason TEXT,
                    message_family TEXT,
                    amount REAL,
                    has_otp INTEGER,
                    has_upi_handle INTEGER,
                    has_upi_deeplink INTEGER,
                    has_url INTEGER,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
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
                    event_id TEXT,
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

                CREATE TABLE IF NOT EXISTS essential_goal_profile (
                    participant_id TEXT PRIMARY KEY,
                    cohort TEXT NOT NULL,
                    essential_goals TEXT NOT NULL,
                    language TEXT NOT NULL,
                    setup_skipped INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS experiment_assignment (
                    participant_id TEXT NOT NULL,
                    experiment_name TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    PRIMARY KEY (participant_id, experiment_name)
                );

                CREATE TABLE IF NOT EXISTS experiment_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participant_id TEXT NOT NULL,
                    experiment_name TEXT NOT NULL,
                    variant TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS grievances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participant_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    details TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS goal_memory (
                    participant_id TEXT NOT NULL,
                    merchant_key TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    positive_count INTEGER NOT NULL DEFAULT 0,
                    negative_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (participant_id, merchant_key, goal)
                );

                CREATE TABLE IF NOT EXISTS goal_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    participant_id TEXT NOT NULL,
                    alert_id TEXT NOT NULL,
                    merchant_key TEXT NOT NULL,
                    selected_goal TEXT NOT NULL,
                    is_essential INTEGER NOT NULL,
                    source_confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS alert_goal_context (
                    alert_id TEXT PRIMARY KEY,
                    participant_id TEXT NOT NULL,
                    merchant_key TEXT NOT NULL,
                    inferred_goal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    gate_passed INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS unified_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    participant_id TEXT NOT NULL,
                    telemetry_family TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    alert_id TEXT,
                    source_route TEXT NOT NULL,
                    source TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    amount REAL,
                    category TEXT,
                    app_name TEXT,
                    scenario TEXT,
                    risk_level TEXT,
                    reason TEXT,
                    stage INTEGER,
                    action TEXT,
                    channel TEXT,
                    signal_type TEXT,
                    signal_confidence TEXT,
                    projected_daily_spend REAL,
                    daily_safe_limit REAL,
                    risk_score REAL,
                    confidence_score REAL,
                    frequency_bucket TEXT,
                    tone_selected TEXT,
                    summary_text TEXT,
                    context_json TEXT NOT NULL DEFAULT '{}',
                    extensions_json TEXT NOT NULL DEFAULT '{}'
                );
                """
            )
            self._ensure_column(conn, "literacy_state", "first_event_date TEXT")
            self._ensure_column(conn, "literacy_state", "warmup_active INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "literacy_state", "adaptive_daily_safe_limit REAL")
            self._ensure_column(conn, "literacy_events", "participant_id TEXT NOT NULL DEFAULT 'global_user'")
            self._ensure_column(conn, "literacy_events", "signal_type TEXT NOT NULL DEFAULT 'expense'")
            self._ensure_column(conn, "literacy_events", "signal_confidence TEXT NOT NULL DEFAULT 'confirmed'")
            self._ensure_column(conn, "literacy_events", "category TEXT")
            self._ensure_column(conn, "literacy_events", "note TEXT")
            self._ensure_column(conn, "participant_policy", "daily_safe_limit REAL NOT NULL DEFAULT 1200")
            self._ensure_column(conn, "participant_policy", "warning_ratio REAL NOT NULL DEFAULT 0.9")
            self._ensure_column(conn, "participant_policy", "is_auto INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(conn, "participant_policy", "updated_at TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "app_logs", "event_id TEXT")
            self._ensure_column(conn, "app_logs", "event_type TEXT")
            self._ensure_column(conn, "app_logs", "source_app TEXT")
            self._ensure_column(conn, "app_logs", "target_app TEXT")
            self._ensure_column(conn, "app_logs", "correlation_id TEXT")
            self._ensure_column(conn, "app_logs", "classification TEXT")
            self._ensure_column(conn, "app_logs", "setup_state TEXT")
            self._ensure_column(conn, "app_logs", "suppression_reason TEXT")
            self._ensure_column(conn, "app_logs", "message_family TEXT")
            self._ensure_column(conn, "app_logs", "amount REAL")
            self._ensure_column(conn, "app_logs", "has_otp INTEGER")
            self._ensure_column(conn, "app_logs", "has_upi_handle INTEGER")
            self._ensure_column(conn, "app_logs", "has_upi_deeplink INTEGER")
            self._ensure_column(conn, "app_logs", "has_url INTEGER")
            self._ensure_column(conn, "app_logs", "metadata_json TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "alert_feedback", "event_id TEXT")
            self._ensure_column(conn, "unified_telemetry", "event_id TEXT")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_app_logs_event_id ON app_logs(event_id) WHERE event_id IS NOT NULL"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_alert_feedback_event_id ON alert_feedback(event_id) WHERE event_id IS NOT NULL"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_unified_telemetry_event_id ON unified_telemetry(event_id) WHERE event_id IS NOT NULL"
            )

    def _json_text(self, value: dict | None) -> str:
        if not isinstance(value, dict):
            return "{}"
        return json.dumps(value, ensure_ascii=True, sort_keys=True)

    def _parse_json_object(self, value: str | None) -> dict:
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column_def: str) -> None:
        column_name = column_def.split()[0]
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {row["name"] for row in rows}
        if column_name in existing:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")

    def _parse_app_log_row(self, row: sqlite3.Row) -> dict:
        data = dict(row)
        data["metadata"] = self._parse_json_object(data.pop("metadata_json", None))
        for key in ("has_otp", "has_upi_handle", "has_upi_deeplink", "has_url"):
            value = data.get(key)
            if value is not None:
                data[key] = bool(value)
        return data

    def recent_app_logs(
        self,
        participant_id: str | None = None,
        *,
        limit: int = 25,
        event_type: str | None = None,
        correlation_id: str | None = None,
        classification: str | None = None,
        context_only: bool = False,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if participant_id:
            clauses.append("participant_id=?")
            params.append(participant_id)
        if event_type:
            clauses.append("event_type=?")
            params.append(event_type)
        if correlation_id:
            clauses.append("correlation_id=?")
            params.append(correlation_id)
        if classification:
            clauses.append("classification=?")
            params.append(classification)
        if context_only:
            clauses.append("event_type IS NOT NULL")
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT participant_id, level, message, event_type, source_app, target_app,
                       correlation_id, classification, setup_state, suppression_reason,
                       message_family, amount, has_otp, has_upi_handle, has_upi_deeplink,
                       has_url, metadata_json, language, timestamp
                FROM app_logs
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._parse_app_log_row(row) for row in rows]

    def context_event_breakdown(self, participant_id: str | None = None) -> dict:
        clauses = ["event_type IS NOT NULL"]
        params: list[object] = []
        if participant_id:
            clauses.append("participant_id=?")
            params.append(participant_id)
        where_sql = " AND ".join(clauses)

        with self._connect() as conn:
            by_event_type = [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT event_type, COUNT(*) AS count
                    FROM app_logs
                    WHERE {where_sql}
                    GROUP BY event_type
                    ORDER BY count DESC, event_type
                    """,
                    tuple(params),
                ).fetchall()
            ]
            by_classification = [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT classification, COUNT(*) AS count
                    FROM app_logs
                    WHERE {where_sql}
                    GROUP BY classification
                    ORDER BY count DESC, classification
                    """,
                    tuple(params),
                ).fetchall()
            ]
            by_message_family = [
                dict(row)
                for row in conn.execute(
                    f"""
                    SELECT message_family, COUNT(*) AS count
                    FROM app_logs
                    WHERE {where_sql}
                    GROUP BY message_family
                    ORDER BY count DESC, message_family
                    """,
                    tuple(params),
                ).fetchall()
            ]
        return {
            "by_event_type": by_event_type,
            "by_classification": by_classification,
            "by_message_family": by_message_family,
        }

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
        signal_type: str = "expense",
        signal_confidence: str = "confirmed",
        category: str | None = None,
        amount: float | None = None,
        app_name: str | None = None,
        note: str | None = None,
        reason: str | None = None,
        stage: int | None = None,
        daily_spend: float | None = None,
        daily_safe_limit: float | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO literacy_events (
                    participant_id, event_type, source, signal_type, signal_confidence, category, amount, app_name, note, reason, stage, daily_spend, daily_safe_limit, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    participant_id,
                    event_type,
                    source,
                    signal_type,
                    signal_confidence,
                    category,
                    amount,
                    app_name,
                    note,
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

    def analytics(
        self,
        recent_limit: int = 25,
        participant_id: str | None = None,
        event_type: str | None = None,
        correlation_id: str | None = None,
    ) -> dict:
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
            recent_logs = self.recent_app_logs(
                participant_id=participant_id,
                limit=recent_limit,
                event_type=event_type,
                correlation_id=correlation_id,
            )
            recent_context_events = self.recent_app_logs(
                participant_id=participant_id,
                limit=recent_limit,
                event_type=event_type,
                correlation_id=correlation_id,
                context_only=True,
            )

        return {
            "event_breakdown": event_breakdown,
            "stage_breakdown": stage_breakdown,
            "recent_feedback": recent_feedback,
            "recent_app_logs": recent_logs,
            "recent_context_events": recent_context_events,
            "context_event_breakdown": self.context_event_breakdown(participant_id=participant_id),
        }

    def add_app_log(
        self,
        participant_id: str,
        level: str,
        message: str,
        language: str,
        timestamp: str,
        event_id: str | None = None,
        event_type: str | None = None,
        source_app: str | None = None,
        target_app: str | None = None,
        correlation_id: str | None = None,
        classification: str | None = None,
        setup_state: str | None = None,
        suppression_reason: str | None = None,
        message_family: str | None = None,
        amount: float | None = None,
        has_otp: bool | None = None,
        has_upi_handle: bool | None = None,
        has_upi_deeplink: bool | None = None,
        has_url: bool | None = None,
        metadata: dict | None = None,
    ) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO app_logs (
                    event_id, participant_id, level, message, event_type, source_app, target_app,
                    correlation_id, classification, setup_state, suppression_reason, message_family,
                    amount, has_otp, has_upi_handle, has_upi_deeplink, has_url, metadata_json,
                    language, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    participant_id,
                    level,
                    message,
                    event_type,
                    source_app,
                    target_app,
                    correlation_id,
                    classification,
                    setup_state,
                    suppression_reason,
                    message_family,
                    amount,
                    None if has_otp is None else (1 if has_otp else 0),
                    None if has_upi_handle is None else (1 if has_upi_handle else 0),
                    None if has_upi_deeplink is None else (1 if has_upi_deeplink else 0),
                    None if has_url is None else (1 if has_url else 0),
                    self._json_text(metadata),
                    language,
                    timestamp,
                ),
            )
        return cursor.rowcount > 0

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

    def reset_literacy_profile(self, participant_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM literacy_state WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM participant_policy WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM daily_spend_history WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM literacy_events WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM alert_feedback WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM alert_features WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM essential_goal_profile WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM experiment_assignment WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM experiment_events WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM goal_memory WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM goal_feedback WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM alert_goal_context WHERE participant_id=?", (participant_id,))
            conn.execute("DELETE FROM unified_telemetry WHERE participant_id=?", (participant_id,))

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
        event_id: str | None = None,
    ) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO alert_feedback (
                    event_id, alert_id, participant_id, action, channel, title, message, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, alert_id, participant_id, action, channel, title, message, timestamp),
            )
        return cursor.rowcount > 0

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

    def add_unified_telemetry(
        self,
        *,
        participant_id: str,
        telemetry_family: str,
        record_type: str,
        event_name: str,
        source_route: str,
        source: str,
        timestamp: str,
        event_id: str | None = None,
        alert_id: str | None = None,
        amount: float | None = None,
        category: str | None = None,
        app_name: str | None = None,
        scenario: str | None = None,
        risk_level: str | None = None,
        reason: str | None = None,
        stage: int | None = None,
        action: str | None = None,
        channel: str | None = None,
        signal_type: str | None = None,
        signal_confidence: str | None = None,
        projected_daily_spend: float | None = None,
        daily_safe_limit: float | None = None,
        risk_score: float | None = None,
        confidence_score: float | None = None,
        frequency_bucket: str | None = None,
        tone_selected: str | None = None,
        summary_text: str | None = None,
        context: dict | None = None,
        extensions: dict | None = None,
    ) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO unified_telemetry (
                    event_id, participant_id, telemetry_family, record_type, event_name, alert_id,
                    source_route, source, timestamp, amount, category, app_name, scenario,
                    risk_level, reason, stage, action, channel, signal_type, signal_confidence,
                    projected_daily_spend, daily_safe_limit, risk_score, confidence_score,
                    frequency_bucket, tone_selected, summary_text, context_json, extensions_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    participant_id,
                    telemetry_family,
                    record_type,
                    event_name,
                    alert_id,
                    source_route,
                    source,
                    timestamp,
                    amount,
                    category,
                    app_name,
                    scenario,
                    risk_level,
                    reason,
                    stage,
                    action,
                    channel,
                    signal_type,
                    signal_confidence,
                    projected_daily_spend,
                    daily_safe_limit,
                    risk_score,
                    confidence_score,
                    frequency_bucket,
                    tone_selected,
                    summary_text,
                    self._json_text(context),
                    self._json_text(extensions),
                ),
            )
        return cursor.rowcount > 0

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
                WHERE participant_id=?
                  AND signal_type='expense'
                  AND amount IS NOT NULL
                  AND amount > 0
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
                  AND signal_type='expense'
                  AND timestamp >= ?
                """,
                (participant_id, since_timestamp),
            ).fetchone()
        return int(row["cnt"]) if row else 0

    def recent_financial_signals(self, participant_id: str, limit: int = 25) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type, source, signal_type, signal_confidence, category, amount, note, timestamp
                FROM literacy_events
                WHERE participant_id=?
                  AND event_type IN ('sms_ingest_event', 'sms_partial_context')
                ORDER BY id DESC
                LIMIT ?
                """,
                (participant_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

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

    def recent_unified_telemetry(
        self,
        participant_id: str | None = None,
        telemetry_family: str | None = None,
        record_type: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if participant_id:
            clauses.append("participant_id=?")
            params.append(participant_id)
        if telemetry_family:
            clauses.append("telemetry_family=?")
            params.append(telemetry_family)
        if record_type:
            clauses.append("record_type=?")
            params.append(record_type)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT event_id, participant_id, telemetry_family, record_type, event_name, alert_id,
                       source_route, source, timestamp, amount, category, app_name, scenario,
                       risk_level, reason, stage, action, channel, signal_type,
                       signal_confidence, projected_daily_spend, daily_safe_limit,
                       risk_score, confidence_score, frequency_bucket, tone_selected,
                       summary_text, context_json, extensions_json
                FROM unified_telemetry
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        records: list[dict] = []
        for row in rows:
            data = dict(row)
            data["context"] = self._parse_json_object(data.pop("context_json"))
            data["extensions"] = self._parse_json_object(data.pop("extensions_json"))
            records.append(data)
        return records

    def latest_unified_telemetry_for_alert(
        self,
        alert_id: str,
        participant_id: str | None = None,
    ) -> dict | None:
        clauses = ["alert_id=?"]
        params: list[object] = [alert_id]
        if participant_id:
            clauses.append("participant_id=?")
            params.append(participant_id)
        where_sql = " AND ".join(clauses)
        with self._connect() as conn:
            row = conn.execute(
                f"""
                SELECT event_id, participant_id, telemetry_family, record_type, event_name, alert_id,
                       source_route, source, timestamp, amount, category, app_name, scenario,
                       risk_level, reason, stage, action, channel, signal_type,
                       signal_confidence, projected_daily_spend, daily_safe_limit,
                       risk_score, confidence_score, frequency_bucket, tone_selected,
                       summary_text, context_json, extensions_json
                FROM unified_telemetry
                WHERE {where_sql}
                ORDER BY id DESC
                LIMIT 1
                """,
                tuple(params),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["context"] = self._parse_json_object(data.pop("context_json"))
        data["extensions"] = self._parse_json_object(data.pop("extensions_json"))
        return data

    def unified_telemetry_comparison(
        self,
        participant_id: str | None = None,
        limit: int = 200,
    ) -> dict:
        records = self.recent_unified_telemetry(participant_id=participant_id, limit=limit)
        participant_ids = {
            str(record.get("participant_id") or "").strip()
            for record in records
            if str(record.get("participant_id") or "").strip()
        }
        participant_metadata = self._participant_analysis_metadata(participant_ids)

        def empty_bucket() -> dict:
            return {
                "total_records": 0,
                "generated_count": 0,
                "action_count": 0,
                "fallback_count": 0,
                "usefulness_count": 0,
                "high_risk_count": 0,
                "critical_risk_count": 0,
                "dismissed_count": 0,
                "helpful_count": 0,
                "not_useful_count": 0,
                "latest_timestamp": None,
                "action_breakdown": {},
                "scenario_breakdown": {},
                "trace_sample": [],
                "noise_indicators": {
                    "dismissal_ratio": 0.0,
                    "negative_feedback_ratio": None,
                    "fallback_ratio": 0.0,
                },
            }

        families: dict[str, dict] = {
            "payment_warning": empty_bucket(),
            "cashflow": empty_bucket(),
        }
        language_slices: dict[str, dict] = {}
        cohort_slices: dict[str, dict] = {}
        variant_slices: dict[str, dict] = {}
        for record in records:
            family = str(record.get("telemetry_family") or "unknown")
            bucket = families.setdefault(family, empty_bucket())
            bucket["total_records"] += 1
            record_type = str(record.get("record_type") or "").lower()
            if record_type == "generated":
                bucket["generated_count"] += 1
            elif record_type == "action":
                bucket["action_count"] += 1
            elif record_type == "fallback":
                bucket["fallback_count"] += 1
            elif record_type == "usefulness":
                bucket["usefulness_count"] += 1
            risk_level = str(record.get("risk_level") or "").lower()
            if risk_level == "high":
                bucket["high_risk_count"] += 1
            elif risk_level == "critical":
                bucket["critical_risk_count"] += 1
            action = str(record.get("action") or "").strip().lower()
            if action:
                bucket["action_breakdown"][action] = bucket["action_breakdown"].get(action, 0) + 1
            if action == "dismissed":
                bucket["dismissed_count"] += 1
            if action == "useful":
                bucket["helpful_count"] += 1
            if action == "not_useful":
                bucket["not_useful_count"] += 1
            scenario_key = (
                str(record.get("scenario") or "").strip()
                or str(record.get("reason") or "").strip()
                or str(record.get("event_name") or "").strip()
            )
            bucket["scenario_breakdown"][scenario_key] = bucket["scenario_breakdown"].get(scenario_key, 0) + 1
            timestamp = record.get("timestamp")
            if timestamp and (
                bucket["latest_timestamp"] is None or str(timestamp) > str(bucket["latest_timestamp"])
            ):
                bucket["latest_timestamp"] = timestamp
            if len(bucket["trace_sample"]) < 5:
                bucket["trace_sample"].append(
                    {
                        "event_id": record.get("event_id"),
                        "alert_id": record.get("alert_id"),
                        "timestamp": timestamp,
                        "event_name": record.get("event_name"),
                        "record_type": record_type,
                        "action": record.get("action"),
                    }
                )

            metadata = participant_metadata.get(str(record.get("participant_id") or "").strip(), {})
            extensions = record.get("extensions") or {}
            language_key = str(
                extensions.get("language") or metadata.get("language") or "unknown"
            ).strip() or "unknown"
            cohort_key = str(metadata.get("cohort") or "unknown").strip() or "unknown"
            variant_key = str(
                extensions.get("experiment_variant") or metadata.get("variant") or "unknown"
            ).strip() or "unknown"
            self._accumulate_slice(language_slices, language_key, family, action)
            self._accumulate_slice(cohort_slices, cohort_key, family, action)
            self._accumulate_slice(variant_slices, variant_key, family, action)

        for bucket in families.values():
            generated_count = int(bucket["generated_count"])
            usefulness_count = int(bucket["usefulness_count"])
            trigger_count = generated_count + int(bucket["fallback_count"])
            bucket["noise_indicators"] = {
                "dismissal_ratio": round(bucket["dismissed_count"] / generated_count, 4)
                if generated_count
                else 0.0,
                "negative_feedback_ratio": round(bucket["not_useful_count"] / usefulness_count, 4)
                if usefulness_count
                else None,
                "fallback_ratio": round(bucket["fallback_count"] / trigger_count, 4)
                if trigger_count
                else 0.0,
            }

        return {
            "sample_size": len(records),
            "payment_warning": families["payment_warning"],
            "cashflow": families["cashflow"],
            "language_slices": language_slices,
            "cohort_slices": cohort_slices,
            "variant_slices": variant_slices,
        }

    def _participant_analysis_metadata(self, participant_ids: set[str]) -> dict[str, dict]:
        if not participant_ids:
            return {}
        ordered_ids = sorted(participant_ids)
        placeholders = ", ".join("?" for _ in ordered_ids)
        metadata = {
            participant_id: {"language": None, "cohort": None, "variant": None}
            for participant_id in ordered_ids
        }
        with self._connect() as conn:
            for row in conn.execute(
                f"""
                SELECT participant_id, language
                FROM consents
                WHERE participant_id IN ({placeholders})
                """,
                tuple(ordered_ids),
            ).fetchall():
                metadata[str(row["participant_id"])]["language"] = row["language"]
            for row in conn.execute(
                f"""
                SELECT participant_id, cohort
                FROM essential_goal_profile
                WHERE participant_id IN ({placeholders})
                """,
                tuple(ordered_ids),
            ).fetchall():
                metadata[str(row["participant_id"])]["cohort"] = row["cohort"]
            for row in conn.execute(
                f"""
                SELECT participant_id, variant
                FROM experiment_assignment
                WHERE experiment_name='adaptive_alerts_v1'
                  AND participant_id IN ({placeholders})
                """,
                tuple(ordered_ids),
            ).fetchall():
                metadata[str(row["participant_id"])]["variant"] = row["variant"]
        return metadata

    def _accumulate_slice(
        self,
        slices: dict[str, dict],
        key: str,
        family: str,
        action: str,
    ) -> None:
        bucket = slices.setdefault(
            key,
            {
                "total_records": 0,
                "family_breakdown": {},
                "action_breakdown": {},
                "helpful_count": 0,
                "not_useful_count": 0,
                "dismissed_count": 0,
            },
        )
        bucket["total_records"] += 1
        bucket["family_breakdown"][family] = bucket["family_breakdown"].get(family, 0) + 1
        if action:
            bucket["action_breakdown"][action] = bucket["action_breakdown"].get(action, 0) + 1
        if action == "useful":
            bucket["helpful_count"] += 1
        elif action == "not_useful":
            bucket["not_useful_count"] += 1
        elif action == "dismissed":
            bucket["dismissed_count"] += 1

    def get_essential_goal_profile(self, participant_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT participant_id, cohort, essential_goals, language, setup_skipped, created_at, updated_at
                FROM essential_goal_profile
                WHERE participant_id=?
                """,
                (participant_id,),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            goals = data.get("essential_goals") or "[]"
            data["essential_goals"] = json.loads(goals)
            data["setup_skipped"] = bool(data.get("setup_skipped", 0))
            return data

    def upsert_essential_goal_profile(
        self,
        participant_id: str,
        cohort: str,
        essential_goals: list[str],
        language: str,
        setup_skipped: bool,
        timestamp: str,
    ) -> None:
        goals_json = json.dumps(essential_goals, ensure_ascii=True)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO essential_goal_profile (
                    participant_id, cohort, essential_goals, language, setup_skipped, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(participant_id)
                DO UPDATE SET
                    cohort=excluded.cohort,
                    essential_goals=excluded.essential_goals,
                    language=excluded.language,
                    setup_skipped=excluded.setup_skipped,
                    updated_at=excluded.updated_at
                """,
                (
                    participant_id,
                    cohort,
                    goals_json,
                    language,
                    1 if setup_skipped else 0,
                    timestamp,
                    timestamp,
                ),
            )

    def get_experiment_assignment(self, participant_id: str, experiment_name: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT participant_id, experiment_name, variant, assigned_at
                FROM experiment_assignment
                WHERE participant_id=? AND experiment_name=?
                """,
                (participant_id, experiment_name),
            ).fetchone()
            return dict(row) if row else None

    def upsert_experiment_assignment(
        self,
        participant_id: str,
        experiment_name: str,
        variant: str,
        assigned_at: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO experiment_assignment (participant_id, experiment_name, variant, assigned_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(participant_id, experiment_name)
                DO UPDATE SET
                    variant=excluded.variant,
                    assigned_at=excluded.assigned_at
                """,
                (participant_id, experiment_name, variant, assigned_at),
            )

    def add_experiment_event(
        self,
        participant_id: str,
        experiment_name: str,
        variant: str,
        event_type: str,
        payload: dict,
        timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO experiment_events (
                    participant_id, experiment_name, variant, event_type, payload_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    participant_id,
                    experiment_name,
                    variant,
                    event_type,
                    json.dumps(payload, ensure_ascii=True),
                    timestamp,
                ),
            )

    def list_experiment_events(
        self,
        participant_id: str | None = None,
        experiment_name: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[object] = []
        if participant_id:
            clauses.append("participant_id=?")
            params.append(participant_id)
        if experiment_name:
            clauses.append("experiment_name=?")
            params.append(experiment_name)
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT participant_id, experiment_name, variant, event_type, payload_json, timestamp
                FROM experiment_events
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        events: list[dict] = []
        for row in rows:
            data = dict(row)
            data["payload"] = json.loads(data.pop("payload_json") or "{}")
            events.append(data)
        return events

    def recent_literacy_events(self, participant_id: str, limit: int = 25) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type, source, signal_type, signal_confidence, category, amount, app_name, note, reason, stage, daily_spend, daily_safe_limit, timestamp
                FROM literacy_events
                WHERE participant_id=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (participant_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_alert_features(self, participant_id: str, limit: int = 25) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT alert_id, timestamp, amount, projected_spend, daily_safe_limit, spend_ratio,
                       txn_anomaly_score, hour_of_day, rapid_txn_flag, upi_open_flag,
                       recent_dismissals_24h, risk_score, confidence_score, tone_selected, frequency_bucket
                FROM alert_features
                WHERE participant_id=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (participant_id, limit),
            ).fetchall()
        records: list[dict] = []
        for row in rows:
            data = dict(row)
            data["rapid_txn_flag"] = bool(data["rapid_txn_flag"])
            data["upi_open_flag"] = bool(data["upi_open_flag"])
            records.append(data)
        return records

    def recent_alert_feedback(self, participant_id: str, limit: int = 25) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT alert_id, action, channel, title, message, timestamp
                FROM alert_feedback
                WHERE participant_id=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (participant_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_grievance(
        self,
        participant_id: str,
        category: str,
        details: str,
        timestamp: str,
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO grievances (participant_id, category, details, status, created_at, updated_at)
                VALUES (?, ?, ?, 'open', ?, ?)
                """,
                (participant_id, category, details, timestamp, timestamp),
            )
            return int(cur.lastrowid)

    def update_grievance_status(self, grievance_id: int, status: str, timestamp: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE grievances
                SET status=?, updated_at=?
                WHERE id=?
                """,
                (status, timestamp, grievance_id),
            )
            return cur.rowcount > 0

    def list_grievances(self, participant_id: str | None = None, limit: int = 100) -> list[dict]:
        with self._connect() as conn:
            if participant_id:
                rows = conn.execute(
                    """
                    SELECT id, participant_id, category, details, status, created_at, updated_at
                    FROM grievances
                    WHERE participant_id=?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (participant_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT id, participant_id, category, details, status, created_at, updated_at
                    FROM grievances
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def goal_memory_rows(self, participant_id: str, merchant_key: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT goal, positive_count, negative_count, updated_at
                FROM goal_memory
                WHERE participant_id=? AND merchant_key=?
                ORDER BY updated_at DESC
                """,
                (participant_id, merchant_key),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_goal_memory(
        self,
        participant_id: str,
        merchant_key: str,
        goal: str,
        delta_positive: int,
        delta_negative: int,
        timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO goal_memory (
                    participant_id, merchant_key, goal, positive_count, negative_count, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(participant_id, merchant_key, goal)
                DO UPDATE SET
                    positive_count=MAX(0, goal_memory.positive_count + excluded.positive_count),
                    negative_count=MAX(0, goal_memory.negative_count + excluded.negative_count),
                    updated_at=excluded.updated_at
                """,
                (
                    participant_id,
                    merchant_key,
                    goal,
                    delta_positive,
                    delta_negative,
                    timestamp,
                ),
            )

    def add_goal_feedback(
        self,
        participant_id: str,
        alert_id: str,
        merchant_key: str,
        selected_goal: str,
        is_essential: bool,
        source_confidence: float,
        timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO goal_feedback (
                    participant_id, alert_id, merchant_key, selected_goal, is_essential, source_confidence, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    participant_id,
                    alert_id,
                    merchant_key,
                    selected_goal,
                    1 if is_essential else 0,
                    source_confidence,
                    timestamp,
                ),
            )

    def upsert_alert_goal_context(
        self,
        alert_id: str,
        participant_id: str,
        merchant_key: str,
        inferred_goal: str,
        confidence: float,
        gate_passed: bool,
        source: str,
        timestamp: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO alert_goal_context (
                    alert_id, participant_id, merchant_key, inferred_goal, confidence, gate_passed, source, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(alert_id)
                DO UPDATE SET
                    merchant_key=excluded.merchant_key,
                    inferred_goal=excluded.inferred_goal,
                    confidence=excluded.confidence,
                    gate_passed=excluded.gate_passed,
                    source=excluded.source,
                    timestamp=excluded.timestamp
                """,
                (
                    alert_id,
                    participant_id,
                    merchant_key,
                    inferred_goal,
                    confidence,
                    1 if gate_passed else 0,
                    source,
                    timestamp,
                ),
            )

    def get_alert_goal_context(self, alert_id: str, participant_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT alert_id, participant_id, merchant_key, inferred_goal, confidence, gate_passed, source, timestamp
                FROM alert_goal_context
                WHERE alert_id=? AND participant_id=?
                """,
                (alert_id, participant_id),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["gate_passed"] = bool(data["gate_passed"])
        return data

    def recent_goal_feedback(self, participant_id: str, limit: int = 25) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT alert_id, merchant_key, selected_goal, is_essential, source_confidence, timestamp
                FROM goal_feedback
                WHERE participant_id=?
                ORDER BY id DESC
                LIMIT ?
                """,
                (participant_id, limit),
            ).fetchall()
        records: list[dict] = []
        for row in rows:
            item = dict(row)
            item["is_essential"] = bool(item["is_essential"])
            records.append(item)
        return records
