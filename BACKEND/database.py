"""
database.py
-----------
SQLite connection helper and schema initialisation for the Banking Web Application.

Responsibilities:
  • Open a per-request SQLite connection with column-name row access.
  • Create tables (users, accounts, transactions) if they do not exist.
  • Seed one test user + account on first run so the app is immediately usable.

No Flask imports live here — this module is pure Python so it can be used by
both the Flask application and the test suite (with an in-memory DB).
"""

import sqlite3
import os

from werkzeug.security import generate_password_hash

from config import DATABASE_PATH


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Open and return a SQLite connection.

    Uses sqlite3.Row as the row factory so query results support column-name
    access (e.g. row['balance']) rather than positional index access.

    Args:
        db_path: Optional override path.  Defaults to DATABASE_PATH from
                 config.py.  Pass ':memory:' in tests to get an isolated DB.
    """
    path = db_path or DATABASE_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # Enforce foreign-key constraints on every connection.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db(db_path: str = None) -> None:
    """
    Create tables if they do not already exist.

    Safe to call at every application startup — uses CREATE TABLE IF NOT EXISTS
    so existing data is never touched.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()

        # --- users table ---------------------------------------------------
        # Stores customer identity and hashed credentials.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                display_name  TEXT    NOT NULL,
                password_hash TEXT    NOT NULL
            )
        """)

        # --- accounts table ------------------------------------------------
        # One account per user; balance stored as REAL (64-bit float).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL UNIQUE,
                balance    REAL    NOT NULL DEFAULT 0.0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # --- transactions table --------------------------------------------
        # Immutable audit log of every deposit and withdrawal.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id  INTEGER NOT NULL,
                type        TEXT    NOT NULL CHECK(type IN ('deposit', 'withdrawal')),
                amount      REAL    NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        """)

        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def seed_db(db_path: str = None) -> None:
    """
    Insert a demo user + account if no users exist yet.

    This lets a developer log in immediately after first run without any
    manual database work.

    Demo credentials:
        Username : demo
        Password : password123
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM users")
        row = cursor.fetchone()
        if row["cnt"] > 0:
            # Data already exists — skip seeding.
            return

        hashed = generate_password_hash("password123")
        cursor.execute(
            "INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)",
            ("demo", "Alex Johnson", hashed),
        )
        user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO accounts (user_id, balance) VALUES (?, ?)",
            (user_id, 1000.00),
        )
        conn.commit()
    finally:
        conn.close()
