from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "users.db"
APP_TIMEZONE_NAME = os.getenv("BASKETBALL_TIMEZONE", "America/New_York")
APP_TIMEZONE = ZoneInfo(APP_TIMEZONE_NAME)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_usage_tracking() -> None:
    """Create analytics tables and migrate the user role column when needed."""
    with get_connection() as connection:
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
        if "role" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id TEXT,
                event_type TEXT NOT NULL,
                page_name TEXT,
                player_id INTEGER,
                player_name TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_events(user_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_events(event_type)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_events(created_at)")

        connection.commit()


def ensure_session_id() -> str:
    if "analytics_session_id" not in st.session_state:
        st.session_state.analytics_session_id = str(uuid.uuid4())
    return st.session_state.analytics_session_id


def log_event(
    event_type: str,
    *,
    page_name: str | None = None,
    player_id: int | None = None,
    player_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write a lightweight product-usage event for the authenticated user."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO activity_events (
                user_id, session_id, event_type, page_name,
                player_id, player_name, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                ensure_session_id(),
                event_type,
                page_name,
                int(player_id) if player_id is not None else None,
                player_name,
                json.dumps(metadata or {}, default=str),
            ),
        )
        connection.commit()


def track_page_view(page_name: str) -> None:
    """Record navigation once when the user changes page, not on every widget rerun."""
    previous_page = st.session_state.get("analytics_last_page")
    if previous_page != page_name:
        log_event("page_view", page_name=page_name)
        st.session_state.analytics_last_page = page_name


def track_player_view(player_id: int, player_name: str) -> None:
    """Record a primary player-profile lookup once when the selected player changes."""
    key = f"{player_id}:{player_name}"
    if st.session_state.get("analytics_last_player") != key:
        log_event(
            "player_view",
            page_name="Player Profile",
            player_id=player_id,
            player_name=player_name,
        )
        st.session_state.analytics_last_player = key


def track_player_comparison(player_id: int | None, player_name: str | None) -> None:
    if player_id is None or not player_name:
        return
    key = f"{player_id}:{player_name}"
    if st.session_state.get("analytics_last_comparison") != key:
        log_event(
            "player_compare",
            page_name="Player Profile",
            player_id=player_id,
            player_name=player_name,
        )
        st.session_state.analytics_last_comparison = key


def _to_app_timezone(series: pd.Series) -> pd.Series:
    """Convert SQLite UTC timestamps to the dashboard timezone for display/filtering."""
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    return parsed.dt.tz_convert(APP_TIMEZONE)


def current_app_time() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(APP_TIMEZONE))


def read_users() -> pd.DataFrame:
    query = """
        SELECT user_id, username, first_name, last_name, role, created_at
        FROM users
        ORDER BY created_at
    """
    with get_connection() as connection:
        frame = pd.read_sql_query(query, connection)
    if "created_at" in frame:
        frame["created_at"] = _to_app_timezone(frame["created_at"])
    return frame


def read_events() -> pd.DataFrame:
    query = """
        SELECT
            e.event_id,
            e.user_id,
            u.username,
            u.first_name,
            u.last_name,
            u.role,
            e.session_id,
            e.event_type,
            e.page_name,
            e.player_id,
            e.player_name,
            e.metadata_json,
            e.created_at
        FROM activity_events e
        LEFT JOIN users u ON u.user_id = e.user_id
        ORDER BY e.created_at
    """
    with get_connection() as connection:
        frame = pd.read_sql_query(query, connection)
    if "created_at" in frame:
        frame["created_at"] = _to_app_timezone(frame["created_at"])
    return frame


