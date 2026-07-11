"""
tests/test_services.py
-----------------------
Unit tests for auth_service and account_service.

All tests use an isolated in-memory SQLite database (':memory:') so they
never touch the real bank.db file and can run in any order without
side-effects.

Run:
    cd BACKEND
    pytest tests/test_services.py -v
"""

import sys
import os

# ---------------------------------------------------------------------------
# Make BACKEND/ importable when pytest is run from the BACKEND/ directory
# or from the project root.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import pytest
from werkzeug.security import generate_password_hash

import database
from services.auth_service import get_user_by_username, verify_password
from services.account_service import (
    get_balance,
    deposit,
    withdraw,
    get_transaction_history,
    InsufficientFundsError,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def db(tmp_path):
    """
    Provide a fresh, fully-initialised, temporary SQLite database for each
    test.  Uses tmp_path (a pytest built-in) so each test gets a unique file
    path and isolation is guaranteed.
    """
    db_path = str(tmp_path / "test_bank.db")
    database.init_db(db_path)
    database.seed_db(db_path)  # Creates demo user with $1000.00 balance.
    return db_path


# ===========================================================================
# auth_service — get_user_by_username
# ===========================================================================

class TestGetUserByUsername:

    def test_returns_user_when_username_exists(self, db):
        """A seeded user can be retrieved by their exact username."""
        user = get_user_by_username("demo", db_path=db)
        assert user is not None
        assert user["username"] == "demo"
        assert user["display_name"] == "Alex Johnson"

    def test_returns_none_when_username_missing(self, db):
        """Looking up a username that does not exist returns None."""
        user = get_user_by_username("nonexistent_user", db_path=db)
        assert user is None

    def test_lookup_is_case_sensitive(self, db):
        """Username comparison must be exact — 'DEMO' ≠ 'demo'."""
        user = get_user_by_username("DEMO", db_path=db)
        assert user is None

    def test_password_hash_is_not_plaintext(self, db):
        """The stored password must never be the plain-text password."""
        user = get_user_by_username("demo", db_path=db)
        assert user["password_hash"] != "password123"


# ===========================================================================
# auth_service — verify_password
# ===========================================================================

class TestVerifyPassword:

    def test_correct_password_returns_true(self, db):
        """Correct plain-text password matches the stored hash."""
        user = get_user_by_username("demo", db_path=db)
        assert verify_password("password123", user["password_hash"]) is True

    def test_wrong_password_returns_false(self, db):
        """An incorrect password does not match."""
        user = get_user_by_username("demo", db_path=db)
        assert verify_password("wrongpassword", user["password_hash"]) is False

    def test_empty_password_returns_false(self, db):
        """An empty string does not match any valid hash."""
        user = get_user_by_username("demo", db_path=db)
        assert verify_password("", user["password_hash"]) is False


# ===========================================================================
# account_service — get_balance
# ===========================================================================

class TestGetBalance:

    def test_returns_seeded_balance(self, db):
        """The seeded account starts with exactly $1000.00."""
        user = get_user_by_username("demo", db_path=db)
        balance = get_balance(user["id"], db_path=db)
        assert balance == 1000.00

    def test_returns_float(self, db):
        """Balance must be returned as a float, not an integer or string."""
        user = get_user_by_username("demo", db_path=db)
        balance = get_balance(user["id"], db_path=db)
        assert isinstance(balance, float)

    def test_raises_for_unknown_user(self, db):
        """An account lookup for a non-existent user raises RuntimeError."""
        with pytest.raises(RuntimeError):
            get_balance(99999, db_path=db)


# ===========================================================================
# account_service — deposit
# ===========================================================================

class TestDeposit:

    def test_increases_balance_by_exact_amount(self, db):
        """Depositing $250 raises the $1000 balance to exactly $1250."""
        user = get_user_by_username("demo", db_path=db)
        new_balance = deposit(user["id"], 250.00, db_path=db)
        assert new_balance == 1250.00

    def test_returns_new_balance(self, db):
        """deposit() returns the updated balance, not None."""
        user = get_user_by_username("demo", db_path=db)
        result = deposit(user["id"], 100.00, db_path=db)
        assert result == 1100.00

    def test_subsequent_deposits_accumulate(self, db):
        """Multiple deposits stack correctly on the same account."""
        user = get_user_by_username("demo", db_path=db)
        deposit(user["id"], 100.00, db_path=db)
        deposit(user["id"], 200.00, db_path=db)
        balance = get_balance(user["id"], db_path=db)
        assert balance == 1300.00

    def test_decimal_deposit_is_handled(self, db):
        """A fractional amount is rounded to 2 decimal places."""
        user = get_user_by_username("demo", db_path=db)
        new_balance = deposit(user["id"], 0.01, db_path=db)
        assert new_balance == 1000.01

    def test_zero_amount_raises_value_error(self, db):
        """A zero deposit is rejected with ValueError."""
        user = get_user_by_username("demo", db_path=db)
        with pytest.raises(ValueError, match="greater than zero"):
            deposit(user["id"], 0, db_path=db)

    def test_negative_amount_raises_value_error(self, db):
        """A negative deposit is rejected with ValueError."""
        user = get_user_by_username("demo", db_path=db)
        with pytest.raises(ValueError):
            deposit(user["id"], -50.00, db_path=db)

    def test_balance_unchanged_after_rejected_deposit(self, db):
        """A failed deposit must not alter the balance."""
        user = get_user_by_username("demo", db_path=db)
        try:
            deposit(user["id"], 0, db_path=db)
        except ValueError:
            pass
        assert get_balance(user["id"], db_path=db) == 1000.00


# ===========================================================================
# account_service — withdraw
# ===========================================================================

class TestWithdraw:

    def test_decreases_balance_by_exact_amount(self, db):
        """Withdrawing $300 from a $1000 balance yields $700."""
        user = get_user_by_username("demo", db_path=db)
        new_balance = withdraw(user["id"], 300.00, db_path=db)
        assert new_balance == 700.00

    def test_returns_new_balance(self, db):
        """withdraw() returns the updated balance."""
        user = get_user_by_username("demo", db_path=db)
        result = withdraw(user["id"], 500.00, db_path=db)
        assert result == 500.00

    def test_withdraw_entire_balance(self, db):
        """A user may withdraw the exact balance, leaving $0."""
        user = get_user_by_username("demo", db_path=db)
        new_balance = withdraw(user["id"], 1000.00, db_path=db)
        assert new_balance == 0.00

    def test_insufficient_funds_raises_error(self, db):
        """Withdrawing more than the balance raises InsufficientFundsError."""
        user = get_user_by_username("demo", db_path=db)
        with pytest.raises(InsufficientFundsError):
            withdraw(user["id"], 1000.01, db_path=db)

    def test_balance_unchanged_after_insufficient_funds(self, db):
        """A failed withdrawal must leave the balance unchanged (atomicity)."""
        user = get_user_by_username("demo", db_path=db)
        try:
            withdraw(user["id"], 9999.00, db_path=db)
        except InsufficientFundsError:
            pass
        assert get_balance(user["id"], db_path=db) == 1000.00

    def test_zero_amount_raises_value_error(self, db):
        """A zero withdrawal is rejected with ValueError."""
        user = get_user_by_username("demo", db_path=db)
        with pytest.raises(ValueError):
            withdraw(user["id"], 0, db_path=db)

    def test_negative_amount_raises_value_error(self, db):
        """A negative withdrawal is rejected with ValueError."""
        user = get_user_by_username("demo", db_path=db)
        with pytest.raises(ValueError):
            withdraw(user["id"], -100.00, db_path=db)

    def test_insufficient_funds_message_contains_balance(self, db):
        """The InsufficientFundsError message must include the current balance."""
        user = get_user_by_username("demo", db_path=db)
        with pytest.raises(InsufficientFundsError, match=r"\$1,000\.00"):
            withdraw(user["id"], 5000.00, db_path=db)

# ===========================================================================
# account_service — get_transaction_history
# ===========================================================================

class TestGetTransactionHistory:

    def test_empty_history_on_fresh_account(self, db):
        """A brand-new account has no transactions."""
        user = get_user_by_username("demo", db_path=db)
        history = get_transaction_history(user["id"], db_path=db)
        assert history == []

    def test_deposit_appears_in_history(self, db):
        """After a deposit, one transaction record is returned."""
        from services.account_service import get_transaction_history
        user = get_user_by_username("demo", db_path=db)
        deposit(user["id"], 100.00, db_path=db)
        history = get_transaction_history(user["id"], db_path=db)
        assert len(history) == 1
        assert history[0]["type"] == "deposit"
        assert history[0]["amount"] == 100.00

    def test_withdrawal_appears_in_history(self, db):
        """After a withdrawal, one transaction record is returned."""
        from services.account_service import get_transaction_history
        user = get_user_by_username("demo", db_path=db)
        withdraw(user["id"], 50.00, db_path=db)
        history = get_transaction_history(user["id"], db_path=db)
        assert len(history) == 1
        assert history[0]["type"] == "withdrawal"
        assert history[0]["amount"] == 50.00

    def test_history_ordered_newest_first(self, db):
        """Transactions are returned newest-first (descending by id)."""
        from services.account_service import get_transaction_history
        user = get_user_by_username("demo", db_path=db)
        deposit(user["id"], 10.00, db_path=db)
        deposit(user["id"], 20.00, db_path=db)
        history = get_transaction_history(user["id"], db_path=db)
        assert history[0]["amount"] == 20.00
        assert history[1]["amount"] == 10.00

    def test_limit_is_respected(self, db):
        """The limit parameter caps the number of returned records."""
        from services.account_service import get_transaction_history
        user = get_user_by_username("demo", db_path=db)
        for i in range(5):
            deposit(user["id"], float(i + 1) * 10, db_path=db)
        history = get_transaction_history(user["id"], limit=3, db_path=db)
        assert len(history) == 3

    def test_returns_list_of_dicts(self, db):
        """Each record is a plain dict with the expected keys."""
        from services.account_service import get_transaction_history
        user = get_user_by_username("demo", db_path=db)
        deposit(user["id"], 1.00, db_path=db)
        history = get_transaction_history(user["id"], db_path=db)
        record = history[0]
        assert isinstance(record, dict)
        assert "id" in record
        assert "type" in record
        assert "amount" in record
        assert "created_at" in record

