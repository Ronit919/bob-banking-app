"""
tests/test_integration.py
--------------------------
Integration tests for the Flask application.

Uses Flask's built-in test client to simulate real HTTP requests — no
actual server is started.  Each test gets its own isolated temporary
database so tests cannot interfere with one another.

Run:
    cd BACKEND
    pytest tests/test_integration.py -v
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
def test_app(tmp_path, monkeypatch):
    """
    Configure the Flask app for testing:
      • TESTING = True          — disables error propagation to the test client.
      • WTF_CSRF_ENABLED = False — no CSRF tokens in tests.
      • DATABASE_PATH overridden via monkeypatch so each test uses a fresh DB.
    """
    db_path = str(tmp_path / "test_bank.db")

    # Patch the DATABASE_PATH that database.py reads.
    monkeypatch.setattr("database.DATABASE_PATH", db_path)
    monkeypatch.setattr("config.DATABASE_PATH", db_path)

    flask_app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret-key",
    )

    # Initialise and seed the isolated DB.
    database.init_db(db_path)
    database.seed_db(db_path)

    yield flask_app


@pytest.fixture
def client(test_app):
    """Return a Flask test client with cookie support."""
    return test_app.test_client()


@pytest.fixture
def auth_client(client):
    """
    Return a test client that is already logged in as the demo user.
    Reuses the 'client' fixture so the same DB isolation applies.
    """
    client.post(
        "/login",
        data={"username": "demo", "password": "password123"},
        follow_redirects=False,
    )
    return client


# ===========================================================================
# Root redirect
# ===========================================================================

class TestRootRedirect:

    def test_root_redirects_to_login(self, client):
        """GET / must redirect to /login."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ===========================================================================
# GET /login
# ===========================================================================

class TestLoginPage:

    def test_login_page_renders(self, client):
        """GET /login returns 200 and contains the login form."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Customer Login" in response.data

    def test_logged_in_user_is_redirected_to_dashboard(self, auth_client):
        """A user who is already logged in is redirected away from /login."""
        response = auth_client.get("/login", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]


# ===========================================================================
# POST /login
# ===========================================================================

class TestLoginPost:

    def test_valid_credentials_redirect_to_dashboard(self, client):
        """Correct credentials redirect to /dashboard."""
        response = client.post(
            "/login",
            data={"username": "demo", "password": "password123"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]

    def test_wrong_password_returns_401(self, client):
        """Wrong password returns HTTP 401 and re-renders the login page."""
        response = client.post(
            "/login",
            data={"username": "demo", "password": "wrongpassword"},
            follow_redirects=True,
        )
        assert response.status_code == 401
        assert b"Invalid username or password" in response.data

    def test_unknown_username_returns_401(self, client):
        """Unknown username returns HTTP 401 with the same generic message."""
        response = client.post(
            "/login",
            data={"username": "ghost", "password": "anything"},
            follow_redirects=True,
        )
        assert response.status_code == 401
        assert b"Invalid username or password" in response.data

    def test_empty_username_returns_400(self, client):
        """Missing username field returns HTTP 400."""
        response = client.post(
            "/login",
            data={"username": "", "password": "password123"},
            follow_redirects=True,
        )
        assert response.status_code == 400
        assert b"Username is required" in response.data

    def test_empty_password_returns_400(self, client):
        """Missing password field returns HTTP 400."""
        response = client.post(
            "/login",
            data={"username": "demo", "password": ""},
            follow_redirects=True,
        )
        assert response.status_code == 400
        assert b"Password is required" in response.data

    def test_login_error_never_mentions_which_field_wrong(self, client):
        """
        The error message for a wrong password must NOT say 'username not found'
        or 'wrong password' — only a generic message to prevent enumeration.
        """
        response = client.post(
            "/login",
            data={"username": "demo", "password": "wrong"},
            follow_redirects=True,
        )
        assert b"username not found" not in response.data.lower()
        assert b"wrong password" not in response.data.lower()


# ===========================================================================
# GET /dashboard
# ===========================================================================

class TestDashboard:

    def test_dashboard_accessible_when_logged_in(self, auth_client):
        """Authenticated user reaches the dashboard (HTTP 200)."""
        response = auth_client.get("/dashboard")
        assert response.status_code == 200
        assert b"Dashboard" in response.data

    def test_dashboard_shows_display_name(self, auth_client):
        """Dashboard contains the customer's display name."""
        response = auth_client.get("/dashboard")
        assert b"Alex Johnson" in response.data

    def test_dashboard_shows_balance(self, auth_client):
        """Dashboard shows the seeded balance value."""
        response = auth_client.get("/dashboard")
        assert b"1,000.00" in response.data

    def test_dashboard_redirects_unauthenticated(self, client):
        """Unauthenticated request to /dashboard redirects to /login."""
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ===========================================================================
# POST /deposit
# ===========================================================================

class TestDeposit:

    def test_valid_deposit_updates_balance(self, auth_client):
        """A $250 deposit should make the balance $1250."""
        auth_client.post("/deposit", data={"amount": "250"})
        response = auth_client.get("/dashboard")
        assert b"1,250.00" in response.data

    def test_valid_deposit_shows_success_message(self, auth_client):
        """A successful deposit shows a flash success message."""
        response = auth_client.post(
            "/deposit", data={"amount": "100"}, follow_redirects=True
        )
        assert b"Successfully deposited" in response.data

    def test_deposit_zero_shows_error(self, auth_client):
        """A zero deposit is rejected with an error flash message."""
        response = auth_client.post(
            "/deposit", data={"amount": "0"}, follow_redirects=True
        )
        assert b"greater than zero" in response.data

    def test_deposit_empty_amount_shows_error(self, auth_client):
        """An empty amount field is rejected."""
        response = auth_client.post(
            "/deposit", data={"amount": ""}, follow_redirects=True
        )
        assert b"enter a deposit amount" in response.data

    def test_deposit_non_numeric_shows_error(self, auth_client):
        """A non-numeric amount is rejected with an error flash message."""
        response = auth_client.post(
            "/deposit", data={"amount": "abc"}, follow_redirects=True
        )
        assert b"valid number" in response.data

    def test_deposit_negative_shows_error(self, auth_client):
        """A negative amount is rejected."""
        response = auth_client.post(
            "/deposit", data={"amount": "-50"}, follow_redirects=True
        )
        assert b"greater than zero" in response.data

    def test_deposit_unauthenticated_redirects(self, client):
        """Unauthenticated deposit request redirects to login."""
        response = client.post(
            "/deposit", data={"amount": "100"}, follow_redirects=False
        )
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ===========================================================================
# POST /withdraw
# ===========================================================================

class TestWithdraw:

    def test_valid_withdrawal_updates_balance(self, auth_client):
        """A $400 withdrawal reduces a $1000 balance to $600."""
        auth_client.post("/withdraw", data={"amount": "400"})
        response = auth_client.get("/dashboard")
        assert b"600.00" in response.data

    def test_valid_withdrawal_shows_success_message(self, auth_client):
        """A successful withdrawal shows a flash success message."""
        response = auth_client.post(
            "/withdraw", data={"amount": "100"}, follow_redirects=True
        )
        assert b"Successfully withdrew" in response.data

    def test_insufficient_funds_shows_error(self, auth_client):
        """Withdrawing more than the balance shows an insufficient-funds error."""
        response = auth_client.post(
            "/withdraw", data={"amount": "9999"}, follow_redirects=True
        )
        assert b"Insufficient funds" in response.data

    def test_insufficient_funds_balance_unchanged(self, auth_client):
        """A failed withdrawal must not change the balance."""
        auth_client.post("/withdraw", data={"amount": "9999"})
        response = auth_client.get("/dashboard")
        assert b"1,000.00" in response.data

    def test_withdraw_zero_shows_error(self, auth_client):
        """A zero withdrawal is rejected."""
        response = auth_client.post(
            "/withdraw", data={"amount": "0"}, follow_redirects=True
        )
        assert b"greater than zero" in response.data

    def test_withdraw_empty_amount_shows_error(self, auth_client):
        """An empty amount field is rejected."""
        response = auth_client.post(
            "/withdraw", data={"amount": ""}, follow_redirects=True
        )
        assert b"enter a withdrawal amount" in response.data

    def test_withdraw_non_numeric_shows_error(self, auth_client):
        """A non-numeric withdrawal amount is rejected."""
        response = auth_client.post(
            "/withdraw", data={"amount": "xyz"}, follow_redirects=True
        )
        assert b"valid number" in response.data

    def test_withdraw_unauthenticated_redirects(self, client):
        """Unauthenticated withdrawal request redirects to login."""
        response = client.post(
            "/withdraw", data={"amount": "100"}, follow_redirects=False
        )
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ===========================================================================
# GET /logout
# ===========================================================================

class TestLogout:

    def test_logout_redirects_to_login(self, auth_client):
        """Logout redirects to /login."""
        response = auth_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_logout_shows_success_message(self, auth_client):
        """Logout flash message confirms the user has been logged out."""
        response = auth_client.get("/logout", follow_redirects=True)
        assert b"logged out" in response.data

    def test_dashboard_inaccessible_after_logout(self, auth_client):
        """After logout, /dashboard redirects to /login."""
        auth_client.get("/logout")
        response = auth_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_logout_unauthenticated_redirects(self, client):
        """Calling /logout without a session redirects to /login."""
        response = client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ===========================================================================
# Custom error pages
# ===========================================================================

class TestErrorPages:

    def test_404_returns_custom_page(self, client):
        """A non-existent route returns a 404 with the custom error page."""
        response = client.get("/this-route-does-not-exist")
        assert response.status_code == 404
        assert b"404" in response.data
