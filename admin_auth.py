from __future__ import annotations

import hashlib
import hmac
import os
import sqlite3
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "users.db"
PASSWORD_ITERATIONS = 600_000
DEFAULT_ADMIN_USERNAME = os.getenv("BASKETBALL_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("BASKETBALL_ADMIN_PASSWORD", "Admin@123")


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if salt is None:
        salt = os.urandom(32)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return digest.hex(), salt.hex()


def initialize_admin_database() -> None:
    with _connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing = con.execute("SELECT admin_id FROM admin_users LIMIT 1").fetchone()
        if existing is None:
            password_hash, password_salt = _hash_password(DEFAULT_ADMIN_PASSWORD)
            con.execute(
                "INSERT INTO admin_users (username, password_hash, password_salt) VALUES (?, ?, ?)",
                (DEFAULT_ADMIN_USERNAME.strip().lower(), password_hash, password_salt),
            )
        con.commit()


def authenticate_admin(username: str, password: str) -> bool:
    with _connect() as con:
        row = con.execute(
            "SELECT username, password_hash, password_salt FROM admin_users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
    if row is None:
        return False
    submitted, _ = _hash_password(password, bytes.fromhex(row["password_salt"]))
    return hmac.compare_digest(submitted, row["password_hash"])


def initialize_admin_session() -> None:
    st.session_state.setdefault("admin_logged_in", False)
    st.session_state.setdefault("admin_username", None)


def set_admin_session(username: str) -> None:
    st.session_state.admin_logged_in = True
    st.session_state.admin_username = username.strip().lower()


def clear_admin_session() -> None:
    for key in ["admin_logged_in", "admin_username"]:
        st.session_state.pop(key, None)
    initialize_admin_session()


def is_admin_logged_in() -> bool:
    return bool(st.session_state.get("admin_logged_in"))
