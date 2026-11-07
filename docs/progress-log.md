# Progress log

One entry per step: what was built, what was tested, what went wrong.

## Step 0: Requirements and planning (27 October)

- Reviewed the project document; agreed roles, workflow, lifecycle, and stack (see decisions D1 to D17).
- Revised Chapter Three: three roles, 29 functional, 8 non-functional and 15 security requirements,
  nine diagrams, permission matrix, and status lifecycle.
- Approved: all seven confirmation items, the stack table, and the performance targets.

## Step 1.1: Project skeleton (27 to 28 October)

**Built:** configuration loader that refuses weak or missing secrets; application factory; safe error
handling; restricted CORS; hidden API docs in production; `/health`; test setup; `.gitignore`.

**Files:** `app/config.py`, `app/main.py`, `tests/conftest.py`, `tests/test_config.py`, `tests/test_app.py`,
`pytest.ini`, `requirements.in`, `requirements-dev.in`, `requirements.lock.txt`, `.env.example`, `.gitignore`.

**Results:**
- 25 tests passed (16 configuration, 9 application), before and after the `httpx2` change.
- `pip-audit`: no known vulnerabilities. `bandit`: 0 issues in 105 lines.
- `/health` returned 200; `/docs` returned 200 in development; an unknown route returned 404.
- Start without `.env`: stopped with `ConfigError: SECRET_KEY is not set`, no server running.

**Problems and fixes:**
- Nine tests errored with `fixture 'client' not found`: pytest was not loading `conftest.py`. The error
  paths showed a `test` folder although the project uses `tests`. Resolved on 28 October by renaming the
  folder to `tests` and making sure `conftest.py` sat inside it; all 25 tests then passed.
- A test-client warning led to replacing `httpx` with `httpx2` (D21).

## Step 1.2: Database foundation (29 October)

**Built:** PostgreSQL accounts and databases; SQLAlchemy base class with a constraint naming convention;
Alembic with a first migration that gives the app account read and write access to future tables only;
database settings validation; `check_db` command; database permission tests.

**Files:** `app/config.py` (replaced), `app/database.py`, `app/check_db.py`, `alembic.ini`,
`alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/0001_baseline_privileges.py`,
`tests/conftest.py` (replaced), `tests/test_config.py` (replaced), `tests/test_database.py`,
`.env.example`, `requirements.in`.

**Results:**
- 43 tests passed (27 configuration, 9 application, 7 database).
- Migration: upgrade, downgrade, and upgrade again all ran cleanly. `heads` and `current` show `0001`.
- `check_db`: connected as `pillbrook_app` to PostgreSQL 18.2.
- Manual check: `CREATE TABLE` as `pillbrook_app` returned `permission denied for schema public`.
- `pip-audit`: no known vulnerabilities. `bandit`: 0 issues in 272 lines.
- The `postgres` access rules were restored to `scram-sha-256` after the password reset.

**Problems and fixes:**
- Forgotten `postgres` password: reset by briefly setting `trust` in `pg_hba.conf` for local connections,
  setting a new password with `\password postgres`, then restoring `scram-sha-256` and restarting the service.
- SQL typed into PowerShell instead of psql: SQL belongs at the `postgres=#` prompt.
- `check_db.py` was not found: the file was missing or misnamed.
- The migration file sat in `alembic\` and `versions` had been created as a file. Alembic therefore saw no
  migration, and one test failed. Fixed by creating `versions` as a folder and moving the file in.
- My first downgrade test could pass with no migration at all. Replaced with a test that checks access
  exists while migrated and disappears after the downgrade, and added a test that the migration is registered.

  ## Step 1.3: React skeleton and API connection (30 October)

**Built:** React app (Vite, React Router) in `frontend/`; a development proxy so the browser talks to
one address; the API moved under `/api`; an `apiFetch` helper that only calls `/api/` paths and never
echoes submitted data; Home, System status and Page-not-found screens; mobile-first base styles.

**Files:** `backend/app/main.py` and `backend/tests/test_app.py` (replaced); `frontend/package.json`,
`package-lock.json`, `vite.config.js`, `index.html`; `src/main.jsx`, `App.jsx`, `api.js`, `styles.css`;
`src/pages/Home.jsx`, `Status.jsx`, `NotFound.jsx`; `src/test/setup.js`; tests `src/api.test.js`,
`src/App.test.jsx`, `src/pages/Status.test.jsx`; root `.gitignore` (Node lines).

**Installed (resolved by npm on 30 October):** react 19.3.1, react-dom 19.3.1, react-router 7.18.5,
vite 8.3.5, @vitejs/plugin-react 6.1.2, vitest 5.0.5, jsdom 29.1.1, @testing-library/react 16.3.3,
@testing-library/dom 10.4.2.

**Results:**
- Backend: 44 tests passed (27 configuration, 10 application, 7 database).
- Frontend: 15 tests passed (9 API helper, 3 Status page, 3 routing).
- `npm run build` succeeded: 25 modules, 260 kB script (83 kB compressed).
- `npm audit`: 0 vulnerabilities. No backend dependencies changed in this step.
- Browser checks: the Status page, the proxy (`/api/health` through port 5173), the not-found page, the
  API docs at `/api/docs`, and the unreachable-server message all behaved as expected.

**Problems and fixes:**
- `src/App.jsx` was not created, which caused three failures at once: the routing tests, the build, and
  the dev server all reported `Failed to resolve import "./App.jsx"`.
- `backend/tests/test_app.py` still held the old content, so two tests asked for `/health` and `/docs`.
  Replacing it fixed both. Python's saved copies still remembered the old `test` folder name; clearing
  `.pytest_cache` and `__pycache__` removed the stale path.
- `uvicorn.exe` is blocked by a Windows Application Control policy. All tools are run through `python -m`.

## Step 2.1: Users table, password handling, first Administrator (31 October)

**Built:** `users` table (migration 0002) with rules enforced by the database; `User` model; Argon2id
hashing at the OWASP minimum (19 MiB, 2 rounds, 1 lane); password rules (15 to 128 characters, NFKC
normalisation, no name, email name or "pillbrook", not on the common-password list); common-password
list (SecLists NCSC top 100,000, 99,840 lines, MIT licence); email checker; `create_admin` command;
`measure_hashing` timer.

**Files:** `app/models.py`, `app/passwords.py`, `app/emails.py`, `app/create_admin.py`,
`app/measure_hashing.py`, `app/data/common_passwords.txt`, `app/data/README.md`,
`alembic/versions/0002_users.py`; `alembic/env.py` (one line added); tests `test_passwords.py`,
`test_emails.py`, `test_users_table.py`, `test_create_admin.py`; `conftest.py` (replaced) and
`test_database.py` (one test updated); `requirements.in`, `requirements.lock.txt`.

**Installed:** argon2-cffi 25.1.0, email-validator 2.3.0 (with dnspython 2.9.1, cffi 2.1.1, pycparser 3.12).

**Results:**
- 92 tests passed (27 configuration, 10 application, 7 database, 21 password, 11 email, 7 users-table,
  9 first-Administrator).
- Migration 0002 applied to the development database; `alembic current` shows `0002 (head)`.
- Hashing takes about 40 ms and checking about 40 ms on the development computer.
- `pip-audit`: no known vulnerabilities. `bandit`: 0 issues.
- The first Administrator was created with `python -m app.create_admin`.
- Stored row checked: role `admin`, verified, hash begins `$argon2id$v=19$m=19456,t=2,p=1$`.
- A second run of `create_admin` refused with "An Administrator already exists."

**Problems and fixes:**
- The first test run failed with `cannot import name 'passwords'` because the new files were not yet in
  `backend\app`. Creating them fixed it.
- `create_admin.py` was missing on its first run: `No module named app.create_admin`.

## Step 2.2a: Login, sessions, throttling and audit log: the API (1 November)

**Built:** login, logout and "who am I" endpoints under /api/auth; sessions kept in the database (a
random 256-bit code in a protected cookie, only its SHA-256 fingerprint stored); idle expiry (60 minutes)
and absolute expiry (12 hours); lock after 4 wrong attempts within 10 minutes for 10 minutes; one
identical answer for every kind of failed login; CSRF token derived from the session code and
SECRET_KEY; an audit log the application account can add to and read but not change or delete;
automatic upgrade of old password hashes at login; migration 0003 (sessions, audit_log).

**Files:** `app/tokens.py`, `app/throttle.py`, `app/schemas.py`, `app/audit.py`, `app/sessions.py`,
`app/auth.py`, `alembic/versions/0003_sessions_and_audit_log.py`; `app/models.py`, `app/database.py`,
`app/main.py` and `app/config.py` (changed); tests `test_tokens.py`, `test_throttle.py`,
`test_auth_tables.py`, `test_auth_api.py`; `conftest.py` (replaced); `test_database.py` (one test updated).
No new packages.

**Results:**
- 140 tests passed (92 earlier, plus 7 token, 6 throttle, 6 table, 29 API).
- Migration 0003 applied; `alembic current` shows `0003 (head)`.
- Live check from PowerShell: login 200 (user and role admin, no password or hash), me 200, logout 204,
  me 401 "Not signed in."
- `/docs` moved to `/api/docs` earlier (D25); the old address returns 404.
- `pip-audit`: no known vulnerabilities. `bandit`: 0 issues in 877 lines.
- Password list: Git reports `i/lf w/lf attr/-text`; `.gitattributes` keeps its line endings unchanged.
## Step 2.2b: Login screens (2 November)

**Built:** sign-in state for the whole app, kept in memory only; login page with labelled fields, a
"Show password" box, clear messages and a button that disables while sending; header with name, role and
Sign out; "My account" page; protected pages that send a signed-out visitor to the sign-in page and bring
them back; the CSRF token sent automatically on every change; a notice when a session ends by itself;
a retry screen when the server cannot be reached; the home page greets a signed-in user.

**Files:** `frontend/src/auth.jsx`, `SessionGate.jsx`, `RequireAuth.jsx`, `roles.js`,
`pages/Login.jsx`, `pages/Account.jsx`, `test/mockApi.js`; changed `api.js`, `App.jsx`, `main.jsx`,
`pages/Home.jsx`, `styles.css`; tests `auth.test.jsx`, `pages/Login.test.jsx`, `roles.test.js`,
`api.test.js` and `App.test.jsx` (replaced). No new packages; the backend did not change.

**Results:**
- Frontend: 47 tests passed in 6 files (14 API helper, 9 sign-in state, 11 sign-in page, 9 App,
  1 roles, 3 status page). Backend: 140 passed.
- `npm run build`: 31 modules, 267 kB (85 kB compressed). `npm audit`: 0 vulnerabilities.
- Checked in the browser: the sign-in redirect and return, sign-in, staying signed in after a reload,
  empty browser storage and an HttpOnly session cookie, sign-out to the home page, the wrong-password
  message, and the public status page.

**Problems and fixes:**
- A test showed that signing out from a protected page landed on the sign-in page, and the next person to
  sign in would have been taken back to the previous page. Fixed by recording that the person signed out
  on purpose (`signedOutOnPurpose`), so protected pages send them home.
- One of my edit instructions put a new check into the wrong test, so one test failed although the app was
  correct. The whole test file was replaced.
- `backend/.env` was found with a malformed line 21 (`.env line 21 is not in KEY=VALUE form`), so the
  backend refused to start. The configuration check worked as designed. Fixed by correcting the file.
- The cause of the problem was a copy-paste error: the line was meant to be a comment, but the `#` was missing.
## Step 2.3: Role-based access control (5 November)

**Built:** Chapter Three's permission table (Table 3.3) as code (13 permissions, read-only at run time);
guards for protected functions (`require_signed_in` and `require_permission`, the second with an option
for anything that changes data); the role is read from the database on every request, so a change applies
at once; a refusal answers 403 without saying what was needed and is recorded in the audit log;
sign-in and `/api/auth/me` return the role's permissions; screens show menu links by permission and a
"You don't have permission" page.

**Files:** backend `app/permissions.py`, `app/access.py` (new), `app/auth.py`, `app/schemas.py`,
`app/audit.py` (changed), tests `test_permissions.py`, `test_route_guards.py`, `test_access.py`;
frontend `src/navigation.js`, `src/RequirePermission.jsx`, `src/pages/Forbidden.jsx` (new), `auth.jsx`,
`App.jsx`, `test/mockApi.js` (changed), tests `navigation.test.js`, `RequirePermission.test.jsx`,
`permissions.test.jsx`. No new packages.

**Results:** backend 163 passed; frontend 59 passed in 9 files; build clean; `npm audit` 0
vulnerabilities; `pip-audit` clean; `bandit` 0 issues; the Administrator's `/api/auth/me` listed 12
permissions as expected.

**Problems and fixes:**
- My first "every route has a guard" test walked `app.routes`, but this FastAPI version keeps included
  routes inside an `_IncludedRouter`, so the test saw no routes. Two of its tests passed without checking
  anything; only a third, which compared the open-route list with the routes that exist, caught it.
- A second attempt (capturing the route during a request) also failed on this version.
- The final test uses only public behaviour: it reads the routes the application advertises, sends a
  request with no sign-in to each one that is not on the open list, and requires 401. A scratch route added
  without a guard proves the check can fail.
- This check cannot tell that a route has the wrong permission. Each endpoint therefore gets its own
  role-by-role test (decision D55).

**Problems and fixes:** none in this step.

## Unresolved

- Repository scan for committed secrets (SR10): no source control in use yet.
- `requirements.lock.txt` includes development tools. A production-only list comes in Phase 6.