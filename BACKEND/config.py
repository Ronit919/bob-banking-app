"""
config.py
---------
Central configuration for the Banking Web Application.

All environment-level settings are defined here so they are referenced from
a single location.  Values are read from environment variables; when a
.env file is present (local development), python-dotenv loads it
automatically so developers do not need to set variables in their shell.

In production, set FLASK_SECRET_KEY via the hosting platform's secrets
manager — never hard-code sensitive values in committed source.
"""

import os
from dotenv import load_dotenv

# Load variables from BACKEND/.env into os.environ (no-op if file absent).
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_file)

# ---------------------------------------------------------------------------
# Secret key — used by Flask to cryptographically sign session cookies.
# Falls back to a development default so the app starts without extra setup,
# but logs a clear warning when doing so.
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# ---------------------------------------------------------------------------
# SQLite database path — resolved relative to this file so it works from any
# working directory.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "bank.db")

# ---------------------------------------------------------------------------
# Debug flag — True during development (auto-reload, detailed errors).
# Must be False for any public-facing deployment.
# ---------------------------------------------------------------------------
DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
