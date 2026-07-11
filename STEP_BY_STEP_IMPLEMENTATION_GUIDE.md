# Banking Web Application — Step-by-Step Implementation Guide

> **Reference:** This guide expands on [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md).
> Every instruction is written in plain English. No source code is included — only logic,
> reasoning, and the precise steps a developer must follow.

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Backend Implementation](#2-backend-implementation)
3. [Frontend Implementation](#3-frontend-implementation)
4. [Integration Steps](#4-integration-steps)
5. [Validation Rules](#5-validation-rules)
6. [Testing](#6-testing)
7. [Deployment](#7-deployment)

---

## 1. Environment Setup

### 1.1 Prerequisites Check

Before writing a single line of code, confirm that the following tools are available on the
development machine:

- **Python 3.9 or higher** — the runtime for the Flask backend.
- **pip** — Python's package installer; it ships with modern Python distributions.
- **A terminal / command prompt** — all setup commands are run here.
- **A code editor** (e.g. VS Code) — for writing and navigating files.

Verify Python is installed by asking the terminal to print its version. If the command is not
found, download Python from python.org and re-run the check before continuing.

---

### 1.2 Create the Project Directory Structure

Create the top-level project folder (e.g. `banking-app/`) and inside it create two sub-folders:
`FRONTEND/` and `BACKEND/`. These two folders must remain completely separate — one owns all
browser-facing files, the other owns all server-side files.

Inside `FRONTEND/`, create two more folders: `templates/` and `static/`. Inside `static/`,
create `css/` and `js/` sub-folders. These will hold the HTML pages and stylesheets
respectively.

Inside `BACKEND/`, create a `services/` sub-folder. This is where all business logic modules
will live, cleanly separated from the Flask routing layer.

The resulting skeleton should match the folder structure documented in Section 4 of
`IMPLEMENTATION_PLAN.md`.

---

### 1.3 Create and Activate a Python Virtual Environment

Navigate into the `BACKEND/` folder in the terminal. Create a virtual environment there. A
virtual environment is an isolated Python installation that keeps this project's dependencies
separate from every other project on the machine.

After creation, activate the virtual environment:

- On **Windows**, run the `activate` script inside the `Scripts/` folder of the newly created
  environment.
- On **macOS / Linux**, source the `activate` script inside the `bin/` folder.

Once activated, the terminal prompt will show the environment name in parentheses. All
subsequent `pip install` commands must be run while this environment is active.

---

### 1.4 Install Flask and Dependencies

With the virtual environment active, use `pip` to install the following packages:

- **Flask** — the web framework that handles routing, templating, and sessions.
- **Werkzeug** — Flask depends on this automatically, but it also provides the password hashing
  utilities (`generate_password_hash` and `check_password_hash`) that will be used in the
  authentication service.

After installation, generate a `requirements.txt` file by asking `pip` to freeze the currently
installed packages into that file. Place `requirements.txt` inside the `BACKEND/` folder. This
file allows any other developer to recreate the exact same environment by running
`pip install -r requirements.txt`.

---

### 1.5 Verify the Flask Installation

Create a temporary, minimal Python file inside `BACKEND/` that imports Flask and prints the
Flask version to the terminal. Run it to confirm the installation succeeded, then delete the
temporary file. Do not proceed to backend implementation until this check passes.

---

## 2. Backend Implementation

### 2.1 Configuration File (`config.py`)

The first real file to create is the configuration module. This file's sole job is to hold
environment-level settings so that they are defined in one place and referenced everywhere else.

Define the following settings inside this file:

- **`SECRET_KEY`** — a long, random string used by Flask to sign session cookies. This must
  never be guessed or exposed publicly. During development, any long random string works; in
  production this must come from a secure environment variable.
- **`DATABASE_PATH`** — the file-system path to the SQLite database file (`bank.db`). Express
  this as a path relative to the `BACKEND/` folder so it works regardless of where the project
  is checked out.
- **`DEBUG`** — a boolean flag. Set it to `True` during development so Flask auto-reloads on
  file changes and shows detailed error pages. It must be `False` in production.

No business logic belongs here — only constants.

---

### 2.2 Database Helper (`database.py`)

This module owns the entire relationship between the application and SQLite. It must do three
things:

**Open a connection.**
Write a function that opens a connection to `bank.db` using Python's built-in `sqlite3` module.
The connection path is read from `config.py`. This function is called once per request, not once
per application start, because SQLite connections are not thread-safe and must not be shared.

**Initialise tables.**
Write a second function that creates the three required tables — `users`, `accounts`, and
`transactions` — if they do not already exist. Use the `CREATE TABLE IF NOT EXISTS` SQL
construct so this function is safe to call at every startup without destroying existing data.
Think through what each table needs to store:

- `users` must hold an identifier, a unique username, a full display name, and a hashed
  password field.
- `accounts` must hold an identifier, a foreign key pointing to the owning user, and the
  current balance stored as a decimal number.
- `transactions` must hold an identifier, a foreign key to the account, a transaction type
  (either "deposit" or "withdrawal"), the amount, and a timestamp.

**Seed test data.**
Write a third function that checks whether any users already exist, and if not, inserts one test
user. Hash the test password using Werkzeug's `generate_password_hash` before storing it. Also
insert a corresponding account row for that user with a non-zero starting balance. This lets a
developer log in immediately after first run without manual database work.

**Wire initialisation to app startup.**
This `database.py` module must be called from `app.py` before the first request is ever served,
so that `bank.db` and all tables are guaranteed to exist at runtime.

---

### 2.3 Authentication Service (`services/auth_service.py`)

This module contains all logic related to identity — who the user is and whether they are
allowed in.

**Password verification logic.**
Write a function that accepts a plain-text password and a stored hash, and returns `True` or
`False`. Use Werkzeug's `check_password_hash` for this comparison. Never compare passwords with
a plain `==` operator — hashed comparison is mandatory.

**User lookup logic.**
Write a function that takes a username, queries the `users` table, and returns the full user
record if found, or `None` if not. This function must use a parameterised query (passing the
username as a bound parameter, not by string concatenation) to prevent SQL injection.

**Session creation logic.**
Write a function that receives a verified user record and writes the user's ID and display name
into Flask's `session` dictionary. Flask's session object is a signed cookie — its contents are
safe to read but cannot be tampered with by the browser because Flask signs them with the
`SECRET_KEY`.

**Session teardown logic.**
Write a function that clears the session dictionary entirely. This is called when the user logs
out.

**Login-required decorator.**
Write a function that can be used as a decorator on any Flask route. Inside it, check whether a
user ID exists in `session`. If it does, allow the route to proceed normally. If it does not,
redirect the request to the login page with an appropriate flash message. This decorator must be
applied to every protected route — dashboard, deposit, and withdraw.

---

### 2.4 Account Service (`services/account_service.py`)

This module owns all logic related to money. No route handler should ever compute a balance or
update funds directly — those operations must go through this service.

**Get balance.**
Write a function that accepts a user ID, queries the `accounts` table for the account belonging
to that user, and returns the current balance as a float. If no account is found, raise a clear
exception rather than returning `None` silently.

**Deposit.**
Write a function that accepts a user ID and a deposit amount. It must:

1. Retrieve the current balance for the user.
2. Add the deposit amount to the current balance to compute the new balance.
3. Update the `accounts` table with the new balance.
4. Insert a row into the `transactions` table recording the deposit type, the amount, and the
   current timestamp.
5. Commit the database transaction so both writes are saved atomically. If either write fails,
   roll back both so the database remains consistent.

**Withdraw.**
Write a function that accepts a user ID and a withdrawal amount. It must:

1. Retrieve the current balance for the user.
2. Check that the current balance is greater than or equal to the withdrawal amount. If not,
   raise an exception with a message like "Insufficient funds" — the route handler will catch
   this and convert it into a flash message.
3. Subtract the withdrawal amount from the current balance.
4. Update the `accounts` table with the new balance.
5. Insert a row into the `transactions` table recording the withdrawal type, the amount, and the
   timestamp.
6. Commit atomically, same as deposit.

The key design principle: this service never imports Flask. It only uses `database.py` and
Python's standard library. Keeping Flask out of the service layer means it can be tested
independently of HTTP.

---

### 2.5 Flask Application Entry Point (`app.py`)

This file is the nerve centre of the backend. It creates the Flask application object, registers
all routes, and ties together configuration, the database, and the service layer.

**Create the Flask app object.**
Instantiate a Flask application and pass it the path to `FRONTEND/templates/` as the template
folder and `FRONTEND/static/` as the static folder. This is a critical step — Flask defaults to
looking for templates next to `app.py`, but the project structure places them in a separate
`FRONTEND/` folder, so the paths must be set explicitly.

**Load configuration.**
Apply all settings from `config.py` to the Flask app object so that `SECRET_KEY` and other
settings are available throughout the application.

**Register an app startup hook.**
Tell Flask to call the database initialisation function from `database.py` once before the first
request is processed. This guarantees the database tables and seed data exist before any route
is hit.

**Implement the following routes:**

---

#### Route: `GET /` (Root Redirect)
When a user lands on the root URL, redirect them immediately to `/login`. This ensures there is
no "dead" root page.

---

#### Route: `GET /login`
Check whether the user already has an active session. If they do, redirect them to `/dashboard`
— there is no reason to show the login page to someone already logged in. If they do not have a
session, render the `login.html` template.

---

#### Route: `POST /login`
This route handles the login form submission. The logic sequence is:

1. Extract the username and password from the submitted form data.
2. Call the `auth_service` user lookup function to find the user record by username.
3. If no user is found, flash an error message saying the credentials are invalid and re-render
   the login page. Do not say "username not found" specifically — always use a generic "Invalid
   username or password" message to avoid revealing which field was wrong.
4. If a user is found, call the password verification function. If the password does not match,
   same generic error and re-render.
5. If both checks pass, call the session creation function to write the user into the session,
   then redirect to `/dashboard`.

---

#### Route: `GET /logout`
Call the session teardown function. Flash a "You have been logged out" message. Redirect to
`/login`. Apply the `login_required` decorator so only authenticated users can call this route.

---

#### Route: `GET /dashboard`
Apply the `login_required` decorator. Read the user ID from the session. Call
`account_service.get_balance()` with that user ID. Pass the user's display name (also from the
session) and the retrieved balance to `render_template('dashboard.html', ...)`. The template
will handle display.

---

#### Route: `POST /deposit`
Apply the `login_required` decorator. The logic sequence is:

1. Extract the amount from the submitted form data.
2. Pass it to the validation layer (see Section 5). If invalid, flash the error and redirect
   back to `/dashboard`.
3. Call `account_service.deposit()` with the user ID from the session and the validated amount.
4. Flash a success message showing the deposited amount.
5. Redirect to `/dashboard` so the updated balance is shown immediately.

---

#### Route: `POST /withdraw`
Apply the `login_required` decorator. The logic sequence mirrors deposit, with one addition:

1. Extract and validate the amount.
2. Call `account_service.withdraw()` inside a `try/except` block. The withdraw function raises
   an exception if funds are insufficient.
3. If the exception is caught, flash the exception message as an error and redirect to
   `/dashboard`.
4. On success, flash a success message and redirect to `/dashboard`.

---

### 2.6 Session Management

Flask's built-in session is a signed browser cookie. Understand how it works:

- When a user logs in, data written to `session` (like `user_id` and `display_name`) is
  serialised, signed with `SECRET_KEY`, and sent to the browser as a cookie.
- On every subsequent request, Flask reads the cookie, verifies the signature, and makes the
  session data available in the `session` dictionary.
- Because it is a **signed** cookie, the browser cannot modify the session contents without
  invalidating the signature. However, the contents can be read by the browser, so never store
  sensitive data (like passwords or raw balances) in the session. Only store non-sensitive
  identifiers.
- When the user logs out or the session is cleared, Flask instructs the browser to delete the
  cookie.

The `login_required` decorator relies entirely on checking whether `session` contains a valid
`user_id`. If it does not, the request is rejected before any route logic runs.

---

### 2.7 Error Handling

Define the following error-handling behaviours at the application level:

**404 Not Found.**
Register a custom 404 handler in `app.py` that renders a minimal HTML page saying the requested
page does not exist, with a link back to `/login`. This prevents Flask's raw default error page
from being shown to users.

**500 Internal Server Error.**
Register a custom 500 handler that renders a minimal HTML page saying something went wrong,
again with a link back to `/login`. This must not expose stack traces to the user. Stack traces
are only visible in the terminal when `DEBUG = True`.

**Application-level exceptions.**
Any exception raised by the service layer (such as the insufficient-funds exception from
`account_service.withdraw()`) must be caught in the route handler using `try/except`. The caught
exception message is converted into a Flask flash message and the user is redirected. Never let
an unhandled exception reach the browser in production.

---

## 3. Frontend Implementation

### 3.1 Base Layout Template (`base.html`)

This is the master template that all other pages inherit from. Build it first because every
other template extends it.

The base layout must include:

- The full HTML5 document structure (`<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`).
- A `<meta name="viewport">` tag for responsive behaviour on mobile devices.
- The Bootstrap CSS CDN link inside `<head>` — no local Bootstrap installation is needed.
- A navigation bar using Bootstrap's `navbar` component. The navbar must display the application
  name (e.g. "SecureBank") on the left and a "Logout" link on the right. The logout link should
  only appear when the user is logged in — use Jinja2's `if session` conditional to control
  visibility.
- A Jinja2 **block** called `content` in the body. This is the placeholder that child templates
  will fill with their own HTML.
- A flash message area placed above the `content` block. Loop through Flask's `get_flashed_messages(with_categories=True)` and render each message as a Bootstrap `alert` component. Use
  the category (`success` or `danger`) to choose the correct Bootstrap alert colour class.
- The Bootstrap JS bundle CDN link at the bottom of `<body>`, before the closing tag.

---

### 3.2 Login Page (`login.html`)

This page extends `base.html` and fills the `content` block with the login form.

Layout goal: a centred card on the page, readable on both mobile and desktop. Use Bootstrap's
grid system (`container`, `row`, `col`) to centre the card horizontally and vertically.

The card must contain:

- A heading: "Customer Login" or similar.
- An input field for the username. Mark it as `required`. Use a Bootstrap `form-control` class.
- An input field for the password. Use `type="password"` so the characters are hidden. Mark it
  as `required`.
- A submit button labelled "Login". Style it with Bootstrap's primary button class.
- The form's `action` attribute must point to the `POST /login` route, and the `method` must be
  `POST`.

Do not add any JavaScript validation to this form. The backend handles all validation. The only
client-side constraint is HTML5's `required` attribute, which prevents submission of empty
fields.

---

### 3.3 Dashboard Page (`dashboard.html`)

This page extends `base.html` and is the primary screen after login. It serves three purposes:
displaying the balance, offering a deposit form, and offering a withdrawal form.

**Balance card.**
At the top of the content area, show a Bootstrap card or jumbotron-style panel that displays:

- A greeting: "Welcome, [customer full name]" — use the `display_name` variable passed from the
  route.
- The current balance, formatted as currency (e.g. "$1,250.00") — use the `balance` variable
  passed from the route. Use Jinja2's `|round(2)` filter and format it with a dollar sign prefix
  in the template.

**Deposit form.**
Place the deposit form in a card below the balance. It must contain:

- A heading: "Deposit Funds".
- A numeric input for the amount. Set `type="number"`, `min="0.01"`, `step="0.01"`, and mark it
  `required`. This enforces positive amounts at the browser level before the form is even
  submitted.
- A submit button labelled "Deposit". Style it with Bootstrap's success (green) button class.
- The form's `action` must point to `POST /deposit`.

**Withdrawal form.**
Place the withdrawal form in a card alongside or below the deposit form. It must contain:

- A heading: "Withdraw Funds".
- A numeric input with the same constraints as the deposit form.
- A submit button labelled "Withdraw". Style it with Bootstrap's warning (yellow) or danger
  (red) button class to visually distinguish it from the deposit action.
- The form's `action` must point to `POST /withdraw`.

**Layout tip.**
Use Bootstrap's two-column grid (`col-md-6`) to place the deposit and withdrawal forms side by
side on desktop, and stacked on mobile. This is achieved automatically by Bootstrap's responsive
grid when the viewport narrows.

---

### 3.4 Bootstrap Layout Principles

Apply these Bootstrap conventions consistently across all templates:

- Wrap all page content in a `<div class="container">` or `<div class="container-fluid">`. This
  provides automatic horizontal padding and centres content on wide screens.
- Use `row` and `col-*` classes to create multi-column layouts. Always think in terms of a
  12-column grid — two equal columns are `col-md-6` each.
- Use `card` components to visually group related content (the balance panel, each form). A card
  gives a clean bordered box with padding.
- Use `mb-3`, `mt-4`, `p-3`, and similar spacing utility classes to add margin and padding
  without writing custom CSS.
- Use `text-center` to centre headings and labels.
- Keep `custom.css` minimal — only add overrides that Bootstrap cannot achieve with utility
  classes (e.g., a brand colour or custom font).

---

## 4. Integration Steps

### 4.1 Connect Flask to the Frontend Folder

By default, Flask looks for templates in a `templates/` folder next to `app.py`, and for static
files in a `static/` folder. Since this project places those folders inside `FRONTEND/`, the
Flask application object must be told where to look.

When creating the Flask app object in `app.py`, pass two keyword arguments:

- `template_folder` — set this to the absolute or relative path pointing to
  `FRONTEND/templates/`.
- `static_folder` — set this to the absolute or relative path pointing to `FRONTEND/static/`.

Use Python's `os.path` module to construct these paths relative to the location of `app.py`.
This makes the paths portable — they work on any machine regardless of where the project folder
is placed.

Once this is set, `render_template('login.html')` will find the file in `FRONTEND/templates/login.html`, and Flask will serve files from `FRONTEND/static/` at the `/static/` URL prefix.

---

### 4.2 Connect Flask to SQLite

SQLite integration requires no third-party library — Python's built-in `sqlite3` module handles
everything. The integration follows a per-request connection pattern:

1. When a request arrives that needs database access, the service function calls
   `database.get_connection()` to open a connection to `bank.db`.
2. The function performs its queries on that connection.
3. For write operations (deposit, withdrawal), the function commits or rolls back as appropriate,
   then closes the connection.
4. For read operations (get balance, look up user), the function closes the connection after
   reading.

**Row factory.**
Configure the SQLite connection to use `sqlite3.Row` as the row factory. This lets query results
be accessed by column name (e.g., `row['balance']`) instead of by numeric index (e.g.,
`row[2]`). This makes the service layer code far more readable and less fragile when the schema
evolves.

**Database path.**
The path to `bank.db` is read from `config.py`. Ensure the path is absolute (constructed using
`os.path.join` and `os.path.dirname(__file__)`) so that SQLite always finds the file regardless
of which directory the application is launched from.

---

### 4.3 Connect HTML Forms to Flask Routes

Each HTML form's `action` attribute determines which Flask route receives the submission:

| Form | Method | Action attribute value |
|---|---|---|
| Login | POST | `/login` |
| Deposit | POST | `/deposit` |
| Withdraw | POST | `/withdraw` |
| Logout link | GET (anchor) | `/logout` |

The form field `name` attributes must exactly match what the Flask route reads from
`request.form`. For example, if the login form has `<input name="username">`, then the route
reads it as `request.form.get('username')`. Any mismatch results in `None` being received on the
backend.

**CSRF consideration.**
Flask does not include built-in CSRF protection. For this prototype, accept this limitation.
Document it as a known gap to be addressed before any public-facing deployment (typically by
adding the `flask-wtf` extension, which provides CSRF tokens automatically).

---

### 4.4 Flash Message Flow

Flash messages are the bridge between a route's result and the template's display. The flow is:

1. A route calls `flash('message text', 'category')` where category is `'success'` or
   `'danger'`.
2. Flask stores the message in the session temporarily (it is consumed on the next render and
   then discarded).
3. The next page rendered (always `dashboard.html` after a transaction, or `login.html` after a
   failed login) calls `get_flashed_messages(with_categories=True)` inside the Jinja2 template
   and renders each message as a Bootstrap alert.
4. After the page is rendered, the messages are gone — they will not appear on the next refresh.

This pattern ensures that submitting a form and then refreshing the results page does not
re-display stale messages.

---

## 5. Validation Rules

Validation happens at two levels: the browser (HTML5 constraints) and the backend (Python logic).
The backend validation is authoritative. The frontend validation is a convenience only.

### 5.1 Login Validation

| Check | Where | What to do if it fails |
|---|---|---|
| Username field is not empty | Browser (HTML5 `required`) | Browser prevents form submission |
| Password field is not empty | Browser (HTML5 `required`) | Browser prevents form submission |
| Username field is not empty | Backend (`request.form.get`) | Flash "Username is required" and re-render login |
| Password field is not empty | Backend | Flash "Password is required" and re-render login |
| Username exists in the database | Backend (`auth_service`) | Flash generic "Invalid username or password" and re-render login |
| Password matches the stored hash | Backend (`check_password_hash`) | Flash same generic message — do not distinguish between wrong username and wrong password |

The generic error message for credential failures is intentional. Saying "username not found"
leaks information about which usernames exist in the system — always use the same message for
both failure modes.

---

### 5.2 Balance Validation (Read)

- The `get_balance()` function must verify that an account record exists for the given user ID.
  If no account is found, this indicates a data integrity problem and the application should log
  an error and display a generic "Account error" message rather than crashing.
- Balance is always read fresh from the database on every dashboard load. Never cache the
  balance in the session — a cached value can be stale if another process modifies the record.

---

### 5.3 Deposit Validation

Apply these checks in order. Stop at the first failure and flash the corresponding error:

1. **Presence** — The amount field must not be empty or missing.
2. **Numeric** — The amount must be convertible to a float. Use a `try/except` around the
   conversion. If it raises a `ValueError`, the user typed a non-numeric string.
3. **Positive** — The converted float must be strictly greater than zero. A zero deposit makes
   no financial sense and should be rejected.
4. **Precision** — Optionally, round the amount to two decimal places before processing to
   prevent floating-point oddities (e.g., `10.999999` becoming `11.00`).

---

### 5.4 Withdrawal Validation

Apply all the same checks as deposit (presence, numeric, positive), plus one additional check:

5. **Sufficient funds** — After passing the format checks, call `account_service.withdraw()`,
   which internally checks whether `current_balance >= amount`. If not, it raises an exception.
   The route handler catches this exception and flashes "Insufficient funds. Your current
   balance is $X.XX." This message is more helpful than a generic error because the user needs
   to know what they have available.

Never subtract a negative withdrawal amount (which would act as a deposit). The `positive` check
prevents this.

---

## 6. Testing

### 6.1 Unit Tests

Unit tests verify individual functions in isolation — no Flask server, no real database.

**What to unit test:**

- **`auth_service` — password verification:** Call `check_password_hash` with a known hash and
  a matching plain-text password. Assert it returns `True`. Repeat with a wrong password and
  assert it returns `False`.
- **`auth_service` — user lookup:** Use a temporary in-memory SQLite database (`:memory:`) to
  insert a test user, then call the lookup function and assert it returns the correct record.
  Call it with a non-existent username and assert it returns `None`.
- **`account_service` — deposit logic:** Create an in-memory database with a test account at a
  known balance, call `deposit()`, then query the balance and assert it increased by the exact
  amount. Also assert a transaction row was inserted.
- **`account_service` — withdrawal logic (success):** Same setup. Call `withdraw()` with an
  amount less than the balance. Assert the balance decreased correctly and a transaction row was
  inserted.
- **`account_service` — withdrawal logic (insufficient funds):** Call `withdraw()` with an
  amount greater than the balance. Assert the expected exception is raised. Assert the balance
  is unchanged afterwards.
- **Validation functions:** If validators are extracted into their own helper module, test each
  one with valid input (assert no error raised), missing input, non-numeric input, and zero
  input.

Place unit tests in a `BACKEND/tests/` folder. Name each file `test_<module>.py` so that test
runners (like `pytest`) auto-discover them.

---

### 6.2 Integration Tests

Integration tests verify that Flask routes, the service layer, and the database all work
together correctly. Use Flask's built-in **test client** (`app.test_client()`) which simulates
HTTP requests without starting a real server.

**What to integration test:**

- **Login — valid credentials:** POST to `/login` with correct username and password. Assert
  the response redirects to `/dashboard`. Assert the session contains the expected `user_id`.
- **Login — invalid credentials:** POST to `/login` with a wrong password. Assert the response
  re-renders the login page (HTTP 200, not a redirect). Assert a flash error message is present
  in the response body.
- **Dashboard access — authenticated:** With an active session, GET `/dashboard`. Assert HTTP
  200. Assert the customer's name and a balance value appear in the response body.
- **Dashboard access — unauthenticated:** Without a session, GET `/dashboard`. Assert the
  response redirects to `/login`.
- **Deposit — valid amount:** POST to `/deposit` with a positive amount while authenticated.
  Assert redirect to `/dashboard`. Assert the balance shown on the subsequent dashboard load
  has increased by the deposited amount.
- **Deposit — invalid amount (zero):** POST to `/deposit` with `amount=0`. Assert redirect to
  `/dashboard` with an error flash message in the response.
- **Withdrawal — sufficient funds:** POST to `/withdraw` with an amount less than the balance.
  Assert redirect to `/dashboard`. Assert balance decreased.
- **Withdrawal — insufficient funds:** POST to `/withdraw` with an amount greater than the
  balance. Assert redirect to `/dashboard` with a "Insufficient funds" flash message.
- **Logout:** GET `/logout` while authenticated. Assert redirect to `/login`. Assert the session
  is cleared (no `user_id` present).

For each integration test, initialise a fresh in-memory database at the start of the test
function and tear it down afterwards. This prevents tests from interfering with one another.

---

### 6.3 Manual Testing Checklist

Run through this checklist in a real browser after all automated tests pass. Check each item
before marking the project complete.

**Authentication**
- [ ] Visiting the app root (`/`) redirects to the login page.
- [ ] Submitting the login form with empty fields shows browser validation warnings (not a
  server error).
- [ ] Submitting with an incorrect username shows the generic "Invalid username or password"
  message.
- [ ] Submitting with a correct username but wrong password shows the same generic message.
- [ ] Submitting with correct credentials redirects to the dashboard.
- [ ] After login, navigating directly back to `/login` redirects to the dashboard.

**Dashboard**
- [ ] The dashboard displays the correct customer name.
- [ ] The balance displayed matches what was seeded in the database.
- [ ] The dashboard is inaccessible without a session (navigating directly to `/dashboard` after
  clearing cookies redirects to login).

**Deposit**
- [ ] Depositing a valid amount (e.g., $100.00) updates the balance shown on the dashboard
  immediately after the redirect.
- [ ] A green success flash message appears after a successful deposit.
- [ ] Depositing zero shows an error flash message and the balance is unchanged.
- [ ] Depositing a negative number (if the browser allows it by bypassing `min`) shows an error.
- [ ] Depositing a non-numeric string (bypassing HTML validation via browser dev tools) shows an
  error.

**Withdrawal**
- [ ] Withdrawing a valid amount updates the balance correctly.
- [ ] A success flash message appears after a successful withdrawal.
- [ ] Attempting to withdraw more than the current balance shows the "Insufficient funds"
  message and leaves the balance unchanged.
- [ ] Withdrawing zero shows an error.

**Logout**
- [ ] Clicking logout redirects to the login page.
- [ ] After logout, pressing the browser back button and attempting to access `/dashboard`
  redirects to login (session is truly cleared).
- [ ] A "You have been logged out" flash message appears on the login page after logout.

**Responsiveness**
- [ ] Shrink the browser window to mobile width (< 768 px). All forms remain readable and
  usable. Columns stack vertically.
- [ ] The navigation bar collapses or remains usable at narrow widths.

---

## 7. Deployment

### 7.1 Run Locally (Development)

Follow these steps every time the application is started for local development:

1. Open a terminal and navigate to the `BACKEND/` folder.
2. Activate the Python virtual environment.
3. Run `app.py` using Python. Flask will start its built-in development server on
   `http://127.0.0.1:5000` by default.
4. Open a web browser and navigate to `http://localhost:5000`.
5. Use the seeded test credentials to log in.

The development server auto-reloads whenever a `.py` file is saved, thanks to `DEBUG = True` in
`config.py`. Template changes in `FRONTEND/templates/` are reflected immediately on the next
browser refresh without restarting the server.

To stop the server, press `Ctrl + C` in the terminal.

---

### 7.2 Production Considerations

The Flask built-in development server is **not suitable for production**. It handles only one
request at a time, is not hardened against malicious input, and exposes debug information. The
following changes must be made before deploying to any internet-facing environment:

**Switch to a production WSGI server.**
Deploy the Flask application behind a production-grade WSGI server such as **Gunicorn** (Linux /
macOS) or **Waitress** (Windows-compatible). These servers can handle multiple simultaneous
requests and are designed for production workloads. Add the chosen WSGI server to
`requirements.txt`.

**Disable debug mode.**
Set `DEBUG = False` in `config.py` (or read it from an environment variable). In production,
stack traces must never be sent to the browser.

**Secure the secret key.**
Never hard-code `SECRET_KEY` in source code for production. Read it from an environment variable
at runtime (e.g., `os.environ.get('SECRET_KEY')`). If the environment variable is missing at
startup, the application should refuse to start rather than fall back to a weak default.

**Use HTTPS.**
All HTTP traffic in production must be served over TLS (HTTPS). This is typically handled by a
reverse proxy such as **Nginx** or a cloud platform's load balancer placed in front of the
WSGI server. Never serve a banking application over plain HTTP in production.

**Upgrade the database.**
SQLite is appropriate for single-user development but is not suitable for concurrent multi-user
production traffic. Migrate to **PostgreSQL** or **MySQL** for production. The service layer's
use of parameterised queries makes this migration straightforward — only the connection setup in
`database.py` needs to change, not the query logic.

**Add CSRF protection.**
Install the `flask-wtf` extension and enable its CSRF protection for all forms. This prevents
cross-site request forgery attacks, where a malicious website tricks a logged-in user's browser
into submitting a form to the banking app.

**Set session cookie flags.**
Configure Flask to set the session cookie with `Secure=True` (only sent over HTTPS),
`HttpOnly=True` (not accessible to JavaScript), and `SameSite=Lax` (reduces CSRF risk). These
flags are set via Flask's configuration and add meaningful security with zero effort.

**Implement logging.**
Replace any `print` statements with Python's `logging` module. Configure log output to a file
or a centralised logging service. Log all authentication attempts (success and failure), all
transaction events, and all unhandled exceptions. Never log passwords or raw session data.

---

*This guide is intentionally code-free. It describes the logic, sequence, and reasoning behind
each implementation step. Refer to [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) for the
architectural overview and folder structure that this guide implements.*
