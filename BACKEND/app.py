"""
app.py
------
Flask application entry point for the Banking Web Application.

Responsibilities:
  • Create the Flask app object, pointing template and static folders at
    the FRONTEND/ directory (which lives one level above BACKEND/).
  • Load configuration from config.py.
  • Initialise and seed the SQLite database before the first request.
  • Register all routes: root redirect, login, logout, dashboard,
    deposit, and withdrawal.
  • Register custom 404 and 500 error handlers.

Run (development):
    cd BACKEND
    python app.py
"""

import os
import sys
import logging

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

# ---------------------------------------------------------------------------
# Path helpers — resolve FRONTEND/ folder relative to this file so the app
# works regardless of where it is launched from.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_TEMPLATES = os.path.join(PROJECT_ROOT, "FRONTEND", "templates")
FRONTEND_STATIC = os.path.join(PROJECT_ROOT, "FRONTEND", "static")

# ---------------------------------------------------------------------------
# Create the Flask application.
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=FRONTEND_TEMPLATES,
    static_folder=FRONTEND_STATIC,
)

# ---------------------------------------------------------------------------
# Load configuration.
# ---------------------------------------------------------------------------
import config  # noqa: E402

app.secret_key = config.SECRET_KEY
app.config["DEBUG"] = config.DEBUG

if config.SECRET_KEY == "dev-secret-key-change-in-production":
    logging.warning(
        "WARNING: Using the default development SECRET_KEY. "
        "Set the FLASK_SECRET_KEY environment variable before deploying."
    )

# ---------------------------------------------------------------------------
# Import services AFTER app is created (auth_service imports flask.session).
# ---------------------------------------------------------------------------
from services.auth_service import (  # noqa: E402
    get_user_by_username,
    verify_password,
    create_session,
    destroy_session,
    login_required,
)
from services.account_service import (  # noqa: E402
    get_balance,
    deposit as svc_deposit,
    withdraw as svc_withdraw,
    get_transaction_history,
    InsufficientFundsError,
)
import database  # noqa: E402

# ---------------------------------------------------------------------------
# Database initialisation — runs once before the very first request.
# ---------------------------------------------------------------------------
with app.app_context():
    database.init_db()
    database.seed_db()


# ===========================================================================
# Routes
# ===========================================================================

# ---------------------------------------------------------------------------
# Root — redirect to login.
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Redirect root URL to the login page."""
    return redirect(url_for("login_get"))


# ---------------------------------------------------------------------------
# Login — GET
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET"])
def login_get():
    """
    Render the login page.
    If the user already has an active session redirect directly to the
    dashboard — no need to see the login form again.
    """
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


# ---------------------------------------------------------------------------
# Login — POST
# ---------------------------------------------------------------------------
@app.route("/login", methods=["POST"])
def login_post():
    """
    Process the login form submission.

    Validation sequence:
      1. Check that username and password fields are not blank.
      2. Look up the user by username.
      3. Verify the password hash.
      4. On success create the session and redirect to dashboard.
      5. On any failure flash a generic error (never reveal which field failed).
    """
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Step 1 — presence checks.
    if not username:
        flash("Username is required.", "danger")
        return render_template("login.html"), 400
    if not password:
        flash("Password is required.", "danger")
        return render_template("login.html"), 400

    # Step 2 — user lookup.
    user = get_user_by_username(username)

    # Step 3 — credential verification.
    # Both "user not found" and "wrong password" return the same message to
    # avoid leaking which field was wrong (username enumeration prevention).
    if user is None or not verify_password(password, user["password_hash"]):
        flash("Invalid username or password. Please try again.", "danger")
        return render_template("login.html"), 401

    # Step 4 — create session and proceed.
    create_session(user)
    flash(f"Welcome back, {user['display_name']}!", "success")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------
@app.route("/logout")
@login_required
def logout():
    """Destroy the session and redirect to the login page."""
    destroy_session()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("login_get"))


# ---------------------------------------------------------------------------
# Dashboard — GET
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    """
    Render the customer dashboard with the current balance.

    The balance is read fresh from the database on every request — it is
    never cached in the session to avoid stale values.
    """
    user_id = session["user_id"]
    display_name = session["display_name"]
    try:
        balance = get_balance(user_id)
        transactions = get_transaction_history(user_id, limit=10)
    except RuntimeError as exc:
        logging.error("Dashboard balance error for user_id=%s: %s", user_id, exc)
        flash("Could not retrieve account balance. Please contact support.", "danger")
        balance = None
        transactions = []
    return render_template(
        "dashboard.html",
        display_name=display_name,
        balance=balance,
        transactions=transactions,
    )


# ---------------------------------------------------------------------------
# Deposit — POST
# ---------------------------------------------------------------------------
@app.route("/deposit", methods=["POST"])
@login_required
def deposit():
    """
    Process a deposit request.

    Validation sequence (backend — authoritative):
      1. Amount field must not be empty.
      2. Amount must be convertible to a float.
      3. Amount must be strictly greater than zero.
      4. Call account_service.deposit(); it raises ValueError for non-positive
         amounts (defence-in-depth).
    """
    raw_amount = request.form.get("amount", "").strip()
    user_id = session["user_id"]

    # Step 1 — presence.
    if not raw_amount:
        flash("Please enter a deposit amount.", "danger")
        return redirect(url_for("dashboard"))

    # Step 2 — numeric conversion.
    try:
        amount = float(raw_amount)
    except ValueError:
        flash("Deposit amount must be a valid number.", "danger")
        return redirect(url_for("dashboard"))

    # Step 3 — positive check.
    if amount <= 0:
        flash("Deposit amount must be greater than zero.", "danger")
        return redirect(url_for("dashboard"))

    # Step 4 — service call.
    try:
        new_balance = svc_deposit(user_id, amount)
        flash(
            f"Successfully deposited ${amount:,.2f}. "
            f"New balance: ${new_balance:,.2f}.",
            "success",
        )
    except ValueError as exc:
        flash(str(exc), "danger")
    except Exception as exc:
        logging.error("Deposit error for user_id=%s: %s", user_id, exc)
        flash("An unexpected error occurred during the deposit. Please try again.", "danger")

    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Withdraw — POST
# ---------------------------------------------------------------------------
@app.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
    """
    Process a withdrawal request.

    Validation sequence (backend — authoritative):
      1. Amount field must not be empty.
      2. Amount must be convertible to a float.
      3. Amount must be strictly greater than zero.
      4. Call account_service.withdraw(); it raises InsufficientFundsError
         when the balance is too low, or ValueError for non-positive amounts.
    """
    raw_amount = request.form.get("amount", "").strip()
    user_id = session["user_id"]

    # Step 1 — presence.
    if not raw_amount:
        flash("Please enter a withdrawal amount.", "danger")
        return redirect(url_for("dashboard"))

    # Step 2 — numeric conversion.
    try:
        amount = float(raw_amount)
    except ValueError:
        flash("Withdrawal amount must be a valid number.", "danger")
        return redirect(url_for("dashboard"))

    # Step 3 — positive check.
    if amount <= 0:
        flash("Withdrawal amount must be greater than zero.", "danger")
        return redirect(url_for("dashboard"))

    # Step 4 — service call.
    try:
        new_balance = svc_withdraw(user_id, amount)
        flash(
            f"Successfully withdrew ${amount:,.2f}. "
            f"New balance: ${new_balance:,.2f}.",
            "success",
        )
    except InsufficientFundsError as exc:
        flash(str(exc), "danger")
    except ValueError as exc:
        flash(str(exc), "danger")
    except Exception as exc:
        logging.error("Withdrawal error for user_id=%s: %s", user_id, exc)
        flash("An unexpected error occurred during the withdrawal. Please try again.", "danger")

    return redirect(url_for("dashboard"))


# ===========================================================================
# Error handlers
# ===========================================================================

@app.errorhandler(404)
def not_found(error):
    """Render a friendly 404 page instead of Flask's default."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    """Render a friendly 500 page. Never expose stack traces to users."""
    logging.error("500 error: %s", error)
    return render_template("500.html"), 500


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG if config.DEBUG else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=config.DEBUG,
    )
