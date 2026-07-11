"""
tests/test_e2e.py
-----------------
End-to-end functional test covering the complete user journey:

    Login → View Balance → Deposit → Withdraw → Verify Balance → Logout

This test treats the application as a black box — it only interacts through
HTTP via Flask's test client, exactly as a browser would.  It verifies that
all layers (routes, services, database) work together correctly for the
primary happy path and the primary failure path (insufficient funds).

Run:
    cd BACKEND
    pytest tests/test_e2e.py -v
"""

import sys
import os

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
import database
from app import app as flask_app


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def e2e_app(tmp_path, monkeypatch):
    """
    Provide a fully-configured Flask test application backed by a fresh
    temporary SQLite database.

    Isolation guarantees:
      • Each test function gets a unique tmp_path directory, so a new
        bank.db is created for every test — no shared state.
      • monkeypatch overrides DATABASE_PATH in both database and config
        modules so service-layer code reads/writes the temp DB.
    """
    db_path = str(tmp_path / "e2e_bank.db")

    monkeypatch.setattr("database.DATABASE_PATH", db_path)
    monkeypatch.setattr("config.DATABASE_PATH", db_path)

    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="e2e-test-secret-key",
    )

    database.init_db(db_path)
    database.seed_db(db_path)   # Creates demo / password123 with $1,000.00

    yield flask_app


@pytest.fixture
def browser(e2e_app):
    """
    Return a stateful Flask test client.

    Named 'browser' to emphasise that this fixture models a browser session
    across multiple page visits.
    """
    return e2e_app.test_client()


# ===========================================================================
# E2E — Primary happy path
# ===========================================================================

class TestFullUserJourney:
    """
    Covers the complete primary path a customer follows every session:

        1. Visit root — redirected to login
        2. Log in with valid credentials
        3. Dashboard loads and shows correct opening balance ($1,000.00)
        4. Deposit $500 — balance becomes $1,500.00
        5. Withdraw $200 — balance becomes $1,300.00
        6. Confirm final balance is $1,300.00
        7. Log out — session cleared
        8. Confirm dashboard is inaccessible after logout
    """

    def test_step_1_root_redirects_to_login(self, browser):
        """Visiting / redirects unauthenticated users to the login page."""
        response = browser.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_step_2_login_with_valid_credentials(self, browser):
        """
        Submitting the correct username and password redirects to /dashboard
        and sets the session.
        """
        response = browser.post(
            "/login",
            data={"username": "demo", "password": "password123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_step_3_dashboard_shows_opening_balance(self, browser):
        """
        After login, the dashboard shows the seeded opening balance of $1,000.00
        and the customer's display name.
        """
        browser.post(
            "/login",
            data={"username": "demo", "password": "password123"},
        )
        response = browser.get("/dashboard")
        assert response.status_code == 200
        assert b"Alex Johnson" in response.data
        assert b"1,000.00" in response.data

    def test_step_4_deposit_500_updates_balance(self, browser):
        """
        Depositing $500 increases the balance from $1,000.00 to $1,500.00.
        The success message and updated balance both appear on the dashboard.
        """
        browser.post(
            "/login",
            data={"username": "demo", "password": "password123"},
        )
        response = browser.post(
            "/deposit",
            data={"amount": "500"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Successfully deposited" in response.data
        assert b"500.00" in response.data
        assert b"1,500.00" in response.data

    def test_step_5_withdraw_200_updates_balance(self, browser):
        """
        After a $500 deposit (balance = $1,500.00), withdrawing $200 reduces
        the balance to $1,300.00.  The success message appears.
        """
        browser.post(
            "/login",
            data={"username": "demo", "password": "password123"},
        )
        browser.post("/deposit", data={"amount": "500"})

        response = browser.post(
            "/withdraw",
            data={"amount": "200"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Successfully withdrew" in response.data
        assert b"1,300.00" in response.data

    def test_step_6_final_balance_is_correct(self, browser):
        """
        After deposit($500) then withdraw($200), a fresh GET /dashboard
        shows the definitive balance of $1,300.00 — confirming the database
        state is persistent across requests.
        """
        browser.post(
            "/login",
            data={"username": "demo", "password": "password123"},
        )
        browser.post("/deposit", data={"amount": "500"})
        browser.post("/withdraw", data={"amount": "200"})

        response = browser.get("/dashboard")
        assert response.status_code == 200
        assert b"1,300.00" in response.data

    def test_step_7_logout_clears_session(self, browser):
        """
        Clicking logout redirects to /login and shows a confirmation message.
        """
        browser.post(
            "/login",
            data={"username": "demo", "password": "password123"},
        )
        response = browser.get("/logout", follow_redirects=True)
        assert response.status_code == 200
        assert b"logged out" in response.data
        # Must be back on the login page.
        assert b"Customer Login" in response.data

    def test_step_8_dashboard_inaccessible_after_logout(self, browser):
        """
        After logging out, accessing /dashboard redirects back to /login —
        confirming the session was completely cleared.
        """
        browser.post(
            "/login",
            data={"username": "demo", "password": "password123"},
        )
        browser.get("/logout")  # log out

        response = browser.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ===========================================================================
# E2E — Complete journey as a single sequential test
# ===========================================================================

class TestFullJourneySequential:
    """
    Single test that drives the entire Login → Deposit → Withdraw → Logout
    sequence in one continuous browser session against one shared database.

    This mirrors the manual testing checklist and proves that state (balance)
    accumulates correctly across multiple HTTP round trips.
    """

    def test_complete_login_deposit_withdraw_logout_flow(self, browser):
        """
        Full sequential E2E:
          • Login                     → redirects to dashboard
          • View dashboard            → opening balance $1,000.00
          • Deposit $300              → balance $1,300.00, success flash
          • Withdraw $150             → balance $1,150.00, success flash
          • Attempt withdraw $9,000   → rejected, balance unchanged
          • Logout                    → redirected to login, session gone
          • Access dashboard          → redirected to login (not /dashboard)
        """
        # ── 1. Login ────────────────────────────────────────────────────────
        r = browser.post(
            "/login",
            data={"username": "demo", "password": "password123"},
            follow_redirects=True,
        )
        assert b"Dashboard" in r.data, "Should land on dashboard after login."
        assert b"1,000.00" in r.data, "Opening balance should be $1,000.00."

        # ── 2. Deposit $300 ─────────────────────────────────────────────────
        r = browser.post(
            "/deposit",
            data={"amount": "300"},
            follow_redirects=True,
        )
        assert b"Successfully deposited" in r.data
        assert b"1,300.00" in r.data, "Balance should be $1,300.00 after deposit."

        # ── 3. Withdraw $150 ────────────────────────────────────────────────
        r = browser.post(
            "/withdraw",
            data={"amount": "150"},
            follow_redirects=True,
        )
        assert b"Successfully withdrew" in r.data
        assert b"1,150.00" in r.data, "Balance should be $1,150.00 after withdrawal."

        # ── 4. Attempt to overdraw ───────────────────────────────────────────
        r = browser.post(
            "/withdraw",
            data={"amount": "9000"},
            follow_redirects=True,
        )
        assert b"Insufficient funds" in r.data
        assert b"1,150.00" in r.data, "Balance must be unchanged after failed withdrawal."

        # ── 5. Logout ────────────────────────────────────────────────────────
        r = browser.get("/logout", follow_redirects=True)
        assert b"logged out" in r.data
        assert b"Customer Login" in r.data, "Should return to login page."

        # ── 6. Dashboard blocked after logout ────────────────────────────────
        r = browser.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]


# ===========================================================================
# E2E — Invalid login path
# ===========================================================================

class TestInvalidLoginJourney:
    """
    Validates that the login error path is secure and user-friendly.
    """

    def test_wrong_password_does_not_reach_dashboard(self, browser):
        """
        A user with the correct username but wrong password must NOT reach
        the dashboard and must receive a generic error message.
        """
        r = browser.post(
            "/login",
            data={"username": "demo", "password": "wrongpassword"},
            follow_redirects=True,
        )
        assert r.status_code == 401
        assert b"Invalid username or password" in r.data
        assert b"Dashboard" not in r.data

    def test_unknown_user_does_not_reach_dashboard(self, browser):
        """
        An entirely unknown username must fail with the same generic message —
        preventing username enumeration.
        """
        r = browser.post(
            "/login",
            data={"username": "hacker", "password": "anything"},
            follow_redirects=True,
        )
        assert r.status_code == 401
        assert b"Invalid username or password" in r.data
        assert b"Dashboard" not in r.data

    def test_empty_credentials_do_not_reach_dashboard(self, browser):
        """
        Submitting completely empty credentials is rejected at the backend
        validation layer (HTTP 400) and never reaches credential checking.
        """
        r = browser.post(
            "/login",
            data={"username": "", "password": ""},
            follow_redirects=True,
        )
        assert r.status_code == 400
        assert b"Dashboard" not in r.data
