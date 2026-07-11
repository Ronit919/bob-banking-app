"""
services/auth_service.py
------------------------
Authentication business logic for the Banking Web Application.

Responsibilities:
  • Look up a user record by username (parameterised query — no SQL injection).
  • Verify a plain-text password against the stored hash (Werkzeug).
  • Write / clear the server-side Flask session.
  • Provide a login_required decorator for protecting Flask routes.

This module does NOT import Flask routing primitives so it can be unit-tested
without a running application context.  The decorator and session helpers do
import Flask's session and redirect utilities — those are imported lazily at
the top so the module remains importable from test contexts that have an
app context pushed.
"""

from functools import wraps

from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash

from database import get_connection


# ---------------------------------------------------------------------------
# User lookup
# ---------------------------------------------------------------------------

def get_user_by_username(username: str, db_path: str = None):
    """
    Retrieve a user record from the database by username.

    Uses a parameterised query to prevent SQL injection.

    Returns:
        sqlite3.Row if found, None otherwise.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, display_name, password_hash "
            "FROM users WHERE username = ?",
            (username,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Password verification
# ---------------------------------------------------------------------------

def verify_password(plain_text: str, stored_hash: str) -> bool:
    """
    Compare a plain-text password against a Werkzeug password hash.

    Never use == for password comparison — always use check_password_hash
    to ensure constant-time comparison and correct hash format handling.

    Returns:
        True if the password matches, False otherwise.
    """
    return check_password_hash(stored_hash, plain_text)


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def create_session(user_row) -> None:
    """
    Write the authenticated user's non-sensitive identifiers into the Flask
    session cookie.

    Only user_id and display_name are stored — never the password hash or
    any other sensitive field.
    """
    session.clear()
    session["user_id"] = user_row["id"]
    session["display_name"] = user_row["display_name"]
    session["username"] = user_row["username"]


def destroy_session() -> None:
    """
    Completely clear the Flask session, effectively logging the user out.
    Flask will instruct the browser to delete the session cookie.
    """
    session.clear()


# ---------------------------------------------------------------------------
# login_required decorator
# ---------------------------------------------------------------------------

def login_required(f):
    """
    Route decorator that rejects unauthenticated requests.

    Usage:
        @app.route('/dashboard')
        @login_required
        def dashboard():
            ...

    If session['user_id'] is not present the request is redirected to the
    login page with an informational flash message.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("login_get"))
        return f(*args, **kwargs)
    return decorated_function
