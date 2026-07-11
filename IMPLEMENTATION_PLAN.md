# Banking Web Application — Implementation Plan

---

## 1. Solution Overview

### Objective
Build a browser-based banking web application that allows customers to securely log in, view their account balance, deposit funds, and withdraw funds, all backed by a lightweight Python Flask API and an SQLite database.

### Scope

| In Scope | Out of Scope |
|---|---|
| Customer login and logout | Multi-factor authentication |
| Dashboard with account summary | Admin / back-office portal |
| View current balance | Inter-bank or wire transfers |
| Deposit and withdrawal transactions | Loan or credit management |
| Session-based authentication | Mobile native application |
| Single-currency accounts (USD) | Multi-currency support |

### Users
- **Customer** — An individual account holder who authenticates and manages their own bank account through the web interface.

### Functional Requirements
1. A customer can log in with a username and password.
2. A customer is redirected to a personalised dashboard after successful login.
3. The dashboard displays the customer's name and current account balance.
4. A customer can deposit a positive monetary amount into their account.
5. A customer can withdraw a positive monetary amount, provided sufficient funds exist.
6. A customer can log out, which terminates the active session.
7. Unauthenticated access to protected pages redirects the user to the login page.

### Non-Functional Requirements
- **Security** — Passwords must be stored as hashed values; session tokens must be server-managed.
- **Usability** — All pages must be responsive and render correctly on desktop and mobile viewports via Bootstrap.
- **Reliability** — Every deposit and withdrawal must be treated as an atomic operation; partial updates must not persist.
- **Maintainability** — Frontend and Backend code must be separated into distinct top-level folders with clear internal structure.
- **Performance** — All page responses should be returned within 500 ms for a single concurrent user on localhost.

### Assumptions
- A single account is associated with each registered customer.
- Initial account seeding (creating test users) is done manually or via a setup script.
- The application runs on `localhost` during development; production deployment is out of scope.
- SQLite is sufficient for the expected single-user / low-concurrency load of this prototype.
- Bootstrap is loaded via CDN; no Node.js build step is required for the frontend.

---

## 2. High-Level Architecture

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                        BROWSER                           │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              FRONTEND  (FRONTEND/)                 │  │
│  │   HTML pages + Bootstrap CSS + minimal JS          │  │
│  │                                                    │  │
│  │  login.html  │  dashboard.html  │  shared layout   │  │
│  └────────────────────┬───────────────────────────────┘  │
└───────────────────────┼──────────────────────────────────┘
                        │  HTTP requests (form POST / GET)
                        ▼
┌──────────────────────────────────────────────────────────┐
│                   BACKEND  (BACKEND/)                    │
│                                                          │
│  Flask Application (app.py)                              │
│  ┌───────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │   Auth    │  │ Dashboard  │  │  Transactions        │ │
│  │  Routes   │  │  Routes    │  │  Routes              │ │
│  └─────┬─────┘  └─────┬──────┘  └──────────┬───────────┘ │
│        └──────────────┴──────────────────┬─┘             │
│                                          │               │
│  ┌───────────────────────────────────────▼─────────────┐ │
│  │              Service / Helper Layer                 │ │
│  │   auth_service  │  account_service  │  validators   │ │
│  └───────────────────────────────────────────────────┬─┘ │
└──────────────────────────────────────────────────────┼───┘
                                                       │  SQLite queries
                                                       ▼
┌──────────────────────────────────────────────────────────┐
│                  DATABASE  (BACKEND/)                    │
│                                                          │
│   bank.db  (SQLite file)                                 │
│   Tables: users, accounts, transactions                  │
└──────────────────────────────────────────────────────────┘
```

### Frontend → Backend → Database Interaction

1. The browser renders static HTML templates served by Flask (Jinja2).
2. User actions (login form submit, deposit form submit) are sent as HTTP POST requests to Flask route handlers.
3. Flask route handlers call the service layer, which reads from or writes to the SQLite database.
4. The service layer returns results to the route handler, which either redirects or re-renders a template with updated data.

### Request Lifecycle

```
User Action (click / form submit)
        │
        ▼
Browser sends HTTP Request (GET or POST)
        │
        ▼
Flask Router matches URL to a route handler
        │
        ├─ Session valid? ──No──▶ Redirect to /login
        │
        ▼
Route Handler calls Service function
        │
        ▼
Service Layer executes DB query via SQLite
        │
        ▼
Result returned up the chain
        │
        ▼
Flask renders Jinja2 template with data
        │
        ▼
HTTP Response sent to browser
        │
        ▼
Browser renders updated page
```

---

## 3. Component Design

### Frontend Responsibilities
- Render all user-facing HTML pages using Bootstrap for layout and styling.
- Provide forms for login, deposit, and withdrawal actions.
- Display flash messages (success / error feedback) returned by the backend.
- Enforce basic client-side input constraints (e.g., HTML5 `required`, `type="number"`, `min="0.01"`).
- Contain no business logic; all validation and computation happens in the backend.

### Backend Responsibilities
- Serve all HTML pages via Flask routes using Jinja2 templates.
- Authenticate users and manage server-side sessions.
- Validate all incoming form data before processing.
- Execute all business logic (balance checks, fund calculations).
- Communicate with SQLite through a service/helper layer; routes must not contain raw SQL.
- Return appropriate flash messages and redirect responses after state-changing operations.

### Database Responsibilities
- Persist all user credentials (hashed passwords), account balances, and transaction records.
- Enforce referential integrity between users, accounts, and transactions.
- Execute all reads and writes atomically to prevent partial updates.
- Store no plaintext passwords.

---

## 4. Folder Structure

```
project-root/
│
├── IMPLEMENTATION_PLAN.md          # This document
│
├── FRONTEND/                       # All browser-facing assets
│   ├── templates/                  # Jinja2 HTML templates (served by Flask)
│   │   ├── base.html               # Shared layout, Bootstrap CDN link, nav bar
│   │   ├── login.html              # Login form page
│   │   └── dashboard.html          # Dashboard, balance, deposit & withdraw forms
│   └── static/                     # Static files served as-is
│       ├── css/
│       │   └── custom.css          # Project-specific style overrides
│       └── js/
│           └── app.js              # Minimal client-side helpers (optional)
│
└── BACKEND/                        # All server-side code and data
    ├── app.py                      # Flask application entry point, route registration
    ├── config.py                   # App configuration (secret key, DB path, debug flag)
    ├── database.py                 # SQLite connection helper, initialisation logic
    ├── bank.db                     # SQLite database file (auto-created on first run)
    ├── services/
    │   ├── auth_service.py         # Login validation, password hashing, session helpers
    │   └── account_service.py      # Balance retrieval, deposit, withdrawal logic
    └── requirements.txt            # Python dependencies (Flask, Werkzeug, etc.)
```

### Responsibility of Each Folder

| Path | Responsibility |
|---|---|
| `FRONTEND/templates/` | Jinja2 HTML pages consumed by Flask's `render_template()` |
| `FRONTEND/static/` | CSS overrides and optional JS; served verbatim by Flask |
| `BACKEND/` (root) | Application entry point, configuration, DB initialisation |
| `BACKEND/services/` | Business logic and data-access functions; no Flask imports |
| `BACKEND/bank.db` | Single-file SQLite database created automatically at startup |

---

## 5. Module Breakdown

### Authentication Module
- **Purpose** — Control access to the application; ensure only verified customers can reach protected pages.
- **Key Responsibilities**
  - Accept username + password from the login form.
  - Verify credentials against the stored hashed password.
  - Create and store a server-side session on successful login.
  - Destroy the session on logout.
  - Provide a `login_required` decorator (or equivalent guard) used by all protected routes.
- **Pages / Routes** — `GET /login`, `POST /login`, `GET /logout`
- **Owner Component** — `BACKEND/services/auth_service.py`, `BACKEND/app.py` (route handlers)

### Dashboard Module
- **Purpose** — Provide the customer's home screen after login; present account summary and navigation to all actions.
- **Key Responsibilities**
  - Fetch and display the customer's full name and current balance.
  - Render quick-access forms for Deposit and Withdraw on the same page.
  - Display flash messages from any preceding transaction.
- **Pages / Routes** — `GET /dashboard`
- **Owner Component** — `FRONTEND/templates/dashboard.html`, `BACKEND/app.py` (dashboard route)

### Account Management Module
- **Purpose** — Expose the customer's account data in a read-only view.
- **Key Responsibilities**
  - Retrieve the current balance for the authenticated customer.
  - Format and surface balance data to the dashboard template.
  - Remain stateless between requests; no balance caching.
- **Pages / Routes** — Embedded within `/dashboard` (no separate page required for this scope)
- **Owner Component** — `BACKEND/services/account_service.py`

### Transactions Module
- **Purpose** — Handle all state-changing monetary operations (deposits and withdrawals).
- **Key Responsibilities**
  - Validate that the submitted amount is a positive number.
  - For withdrawals, confirm that the account balance is sufficient before proceeding.
  - Atomically update the account balance and append a transaction record.
  - Return a descriptive success or error flash message to the dashboard.
- **Pages / Routes** — `POST /deposit`, `POST /withdraw`
- **Owner Component** — `BACKEND/services/account_service.py`, `BACKEND/app.py` (transaction routes)

---

## 6. Implementation Roadmap

### Development Phases

#### Phase 1 — Project Scaffolding
- Create the `FRONTEND/` and `BACKEND/` directory structures.
- Set up the Python virtual environment and install Flask.
- Initialise the Flask application with configuration and static/template folder paths pointing to `FRONTEND/`.
- Create `requirements.txt`.

**Dependencies** — None. Starting point for all subsequent phases.
**Estimated Effort** — Small (environment setup only)

---

#### Phase 2 — Database Initialisation
- Implement `BACKEND/database.py` with SQLite connection helper and table-creation logic.
- Wire database initialisation to the Flask app startup sequence.
- Seed at least one test customer account for local development.

**Dependencies** — Phase 1 complete (Flask app exists).
**Estimated Effort** — Small

---

#### Phase 3 — Authentication
- Implement `auth_service.py`: credential lookup, password hash comparison, session creation and destruction.
- Implement login and logout routes in `app.py`.
- Build `FRONTEND/templates/login.html` with Bootstrap form, username/password fields, and flash message area.
- Build `FRONTEND/templates/base.html` shared layout with navigation bar and logout link.
- Implement the `login_required` route guard.

**Dependencies** — Phase 2 (database must be initialised with user records).
**Estimated Effort** — Medium

---

#### Phase 4 — Dashboard and Balance View
- Implement the `/dashboard` route in `app.py`; apply `login_required` guard.
- Implement `account_service.get_balance()` to retrieve the current balance for the session user.
- Build `FRONTEND/templates/dashboard.html` extending `base.html`; display customer name, balance, and flash messages.

**Dependencies** — Phase 3 (session must be established before dashboard is accessible).
**Estimated Effort** — Small-to-Medium

---

#### Phase 5 — Transactions (Deposit and Withdraw)
- Implement `account_service.deposit()` and `account_service.withdraw()` in `account_service.py`.
- Implement `POST /deposit` and `POST /withdraw` routes in `app.py`; apply `login_required`.
- Add Deposit and Withdraw forms to `dashboard.html` (amount input + submit button each).
- Surface success/error flash messages on the dashboard after each transaction.

**Dependencies** — Phase 4 (dashboard must exist to redirect back to after transactions).
**Estimated Effort** — Medium

---

#### Phase 6 — Styling and UX Polish
- Apply Bootstrap utility classes and layout grid to all templates for responsive design.
- Add `FRONTEND/static/css/custom.css` for any brand-specific overrides.
- Verify all pages render correctly at mobile and desktop breakpoints.
- Confirm flash messages are visually distinct (Bootstrap `alert` colours for success/danger).

**Dependencies** — Phases 3–5 (all pages must exist before final styling pass).
**Estimated Effort** — Small

---

#### Phase 7 — Integration Testing and Validation
- Manually test the full user journey: login → view balance → deposit → withdraw → logout.
- Verify edge cases: wrong password, withdrawal exceeding balance, empty/zero amounts.
- Confirm session expiry redirects to login page.
- Review that no raw passwords appear in the database.

**Dependencies** — All previous phases complete.
**Estimated Effort** — Small

---

### Dependency Chain Summary

```
Phase 1 — Scaffolding
    └─▶ Phase 2 — Database
            └─▶ Phase 3 — Authentication
                    └─▶ Phase 4 — Dashboard & Balance
                            └─▶ Phase 5 — Transactions
                                    └─▶ Phase 6 — Styling Polish
                                            └─▶ Phase 7 — Testing
```

---

*This document is a planning-level specification. It intentionally omits database schema definitions, SQL scripts, API contracts, and low-level implementation details. Those artefacts are produced during implementation.*
