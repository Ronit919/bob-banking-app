"""
services/account_service.py
----------------------------
Account and transaction business logic for the Banking Web Application.

Responsibilities:
  • Retrieve the current balance for a given user.
  • Process deposits atomically (update balance + insert transaction record).
  • Process withdrawals atomically with an insufficient-funds guard.

Design rules:
  • No Flask imports — pure Python so this module is independently testable.
  • All writes use a single connection with explicit commit / rollback to
    guarantee atomicity.
  • Monetary amounts are rounded to 2 decimal places before storage to avoid
    floating-point drift.
"""

from database import get_connection


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class InsufficientFundsError(Exception):
    """Raised when a withdrawal amount exceeds the available account balance."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_account(cursor, user_id: int):
    """
    Fetch the account row for a given user.  Raises RuntimeError if not found
    so callers receive a clear signal rather than a silent None.
    """
    cursor.execute(
        "SELECT id, balance FROM accounts WHERE user_id = ?",
        (user_id,),
    )
    account = cursor.fetchone()
    if account is None:
        raise RuntimeError(f"No account found for user_id={user_id}.")
    return account


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_balance(user_id: int, db_path: str = None) -> float:
    """
    Return the current balance for the account belonging to user_id.

    Args:
        user_id: The authenticated user's primary key.
        db_path: Optional DB path override (used by tests with ':memory:').

    Returns:
        Current balance as a float rounded to 2 decimal places.
    """
    conn = get_connection(db_path)
    try:
        account = _get_account(conn.cursor(), user_id)
        return round(account["balance"], 2)
    finally:
        conn.close()


def deposit(user_id: int, amount: float, db_path: str = None) -> float:
    """
    Add *amount* to the account balance and record the transaction.

    The balance update and transaction insert are committed as a single unit.
    If either write fails the entire operation is rolled back.

    Args:
        user_id: The authenticated user's primary key.
        amount:  Positive monetary amount to deposit.
        db_path: Optional DB path override.

    Returns:
        New balance as a float rounded to 2 decimal places.

    Raises:
        ValueError: If amount is not positive.
    """
    amount = round(float(amount), 2)
    if amount <= 0:
        raise ValueError("Deposit amount must be greater than zero.")

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        account = _get_account(cursor, user_id)
        new_balance = round(account["balance"] + amount, 2)

        cursor.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?",
            (new_balance, account["id"]),
        )
        cursor.execute(
            "INSERT INTO transactions (account_id, type, amount) VALUES (?, 'deposit', ?)",
            (account["id"], amount),
        )
        conn.commit()
        return new_balance
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def withdraw(user_id: int, amount: float, db_path: str = None) -> float:
    """
    Deduct *amount* from the account balance and record the transaction.

    Checks that sufficient funds are available before modifying any data.
    The balance update and transaction insert are committed as a single unit.

    Args:
        user_id: The authenticated user's primary key.
        amount:  Positive monetary amount to withdraw.
        db_path: Optional DB path override.

    Returns:
        New balance as a float rounded to 2 decimal places.

    Raises:
        ValueError:              If amount is not positive.
        InsufficientFundsError:  If current balance < amount.
    """
    amount = round(float(amount), 2)
    if amount <= 0:
        raise ValueError("Withdrawal amount must be greater than zero.")

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        account = _get_account(cursor, user_id)

        if account["balance"] < amount:
            raise InsufficientFundsError(
                f"Insufficient funds. "
                f"Your current balance is ${account['balance']:,.2f}."
            )

        new_balance = round(account["balance"] - amount, 2)

        cursor.execute(
            "UPDATE accounts SET balance = ? WHERE id = ?",
            (new_balance, account["id"]),
        )
        cursor.execute(
            "INSERT INTO transactions (account_id, type, amount) VALUES (?, 'withdrawal', ?)",
            (account["id"], amount),
        )
        conn.commit()
        return new_balance
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_transaction_history(user_id: int, limit: int = 10, db_path: str = None) -> list:
    """
    Return the most recent transactions for the account belonging to user_id.

    Transactions are returned newest-first.  Results are converted from
    sqlite3.Row objects to plain dicts so templates can iterate them freely.

    Args:
        user_id:  The authenticated user's primary key.
        limit:    Maximum number of records to return (default 10).
        db_path:  Optional DB path override.

    Returns:
        List of dicts with keys: id, type, amount, created_at.
        Empty list if no transactions exist yet.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        account = _get_account(cursor, user_id)
        cursor.execute(
            """
            SELECT id, type, amount, created_at
            FROM   transactions
            WHERE  account_id = ?
            ORDER  BY id DESC
            LIMIT  ?
            """,
            (account["id"], limit),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
