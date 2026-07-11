# SecureBank — Banking Web Application

A full-stack banking web application built with **Python Flask**, **Bootstrap 5**, and **SQLite**.

---

## Features

| Feature | Route |
|---|---|
| Customer Login | `GET /login` · `POST /login` |
| Dashboard — view balance | `GET /dashboard` |
| Deposit funds | `POST /deposit` |
| Withdraw funds | `POST /withdraw` |
| Recent transaction history | Embedded in `/dashboard` |
| Logout | `GET /logout` |

---

## Project Structure

```
project-root/
├── .gitignore
├── .env.example             ← Template for local env variables
├── IMPLEMENTATION_PLAN.md
├── STEP_BY_STEP_IMPLEMENTATION_GUIDE.md
├── README.md
│
├── FRONTEND/
│   ├── templates/
│   │   ├── base.html          ← Shared layout, Bootstrap 5 CDN, navbar, flash messages
│   │   ├── login.html         ← Customer login form
│   │   ├── dashboard.html     ← Balance card, deposit/withdraw forms, transaction history
│   │   ├── 404.html           ← Custom not-found page
│   │   └── 500.html           ← Custom server-error page
│   └── static/
│       ├── css/custom.css     ← Brand overrides (Bootstrap utility-first)
│       └── js/app.js          ← Password toggle, double-submit guard
│
└── BACKEND/
    ├── app.py                 ← Flask entry point — all routes registered here
    ├── config.py              ← SECRET_KEY, DATABASE_PATH, DEBUG (reads from .env)
    ├── database.py            ← SQLite helper, schema init (CREATE TABLE IF NOT EXISTS), seed data
    ├── init_db.py             ← Standalone DB reset + seed script
    ├── requirements.txt       ← Flask, Werkzeug, python-dotenv, pytest
    ├── .env                   ← Local secrets (git-ignored — copy from .env.example)
    ├── .env.example           ← Safe-to-commit template for .env
    ├── bank.db                ← Auto-created SQLite file (git-ignored)
    ├── services/
    │   ├── auth_service.py    ← User lookup, password hash, session create/destroy, @login_required
    │   └── account_service.py ← get_balance, deposit, withdraw, get_transaction_history
    └── tests/
        ├── test_services.py   ← Unit tests (pure Python, in-memory SQLite)
        ├── test_integration.py← Integration tests (Flask test client, per-test isolated DB)
        └── test_e2e.py        ← End-to-end functional tests (login → deposit → withdraw → logout)
```

---

## Quick Start

### 1 — Prerequisites

- **Python 3.9 or higher** — verify with `python --version`
- **pip** — bundled with modern Python distributions

### 2 — Set up the virtual environment

```bash
cd BACKEND
python -m venv venv
```

Activate it:

| Platform | Command |
|---|---|
| Windows (PowerShell) | `.\venv\Scripts\Activate.ps1` |
| Windows (cmd.exe) | `.\venv\Scripts\activate.bat` |
| macOS / Linux | `source venv/bin/activate` |

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure environment variables

Copy the example file and edit it with your own values:

```bash
# macOS / Linux
cp .env.example .env

# Windows (cmd.exe)
copy .env.example .env
```

The defaults in `.env.example` are safe for local development.
For production, generate a real secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as the value of `FLASK_SECRET_KEY` in `.env`.

### 5 — Initialise the database

```bash
python init_db.py
```

This creates `bank.db`, creates all three tables (`users`, `accounts`, `transactions`),
and seeds the demo account. Running it again will prompt before overwriting existing data.

### 6 — Run the application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

> The database is also initialised automatically on first run if `init_db.py` has not
> been run yet — `app.py` calls `database.init_db()` and `database.seed_db()` at startup.

### 7 — Demo credentials

| Field | Value |
|---|---|
| Username | `demo` |
| Password | `password123` |
| Opening balance | $1,000.00 |

---

## Running Tests

```bash
cd BACKEND
pytest tests/ -v
```

| Test file | Tests | What is covered |
|---|---|---|
| `tests/test_services.py` | 31 unit tests | auth service, account service, transaction history, all edge cases |
| `tests/test_integration.py` | 33 integration tests | every route, session state, error pages |
| `tests/test_e2e.py` | 13 functional tests | login → deposit → withdraw → logout complete flows |

**Expected total: 77 tests, 0 failures.**

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FLASK_SECRET_KEY` | `dev-secret-key-…` | Session signing key — **change in production** |
| `FLASK_DEBUG` | `true` | Set to `false` for production |

Set via `.env` (local) or the hosting platform's secrets manager (production).

Example (PowerShell — without `.env` file):
```powershell
$env:FLASK_SECRET_KEY = "your-strong-random-key"
$env:FLASK_DEBUG = "false"
python app.py
```

---

## Database Schema

Three tables inside `BACKEND/bank.db`:

| Table | Purpose |
|---|---|
| `users` | Customer identity — `id`, `username` (unique), `display_name`, `password_hash` |
| `accounts` | One account per user — `id`, `user_id` (FK), `balance` |
| `transactions` | Immutable audit log — `id`, `account_id` (FK), `type` (deposit/withdrawal), `amount`, `created_at` |

All foreign keys are enforced (`PRAGMA foreign_keys = ON`).
All multi-statement writes use explicit `commit()`/`rollback()` for atomicity.

---

## Architecture

```
Browser (Bootstrap 5 HTML + Jinja2)
       │  HTTP GET / POST (form submit)
       ▼
BACKEND/app.py  (Flask routes — no SQL, no business logic)
       │
       ├──▶ services/auth_service.py    (login, session, @login_required)
       │
       └──▶ services/account_service.py (balance, deposit, withdraw, history)
                        │  sqlite3 parameterised queries
                        ▼
                   bank.db  (SQLite — users, accounts, transactions)
```

- **Frontend** (`FRONTEND/`) — Jinja2 templates; Bootstrap 5 CDN; zero business logic.
- **Routes** (`app.py`) — HTTP boundary only; all logic delegated to services.
- **Services** (`BACKEND/services/`) — Pure Python; no Flask imports; fully unit-testable.
- **Database** (`bank.db`) — Single file; per-request connections; atomic writes.

---

## Security Notes

- Passwords stored as **Werkzeug bcrypt hashes** — never plain-text.
- Login errors return a **generic message** — username enumeration is prevented.
- Session cookies are **signed with `SECRET_KEY`** — contents cannot be tampered with.
- All queries use **parameterised statements** — SQL injection is not possible.
- **Double-submit** prevention on transaction forms via `app.js` spinner guard.
- `SECRET_KEY` loaded from `.env` via **python-dotenv** — not hard-coded in source.

---

## Production Checklist

- [ ] Generate and set a strong `FLASK_SECRET_KEY` in the hosting environment's secret store.
- [ ] Set `FLASK_DEBUG=false`.
- [ ] Serve behind **Gunicorn** (Linux) or **Waitress** (Windows), not the Flask dev server.
- [ ] Put a reverse proxy (**Nginx** / cloud load balancer) in front and enable **HTTPS / TLS**.
- [ ] Replace SQLite with **PostgreSQL** for concurrent multi-user production load.
- [ ] Add **CSRF protection** with `flask-wtf`.
- [ ] Set `Secure=True`, `HttpOnly=True`, `SameSite=Lax` on the session cookie via Flask config.
- [ ] Configure structured logging to a file or centralised log aggregator.
