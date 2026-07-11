"""
init_db.py
----------
Standalone database initialisation and seeding script.

Run this script once before starting the application for the first time,
or any time you want to reset the database to its initial seeded state.

Usage (from the BACKEND/ directory, with the virtual environment active):

    python init_db.py

What it does:
  1. Drops bank.db if it already exists (fresh-start reset).
  2. Creates the three tables: users, accounts, transactions.
  3. Seeds one demo customer account so the app can be used immediately.

Demo credentials created by this script:
  Username : demo
  Password : password123
  Balance  : $1,000.00

WARNING: Running this script will DELETE all existing data in bank.db.
         Do not run it against a database that holds real customer data.
"""

import os
import sys
import logging

# ---------------------------------------------------------------------------
# Ensure BACKEND/ is on the Python path so imports resolve whether this
# script is run directly or via `python -m`.
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import database
from config import DATABASE_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def reset_and_seed() -> None:
    """
    Drop and recreate bank.db, then seed it with the demo account.

    Asks for confirmation before deleting an existing database so accidental
    runs cannot silently destroy data.
    """
    if os.path.exists(DATABASE_PATH):
        answer = input(
            f"\nbank.db already exists at:\n  {DATABASE_PATH}\n\n"
            "This will DELETE all existing data. Continue? [y/N] "
        ).strip().lower()
        if answer != "y":
            logger.info("Aborted — database was not modified.")
            sys.exit(0)
        os.remove(DATABASE_PATH)
        logger.info("Existing bank.db removed.")

    logger.info("Creating tables …")
    database.init_db()
    logger.info("Tables created: users, accounts, transactions.")

    logger.info("Seeding demo account …")
    database.seed_db()
    logger.info("Demo account seeded.")

    logger.info(
        "\nDatabase initialised successfully.\n"
        "  Username : demo\n"
        "  Password : password123\n"
        "  Balance  : $1,000.00\n"
        "\nRun the application with:  python app.py"
    )


if __name__ == "__main__":
    reset_and_seed()
